---
doc_id: "mlflow/docs/docs/genai/tracing/integrations/listing/gemini"
source_path: "mlflow/docs/docs/genai/tracing/integrations/listing/gemini.mdx"
title: "Tracing Gemini"
description: "Trace Google Gemini model interactions with MLflow for full observability into LLM calls, token usage, and response quality."
keywords: ["gemini", "google", "tracing", "mlflow", "llm"]
---

# Tracing Gemini

[MLflow Tracing](../../) provides automatic tracing capability for Google Gemini. By enabling auto tracing
for Gemini by calling the `mlflow.gemini.autolog` function, MLflow will capture nested traces and log them to the active MLflow Experiment upon invocation of Gemini Python SDK. In Typescript, you can instead use the `tracedGemini` function to wrap the Gemini client.

MLflow trace automatically captures the following information about Gemini calls:

- Prompts and completion responses
- Latencies
- Model name
- Additional metadata such as `temperature`, `max_tokens`, if specified.
- Token usage (input, output, and total tokens)
- Function calling if returned in the response
- Any exception if raised

## Getting Started

### 1. Install Dependencies

**Python**

```bash
pip install mlflow google-generativeai
```

**JS / TS**

```bash
npm install @mlflow/gemini @google/generative-ai
```

### 3. Enable Tracing and Make API Calls

**Python**

Enable tracing with `mlflow.gemini.autolog()` and make API calls as usual.

```python
import mlflow
import google.generativeai as genai
import os

# Enable auto-tracing for Gemini
mlflow.gemini.autolog()

# Set a tracking URI and an experiment
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("Gemini")

# Configure your API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Use Gemini as usual - traces will be automatically captured
model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content("What is the capital of France?")
print(response.text)
```

**JS / TS**

Wrap the Gemini client with the `tracedGemini` function and make API calls as usual.

```typescript
import { GoogleGenerativeAI } from "@google/generative-ai";
import { tracedGemini } from "@mlflow/gemini";

// Wrap the Gemini client with the tracedGemini function
const genAI = tracedGemini(new GoogleGenerativeAI(process.env.GOOGLE_API_KEY));
const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });

// Invoke the client as usual
const result = await model.generateContent("What is the capital of France?");
console.log(result.response.text());
```

### 4. View Traces in MLflow UI

Browse to the MLflow UI at http://localhost:5000 (or your MLflow server URL) and you should see the traces for the Gemini API calls.

→ View [Next Steps](#next-steps) for learning about more MLflow features like user feedback tracking, prompt management, and evaluation.

**Note**

Current MLflow tracing integration supports both new [Google GenAI SDK](https://github.com/googleapis/python-genai) and legacy [Google AI Python SDK](https://github.com/google-gemini/generative-ai-python).
However, it may drop support for the legacy package without notice, and it is highly recommended to migrate your use cases to the new Google GenAI SDK.

## Supported APIs

MLflow supports automatic tracing for the following Gemini APIs:

### Python

| Text Generation | Chat | Function Calling | Streaming |  Async   | Image | Video |
| :-------------: | :--: | :--------------: | :-------: | :------: | :---: | :---: |
|       ✅        |  ✅  |        ✅        |     -     | ✅ (\*1) |   -   |   -   |

(\*1) Async support was added in MLflow 3.2.0.

### TypeScript / JavaScript

| Content Generation | Chat | Function Calling | Streaming | Async |
| :----------------: | :--: | :--------------: | :-------: | :---: |
|         ✅         |  -   |     ✅ (\*2)     |     -     |  ✅   |

(\*2) Only `models.generateContent()` is supported. Function calls in responses are captured and can be rendered in the MLflow UI. The TypeScript SDK is natively async.

To request support for additional APIs, please open a [feature request](https://github.com/mlflow/mlflow/issues) on GitHub.

## Examples

### Basic Text Generation

**Python**

```python
import mlflow
import google.genai as genai
import os

# Turn on auto tracing for Gemini
mlflow.gemini.autolog()

# Optional: Set a tracking URI and an experiment
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("Gemini")


# Configure the SDK with your API key.
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Use the generate_content method to generate responses to your prompts.
response = client.models.generate_content(
    model="gemini-1.5-flash", contents="The opposite of hot is"
)
```

**JS / TS**

```typescript
import { GoogleGenAI } from "@google/genai";
import { tracedGemini } from "@mlflow/gemini";

const client = tracedGemini(new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY }));

const response = await client.models.generateContent({
    model: "gemini-2.5-flash",
    contents: "What is the capital of France?"
});
```

## Multi-turn chat interactions

MLflow support tracing multi-turn conversations with Gemini:

```python
import mlflow

mlflow.gemini.autolog()

chat = client.chats.create(model="gemini-1.5-flash")
response = chat.send_message("In one sentence, explain how a computer works to a young child.")
print(response.text)
response = chat.send_message("Okay, how about a more detailed explanation to a high schooler?")
print(response.text)
```

## Async

MLflow Tracing supports asynchronous API of the Gemini SDK since MLflow 3.2.0. The usage is same as the synchronous API.

**Python**

```python
# Configure the SDK with your API key.
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Async API is invoked through the `aio` namespace.
response = await client.aio.models.generate_content(
    model="gemini-1.5-flash", contents="The opposite of hot is"
)
```

**JS / TS**

Gemini Typescript / Javascript SDK is natively async. See the basic example above.

## Embeddings

MLflow Tracing for Gemini SDK supports embeddings API (Python only):

```python
result = client.models.embed_content(model="text-embedding-004", contents="Hello world")
```

## Tracking Token Usage and Cost

MLflow automatically tracks token usage and cost for Gemini API calls. The token usage for each LLM call will be logged in each Trace/Span and the aggregated cost and time trend are displayed in the built-in dashboard. See the [Token Usage and Cost Tracking](/genai/tracing/token-usage-cost) documentation for details on accessing this information programmatically.

Token usage and cost tracking is supported for both Python and TypeScript/JavaScript implementations.

### Disable auto-tracing

Auto tracing for Gemini can be disabled globally by calling `mlflow.gemini.autolog(disable=True)` or `mlflow.autolog(disable=True)`.
