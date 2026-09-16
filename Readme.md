# PROYECTO RAG CON DOCUMENTACIÓN MLFLOW

## 1. Primeros pasos: Configuración y pruebas con GenAI

Lo primero que hice fue crear el API Key y lanzar unas cuantas llamadas básicas
para probar las primeras interacciones con el sistema. Tras eso, estuve viendo
la disponibilidad de modelos para el plan que uso y entendiendo bien sus
limitaciones.

Aún así, durante las pruebas detecté errores del tipo 503 UNAVAILABLE. Para
solucionarlo y no romper la ejecución, implementé una lógica de reintentos: el
código hace varias iteraciones metiendo un tiempo de espera entremedio para ver
si se libera el modelo. Si sigue sin responder, cambia automáticamente a otro
modelo secundario para asegurar que obtenemos respuesta.

## 2. Preprocesado y limpieza de los documentos (.mdx)

El siguiente paso clave para el proyecto fue elegir la documentación sobre la
cual iba a hacer el sistema RAG. Escogí la documentación de la librería MLflow
ya que no es tan utilizada como FastAPI o similares, y por tanto está menos
memorizada por los modelos. Después, procesé los documentos en crudo
(data/raw). Como la documentación original está en .mdx, trae mucho ruido de
React (etiquetas JSX, sentencias import/export, componentes visuales). Si
indexaba eso tal cual, iba a meter mucha información irrelevante en los embeddings.

Como no sabía muy bien cómo realizar esta limpieza y no es información
comprometida, utilicé el agente de Claude Code para que hiciera un archivo .py
de limpieza:

Protección del código (Enmascaramiento): Antes de borrar nada, el script
detecta los bloques de código y los sustituye por unos caracteres ocultos de
Unicode. De esta forma, al pasar las expresiones regulares para borrar los
import de React, no me cargo los import mlflow de los scripts de ejemplo. Al
terminar la limpieza, el código vuelve a su sitio intacto.

Parseo de componentes y tablas: Se desenvuelven las etiquetas estructurales
(como <Tabs>) re-indentando el texto para que Markdown no lo lea como código
por error, y las tablas HTML complejas se aplanan a un formato lineal. Además,
el frontmatter de cada archivo se extrae para usarlo luego como metadatos.

Breadcrumbs (Migas de pan): Implementé una función con una pila (stack) que va
leyendo los encabezados (#, ##, ###) para saber la ruta exacta de cada párrafo
dentro del documento.

El resultado de esta fase es un documentos.jsonl con un registro por documento:
doc_id, path, title, text, n_chars, encabezados y metadatos.

## 3. Chunking

Con los textos limpios, diseñé el empaquetado final asegurando que no se pierda
el contexto semántico:

Código indivisible: Programé un cortador que divide el texto en párrafos pero
trata los bloques de código como unidades cerradas. Así evito que una función
de Python se parta por la mitad.

Solape por tokens (Overlap): Voy agrupando los bloques calculando su tamaño con
el tokenizador. Es importante contar con el tokenizador del modelo de
embeddings y no por palabras ni caracteres: si el chunk se pasa del límite del
modelo, este lo trunca en silencio y pierdes el final del texto sin que salte
ningún error. Cuando supero el límite (max_tokens), cierro el chunk. Para no
perder el hilo entre fragmentos, el nuevo chunk arranca haciendo un solape
hacia atrás, incluyendo los últimos párrafos del bloque anterior.

Ensamblaje del contexto: A cada chunk de texto le concateno su breadcrumb justo
antes del contenido. Esto es lo que se embebe, no el texto a secas: un
fragmento que dice "Set the value to false to disable it" no significa nada por
sí solo, pero con "Tracking > Automatic Logging > Configuration" delante sí.
Guardo los dos campos por separado, text para mostrar y embed_text para
vectorizar.

El resultado se exporta a chunks.jsonl, un registro por fragmento con sus
metadatos.

## 4. Cazando bugs en el chunker

Antes de seguir, me puse a leer los chunks más cortos que había generado y me
encontré con cosas raras. Había breadcrumbs del tipo "MLflow Langchain
Autologging > Your LangChain model code here", que claramente no era un
encabezado de ninguna sección.

El problema era que la expresión regular buscaba líneas que empiezan por # para
detectar los encabezados de Markdown, pero en Python los comentarios también
empiezan por #. Así que cualquier comentario dentro de un bloque de código se
estaba interpretando como un título de sección, partiendo los documentos donde
no tocaba. Eran 501 breadcrumbs falsos, un 25% del total.

Lo arreglé localizando primero los bloques de código cercados y descartando
cualquier # que caiga dentro. Por el camino salieron dos fallos más: la regex
usaba \s+, que incluye el salto de línea, así que una almohadilla suelta se
comía el \n y convertía la línea siguiente en título; y el cortador solo
reconocía los bloques con ```, así que uno abierto con ~~~ sí se podía partir
por la mitad.

Para verificarlo comprobé que la última parte de cada breadcrumb existe de
verdad como encabezado Markdown en su documento. Pasó de 501 falsos a 0.

También ajusté la red de seguridad que descartaba los chunks demasiado cortos:
tal y como estaba, 26 documentos se quedaban sin ningún chunk y desaparecían
del índice, entre ellos 14 fichas de integración (Cohere, DeepSeek, xAI) que
solo tienen título y descripción. La regla ahora es que un chunk corto solo se
descarta si su documento produce algún otro chunk. Si es el único, se conserva.

El resultado final son 2.013 chunks de 323 documentos, con una mediana de 321
tokens y ningún documento fuera del índice.

## 5. El set de evaluación

Antes de empezar a probar configuraciones, monté el set de evaluación. La idea
es tener un conjunto de preguntas donde yo ya sé cuál es la respuesta y en qué
parte del documento está, para poder medir con números si un cambio mejora o
empeora el sistema en vez de ir probando a ojo.

La decisión de diseño importante fue cómo referenciar el fragmento correcto. Lo
natural sería guardar el chunk_id, pero entonces el set se rompe en cuanto
cambie el tamaño de chunk, y cambiar el chunking es justo uno de los
experimentos que quiero hacer. Así que cada caso guarda un ancla: una frase
literal del documento que contiene la respuesta. Un chunk es relevante si su
texto contiene esa frase, y eso se recalcula sobre el troceado que tenga en
cada momento.

Generación: muestreo un chunk de cada documento (uno por doc_id, para que las
preguntas cubran el corpus en vez de concentrarse en los documentos largos) y
le pido a Gemini que escriba una pregunta y devuelva la frase literal donde
está la respuesta, todo en JSON.

Filtros automáticos: verifico que el ancla aparece de verdad en el chunk y que
aparece solo una vez. Los primeros intentos fallaban bastante porque el modelo
se comía el marcado de Markdown: devolvía "aware of your codebase and context"
cuando en el original ponía "**aware of your codebase and context**". Lo
resolví con una función de normalización que quita negritas, cursivas, código
en línea y enlaces antes de comparar. Esa misma función la uso luego al
evaluar, para que el criterio sea idéntico en los dos sitios.

Cuotas: aquí me encontré con que el plan gratuito de Gemini tiene un límite de
20 peticiones al día por modelo, no por minuto como pensaba. Se cortó a mitad
de la tanda. Cambié a un modelo lite, que tiene la cuota más alta, y añadí
guardado incremental y reanudación para que un corte no obligue a empezar de
cero.

Revisión manual: este paso no me lo salté. Los filtros automáticos quitan el
ruido evidente, pero hay preguntas que pasan el filtro y no sirven (demasiado
vagas, o autorreferenciales del tipo "¿para qué sirve esta sección?").

## 6. Embeddings y baseline

Los embeddings los genero en local con sentence-transformers y el modelo
multilingual-e5-base, no por API. El motivo es que voy a reindexar el corpus
entero muchas veces (cada cambio de tamaño de chunk, de solape, y una vez por
cada modelo que compare), y en local eso es gratis e ilimitado. La API de
Gemini la reservo para la generación de respuestas, donde es una llamada por
pregunta.

E5 es un modelo asimétrico, así que hay que anteponer "passage: " a los
documentos y "query: " a las consultas. Olvidarlo degrada el rendimiento sin
dar ningún error, así que lo dejé fijado en la configuración.

Guardo los vectores en un .npy junto a un fichero con los chunk_id en el mismo
orden y otro con la configuración usada. Los tres van juntos: sin el de ids no
sé qué fila es qué chunk, y sin el de config no sé con qué modelo se generó.
Esto último importa porque los espacios vectoriales de dos modelos distintos no
son comparables: si mañana amplío el corpus, los chunks nuevos tienen que
embeberse con el mismo modelo o la búsqueda devuelve basura sin dar error.

Para la búsqueda no hace falta base de datos vectorial todavía. Con 2.013
vectores normalizados, la similitud coseno es una multiplicación de matrices en
numpy y tarda milisegundos, además de ser exacta en vez de aproximada. La
búsqueda está encapsulada en una función con una firma clara, así que migrar a
PostgreSQL con pgvector más adelante es reescribir esa función y nada más.

Primeros resultados (baseline: denso, sin híbrido y sin reranker):

| Métrica   | Valor |
|-----------|-------|
| Recall@1  | 0,276 |
| Recall@5  | 0,517 |
| Recall@20 | 0,793 |
| MRR       | 0,393 |
| nDCG@10   | 0,405 |

La brecha entre Recall@5 y Recall@20 es de 27 puntos, y eso dice algo concreto:
el sistema encuentra el chunk correcto en 4 de cada 5 preguntas, pero lo coloca
demasiado abajo en el ranking. Es justo el escenario donde un reranker tiene
margen para mejorar mucho.

Al mirar las preguntas que peor funcionan me di cuenta de otra cosa: están en
español y el corpus está en inglés. Sin querer he montado un sistema de
recuperación cross-lingüe, que es más difícil que buscar en el mismo idioma. El
siguiente experimento es traducir las preguntas y reevaluar con el mismo
índice, para medir cuánto de la diferencia se explica por ahí.

## 7. Siguientes pasos

- Reevaluar con las preguntas traducidas al inglés y comparar con el set en
  español.
- Limpiar del set las preguntas demasiado vagas o autorreferenciales.
- Búsqueda híbrida: añadir BM25 en paralelo y fusionar los dos rankings con
  Reciprocal Rank Fusion.
- Reranker con cross-encoder sobre el top-50.
- Barrido de configuraciones (tamaño de chunk, solape, modelos de embeddings)
  registrando cada run en MLflow.
- Generación de respuestas con citas, midiendo primero cuánto sabe el modelo a
  libro cerrado para saber cuánto aporta el RAG de verdad.
- API con FastAPI y despliegue con Docker.

## Estructura del repo

```
rag-docs/
├── data/
│   ├── raw/              documentación clonada de MLflow
│   └── processed/        documentos.jsonl, chunks.jsonl, embeddings
├── eval/
│   └── eval_set.jsonl    set de evaluación
├── src/
│   ├── ingest/           parseo de .mdx y chunking
│   ├── index/            generación de embeddings
│   ├── retrieve/         búsqueda
│   ├── evaluate/         generación del set y métricas
│   └── api/
└── tests/
```