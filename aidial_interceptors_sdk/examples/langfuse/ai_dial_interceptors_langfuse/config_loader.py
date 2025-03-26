from .config import Config

import os
import json
import base64


class ConfigLoader:
    CONFIG_KEY = "CONFIG"
    CONFIG_BASE64_KEY = "CONFIG_BASE64"
    CONFIG_PATH_KEY = "CONFIG_PATH"
    DEFAULT_KEY = "default"

    def __init__(self):
        self.config = self._load_all()
        self.deployments = self.config.get("deployments")
        self.organisations = self.config.get("organisations")

    def load(self, keyword: str = "") -> Config:
        default_config = {}
        config = {}
        if self.is_present(self.DEFAULT_KEY):
            default_config = self._load_deployment(self.DEFAULT_KEY)
        if keyword != "" and self.is_present(keyword):
            config = self._load_deployment(keyword)
        config = self._merge_dicts(default_config, config)
        return Config.model_validate(config)

    def is_present(self, keyword) -> bool:
        return keyword in self.deployments

    def _load_all(self) -> dict:
        config_json = os.environ.get(self.CONFIG_KEY)
        config_base64_json = os.environ.get(self.CONFIG_BASE64_KEY)
        config_path = os.environ.get(self.CONFIG_PATH_KEY)
        if config_json is None and config_base64_json is not None:
            config_json = base64.b64decode(config_base64_json.encode()).decode("utf-8")
        if config_json is None and config_path is not None:
            with open(config_path, "r", encoding="utf-8") as f:
                config_json = f.read()
        if config_json is None:
            raise ValueError(
                f"{self.CONFIG_KEY} and {self.CONFIG_BASE64_KEY} not found in ENV."
            )
        return json.loads(config_json)

    def _load_deployment(self, key) -> dict:
        config = self.deployments[key] if self.deployments else {}
        if self.organisations and "organisation" in config:
            org_config = self.organisations[config["organisation"]]
            config = self._merge_dicts(org_config, config)
        return config

    def _merge_dicts(self, dict1: dict, dict2: dict) -> dict:
        merged = dict1.copy()
        for key, value in dict2.items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                merged[key] = self._merge_dicts(merged[key], value)
            else:
                merged[key] = value
        return merged
