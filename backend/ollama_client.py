"""Small Ollama generate API client with environment-configurable endpoint and model."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from pathlib import Path

import yaml


class OllamaError(RuntimeError):
    """Raised when inference configuration or the Ollama request is invalid."""


class OllamaClient:
    def __init__(self, host: str | None = None, model: str | None = None, timeout: int = 60):
        config_path = Path(os.getenv("CONFIG_FILE", "config.yaml"))
        config = {}
        if config_path.is_file():
            try:
                loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as exc:
                raise OllamaError("Unable to read Ollama configuration file") from exc
            if isinstance(loaded, dict):
                config = loaded
        inference = config.get("inference", {})
        inference = inference if isinstance(inference, dict) else {}
        configured_host = host or os.getenv("OLLAMA_HOST") or inference.get("host") or ""
        configured_model = model or os.getenv("OLLAMA_MODEL") or inference.get("model") or ""
        self.host = str(configured_host).rstrip("/")
        self.model = str(configured_model)
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        if not self.host or not self.model:
            raise OllamaError("Set OLLAMA_HOST and OLLAMA_MODEL before requesting inference")
        payload = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": False}
        ).encode()
        request = Request(
            f"{self.host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise OllamaError(
                "Ollama request failed; check the configured host, model, and server status"
            ) from exc
        result = body.get("response")
        if not isinstance(result, str):
            raise OllamaError("Ollama response did not contain generated text")
        return result
