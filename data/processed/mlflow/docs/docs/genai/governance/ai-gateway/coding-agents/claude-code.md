---
doc_id: "mlflow/docs/docs/genai/governance/ai-gateway/coding-agents/claude-code"
source_path: "mlflow/docs/docs/genai/governance/ai-gateway/coding-agents/claude-code.mdx"
title: "Claude Code"
description: "Use Claude Code with the MLflow AI Gateway to get centralized observability while authenticating with your own Anthropic subscription."
---

# Claude Code + MLflow AI Gateway

Route [Claude Code](https://docs.anthropic.com/en/docs/claude-code) through the MLflow AI Gateway to get centralized tracing and observability, while each developer authenticates with their own Anthropic subscription.

## Prerequisites

- MLflow server running with a SQL backend (`mlflow server --port 5000`)
- Claude Code installed (`npm install -g @anthropic-ai/claude-code`)

## Step 1: Create an Anthropic Endpoint

Navigate to the **AI Gateway** tab at `http://localhost:5000/#/gateway` and click **Claude Code** in the quick start. Then click "create" to create an endpoint. The endpoint name is pre-filled as `claude-code` — you can change it, but make sure to use the same name in the next step.

## Step 2: Configure Environment Variables

Set the following environment variables so Claude Code routes through the gateway and uses your endpoint:

```bash
export ANTHROPIC_BASE_URL="http://localhost:5000/gateway/proxy/claude-code"
```

## Step 3: Run Claude Code

```bash
claude
```

Claude Code authenticates using your existing Anthropic credentials (stored in `~/.claude`) and all requests are proxied through the gateway.

## What You Get

Every conversation is captured as an MLflow trace. Open the **Logs** tab in the MLflow UI to inspect inputs, outputs, token usage, and latency for every request.

![Claude Code trace in MLflow](/images/genai/governance/ai-gateway/claude-code-trace.png)
