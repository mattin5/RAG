"""
Aplica la revision manual al set de evaluacion.

Busca los casos por su campo "id", nunca por posicion en la lista: los ids no
se mueven aunque se borren casos, los indices si.

Antes de escribir nada, comprueba que cada ancla nueva aparece en al menos un
chunk y avisa si aparece en varios documentos distintos. Si algo falla, no
toca el fichero.

Uso:
    python -m src.evaluate.aplicar_revision
"""

import json
import shutil

from src.evaluate.texto import norm

EVAL_PATH = "eval/eval_set_borrador.jsonl"
CHUNKS_PATH = "data/processed/chunks.jsonl"
BACKUP_PATH = "eval/eval_set_pre_revision.jsonl"


# --------------------------------------------------------------------------
# La revision
# --------------------------------------------------------------------------

BORRAR = {"q027", "q055"}
AMBIGUEDAD_ACEPTADA = {"q030"}

REESCRIBIR = {
    "q015": {
        "pregunta": "¿Cómo se llama el juez incorporado en MLflow que evalúa si "
                    "la respuesta generada atiende directamente la entrada del "
                    "usuario sin desviarse a temas no relacionados?",
        "respuesta": "RelevanceToQuery",
        "ancla": "RelevanceToQuery: Evaluates if your app's response directly "
                 "addresses the user's input",
    },
    "q019": {
        "pregunta": "Si ya uso la librería transformers, ¿qué sección de la "
                    "documentación de MLflow me ayuda a empezar con tracking e "
                    "inferencia?",
        "respuesta": "La sección de tutoriales y guías del flavor Transformers "
                     "de MLflow",
        "ancla": "If this is your first exposure to transformers or use "
                 "transformers extensively but are new to MLflow, this is a "
                 "great place to start.",
    },
    "q022": {
        "pregunta": "¿Qué comando de npm hay que ejecutar para instrumentar con "
                    "MLflow una aplicación JavaScript que usa FireworksAI?",
        "respuesta": "npm install @mlflow/openai openai",
        "ancla": "Create an OpenAI client configured for FireworksAI",
    },
    "q023": {
        "pregunta": "¿Qué valor asigna en el campo value del objeto Feedback el "
                    "juez Correctness de MLflow cuando la respuesta es correcta?",
        "respuesta": '"yes"',
        "ancla": '- value: "yes" if response is correct, "no" if incorrect',
    },
    "q024": {
        "pregunta": "¿En qué URL local se visualizan los traces tras definir e "
                    "invocar un agente de LangGraph en MLflow?",
        "respuesta": "http://localhost:5000, la interfaz de MLflow",
        "ancla": "MLflow automatically tracks token usage and cost for LangGraph.",
    },
    "q026": {
        "pregunta": "¿Qué capacidades ofrece MLflow para flujos de trabajo de "
                    "deep learning con frameworks como PyTorch o TensorFlow?",
        "respuesta": "Seguimiento de experimentos, gestión de modelos y "
                     "capacidades de despliegue",
        "ancla": "From PyTorch training loops to TensorFlow models, MLflow "
                 "streamlines your path from experimentation to production.",
    },
    "q030": {
        "pregunta": "¿Qué juez integrado de MLflow se utiliza en sistemas RAG "
                    "para evaluar si los documentos recuperados contienen toda "
                    "la información necesaria?",
        "respuesta": "RetrievalSufficiency",
        "ancla": "RetrievalSufficiency | Do retrieved documents contain all "
                 "necessary information?",
    },
    "q042": {
        "pregunta": "¿Cómo se registran los datos de entrada en un span dentro "
                    "de MLflow Tracing?",
        "respuesta": "Con el método span.set_inputs()",
        "ancla": "You can log input data with the `span.set_inputs()` method "
                 "for a span object returned by the",
    },
    "q052": {
        "pregunta": "¿Qué valor devuelve en el campo value el juez "
                    "ToolCallEfficiency de MLflow si las llamadas a "
                    "herramientas son eficientes?",
        "respuesta": '"yes"',
        "ancla": '- value: "yes" if tool calls are efficient, "no" if otherwise',
    },
}


# --------------------------------------------------------------------------

def comprobar_ancla(ancla: str, chunks: list[dict]) -> tuple[int, set[str]]:
    """Devuelve (n_chunks_que_la_contienen, docs_distintos)."""
    a = norm(ancla)
    hits = [c for c in chunks if a in norm(c["text"])]
    return len(hits), {c["doc_id"] for c in hits}


def main():
    casos = [json.loads(l) for l in open(EVAL_PATH, encoding="utf-8")]
    chunks = [json.loads(l) for l in open(CHUNKS_PATH, encoding="utf-8")]
    por_id = {c["id"]: c for c in casos}

    # Nada de esto debe fallar en silencio
    faltan = (BORRAR | set(REESCRIBIR)) - set(por_id)
    if faltan:
        raise SystemExit(f"Estos ids no estan en el set: {sorted(faltan)}")

    # 1. Comprobar las anclas nuevas ANTES de tocar el fichero
    print("Comprobacion de anclas nuevas:\n")
    problemas = []
    for qid in sorted(REESCRIBIR):
        n, docs = comprobar_ancla(REESCRIBIR[qid]["ancla"], chunks)
        if n == 0:
            estado = "SIN CHUNKS"
            problemas.append(qid)
        elif len(docs) > 1:
            if qid in AMBIGUEDAD_ACEPTADA:
                estado = f"ok ({len(docs)} docs, aceptado)"
            else:
                estado = f"EN {len(docs)} DOCS DISTINTOS"
                problemas.append(qid)
        else:
            estado = "ok"
        print(f"  {qid}  chunks={n:<3} docs={len(docs):<3} {estado}")

    if problemas:
        raise SystemExit(
            f"\nNo escribo nada. Revisa las anclas de: {sorted(problemas)}"
        )

    # 2. Aplicar los cambios (por id, no por posicion)
    shutil.copy(EVAL_PATH, BACKUP_PATH)

    nuevos = []
    for caso in casos:
        qid = caso["id"]
        if qid in BORRAR:
            continue
        if qid in REESCRIBIR:
            caso = {**caso, **REESCRIBIR[qid], "reescrito": True}
        nuevos.append(caso)

    with open(EVAL_PATH, "w", encoding="utf-8") as f:
        for caso in nuevos:
            f.write(json.dumps(caso, ensure_ascii=False) + "\n")

    print(f"\nCasos: {len(casos)} -> {len(nuevos)} "
          f"({len(BORRAR)} borrados, {len(REESCRIBIR)} reescritos)")
    print(f"Copia de seguridad en {BACKUP_PATH}\n")

    # 3. Comprobacion final sobre TODO el set, no solo los tocados
    huerfanos, ambiguos = [], []
    for caso in nuevos:
        if caso.get("tipo") == "sin_respuesta":
            continue
        anclas = caso.get("anclas") or ([caso["ancla"]] if caso.get("ancla") else [])
        for a in anclas:
            n, docs = comprobar_ancla(a, chunks)
            if n == 0:
                huerfanos.append(caso["id"])
            elif len(docs) > 1:
                ambiguos.append(f"{caso['id']}({len(docs)} docs)")

    print(f"Huerfanos (imposibles de acertar): {huerfanos or 'ninguno'}")
    print(f"Anclas en varios documentos      : {ambiguos or 'ninguna'}")


if __name__ == "__main__":
    main()