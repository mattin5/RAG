---
doc_id: "mlflow/docs/docs/genai/eval-monitor/scorers/llm-judge/rag/relevance"
source_path: "mlflow/docs/docs/genai/eval-monitor/scorers/llm-judge/rag/relevance.mdx"
title: "Answer and Context Relevance Judges"
---

# Answer and Context Relevance Judges

MLflow provides two built-in LLM judges to assess relevance in your LLM applications and AI agents. These judges help diagnose quality issues - if context isn't relevant, the generation step cannot produce a helpful response.

- `RelevanceToQuery`: Evaluates if your app's response directly addresses the user's input
- `RetrievalRelevance`: Evaluates if each document returned by your app's retriever(s) is relevant

## Usage Examples

### RelevanceToQuery Judge

This judge evaluates if your app's response directly addresses the user's input without deviating into unrelated topics.

You can invoke the judge directly with a single input for testing, or pass it to mlflow.genai.evaluate for running full evaluation on a dataset.

**Requirements:**

- **Trace requirements**: `inputs` and `outputs` must be on the Trace's root span

**Invoke directly**

```python
import mlflow
from mlflow.genai.scorers import RelevanceToQuery

assessment = RelevanceToQuery(name="my_relevance_to_query")(
    inputs={"question": "What is the capital of France?"},
    outputs="The capital of France is Paris.",
)
print(assessment)
```

**Invoke with evaluate()**

```python
import mlflow
from mlflow.genai.scorers import RelevanceToQuery

data = [
    {
        "inputs": {"question": "What is the capital of France?"},
        "outputs": "The capital of France is Paris.",
    }
]
result = mlflow.genai.evaluate(data=data, scorers=[RelevanceToQuery()])
```

### RetrievalRelevance Judge

This judge evaluates if each document returned by your app's retriever(s) is relevant to the input request. It evaluates each retriever span separately and returns a separate `Feedback` object for each retriever span in your trace.

**Requirements:**

- **Trace requirements**: The MLflow Trace must contain at least one span with `span_type` set to `RETRIEVER`

**Invoke directly**

```python
from mlflow.genai.scorers import RetrievalRelevance
import mlflow

# Get a trace from a previous run
trace = mlflow.get_trace("<your-trace-id>")

# Assess if each retrieved document is relevant
feedbacks = RetrievalRelevance()(trace=trace)
print(feedbacks)
```

**Invoke with evaluate()**

```python
import mlflow
from mlflow.genai.scorers import RetrievalRelevance

# Evaluate traces from previous runs
results = mlflow.genai.evaluate(
    data=traces,  # DataFrame or list containing trace data
    scorers=[RetrievalRelevance()],
)
```

**Tip**
For a complete RAG application example with these judges, see the [RAG Evaluation guide](/genai/eval-monitor/scorers/llm-judge/rag/).

## Interpret results

The judge returns a `Feedback` object containing:

- **value**: "yes" if context is relevant, "no" if not
- **rationale**: Explanation of why the judge found the context relevant or irrelevant
