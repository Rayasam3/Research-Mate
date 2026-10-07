from datetime import date

import pytest

from app.schemas.paper import Paper, PaperSource
from app.schemas.summary import SummaryStatus
from app.services import summarizer
from app.services.llm_client import LlmError


async def _async_return(value):
    return value

def _paper(**overrides) -> Paper:
    defaults = dict(
        external_id="1706.03762",
        source=PaperSource.ARXIV,
        title="Attention Is All You Need",
        authors=["Ashish Vaswani"],
        abstract="A transformer paper.",
        published_date=date(2017, 6, 12),
        pdf_url="https://arxiv.org/pdf/1706.03762",
        doi="10.48550/arXiv.1706.03762",
        url="https://arxiv.org/abs/1706.03762",
    )
    defaults.update(overrides)
    return Paper(**defaults)


_FAKE_LLM_RESPONSE = {
    "tldr": "This paper introduces the Transformer architecture.",
    "problem": "Sequence modeling relied on slow, sequential recurrent networks.",
    "method_explained": "It uses self-attention to relate all positions in a sequence at once.",
    "key_results": "Achieved 28.4 BLEU on WMT 2014 English-to-German translation.",
    "limitations": "Quadratic memory cost with sequence length.",
}


@pytest.mark.asyncio
async def test_summarize_paper_not_ingested(monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "cache_dir", str(tmp_path))
    monkeypatch.setattr(summarizer, "load_paper_metadata", lambda paper_id: None)

    result = await summarizer.summarize_paper("nonexistent_paper")
    assert result["status"] == SummaryStatus.NOT_INGESTED
    assert result["card"] is None


@pytest.mark.asyncio
async def test_summarize_paper_no_chunks(monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "cache_dir", str(tmp_path))
    monkeypatch.setattr(summarizer, "load_paper_metadata", lambda paper_id: _paper())
    monkeypatch.setattr(summarizer, "get_chunks_for_paper", lambda paper_id, limit=None: [])

    result = await summarizer.summarize_paper("some_paper")
    assert result["status"] == SummaryStatus.NO_CHUNKS_AVAILABLE


@pytest.mark.asyncio
async def test_summarize_paper_llm_connection_failure(monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "cache_dir", str(tmp_path))
    monkeypatch.setattr(summarizer, "load_paper_metadata", lambda paper_id: _paper())
    monkeypatch.setattr(summarizer, "get_chunks_for_paper", lambda paper_id, limit=None: ["some chunk text"])

    async def fake_generate_json(prompt):
        raise LlmError("Could not connect to Ollama")

    monkeypatch.setattr(summarizer, "generate_json", fake_generate_json)

    result = await summarizer.summarize_paper("some_paper")
    assert result["status"] == SummaryStatus.LLM_FAILED
    assert "Ollama" in result["message"]


@pytest.mark.asyncio
async def test_summarize_paper_llm_missing_fields(monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "cache_dir", str(tmp_path))
    monkeypatch.setattr(summarizer, "load_paper_metadata", lambda paper_id: _paper())
    monkeypatch.setattr(summarizer, "get_chunks_for_paper", lambda paper_id, limit=None: ["chunk"])

    async def fake_generate_json(prompt):
        return {"tldr": "Only this field is present."}

    monkeypatch.setattr(summarizer, "generate_json", fake_generate_json)

    result = await summarizer.summarize_paper("some_paper")
    assert result["status"] == SummaryStatus.LLM_FAILED
    assert "missing" in result["message"].lower()


@pytest.mark.asyncio
async def test_summarize_paper_full_success(monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "cache_dir", str(tmp_path))
    monkeypatch.setattr(summarizer, "load_paper_metadata", lambda paper_id: _paper())
    monkeypatch.setattr(summarizer, "get_chunks_for_paper", lambda paper_id, limit=None: ["chunk 1", "chunk 2"])

    async def fake_generate_json(prompt):
        return dict(_FAKE_LLM_RESPONSE)

    monkeypatch.setattr(summarizer, "generate_json", fake_generate_json)

    result = await summarizer.summarize_paper("arxiv_1706.03762")
    assert result["status"] == SummaryStatus.SUCCESS
    card = result["card"]
    assert card.tldr == _FAKE_LLM_RESPONSE["tldr"]
    assert "Vaswani, A." in card.citation_apa
    assert card.citation_bibtex.startswith("@article{")


@pytest.mark.asyncio
async def test_summarize_paper_uses_cache_on_second_call(monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "cache_dir", str(tmp_path))
    monkeypatch.setattr(summarizer, "load_paper_metadata", lambda paper_id: _paper())
    monkeypatch.setattr(summarizer, "get_chunks_for_paper", lambda paper_id, limit=None: ["chunk"])

    call_count = {"n": 0}

    async def fake_generate_json(prompt):
        call_count["n"] += 1
        return dict(_FAKE_LLM_RESPONSE)

    monkeypatch.setattr(summarizer, "generate_json", fake_generate_json)

    first = await summarizer.summarize_paper("arxiv_1706.03762")
    second = await summarizer.summarize_paper("arxiv_1706.03762")

    assert call_count["n"] == 1
    assert first["card"].tldr == second["card"].tldr
    assert second["status"] == SummaryStatus.ALREADY_CACHED


def test_build_prompt_includes_title_abstract_and_excerpts():
    prompt = summarizer.build_prompt("My Paper Title", "The full abstract text.", ["excerpt one", "excerpt two"])
    assert "My Paper Title" in prompt
    assert "The full abstract text." in prompt
    assert "excerpt one" in prompt
    assert "excerpt two" in prompt


def test_get_abstract_prefers_pdf_text_over_search_source():
    pdf_text = "Title\nAbstract— " + "We study graphs in depth. " * 20 + "\nIndex Terms— graphs\nI. INTRODUCTION\nBody"
    abstract = summarizer.get_abstract(_paper(abstract="short metadata abstract"), pdf_text)
    assert abstract.startswith("We study graphs")
    assert "Index Terms" not in abstract


def test_get_abstract_falls_back_to_search_source():
    abstract = summarizer.get_abstract(_paper(abstract="metadata abstract"), "no abstract heading in this text")
    assert abstract == "metadata abstract"


def test_pick_excerpts_uses_intro_experiments_and_conclusion():
    text = (
        "Title\n1 Introduction\nWe propose a new model. Our contributions are listed here.\n"
        "2 Method\nThe model works like this.\n"
        "3 Experiments\nOur model reaches 91.2% accuracy on Cora.\n"
        "4 Conclusion\nWe showed it works. Future work is needed.\n"
        "References\n[1] Someone"
    )
    joined = "\n".join(summarizer.pick_excerpts(text, ""))
    assert "contributions" in joined
    assert "91.2%" in joined
    assert "Future work" in joined
    assert "Someone" not in joined
