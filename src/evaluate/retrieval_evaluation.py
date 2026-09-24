"""
Evaluacion del retrieval: baseline denso.

Calcula Recall@k, MRR y nDCG sobre el set de evaluacion y registra el run
en MLflow.

La relevancia se decide por el ANCLA, no por chunk_id: un chunk es relevante
si su texto normalizado contiene el ancla normalizada. Asi el set sobrevive
a cualquier cambio de chunking.

Uso:
    python -m src.evaluate.retrieval_evaluation e5base_512
"""

import argparse
import json
import os

import mlflow
import numpy as np
from sentence_transformers import SentenceTransformer

from src.evaluate.texto import norm   # la MISMA norm que uso el generador

EVAL_PATH = "eval/eval_set_borrador.jsonl"
DIR = "data/processed"
PREFIJO_QUERY = "query: "
KS = (1, 3, 5, 10, 20)


# --------------------------------------------------------------------------
# Relevancia
# --------------------------------------------------------------------------

def anclas_de(caso: dict) -> list[str]:
    """Un caso normal tiene 'ancla'; uno multisalto tiene 'anclas'."""
    if caso.get("anclas"):
        return caso["anclas"]
    return [caso["ancla"]] if caso.get("ancla") else []


def relevantes_por_ancla(anclas, textos_norm) -> list[set[int]]:
    """Para cada ancla, el conjunto de indices de chunk que la contienen."""
    out = []
    for a in anclas:
        an = norm(a)
        out.append({i for i, t in enumerate(textos_norm) if an in t})
    return out

def docs_relevantes(grupos, chunks) -> set[str]:
    """Documentos a los que pertenecen los chunks que contienen el ancla."""
    return {chunks[i]["doc_id"] for g in grupos for i in g}

def ranking_docs(ranking, chunks) -> list[str]:
    """Ranking de documentos: el orden de primera aparicion en el de chunks."""
    vistos, out = set(), []
    for idx in ranking:
        d = chunks[idx]["doc_id"]
        if d not in vistos:
            vistos.add(d)
            out.append(d)
    return out

# --------------------------------------------------------------------------
# Metricas
# --------------------------------------------------------------------------

def hit_at_k(ranking, grupos, k) -> float:
    """1.0 si el top-k cubre TODAS las anclas del caso (multisalto incluido)."""
    top = set(ranking[:k])
    return float(all(top & g for g in grupos))


def recall_at_k(ranking, grupos, k) -> float:
    """Proporcion de anclas cubiertas por el top-k."""
    top = set(ranking[:k])
    return sum(1 for g in grupos if top & g) / len(grupos)


def mrr(ranking, grupos) -> float:
    """1/posicion del primer chunk relevante para cualquier ancla."""
    todos = set().union(*grupos)
    for pos, idx in enumerate(ranking, 1):
        if idx in todos:
            return 1.0 / pos
    return 0.0


def ndcg_at_k(ranking, grupos, k) -> float:
    todos = set().union(*grupos)
    dcg = sum(
        1.0 / np.log2(pos + 1)
        for pos, idx in enumerate(ranking[:k], 1)
        if idx in todos
    )
    ideal = min(len(todos), k)
    idcg = sum(1.0 / np.log2(p + 1) for p in range(1, ideal + 1))
    return dcg / idcg if idcg else 0.0


def doc_hit_at_k(ranking, grupos, chunks, k) -> float:
    """¿Algun chunk del top-k pertenece al documento correcto?"""
    relevantes = docs_relevantes(grupos, chunks)
    return float(any(chunks[i]["doc_id"] in relevantes for i in ranking[:k]))


def doc_mrr(ranking, grupos, chunks) -> float:
    relevantes = docs_relevantes(grupos, chunks)
    for pos, d in enumerate(ranking_docs(ranking, chunks), 1):
        if d in relevantes:
            return 1.0 / pos
    return 0.0
# --------------------------------------------------------------------------
# Principal
# --------------------------------------------------------------------------

def main(nombre: str, eval_path: str = EVAL_PATH):
    prefijo = os.path.join(DIR, nombre)
    emb = np.load(f"{prefijo}.npy")
    ids = json.load(open(f"{prefijo}_ids.json", encoding="utf-8"))
    cfg = json.load(open(f"{prefijo}_config.json", encoding="utf-8"))

    chunks = [json.loads(l) for l in open(cfg["chunks_path"], encoding="utf-8")]
    assert [c["chunk_id"] for c in chunks] == ids, \
        "chunks.jsonl no coincide con el indice: reindexa"

    textos_norm = [norm(c["text"]) for c in chunks]

    casos = [json.loads(l) for l in open(eval_path, encoding="utf-8")]
    con_ancla = [c for c in casos if c.get("tipo") != "sin_respuesta"]
    sin_ancla = len(casos) - len(con_ancla)
    print(f"{len(con_ancla)} casos evaluables ({sin_ancla} sin respuesta, "
          f"se evaluan en la fase de generacion)")

    # Comprobacion de casos huerfanos
    grupos_por_caso, huerfanos = [], []
    for caso in con_ancla:
        grupos = relevantes_por_ancla(anclas_de(caso), textos_norm)
        if any(len(g) == 0 for g in grupos):
            huerfanos.append(caso["id"])
        grupos_por_caso.append(grupos)

    if huerfanos:
        print(f"\nAVISO: {len(huerfanos)} casos sin ningun chunk relevante "
              f"(imposibles de acertar): {huerfanos[:10]}")

    # Busqueda: una sola multiplicacion para todas las preguntas
    model = SentenceTransformer(cfg["modelo"])
    Q = model.encode(
        [PREFIJO_QUERY + c["pregunta"] for c in con_ancla],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    sims = Q @ emb.T                            # (n_preguntas, n_chunks)
    rankings = np.argsort(-sims, axis=1)[:, :max(KS)]

    # Agregacion
    res = {}
    for k in KS:
        res[f"hit@{k}"] = float(np.mean([
            hit_at_k(r, g, k) for r, g in zip(rankings, grupos_por_caso)
        ]))
        res[f"recall@{k}"] = float(np.mean([
            recall_at_k(r, g, k) for r, g in zip(rankings, grupos_por_caso)
        ]))
        res[f"doc_hit@{k}"] = float(np.mean([
        doc_hit_at_k(r, g, chunks, k) for r, g in zip(rankings, grupos_por_caso)
        ]))
    res["mrr"] = float(np.mean([
        mrr(r, g) for r, g in zip(rankings, grupos_por_caso)
    ]))
    res["ndcg@10"] = float(np.mean([
        ndcg_at_k(r, g, 10) for r, g in zip(rankings, grupos_por_caso)
    ]))

    res["doc_mrr"] = float(np.mean([
    doc_mrr(r, g, chunks) for r, g in zip(rankings, grupos_por_caso)
    ]))
    # Reemplazamos el '@' por un '_' para que MLflow lo acepte
    safe_res = {k.replace('@', '_'): v for k, v in res.items()}
    mlflow.log_metrics(safe_res)
    print()
    for m, v in res.items():
        print(f"{m:<12} {v:.3f}")

    # Los 10 peores casos, para mirarlos a mano
    print("\nPeores casos:")
    peores = sorted(
        zip(con_ancla, rankings, grupos_por_caso),
        key=lambda x: mrr(x[1], x[2]),
    )[:10]
    for caso, r, g in peores:
        pos = next((i + 1 for i, idx in enumerate(r)
                    if idx in set().union(*g)), None)
        print(f"  {caso['id']}  pos={pos or '>20'}  {caso['pregunta'][:70]}")

    # MLflow
    mlflow.set_experiment("rag-retrieval")
    mlflow.end_run()
    with mlflow.start_run(run_name=f"denso-{nombre}"):
        mlflow.log_params({
            "indice": nombre,
            "metodo": "denso",
            "reranker": "no",
            "hibrido": "no",
            "n_casos": len(con_ancla),
            **{k: v for k, v in cfg.items() if k != "fecha"},
        })
        mlflow.log_metrics(safe_res)
        mlflow.log_artifact(eval_path)
        mlflow.log_artifact(f"{prefijo}_config.json")

    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("nombre", help="prefijo del indice, p.ej. e5base_512")
    ap.add_argument("--eval", default=EVAL_PATH)
    a = ap.parse_args()
    main(a.nombre, a.eval)