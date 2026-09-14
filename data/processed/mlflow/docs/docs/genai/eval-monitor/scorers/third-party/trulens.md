---
doc_id: "mlflow/docs/docs/genai/eval-monitor/scorers/third-party/trulens"
source_path: "mlflow/docs/docs/genai/eval-monitor/scorers/third-party/trulens.mdx"
title: "TruLens"
---

# TruLens

[TruLens](https://www.trulens.org/) is an evaluation and observability framework for LLM applications that provides feedback functions for RAG systems and agent trace analysis. MLflow's TruLens integration allows you to use TruLens feedback functions as MLflow scorers, including benchmarked [goal-plan-action alignment evaluations](https://arxiv.org/abs/2510.08847) for agent traces.

## Prerequisites

TruLens scorers require the `trulens` and `trulens-providers-litellm` packages:

```bash
pip install trulens trulens-providers-litellm
```

## Quick Start

**Invoke directly**

```python
from mlflow.genai.scorers.trulens import Groundedness

scorer = Groundedness(model="openai:/gpt-5-mini")
feedback = scorer(
    inputs="What is MLflow?",
    outputs="MLflow is an open-source AI engineering platform for agents and LLMs.",
    expectations={
        "context": "MLflow is an ML platform for experiment tracking and model deployment."
    },
)

print(feedback.value)  # "yes" or "no"
print(feedback.metadata["score"])  # 0.85
```

**Invoke with evaluate()**

```python
import mlflow
from mlflow.genai.scorers.trulens import Groundedness, AnswerRelevance

eval_dataset = [
    {
        "inputs": {"query": "What is MLflow?"},
        "outputs": "MLflow is an open-source AI engineering platform for agents and LLMs.",
        "expectations": {
            "context": "MLflow is an ML platform for experiment tracking and model deployment."
        },
    },
    {
        "inputs": {"query": "How do I track experiments?"},
        "outputs": "You can use mlflow.start_run() to begin tracking experiments.",
        "expectations": {
            "context": "MLflow provides APIs like mlflow.start_run() for experiment tracking."
        },
    },
]

results = mlflow.genai.evaluate(
    data=eval_dataset,
    scorers=[
        Groundedness(model="openai:/gpt-5-mini"),
        AnswerRelevance(model="openai:/gpt-5-mini"),
    ],
)
```

## Available TruLens Scorers

TruLens scorers are organized into categories based on their evaluation focus:

### RAG (Retrieval-Augmented Generation) Metrics

Evaluate retrieval quality and answer generation in RAG systems:

| Scorer                                                                                 | What does it evaluate?                                | TruLens Docs                                                                                                                   |
| -------------------------------------------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Groundedness         | Is the response grounded in the provided context?     | [Link](https://www.trulens.org/reference/trulens/feedback/#trulens.feedback.LLMProvider.groundedness_measure_with_cot_reasons) |
| ContextRelevance | Is the retrieved context relevant to the input query? | [Link](https://www.trulens.org/reference/trulens/feedback/#trulens.feedback.LLMProvider.context_relevance_with_cot_reasons)    |
| AnswerRelevance   | Is the output relevant to the input query?            | [Link](https://www.trulens.org/reference/trulens/feedback/#trulens.feedback.LLMProvider.relevance_with_cot_reasons)            |
| Coherence               | Is the output coherent and logically consistent?      | [Link](https://www.trulens.org/reference/trulens/feedback/#trulens.feedback.LLMProvider.coherence_with_cot_reasons)            |

### Agent Trace Metrics

Evaluate AI agent execution traces using [goal-plan-action alignment](https://arxiv.org/abs/2510.08847):

| Scorer                                                                                       | What does it evaluate?                                              | TruLens Docs                                                                                                                   |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| LogicalConsistency   | Is the agent's reasoning logically consistent throughout execution? | [Link](https://www.trulens.org/reference/trulens/feedback/#trulens.feedback.LLMProvider.logical_consistency_with_cot_reasons)  |
| ExecutionEfficiency | Does the agent take an optimal path without unnecessary steps?      | [Link](https://www.trulens.org/reference/trulens/feedback/#trulens.feedback.LLMProvider.execution_efficiency_with_cot_reasons) |
| PlanAdherence             | Does the agent follow its stated plan during execution?             | [Link](https://www.trulens.org/reference/trulens/feedback/#trulens.feedback.LLMProvider.plan_adherence_with_cot_reasons)       |
| PlanQuality                 | Is the agent's plan well-structured and appropriate for the goal?   | [Link](https://www.trulens.org/reference/trulens/feedback/#trulens.feedback.LLMProvider.plan_quality_with_cot_reasons)         |
| ToolSelection             | Does the agent choose the appropriate tools for each step?          | [Link](https://www.trulens.org/reference/trulens/feedback/#trulens.feedback.LLMProvider.tool_selection_with_cot_reasons)       |
| ToolCalling                 | Does the agent invoke tools with correct parameters?                | [Link](https://www.trulens.org/reference/trulens/feedback/#trulens.feedback.LLMProvider.tool_calling_with_cot_reasons)         |

Agent trace scorers require a `trace` argument and evaluate the full execution trace:

```python
import mlflow
from mlflow.genai.scorers.trulens import LogicalConsistency, ToolSelection

traces = mlflow.search_traces(experiment_ids=["1"])
results = mlflow.genai.evaluate(
    data=traces,
    scorers=[
        LogicalConsistency(model="openai:/gpt-5-mini"),
        ToolSelection(model="openai:/gpt-5-mini"),
    ],
)
```

## Creating Scorers by Name

You can also create TruLens scorers dynamically using get_scorer:

```python
from mlflow.genai.scorers.trulens import get_scorer

# Create scorer by name
scorer = get_scorer(
    metric_name="Groundedness",
    model="openai:/gpt-5-mini",
)

feedback = scorer(
    inputs="What is MLflow?",
    outputs="MLflow is a platform for ML workflows.",
    expectations={"context": "MLflow is an ML platform."},
)
```

## Configuration

TruLens scorers accept common parameters for controlling evaluation behavior:

```python
from mlflow.genai.scorers.trulens import Groundedness, ContextRelevance

# Common parameters
scorer = Groundedness(
    model="openai:/gpt-5-mini",  # Model URI (also supports "databricks", "databricks:/endpoint", etc.)
    threshold=0.7,  # Pass/fail threshold (0.0-1.0, scorer passes if score >= threshold)
)

# Default threshold is 0.5
scorer = ContextRelevance(model="openai:/gpt-5-mini")
```

Refer to the [TruLens documentation](https://www.trulens.org/) for additional details on feedback functions and advanced usage.
