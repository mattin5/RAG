---
doc_id: "mlflow/docs/docs/genai/governance/ai-gateway/coding-agents/index"
source_path: "mlflow/docs/docs/genai/governance/ai-gateway/coding-agents/index.mdx"
title: "Coding Agents & Long-Running Agents"
description: "Use Claude Code, OpenAI Codex, Gemini CLI, and Hermes Agent with the MLflow AI Gateway for centralized observability and governance."
---

# Coding Agents & Long-Running Agents

The MLflow AI Gateway supports popular AI coding agents such as **Claude Code**, **OpenAI Codex**, and **Gemini CLI**, as well as long-running agent runtimes like **Hermes Agent**.

Coding agents and long-running agent runtimes can make dozens or hundreds of LLM calls per session, often running autonomously for extended periods while also invoking tools and managing their own state. Without visibility or controls in place, it's easy to lose track of what they're doing, how much they're spending, and whether they're operating within your organization's policies. Routing these agents through the gateway gives your team three key capabilities:
