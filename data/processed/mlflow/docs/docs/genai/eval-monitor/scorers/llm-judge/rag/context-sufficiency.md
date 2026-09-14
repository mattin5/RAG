---
doc_id: "mlflow/docs/docs/genai/eval-monitor/scorers/llm-judge/rag/context-sufficiency"
source_path: "mlflow/docs/docs/genai/eval-monitor/scorers/llm-judge/rag/context-sufficiency.mdx"
title: "RetrievalSufficiency judge"
---

# RetrievalSufficiency judge

The `RetrievalSufficiency` judge evaluates whether the retrieved context (from RAG applications, agents, or any system that retrieves documents) contains enough information to adequately answer the user's request based on the ground truth label provided as `expected_facts` or an `expected_response`.

This built-in LLM judge is designed for evaluating RAG systems where you need to ensure that your retrieval process is providing all necessary information.

## Usage examples

The `RetrievalSufficiency` judge can be invoked directly for single trace assessment or used with MLflow's evaluation framework for batch evaluation.

**Requirements:**

- **Trace requirements**:
  - The MLflow Trace must contain at least one span with `span_type` set to `RETRIEVER`
  - `inputs` and `outputs` must be on the Trace's root span

- **Ground-truth labels**: Required - must provide either `expected_facts` or `expected_response` in the expectations dictionary

**Invoke directly**

```python
from mlflow.genai.scorers import RetrievalSufficiency
import mlflow

# Get a trace from a previous run
trace = mlflow.get_trace("<your-trace-id>")

# Assess if the retrieved context is sufficient for the expected facts
feedback = RetrievalSufficiency()(
    trace=trace,
    expectations={
        "expected_facts": [
            "MLflow is an open source AI engineering platform",
            "Features include observability",
            "Features include evaluation",
            "Features include prompt management",
            "Features include AI Gateway",
        ]
    },
)
print(feedback)
```

**Invoke with evaluate()**

```python
import mlflow
from mlflow.genai.scorers import RetrievalSufficiency

# Evaluate traces from previous runs with ground truth expectations
results = mlflow.genai.evaluate(
    data=eval_dataset,  # Dataset with trace data and expected_facts
    scorers=[RetrievalSufficiency()],
)
```

**Tip**
For a complete RAG application example with this judge, see the [RAG Evaluation guide](/genai/eval-monitor/scorers/llm-judge/rag/).

## Interpret results

The RetrievalSufficiency judge evaluates each retriever span separately and returns a separate Feedback object for each retriever span in your trace. Each `Feedback` object contains:

- **value**: "yes" if the retrieved documents contain all the information needed to generate the expected facts, "no" if the retrieved documents are missing critical information
- **rationale**: Explanation of which expected facts the context covers or lacks

This helps you identify when your retrieval system is failing to fetch all necessary information, which is a common cause of incomplete or incorrect responses in RAG applications.
