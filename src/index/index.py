"""
Indexado: genera los embeddings de los chunks y los guarda en disco.

Escribe tres ficheros con el mismo prefijo:
    <prefijo>.npy          matriz (n_chunks, dim) float32, normalizada
    <prefijo>_ids.json     lista de chunk_id en el MISMO orden que las filas
    <prefijo>_config.json  la configuracion con la que se genero

Los tres van juntos. Sin el fichero de ids no sabes que fila es que chunk,
y sin el de config no sabes con que modelo se genero.

Uso:
    python -m src.index.index data/processed/chunks.jsonl e5base_512
"""

import argparse
import json
import os
from datetime import date

import numpy as np
from sentence_transformers import SentenceTransformer

MODELO = "intfloat/multilingual-e5-base"
PREFIJO_DOC = "passage: "     # prefijo que espera E5 para documentos
BATCH_SIZE = 32
DIR_SALIDA = "data/processed"


def indexar(chunks_path: str, nombre: str, modelo: str = MODELO):
    chunks = [json.loads(l) for l in open(chunks_path, encoding="utf-8")]
    print(f"{len(chunks)} chunks leidos de {chunks_path}")

    model = SentenceTransformer(modelo)
    print(f"modelo    : {modelo}")
    print(f"dimension : {model.get_sentence_embedding_dimension()}")
    print(f"max_seq   : {model.max_seq_length}")

    # Aviso si algun chunk va a truncarse
    largos = [c for c in chunks if c["n_tokens"] > model.max_seq_length]
    if largos:
        print(f"AVISO: {len(largos)} chunks superan max_seq_length "
              f"y se truncaran al embeber")

    textos = [PREFIJO_DOC + c["embed_text"] for c in chunks]

    emb = model.encode(
        textos,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,    # producto escalar == coseno
        show_progress_bar=True,
        convert_to_numpy=True,
    ).astype(np.float32)

    # Comprobaciones
    normas = np.linalg.norm(emb, axis=1)
    assert emb.shape[0] == len(chunks), "filas != chunks"
    assert np.allclose(normas, 1.0, atol=1e-4), "vectores sin normalizar"

    os.makedirs(DIR_SALIDA, exist_ok=True)
    prefijo = os.path.join(DIR_SALIDA, nombre)

    np.save(f"{prefijo}.npy", emb)
    with open(f"{prefijo}_ids.json", "w", encoding="utf-8") as f:
        json.dump([c["chunk_id"] for c in chunks], f)
    with open(f"{prefijo}_config.json", "w", encoding="utf-8") as f:
        json.dump({
            "modelo": modelo,
            "prefijo_doc": PREFIJO_DOC,
            "dimension": int(emb.shape[1]),
            "n_chunks": int(emb.shape[0]),
            "chunks_path": chunks_path,
            "normalizado": True,
            "fecha": str(date.today()),
        }, f, indent=2, ensure_ascii=False)

    print(f"\nGuardado: {prefijo}.npy  {emb.shape}  "
          f"({emb.nbytes / 1e6:.1f} MB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("chunks_path")
    ap.add_argument("nombre", help="prefijo de salida, p.ej. e5base_512")
    ap.add_argument("--modelo", default=MODELO)
    a = ap.parse_args()
    indexar(a.chunks_path, a.nombre, a.modelo)