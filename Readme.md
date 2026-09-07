# PROYECTO RAG CON DOCUMENTACIÓN MLFLOW
1. Primeros pasos:
- Entender genai:
Crear el ApiKey, y hacer las primeraas llamadas para obtener las primeras interacciones. Tras eso, ver la disponiblidad de modelos que hay para el plan que uso y entender las limitaciones de uso de cada modelo. Como las limitaciones son por X llamdas/minuto, no me condiciona tanto porque serán llamadas más puntuales. Aún así, detecto errores como `503 UNAVAILABLE`. Para solucionarlo, hago varias iteraciones con tiempo de espera entremedio para ver si se libera el modelo, y si no, cambia de modelo hasta obtener respuesta. 
- Encontrar una api para transcribir
Tras buscar información sobre apis y librerías que se usan para transcribir, como los videos que voy a usar son de Youtube y tienen subtitulos generados automáticamente, no tengo que usar Whisper o alguna parecida. Probar las primeras transcripciones, cambios de parámetros como idioma...
- Seleccionar cómo quiero guardar la información


- Hacer la primera cadena
video -> transcripción -> Gemini -> información relevante en formato deseado 