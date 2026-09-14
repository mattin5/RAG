---
doc_id: "mlflow/docs/docs/genai/version-tracking/index"
source_path: "mlflow/docs/docs/genai/version-tracking/index.mdx"
title: "Version Tracking for Agents and LLMs"
description: "Understand how MLflow enables version tracking for your complete agent and LLM applications using LoggedModels, linking code, configurations, evaluations, and traces."
---

# Version Tracking for LLM Applications and AI Agents

MLflow's **LoggedModel** provides systematic version control for your entire LLM application or AI agent—code, configurations, evaluations, and traces. Stop losing track of what works and start building with confidence through complete application lifecycle management.

## Why Version Control Matters for LLM Applications and AI Agents

LLM applications and AI agents are complex systems with interdependent components. Without systematic versioning, development becomes chaotic and deployments risky.

## How LoggedModel Powers Version Control

MLflow's LoggedModel adapts traditional ML model versioning for LLM applications and AI agents. Instead of just tracking model weights, it becomes a comprehensive metadata hub that coordinates all the moving parts of your AI system.

## Start Version Tracking in 5 Minutes

Transform chaotic AI development into systematic version control with just a few lines of code.

### Automatic Version Tracking with Git Integration

Link your application versions to git commits for complete traceability:

```python
import mlflow
import openai
import os

# Fix: Added missing import
os.environ["OPENAI_API_KEY"] = "your-api-key-here"

# Configure MLflow experiment
mlflow.set_experiment("customer-support-agent")

# Get current git commit using MLflow's built-in utilities
from mlflow.utils.git_utils import get_git_commit

git_commit = get_git_commit(".")
if git_commit:
    git_commit = git_commit[:8]  # Use short hash
else:
    git_commit = "local-dev"  # Fallback if not in git repo

# Create version identifier
app_name = "customer_support_agent"
version_name = f"{app_name}-{git_commit}"

# Set active model context - all traces will link to this version
mlflow.set_active_model(name=version_name)

# Enable automatic tracing
mlflow.openai.autolog()

# Your application code - now automatically versioned and traced
client = openai.OpenAI()
test_questions = [
    "How do I reset my password?",
    "What are your business hours?",
    "Can I get a refund for my order?",
]

for question in test_questions:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": question}],
        temperature=0.7,
        max_tokens=1000,
    )
    # ✅ Automatically: traced, versioned, and linked to git commit
```

**What happens automatically:**

- Every LLM call generates a detailed trace
- All traces link to your specific application version
- Git commit provides exact code reproducibility
- Version performance can be compared objectively

### Version Management Made Simple

```python
# Create a new version for experimentation
with mlflow.set_active_model(name=f"agent-v2-{new_commit}"):
    # Test new prompt engineering approach
    improved_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful customer support agent. Be concise and actionable.",
            },
            {"role": "user", "content": question},
        ],
        temperature=0.3,  # Lower temperature for consistency
        max_tokens=500,  # More focused responses
    )
    # ✅ New version automatically tracked with different configurations
```

Context manager automatically handles version switching—clean, explicit, and error-free.

### Compare Versions Systematically

```python
import pandas as pd

# Evaluate multiple versions against the same test set
eval_data = pd.DataFrame({
    "inputs": test_questions,
    "expected_categories": ["account", "business_info", "billing"],
})

# Version A: Original configuration
results_v1 = mlflow.evaluate(
    model_uri=f"models:/{app_name}-{commit_v1}",
    data=eval_data,
    extra_metrics=[
        mlflow.metrics.toxicity(),
        mlflow.metrics.latency(),
        mlflow.metrics.flesch_kincaid_grade_level(),
    ],
)

# Version B: Improved prompts
results_v2 = mlflow.evaluate(
    model_uri=f"models:/{app_name}-{commit_v2}",
    data=eval_data,
    extra_metrics=[
        mlflow.metrics.toxicity(),
        mlflow.metrics.latency(),
        mlflow.metrics.flesch_kincaid_grade_level(),
    ],
)

# ✅ Side-by-side comparison shows which version performs better
```

Objective metrics remove guesswork from version selection.

## Prerequisites

Ready to implement systematic version tracking? You'll need:

- **MLflow 3.0+** (`pip install --upgrade 'mlflow>=3.1'`)
- **Git repository** for your application code
- **Python 3.10+**
- **LLM API access** (OpenAI, Anthropic, etc.)

**Tip**
For Databricks-hosted MLflow Tracking: `pip install --upgrade 'mlflow[databricks]>=3.1'`

## Advanced Version Tracking Capabilities

Once you've mastered basic version tracking, explore these advanced patterns for production LLM applications and AI agents.

Start with the code examples above, then explore the advanced capabilities as your application grows in complexity.
