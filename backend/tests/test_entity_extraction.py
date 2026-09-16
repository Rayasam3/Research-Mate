import pytest

from app.services import entity_extraction
from app.services.entity_extraction import extract_entities
from app.services.llm_client import LlmError


@pytest.mark.asyncio
async def test_extract_entities_empty_chunks_returns_empty():
    result = await extract_entities("Some Title", [])
    assert result == {"methods": [], "datasets": []}


@pytest.mark.asyncio
async def test_extract_entities_success(monkeypatch):
    async def fake_generate_json(prompt):
        return {"methods": ["Transformer", "self-attention"], "datasets": ["ImageNet"]}

    monkeypatch.setattr(entity_extraction, "generate_json", fake_generate_json)

    result = await extract_entities("A Paper", ["some chunk text"])
    assert result["methods"] == ["Transformer", "self-attention"]
    assert result["datasets"] == ["ImageNet"]


@pytest.mark.asyncio
async def test_extract_entities_dedupes_and_strips_whitespace(monkeypatch):
    async def fake_generate_json(prompt):
        return {"methods": ["ResNet", "  ResNet  ", "ResNet"], "datasets": [" CIFAR-100 "]}

    monkeypatch.setattr(entity_extraction, "generate_json", fake_generate_json)

    result = await extract_entities("A Paper", ["chunk"])
    assert result["methods"] == ["ResNet"]
    assert result["datasets"] == ["CIFAR-100"]


@pytest.mark.asyncio
async def test_extract_entities_llm_failure_returns_empty(monkeypatch):
    async def fake_generate_json(prompt):
        raise LlmError("boom")

    monkeypatch.setattr(entity_extraction, "generate_json", fake_generate_json)

    result = await extract_entities("A Paper", ["chunk"])
    assert result == {"methods": [], "datasets": []}


def test_build_extraction_prompt_includes_title_and_chunks():
    prompt = entity_extraction.build_extraction_prompt("My Title", ["chunk text here"])
    assert "My Title" in prompt
    assert "chunk text here" in prompt