"""Limpieza de documentacion .mdx (Docusaurus/MDX) para el pipeline RAG.

Recorre `data/raw/` de forma recursiva, limpia cada `.mdx` y escribe en
`data/processed/`:

  * un `.md` limpio por documento, replicando el arbol de carpetas de origen
  * `documents.jsonl`, un registro por documento con el texto limpio y los
    metadatos (frontmatter + derivados), listo para el chunker de la fase 2;
  * `preprocess_report.json`, con las estadisticas de la pasada.

Que se elimina
--------------
  * Sentencias ESM `import ... from "..."` / `export const|default|...`.
  * Componentes React puramente visuales o de navegacion (tarjetas, rejillas,
    imagenes decorativas) junto con todo su contenido.
  * Componentes autocerrados desconocidos (`<ServerSetup />`): son inclusiones
    que no podemos resolver sin ejecutar Docusaurus.
  * Comentarios MDX `{/* ... */}` y HTML `<!-- ... -->`.
  * Etiquetas HTML/JSX vacias o meramente estructurales (`<div>`, `<span>`...).

Que se preserva
---------------
  * El texto principal y la jerarquia de encabezados Markdown.
  * Los bloques de codigo cercados, intactos y con su lenguaje.
  * Las tablas: las Markdown tal cual y las HTML/`<Table>` convertidas a
    tablas Markdown.
  * El contenido envuelto en componentes contenedores (`<Tabs>`, `<TabItem>`,
    `<div>`): se quita la etiqueta y se re-indenta el contenido para que no
    acabe interpretado como bloque de codigo.
  * El frontmatter YAML, extraido como metadatos.

Uso
---
    python src/ingest/preprocess_mdx.py
    python src/ingest/preprocess_mdx.py --limit 5 --dry-run -v Para que pruebe con 5 documentos,
    sin generar los archivos resultantes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

try:  # PyYAML es opcional: hay un parser minimo de respaldo
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "processed"

# Marcadores en el area de uso privado Unicode: no aparecen en la documentacion
# y sobreviven a cualquier regex o parseo de etiquetas.
CODE_MARK = ""
INLINE_MARK = ""


# ---------------------------------------------------------------------------
# Reglas por componente
# ---------------------------------------------------------------------------

# Componentes puramente visuales o de navegacion: se eliminan con hijos.
DROP_COMPONENTS = {
    "ConceptOverview",
    "DAGLoop",
    "FeatureHighlights",
    "GenAIDemoCard",
    "ImageBox",
    "LogoCard",
    "NotebookDownloadButton",
    "OTelIntegrationCard",
    "PageCard",
    "SmallLogoCard",
    "TOCInline",
    "TileCard",
    "TilesGrid",
    "TitleCard",
    "TracingIntegrations",
    "WorkflowSteps",
}

# Contenedores que aportan estructura visual pero envuelven contenido util:
# se quita la etiqueta y se conserva el interior.
UNWRAP_COMPONENTS = {
    "Tabs",
    "TabsWrapper",
    "Link",
    "Fragment",
    # `Card`/`CardGroup` a veces son navegacion (dentro llevan `PageCard`, que
    # si se descarta) y a veces envuelven ejemplos de prompts con su codigo.
    "Card",
    "CardGroup",
}

# Etiquetas HTML que se eliminan con su contenido.
DROP_HTML = {"img", "picture", "source", "iframe", "svg", "path", "style", "script"}

# Etiquetas HTML de tabla: las gestiona el conversor de tablas, no el renderer.
TABLE_TAGS = {"table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption", "colgroup", "col"}

# Etiquetas en ingles a proposito: el corpus esta en ingles y lo que se
# incrusta debe quedar en un solo idioma.
ADMONITION_LABELS = {
    "note": "Note",
    "tip": "Tip",
    "info": "Info",
    "warning": "Warning",
    "danger": "Danger",
    "caution": "Caution",
    "important": "Important",
}

CODE_MARK_RE = re.compile(f"{CODE_MARK}(\\d+){CODE_MARK}")
TAG_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9._:-]*")
FENCE_OPEN_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
INLINE_CODE_RE = re.compile(r"(?<!`)(`+)(?!`)([^\n]+?)(?<!`)\1(?!`)")
MDX_COMMENT_RE = re.compile(r"\{\s*/\*.*?\*/\s*\}", re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
ESM_IMPORT_RE = re.compile(
    r"""^[ \t]*import\s+(?:[\w*{}\s,]+\s+from\s+)?["'][^"'\n]+["'];?[ \t]*$""", re.MULTILINE
)
ESM_EXPORT_RE = re.compile(
    r"^[ \t]*export\s+(?:default|const|let|var|function|class|\{|\*).*$", re.MULTILINE
)
ADMONITION_OPEN_RE = re.compile(r"^[ \t]*:::(" + "|".join(ADMONITION_LABELS) + r")[ \t]*(.*)$")
ADMONITION_CLOSE_RE = re.compile(r"^[ \t]*:::[ \t]*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$", re.MULTILINE)
THEMATIC_BREAK_RE = re.compile(r"[ \t]{0,3}(?:-{3,}|\*{3,}|_{3,})[ \t]*")
EMPTY_HTML_RE = re.compile(r"<([A-Za-z][\w.:-]*)[^>]*>\s*</\1>")


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


def split_frontmatter(text: str) -> tuple[str, str]:
    """Separa el bloque frontmatter YAML (`---`) del cuerpo del documento."""
    if not text.startswith("---"):
        return "", text
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return "", text
    for idx in range(1, len(lines)):
        if lines[idx].strip() in {"---", "..."}:
            return "\n".join(lines[1:idx]), "\n".join(lines[idx + 1 :])
    return "", text


def parse_frontmatter(raw: str) -> dict[str, Any]:
    """Parsea el frontmatter con PyYAML si esta disponible; si no, a mano."""
    if not raw.strip():
        return {}
    if yaml is not None:
        try:
            data = yaml.safe_load(raw)
            if isinstance(data, dict):
                return _jsonable(data)
            return {}
        except Exception:  # YAML invalido: caemos al parser minimo
            pass
    return _simple_yaml(raw)


def _jsonable(value: Any) -> Any:
    """Deja el frontmatter serializable a JSON.

    PyYAML convierte `date: 2024-01-30` en un `datetime.date`, que revienta al
    escribir el jsonl. Cualquier tipo que no sea JSON se guarda como texto.
    """
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _simple_yaml(raw: str) -> dict[str, Any]:
    """Parser minimo para el frontmatter tipico: `clave: valor`, listas planas.

    Cubre lo que aparece en las docs de MLflow (title, description, keywords,
    sidebar_*, tags). No pretende ser YAML completo.
    """
    data: dict[str, Any] = {}
    key: str | None = None
    for line in raw.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.lstrip().startswith("- ") and key:
            data.setdefault(key, [])
            if isinstance(data[key], list):
                data[key].append(_scalar(line.lstrip()[2:]))
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+):[ \t]*(.*)$", line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if value == "":
            data[key] = []  # posible lista en bloque; se rellena arriba
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [_scalar(p) for p in inner.split(",") if p.strip()] if inner else []
        else:
            data[key] = _scalar(value)
    return {k: v for k, v in data.items() if v != [] or isinstance(v, list)}


def _scalar(value: str) -> Any:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return value


# ---------------------------------------------------------------------------
# Proteccion del codigo
# ---------------------------------------------------------------------------


@dataclass
class CodeVault:
    """Guarda los fragmentos de codigo mientras se limpia el resto del texto.

    Es la pieza critica del script: en las docs de MLflow hay lineas
    `export MLFLOW_TRACKING_URI=...` (bash) e `import mlflow` (Python) dentro de
    bloques cercados. Sin proteger el codigo, la limpieza de sentencias ESM se
    los llevaria por delante.
    """

    blocks: list[str] = field(default_factory=list)
    spans: list[str] = field(default_factory=list)

    def hide_fenced(self, text: str) -> str:
        out: list[str] = []
        lines = text.split("\n")
        i = 0
        while i < len(lines):
            match = FENCE_OPEN_RE.match(lines[i])
            if not match or not match.group("fence"):
                out.append(lines[i])
                i += 1
                continue
            indent, fence = match.group("indent"), match.group("fence")
            char, size = fence[0], len(fence)
            body = [lines[i]]
            i += 1
            while i < len(lines):
                body.append(lines[i])
                stripped = lines[i].strip()
                if stripped and stripped[0] == char and set(stripped) == {char} and len(stripped) >= size:
                    i += 1
                    break
                i += 1
            # Se guarda sin la indentacion del cercado de apertura: al restaurar
            # se re-aplica la indentacion que tenga el marcador en ese momento,
            # de modo que el codigo dentro de un <TabItem> acabe a margen cero
            # y el de una lista conserve su sangria.
            dedented = "\n".join(_strip_prefix(line, indent) for line in body)
            self.blocks.append(dedented)
            out.append(f"{indent}{CODE_MARK}{len(self.blocks) - 1}{CODE_MARK}")
        return "\n".join(out)

    def hide_inline(self, text: str) -> str:
        def repl(match: re.Match[str]) -> str:
            self.spans.append(match.group(0))
            return f"{INLINE_MARK}{len(self.spans) - 1}{INLINE_MARK}"

        return INLINE_CODE_RE.sub(repl, text)

    def restore(self, text: str) -> str:
        def repl_inline(match: re.Match[str]) -> str:
            return self.spans[int(match.group(1))]

        text = re.sub(f"{INLINE_MARK}(\\d+){INLINE_MARK}", repl_inline, text)

        def repl_block(match: re.Match[str]) -> str:
            indent = match.group(1)
            block = self.blocks[int(match.group(2))]
            return "\n".join(indent + line if line else line for line in block.split("\n"))

        text = re.sub(f"^([ \\t]*){CODE_MARK}(\\d+){CODE_MARK}", repl_block, text, flags=re.MULTILINE)

        def repl_stray(match: re.Match[str]) -> str:
            # Marcador que quedo en mitad de una linea: se degrada a codigo
            # en linea para no dejar basura ni perder el fragmento.
            body = self.blocks[int(match.group(1))].split("\n")[1:-1]
            return "`" + " ".join(" ".join(body).split()) + "`"

        return CODE_MARK_RE.sub(repl_stray, text)

    def count_blocks(self) -> int:
        return len(self.blocks)


def _strip_prefix(line: str, prefix: str) -> str:
    """Quita la indentacion del cercado de apertura sin tocar el codigo."""
    if not prefix:
        return line
    if line.startswith(prefix):
        return line[len(prefix) :]
    return line.lstrip() if not line.strip() else line


# ---------------------------------------------------------------------------
# Escaneo de etiquetas JSX/HTML
# ---------------------------------------------------------------------------


@dataclass
class Tag:
    name: str
    attrs_raw: str
    closing: bool
    self_closing: bool
    start: int
    end: int  # indice del caracter siguiente a '>'


def scan_tag(text: str, i: int) -> Tag | None:
    """Lee una etiqueta que empieza en `text[i] == '<'`.

    Respeta comillas y llaves anidadas, asi que soporta props JSX multilinea
    como `features={[{...}, {...}]}`. Devuelve None si no es una etiqueta
    (comparaciones en prosa, autolinks `<https://...>`, correos `<a@b.com>`).
    """
    if text[i] != "<":
        return None
    j = i + 1
    closing = False
    if j < len(text) and text[j] == "/":
        closing = True
        j += 1
    match = TAG_NAME_RE.match(text, j)
    if not match:
        return None
    name = match.group(0)
    j = match.end()
    # Tras el nombre solo puede venir espacio, '/' o '>'. Esto descarta
    # autolinks (`<https://x>`, `<user@host>`) y comparaciones.
    if j < len(text) and text[j] not in " \t\r\n/>":
        return None
    depth = 0
    quote = ""
    while j < len(text):
        c = text[j]
        if quote:
            if c == quote:
                quote = ""
        # Dentro de una expresion `{...}` el apostrofo casi siempre es prosa
        # ("optimize your LLM's outputs" en un fragmento `<>...</>`), no el
        # inicio de una cadena: tratarlo como comilla dejaba la etiqueta sin
        # cerrar y volcaba el componente entero al texto limpio.
        elif c == '"' or (c == "'" and depth == 0):
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth = max(0, depth - 1)
        elif c == ">" and depth == 0:
            break
        j += 1
    else:
        return None  # etiqueta sin cerrar
    inner = text[match.end() : j]
    self_closing = inner.rstrip().endswith("/")
    if self_closing:
        inner = inner.rstrip()[:-1]
    return Tag(name, inner, closing, self_closing, i, j + 1)


def parse_attrs(raw: str) -> dict[str, str]:
    """Extrae props `clave="valor"` o `clave={expr}` de una etiqueta."""
    attrs: dict[str, str] = {}
    i = 0
    while i < len(raw):
        match = re.compile(r"\s*([A-Za-z_][\w.:-]*)\s*").match(raw, i)
        if not match:
            i += 1
            continue
        key = match.group(1)
        i = match.end()
        if i >= len(raw) or raw[i] != "=":
            attrs[key] = "true"
            continue
        i += 1
        if i < len(raw) and raw[i] in "\"'":
            quote = raw[i]
            end = raw.find(quote, i + 1)
            if end == -1:
                break
            attrs[key] = raw[i + 1 : end]
            i = end + 1
        elif i < len(raw) and raw[i] == "{":
            depth, j, quote = 0, i, ""
            while j < len(raw):
                c = raw[j]
                if quote:
                    if c == quote:
                        quote = ""
                elif c == '"':  # ver la nota sobre apostrofos en `scan_tag`
                    quote = c
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            attrs[key] = raw[i + 1 : j].strip()
            i = j + 1
        else:
            match_bare = re.compile(r"(\S+)").match(raw, i)
            if not match_bare:
                break
            attrs[key] = match_bare.group(1)
            i = match_bare.end()
    return attrs


def find_matching_close(text: str, tag: Tag) -> int | None:
    """Devuelve el indice final de la etiqueta de cierre que empareja con `tag`."""
    depth = 1
    i = tag.end
    while i < len(text):
        pos = text.find("<", i)
        if pos == -1:
            return None
        found = scan_tag(text, pos)
        if not found:
            i = pos + 1
            continue
        if found.name == tag.name and not found.self_closing:
            depth += -1 if found.closing else 1
            if depth == 0:
                return found.end
        i = found.end
    return None


# ---------------------------------------------------------------------------
# Tablas HTML -> Markdown
# ---------------------------------------------------------------------------


def convert_html_tables(text: str) -> str:
    """Convierte `<Table>`/`<table>` con HTML crudo en tablas Markdown."""
    out: list[str] = []
    i = 0
    while True:
        pos = text.find("<", i)
        if pos == -1:
            out.append(text[i:])
            break
        tag = scan_tag(text, pos)
        if not tag or tag.closing or tag.name.lower() != "table":
            out.append(text[i : pos + 1])
            i = pos + 1
            continue
        end = find_matching_close(text, tag) if not tag.self_closing else tag.end
        if end is None:
            out.append(text[i : pos + 1])
            i = pos + 1
            continue
        out.append(text[i:pos])
        markdown = _html_table_to_markdown(text[tag.end : end])
        if markdown:
            out.append(f"\n\n{markdown}\n\n")
        i = end
    return "".join(out)


def _html_table_to_markdown(inner: str) -> str:
    rows: list[tuple[bool, list[str]]] = []
    for tr in re.finditer(r"(?is)<tr[^>]*>(.*?)</tr>", inner):
        cells: list[str] = []
        header = False
        for cell in re.finditer(r"(?is)<(t[hd])[^>]*>(.*?)</\1>", tr.group(1)):
            header = header or cell.group(1).lower() == "th"
            cells.append(cell.group(2))
        if cells:
            rows.append((header, cells))
    if not rows:
        return ""
    # Una tabla Markdown no admite bloques de codigo dentro de una celda: si los
    # hay (ejemplos largos en columnas "Example"), se pasa a formato lineal para
    # no perderlos.
    if any(CODE_MARK_RE.search(cell) for _, cells in rows for cell in cells):
        return _html_table_to_linear(rows)
    cleaned = [(header, [_clean_cell(c) for c in cells]) for header, cells in rows]
    width = max(len(cells) for _, cells in cleaned)
    header_row, body = (cleaned[0][1], cleaned[1:]) if cleaned[0][0] else ([""] * width, cleaned)
    lines = [_md_row(header_row, width), _md_row(["---"] * width, width)]
    lines += [_md_row(cells, width) for _, cells in body]
    return "\n".join(lines)


def _html_table_to_linear(rows: list[tuple[bool, list[str]]]) -> str:
    """Renderiza la tabla como lista `campo: valor`, con el codigo aparte."""
    header = [_clean_cell(c) for c in rows[0][1]] if rows[0][0] else []
    body = rows[1:] if rows[0][0] else rows
    chunks: list[str] = []
    for _, cells in body:
        lines: list[str] = []
        for idx, cell in enumerate(cells):
            name = header[idx] if idx < len(header) else ""
            texts = [p for kind, p in _cell_parts(cell) if kind == "text"]
            codes = [p for kind, p in _cell_parts(cell) if kind == "code"]
            value = " ".join(texts)
            if name and value:
                lines.append(f"- **{name}**: {value}")
            elif value:
                lines.append(f"- {value}")
            elif name and codes:
                lines.append(f"- **{name}**:")
            for marker in codes:
                lines += ["", marker, ""]
        if lines:
            chunks.append("\n".join(lines))
    return "\n\n".join(chunks)


def _cell_parts(raw: str) -> list[tuple[str, str]]:
    """Trocea una celda en texto y marcadores de bloque de codigo."""
    text = re.sub(r"(?is)<br\s*/?>", "\n", raw)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    parts: list[tuple[str, str]] = []
    pos = 0
    for match in CODE_MARK_RE.finditer(text):
        before = text[pos : match.start()]
        if before.strip():
            parts.append(("text", " ".join(before.split())))
        parts.append(("code", match.group(0)))
        pos = match.end()
    tail = text[pos:]
    if tail.strip():
        parts.append(("text", " ".join(tail.split())))
    return parts


def _md_row(cells: list[str], width: int) -> str:
    padded = list(cells) + [""] * (width - len(cells))
    return "| " + " | ".join(padded) + " |"


def _clean_cell(raw: str) -> str:
    text = re.sub(r"(?is)<br\s*/?>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    text = text.replace("\\{", "{").replace("\\}", "}").replace("|", "\\|")
    return " ".join(text.split())


# ---------------------------------------------------------------------------
# Transformacion JSX
# ---------------------------------------------------------------------------


@dataclass
class _Frame:
    name: str
    dedent: int = 0
    pending: bool = False
    open_indent: int = 0


class JsxRenderer:
    """Recorre el MDX y emite Markdown plano.

    Reglas:
      * componentes de `DROP_COMPONENTS` y autocerrados desconocidos -> fuera,
        con hijos incluidos;
      * componentes con manejador propio (`APILink`, `TabItem`...) -> texto;
      * el resto (contenedores, HTML estructural) -> se desenvuelve.

    Al desenvolver un contenedor se corrige la indentacion del contenido: en
    Docusaurus el interior de `<Tabs>`/`<div>` viene sangrado 2-6 espacios, y
    sin re-indentar Markdown lo leeria como bloque de codigo indentado.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self.out: list[str] = []
        self.stack: list[_Frame] = []
        self.pending: list[_Frame] = []
        self.dedent = 0
        self.drop_depth = 0
        self.drop_name = ""
        self.at_line_start = True
        self._ws = ""

    # -- emision ---------------------------------------------------------
    def _emit(self, chunk: str, measure: bool = True) -> None:
        """Emite texto. `measure=False` para texto generado por el script
        (etiquetas de pestaña, titulos sinteticos): no lleva indentacion de
        origen, asi que no debe servir de referencia para desindentar."""
        if not chunk or self.drop_depth:
            return
        parts = chunk.split("\n")
        for idx, part in enumerate(parts):
            if idx:
                self._ws = ""
                self.out.append("\n")
                self.at_line_start = True
            if not part:
                continue
            if self.at_line_start:
                stripped = part.lstrip(" \t")
                if not stripped:
                    self._ws += part  # espacios sueltos: puede seguir contenido
                    continue
                part = self._ws + part
                self._ws = ""
                if measure:
                    indent = len(part) - len(part.lstrip(" \t"))
                    if self.pending:
                        self._resolve_pending(indent)
                    if self.dedent:
                        part = part[min(self.dedent, indent) :]
                self.at_line_start = False
            self.out.append(part)

    def _resolve_pending(self, indent: int) -> None:
        """Fija cuanto hay que desindentar segun la primera linea con contenido."""
        outer = self.pending[0]
        increment = max(0, indent - outer.open_indent)
        outer.dedent = increment
        self.dedent += increment
        self.pending.clear()

    # -- recorrido -------------------------------------------------------
    def render(self) -> str:
        text = self.text
        i = 0
        while i < len(text):
            pos = text.find("<", i)
            if pos == -1:
                self._emit(text[i:])
                break
            self._emit(text[i:pos])
            tag = scan_tag(text, pos)
            if not tag:
                self._emit("<")
                i = pos + 1
                continue
            self._handle(tag)
            i = tag.end
        while self.stack:
            self._pop(self.stack[-1].name)
        return "".join(self.out)

    def _handle(self, tag: Tag) -> None:
        name = tag.name
        lower = name.lower()

        if self.drop_depth:  # dentro de un subarbol descartado
            if tag.name == self.drop_name and not tag.self_closing:
                self.drop_depth += -1 if tag.closing else 1
                if self.drop_depth == 0:
                    self.drop_name = ""
            return

        if tag.closing:
            self._pop(name)
            return

        if lower == "br":
            self._emit("\n")
            return
        if lower == "hr":
            self._emit("\n\n---\n\n")
            return

        handler = getattr(self, f"_tag_{name}", None)
        if handler is not None:
            handler(tag)
            return

        if name in DROP_COMPONENTS or lower in DROP_HTML:
            self._drop(tag)
            return

        # Autocerrado desconocido y capitalizado: es una inclusion o un widget
        # que no podemos resolver -> se descarta.
        if tag.self_closing:
            if name[0].isupper() and name not in UNWRAP_COMPONENTS:
                return
            return

        self._unwrap(tag)

    def _drop(self, tag: Tag) -> None:
        if tag.self_closing:
            return
        self.drop_depth = 1
        self.drop_name = tag.name

    def _unwrap(self, tag: Tag, prefix: str = "") -> None:
        if prefix:
            self._emit(prefix, measure=False)
        frame = _Frame(tag.name, open_indent=self._source_indent(tag))
        if self._alone_on_line(tag):
            frame.pending = True
            self.pending.append(frame)
        self.stack.append(frame)

    def _pop(self, name: str) -> None:
        for idx in range(len(self.stack) - 1, -1, -1):
            if self.stack[idx].name == name:
                for frame in self.stack[idx:]:
                    if frame in self.pending:
                        self.pending.remove(frame)
                    self.dedent -= frame.dedent
                del self.stack[idx:]
                return

    # -- utilidades de posicion -----------------------------------------
    def _source_indent(self, tag: Tag) -> int:
        line_start = self.text.rfind("\n", 0, tag.start) + 1
        prefix = self.text[line_start : tag.start]
        return len(prefix) if not prefix.strip() else 0

    def _alone_on_line(self, tag: Tag) -> bool:
        line_start = self.text.rfind("\n", 0, tag.start) + 1
        if self.text[line_start : tag.start].strip():
            return False
        rest = self.text[tag.end :]
        newline = rest.find("\n")
        tail = rest if newline == -1 else rest[:newline]
        return not tail.strip()

    # -- manejadores especificos ----------------------------------------
    def _tag_APILink(self, tag: Tag) -> None:
        """`<APILink fn="mlflow.x" />` -> `mlflow.x` en formato codigo."""
        attrs = parse_attrs(tag.attrs_raw)
        target = attrs.get("fn") or attrs.get("obj") or attrs.get("to") or ""
        if tag.self_closing:
            if target:
                self._emit(f"`{target}`")
            return
        self.stack.append(_Frame(tag.name))  # con hijos: nos quedamos su texto

    def _tag_StepHeader(self, tag: Tag) -> None:
        """Cabecera de paso numerado -> encabezado Markdown de nivel 3."""
        attrs = parse_attrs(tag.attrs_raw)
        number = attrs.get("number", "").strip("{} ")
        title = attrs.get("title", "").strip()
        if title:
            label = f"{number}. {title}" if number else title
            self._emit(f"\n\n### {label}\n\n", measure=False)
        if not tag.self_closing:
            self.stack.append(_Frame(tag.name))

    def _tag_TabItem(self, tag: Tag) -> None:
        """Conserva la etiqueta de la pestaña: distingue el ejemplo Python del JS."""
        attrs = parse_attrs(tag.attrs_raw)
        label = attrs.get("label") or attrs.get("value") or ""
        prefix = f"\n\n**{label}**\n\n" if label else ""
        self._unwrap(tag, prefix)

    def _tag_CollapsibleSection(self, tag: Tag) -> None:
        attrs = parse_attrs(tag.attrs_raw)
        title = attrs.get("title", "").strip()
        self._unwrap(tag, f"\n\n**{title}**\n\n" if title else "")

    def _tag_summary(self, tag: Tag) -> None:
        """El resumen de un `<details>` hace las veces de titulo de la seccion."""
        self._unwrap(tag, "\n\n")


# ---------------------------------------------------------------------------
# Limpieza final
# ---------------------------------------------------------------------------


def normalize_admonitions(text: str) -> str:
    """`:::warning Titulo` ... `:::` -> una linea en negrita + el contenido."""
    out: list[str] = []
    depth = 0
    for line in text.split("\n"):
        match = ADMONITION_OPEN_RE.match(line)
        if match:
            depth += 1
            kind, title = match.group(1), match.group(2).strip()
            out.append(f"**{title or ADMONITION_LABELS[kind]}**")
            continue
        if depth and ADMONITION_CLOSE_RE.match(line):
            depth -= 1
            out.append("")
            continue
        out.append(line)
    return "\n".join(out)


def drop_empty_sections(text: str) -> str:
    """Elimina encabezados que se quedaron sin contenido.

    Al quitar las rejillas de tarjetas, secciones como `## Learn More` quedan
    vacias. Se borra un encabezado solo si lo que sigue es otro encabezado del
    mismo nivel o superior (o el final del documento); los encabezados padre,
    seguidos de subsecciones, se conservan.
    """
    lines = text.split("\n")
    keep = [True] * len(lines)
    for idx, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+\S", line)
        if not match:
            continue
        level = len(match.group(1))
        for nxt in range(idx + 1, len(lines)):
            if not keep[nxt] or not lines[nxt].strip():
                continue
            following = re.match(r"^(#{1,6})\s+\S", lines[nxt])
            if following and len(following.group(1)) <= level:
                keep[idx] = False
            break
        else:
            keep[idx] = False  # encabezado final sin contenido
    return "\n".join(line for line, ok in zip(lines, keep) if ok)


def drop_thematic_breaks(text: str) -> str:
    """Quita las lineas separadoras sueltas (`---`, `***`, `___`).

    Son decoracion: no dicen nada que se pueda recuperar y, al trocear el
    documento por encabezados, una separadora justo delante de un encabezado se
    queda como el cuerpo entero de la seccion anterior y acaba siendo un chunk
    de un solo token.

    Se respeta el encabezado setext (`Titulo` y debajo `---`), que se reconoce
    porque la linea anterior no esta en blanco.
    """
    lines = text.split("\n")
    keep = []
    for idx, line in enumerate(lines):
        if THEMATIC_BREAK_RE.fullmatch(line) and (idx == 0 or not lines[idx - 1].strip()):
            continue
        keep.append(line)
    return "\n".join(keep)


def tidy(text: str) -> str:
    """Deja el Markdown presentable: sin restos de HTML vacio ni huecos.

    Se ejecuta con el codigo todavia oculto tras los marcadores: asi ni el
    desescapado MDX ni el colapso de lineas en blanco pueden tocar el interior
    de un bloque de codigo.
    """
    text = EMPTY_HTML_RE.sub("", text)
    text = drop_thematic_breaks(text)
    text = re.sub(r"\\([{}<>])", r"\1", text)  # escapes MDX
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = drop_empty_sections(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Pipeline por documento
# ---------------------------------------------------------------------------


@dataclass
class Document:
    doc_id: str
    path: str
    output_path: str
    title: str
    text: str
    n_chars: int
    n_words: int
    n_code_blocks: int
    headings: list[dict[str, Any]]
    metadata: dict[str, Any]
    content_sha1: str

    def to_record(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "path": self.path,
            "output_path": self.output_path,
            "title": self.title,
            "text": self.text,
            "n_chars": self.n_chars,
            "n_words": self.n_words,
            "n_code_blocks": self.n_code_blocks,
            "headings": self.headings,
            "content_sha1": self.content_sha1,
            "metadata": self.metadata,
        }


def clean_mdx(source: str) -> tuple[str, dict[str, Any], int, list[dict[str, Any]]]:
    """Devuelve (markdown limpio, frontmatter, bloques de codigo, encabezados)."""
    source = source.replace("\r\n", "\n").replace("\r", "\n")
    raw_front, body = split_frontmatter(source)
    front = parse_frontmatter(raw_front)

    vault = CodeVault()
    body = vault.hide_fenced(body)
    body = vault.hide_inline(body)

    body = MDX_COMMENT_RE.sub("", body)
    body = HTML_COMMENT_RE.sub("", body)
    body = ESM_IMPORT_RE.sub("", body)
    body = ESM_EXPORT_RE.sub("", body)

    body = convert_html_tables(body)
    body = JsxRenderer(body).render()
    body = normalize_admonitions(body)
    body = tidy(body)

    # Los encabezados se extraen antes de restaurar el codigo: si no, los
    # comentarios `# ...` de los ejemplos en Python pasarian por titulos.
    headings = [
        {"level": len(m.group(1)), "text": m.group(2).strip()} for m in HEADING_RE.finditer(body)
    ]

    body = vault.restore(body).strip()
    return (body + "\n" if body else ""), front, vault.count_blocks(), headings


def build_document(path: Path, raw_dir: Path) -> Document:
    text, front, n_code, headings = clean_mdx(path.read_text(encoding="utf-8", errors="replace"))
    rel = path.relative_to(raw_dir)
    doc_id = rel.with_suffix("").as_posix()
    out_rel = rel.with_suffix(".md")

    title = str(front.get("title") or "").strip()
    if not title:
        title = next((h["text"] for h in headings if h["level"] == 1), "") or path.stem

    keywords = front.get("keywords") or front.get("tags") or []
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]

    description = str(front.get("description") or "").strip()
    metadata = {
        "source": "mlflow-docs",
        "title": title,
        "description": description,
        "keywords": list(keywords),
        "sidebar_label": str(front.get("sidebar_label") or "").strip(),
        "section": rel.parent.as_posix(),
        "has_frontmatter": bool(front),
        "frontmatter_only": False,
        "frontmatter": front,
    }

    # Paginas cuyo cuerpo entero era un componente (las fichas de integracion
    # de `tracing/integrations/listing/`): sin esto se quedarian en blanco y
    # perderiamos la senal de que MLflow soporta ese proveedor.
    if not text.strip() and (title or description):
        text = f"# {title}\n\n{description}\n".replace("\n\n\n", "\n\n")
        metadata["frontmatter_only"] = True
        headings = [{"level": 1, "text": title}] if title else []
    return Document(
        doc_id=doc_id,
        path=rel.as_posix(),
        output_path=out_rel.as_posix(),
        title=title,
        text=text,
        n_chars=len(text),
        n_words=len(text.split()),
        n_code_blocks=n_code,
        headings=headings,
        metadata=metadata,
        content_sha1=hashlib.sha1(text.encode("utf-8")).hexdigest(),
    )


def render_output_md(doc: Document) -> str:
    """Markdown limpio con una cabecera YAML minima con los metadatos clave."""
    lines = ["---", f"doc_id: {json.dumps(doc.doc_id, ensure_ascii=False)}"]
    lines.append(f"source_path: {json.dumps(doc.path, ensure_ascii=False)}")
    lines.append(f"title: {json.dumps(doc.title, ensure_ascii=False)}")
    if doc.metadata["description"]:
        lines.append(f"description: {json.dumps(doc.metadata['description'], ensure_ascii=False)}")
    if doc.metadata["keywords"]:
        lines.append(f"keywords: {json.dumps(doc.metadata['keywords'], ensure_ascii=False)}")
    lines += ["---", "", doc.text]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def iter_sources(raw_dir: Path, patterns: Iterable[str]) -> Iterator[Path]:
    seen: set[Path] = set()
    for pattern in patterns:
        for path in sorted(raw_dir.rglob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def summarize(docs: list[Document], skipped: list[tuple[str, str]]) -> dict[str, Any]:
    sizes = sorted(d.n_chars for d in docs)
    stats: dict[str, Any] = {
        "n_documents": len(docs),
        "n_skipped": len(skipped),
        "skipped": skipped[:50],
        "total_chars": sum(sizes),
        "n_code_blocks": sum(d.n_code_blocks for d in docs),
        "with_frontmatter": sum(1 for d in docs if d.metadata["has_frontmatter"]),
        "trivial_lt_500_chars": sum(1 for s in sizes if s < 500),
        "large_gt_20000_chars": sum(1 for s in sizes if s > 20000),
    }
    if sizes:
        stats["chars"] = {
            "min": sizes[0],
            "p25": sizes[len(sizes) // 4],
            "median": int(statistics.median(sizes)),
            "p75": sizes[3 * len(sizes) // 4],
            "p95": sizes[int(0.95 * (len(sizes) - 1))],
            "max": sizes[-1],
            "mean": round(statistics.mean(sizes), 1),
        }
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR, help="carpeta de entrada")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="carpeta de salida")
    parser.add_argument("--pattern", action="append", default=None, help="glob de entrada (repetible; por defecto *.mdx)")
    parser.add_argument("--jsonl", default="documents.jsonl", help="nombre del jsonl de salida")
    parser.add_argument("--min-chars", type=int, default=1, help="descarta documentos con menos caracteres limpios")
    parser.add_argument("--limit", type=int, default=0, help="procesa solo los N primeros (pruebas)")
    parser.add_argument("--no-md", action="store_true", help="no escribe los .md, solo el jsonl")
    parser.add_argument("--dry-run", action="store_true", help="no escribe nada, solo informa")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    raw_dir: Path = args.raw_dir.resolve()
    out_dir: Path = args.out_dir.resolve()
    if not raw_dir.is_dir():
        parser.error(f"no existe la carpeta de entrada: {raw_dir}")

    patterns = args.pattern or ["*.mdx"]
    docs: list[Document] = []
    skipped: list[tuple[str, str]] = []

    for count, path in enumerate(iter_sources(raw_dir, patterns), start=1):
        if args.limit and count > args.limit:
            break
        rel = path.relative_to(raw_dir).as_posix()
        try:
            doc = build_document(path, raw_dir)
        except Exception as exc:  # un fichero raro no debe tumbar la pasada
            skipped.append((rel, f"error: {exc}"))
            print(f"  ! {rel}: {exc}", file=sys.stderr)
            continue
        if doc.n_chars < args.min_chars:
            skipped.append((rel, "vacio tras la limpieza"))
            continue
        docs.append(doc)
        if args.verbose:
            print(f"  + {rel} -> {doc.n_chars} chars, {doc.n_code_blocks} bloques de codigo")

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        if not args.no_md:
            for doc in docs:
                target = out_dir / doc.output_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(render_output_md(doc), encoding="utf-8")
        jsonl = out_dir / args.jsonl
        with jsonl.open("w", encoding="utf-8") as handle:
            for doc in docs:
                handle.write(json.dumps(doc.to_record(), ensure_ascii=False) + "\n")

    stats = summarize(docs, skipped)
    if not args.dry_run:
        (out_dir / "preprocess_report.json").write_text(
            json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"\nDocumentos procesados : {stats['n_documents']}")
    print(f"Descartados           : {stats['n_skipped']}")
    print(f"Con frontmatter       : {stats['with_frontmatter']}")
    print(f"Bloques de codigo     : {stats['n_code_blocks']}")
    if "chars" in stats:
        c = stats["chars"]
        print(f"Longitud (caracteres) : min {c['min']} | p25 {c['p25']} | mediana {c['median']} "
              f"| p75 {c['p75']} | p95 {c['p95']} | max {c['max']}")
    print(f"Triviales (<500 chars): {stats['trivial_lt_500_chars']}")
    print(f"Enormes (>20k chars)  : {stats['large_gt_20000_chars']}")
    if not args.dry_run:
        print(f"\nSalida: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
