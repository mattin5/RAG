---
doc_id: "mlflow/docs/docs/genai/concepts/feedback"
source_path: "mlflow/docs/docs/genai/concepts/feedback.mdx"
title: "Feedback Concepts"
description: "Learn about MLflow Feedback for capturing quality assessments of LLM and AI agent outputs from automated and human sources."
---

# Feedback Concepts

## What is Feedback?

**Feedback** in MLflow represents the result of any quality assessment performed on your LLM application or AI agent outputs. It provides a standardized way to capture evaluations, whether they come from automated systems, LLM judges, or human reviewers.

Feedback serves as the bridge between running your application and understanding its quality, enabling you to systematically track performance across different dimensions like correctness, relevance, safety, and adherence to guidelines.

## Core Structure

Feedback is often created by different sources, such as human annotators, LLM judges, or real user's feedback in the application. The `Feedback` object in MLflow is a standard container for storing these signals along with metadata to track
how they are created. Feedbacks are associated with a Trace, or a particular Span in the Trace.

## Feedback Object Schema

| Field                 | Type                        | Description                                                                                                                                                                                                                                                                                                                                                                                             |
| --------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                | `str`                       | A string identifying the specific quality aspect being assessed                                                                                                                                                                                                                                                                                                                                         |
| `value`               | `Any`                       | The actual feedback value, which can be

 Numeric scores (e.g., `0.0` to `1.0`, `1` to `5`)Boolean values (`True`/`False`)Categorical labels (e.g., `"PASS"`, `"FAIL"`, `"EXCELLENT"`)Structured data (e.g., `{"score": 0.8, "confidence": 0.9}`)                                                                                                 |
| `rationale`           | `str`                       | A string explaining why the feedback is given to the trace.                                                                                                                                                                                                                                                                                                                                             |
| `source`              | `AssessmentSource`          | The source of the feedback, composed of the type of the source and ID.

 `HUMAN`: Represents a human review. ID can be the identifier for the annotator, such as name, account, email, etc.`LLM_JUDGE`: Represents an LLM-based evaluation. ID may be the name of the judge model e.g., "openai:/4o-mini".`CODE`: Represents any other programmatic check. |
| `error`               | `Optional[AssessmentError]` | An optional error associated with the feedback. This is used to indicate that the feedback was not processed successfully, for example, an exception from the LLM judge execution.                                                                                                                                                                                                                      |
| `metadata`            | `Optional[dict[str, str]]`  | Optional key-value pairs associated with the feedback.                                                                                                                                                                                                                                                                                                                                                  |
| `create_time_ms`      | `int`                       | The timestamp of when the feedback is created, in milliseconds.                                                                                                                                                                                                                                                                                                                                         |
| `last_update_time_ms` | `int`                       | The timestamp of when the feedback is updated, in milliseconds.                                                                                                                                                                                                                                                                                                                                         |
| `trace_id`            | `str`                       | The ID of the trace that the feedback is attached to.                                                                                                                                                                                                                                                                                                                                                   |
| `span_id`             | `Optional[str]`             | The ID of the span that the feedback is attached to, if it is associated with a particular span in the trace. For example, you can give a feedback to the specific retriever output in the RAG application.                                                                                                                                                                                             |

## Feedback Examples

**Human Feedback for Hallucination in the Response**

```json
{
    "name": "hallucination",
    "value": false,
    "rationale": "The response is factual and does not contain any hallucinations.",
    "source": {
        "source_type": "HUMAN",
        "source_id": "john@example.com"
    }
}
```

**LLM Judge Feedback for Factual Accuracy**

```json
{
    "name": "factual_accuracy",
    "value": 0.85,
    "rationale": "The response correctly identifies 3 out of 4 key facts about MLflow, but incorrectly states the founding year.",
    "source": {
        "source_type": "LLM_JUDGE",
        "source_id": "openai:/4o-mini"
    },
    "metadata": {
        # Store link to the prompt used for the judge, registered in MLflow Prompt Registry
        "judge_prompt": "prompts:factual_accuracy_judge/1"
    }
}
```

**Error Feedback from LLM Judge (Rate Limit Exceeded)**

```json
{
    "name": "safety",
    "error": {
        "error_code": "RATE_LIMIT_EXCEEDED",
        "error_message": "Rate limit for the judge exceeded.",
        "stack_trace": "..."
    },
    "source": {
        "source_type": "LLM_JUDGE",
        "source_id": "openai:/4o-mini"
    }
}
```
