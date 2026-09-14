---
doc_id: "mlflow/docs/docs/genai/eval-monitor/scorers/llm-judge/response-quality/correctness"
source_path: "mlflow/docs/docs/genai/eval-monitor/scorers/llm-judge/response-quality/correctness.mdx"
title: "Correctness Judge"
---

# Correctness Judge

The `Correctness` judge assesses whether your LLM application or AI agent's response is factually correct by comparing it against provided ground truth information (`expected_facts` or `expected_response`).

This built-in LLM judge is designed for evaluating application responses against known correct answers.

## Usage examples

**Invoke directly**

```python
from mlflow.genai.scorers import Correctness

correctness_judge = Correctness()

# Example 1: Response contains expected facts
feedback = correctness_judge(
    inputs={"request": "What is MLflow?"},
    outputs={"response": "MLflow is an open-source AI engineering platform for agents and LLMs."},
    expectations={
        "expected_facts": [
            "MLflow is open-source",
            "MLflow is an AI engineering platform",
        ]
    },
)

# Example 2: Response missing or contradicting facts
feedback = correctness_judge(
    inputs={"request": "When was MLflow released?"},
    outputs={"response": "MLflow was released in 2017."},
    expectations={"expected_facts": ["MLflow was released in June 2018"]},
)

# Example 3: Using expected_response instead of expected_facts
feedback = correctness_judge(
    inputs={"request": "What is the capital of France?"},
    outputs={"response": "The capital of France is Paris."},
    expectations={"expected_response": "Paris is the capital of France."},
)
```

**Invoke with evaluate()**

```python
import mlflow
from mlflow.genai.scorers import Correctness

# Create evaluation dataset with ground truth
eval_dataset = [
    # Example 1: Response contains expected facts
    {
        "inputs": {"request": "What is MLflow?"},
        "outputs": {
            "response": "MLflow is an open-source AI engineering platform for agents and LLMs."
        },
        "expectations": {
            "expected_facts": [
                "MLflow is open-source",
                "MLflow is an AI engineering platform",
            ]
        },
    },
    # Example 2: Response missing or contradicting facts
    {
        "inputs": {"request": "When was MLflow released?"},
        "outputs": {"response": "MLflow was released in 2017."},
        "expectations": {"expected_facts": ["MLflow was released in June 2018"]},
    },
    # Example 3: Using expected_response instead of expected_facts
    {
        "inputs": {"request": "What is the capital of France?"},
        "outputs": {"response": "The capital of France is Paris."},
        "expectations": {"expected_response": "Paris is the capital of France."},
    },
]

# Run evaluation with Correctness judge
eval_results = mlflow.genai.evaluate(
    data=eval_dataset,
    scorers=[
        Correctness(
            model="openai:/gpt-4o-mini",  # Optional.
        )
    ],
)
```

**Tip**
Use `expected_facts` rather than `expected_response` for more flexible evaluation - the response doesn't need to match word-for-word, just contain the key facts.

## Interpret results

The judge returns a Feedback object with:

- **value**: "yes" if response is correct, "no" if incorrect
- **rationale**: Detailed explanation of which facts are supported or missing
