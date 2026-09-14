---
doc_id: "mlflow/docs/docs/quickstart_drilldown/index"
source_path: "mlflow/docs/docs/quickstart_drilldown/index.mdx"
title: "Quickstart Options and Troubleshooting"
description: "Customize your MLflow installation, configure tracking URIs, set up remote servers, and troubleshoot common setup issues."
---

# Quickstart options and troubleshooting

## Customize and troubleshoot MLflow installation {#quickstart_drilldown_install}

### Python library options

Rather than the default MLflow library, you can install the following variations:

| **Name** | **`pip install` command** | **Description** |
| --- | --- | --- |
| mlflow-skinny | `pip install mlflow-skinny` | Lightweight MLflow package without SQL storage, server, UI, or data science dependencies. |
| mlflow[extras] | `pip install 'mlflow[extras]'` | MLflow package with all dependencies needed to run various MLflow flavors. These dependencies are listed in [this document](https://github.com/mlflow/mlflow/blob/master/requirements/extra-ml-requirements.txt). |
| In-development version | `pip install git+https://github.com/mlflow/mlflow.git@master` | This is the latest version of MLflow, which may be useful for getting hot-fixes or new features. |

### Python and Mac OS X

We strongly recommend using a virtual environment manager on Macs. We always recommend
using virtual environments, but they are especially important on Mac OS X because the system
`python` version varies depending on the installation and whether you've installed the Xcode
command line tools. The default environment manager for MLflow is `virtualenv`.
Other popular options are `conda` and `venv`.

### Python

We release MLflow on:

- PyPI (`pip install mlflow`)
- conda-forge (`conda install -c conda-forge mlflow`)

### R and Java

We release MLflow on:

- CRAN (`install.packages("mlflow")`)
- Maven Central (`mlflow-client`, `mlflow-parent`, `mlflow-spark`)

For R, see installing MLflow for R.
For Java, see Java API.

## Save and serve models {#quickstart_drilldown_log_and_load_model}

MLflow includes a generic `MLmodel` format for saving **models** from a variety of tools in diverse
**flavors**. For example, many models can be served as Python functions, so an `MLmodel` file can
declare how each model should be interpreted as a Python function in order to let various tools
serve it. MLflow also includes tools for running such models locally and exporting them to Docker
containers or commercial serving platforms.

To illustrate this functionality, the `mlflow.sklearn` flavor can log scikit-learn models as
MLflow artifacts and then load them again for serving. There is an example training application in
[sklearn_logistic_regression/train.py](https://github.com/mlflow/mlflow/tree/master/examples/sklearn_logistic_regression).
To run it, switch to the MLflow repository root and run:

```bash
python examples/sklearn_logistic_regression/train.py
```

When you run the example, it outputs an MLflow run ID for that experiment. If you look at the
`mlflow server`, you will also see that the run saved a **model** folder containing an `MLmodel`
description file and a pickled scikit-learn model. You can pass the run ID and the path of the model
within the artifacts directory (here **model/**) to various tools. For example, MLflow includes a
simple REST server for python-based models:

```bash
mlflow models serve -m --env-manager local runs:/<RUN_ID>/model
```

**Note**
By default the server runs on port 5000. If that port is already in use, use the `--port` option to
specify a different port. For example: `mlflow models serve -m runs:/<RUN_ID>/model --port 1234`

Once you have started the server, you can pass it some sample data and see the
predictions.

The following example uses `curl` to send a JSON-serialized pandas DataFrame with the `split`
orientation to the model server. For more information about the input data formats accepted by
the pyfunc model server, see the [MLflow deployment tools documentation](/deployment/deploy-model-locally).

```bash
curl -d '{"dataframe_split": {"columns": ["x"], "data": [[1], [-1]]}}' -H 'Content-Type: application/json' -X POST localhost:5000/invocations
```

which returns:

```bash
[1, 0]
```

For more information, see [MLflow Models](/model).
