---
doc_id: "mlflow/docs/docs/genai/flavors/index"
source_path: "mlflow/docs/docs/genai/flavors/index.mdx"
title: "Agent Packaging & Deployment"
description: "Package and deploy LangChain, LangGraph, LlamaIndex, and custom agents with MLflow's native flavors."
---

# MLflow LLM and AI Agent Packaging Integrations

MLflow 3 delivers built-in support for packaging and deploying applications written with the LLM and AI agent frameworks you depend on. Whether you're orchestrating chains with LangChain or LangGraph, indexing documents in LlamaIndex, wiring up agent patterns via ChatModel and ResponseAgent, or rolling your own with a PythonModel, MLflow provides native packaging and deployment APIs ("flavors") to streamline your path to production.

**[OpenAI Model Logging Deprecated]**
The `mlflow.openai.log_model()` API has been deprecated. If you were using it to save prompts, please migrate to the [MLflow Prompt Registry](/genai/prompt-registry), which provides superior versioning, aliasing, lineage tracking, and collaboration features for managing prompts separately from models.

## Why MLflow Integrations?

By choosing MLflow's native flavors, you gain end-to-end visibility and control without swapping tools:

- **Unified Tracking & Models**: All calls, parameters, artifacts, and prompt templates become tracked entities within MLflow Experiments. Serialized application code becomes a LoggedModel—viewable and referenceable within the MLflow UI and APIs.
- **Zero-Boilerplate Setup**: A single `mlflow.<flavor>.log_model(...)` call (or one line of auto-instrumentation) wires into your existing code.
- **Reproducibility by Default**: MLflow freezes your prompt template, application parameters, framework versions, and dependencies so you can reproduce any result, anytime.
- **Seamless Transition to Serving**: Each integration produces a standardized MLflow Model you can deploy for batch scoring or real-time inference with `mlflow models serve`.

## Start Integrating in Minutes

Before you begin, make sure you have:

- Python 3.9+ and MLflow 3.x installed (`pip install --upgrade mlflow`)
- Credentials or API keys for your chosen provider (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)
- An MLflow Tracking Server (local or remote)

**[Ready to dive in?]**
Pick your integration from the list below and follow the concise guide—each one gets you up and running in under 10 minutes.

## Integration Guides

MLflow supports first-party flavors for these LLM and AI agent frameworks and patterns. Click to explore:

## Continue Your Journey

Once your integration is in place, take advantage of MLflow's full [LLMOps](https://mlflow.org/llmops) platform:

### 🔍 Observability & Debugging

- [Tracing & Observability](/genai/tracing)

### 🧪 Evaluation & QA

- [LLM Evaluation Framework](https://docs.databricks.com/aws/en/mlflow3/genai/getting-started/eval.html)

### 🚀 Deployment & Monitoring

- [Prompt Engineering UI](/genai/prompt-registry/prompt-engineering)
- [Application Serving](/genai/serving)
