# Plan de proyecto — RAG sobre la documentación de MLflow

Plan por fases. Cada fase tiene un entregable y un criterio de "hecho".
No pases a la siguiente sin cumplirlo: la mayoría de proyectos RAG que se
atascan lo hacen por avanzar sobre una base que no se comprobó.

---

## Estructura del repo

```
rag-docs/
├── docker-compose.yml
├── requirements.txt
├── README.md
├── data/
│   ├── raw/              # markdown clonado, sin tocar
│   └── processed/        # documentos parseados (jsonl)
├── eval/
│   └── eval_set.jsonl    # el set de evaluación, versionado
├── src/
│   ├── ingest/           # parseo, chunking
│   ├── index/            # embeddings, escritura en pgvector, BM25
│   ├── retrieve/         # búsqueda densa, léxica, fusión, reranking
│   ├── generate/         # prompt, llamada al LLM, parseo de citas
│   ├── evaluate/         # métricas de recuperación y de generación
│   └── api/              # FastAPI
└── notebooks/            # exploración, gráficas de resultados
```

Separar `retrieve` de `generate` desde el principio permite evaluar la recuperación sin gastar una sola llamada al LLM.

---

## Fase 0 — Entorno

**Qué hacer**

1. Repo git, entorno virtual, `requirements.txt`.
2. `docker-compose.yml` con Postgres + extensión `pgvector`, y volumen
   persistente para no perder el índice al reiniciar.
3. MLflow apuntando a un directorio local (`mlflow ui` con backend en
   ficheros basta; no necesitas servidor).
4. Un script `scripts/check_env.py` que conecte a Postgres, ejecute
   `CREATE EXTENSION IF NOT EXISTS vector;` y registre un run vacío en MLflow.

**Hecho cuando** el script pasa de principio a fin sin tocar nada a mano.

*Tiempo: media tarde.*

---

## Fase 1 — Corpus

**Qué hacer**

1. Clonar el repo de MLflow y quedarte solo con la carpeta de documentación.
   Descarta código fuente, tests y notebooks de ejemplo.
2. Escribir un parser que recorra los `.md` y produzca un `jsonl` con un
   registro por documento:

```json
{
  "doc_id": "tracking/autolog",
  "path": "docs/source/tracking/autolog.md",
  "title": "Automatic Logging",
  "text": "...",
  "n_chars": 8421
}
```

3. **Cuenta cosas antes de seguir.** Número de documentos, distribución de
   longitudes, cuántos son triviales (menos de 500 caracteres), cuántos
   enormes. Un histograma de longitudes en un notebook.

**Trampa habitual:** los bloques de código dentro del markdown. Decide ahora
qué haces con ellos (¿los mantienes? ¿los truncas? ¿los indexas aparte?) y
déjalo escrito. Si no decides, decidirá el azar y no sabrás por qué falla.

**Hecho cuando** tienes el `jsonl` y sabes decir cuántos documentos hay y de
qué tamaño.

*Tiempo: una tarde.*

---

## Fase 2 — Chunking

**Qué hacer**

1. Chunker estructural: parte por encabezados markdown (`#`, `##`, `###`),
   y si una sección supera el máximo, subdivide recursivamente.
2. Cada chunk lleva estos metadatos, sin excepción:

```json
{
  "chunk_id": "tracking/autolog#configuracion-0",
  "doc_id": "tracking/autolog",
  "path": "...",
  "breadcrumb": "Tracking > Automatic Logging > Configuración",
  "text": "...",
  "n_tokens": 384
}
```

3. El texto que se embebe **no** es `text` a secas, sino
   `breadcrumb + "\n\n" + text`. Esa es la contextualización del chunk.

**Hecho cuando** puedes coger 10 chunks al azar, leerlos, y en todos se
entiende de qué hablan sin abrir el documento original.

*Tiempo: una tarde.*

---

## Fase 3 — El set de evaluación

Aquí es donde se decide si el proyecto va a servir para algo. Y hay una
decisión de diseño crítica.

### El problema del `chunk_id`

Si anclas el set de evaluación a `chunk_id`, **el set se rompe la primera vez
que cambies el tamaño de chunk**, porque los ids cambian. Y cambiar el
chunking es justo uno de los experimentos que quieres hacer.

### La solución: anclar al texto

Cada caso guarda un fragmento literal del documento que contiene la respuesta:

```json
{
  "id": "q001",
  "pregunta": "¿Qué función activa el autologging para scikit-learn?",
  "respuesta": "mlflow.sklearn.autolog()",
  "doc_id": "tracking/autolog",
  "ancla": "mlflow.sklearn.autolog() enables automatic logging",
  "tipo": "factual"
}
```

Y defines la relevancia así: **un chunk es relevante si su texto contiene el
ancla**. Eso sobrevive a cualquier reconfiguración del chunking, porque se
recalcula sobre los chunks del momento.

### Cómo construirlo

1. Muestrea 60–80 chunks cubriendo secciones distintas.
2. Por cada uno, pide a un LLM que genere una pregunta y que devuelva la
   frase literal donde está la respuesta. Esa frase es el ancla.
3. **Revisa uno a uno.** Descarta las que copian el chunk literalmente, las
   ambiguas y las que se responden sin leer nada.
4. Verifica programáticamente que cada ancla aparece exactamente una vez en
   el documento indicado. Si aparece cero o dos veces, el caso está mal.
5. Añade a mano:
   - 10 preguntas **sin respuesta** (sobre ML pero no cubiertas en los docs).
   - 5 preguntas **multi-salto**, con dos anclas en documentos distintos.

**Hecho cuando** tienes 50+ casos validados, todos con ancla verificada, en
`eval/eval_set.jsonl` con un commit propio.

*Tiempo: dos tardes. Es la fase más aburrida y la más importante.*

---

## Fase 4 — Baseline

**Qué hacer**

1. Un solo modelo de embeddings local, chunking fijo de 512, top-5, búsqueda
   densa a secas. Sin híbrido, sin reranker.
2. Indexa a pgvector.
3. Implementa las métricas: Recall@1, @5, @20, MRR, nDCG@10.
4. Registra el run en MLflow con todos los parámetros.

**Chequeo de cordura opcional:** si tienes dudas de si tu código de métricas
está bien, pasa un dataset de QA ya etiquetado (XQuAD, MLQA) por el mismo
pipeline. Si sacas números razonables ahí, tu implementación es correcta.

**Hecho cuando** tienes una tabla con las cinco métricas y un run de MLflow
que la reproduce.

**Qué esperar:** con un corpus limpio y chunking decente, Recall@5 entre 0,60
y 0,80. Si sale por debajo de 0,40, hay un bug —lo más probable, el prefijo
`query:`/`passage:` olvidado, o estar comparando con distancia euclídea
cuando el modelo espera coseno.

*Tiempo: dos tardes.*

---

## Fase 5 — Híbrido

**Qué hacer**

1. Índice BM25 en paralelo (el FTS de Postgres o `rank_bm25`).
2. Fusión con RRF, k = 60.
3. Mide. Compara con el baseline sobre el mismo set.

**Qué esperar:** subida de 5 a 15 puntos en Recall@5. En documentación técnica
el efecto suele ser grande, porque las preguntas contienen nombres de
funciones y parámetros que la búsqueda densa no ancla bien.

**Análisis que merece la pena:** ¿qué preguntas arregla el BM25 que la densa
fallaba, y al revés? Ahí se ve la intuición de por qué el híbrido funciona.

*Tiempo: una tarde.*

---

## Fase 6 — Reranker

**Qué hacer**

1. Recupera top-50 con el híbrido, reordena con un cross-encoder, quédate con
   top-5.
2. Mide.

**Antes de implementarlo**, mira tu Recall@20 del baseline. Ese es el techo
que el reranker puede alcanzar. Si Recall@20 es 0,90 y Recall@5 es 0,65,
tienes 25 puntos de margen. Si Recall@20 es 0,70, el reranker te dará poco y
el problema está en el chunking o el corpus.

*Tiempo: una tarde.*

---

## Fase 7 — Barrido de configuración

Ahora que el pipeline es sólido, experimenta. Un cambio cada vez, un run de
MLflow por configuración.

| Experimento | Valores |
|---|---|
| Tamaño de chunk | 256 / 512 / 1024 |
| Solape | 0 % / 10 % / 20 % |
| Chunking | fijo vs estructural |
| Contextualización | con breadcrumb vs sin |
| Modelo de embeddings | 3–4 candidatos |
| top-k antes del reranker | 20 / 50 / 100 |

**Entregable:** una tabla de resultados y dos o tres gráficas. Esto es el
corazón del proyecto, más que la demo.

*Tiempo: dos o tres tardes, casi todo esperando a que reindexe.*

---

## Fase 8 — Generación

**Qué hacer**

1. **Primero, la línea base a libro cerrado.** Pasa el set de evaluación por
   el LLM sin contexto ninguno. Anota el acierto. Ese número te dice cuánto
   sabía ya, y por tanto cuánto aporta tu RAG.
2. Prompt con chunks numerados, instrucción de responder solo con el
   contexto, obligación de citar y de decir "no lo sé".
3. Parsea las citas de la respuesta y verifica que apuntan a chunks que
   realmente se le pasaron.
4. Métricas: fidelidad, corrección, tasa de abstención sobre las 10 preguntas
   sin respuesta.
5. Test de contexto falseado sobre 20 casos: manipula un dato del chunk y
   comprueba si el modelo responde con el dato falso (usa el contexto) o con
   el real (tira de memoria).

**Hecho cuando** puedes enseñar la tabla: libro cerrado vs RAG, con la
diferencia.

*Tiempo: dos tardes.*

---

## Fase 9 — Empaquetado

**Qué hacer**

1. FastAPI con `POST /query` (pregunta → respuesta + citas + chunks usados) y
   `GET /health`.
2. Devuelve siempre los chunks recuperados junto a la respuesta. Es lo que
   hace el sistema depurable desde fuera.
3. Docker Compose: API + Postgres.
4. README con: arquitectura, cómo levantarlo, y **la tabla de resultados**.

*Tiempo: una o dos tardes.*

---

## Fase 10 — Cambio de corpus

Sustituyes el corpus de la fase 1 y construyes un nuevo set de evaluación con
el mismo formato. Todo lo demás vale tal cual.

Aquí es donde el trabajo previo rinde: cuando las métricas bajen, ya sabes que
no es tu código, porque el mismo código daba buenos números antes. Esa es la
condición que hace que la comparativa de modelos signifique algo.

---

## Resumen de tiempos

| Fase | Tardes |
|---|---|
| 0. Entorno | 0,5 |
| 1. Corpus | 1 |
| 2. Chunking | 1 |
| 3. Set de evaluación | 2 |
| 4. Baseline | 2 |
| 5. Híbrido | 1 |
| 6. Reranker | 1 |
| 7. Barrido | 3 |
| 8. Generación | 2 |
| 9. Empaquetado | 1,5 |
| **Total fase 1 del proyecto** | **~15 tardes** |

Es decir, entre tres y cinco semanas a ritmo de proyecto personal. Si te
salen dos meses, es normal: siempre son dos meses.

---

## Los tres puntos donde se atascan estos proyectos

1. **Saltarse el set de evaluación** y empezar a ajustar a ojo. Sin métricas
   no sabes si mejoras, y acabas dando vueltas.
2. **Parseo del corpus.** Por eso empezamos con markdown y no con PDF.
3. **Cambiar varias cosas a la vez** y no poder atribuir la mejora. La
   disciplina de un run de MLflow por cambio parece burocracia hasta la
   décima configuración, y entonces es lo único que te salva.
