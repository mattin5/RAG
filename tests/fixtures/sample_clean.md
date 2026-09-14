# MLflow Keras 3.0 Integration

## Introduction

**Keras 3.0** is a high-level neural networks API that runs on TensorFlow, JAX, and PyTorch backends.

## Autologging

**Warning**
Autologging requires Keras 3.0 or above.

Enable it with `mlflow.tensorflow.autolog`, or take control with
`MlflowCallback`:

**Python**

#### Enable autologging

Set the tracking URI and let MLflow log the run for you:

```python
import mlflow
from tensorflow import keras

mlflow.tensorflow.autolog()
```

- **Metrics**: logged every epoch
- **Artifacts**: the serialized model

**Shell**

```bash
export MLFLOW_TRACKING_URI="http://localhost:5000"
export MLFLOW_EXPERIMENT_NAME="keras"
```

### 3. Check the results

Open the MLflow UI and compare the runs.

## Supported output types

| Pipeline Type | Output Type |
| --- | --- |
| Text Classification | pd.DataFrame (dtypes: {'label': str}) |
| Translation | List[str] |
