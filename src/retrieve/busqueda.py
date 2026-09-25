"""
Busqueda: densa, lexica (BM25) e hibrida (RRF).

Las tres funciones devuelven lo mismo: una lista con un ranking por pregunta,
donde cada ranking es una lista de INDICES de chunk (posicion en chunks.jsonl)
ordenada de mas a menos relevante. Asi el evaluador no sabe ni le importa que
metodo se uso.

Uso tipico:
    chunks = [json.loads(l) for l in open(...)]
    bm25 = construir_bm25(chunks)
    rankings = buscar_hibrido(preguntas, emb, model, bm25, k=20)
"""

import re

import numpy as np
from rank_bm25 import BM25Okapi

PREFIJO_QUERY = "query: "      # E5 espera este prefijo en las consultas
K_RRF = 60                     # constante de Reciprocal Rank Fusion
N_CANDIDATOS = 100             # cuantos pide cada buscador antes de fusionar


# --------------------------------------------------------------------------
# Tokenizacion para BM25
# --------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def tokenizar(texto: str) -> list[str]:
    """
    Minusculas y separacion por todo lo que no sea alfanumerico o guion bajo.

    Decision importante para este corpus: al partir por puntos y parentesis,
    `span.set_inputs()` produce los tokens ['span', 'set_inputs'], de modo que
    una pregunta que mencione set_inputs casa aunque no escriba la llamada
    entera. Conservar el guion bajo mantiene los identificadores enteros.

    Es una hipotesis, no una verdad: se puede comparar contra otras
    tokenizaciones midiendo el Recall.
    """
    return _TOKEN_RE.findall(texto.lower())


def construir_bm25(chunks: list[dict]) -> BM25Okapi:
    """
    Indice lexico en memoria. Con unos miles de chunks tarda menos de un
    segundo, asi que no hace falta persistirlo.

    Se indexa `text`, NO `embed_text`: el breadcrumb ayuda al embedding pero
    en BM25 solo repite los mismos terminos en todos los chunks de un mismo
    documento, lo que desplaza las frecuencias sin aportar senal.
    """
    return BM25Okapi([tokenizar(c["text"]) for c in chunks])


# --------------------------------------------------------------------------
# Busqueda densa
# --------------------------------------------------------------------------

def buscar_denso(preguntas, emb, model, k: int = 20) -> list[list[int]]:
    """Similitud coseno contra todos los chunks (los vectores estan normalizados)."""
    Q = model.encode(
        [PREFIJO_QUERY + p for p in preguntas],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    sims = Q @ emb.T                                   # (n_preguntas, n_chunks)
    return [list(r) for r in np.argsort(-sims, axis=1)[:, :k]]


# --------------------------------------------------------------------------
# Busqueda lexica
# --------------------------------------------------------------------------

def buscar_bm25(preguntas, bm25: BM25Okapi, k: int = 20) -> list[list[int]]:
    """BM25 sobre los tokens de la pregunta. Sin prefijo: no es un modelo neuronal."""
    rankings = []
    for p in preguntas:
        scores = bm25.get_scores(tokenizar(p))
        rankings.append(list(np.argsort(-scores)[:k]))
    return rankings


# --------------------------------------------------------------------------
# Fusion
# --------------------------------------------------------------------------

def rrf(rankings: list[list[int]], k_rrf: int = K_RRF) -> list[int]:
    """
    Reciprocal Rank Fusion de varios rankings del MISMO query.

        score(d) = suma_i  1 / (k + rank_i(d))

    Usa solo las posiciones, no las puntuaciones, asi que no hay que calibrar
    escalas entre un buscador que devuelve cosenos (0 a 1) y otro que devuelve
    puntuaciones BM25 sin acotar.
    """
    scores: dict[int, float] = {}
    for ranking in rankings:
        for pos, idx in enumerate(ranking, 1):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k_rrf + pos)
    return sorted(scores, key=lambda i: -scores[i])


def buscar_hibrido(
    preguntas,
    emb,
    model,
    bm25: BM25Okapi,
    k: int = 20,
    n_candidatos: int = N_CANDIDATOS,
    k_rrf: int = K_RRF,
) -> list[list[int]]:
    """
    Ejecuta los dos buscadores, fusiona con RRF y devuelve el top-k.

    Cada buscador aporta n_candidatos (mas profundo que k) para que la fusion
    tenga margen: un chunk en la posicion 40 de la densa y la 3 de BM25 debe
    poder subir al top-5, y eso no puede pasar si solo se fusionan los 20
    primeros de cada uno.
    """
    r_densos = buscar_denso(preguntas, emb, model, k=n_candidatos)
    r_bm25 = buscar_bm25(preguntas, bm25, k=n_candidatos)
    return [rrf([rd, rb], k_rrf)[:k] for rd, rb in zip(r_densos, r_bm25)]