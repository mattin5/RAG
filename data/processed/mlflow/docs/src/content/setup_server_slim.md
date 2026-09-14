---
doc_id: "mlflow/docs/src/content/setup_server_slim"
source_path: "mlflow/docs/src/content/setup_server_slim.mdx"
title: "setup_server_slim"
---

**Local (pip)**

If you have a local Python environment >= 3.10, you can start the MLflow server locally using the `mlflow` CLI command.

```bash
mlflow server
```

**Local (docker)**

MLflow also provides a Docker Compose file to start a local MLflow server with a postgres database and a minio server.

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/mlflow/mlflow.git
cd mlflow
git sparse-checkout set docker-compose
cd docker-compose
cp .env.dev.example .env
docker compose up -d
```

Refer to the [instruction](https://github.com/mlflow/mlflow/tree/master/docker-compose/README.md) for more details, e.g., overriding the default environment variables.
