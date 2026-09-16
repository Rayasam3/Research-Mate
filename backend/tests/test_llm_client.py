import httpx
import pytest

from app.core.config import settings
from app.services import llm_client
from app.services.llm_client import LlmError, generate_json


@pytest.fixture(autouse=True)
def _reset_provider():
    original = settings.llm_provider
    yield
    settings.llm_provider = original


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code
        self.text = str(json_data)

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://fake")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self):
        return self._json_data


@pytest.mark.asyncio
async def test_generate_json_ollama_success(monkeypatch):
    settings.llm_provider = "ollama"

    async def fake_post(self, url, json=None, headers=None):
        return _FakeResponse({"response": '{"tldr": "hello"}'})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await generate_json("some prompt")
    assert result == {"tldr": "hello"}


@pytest.mark.asyncio
async def test_generate_json_ollama_connect_error(monkeypatch):
    settings.llm_provider = "ollama"

    async def fake_post(self, url, json=None, headers=None):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(LlmError, match="Could not connect to Ollama"):
        await generate_json("some prompt")


@pytest.mark.asyncio
async def test_generate_json_groq_success(monkeypatch):
    settings.llm_provider = "groq"
    monkeypatch.setattr(settings, "groq_api_key", "fake-key")

    async def fake_post(self, url, json=None, headers=None):
        return _FakeResponse(
            {"choices": [{"message": {"content": '{"tldr": "hello from groq"}'}}]}
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await generate_json("some prompt")
    assert result == {"tldr": "hello from groq"}


@pytest.mark.asyncio
async def test_generate_json_groq_missing_api_key(monkeypatch):
    settings.llm_provider = "groq"
    monkeypatch.setattr(settings, "groq_api_key", "")

    with pytest.raises(LlmError, match="GROQ_API_KEY"):
        await generate_json("some prompt")


@pytest.mark.asyncio
async def test_generate_json_groq_http_error(monkeypatch):
    settings.llm_provider = "groq"
    monkeypatch.setattr(settings, "groq_api_key", "fake-key")

    async def fake_post(self, url, json=None, headers=None):
        return _FakeResponse({"error": "bad request"}, status_code=400)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(LlmError, match="Groq request failed"):
        await generate_json("some prompt")


@pytest.mark.asyncio
async def test_generate_json_invalid_json_response(monkeypatch):
    settings.llm_provider = "ollama"

    async def fake_post(self, url, json=None, headers=None):
        return _FakeResponse({"response": "not valid json"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    with pytest.raises(LlmError, match="wasn't valid JSON"):
        await generate_json("some prompt")