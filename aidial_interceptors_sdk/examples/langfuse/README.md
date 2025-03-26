# ai-dial-interceptors-langfuse

Implements AI DIAL integration with [Langfuse](https://langfuse.com/) using [ai-dial-interceptors-sdk](https://github.com/epam/ai-dial-interceptors-sdk) for trace collection.

### Requirements

1. [DIAL](https://epam-rail.com/)
2. [Langfuse](https://langfuse.com/)

### Run

`docker compose up`

### Example of config.json for DIAL-CORE

```json
{
  "routes": {},
  "interceptors": {
    "langfuse": {
        "endpoint": "http://host.docker.internal:8081/openai/deployments/langfuse/chat/completions"
    }
  },
  "models": {
    "gpt-4o": {
      "type": "chat",
      "displayName": "Self-hosted chat model",
      "endpoint": "http://ollama:11434/v1/chat/completions",
      "interceptors": [
        "langfuse"
      ]
    }
  },
  "keys": {
    "dial_api_key": {
      "project": "TEST-PROJECT",
      "role": "default"
    }
  },
  "roles": {
    "default": {
      "limits": {
        "gpt-4o": {}
      }
    }
  }
}
```

### Langfuse run locally

[Manual](https://langfuse.com/self-hosting/local)


### Custom content (state)

1. langfuse_session_id - saves the session ID between requests

### Tokens

Langfuse automatically calculates tokens and price for each trace when model is present in the list "Trace->Models" on the Langfuse side.

### Config

The configuration is in JSON format. 
The first-level keys in the "deployments" segment are named after a specific model, assistant, or application.
"Default" is a mandatory key that contains default values for "deployments" segment.

### Config list

| Path | Name | Description | Type | Example |
| ---- | ---- | ----------- | ---- | ------- |
| organisations.org_example | track_user_data | Activate tracking user data | boolean | true |
| organisations.org_example.langfuse | secret_key | Secret key of the project  | string | sk-...-fce19b5f1322 |
| organisations.org_example.langfuse | public_key | Public key of the project  | string | pk-...-e9e8a18915c4 |
| organisations.org_example.langfuse | host | Langfuse server host  | string | http://host.docker.internal:4000 |
| deployments.default | organisation | Organisation id | sting | org_example |
| deployments.default | track_user_data | Activate tracking user data | boolean | true |
| deployments.default.langfuse | secret_key | Secret key of the project  | string | sk-...-fce19b5f1322 |
| deployments.default.langfuse | public_key | Public key of the project  | string | pk-...-e9e8a18915c4 |
| deployments.default.langfuse | host | Langfuse server host  | string | http://host.docker.internal:4000 |

### Config example

```json
{
  "organisations": {
      "org_1": {
        "track_user_data": true,
        "langfuse": {
          "secret_key": "dial_secret_key",
          "public_key": "dial_secret_key",
          "host": "http://host.docker.internal:4000"
        }
      },
      "org_2": {
        "track_user_data": false,
        "langfuse": {
          "secret_key": "dial_secret_key_2",
          "public_key": "dial_secret_key_2",
          "host": "http://host.docker.internal:4000"
        }
      }
  },
  "deployments": {
    "default": {
      "organisation": "org_1"
    },
    "gpt-4o": {
      "organisation": "org_2"
    },
    "gpt-4o-mini": {
      "organisation": "org_2",
      "track_user_data": true
    }
  }
}
```

### ENVs

| Name | Required | Description | Default value | Example |
| ---- | -------- | ----------- | ------------- | ------- |
| DIAL_URL | true | DIAL server URL (not a chat URL) || http://host.docker.internal:8080 |
| CONFIG | false | Stores separate Langfuse configurations for each deployment. Represents a JSON string. The "default" key is required. Optional if CONFIG_BASE64 or CONFIG_PATH is present. || [Config example](#config-example) |
| CONFIG_BASE64 | false | Encoded value of `CONFIG`. Base64 is used for encoding. Optional if CONFIG or CONFIG_PATH is present. || [Config example](#config-example) |
| CONFIG_PATH | false | Contains the path to the configuration file. Optional if CONFIG or CONFIG_PATH is present. || [Config example](#config-example) |


### Commands

1. `make install` - install dependencies
1. `make lint` - run linters
1. `make format` - run code formatters

## TODO

1. Rate (aidial-interceptors-sdk does not support rate endpoint at this moment). The [issue](https://github.com/epam/ai-dial-interceptors-sdk/issues/31)
2. Use "X-Conversation-ID" instead of "langfuse_session_id" after resolving the [issue](https://github.com/epam/ai-dial-chat/issues/3345)

