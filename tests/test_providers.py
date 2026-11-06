import io
import json
import urllib.error

import pytest

from rulecheck_ar import providers
from rulecheck_ar.providers import (
    AnthropicProvider,
    OpenAICompatibleProvider,
    ProviderError,
    get_provider,
)


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _install_fake(monkeypatch, payload=None, error=None):
    """Replace urlopen; returns a dict that records the last request."""
    seen = {}

    def fake_urlopen(request, timeout=None):
        seen["url"] = request.full_url
        seen["headers"] = {k.lower(): v for k, v in request.header_items()}
        seen["body"] = json.loads(request.data.decode("utf-8"))
        seen["timeout"] = timeout
        if error is not None:
            raise error
        return _FakeResponse(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr(providers.urllib.request, "urlopen", fake_urlopen)
    return seen


def test_anthropic_request_shape_and_text_extraction(monkeypatch):
    seen = _install_fake(
        monkeypatch,
        {
            "content": [
                {"type": "text", "text": "مرحبًا "},
                {"type": "tool_use", "id": "x"},
                {"type": "text", "text": "بك"},
            ],
            "stop_reason": "end_turn",
        },
    )
    provider = AnthropicProvider(model="some-model", api_key="k-123", system_prompt="قواعد")
    assert provider.generate("سؤال") == "مرحبًا بك"
    assert seen["url"] == "https://api.anthropic.com/v1/messages"
    assert seen["headers"]["x-api-key"] == "k-123"
    assert seen["headers"]["anthropic-version"] == AnthropicProvider.API_VERSION
    assert seen["body"]["model"] == "some-model"
    assert seen["body"]["system"] == "قواعد"
    assert seen["body"]["messages"] == [{"role": "user", "content": "سؤال"}]
    assert seen["body"]["max_tokens"] == 1024


def test_anthropic_omits_system_when_not_given_and_honours_base_url(monkeypatch):
    seen = _install_fake(monkeypatch, {"content": [{"type": "text", "text": "ok"}]})
    provider = AnthropicProvider(model="m", api_key="k", base_url="https://gw.example/")
    provider.generate("hi")
    assert "system" not in seen["body"]
    assert seen["url"] == "https://gw.example/v1/messages"


def test_anthropic_requires_key_and_model(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider(model="m")
    with pytest.raises(ProviderError, match="--model"):
        AnthropicProvider(model="", api_key="k")


def test_anthropic_key_comes_from_environment(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
    seen = _install_fake(monkeypatch, {"content": [{"type": "text", "text": "ok"}]})
    get_provider("anthropic", model="m").generate("hi")
    assert seen["headers"]["x-api-key"] == "from-env"


def test_anthropic_empty_content_is_an_error_with_stop_reason(monkeypatch):
    _install_fake(monkeypatch, {"content": [], "stop_reason": "refusal"})
    with pytest.raises(ProviderError, match="stop_reason=refusal"):
        AnthropicProvider(model="m", api_key="k").generate("hi")


def test_anthropic_unexpected_shape(monkeypatch):
    _install_fake(monkeypatch, {"nope": 1})
    with pytest.raises(ProviderError, match="unexpected response shape"):
        AnthropicProvider(model="m", api_key="k").generate("hi")


def test_http_error_message_has_status_only(monkeypatch):
    error = urllib.error.HTTPError("https://x", 401, "Unauthorized", {}, io.BytesIO(b"secret-body"))
    _install_fake(monkeypatch, error=error)
    with pytest.raises(ProviderError) as info:
        AnthropicProvider(model="m", api_key="super-secret-key").generate("hi")
    assert str(info.value) == "HTTP 401 from provider"
    assert "super-secret-key" not in str(info.value)
    assert "secret-body" not in str(info.value)


def test_network_error_is_wrapped(monkeypatch):
    _install_fake(monkeypatch, error=urllib.error.URLError("boom"))
    with pytest.raises(ProviderError, match="network error"):
        AnthropicProvider(model="m", api_key="k").generate("hi")


def test_openai_compatible_request_shape(monkeypatch):
    seen = _install_fake(monkeypatch, {"choices": [{"message": {"content": "رد"}}]})
    provider = OpenAICompatibleProvider(
        model="m", base_url="https://gw.example/v1/", api_key="k", system_prompt="s"
    )
    assert provider.generate("q") == "رد"
    assert seen["url"] == "https://gw.example/v1/chat/completions"
    assert seen["headers"]["authorization"] == "Bearer k"
    assert seen["body"]["messages"][0] == {"role": "system", "content": "s"}
    assert seen["body"]["messages"][1] == {"role": "user", "content": "q"}


def test_openai_compatible_unexpected_shape(monkeypatch):
    _install_fake(monkeypatch, {"choices": []})
    provider = OpenAICompatibleProvider(model="m", base_url="https://gw.example/v1")
    with pytest.raises(ProviderError, match="unexpected response shape"):
        provider.generate("q")


def test_unknown_provider_lists_anthropic():
    with pytest.raises(ProviderError, match="anthropic"):
        get_provider("nope")
