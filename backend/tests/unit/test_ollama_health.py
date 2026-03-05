import pytest

from providers.llm.ollama_local import OllamaLocalProvider
from providers.llm.prompt_builder import PromptBuilder


@pytest.mark.asyncio
async def test_health_reports_degraded_when_model_missing(monkeypatch):
    provider = OllamaLocalProvider(
        base_url="http://localhost:11434",
        model="missing-model:latest",
        prompt_builder=PromptBuilder(),
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"models": [{"name": "llama3.2:3b"}]}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            return FakeResponse()

    monkeypatch.setattr("providers.llm.ollama_local.httpx.AsyncClient", lambda timeout=3.0: FakeClient())

    status, detail = await provider.health()
    assert status == "degraded"
    assert "not available" in (detail or "").lower()
