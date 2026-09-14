---
doc_id: "mlflow/docs/src/content/setup_server"
source_path: "mlflow/docs/src/content/setup_server.mdx"
title: "setup_server"
---

**Local (uv)**

Install the Python package manager [uv](https://docs.astral.sh/uv/getting-started/installation/)
(that will also install [`uvx` command](https://docs.astral.sh/uv/guides/tools/) to invoke Python tools without installing them).

Start a MLflow server locally.

```shell
uvx mlflow server
```

**Info**
See [Secure Installs](/self-hosting/security/secure-installs) to learn how to pin dependencies to known good versions using hash checking and upload-time filtering.

**Local (pip)**

**Python Environment**: Python 3.10+

Install the `mlflow` Python package via `pip` and start a MLflow server locally.

```shell
pip install --upgrade mlflow
mlflow server
```

**Info**
See [Secure Installs](/self-hosting/security/secure-installs) to learn how to pin dependencies to known good versions using hash checking and upload-time filtering.

**Local (docker)**

MLflow provides a Docker Compose file to start a local MLflow server with a PostgreSQL database and a MinIO server.

```shell
git clone --depth 1 --filter=blob:none --sparse https://github.com/mlflow/mlflow.git
cd mlflow
git sparse-checkout set docker-compose
cd docker-compose
cp .env.dev.example .env
docker compose up -d
```

Refer to the [instruction](https://github.com/mlflow/mlflow/tree/master/docker-compose/README.md) for more details (e.g., overriding the default environment variables).
