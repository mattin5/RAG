---
doc_id: "mlflow/docs/docs/genai/tracing/integrations/listing/mlflow-ai-gateway"
source_path: "mlflow/docs/docs/genai/tracing/integrations/listing/mlflow-ai-gateway.mdx"
title: "Tracing MLflow AI Gateway"
description: "Trace MLflow AI Gateway requests with MLflow using OpenAI-compatible auto-tracing for full observability into unified multi-provider LLM routing."
keywords: ["mlflow", "ai gateway", "tracing", "openai-compatible", "multi-provider", "llm"]
---

# Tracing MLflow AI Gateway

[MLflow AI Gateway](/genai/governance/ai-gateway/) is a unified, centralized interface for accessing multiple LLM providers. It simplifies API key management, provides a consistent API across providers, and enables seamless switching between models from OpenAI, Anthropic, Google, and other providers.

Since MLflow AI Gateway exposes an OpenAI-compatible API, you can use MLflow's automatic tracing integrations to capture detailed traces of your LLM interactions.

## Integration Options

There are two ways to trace LLM calls through MLflow AI Gateway:

| Approach                | Description                                                                                                           | Best For                                                   |
| :---------------------- | :-------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------- |
| **Server-side Tracing** | Gateway automatically logs all requests when [usage tracking](/genai/governance/ai-gateway/usage-tracking) is enabled | Centralized tracing for all requests through the gateway   |
| **Client-side Tracing** | Use OpenAI SDK with MLflow autolog                                                                                    | Combining LLM traces with your agent or application traces |

When both are used together with a `traceparent` header, the gateway creates a linked span under the agent's trace for end-to-end visibility. See [Distributed Tracing](/genai/tracing/app-instrumentation/distributed-tracing#ai-gateway-integration) for details.

## Prerequisite

### Start MLflow Server with AI Gateway

To start MLflow server with AI Gateway, you need to install the `mlflow` package.

```bash
pip install mlflow
```

Then start the MLflow server as usual, no additional configuration is needed.

```bash
mlflow server
```

### Create Endpoint

Create an endpoint in MLflow AI Gateway to route requests to your LLM provider. See the [AI Gateway Quickstart](/genai/governance/ai-gateway/quickstart/) for detailed setup instructions.

## Query Gateway

You can trace LLM calls through MLflow AI Gateway using any of the following approaches:

**OpenAI SDK**

Since MLflow AI Gateway exposes an OpenAI-compatible API, you can use MLflow's [OpenAI automatic tracing](/genai/tracing/integrations/listing/openai) integration to trace calls.

```python
import mlflow
from openai import OpenAI

# Enable auto-tracing for OpenAI
mlflow.openai.autolog()

# Set MLflow tracking URI and experiment
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("MLflow AI Gateway")

# Point OpenAI client to MLflow AI Gateway
client = OpenAI(
    base_url="http://localhost:5000/gateway/openai/v1",
    api_key="dummy",  # API key not needed, configured server-side
)

response = client.chat.completions.create(
    model="my-endpoint", messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

**Anthropic SDK**

You can use MLflow's [Anthropic automatic tracing](/genai/tracing/integrations/listing/anthropic) integration to trace calls through MLflow AI Gateway.

```python
import mlflow
import anthropic

# Enable auto-tracing for Anthropic
mlflow.anthropic.autolog()

# Set MLflow tracking URI and experiment
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("MLflow AI Gateway")

# Point Anthropic client to MLflow AI Gateway
client = anthropic.Anthropic(
    base_url="http://localhost:5000/gateway/anthropic",
    api_key="dummy",  # API key not needed, configured server-side
)

# Make API calls - traces will be captured automatically
response = client.messages.create(
    max_tokens=1004,
    model="<your-endpoint-name>",  # Use your endpoint name
    messages=[{"role": "user", "content": "Hello world"}],
)
print(response.content[0].text)
```

**Gemini SDK**

You can use MLflow's [Gemini automatic tracing](/genai/tracing/integrations/listing/gemini) integration to trace calls through MLflow AI Gateway.

```python
import mlflow
from google import genai

# Enable auto-tracing for Gemini
mlflow.gemini.autolog()

# Set MLflow tracking URI and experiment
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("MLflow AI Gateway")

# Point Gemini client to MLflow AI Gateway
client = genai.Client(
    http_options={"base_url": "http://localhost:5000/gateway/gemini"},
    api_key="dummy",  # API key not needed, configured server-side
)

# Make API calls - traces will be captured automatically
response = client.models.generate_content(
    model="<your-endpoint-name>",  # Use your endpoint name
    contents={"text": "Hello!"},
)
print(response.text)
```

**LangChain**

You can use MLflow's [LangChain automatic tracing](/genai/tracing/integrations/listing/langchain) integration to trace calls through MLflow AI Gateway.

```python
import mlflow
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

# Enable auto-tracing for LangChain
mlflow.langchain.autolog()

# Set MLflow tracking URI and experiment
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("MLflow AI Gateway")

# Point LangChain to MLflow AI Gateway
llm = ChatOpenAI(
    base_url="http://localhost:5000/gateway/mlflow/v1",
    model="<your-endpoint-name>",  # Use your endpoint name
    api_key="dummy",  # API key not needed, configured server-side
)


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


# Run the agent as usual
agent = create_agent(
    llm,
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)
agent.invoke({"input": "What's the weather in San Francisco?"})
```

## View Traces in MLflow UI

Open the MLflow UI at http://localhost:5000 (or your custom MLflow server URL) to see the traces from your MLflow AI Gateway calls.
