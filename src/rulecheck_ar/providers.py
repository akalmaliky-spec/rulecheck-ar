from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Protocol


class ProviderError(RuntimeError):
    """Raised for provider configuration or request failures."""


class Provider(Protocol):
    def generate(self, prompt: str) -> str: ...


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
        body = json.dumps({"model": self.model, "messages": messages, "temperature": 0})
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            raise ProviderError(f"HTTP {exc.code} from provider") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ProviderError(f"network error: {exc}") from exc
        try:
            return payload["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("unexpected response shape from provider") from exc


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
    raise ProviderError(
        f"unknown provider '{spec}'; use mock:refuse, mock:comply, openai-compatible"
    )
