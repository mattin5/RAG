---
doc_id: "mlflow/docs/docs/genai/tracing/quickstart/index"
source_path: "mlflow/docs/docs/genai/tracing/quickstart/index.mdx"
title: "Tracing Quickstart"
description: "Get started with MLflow Tracing in under 10 minutes by enabling tracing for a simple LLM application."
---

# Tracing Quickstart

**[MLflow Assistant]**

Need help setting up tracing? Try [MLflow Assistant](/genai/getting-started/try-assistant) - a powerful AI assistant that can add MLflow tracing to your project automatically.

**[Set up Tracing with the MLflow CLI]**

From inside your project's Git repository, run a single command to install the MLflow skills and instrument your app for tracing — no manual setup:

```bash
uvx mlflow@latest agent setup
```

Prefer to set things up manually? Read on below.

This quickstart guide will walk you through setting up a simple LLM application with MLflow Tracing. In less than 10 minutes, you'll enable tracing, run a basic application, and explore the generated traces in the MLflow UI.

## Prerequisites

Make sure you have started the MLflow server.
If you don't have the MLflow server running yet, just follow these simple steps to get it started.

## Create a MLflow Experiment

The traces your LLM application or AI agent will send to the MLflow server are grouped into MLflow experiments. We recommend creating one experiment for each LLM application or AI agent.

Let's create a new MLflow experiment using the MLflow UI so that you can start sending your traces.

1. Navigate to the MLflow UI in your browser at [http://localhost:5000](http://localhost:5000).
2. Click on the Create button on the top right.
3. Enter a name for the experiment and click on "Create".

_You can leave the `Artifact Location` field blank for now. It is an advanced configuration to override where MLflow stores experiment data._

## Dependency

To connect your LLM application or AI agent to the MLflow server, you will need to install the MLflow client SDK.

**Python(OpenAI)**

```bash
pip install --upgrade mlflow openai>=1.0.0
```

**TypeScript(OpenAI)**

```bash
npm install @mlflow/openai
```

**Info**

While this guide features an example using the OpenAI SDK, the same steps apply to other LLM providers, including Anthropic, Google, Bedrock, and many others.

For a comprehensive list of LLM providers supported by MLflow, see the [LLM Integrations Overview](/genai/tracing/integrations).

## Start Tracing

Once your experiment is created, you're ready to connect to the MLflow server and begin sending traces from your LLM application or AI agent.

**Python(OpenAI)**

```python
import mlflow
from openai import OpenAI

# Specify the tracking URI for the MLflow server.
mlflow.set_tracking_uri("http://localhost:5000")

# Specify the experiment you just created for your LLM application or AI agent.
# The positional argument is the experiment name. To attach to an existing
# experiment by its numeric ID, pass it with the experiment_id keyword (a numeric
# value passed positionally is treated as a name, not an ID):
mlflow.set_experiment("My Application")
# mlflow.set_experiment(experiment_id="1234567890123456")

# Enable automatic tracing for all OpenAI API calls.
mlflow.openai.autolog()

client = OpenAI()
# The trace of the following is sent to the MLflow server.
client.chat.completions.create(
    model="o4-mini",
    messages=[
        {"role": "system", "content": "You are a helpful weather assistant."},
        {"role": "user", "content": "What's the weather like in Seattle?"},
    ],
)
```

**TypeScript(OpenAI)**

```typescript
import { init } from "@mlflow/core";
import { tracedOpenAI } from "@mlflow/openai";
import { OpenAI } from "openai";

init({
    trackingUri: "http://localhost:5000",
    // NOTE: specifying experiment name is not yet supported in TypeScript SDK.
    // You can copy the experiment id from the experiment details on the MLflow UI.
    experimentId: "<experiment-id>",
});

// Wrap the OpenAI client with the tracedOpenAI function to enable automatic tracing.
const client = tracedOpenAI(new OpenAI());

// The trace of the following is sent to the MLflow server.
client.chat.completions.create({
    model: "o4-mini",
    messages: [
        {"role": "system", "content": "You are a helpful weather assistant."},
        {"role": "user", "content": "What's the weather like in Seattle?"},
    ],
})
```

**OpenTelemetry**

MLflow Server exposes an OTLP endpoint at `/v1/traces` ([OTLP](https://opentelemetry.io/docs/specs/otlp/)). This endpoint accepts traces from any native OpenTelemetry instrumentation, allowing you to trace applications written in other languages such as Java, Go, Rust, etc.

The following example shows how to collect traces from a FastAPI application using OpenTelemetry FastAPI instrumentation.

```python
import os
import uvicorn
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Set the endpoint and header
MLFLOW_TRACKING_URI = "http://localhost:5000"
MLFLOW_EXPERIMENT_ID = "123"

os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{MLFLOW_TRACKING_URI}/v1/traces"
os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = f"x-mlflow-experiment-id={MLFLOW_EXPERIMENT_ID}"

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)


@app.get("/")
async def root():
    return {"message": "Hello, World!"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

For a deeper dive into using MLflow together with OpenTelemetry, see the [OpenTelemetry guide](/genai/tracing/opentelemetry).

## View Your Traces on the MLflow UI

After running the code above, go to the MLflow UI and select the "My Application" experiment, and then select the "Traces" tab. It should show the newly created trace.

**[Learn More About Tracing UI]**

The "Traces" page includes rich information about the trace and supports various actions such as searching, filtering, adding feedbacks, and more. See [View Traces](/genai/tracing/observe-with-traces/ui) for comprehensive guide about how to get the most out of the MLflow Tracing UI.

## Track Multi-Turn Conversations with Sessions

Many LLM applications and AI agents maintain multi-turn conversations with users. MLflow provides built-in support for tracking user sessions by using standard metadata fields. This allows you to group related traces together and analyze conversation flows.

**Python**

Here's how to add user and session tracking to your application:

```python
import mlflow


@mlflow.trace
def chat_completion(message: list[dict], user_id: str, session_id: str):
    """Process a chat message with user and session tracking."""

    # Add user and session context to the current trace
    mlflow.update_current_trace(
        metadata={
            "mlflow.trace.user": user_id,  # Links trace to specific user
            "mlflow.trace.session": session_id,  # Groups trace with conversation
        }
    )

    # Your chat logic here
    return f"Echo: {message[-1]['content'] if message else ''}"
```

**TypeScript**

```typescript
import * as mlflow from "@mlflow/core";

const chatCompletion = mlflow.trace(
    (message: Array<Record<string, any>>, userId: string, sessionId: string) => {
        // Add user and session context to the current trace
        mlflow.updateCurrentTrace({
            metadata: {
                "mlflow.trace.user": userId,
                "mlflow.trace.session": sessionId,
            },
        });

        // Your chat logic here
        return generateResponse(message);
    },
    { name: "chat_completion" }
);
```

For more details on tracking users and sessions, see the [Track Users & Sessions guide](/genai/tracing/track-users-sessions).

## Next Steps

Congrats on sending your first trace with MLflow! Now that you've got the basics working, here are the recommended next steps to deepen your understanding of tracing:
