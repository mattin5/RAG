---
doc_id: "mlflow/docs/docs/classic-ml/deep-learning/sentence-transformers/index"
source_path: "mlflow/docs/docs/classic-ml/deep-learning/sentence-transformers/index.mdx"
title: "MLflow Sentence Transformers Flavor"
description: "Log, version, and deploy Sentence Transformers models with MLflow for semantic embeddings and text similarity tasks."
---

# MLflow Sentence Transformers Flavor

The MLflow Sentence Transformers flavor provides integration with the [Sentence Transformers](https://www.sbert.net/) library for generating semantic embeddings from text.

## Installation

```bash
pip install 'mlflow[sentence-transformers]'
```

## Basic Usage

### Logging and Loading Models

```python
import mlflow
from sentence_transformers import SentenceTransformer

# Load and log a model
model = SentenceTransformer("all-MiniLM-L6-v2")

with mlflow.start_run():
    model_info = mlflow.sentence_transformers.log_model(
        model=model,
        name="model",
        input_example=["Sample text for inference"],
    )

# Load as native sentence transformer
loaded_model = mlflow.sentence_transformers.load_model(model_info.model_uri)
embeddings = loaded_model.encode(["Hello world", "MLflow is great"])

# Load as PyFunc
pyfunc_model = mlflow.pyfunc.load_model(model_info.model_uri)
result = pyfunc_model.predict(["Hello world", "MLflow is great"])
```

### Model Signatures

Define explicit signatures for production deployments:

```python
from mlflow.models import infer_signature

sample_texts = [
    "MLflow makes ML development easier",
    "Sentence transformers create embeddings",
]
sample_embeddings = model.encode(sample_texts)

signature = infer_signature(sample_texts, sample_embeddings)

with mlflow.start_run():
    mlflow.sentence_transformers.log_model(
        model=model,
        name="model",
        signature=signature,
        input_example=sample_texts,
    )
```

## Semantic Search

Build semantic search systems with tracking:

```python
import mlflow
import pandas as pd
from sentence_transformers import SentenceTransformer, util

documents = [
    "Machine learning is a subset of artificial intelligence",
    "Deep learning uses neural networks with multiple layers",
    "MLflow is an open-source AI engineering platform for agents, LLMs, and ML models",
]

with mlflow.start_run():
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Log model parameters
    mlflow.log_params({
        "model_name": "all-MiniLM-L6-v2",
        "embedding_dimension": model.get_sentence_embedding_dimension(),
        "corpus_size": len(documents),
    })

    # Encode corpus
    corpus_embeddings = model.encode(documents, convert_to_tensor=True)

    # Save corpus
    corpus_df = pd.DataFrame({"documents": documents})
    corpus_df.to_csv("corpus.csv", index=False)
    mlflow.log_artifact("corpus.csv")

    # Semantic search
    query = "What tools help with ML development?"
    query_embedding = model.encode(query, convert_to_tensor=True)
    results = util.semantic_search(query_embedding, corpus_embeddings, top_k=3)[0]

    # Log model
    mlflow.sentence_transformers.log_model(
        model=model,
        name="search_model",
        input_example=[query],
    )
```

## Fine-tuning

Track fine-tuning experiments:

```python
import mlflow
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

train_examples = [
    InputExample(texts=["Python programming", "Coding in Python"], label=0.9),
    InputExample(texts=["Machine learning model", "ML algorithm"], label=0.8),
    InputExample(texts=["Software development", "Cooking recipes"], label=0.1),
]

with mlflow.start_run():
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Log training parameters
    mlflow.log_params({
        "base_model": "all-MiniLM-L6-v2",
        "num_epochs": 3,
        "batch_size": 16,
        "learning_rate": 2e-5,
    })

    # Fine-tune
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
    train_loss = losses.CosineSimilarityLoss(model)

    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=3,
        warmup_steps=100,
    )

    # Log fine-tuned model
    mlflow.sentence_transformers.log_model(
        model=model,
        name="fine_tuned_model",
    )
```

## Tutorials
