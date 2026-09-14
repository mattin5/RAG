# MLflow LangChain Autologging

Este documento existe para el test del chunker: tiene bloques de código con
líneas que empiezan por `#`, que es justo lo que la detección de encabezados
confundía con títulos de sección.

## Autologging

Activa el autologging y ejecuta tu cadena:

```python
import mlflow

mlflow.langchain.autolog()

# Your LangChain model code here
...

# Load the model
model = mlflow.langchain.load_model(model_uri)
```

El bloque de arriba tiene dos comentarios que empiezan por `#` y una línea con
tres puntos, que antes se quedaba como una sección entera.

## Notebook

```python
# %%writefile agent.py
import mlflow


# Define the agent
class Agent:
    pass
```

## Variables de entorno

Aquí el cercado es de tildes, no de backticks:

~~~bash
# export MLFLOW_TRACKING_URI
export MLFLOW_TRACKING_URI=http://localhost:5000
export MLFLOW_EXPERIMENT_NAME=demo
~~~

## Documentación anidada

Un bloque de cuatro backticks que contiene otro de tres dentro:

````markdown
# Este título está dentro de un ejemplo de markdown

```python
# y este comentario también
print("hola")
```
````

## Bloque sin cerrar

El fichero se acaba sin cerrar este bloque:

```python
# Este comentario está dentro de un bloque que nadie cierra
config = {"tracking_uri": "http://localhost:5000"}
