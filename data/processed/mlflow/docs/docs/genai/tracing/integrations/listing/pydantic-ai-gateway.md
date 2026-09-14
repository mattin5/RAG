---
doc_id: "mlflow/docs/docs/genai/tracing/integrations/listing/pydantic-ai-gateway"
source_path: "mlflow/docs/docs/genai/tracing/integrations/listing/pydantic-ai-gateway.mdx"
title: "Tracing Pydantic AI Gateway"
description: "Trace Pydantic AI Gateway requests with MLflow using OpenAI and Anthropic-compatible auto-tracing for full observability into multi-provider LLM routing."
keywords: ["pydantic ai gateway", "tracing", "mlflow", "openai-compatible", "multi-provider", "llm"]
---

# Tracing Pydantic AI Gateway

[Pydantic AI Gateway](https://ai.pydantic.dev/gateway/) is a unified interface for accessing multiple AI providers with a single key. It supports models from OpenAI, Anthropic, Google Vertex, Groq, AWS Bedrock, and more. Key features include spending limits, failover management, and zero translation—requests flow through directly in each provider's native format, giving you immediate access to new model features as soon as they are released.

Since Pydantic AI Gateway exposes OpenAI and Anthropic-compatible APIs, you can use MLflow's automatic tracing integrations to capture detailed traces of your LLM interactions.

**[Looking for PydanticAI Agent Framework?]**
This guide covers tracing LLM calls through **Pydantic AI Gateway**. If you're building agents using the Pydantic AI framework directly, see the [PydanticAI Integration](/genai/tracing/integrations/listing/pydantic_ai) guide instead.

## Prerequisite

### Get Pydantic AI Gateway API Key

Create an account on [Pydantic AI Gateway](https://gateway.pydantic.dev/) to get your API key, or bring your own API key from a supported LLM provider.

## Query Gateway

You can trace LLM calls through Pydantic AI Gateway using any of the following approaches:

**OpenAI SDK**

Since Pydantic AI Gateway exposes an OpenAI-compatible API, you can use MLflow's [OpenAI automatic tracing](/genai/tracing/integrations/listing/openai) integration to trace calls.

```python
import mlflow
from openai import OpenAI

# Enable auto-tracing for OpenAI
mlflow.openai.autolog()

# Set MLflow tracking URI and experiment
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("Pydantic AI Gateway")

# Point OpenAI client to Pydantic AI Gateway
client = OpenAI(
    base_url="https://gateway.pydantic.dev/proxy/chat/",
    api_key="<PYDANTIC_AI_GATEWAY_API_KEY>",
)

# Make API calls - traces will be captured automatically
response = client.chat.completions.create(
    model="gpt-5",
    messages=[{"role": "user", "content": "Hello world"}],
)
print(response.choices[0].message.content)
```

**Anthropic SDK**

If your Pydantic AI Gateway is configured to expose an Anthropic-compatible API, you can use MLflow's [Anthropic automatic tracing](/genai/tracing/integrations/listing/anthropic) integration to trace calls.

```python
import mlflow
import anthropic

# Enable auto-tracing for Anthropic
mlflow.anthropic.autolog()

# Set tracking URI and experiment
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("Pydantic AI Gateway")

# Point Anthropic client to Pydantic AI Gateway
client = anthropic.Anthropic(
    base_url="https://gateway.pydantic.dev/proxy/chat/",
    api_key="<PYDANTIC_AI_GATEWAY_API_KEY>",
)

# Make API calls - traces will be captured automatically
response = client.messages.create(
    max_tokens=1000,
    model="claude-sonnet-4-5",
    messages=[{"role": "user", "content": "Hello world"}],
)
print(response.content[0].text)
```

**Pydantic AI Agents**

You can also use the PydanticAI agent framework to interact with models through the gateway, with full tracing support.

```export
PYDANTIC_AI_GATEWAY_API_KEY=your-pydantic-ai-gateway-api-key
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=Pydantic AI Gateway
```

```python
import mlflow
from pydantic_ai import Agent

# Enable auto-tracing for PydanticAI
mlflow.pydantic_ai.autolog()

# Create an agent with the gateway model
# Use the appropriate model identifier for your gateway configuration
agent = Agent(
    "gateway/openai:gpt-4o",  # or your gateway model identifier
    system_prompt="You are a helpful assistant.",
    instrument=True,
)


# Run the agent - traces will be captured automatically
async def main():
    result = await agent.run("What is the capital of France?")
    print(result.output)


# If running in a notebook
await main()

# If running as a script
# import asyncio
# asyncio.run(main())
```

For more advanced PydanticAI features like tool calling, MCP servers, and streaming, see the [PydanticAI Integration](/genai/tracing/integrations/listing/pydantic_ai) guide.

## View Traces in MLflow UI

Open the MLflow UI at http://localhost:5000 (or your custom MLflow server URL) to see the traces from your Pydantic AI Gateway calls.
