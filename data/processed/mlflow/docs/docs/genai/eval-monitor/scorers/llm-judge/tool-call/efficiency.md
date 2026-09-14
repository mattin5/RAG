---
doc_id: "mlflow/docs/docs/genai/eval-monitor/scorers/llm-judge/tool-call/efficiency"
source_path: "mlflow/docs/docs/genai/eval-monitor/scorers/llm-judge/tool-call/efficiency.mdx"
title: "ToolCallEfficiency Judge"
---

# ToolCallEfficiency Judge

The `ToolCallEfficiency` judge evaluates the agent's trajectory for redundancy in tool usage, such as tool calls with the same or similar arguments.

This built-in LLM judge is designed for evaluating AI agents and tool-calling applications where you need to ensure the agent operates efficiently without making unnecessary or duplicate tool calls.

## Usage examples

The `ToolCallEfficiency` judge can be invoked directly for single trace assessment or used with MLflow's evaluation framework for batch evaluation.

**Requirements:**

- **Trace requirements**: - The MLflow Trace must contain at least one span with `span_type` set to `TOOL`

**Invoke directly**

```python
from mlflow.genai.scorers import ToolCallEfficiency
import mlflow

# Get a trace from a previous run
trace = mlflow.get_trace("<your-trace-id>")

# Assess if tool calls are efficient
feedback = ToolCallEfficiency(name="my_tool_call_efficiency")(trace=trace)
print(feedback)
```

**Invoke with evaluate()**

```python
import mlflow
from mlflow.genai.scorers import ToolCallEfficiency

# Evaluate traces from previous runs
results = mlflow.genai.evaluate(
    data=traces,  # DataFrame or list containing trace data
    scorers=[ToolCallEfficiency()],
)
```

**Tip**
For a complete agent example with this judge, see the [Tool Call Evaluation guide](/genai/eval-monitor/scorers/llm-judge/tool-call/).

## Interpret results

The judge returns a Feedback object with:

- **value**: "yes" if tool calls are efficient, "no" if otherwise
- **rationale**: Detailed explanation identifying:
  - Which specific tool calls are redundant (if any)
  - Why certain calls are considered duplicates or could be consolidated
  - Why the tool usage is efficient
