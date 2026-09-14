"""
Generacion del set de evaluacion a partir de los chunks.

Muestrea chunks (uno por documento), pide a Gemini una pregunta y un ancla
literal por cada uno, verifica que el ancla exista de verdad en el chunk y
escribe los casos que pasan el filtro.

La salida es un BORRADOR: hay que revisarla a mano antes de usarla.

Uso:
    python -m src.evaluate.generar_eval_set --n 5    # prueba
    python -m src.evaluate.generar_eval_set --n 60   # tanda completa
"""

import argparse
import json
import os
import random
import time
from collections import defaultdict

from dotenv import load_dotenv
from google import genai

CHUNKS_PATH = "data/processed/chunks.jsonl"
OUT_PATH = "eval/eval_set_borrador.jsonl"
DESCARTES_PATH = "eval/descartes.jsonl"
SEED = 42
MODELO = "gemini-3.5-flash-lite"


PROMPT = """Eres un ingeniero que prepara un conjunto de evaluacion para un
sistema de busqueda sobre la documentacion de MLflow.

Seccion: {breadcrumb}

Texto:
{texto}

Escribe UNA pregunta que un usuario real haria y cuya respuesta este contenida
en ese texto.

Requisitos:
- La pregunta debe poder responderse solo con ese texto.
- No copies frases del texto en la pregunta.
- No uses expresiones como "segun el texto" o "en esta seccion".
- La respuesta debe ser concreta y verificable, no una opinion.

Responde SOLO con este JSON, sin ningun otro texto ni bloques de codigo:
{{"pregunta": "...", "respuesta": "...", "ancla": "..."}}

El campo "ancla" debe ser una frase copiada LITERALMENTE del texto, palabra por
palabra, que contenga la respuesta. No la reformules ni la abrevies."""


# --------------------------------------------------------------------------
# Normalización de texto
# --------------------------------------------------------------------------
import re

def norm(s: str) -> str:
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)   # enlaces -> solo el texto
    s = re.sub(r"[*_`]+", "", s)                      # negrita, cursiva, codigo
    s = re.sub(r"\s+", " ", s)                        # espacios y saltos
    return s.strip().lower()

# --------------------------------------------------------------------------
# Muestreo
# --------------------------------------------------------------------------

def muestrear(path: str, n: int, seed: int = SEED) -> list[dict]:
    """Un chunk de cada uno de n documentos distintos, para cubrir el corpus."""
    por_doc = defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for linea in f:
            c = json.loads(linea)
            por_doc[c["doc_id"]].append(c)

    rng = random.Random(seed)
    docs = rng.sample(sorted(por_doc), min(n, len(por_doc)))
    return [rng.choice(por_doc[d]) for d in docs]


# --------------------------------------------------------------------------
# Llamada al LLM
# --------------------------------------------------------------------------

def parsear_json(texto: str) -> dict | None:
    """El modelo a veces envuelve el JSON en ```json ... ```."""
    limpio = texto.strip()
    if limpio.startswith("```"):
        limpio = limpio.split("```")[1]
        if limpio.startswith("json"):
            limpio = limpio[4:]
    try:
        return json.loads(limpio.strip())
    except json.JSONDecodeError:
        return None


def generar_caso(client, chunk: dict) -> tuple[dict | None, str]:
    """Devuelve (caso, motivo_descarte). Si caso es None, no paso el filtro."""
    prompt = PROMPT.format(breadcrumb=chunk["breadcrumb"], texto=chunk["text"])

    try:
        resp = client.models.generate_content(model=MODELO, contents=prompt)
    except Exception as e:
        return None, f"error_api: {e}"

    datos = parsear_json(resp.text)
    if datos is None:
        return None, "json_invalido"

    if not all(k in datos for k in ("pregunta", "respuesta", "ancla")):
        return None, "faltan_campos"

    ancla = datos["ancla"].strip()
    if not ancla:
        return None, "ancla_vacia"
    
    texto_norm = norm(chunk["text"])
    ancla_norm = norm(ancla)

    # El ancla tiene que existir LITERALMENTE en el chunk
    if ancla_norm not in texto_norm:
        return None, f"ancla_no_literal|{ancla[:120]}"

    # Y tiene que ser univoca dentro del documento
    if texto_norm.count(ancla_norm) > 1:
        return None, "ancla_ambigua"

    return {
        "pregunta": datos["pregunta"].strip(),
        "respuesta": datos["respuesta"].strip(),
        "ancla": ancla,
        "doc_id": chunk["doc_id"],
        "chunk_id_origen": chunk["chunk_id"],   # solo para revisar, no para evaluar
        "breadcrumb": chunk["breadcrumb"],
        "tipo": "factual",
        "revisado": False,
    }, ""


# --------------------------------------------------------------------------
# Principal
# --------------------------------------------------------------------------

def main(n: int):
    load_dotenv()
    client = genai.Client(api_key= os.getenv("GEMINI_API_KEY"))

    chunks = muestrear(CHUNKS_PATH, n)
    print(f"Muestreados {len(chunks)} chunks de {len(chunks)} documentos\n")

    casos, descartes = [], []
    for i, chunk in enumerate(chunks, 1):
        caso, motivo = generar_caso(client, chunk)
        if caso:
            caso["id"] = f"q{len(casos) + 1:03d}"
            casos.append(caso)
            print(f"[{i}/{len(chunks)}] ok   {caso['pregunta']}")
        else:
            descartes.append({"chunk_id": chunk["chunk_id"], "motivo": motivo})
            print(f"[{i}/{len(chunks)}] FALLO ({motivo})")

        time.sleep(10)   # margen para la cuota de la capa gratuita 15 llamadas/minuto

    os.makedirs("eval", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for c in casos:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(DESCARTES_PATH, "w", encoding="utf-8") as f:
        for d in descartes:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"\nGenerados : {len(casos)}")
    print(f"Descartados: {len(descartes)}")
    motivos = defaultdict(int)
    for d in descartes:
        motivos[d["motivo"].split(":")[0]] += 1
    for m, c in sorted(motivos.items(), key=lambda x: -x[1]):
        print(f"  {m}: {c}")
    print(f"\nBorrador en {OUT_PATH} — REVISALO A MANO antes de usarlo.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    main(ap.parse_args().n)