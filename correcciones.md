Contexto: tengo un chunker estructural en src/ingest/chunker.py que trocea
documentación (markdown/MDX de MLflow) por encabezados. Lee
data/processed/documentos.jsonl y escribe un jsonl de chunks.

He encontrado dos bugs al inspeccionar la salida.

BUG 1 (prioritario) — detección de encabezados dentro de bloques de código.
La regex HEADING_RE busca líneas que empiecen por # con re.MULTILINE, así que
los comentarios de Python dentro de bloques de código cercados con ``` se
detectan como encabezados de sección. Ejemplos reales de breadcrumbs
corruptos que ha generado:
  "MLflow Langchain Autologging > Your LangChain model code here"
  "Tracing FireworksAI > Use the client as usual - traces will be automatically captured"
  "ResponsesAgent Introduction > %%writefile agent.py"
Esto parte documentos donde no toca y corrompe la jerarquía de secciones.
Arréglalo para que solo se consideren encabezados las líneas que están fuera
de bloques de código. Ten en cuenta que los bloques pueden abrirse con tres o
más backticks y también con ~~~, y que puede haber bloques sin cerrar al final
del fichero.

BUG 2 — restos de frontmatter y chunks residuales.
Hay chunks cuyo texto es literalmente '---' o '...\n'. Parece que el
frontmatter YAML del principio de algunos ficheros no se está eliminando del
todo en el parser (src/ingest/parser.py) o queda un residuo tras el troceado.
Investiga en cuál de los dos módulos está el origen y arréglalo ahí, no
filtrando a posteriori.

Además, la fusión de secciones cortas (min_tokens) no cubre todos los casos:
siguen saliendo chunks de 1, 9 y 12 tokens. Revisa el bucle de fusión; creo
que cuando una sección corta se fusiona con la siguiente y el resultado sigue
por debajo del mínimo, no se vuelve a comprobar. Como red de seguridad, al
escribir descarta los chunks que queden por debajo de min_tokens y no hayan
podido fusionarse con nada, e informa de cuántos se descartaron.

Restricciones:
- No cambies el formato de salida ni los nombres de los campos del dataclass
  Chunk. Otros módulos dependen de ellos.
- No cambies los valores de CONFIG.
- Mantén el chunker determinista: misma entrada y misma config, misma salida.
- Añade tests en tests/ para ambos bugs: al menos un documento con un bloque
  de código que contenga líneas que empiecen por #, y un documento con
  frontmatter YAML.

Verificación: ejecuta el chunker sobre el corpus real e imprime las
estadísticas que ya tiene (documentos, chunks, tokens min/mediana/max, cuántos
superan el máximo, ids duplicados) más el número de chunks descartados.
Después lista los 10 chunks con menos tokens con su breadcrumb, para que
pueda comprobar a mano que ya no aparecen breadcrumbs procedentes de
comentarios de código.

No toques nada fuera de src/ingest/ y tests/.