---
doc_id: "mlflow/docs/docs/genai/eval-monitor/index"
source_path: "mlflow/docs/docs/genai/eval-monitor/index.mdx"
title: "LLM and Agent Evaluation"
description: "Systematically measure, improve, and monitor the quality of your agent and LLM applications with MLflow's built-in and custom scorers."
---

# Evaluating LLMs and Agents with MLflow

MLflow's evaluation and monitoring capabilities help you systematically measure, improve, and maintain the quality of your LLM applications and AI agents throughout their lifecycle from development through production.

A core tenet of MLflow's evaluation capabilities is **Evaluation-Driven Development**. This is an emerging practice to tackle the challenge of building high-quality LLM/Agentic applications. MLflow is an open source AI engineering platform that is designed to support this practice and help you quickly build production-quality AI agents and LLM applications.

## Key Capabilities

**Dataset Management**

#### Create and maintain a High-Quality Dataset

Before you can evaluate your LLM application or AI agent, you need test data. **Evaluation Datasets** provide a centralized repository for managing test cases, ground truth expectations, and evaluation data at scale.

Think of Evaluation Datasets as your "test database" - a single source of truth for all the data needed to evaluate your AI systems. They transform ad-hoc testing into systematic quality assurance.

[Learn more →](/genai/datasets)

![Trace Dataset](/images/llms/tracing/genai-trace-dataset.png)

**Human Feedback**

#### Track Annotation and Human Feedbacks

Human feedback is essential for building high-quality LLM applications and AI agents that meet user expectations. MLflow supports collecting, managing, and utilizing feedback from end-users and domain experts.

Feedbacks are attached to traces and recorded with metadata, including user, timestamp, revisions, etc.

[Learn more →](/genai/assessments/feedback)

![Trace Feedback](/images/llms/tracing/genai-human-feedback.png)

**LLM-as-a-Judge**

#### Scale Quality Assessment with Automation

Quality assessment is a critical part of building high-quality LLM applications and AI agents, however, it is often time-consuming and requires human expertise. LLMs are powerful tools to automate quality assessment.

MLflow offers various built-in [LLM-as-a-Judge](https://mlflow.org/llm-evaluation) scorers to help automate the process, as well as a flexible toolset to build your own LLM judges with ease.

[Learn more →](/genai/eval-monitor)

![Trace Evaluation](/images/llms/tracing/genai-trace-evaluation.png)

**Systematic Evaluation**

#### Evaluate and Enhance quality

Systematically assessing and improving the quality of LLM applications and AI agents is a challenge. MLflow provides a comprehensive set of tools to help you evaluate and enhance the quality of your applications.

Being the industry's most-trusted open source [AI engineering platform](https://mlflow.org/genai) for agents and LLM applications, MLflow provides a strong foundation for tracking your evaluation results and effectively collaborating with your team.

[Learn more →](/genai/eval-monitor/quickstart)

![Trace Evaluation](/images/llms/tracing/genai-evaluation-compare.png)

**Production Monitoring**

#### Monitor Applications in Production

Understanding and optimizing LLM application and AI agent performance is crucial for efficient operations. [MLflow Tracing](https://mlflow.org/llm-tracing) captures key metrics like latency and token usage at each step, as well as various quality metrics, helping you identify bottlenecks, monitor efficiency, and find optimization opportunities.

[Learn more →](/genai/tracing/prod-tracing)

![Monitoring](/images/llms/tracing/genai-monitoring.png)

## Running an Evaluation

Each evaluation is defined by three components:

| Component | Example |
| --- | --- |
| Dataset Inputs &amp; expectations (and optionally pre-generated outputs and traces) | \[ {"inputs": {"question": "2+2"}, "expectations": {"answer": "4"}}, {"inputs": {"question": "2+3"}, "expectations": {"answer": "5"}} \] |
| Scorer Evaluation criteria | @scorer def exact_match(expectations, outputs): return expectations == outputs |
| Predict Function Generates outputs for the dataset | def predict_fn(question: str) -> str: response = client.chat.completions.create( model="gpt-4o-mini", messages=\[{"role": "user", "content": question}\] ) return response.choices[0].message.content |

The following example shows a simple evaluation of a dataset of questions and expected answers.

```python
import os
import openai
import mlflow
from mlflow.genai.scorers import Correctness, Guidelines

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 1. Define a simple QA dataset
dataset = [
    {
        "inputs": {"question": "Can MLflow manage prompts?"},
        "expectations": {"expected_response": "Yes!"},
    },
    {
        "inputs": {"question": "Can MLflow create a taco for my lunch?"},
        "expectations": {"expected_response": "No, unfortunately, MLflow is not a taco maker."},
    },
]


# 2. Define a prediction function to generate responses
def predict_fn(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": question}]
    )
    return response.choices[0].message.content


# 3.Run the evaluation
results = mlflow.genai.evaluate(
    data=dataset,
    predict_fn=predict_fn,
    scorers=[
        # Built-in LLM judge
        Correctness(),
        # Custom criteria using LLM judge
        Guidelines(name="is_english", guidelines="The answer must be in English"),
    ],
)
```

## Review the results

Open the MLflow UI to review the evaluation results. You can use the following command to start the UI:

```bash
mlflow server --port 5000
```

You should see a new evaluation run is created under the "Runs" tab. Click on the run name to view the evaluation results.
