# AI DIAL Interceptors Python SDK

[![PyPI version](https://img.shields.io/pypi/v/aidial-interceptors-sdk.svg)](https://pypi.org/project/aidial-interceptors-sdk/)

> [!IMPORTANT]
> This package is in early development and subject to rapid changes. Breaking changes between versions are likely as the project evolves.

## Overview

The framework provides useful classes and helpers for creating DIAL Interceptors in Python for chat completion and embedding models.

An interceptor could be thought of as a middleware that

1. modifies an incoming DIAL request received from the client *(or it may leave it as is)*
2. calls upstream DIAL application *(**the upstream** for short)* with the modified request
3. modifies the response from the upstream *(or it may leave it as is)*
4. returns the modified response to the client

The upstream is encapsulated behind a special deployment id `interceptor`. This deployment id is resolved by the DIAL Core into an appropriate deployment id.

Interceptors could be classified into the following categories:

1. **Pre-interceptors** that only modify the incoming request from the client *(e.g. rejecting requests following certain criteria)*
2. **Post-interceptors** that only modify the response received from the upstream *(e.g. censoring the response)*
3. **Generic interceptors** that modify both the incoming request and the response from the upstream *(e.g. caching the responses)*

To create chat completion interceptor one needs to implement instance of the class [ChatCompletionInterceptor](aidial_interceptors_sdk/chat_completion/base.py) and for embedding interceptor - [EmbeddingsInterceptor](aidial_interceptors_sdk/embeddings/base.py).

See [example](aidial_interceptors_sdk/examples/interceptor/registry.py) interceptor implementations for more details.

## Environment Variables

Copy `.env.example` to `.env` and customize it for your environment:

|Variable|Default|Description|
|---|---|---|
|LOG_LEVEL|INFO|Log level. Use DEBUG for dev purposes and INFO in prod|
|WEB_CONCURRENCY|1|Number of workers for the server|
|DIAL_URL||The URL of the DIAL Core server|

## Development

This project uses [Python>=3.11](https://www.python.org/downloads/) and [Poetry>=1.6.1](https://python-poetry.org/) as a dependency manager.

Check out Poetry's [documentation on how to install it](https://python-poetry.org/docs/#installation) on your system before proceeding.

To install requirements:

```sh
poetry install
```

This will install all requirements for running the package, linting, formatting and tests.

### IDE configuration

The recommended IDE is [VSCode](https://code.visualstudio.com/).
Open the project in VSCode and install the recommended extensions.

The VSCode is configured to use PEP-8 compatible formatter [Black](https://black.readthedocs.io/en/stable/index.html).

Alternatively you can use [PyCharm](https://www.jetbrains.com/pycharm/).

Set-up the Black formatter for PyCharm [manually](https://black.readthedocs.io/en/stable/integrations/editors.html#pycharm-intellij-idea) or
install PyCharm>=2023.2 with [built-in Black support](https://blog.jetbrains.com/pycharm/2023/07/2023-2/#black).

### Make on Windows

As of now, Windows distributions do not include the make tool. To run make commands, the tool can be installed using
the following command (since [Windows 10](https://learn.microsoft.com/en-us/windows/package-manager/winget/)):

```sh
winget install GnuWin32.Make
```

For convenience, the tool folder can be added to the PATH environment variable as `C:\Program Files (x86)\GnuWin32\bin`.
The command definitions inside Makefile should be cross-platform to keep the development environment setup simple.

### Lint

To run the linting before committing:

```sh
make lint
```

To auto-fix formatting issues run:

```sh
make format
```

### Test

To run unit tests:

```sh
make test
```

### Clean

To remove the virtual environment and build artifacts:

```sh
make clean
```

## Examples

The repository also provides examples of various DIAL Interceptors all packed into a DIAL service.

Keep in mind, that the following example interceptors aren't ready for a production use.
They are provided solely as examples to demonstrate basic use cases of interceptors. Use at your discretion.

### Chat completion interceptors

|Interceptor name|Category|Description|
|---|---|---|
|reply-as-pirate|Pre|Injects systems prompt `Reply as a pirate` to the request|
|reject-external-links|Pre|Rejects any URL in DIAL attachments which do not point to DIAL Core storage|
|reject-blacklisted-words|Generic|Rejects the request if it contains any blacklisted words|
|image-watermark|Post|Stamps "EPAM DIAL" watermark on all image attachments in the response. Demonstrates how to work with files stored on DIAL File Storage.|
|statistics-reporter|Post|Collects statistics on the response stream *(tokens/sec, finish reason, completion tokens etc)* and reports it in a new stage when response is finished|
|pii-anonymizer|Generic|Anonymizes any PII in the request, calls the upstream, deanonymizes the response|
|replicator:N|Generic|Calls the upstream N times and combines the N response into a single response. Could be useful for stabilization of model's output, since certain models aren't deterministic.|
|cache|Generic|Caches incoming chat completion requests. **Not ready for production use. Use at your discretion**|
|no-op|Generic|No-op interceptor - does not modify the request or the response, simply proxies the upstream|

### Embeddings interceptors

|Interceptor name|Category|Description|
|---|---|---|
|reject-blacklisted-words|Pre|Rejects the request if it contains any blacklisted words|
|normalize-vector|Post|Normalizes the vector in the response|
|project-vector:N|Post|Changes the dimensionality of the vectors in the response to N, where N is an integer path parameter.|
|no-op|Generic|No-op interceptor - does not modify the request or the response, simply proxies the upstream|

### Environment variables

Copy `.env.example` to `.env` and customize it for your environment:

|Variable|Default|Description|
|---|---|---|
|PII_ANONYMIZER_LABELS_TO_REDACT|PERSON,ORG,GPE,PRODUCT|Comma-separated list of spaCy entity types to redact. Find the full list of entities [here](https://github.com/explosion/spacy-models/blob/e46017f5c8241096c1b30fae080f0e0709c8038c/meta/en_core_web_sm-3.7.0.json#L121-L140).|

### Running interceptor as a DIAL service

#### From package

To run the server with examples using pip:

```sh
pip install uvicorn python-dotenv "aidial-interceptors-sdk[examples]"
echo "DIAL_URL=URL" > .env
uvicorn "aidial_interceptors_sdk.examples.app:app" --host "0.0.0.0" --port 5000 --env-file ./.env
```

Don't forget to set the appropriate `DIAL_URL` in the `.env` file.

The command will start the server on `http://localhost:5000` exposing endpoints for each of the interceptors like the following:

- `http://localhost:5000/openai/deployments/pii-anonymizer/chat/completions`
- `http://localhost:5000/openai/deployments/normalize-vector/embeddings`

#### From sources

First clone the repository:

```sh
git clone https://github.com/epam/ai-dial-interceptors-sdk.git
cd ai-dial-interceptors-sdk
echo "DIAL_URL=URL" > .env
```

Then run dev server with examples:

```sh
make examples_serve
```

Or run the server from Docker container:

```sh
make examples_docker_serve
```

### DIAL Core configuration

The interceptor endpoints are defined in the `interceptors` section of the DIAL Core configuration like this:

```json
{
    "interceptors": {
        "chat-reply-as-pirate": {
            "endpoint": "${INTERCEPTOR_SERVICE_URL}/openai/deployments/reply-as-pirate/chat/completions"
        },
        "chat-statistics-reporter": {
            "endpoint": "${INTERCEPTOR_SERVICE_URL}/openai/deployments/statistics-reporter/chat/completions"
        }
    }
}
```

where `INTERCEPTOR_SERVICE_URL` is the URL of the interceptor service, which is `http://localhost:5000` when run locally, or the interceptor service URL when deployed within Kubernetes.

The declared interceptors could be then attached to particular models and applications:

```json
{
    "models": {
        "anthropic.claude-v3-haiku": {
            "type": "chat",
            "iconUrl": "anthropic.svg",
            "endpoint": "${BEDROCK_ADAPTER_SERVICE_URL}/openai/deployments/anthropic.claude-3-haiku-20240307-v1:0/chat/completions",
            "interceptors": [
                "chat-statistics-reporter",
                "chat-reply-as-pirate"
            ]
        }
    }
}
```

Make sure that

1. chat completion interceptors are only used in chat models or application,
2. embeddings interceptors are only used in embeddings models.

The stack of interceptors in DIAL works similarly to a stack of middlewares in Express.js or Django:

```txt
Client -> (original request) ->
  Interceptor 1 -> (modified request #1) ->
    Interceptor 2 -> (modified request #2) ->
      Upstream -> (original response) ->
    Interceptor 2 -> (modified response #1) ->
  Interceptor 1 -> (modified response #2) ->
Client
```

**Every** request/response in the diagram above goes through the DIAL Core. This is hidden from the diagram for brevity.