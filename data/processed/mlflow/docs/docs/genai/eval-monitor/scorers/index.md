---
doc_id: "mlflow/docs/docs/genai/eval-monitor/scorers/index"
source_path: "mlflow/docs/docs/genai/eval-monitor/scorers/index.mdx"
title: "LLM Judges and Scorers"
description: "Learn about MLflow LLM judges and scorers for evaluating GenAI applications, including built-in judges, custom judges, and code-based scorers."
---

# LLM Judges and Scorers

Judges are a key component of the MLflow evaluation framework. They provide a unified interface to define evaluation criteria for your models, agents, and applications. Like their name suggests, judges judge how well your application did based on the evaluation criteria. This could be a pass/fail, true/false, numerical value, or a categorical value.

Choose the right type of judge depending on how much customization and control you need. Each approach builds on the previous one, adding more complexity and control.

Start with [built-in judges](/genai/eval-monitor/scorers/llm-judge/predefined/#available-judges) for quick evaluation. As your needs evolve, build [custom LLM judges](/genai/eval-monitor/scorers/llm-judge/custom-judges) for domain-specific criteria and create [custom code-based scorers](/genai/eval-monitor/scorers/custom) for programmatic business logic.

| Approach                                                                              | Level of customization | Use cases                                                                                                                                                             |
| ------------------------------------------------------------------------------------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Built-in judges](/genai/eval-monitor/scorers/llm-judge/predefined/#available-judges) | Minimal                | Quickly try LLM evaluation with built-in judges such as `Correctness` and `RetrievalGroundedness`.                                                                    |
| [Guidelines judges](/genai/eval-monitor/scorers/llm-judge/guidelines)                 | Moderate               | A built-in judge that checks whether responses pass or fail custom natural-language rules, such as style or factuality guidelines.                                    |
| [Custom judges](/genai/eval-monitor/scorers/llm-judge/custom-judges)                  | Full                   | Create fully customized LLM judges with detailed evaluation criteria and feedback optimization. Capable of returning numerical scores, categories, or boolean values. |
| [Code-based scorers](/genai/eval-monitor/scorers/custom)                              | Full                   | Programmatic scorers that evaluate things like exact matching, format validation, and performance metrics.                                                            |

**Note**
We'll refer to LLM judges and code-based scorers separately, but in the API, both LLM judges and code-based scorers are classified as types of scorers, such as in the functions `list_scorers` and `get_scorer`

## How judges work

A judge receives a [Trace](/genai/concepts/trace) from `evaluate()`. It then does the following:

1. Parses the `trace` to extract specific fields and data that are used to assess quality
2. Runs the judge to perform the quality assessment based on the extracted fields and data
3. Returns the quality assessment as [Feedback](/genai/assessments/feedback) to attach to the `trace`

## LLMs as judges

LLM judges use Large Language Models for quality assessment.

Think of a judge as an AI assistant specialized in quality assessment. It can evaluate your app's inputs, outputs, and even explore the entire execution trace to make assessments based on criteria you define. For example, when checking correctness, exact string matching would fail to recognize that `give me healthy food options` and `food to keep me fit` are semantically the same answer, but an LLM judge can understand they're both correct.

**Note**

Judges use LLMs for evaluation. Use them directly with `mlflow.genai.evaluate()` or wrap them in [custom scorers](/genai/eval-monitor/scorers/custom) for advanced scoring logic.

### Built-in LLM judges

MLflow provides research-validated judges for common use cases.

See the [complete list of built-in judges](/genai/eval-monitor/scorers/llm-judge/predefined/#available-judges) for details on each judge and their usage. You can further improve the judges' accuracy by [aligning them with human feedback](/genai/eval-monitor/scorers/llm-judge/alignment).

### Custom LLM judges

In addition to the built-in judges, MLflow makes it easy to create your own judges with custom prompts and instructions.

Use custom LLM judges when you need to define specialized evaluation tasks, need more control over grades (not just pass/fail), or need to validate that your agent made appropriate decisions and performed operations correctly for your specific use case.

See [Custom judges](/genai/eval-monitor/scorers/llm-judge/custom-judges). Once you've created custom judges, you can further improve their accuracy by [aligning them with human feedback](/genai/eval-monitor/scorers/llm-judge/alignment).

### Select the LLM that powers the judge

You can change the judge model by using the `model` argument in the judge definition. Specify the model in the format `<provider>:/<model-name>`. For example:

```python
from mlflow.genai.scorers import Correctness

Correctness(model="openai:/gpt-5-mini")
```

For a list of supported models, see [selecting judge models](/genai/eval-monitor/scorers/llm-judge/custom-judges/#selecting-judge-models).

**Set a default judge model globally**

Set the `MLFLOW_GENAI_JUDGE_DEFAULT_MODEL` environment variable to change the default judge model, instead of specifying `model` on each scorer individually. All built-in judges and scorers fall back to this model when no explicit `model` argument is provided.

```bash
export MLFLOW_GENAI_JUDGE_DEFAULT_MODEL="openai:/gpt-5-mini"
```

## What Judges you should use?

MLflow provides different types of judges to address different evaluation needs:

> _I want to try evaluation quickly and get some results fast._

&emsp;→ Use [Built-in Judges](/genai/eval-monitor/scorers/llm-judge/predefined) to get started.

> _I want to evaluate my application with a simple natural language criteria, such as "The response must be polite"._

&emsp;→ Use [Guidelines-based Judges](/genai/eval-monitor/scorers/llm-judge/guidelines).

> _I want to use more advanced prompt for evaluating my application._

&emsp;→ Use [Prompt-based Judges](/genai/eval-monitor/scorers/llm-judge/custom-judges).

> _I want to dump the entire trace to the scorer and get detailed insights from it._

&emsp;→ Use [Trace-Based Judges](/genai/eval-monitor/scorers/llm-judge/custom-judges/#trace-based-judges).

> _I want to write my own code for evaluating my application. Other scorers don't fit my advanced needs._

&emsp;→ Use [Code-based Scorers](/genai/eval-monitor/scorers/custom) to implement your own evaluation logic with Python.

If you are still unsure about which judge to use, you can use the "Ask AI" widget in the bottom right

## Code-based scorers

Custom code-based scorers offer the ultimate flexibility to define precisely how your LLM application or AI agent's quality is measured. You can define evaluation metrics tailored to your specific business use case, whether based on simple heuristics, advanced logic, or programmatic evaluations.

Use custom scorers for the following scenarios:

1. Defining a custom heuristic or code-based evaluation metric.
2. Customizing how the data from your app's trace is mapped to built-in LLM judges.
3. Using your own LLM for evaluation.
4. Any other use cases where you need more flexibility and control than provided by custom LLM judges.

See [Create custom code-based scorers](/genai/eval-monitor/scorers/custom).

## How to Write a Good Judge?

In practice, out-of-the-box judges such as 'Groundedness' or 'Safety' struggle to understand your domain-specific data and criteria. Successful practitioners analyze real data to uncover domain-specific failure modes and then define custom evaluation criteria from the ground up. Here is the general workflow of how to define a good judge and iterate on it with MLflow.

**[Pro tip: Version Control Judges]**

As you iterate on the judge, version control becomes important. MLflow can track [Judge Versions](/genai/eval-monitor/scorers/versioning) to help you maintain changes and share the improved judges with your team.
