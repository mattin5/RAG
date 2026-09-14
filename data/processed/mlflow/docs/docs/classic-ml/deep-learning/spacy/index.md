---
doc_id: "mlflow/docs/docs/classic-ml/deep-learning/spacy/index"
source_path: "mlflow/docs/docs/classic-ml/deep-learning/spacy/index.mdx"
title: "MLflow spaCy Integration"
description: "Integrate spaCy NLP pipelines with MLflow for model logging, experiment tracking, versioning, and deployment."
---

# MLflow spaCy Integration

## Introduction

**spaCy** is an industrial-strength natural language processing library designed for production use. It provides pre-trained models and efficient processing pipelines for tasks like named entity recognition, part-of-speech tagging, and text classification.

MLflow's spaCy integration provides model logging, versioning, and deployment capabilities for NLP workflows.

## Model Logging

Log spaCy models to MLflow:

```python
import mlflow
import spacy

# Load or train your spaCy model
nlp = spacy.load("en_core_web_sm")

# Log to MLflow
model_info = mlflow.spacy.log_model(nlp, name="spacy_model")
```

## Custom Training with MLflow

Track custom spaCy training with MLflow:

```python
import mlflow
import spacy
from spacy.training import Example

# Load base model
nlp = spacy.blank("en")
nlp.add_pipe("ner")

# Sample training data
TRAIN_DATA = [
    ("Apple is a tech company", {"entities": [(0, 5, "ORG")]}),
    ("Google acquired YouTube", {"entities": [(0, 6, "ORG"), (16, 23, "PRODUCT")]}),
]

# Convert to Examples
examples = [Example.from_dict(nlp.make_doc(text), annotations) for text, annotations in TRAIN_DATA]

# Initialize and train
optimizer = nlp.initialize()

with mlflow.start_run():
    mlflow.log_params({
        "model": "blank_en",
        "pipeline": "ner",
    })

    for epoch in range(10):
        losses = {}
        for example in examples:
            nlp.update([example], sgd=optimizer, losses=losses)

        mlflow.log_metric("loss", losses["ner"], step=epoch)

    # Log the trained model
    mlflow.spacy.log_model(nlp, name="custom_ner_model")
```

## Model Loading

Load spaCy models from MLflow:

```python
import mlflow

# Load as spaCy model
nlp = mlflow.spacy.load_model("models:/<model_id>")
doc = nlp("Apple is looking at buying a startup")

# Load as PyFunc for deployment
predictor = mlflow.pyfunc.load_model("models:/<model_id>")
predictions = predictor.predict(["Text to process"])
```
