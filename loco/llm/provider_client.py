"""Minimal chat-provider client for Stage 3.2.

This module uses only the Python standard library. It sends a chat completion
request and returns sanitized artifacts that never contain API keys or
authorization headers.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class LLMClientConfig:
    api_key: str
    base_url: str
    model: str
    wire_api: str = "chat"
    reasoning_effort: str = "high"
    timeout_seconds: int = 60


@dataclass(frozen=True)
class ChatCompletionResult:
    content: str
    raw_response: Mapping[str, Any]
    sanitized_response: Mapping[str, Any]
    provenance: Mapping[str, Any]

    def to_artifact_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "loco.stage3_2_chat_response.v1",
            "content": self.content,
            "sanitized_response": dict(self.sanitized_response),
            "provenance": dict(self.provenance),
            "secret_redacted": True,
        }


def load_llm_config_from_env(env_path: Path | str | None = None) -> LLMClientConfig:
    values = dict(os.environ)
    if env_path is not None and Path(env_path).is_file():
        values |= _read_env_file(Path(env_path))

    return LLMClientConfig(
        api_key=_required(values, "LLM_API_KEY"),
        base_url=_required(values, "LLM_BASE_URL").rstrip("/"),
        model=_required(values, "LLM_MODEL"),
        reasoning_effort=values.get("LLM_REASONING_EFFORT", "high"),
        wire_api=values.get("LLM_WIRE_API", "chat"),
    )


def call_chat_completion(
    config: LLMClientConfig,
    *,
    messages: Sequence[Mapping[str, str]],
    temperature: float,
) -> ChatCompletionResult:
    if config.wire_api != "chat":
        raise ValueError("Stage 3.2 only supports LLM_WIRE_API=chat.")
    if not config.api_key:
        raise ValueError("LLM_API_KEY must be set.")

    endpoint = _chat_endpoint(config.base_url)
    payload = {
        "model": config.model,
        "messages": [dict(message) for message in messages],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    if config.reasoning_effort:
        payload["reasoning_effort"] = config.reasoning_effort

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=config.timeout_seconds
        ) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM chat request failed: HTTP {exc.code}: {body}") from exc

    content = _extract_content(raw)
    return ChatCompletionResult(
        content=content,
        raw_response=raw,
        sanitized_response=_sanitize_response(raw),
        provenance={
            "base_url_host": urllib.parse.urlparse(config.base_url).hostname,
            "model": config.model,
            "wire_api": config.wire_api,
            "reasoning_effort": config.reasoning_effort,
            "endpoint_path": urllib.parse.urlparse(endpoint).path,
        },
    )


def _chat_endpoint(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("LLM_BASE_URL must be an absolute URL.")
    path = parsed.path.rstrip("/")
    if path.endswith("/chat/completions"):
        return base_url
    return urllib.parse.urlunparse(parsed._replace(path=f"{path}/chat/completions"))


def _extract_content(raw: Mapping[str, Any]) -> str:
    choices = raw.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("LLM response missing choices.")
    message = choices[0].get("message")
    if not isinstance(message, Mapping):
        raise ValueError("LLM response choice missing message.")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("LLM response message.content must be a non-empty string.")
    return content


def _sanitize_response(raw: Mapping[str, Any]) -> dict[str, Any]:
    sanitized = json.loads(json.dumps(raw))
    for choice in sanitized.get("choices", []):
        message = choice.get("message")
        if isinstance(message, dict) and "content" in message:
            message["content"] = "<omitted>"
    return sanitized


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _required(values: Mapping[str, str], key: str) -> str:
    value = values.get(key)
    if not value:
        raise ValueError(f"{key} must be set.")
    return value
