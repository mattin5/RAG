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

### Acierto a nivel de documento

Con las métricas anteriores solo sabía si el chunk exacto aparecía en el top-k,
pero no si el sistema al menos estaba buscando en el sitio correcto. Así que
añadí métricas a nivel de documento: un acierto cuenta si alguno de los chunks
recuperados pertenece al documento que contiene la respuesta. Los documentos
relevantes los saco de los chunks que contienen el ancla, no del doc_id de la
pregunta, para que funcione también con las preguntas multisalto.

La idea es separar dos fallos distintos: si acierta el documento pero no el
chunk, el sistema sabe de qué va la pregunta pero elige otra sección, y eso es
un problema de chunking; si no acierta ni el documento, el problema es de
fondo, del modelo o de cómo está formulada la consulta.

| k  | Chunk | Documento |
|----|-------|-----------|
| 1  | 0,276 | 0,397     |
| 3  | 0,414 | 0,500     |
| 5  | 0,517 | 0,638     |
| 10 | 0,638 | 0,724     |
| 20 | 0,793 | 0,793     |

MRR: 0,393 a nivel de chunk y 0,499 a nivel de documento.

El dato más revelador es que en k=20 las dos métricas coinciden. Es decir,
siempre que el documento correcto aparece entre los 20 primeros, el chunk
correcto también. No hay ningún caso en el que el sistema llegue al documento y
se pierda dentro de él, así que el chunking no es lo que está limitando el
rendimiento.

En los primeros puestos sí hay una diferencia de unos 12 puntos: muchas veces
el primer resultado es del documento correcto pero de otra sección, y el chunk
bueno está unos puestos más abajo. Eso es justo lo que arregla un reranker, que
solo tiene que reordenar lo que ya está en el top-20.

El problema principal era el 21% de preguntas en las que el sistema no llegaba
ni al documento correcto. Ahí ni el reranker ni el chunking ayudan, porque el
reranker solo reordena lo que el retriever le pasa.

## 7. Revisión del set de evaluación

Antes de tocar nada del pipeline, me puse a leer las preguntas que peor
funcionaban para ver si el problema era del sistema o del set. Encontré tres
causas distintas.

**Términos técnicos destrozados por la traducción.** Las preguntas las generó
Gemini con un prompt en español, así que las escribió en español aunque leyera
chunks en inglés, y por el camino tradujo términos que en la documentación
nunca aparecen traducidos. Una preguntaba por "un intervalo de seguimiento"
cuando el corpus dice *span*; otra por "anidar el paquete" cuando era
*install*. Con el término técnico traducido, el anclaje léxico desaparece del
todo.

**Preguntas vagas.** Cosas del tipo "¿para qué tipo de usuarios está
recomendada esta sección?" o "¿qué herramientas ofrece la plataforma?". Encajan
con decenas de chunks, así que no miden el retriever, miden el ruido.

**Ambigüedad del corpus.** Esta es la más interesante. La documentación de
MLflow describe cada juez de evaluación con la misma estructura, y las páginas
de integraciones están hechas con plantilla, así que comparten párrafos enteros
palabra por palabra. Tenía cuatro preguntas casi idénticas sobre cuatro páginas
casi idénticas. Un humano experto tampoco sabría cuál de ellas le estás
pidiendo.

Al revisar caso por caso descarté 2 preguntas y reescribí 9. El criterio para
reescribir fue hacerlas discriminantes: nombrar el detalle que distingue ese
chunk de sus vecinos (el juez concreto, la integración concreta) pero **sin
filtrar la respuesta en el enunciado**. En un primer intento puse el nombre del
juez entre paréntesis en una pregunta cuya respuesta era precisamente ese
nombre, lo cual habría subido las métricas sin que el sistema mejorase nada.

Las reescrituras las hice sobre los mismos chunks, no muestreando otros nuevos.
Cambiar de chunks habría sido elegir la muestra en función de lo bien que
funciona el sistema, que es justo lo que invalida una evaluación.

Para aplicarlo escribí un script que busca los casos por su campo `id` y nunca
por su posición en la lista (los índices se desplazan al borrar casos, los ids
no), verifica las anclas nuevas antes de escribir nada y aborta si alguna no
aparece en ningún chunk. Los casos tocados quedan marcados con
`"reescrito": true`.

### Anclas en varios documentos

Al verificar las anclas nuevas me encontré con que una aparecía en dos
documentos distintos. La primera reacción fue desambiguarla, pero al abrir los
dos vi que ambos responden correctamente la pregunta: son dos páginas que
documentan el mismo juez. En ese caso tener dos fuentes válidas no es un
defecto, y las métricas ya lo manejan bien, porque cuentan acierto si el top-k
contiene algún chunk relevante.

La regla que me quedó: cuando un ancla aparece en varios documentos, hay que
abrirlos y preguntarse si todos responden. Si sí, se acepta; si uno es la
respuesta equivocada, hay que desambiguar. En otra pregunta sí tuve que
hacerlo, porque el ancla que había elegido aparecía tanto en la página de
LangChain como en la de LangGraph, y la pregunta era específica de LangGraph.

## 8. Baseline con el set revisado

| k  | Chunk | Documento |
|----|-------|-----------|
| 1  | 0,339 | 0,500     |
| 3  | 0,518 | 0,625     |
| 5  | 0,643 | 0,750     |
| 10 | 0,750 | 0,857     |
| 20 | 0,911 | 0,929     |

MRR 0,479, nDCG@10 0,495, MRR a nivel de documento 0,614. 56 preguntas.

**Importante: esta subida no es una mejora del sistema.** El índice, el modelo
y el chunking son exactamente los mismos que antes; lo único que ha cambiado es
el instrumento de medida. Borrar preguntas que fallaban y hacer el resto más
precisas sube las métricas por construcción. Los dos números no son
comparables, y el baseline válido de aquí en adelante es este.

Lo que sí dice algo es el Recall@20, que pasa de 0,793 a 0,911. Ese número es
el techo del sistema: antes había 12 preguntas que el retriever no alcanzaba de
ninguna manera y ahora son 5. Como el retriever no ha cambiado, esas 7
preguntas recuperadas estaban mal formuladas, no eran fallos del sistema.

También aparece por primera vez una diferencia entre chunk y documento en k=20:
0,911 frente a 0,929. Hay exactamente un caso en el que el sistema encuentra el
documento correcto pero no el chunk con el ancla. Es el primer fallo de
chunking real que sale, probablemente un ancla que cae en la frontera entre dos
fragmentos.

El margen sigue estando donde estaba: 27 puntos entre Recall@5 y Recall@20. El
chunk correcto está ahí, solo que mal colocado, que es exactamente lo que
arregla un reranker.

Una limitación que conviene dejar dicha: al hacer las preguntas más
discriminantes, el set mide recuperación con consultas bien formuladas, no
robustez ante consultas vagas. Medir lo segundo sería otro set de preguntas
deliberadamente imprecisas, y es un experimento aparte.

## 9. Traducción del set: recuperación cross-lingüe

Como he mencionado en un apartado anterior, había montado un
sistema de recuperación cross-lingüe, que es más difícil que buscar en el
mismo idioma: el modelo tiene que salvar el salto entre idiomas además de
entender la pregunta.

Antes de tocar nada del pipeline quise medir cuánto costaba eso y cuánto rendimiento estaba perdiendo. Traduje las 56 preguntas al inglés y reevalué con el mismo índice y las mismas anclas, de
modo que lo único que cambia entre las dos corridas es el idioma de la
consulta.

Dos detalles al traducir. Primero, traduje **solo el campo `pregunta`**: las
anclas son texto literal del corpus, ya están en inglés y no se tocan. Segundo,
en el prompt insistí en que no tradujera los términos técnicos (*span*,
*trace*, *judge*, nombres de clases, comandos), porque traducirlos fue
precisamente uno de los problemas que había detectado en el set original.

También aprendí algo por el camino: le pedí a Gemini que devolviera el JSONL
completo y el fichero resultante no se podía parsear, porque las anclas
contienen comillas dobles y el modelo no las escapaba. La solución fue que el
modelo devuelva únicamente la traducción de cada pregunta y que el fichero lo
construya Python con `json.dumps`, copiando el resto de campos del original. Es
más robusto y además garantiza que las anclas no pasan nunca por el modelo.

### Resultados

| Métrica   | Español | Inglés | Δ     |
|-----------|---------|--------|-------|
| Recall@1  | 0,339   | 0,464  | +12,5 |
| Recall@5  | 0,643   | 0,786  | +14,3 |
| Recall@10 | 0,750   | 0,911  | +16,1 |
| Recall@20 | 0,911   | 0,929  | +1,8  |
| MRR       | 0,479   | 0,596  | +11,7 |

A nivel de documento, con las preguntas en inglés: 0,571 en k=1, 0,857 en k=5
y 0,982 en k=10 y k=20. MRR de documento 0,708.

Lo interesante no es que mejore, sino **dónde** mejora. El Recall@20 apenas se
mueve (una sola pregunta), mientras que el Recall@5 sube 14 puntos y el
Recall@10 sube 16. Es decir, el cruce de idiomas no impedía encontrar el chunk
correcto: lo empujaba hacia abajo en el ranking. El modelo multilingüe sí
conecta una pregunta en español con un documento en inglés, pero con menos
confianza, así que el fragmento bueno acababa en la posición 8 en vez de en la
3.

Resumido en una frase: en este corpus, la recuperación cross-lingüe cuesta unos
14 puntos de Recall@5 pero casi nada de Recall@20.

### Qué queda

Con las preguntas en inglés, `doc_hit@20` es 0,982: solo hay una pregunta en la
que el sistema no llega ni al documento correcto. Es el único fallo de fondo
que queda por entender.

El `hit@20` es 0,929, cuatro puntos por debajo. Esa diferencia son 3 preguntas
en las que el documento correcto sí aparece pero el chunk que contiene el ancla
no. Ese sí es un límite del chunking, y es la primera vez que se puede medir.

El margen para un reranker se ha reducido: la brecha entre Recall@5 y Recall@20
ha pasado de 27 puntos a 14. Sigue habiendo recorrido, pero menos, lo cual
significa que el retriever ya coloca razonablemente bien.

## 10. Búsqueda híbrida: BM25 + denso con RRF

La búsqueda densa capta significado pero se pierde con identificadores exactos;
BM25 hace lo contrario. Como la documentación de MLflow está llena de nombres
de funciones y clases, tenía sentido probar las dos y fusionarlas.

**Tokenización.** BM25 compara tokens, así que cómo se parte el texto cambia
mucho el resultado. Uso `[a-z0-9_]+` en minúsculas, lo que parte por puntos y
paréntesis pero conserva los guiones bajos: `span.set_inputs()` produce los
tokens `span` y `set_inputs`, de modo que una pregunta que mencione
`set_inputs` casa aunque no escriba la llamada entera. Es una hipótesis, no una
verdad, y se puede medir contra otras tokenizaciones.

**Qué se indexa.** El campo `text`, no `embed_text`. El breadcrumb ayuda al
embedding pero en BM25 solo repite los mismos términos en todos los chunks de
un documento, desplazando las frecuencias sin aportar señal.

**Fusión.** Reciprocal Rank Fusion con k=60:

    score(d) = Σ_i  1 / (k + rank_i(d))

Usa solo las posiciones, no las puntuaciones, así que no hay que calibrar
escalas entre un buscador que devuelve cosenos entre 0 y 1 y otro que devuelve
puntuaciones BM25 sin acotar. Cada buscador aporta 100 candidatos antes de
fusionar, más profundo que el k final, para que un chunk que esté en la
posición 40 de uno y la 3 del otro pueda subir al top-5.

### Resultados

| Métrica   | Denso | BM25  | Híbrido |
|-----------|-------|-------|---------|
| Recall@1  | 0,464 | 0,482 | 0,607   |
| Recall@3  | 0,661 | 0,696 | 0,804   |
| Recall@5  | 0,786 | 0,786 | 0,893   |
| Recall@10 | 0,911 | 0,839 | 0,946   |
| Recall@20 | 0,929 | 0,893 | 0,964   |
| MRR       | 0,596 | 0,605 | 0,728   |
| nDCG@10   | 0,628 | 0,621 | 0,741   |

A nivel de documento, el híbrido llega a 0,929 en k=3 y 0,982 en k=20.

Lo primero que llama la atención es que **BM25 por sí solo compite con el
modelo neuronal**, y de hecho lo supera en las primeras posiciones. Tiene
sentido: el corpus está lleno de identificadores y las preguntas, después de la
revisión, contienen esos términos exactos. Es el escenario donde la
coincidencia léxica gana. BM25 se queda corto en profundidad, a partir de k=10,
porque no puede encontrar lo que no comparte vocabulario con la pregunta.

Lo segundo es que **el híbrido supera a los dos en todos los k**, y por unos 12
puntos. Eso solo pasa si los dos buscadores fallan en preguntas distintas: si
fallaran en las mismas, la fusión daría aproximadamente el mejor de los dos.
Se ve en los casos concretos. Hay tres preguntas que BM25 no encuentra ni en el
top-20 y que el híbrido recupera a las posiciones 9, 7 y 5, rescatadas por la
parte densa.

### Lo que queda

Con Recall@20 en 0,964 solo hay 2 preguntas de 56 que el sistema no alcanza, y
las dos fallan igual en BM25 y en el híbrido. Tienen algo en común: sus anclas
son muy cortas y están dentro de bloques de código o de viñetas
(`set_model(agent)`, `- Token counts and cost breakdown.`). Antes de culpar al
retriever conviene revisar si el problema es el ancla elegida.

El margen para un reranker se ha reducido mucho: la brecha entre Recall@5
(0,893) y Recall@20 (0,964) es de 7 puntos, cuando en el baseline inicial era
de 27. Sigue mereciendo la pena probarlo, pero el recorrido es bastante menor.

### Evolución hasta aquí

| Configuración                    | Recall@5 | MRR   |
|----------------------------------|----------|-------|
| Denso, preguntas en español      | 0,643    | 0,479 |
| Denso, preguntas en inglés       | 0,786    | 0,596 |
| BM25, preguntas en inglés        | 0,786    | 0,605 |
| Híbrido (RRF), preguntas inglés  | 0,893    | 0,728 |

## 11. Siguientes pasos

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