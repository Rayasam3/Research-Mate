import pytest

from app.core.config import settings
from app.schemas.paper_record import MethodMention, PaperRecord, ResultItem
from app.services import record_extraction as rx
from app.services.llm_client import LlmError

PAPER_TEXT = """Graph Attention for ECG Classification
A. Author, B. Author

Abstract
We propose ECG-GAT, a graph attention network for arrhythmia classification.

1 Introduction
Cardiac arrhythmia detection is important for early diagnosis in cardiology.

2 Related Work
Prior work used support vector machines and plain CNNs on ECG signals.

3 Method
ECG-GAT builds a graph over heartbeats and applies multi-head attention.

4 Experiments
We evaluate on the MIT-BIH dataset and the PTB-XL dataset. ECG-GAT reaches 98.1 accuracy on MIT-BIH.

5 Conclusion
The model needs labelled data. We plan to study self-supervised pretraining.

References
[1] Some cited paper about support vector machines.
"""


def _chunk(text, size=300, overlap=60):
    out, start = [], 0
    while start < len(text):
        out.append(text[start : start + size])
        if start + size >= len(text):
            break
        start += size - overlap
    return out


def test_reassemble_restores_original_text(monkeypatch):
    monkeypatch.setattr(settings, "chunk_overlap_chars", 60)
    chunks = _chunk(PAPER_TEXT)
    assert len(chunks) > 1
    assert rx.reassemble(chunks) == PAPER_TEXT


def test_split_sections_finds_sections_and_drops_noise():
    sections = rx.split_sections(PAPER_TEXT)
    assert "ECG-GAT, a graph attention network" in sections["intro"]
    assert "multi-head attention" in sections["method"]
    assert "MIT-BIH" in sections["experiments"]
    assert "self-supervised pretraining" in sections["conclusion"]
    joined = " ".join(sections.values())
    assert "support vector machines" not in joined  # related work and references dropped


def test_split_sections_falls_back_to_position_without_headings():
    text = "plain text without any headings. " * 200
    sections = rx.split_sections(text)
    assert all(sections[name] for name in ("intro", "method", "experiments", "conclusion"))


def test_select_windows_spreads_evenly_and_respects_cap():
    text = "\n".join(f"line {i} " + "x" * 50 for i in range(400))
    windows = rx.select_windows(text, 1000, 3)
    assert len(windows) == 3
    assert "line 0 " in windows[0] and "line 399 " in windows[-1]
    assert rx.select_windows("", 1000, 3) == []
    assert len(rx.select_windows("short text", 1000, 3)) == 1


def test_parsers_survive_malformed_llm_output():
    assert rx._parse_method_pass("not a dict").methods == []
    record = rx._parse_method_pass(
        {"domain": "Cardiology", "task": None, "methods": ["GNN", {"name": "X", "role": "weird"}, 5, {"role": "used"}]}
    )
    assert record.domain == "Cardiology"
    assert [m.name for m in record.methods] == ["GNN", "X"]
    assert record.methods[1].role == "used"  # invalid role coerced

    experiments = rx._parse_experiment_pass(
        {"datasets": ["A", {"name": "B"}, None], "results": [{"method": "m", "dataset": "A", "value": 9}, {"method": "only"}]}
    )
    assert experiments.datasets == ["A", "B"]
    assert len(experiments.results) == 1 and experiments.results[0].value == "9"

    conclusion = rx._parse_conclusion_pass({"limitations": ["needs data", ""], "future_work": "not a list"})
    assert conclusion.limitations == ["needs data"] and conclusion.future_work == []


def test_merge_records_dedupes_and_keeps_strongest_role():
    a = PaperRecord(
        domain="Cardiology",
        methods=[MethodMention(name="GNN", role="used"), MethodMention(name="SVM", role="baseline")],
        datasets=["MIT-BIH"],
        limitations=["Needs labels"],
    )
    b = PaperRecord(
        task="ECG classification",
        methods=[MethodMention(name="Graph Neural Network (GNN)", role="proposed", novelty="new attention")],
        datasets=["mit-bih", "PTB-XL"],
        results=[ResultItem(method="GNN", dataset="MIT-BIH", metric="acc", value="98")],
        limitations=["needs  labels"],
    )
    merged = rx.merge_records([a, b])
    assert merged.domain == "Cardiology" and merged.task == "ECG classification"
    gnn = [m for m in merged.methods if rx.normalize_key(m.name) == "graph neural network"]
    assert len(gnn) == 1 and gnn[0].role == "proposed" and gnn[0].novelty == "new attention"
    assert len(merged.methods) == 2
    assert merged.datasets == ["MIT-BIH", "PTB-XL"]
    assert len(merged.limitations) == 1


def _fake_llm_factory(calls):
    async def fake_generate_json(prompt):
        calls.append(prompt)
        if '"domain"' in prompt:
            return {"domain": "Cardiology", "task": "ECG classification",
                    "methods": [{"name": "ECG-GAT", "role": "proposed", "novelty": "graph over heartbeats"}]}
        if '"datasets"' in prompt:
            return {"datasets": ["MIT-BIH", "PTB-XL"],
                    "results": [{"method": "ECG-GAT", "dataset": "MIT-BIH", "metric": "accuracy", "value": "98.1"}]}
        return {"limitations": ["Needs labelled data"], "future_work": ["Self-supervised pretraining"]}

    return fake_generate_json


@pytest.mark.asyncio
async def test_extract_paper_record_runs_three_passes_and_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "chunk_overlap_chars", 60)
    monkeypatch.setattr(settings, "cache_dir", str(tmp_path))
    monkeypatch.setattr(settings, "record_call_gap_seconds", 0)
    monkeypatch.setattr(rx, "get_chunks_for_paper", lambda paper_id: _chunk(PAPER_TEXT))
    calls = []
    monkeypatch.setattr(rx, "generate_json", _fake_llm_factory(calls))

    record = await rx.extract_paper_record("arxiv_1", "ECG-GAT")

    assert len(calls) == 3  # one window per pass for a short paper
    assert record.domain == "Cardiology"
    assert [m.name for m in record.methods] == ["ECG-GAT"] and record.methods[0].role == "proposed"
    assert record.datasets == ["MIT-BIH", "PTB-XL"]
    assert record.results[0].value == "98.1"
    assert record.limitations == ["Needs labelled data"] and record.future_work == ["Self-supervised pretraining"]
    assert not any("support vector" in c for c in calls)  # related work never sent to the LLM

    # Second call is served from cache: no new LLM calls, even with no chunks available.
    monkeypatch.setattr(rx, "get_chunks_for_paper", lambda paper_id: [])
    again = await rx.extract_paper_record("arxiv_1", "ECG-GAT")
    assert len(calls) == 3 and again == record


@pytest.mark.asyncio
async def test_failed_llm_calls_are_skipped_and_empty_result_is_not_cached(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "chunk_overlap_chars", 60)
    monkeypatch.setattr(settings, "cache_dir", str(tmp_path))
    monkeypatch.setattr(settings, "record_call_gap_seconds", 0)
    monkeypatch.setattr(rx, "get_chunks_for_paper", lambda paper_id: _chunk(PAPER_TEXT))

    async def always_fails(prompt):
        raise LlmError("rate limited")

    monkeypatch.setattr(rx, "generate_json", always_fails)
    record = await rx.extract_paper_record("arxiv_2", "t")
    assert record == PaperRecord()
    assert not (tmp_path / "records" / "arxiv_2.json").exists()  # will be retried next time


@pytest.mark.asyncio
async def test_no_chunks_returns_empty_record(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "cache_dir", str(tmp_path))
    monkeypatch.setattr(rx, "get_chunks_for_paper", lambda paper_id: [])
    assert await rx.extract_paper_record("arxiv_3", "t") == PaperRecord()


@pytest.mark.asyncio
async def test_extract_and_index_passes_record_to_graph(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "chunk_overlap_chars", 60)
    monkeypatch.setattr(settings, "cache_dir", str(tmp_path))
    monkeypatch.setattr(settings, "record_call_gap_seconds", 0)
    monkeypatch.setattr(rx, "get_chunks_for_paper", lambda paper_id: _chunk(PAPER_TEXT))
    monkeypatch.setattr(rx, "generate_json", _fake_llm_factory([]))
    seen = {}

    async def fake_index(paper_id, paper, record, user_id):
        seen.update(paper_id=paper_id, record=record, user_id=user_id)
        return {"methods": len(record.methods)}

    monkeypatch.setattr(rx, "index_record_in_graph", fake_index)

    class P:
        title = "ECG-GAT"

    out = await rx.extract_and_index_record("arxiv_4", P(), "user_1")
    assert out == {"methods": 1}
    assert seen["user_id"] == "user_1" and seen["record"].datasets == ["MIT-BIH", "PTB-XL"]


def test_numbered_headings_outside_the_fixed_vocabulary_are_understood():
    text = (
        "Title\nAbstract\nWe study X.\n"
        "1 Introduction\n" + "intro text. " * 50 + "\n"
        "2 Problem Setup\n" + "setup text. " * 50 + "\n"
        "3 Our Proposed Algorithm\n" + "algorithm text. " * 50 + "\n"
        "4 Numerical Experiments\n" + "experiment text. " * 50 + "\n"
        "5 Conclusions and Outlook\n" + "conclusion text. " * 50 + "\n"
        "References\n[1] cited.\n"
    )
    s = rx.split_sections(text)
    assert "experiment text" in s["experiments"]
    assert "algorithm text" in s["method"] and "setup text" in s["method"]
    assert "conclusion text" in s["conclusion"]
    assert "cited" not in "".join(s.values())


def test_pick_by_cues_finds_result_heavy_windows():
    plain = "We describe the idea in plain words. " * 20
    rich = "We evaluate on the benchmark dataset; accuracy and F1 beat the baseline. " * 20
    text = plain + "\n" + rich + "\n" + plain
    picked = rx.pick_by_cues(text, 800, 1)
    assert len(picked) == 1 and "benchmark" in picked[0]
