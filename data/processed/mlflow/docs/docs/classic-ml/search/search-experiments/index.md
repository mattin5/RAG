---
doc_id: "mlflow/docs/docs/classic-ml/search/search-experiments/index"
source_path: "mlflow/docs/docs/classic-ml/search/search-experiments/index.mdx"
title: "Search Experiments"
---

# Search Experiments

`mlflow.search_experiments` and `MlflowClient.search_experiments()`
support the same filter string syntax as `mlflow.search_runs` and
`MlflowClient.search_runs`, but the supported identifiers and comparators are different.

## Syntax

See [Search Runs Syntax](/ml/search/search-runs#search-runs-syntax) for more information.

### Identifier

The following identifiers are supported:

- `attributes.name`: Experiment name
- `attributes.creation_time`: Experiment creation time
- `attributes.last_update_time`: Experiment last update time

**Note**
`attributes` can be omitted. `name` is equivalent to `attributes.name`.

- `tags.<tag key>`: Tag

### Comparator

Comparators for string attributes and tags:

- `=`: Equal
- `!=`: Not equal
- `LIKE`: Case-sensitive pattern match
- `ILIKE`: Case-insensitive pattern match

Comparators for tags only:

- `IS NULL`: Tag does not exist
- `IS NOT NULL`: Tag exists

Comparators for numeric attributes:

- `=`: Equal
- `!=`: Not equal
- `<`: Less than
- `<=`: Less than or equal to
- `>`: Greater than
- `>=`: Greater than or equal to

### Examples

```python
# Matches experiments with name equal to 'x'
"attributes.name = 'x'"  # or "name = 'x'"

# Matches experiments with name starting with 'x'
"attributes.name LIKE 'x%'"

# Matches experiments with 'group' tag value not equal to 'x'
"tags.group != 'x'"

# Matches experiments with 'group' tag value containing 'x' or 'X'
"tags.group ILIKE '%x%'"

# Matches experiments with name starting with 'x' and 'group' tag value equal to 'y'
"attributes.name LIKE 'x%' AND tags.group = 'y'"

# Matches experiments that have a 'group' tag
"tags.group IS NOT NULL"

# Matches experiments that do NOT have a 'deprecated' tag
"tags.deprecated IS NULL"
```
