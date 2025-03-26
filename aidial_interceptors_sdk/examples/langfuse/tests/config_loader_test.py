import pytest
import os
import base64
import json
from ai_dial_interceptors_langfuse.config_loader import ConfigLoader
from ai_dial_interceptors_langfuse.config import Config


@pytest.fixture
def setup():
    os.environ.pop(ConfigLoader.CONFIG_KEY, None)
    os.environ.pop(ConfigLoader.CONFIG_BASE64_KEY, None)
    os.environ.pop(ConfigLoader.CONFIG_PATH_KEY, None)


@pytest.fixture
def mock_config():
    return {
        "organisations": {
            "org_1": {
                "langfuse": {
                    "secret_key": "dial_secret_key_2",
                    "public_key": "dial_public_key_2",
                },
            }
        },
        "deployments": {
            "default": {
                "track_user_data": True,
                "langfuse": {
                    "secret_key": "dial_secret_key",
                    "public_key": "dial_public_key",
                    "host": "http://host.docker.internal:4000",
                },
            },
            "mistral": {
                "organisation": "org_1",
                "track_user_data": False,
            },
        },
    }


@pytest.fixture
def mock_env_config(mock_config):
    return json.dumps(mock_config)


@pytest.fixture
def mock_env_config_base64(mock_env_config):
    string_bytes = mock_env_config.encode("utf-8")
    base64_bytes = base64.b64encode(string_bytes)
    base64_string = base64_bytes.decode("utf-8")
    return base64_string


def test_load_default_config(setup, mock_env_config):
    os.environ[ConfigLoader.CONFIG_KEY] = mock_env_config
    loader = ConfigLoader()
    config = loader.load()
    assert isinstance(config, Config)
    assert config.track_user_data
    assert config.langfuse.secret_key == "dial_secret_key"
    assert config.langfuse.public_key == "dial_public_key"
    assert config.langfuse.host == "http://host.docker.internal:4000"


def test_load_default_from_config_base64(setup, mock_env_config_base64):
    os.environ[ConfigLoader.CONFIG_BASE64_KEY] = mock_env_config_base64
    loader = ConfigLoader()
    config = loader.load()
    assert isinstance(config, Config)
    assert config.track_user_data
    assert config.langfuse.secret_key == "dial_secret_key"
    assert config.langfuse.public_key == "dial_public_key"
    assert config.langfuse.host == "http://host.docker.internal:4000"


def test_load_default_from_config_path(setup, mock_env_config, tmp_path):
    file_path = tmp_path / "config.json"
    file_path.write_text(mock_env_config)
    os.environ[ConfigLoader.CONFIG_PATH_KEY] = str(file_path)
    loader = ConfigLoader()
    config = loader.load()
    assert isinstance(config, Config)
    assert config.track_user_data
    assert config.langfuse.secret_key == "dial_secret_key"
    assert config.langfuse.public_key == "dial_public_key"
    assert config.langfuse.host == "http://host.docker.internal:4000"


def test_load_mistral_config(setup, mock_env_config):
    os.environ[ConfigLoader.CONFIG_KEY] = mock_env_config
    loader = ConfigLoader()
    config = loader.load("mistral")
    assert isinstance(config, Config)
    assert not config.track_user_data
    assert config.langfuse.secret_key == "dial_secret_key_2"
    assert config.langfuse.public_key == "dial_public_key_2"
    assert config.langfuse.host == "http://host.docker.internal:4000"


def test_load_not_exists_config(setup, mock_env_config):
    os.environ[ConfigLoader.CONFIG_KEY] = mock_env_config
    loader = ConfigLoader()
    config = loader.load("not-exists")
    assert isinstance(config, Config)
    assert config.track_user_data
    assert config.langfuse.secret_key == "dial_secret_key"
    assert config.langfuse.public_key == "dial_public_key"
    assert config.langfuse.host == "http://host.docker.internal:4000"


def test_load_raises_error_when_no_env(setup):
    with pytest.raises(ValueError, match="CONFIG and CONFIG_BASE64 not found in ENV"):
        ConfigLoader()
