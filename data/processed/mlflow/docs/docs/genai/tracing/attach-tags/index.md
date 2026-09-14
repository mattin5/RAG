---
doc_id: "mlflow/docs/docs/genai/tracing/attach-tags/index"
source_path: "mlflow/docs/docs/genai/tracing/attach-tags/index.mdx"
title: "Setting Trace Tags"
description: "Attach mutable key-value tags to MLflow traces for grouping, filtering, and contextual analysis."
---

# Setting Trace Tags

Tags are mutable key-value pairs that you can attach to traces to add valuable labels and context for grouping and filtering traces. For example, you can tag traces based on the topic of the user's input or the type of request being processed and group them together for analysis and quality evaluation.

## Setting Tags on Ongoing Traces

Use `mlflow.update_current_trace` to add tags during trace execution.

```python
import mlflow


@mlflow.trace
def my_func(x):
    mlflow.update_current_trace(tags={"fruit": "apple"})
    return x + 1


result = my_func(5)
```

**Note**
If the key is already present, the `mlflow.update_current_trace` function will update the key with the new value.

## Setting Tags on Completed Traces

Add or modify tags on traces that have already been completed and logged.

```python
import mlflow

mlflow.set_trace_tag(trace_id="your-trace-id", key="tag_key", value="tag_value")
```

## Retrieving Tags

Tags are stored on the `info.tags` attribute of the trace object.

```python
import mlflow

trace = mlflow.get_trace(trace_id="your-trace-id")
print(trace.info.tags)
# Output: {'tag_key': 'tag_value'}
```

## Searching and Filtering with Tags

Use tags to find specific traces quickly and efficiently.

```python
# Search for traces with tag 'environment' set to 'production'
traces = mlflow.search_traces(filter_string="tags.environment = 'production'")
```

You can also use pattern matching to find traces by tag value.

```python
# Search for traces with tag that contains the word 'mlflow'
traces = mlflow.search_traces(filter_string="tags.topic LIKE '%mlflow%'")
```

View the full list of supported filter syntax in the [Search Traces](/genai/tracing/search-traces) guide.
