---
doc_id: "mlflow/docs/docs/classic-ml/deep-learning/transformers/index"
source_path: "mlflow/docs/docs/classic-ml/deep-learning/transformers/index.mdx"
title: "MLflow Transformers Flavor"
---

# MLflow Transformers Flavor

The MLflow Transformers flavor provides native integration with the [Hugging Face Transformers](https://huggingface.co/docs/transformers/index) library, supporting model logging, loading, and inference for NLP, audio, vision, and multimodal tasks.

## Key Features

- **Pipeline and Component Logging**: Save complete pipelines or individual model components
- **PyFunc Integration**: Deploy models with standardized inference interfaces
- **PEFT Support**: Native support for parameter-efficient fine-tuning (LoRA, QLoRA, etc.)
- **Prompt Templates**: Save and manage prompt templates with pipelines
- **Automatic Metadata Logging**: Model cards and metadata logged automatically
- **Flexible Inference Configuration**: Customize model behavior via `model_config` and signature parameters

## Installation

```bash
pip install mlflow transformers
```

## Basic Usage

### Logging a Pipeline

```python
import mlflow
from transformers import pipeline

# Create a text generation pipeline
text_gen = pipeline("text-generation", model="gpt2")

# Log the pipeline
with mlflow.start_run():
    mlflow.transformers.log_model(
        transformers_model=text_gen,
        name="model",
    )
```

### Loading and Inference

```python
# Load as native transformers
model = mlflow.transformers.load_model("runs:/<run_id>/model")
result = model("Hello, how are you?")

# Load as PyFunc
pyfunc_model = mlflow.pyfunc.load_model("runs:/<run_id>/model")
result = pyfunc_model.predict("Hello, how are you?")
```

## Autologging with HuggingFace Trainer

When using the HuggingFace `Trainer` class for fine-tuning, you can enable automatic logging to MLflow by setting `report_to="mlflow"` in the `TrainingArguments`:

```python
from transformers import TrainingArguments, Trainer

training_args = TrainingArguments(
    output_dir="./results",
    report_to="mlflow",  # Enable MLflow logging
    # ... other training arguments
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    # ... other trainer arguments
)

trainer.train()
```

This automatically logs training metrics, hyperparameters, and model checkpoints to your active MLflow run.

## Tutorials

## Important Considerations

### PyFunc Limitations

- Not all pipeline types are supported for PyFunc inference
- Some outputs (e.g., additional scores, references) may not be captured
- Audio and text LLMs are supported; vision and multimodal models require native loading
- See the [guide](/ml/deep-learning/transformers/guide#loading-a-transformers-model-as-a-python-function) for supported pipeline types

### Input/Output Types

Input and output formats for PyFunc may differ from native pipelines. Ensure compatibility with your data processing workflows.

### Model Configuration

Parameters in `ModelSignature` override those in `model_config` when both are provided.

## Working with Large Models

For models with billions of parameters, MLflow provides optimization techniques to reduce memory usage and speed up logging. See the [large models guide](/ml/deep-learning/transformers/large-models).

## Tasks

The `task` parameter determines input/output format. MLflow supports native Transformers tasks plus advanced tasks like `llm/v1/chat` and `llm/v1/completions` for OpenAI-compatible inference. See the [tasks guide](/ml/deep-learning/transformers/task).
