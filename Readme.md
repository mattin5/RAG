# PROYECTO RAG CON DOCUMENTACIÓN MLFLOW
## 1. Primeros pasos: Configuración y pruebas con GenAI
Lo primero que hice fue crear el API Key y lanzar unas cuantas llamadas básicas para probar las primeras interacciones con el sistema. Tras eso, estuve viendo la disponibilidad de modelos para el plan que uso y entendiendo bien sus limitaciones. Como las restricciones son por X llamadas/minuto, de entrada no me condiciona tanto porque en este proyecto haré llamadas más puntuales.

Aún así, durante las pruebas detecté errores del tipo 503 UNAVAILABLE. Para solucionarlo y no romper la ejecución, implementé una lógica de reintentos: el código hace varias iteraciones metiendo un tiempo de espera entremedio para ver si se libera el modelo. Si sigue sin responder, cambia automáticamente a otro modelo secundario para asegurar que obtenemos respuesta.

## 2. Preprocesado y limpieza de los documentos (.mdx)
El siguiente paso clave para el proyecto fue elegir la documentación sobre el cual iba a hacer el sistema RAG. Escogí ña documentación de la librería MLFlow ya que no es tan utilizada como FastAPI o similares. Después, procesé los documentos en crudo (data/raw). Como la documentación original está en .mdx, trae mucho ruido de React (etiquetas JSX, sentencias import/export, componentes visuales). Si indexaba eso tal cual, iba a meter mucha basura en los embeddings.

Cómo no sabía muy bien cómo realizar esta limpieza y no es información comprometida, utilicé el agente de Claude Code para que hiciera un archivo .py de limpieza: 

Protección del código (Enmascaramiento): Antes de borrar nada, el script detecta los bloques de código y los sustituye por unos caracteres ocultos de Unicode (ej. ). De esta forma, al pasar las expresiones regulares para borrar los import de React, no me cargo los import mlflow de los scripts de ejemplo. Al terminar la limpieza, el código vuelve a su sitio intacto.

Parseo de componentes y tablas: Se desenvuelven las etiquetas estructurales (como <Tabs>) re-indentando el texto para que Markdown no lo lea como código por error, y las tablas HTML complejas se aplanan a un formato lineal. Además, el frontmatter de cada archivo se extrae para usarlo luego como metadatos.

Breadcrumbs (Migas de pan): Implementé una función con una pila (stack) que va leyendo los encabezados (#, ##, ###) para saber la ruta exacta de cada párrafo dentro del documento.

## 3. Chunking y preparación para Qdrant
Con los textos limpios, diseñé el empaquetado final para la base de datos vectorial asegurando que no se pierda el contexto semántico:

Código indivisible: Programé un cortador que divide el texto en párrafos pero trata los bloques de código como unidades cerradas. Así evito que una función de Python se parta por la mitad.

Solape por tokens (Overlap): Voy agrupando los bloques calculando su tamaño con el tokenizador. Cuando supero el límite (max_tokens), cierro el chunk. Para no perder el hilo entre fragmentos, el nuevo chunk arranca haciendo un solape hacia atrás, incluyendo los últimos párrafos del bloque anterior.

Ensamblaje del contexto: Finalmente, a cada chunk de texto le concateno su breadcrumb justo antes del contenido. Todo este resultado lo exporto a un archivo documents.jsonl, obteniendo un registro limpio por cada fragmento con sus metadatos listos para indexar en Qdrant.