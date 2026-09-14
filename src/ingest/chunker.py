"""
Chunker para el corpus de documentacion.

Lee documents.jsonl (la salida de preprocess_mdx.py) y escribe chunks.jsonl.
La configuracion va en un dict.

Uso:
    python chunker.py data/processed/documents.jsonl data/processed/chunks.jsonl
"""     

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, asdict, field

from transformers import AutoTokenizer


# --------------------------------------------------------------------------
# Configuracion
# --------------------------------------------------------------------------

CONFIG = {
    "tokenizer": "intfloat/multilingual-e5-base",  # el del modelo de embeddings
    "max_tokens": 512,
    "min_tokens": 200,       # por debajo de esto, se fusiona
    "overlap_tokens": 64,   # solape al subdividir secciones largas
}


# --------------------------------------------------------------------------
# Estructuras
# --------------------------------------------------------------------------

@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    path: str
    breadcrumb: str
    text: str          # contenido limpio, sin breadcrumb
    embed_text: str    # lo que se embebe: breadcrumb + text
    n_tokens: int
    char_start: int    # posicion en el texto del documento original
    char_end: int


@dataclass
class Section:
    """Una seccion del documento, delimitada por encabezados."""
    breadcrumb: str
    text: str
    char_start: int
    char_end: int
    n_tokens: int = 0


# --------------------------------------------------------------------------
# Troceado en secciones por encabezados
# --------------------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*)$", re.MULTILINE)
# ^, Busca estrictamente en el inicio de la línea.
# (#{1,6}), (Grupo 1): Captura un bloque que tenga entre 1 y 6 almohadillas. Esto es clave porque le indica al script el nivel exacto del título (H1, H2, H3...).
# [ \t]+: Exige uno o mas espacios o tabuladores en la MISMA linea separando las
#         almohadillas del texto (con \s+ una almohadilla suelta se comia el salto
#         de linea y convertia la linea siguiente en titulo).
# (.*) (Grupo 2): Captura todo el texto que viene después de los espacios. Este es el nombre real del título.
# $: Marca el final de la línea.

# Apertura de un bloque de codigo cercado: tres o mas backticks, o tres o mas
# tildes, con un lenguaje opcional detras.
FENCE_RE = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})(?P<info>.*)$")


def find_code_spans(text: str) -> list[tuple[int, int]]:
    """
    Posiciones (inicio, fin) de cada bloque de codigo del texto.

    El cercado se cierra con el mismo caracter y al menos tantos como la
    apertura; un bloque que se queda sin cerrar llega hasta el final del texto.
    """
    spans: list[tuple[int, int]] = []
    apertura: tuple[int, str, int] | None = None
    pos = 0

    for linea in text.split("\n"):
        fin_linea = pos + len(linea)
        desnuda = linea.strip()
        if apertura is None:
            m = FENCE_RE.match(linea)
            if m:
                cercado = m.group("fence")
                apertura = (pos, cercado[0], len(cercado))
        else:
            inicio, caracter, largo = apertura
            if desnuda and set(desnuda) == {caracter} and len(desnuda) >= largo:
                spans.append((inicio, fin_linea))
                apertura = None
        pos = fin_linea + 1  # el +1 es el salto de linea

    if apertura is not None:  # bloque sin cerrar al final del fichero
        spans.append((apertura[0], len(text)))
    return spans


def find_headings(text: str) -> list[re.Match]:
    """
    Encabezados markdown que estan FUERA de los bloques de codigo.

    Sin este filtro, los comentarios de Python (`# Load the model`), las lineas
    magicas de notebook (`%%writefile`, precedidas de #) y cualquier almohadilla
    dentro de un ejemplo se tomaban por titulos de seccion, partian el documento
    donde no tocaba y ensuciaban el breadcrumb.
    """
    spans = find_code_spans(text)
    return [
        m for m in HEADING_RE.finditer(text)
        if not any(inicio <= m.start() < fin for inicio, fin in spans)
    ]


def split_into_sections(text: str, title: str) -> list[Section]:
    """
    Parte el texto por encabezados markdown, manteniendo una pila con la
    jerarquia para construir el breadcrumb de cada seccion. El breadcrumb es la ruta
    que tiene una parte del texto dentro de un documento en concreto.
    """
    matches = find_headings(text) # Una lista con información de la estructura de las secciones, y donde empieza y donde acaba
    sections = []
    stack = [title]  # nivel 0: el titulo del documento

    # Texto antes del primer encabezado (introduccion)
    first_start = matches[0].start() if matches else len(text)
    intro = text[:first_start].strip()
    if intro:
        sections.append(Section(
            breadcrumb=title,
            text=intro,
            char_start=0,
            char_end=first_start,
        ))

    for i, m in enumerate(matches):
        level = len(m.group(1))
        heading = m.group(2).strip()

        # Ajusta la pila al nivel de este encabezado
        stack = stack[:level]
        while len(stack) < level:
            stack.append("")
        stack.append(heading)

        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()

        if not body:
            continue

        breadcrumb = " > ".join(p for p in stack if p)
        sections.append(Section(
            breadcrumb=breadcrumb,
            text=body,
            char_start=body_start,
            char_end=body_end,
        ))

    return sections


# --------------------------------------------------------------------------
# Subdivision de secciones largas
# --------------------------------------------------------------------------

def split_preserving_code(text: str) -> list[str]:
    """
    Parte el texto en bloques, tratando cada bloque de codigo como una unidad
    indivisible. Usa el mismo escaneo de cercados que la deteccion de
    encabezados, asi que respeta tambien los bloques de ~~~ y los de cuatro o
    mas backticks.
    """
    blocks: list[str] = []
    pos = 0
    for inicio, fin in find_code_spans(text):
        prosa = text[pos:inicio]
        blocks.extend(p for p in prosa.split("\n\n") if p.strip())
        codigo = text[inicio:fin].strip("\n")
        if codigo.strip():
            blocks.append(codigo)        # añade el código sin cortarlo
        pos = fin
    blocks.extend(p for p in text[pos:].split("\n\n") if p.strip())
    return blocks


def pack_blocks(blocks, tokenizer, max_tokens, overlap_tokens, min_tokens=0):
    """
    Agrupa bloques hasta llegar a max_tokens. Al cerrar un grupo, arrastra
    los ultimos bloques como solape con el siguiente.

    Si el ultimo grupo se queda por debajo de min_tokens, se reparte con el
    anterior: trocear una seccion larga dejaba colas de unas pocas decenas de
    tokens, que como chunk no valen para nada. Al repartir se pierde el solape
    entre esos dos ultimos grupos, pero el texto sigue siendo continuo y ninguno
    se pasa del maximo.
    """
    cache: dict[str, int] = {}

    def n_tokens(block):
        if block not in cache:
            cache[block] = len(tokenizer.encode(block, add_special_tokens=False))
        return cache[block]

    grupos: list[list[str]] = []
    solapes: list[int] = []          # cuantos bloques iniciales de cada grupo vienen del solape
    current, current_tokens, current_solape = [], 0, 0

    for block in blocks:
        n = n_tokens(block)

        # Un solo bloque ya supera el limite: se emite tal cual
        if n > max_tokens:
            print(f"AVISO: Bloque gigante detectado ({n} tokens).")
            if current:
                grupos.append(current)
                solapes.append(current_solape)
                current, current_tokens, current_solape = [], 0, 0
            grupos.append([block])
            solapes.append(0)
            continue

        if current_tokens + n > max_tokens and current:
            grupos.append(current)
            solapes.append(current_solape)
            # solape hacia atras
            tail, tail_tokens = [], 0
            for b in reversed(current):
                bn = n_tokens(b)
                if tail_tokens + bn > overlap_tokens:
                    break
                tail.insert(0, b)
                tail_tokens += bn
            current, current_tokens, current_solape = tail, tail_tokens, len(tail)

        current.append(block)
        current_tokens += n

    if current:
        grupos.append(current)
        solapes.append(current_solape)

    if min_tokens and len(grupos) >= 2 and sum(n_tokens(b) for b in grupos[-1]) < min_tokens:
        # Los dos ultimos grupos, seguidos y sin el solape duplicado.
        par = grupos[-2] + grupos[-1][solapes[-1]:]
        if sum(n_tokens(b) for b in par) <= max_tokens:
            grupos[-2:] = [par]
            solapes[-2:] = [solapes[-2]]
        else:
            # El corte mas tardio que deje los dos lados entre el minimo y el
            # maximo. Si no hay ninguno, se deja como estaba y de la cola ya se
            # encarga el filtro de escritura.
            for corte in range(len(par) - 1, 0, -1):
                izq, der = par[:corte], par[corte:]
                t_izq = sum(n_tokens(b) for b in izq)
                t_der = sum(n_tokens(b) for b in der)
                if min_tokens <= t_izq and t_izq <= max_tokens and min_tokens <= t_der <= max_tokens:
                    grupos[-2:] = [izq, der]
                    solapes[-2:] = [solapes[-2], 0]
                    break

    return ["\n\n".join(g) for g in grupos]


# --------------------------------------------------------------------------
# Pipeline por documento
# --------------------------------------------------------------------------

def slugify(s: str) -> str:  # Para que los chunk_id tengan un formato unificado, pasado a texto limpio
    s = re.sub(r"[^\w\s-]", "", s.lower())
    return re.sub(r"[\s_]+", "-", s).strip("-")[:60] or "seccion"


def merge_sections(a: Section, b: Section) -> Section:
    """Une dos secciones consecutivas conservando el breadcrumb de la primera."""
    return Section(
        breadcrumb=a.breadcrumb,
        text=a.text + "\n\n" + b.text,
        char_start=a.char_start,
        char_end=b.char_end,
        n_tokens=a.n_tokens + b.n_tokens,
    )


def chunk_document(doc: dict, tokenizer, cfg: dict) -> list[Chunk]:
    sections = split_into_sections(doc["text"], doc["title"])

    for s in sections:
        s.n_tokens = len(tokenizer.encode(s.text, add_special_tokens=False))

    # Fusiona secciones cortas con las siguientes. El acumulador se sigue
    # arrastrando mientras no llegue al minimo, asi que una seccion corta que al
    # fusionarse sigue siendo corta se vuelve a fusionar con la siguiente.
    merged, buffer = [], None
    for s in sections:
        buffer = s if buffer is None else merge_sections(buffer, s)
        if buffer.n_tokens >= cfg["min_tokens"]:
            merged.append(buffer)
            buffer = None
    if buffer is not None:
        # Cola del documento: se pega a la ultima seccion, o se queda sola si el
        # documento entero no llega al minimo.
        if merged:
            merged[-1] = merge_sections(merged[-1], buffer)
        else:
            merged.append(buffer)

    chunks = []
    n_global = 0 #contador global para evitar duplicados 
    for s in merged:
        if s.n_tokens <= cfg["max_tokens"]:
            pieces = [s.text]
        else:
            blocks = split_preserving_code(s.text)
            pieces = pack_blocks(
                blocks, tokenizer, cfg["max_tokens"], cfg["overlap_tokens"],
                cfg["min_tokens"],
            )

        base = slugify(s.breadcrumb.split(" > ")[-1])
        for i, piece in enumerate(pieces):
            embed_text = f"{s.breadcrumb}\n\n{piece}" 
            chunks.append(Chunk(
                chunk_id=f"{doc['doc_id']}#{n_global:04d}-{base}",
                doc_id=doc["doc_id"],
                path=doc["path"],
                breadcrumb=s.breadcrumb,
                text=piece,
                embed_text=embed_text,
                n_tokens=len(tokenizer.encode(piece, add_special_tokens=False)),
                char_start=s.char_start,
                char_end=s.char_end,
            ))
            n_global += 1

    return chunks


def main(in_path: str, out_path: str, cfg: dict = CONFIG):
    tokenizer = AutoTokenizer.from_pretrained(cfg["tokenizer"])

    n_docs = 0
    all_chunks = []
    with open(in_path, encoding="utf-8") as f:
        for line in f:
            doc = json.loads(line)
            all_chunks.extend(chunk_document(doc, tokenizer, cfg))
            n_docs += 1

    # Red de seguridad: un chunk por debajo del minimo se descarta solo si su
    # documento produce algun otro. Si es el unico que produce, se conserva tal
    # cual: descartarlo dejaba el documento entero fuera del indice, y un
    # documento que no esta indexado no se puede recuperar por corto que sea
    # (las fichas de integracion, por ejemplo, son contenido legitimo).
    chunks_por_doc = Counter(c.doc_id for c in all_chunks)

    def se_conserva(c: Chunk) -> bool:
        return c.n_tokens >= cfg["min_tokens"] or chunks_por_doc[c.doc_id] == 1

    kept = [c for c in all_chunks if se_conserva(c)]
    dropped = [c for c in all_chunks if not se_conserva(c)]
    unicos_cortos = [c for c in kept if c.n_tokens < cfg["min_tokens"]]
    docs_vacios = sorted({c.doc_id for c in dropped} - {c.doc_id for c in kept})

    with open(out_path, "w", encoding="utf-8") as f:
        for c in kept:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")

    # Comprobaciones de cordura
    tks = sorted(c.n_tokens for c in kept)
    ids = [c.chunk_id for c in kept]
    print(f"documentos      : {n_docs}")
    print(f"chunks          : {len(kept)}")
    print(f"chunks/doc      : {len(kept) / n_docs:.1f}")
    print(f"tokens min/med/max: {tks[0]} / {tks[len(tks) // 2]} / {tks[-1]}")
    print(f"por encima del max: {sum(1 for t in tks if t > cfg['max_tokens'])}")
    print(f"ids duplicados  : {len(ids) - len(set(ids))}")
    print(f"descartados (<{cfg['min_tokens']} tokens): {len(dropped)}")
    print(f"documentos sin ningun chunk: {len(docs_vacios)}")
    print(f"unicos de su documento conservados por debajo del minimo: {len(unicos_cortos)}")

    if unicos_cortos:
        cortos = sorted(c.n_tokens for c in unicos_cortos)
        print(f"  tokens min/mediana/max: {cortos[0]} / {cortos[len(cortos) // 2]} / {cortos[-1]}")
        paso = max(1, cfg["min_tokens"] // 4)
        for desde in range(0, cfg["min_tokens"], paso):
            hasta = min(desde + paso, cfg["min_tokens"]) - 1
            n = sum(1 for t in cortos if desde <= t <= hasta)
            if n:
                print(f"  {desde:>4}-{hasta:<4} tokens: {n}")

    print("\nlos 10 chunks con menos tokens:")
    for c in sorted(kept, key=lambda c: c.n_tokens)[:10]:
        print(f"  {c.n_tokens:>4} tk | {c.breadcrumb}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])