---
doc_id: "mlflow/docs/docs/genai/getting-started/connect-environment"
source_path: "mlflow/docs/docs/genai/getting-started/connect-environment.mdx"
title: "Set Up MLflow Server"
description: "Learn how to setup the MLflow server for LLM application and AI agent development."
---

# Set Up MLflow Server

**[MLflow Assistant]**
Need help with this setup? Try [MLflow Assistant](/genai/getting-started/try-assistant) - a powerful AI assistant that understands your codebase and can set up MLflow for you.

MLflow is open source, and you can set up the MLflow server using either `pip` or `docker`.

Before you can leverage MLflow for your LLM application and AI agent development, you must first start the MLflow server.

This will start the server at port 5000 on your local machine and you can access the MLflow web UI at http://localhost:5000.

If you are looking for more guidance about self-hosting the MLflow server, please see the [Self-Hosting Guide](/self-hosting) for more details.

**Info**

If you are using MLflow on Databricks, please visit [this](https://docs.databricks.com/aws/en/mlflow3/genai/getting-started/) for environment setup instructions specific to Databricks.

## Next Step

Now that you have started the MLflow server, let's start tracing your LLM application or AI agent.

Follow [this quickstart](/genai/tracing/quickstart) to send your LLM application or AI agent traces to the MLflow server.
