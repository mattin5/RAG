---
doc_id: "mlflow/docs/docs/genai/governance/ai-gateway/index"
source_path: "mlflow/docs/docs/genai/governance/ai-gateway/index.mdx"
title: "MLflow AI Gateway for LLMs"
description: "Manage multiple LLM providers through a single, secure endpoint. Centralize access control, cost tracking, and rate limiting for OpenAI, Anthropic, and more."
---

# MLflow AI Gateway

MLflow's [AI Gateway](https://mlflow.org/ai-gateway) provides a unified interface for deploying and managing multiple LLM providers within your organization. It simplifies interactions with services like OpenAI, Anthropic, and others through a single, secure endpoint.

The gateway excels in production environments where organizations need to manage multiple LLM providers securely while maintaining operational flexibility. Advanced routing capabilities enable traffic splitting for A/B testing and automatic failover chains for high availability.

MLflow AI Gateway also offers passthrough endpoints, enabling requests to be forwarded in providers' native formats. This feature allows you to access provider-specific capabilities as soon as they become available.
