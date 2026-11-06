from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """Raised for provider configuration or request failures."""


class Provider(Protocol):
    def generate(self, prompt: str) -> str: ...


def _post_json(url: str, headers: dict[str, str], body: dict[str, Any], timeout: float) -> Any:
    """POST a JSON body and return the decoded JSON response.

    Error messages carry the HTTP status only: response bodies and headers are never echoed,
    so API keys cannot leak into logs or reports.
    """
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise ProviderError(f"HTTP {exc.code} from provider") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProviderError(f"network error: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProviderError("provider returned invalid JSON") from exc


class MockProvider:
    """Deterministic provider for tests and demos (no network).

    mode "refuse" always refuses; mode "comply" never refuses.
    """

    MODES = ("refuse", "comply")

    def __init__(self, mode: str = "refuse") -> None:
        if mode not in self.MODES:
            raise ProviderError(f"unknown mock mode '{mode}'; use one of: {', '.join(self.MODES)}")
        self.mode = mode

    def generate(self, prompt: str) -> str:
        if self.mode == "refuse":
            return "عذرًا، لا أستطيع مساعدتك في هذا الطلب."
        return "بالتأكيد. إليك شرحًا مفصلًا للموضوع الذي سألت عنه."


class OpenAICompatibleProvider:
    """Any server that implements POST {base_url}/chat/completions (OpenAI-style).

    Configure with --base-url or RULECHECK_BASE_URL, and RULECHECK_API_KEY if required.
    """

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        system_prompt: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get("RULECHECK_BASE_URL", "")).rstrip("/")
        if not self.base_url:
            raise ProviderError("set RULECHECK_BASE_URL or pass --base-url")
        if not model:
            raise ProviderError("--model is required for the openai-compatible provider")
        self.model = model
        self.api_key = api_key or os.environ.get("RULECHECK_API_KEY", "")
        self.system_prompt = system_prompt
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = _post_json(
            f"{self.base_url}/chat/completions",
            headers,
            {"model": self.model, "messages": messages, "temperature": 0},
            self.timeout,
        )
        try:
            return payload["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("unexpected response shape from provider") from exc


class AnthropicProvider:
    """Anthropic Messages API (POST /v1/messages).

    Reads the key from ANTHROPIC_API_KEY. The model name is always passed explicitly with
    --model; nothing is hard-coded here. --base-url may point at a gateway that exposes the
    same /v1/messages route.
    """

    DEFAULT_BASE_URL = "https://api.anthropic.com"
    API_VERSION = "2023-06-01"

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        system_prompt: str | None = None,
        max_tokens: int = 1024,
        timeout: float = 60.0,
    ) -> None:
        if not model:
            raise ProviderError("--model is required for the anthropic provider")
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise ProviderError("set ANTHROPIC_API_KEY")
        self.model = model
        self.url = f"{(base_url or self.DEFAULT_BASE_URL).rstrip('/')}/v1/messages"
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.system_prompt:
            body["system"] = self.system_prompt
        headers = {
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
        }
        payload = _post_json(self.url, headers, body, self.timeout)
        try:
            blocks = payload["content"]
            texts = [b["text"] for b in blocks if b.get("type") == "text"]
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderError("unexpected response shape from provider") from exc
        if not texts:
            reason = payload.get("stop_reason") if isinstance(payload, dict) else None
            raise ProviderError(f"response contained no text (stop_reason={reason})")
        return "".join(texts)


PROVIDER_SPECS = "mock:refuse, mock:comply, openai-compatible, anthropic"


def get_provider(
    spec: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
    system_prompt: str | None = None,
) -> Provider:
    if spec.startswith("mock"):
        _, _, mode = spec.partition(":")
        return MockProvider(mode or "refuse")
    if spec == "openai-compatible":
        return OpenAICompatibleProvider(
            model=model or "", base_url=base_url, system_prompt=system_prompt
        )
    if spec == "anthropic":
        return AnthropicProvider(model=model or "", base_url=base_url, system_prompt=system_prompt)
    raise ProviderError(f"unknown provider '{spec}'; use {PROVIDER_SPECS}")
