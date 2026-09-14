---
doc_id: "mlflow/docs/docs/genai/demo"
source_path: "mlflow/docs/docs/genai/demo.mdx"
title: "Live Demo"
description: "Explore MLflow's publicly hosted demo UI at demo.mlflow.org with pre-loaded sample data — no setup required."
---

# Live Demo

**[demo.mlflow.org](https://demo.mlflow.org/#/experiments/1)** is a publicly hosted MLflow instance pre-loaded with sample data. It's the fastest way to explore the MLflow UI without any local setup.

## What's in the demo?

The demo environment includes sample data across four areas:

## Run the demo locally

Want to explore the same demo data on your own MLflow instance with write access? You can launch it in seconds using the `mlflow demo` command:

```bash
uvx mlflow demo
```

This starts a local MLflow server pre-loaded with the same sample data, giving you full read-write access to experiment and customize.

Alternatively, if you already have a local MLflow instance running, click the **Explore Demo** button in the banner at the top of the home page to load sample data directly into your instance.

## Next steps

Once you've explored the demo, get started with your own MLflow environment:

- [Set Up MLflow Server](/genai/getting-started/connect-environment) — connect to a local or hosted MLflow instance
- [Start Tracing](/genai/tracing/quickstart) — instrument your LLM app and capture your first traces
- [Evaluate LLMs and Agents](/genai/eval-monitor/quickstart/) — run systematic evaluations with LLM judges
