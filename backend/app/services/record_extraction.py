"""
Phase 2: structured, section-aware extraction of a PaperRecord from a
paper's full text.

Instead of showing the LLM one chunk (the abstract), this rebuilds the
paper text, splits it into sections (intro / method / experiments /
conclusion), skips related work, appendices and references, and runs
three focused passes:

  1. methods pass     -> domain, task, methods (role + novelty)
  2. experiments pass -> datasets, results (method x dataset x metric)
  3. conclusion pass  -> stated limitations and future work

Results from every window are merged and cached on disk, so re-indexing a
paper never repeats the LLM calls.
"""
import asyncio
import json
import logging
import re
from pathlib import Path

from app.core.config import settings
from app.schemas.paper_record import MethodMention, PaperRecord, ResultItem
from app.services.graph_ingestion import index_record_in_graph
from app.services.graph_schema import normalize_key
from app.services.llm_client import LlmError, generate_json
from ingestion.vector_store import get_chunks_for_paper

logger = logging.getLogger(__name__)

_CACHE_VERSION = 1
_ROLE_PRIORITY = {"proposed": 0, "baseline": 1, "used": 2}
_MAX_STATEMENTS = 8

# --------------------------------------------------------------------------
# Section splitting
# --------------------------------------------------------------------------

_NUM = r"(?:(?:\d+|[IVXivx]+|[A-Z])(?:\.\d+)*\.?\s+)?"
_HEADING_RE = re.compile(
    r"^\s*" + _NUM + r"(?P<title>"
    r"abstract|introduction|related\s+works?|background|preliminaries|literature\s+review|"
    r"(?:proposed\s+)?(?:methods?|methodology|approach|model|framework)|"
    r"experiments?(?:al)?(?:\s+(?:setup|settings?|results|evaluation))?|"
    r"evaluation|results(?:\s+and\s+discussion)?|discussion|limitations?|"
    r"conclusions?(?:\s+and\s+future\s+work)?|future\s+work|"
    r"references|bibliography|appendix(?:\s+[A-Z])?|acknowledge?ments?"
    r")\s*:?\s*$",
    re.IGNORECASE,
)


def _category(title: str) -> str:
    t = title.lower().strip()
    if t.startswith(("reference", "bibliograph")):
        return "stop"
    if t.startswith(("appendix", "acknowledg")):
        return "skip"
    if t.startswith(("related", "background", "preliminar", "literature")):
        return "skip"
    if t in ("abstract", "introduction"):
        return "intro"
    if t.startswith(("experiment", "evaluation", "result")):
        return "experiments"
    if t.startswith(("discussion", "limitation", "conclusion", "future")):
        return "conclusion"
    return "method"


_NUMBERED_RE = re.compile(r"^\s*(\d{1,2})\.?\s+([A-Z][^\n]{2,70}?)\s*$")
_EXPERIMENT_WORDS = ("experiment", "evaluation", "result", "benchmark", "empirical", "case study", "simulation")
_CONCLUSION_WORDS = ("conclusion", "discussion", "limitation", "future work", "concluding")


def _numbered_category(num: int, title: str, current: str) -> str:
    """Classify a numbered top-level heading outside the fixed vocabulary."""
    t = title.lower()
    if t.startswith(("reference", "bibliograph")):
        return "stop"
    if t.startswith(("related", "background", "preliminar", "literature", "appendix", "acknowledg")):
        return "skip"
    if any(w in t for w in _CONCLUSION_WORDS):
        return "conclusion"
    if any(w in t for w in _EXPERIMENT_WORDS):
        return "experiments"
    if "introduction" in t or t.startswith("abstract"):
        return "intro"
    if num == 1 and current == "intro":
        return "intro"
    # any other top-level section: method, unless we are already past the experiments
    return current if current in ("experiments", "conclusion") else "method"


def reassemble(chunks: list[str]) -> str:
    """Rebuild the paper text from overlapping chunks (drops the overlap)."""
    if not chunks:
        return ""
    overlap = settings.chunk_overlap_chars
    parts = [chunks[0]]
    for chunk in chunks[1:]:
        parts.append(chunk[overlap:] if len(chunk) > overlap else chunk)
    return "".join(parts)


def _positional_sections(text: str) -> dict[str, str]:
    """Fallback when no headings are found: split by position in the paper."""
    cut = None
    for m in re.finditer(r"^\s*(?:\d+\.?\s+)?references\s*$", text, re.IGNORECASE | re.MULTILINE):
        cut = m.start()
    body = text[:cut] if cut else text
    n = len(body)
    a, b, c = int(n * 0.15), int(n * 0.50), int(n * 0.85)
    return {
        "intro": body[:a],
        "method": body[a:b],
        "experiments": body[b:c],
        "conclusion": body[c:],
    }


def split_sections(text: str) -> dict[str, str]:
    """
    Split paper text into intro / method / experiments / conclusion.
    Related work, background, appendices and everything after References
    are dropped. Falls back to a positional split if headings are not
    detected (e.g. unusual PDF layouts).
    """
    buckets: dict[str, list[str]] = {"intro": [], "method": [], "experiments": [], "conclusion": []}
    current = "intro"  # title/abstract block before the first heading
    buffer: list[str] = []
    detected = 0
    stopped = False
    last_num = 0

    for line in text.splitlines():
        match = _HEADING_RE.match(line) if len(line) <= 80 else None
        numbered = None if match or len(line) > 80 else _NUMBERED_RE.match(line)
        if numbered and int(numbered.group(1)) <= last_num:
            numbered = None  # numbers must keep increasing, else it is not a heading
        if numbered:
            num, title = int(numbered.group(1)), numbered.group(2)
            category = _numbered_category(num, title, current)
            if current in buckets and buffer:
                buckets[current].append("\n".join(buffer))
            buffer = []
            detected += 1
            last_num = num
            if category == "stop":
                stopped = True
                break
            current = category
            continue
        if match:
            if current in buckets and buffer:
                buckets[current].append("\n".join(buffer))
            buffer = []
            detected += 1
            category = _category(match.group("title"))
            if category == "stop":
                stopped = True
                break
            current = category
            continue
        buffer.append(line)

    if not stopped and current in buckets and buffer:
        buckets[current].append("\n".join(buffer))

    sections = {name: "\n".join(parts).strip() for name, parts in buckets.items()}
    if detected < 2 or (not sections["method"] and not sections["experiments"]):
        return _positional_sections(text)
    return sections


def _all_windows(text: str, size: int) -> list[str]:
    text = text.strip()
    windows: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            floor = start + int(size * 0.8)
            cut = text.rfind("\n", floor, end)
            if cut == -1:
                cut = text.rfind(". ", floor, end)
            if cut != -1:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            windows.append(piece)
        start = end
    return windows


def select_windows(text: str, size: int, max_windows: int) -> list[str]:
    """Split text into windows and pick at most max_windows, spread evenly."""
    windows = _all_windows(text, size)
    if len(windows) <= max_windows:
        return windows
    if max_windows <= 1:
        return windows[:1]
    last = len(windows) - 1
    indices = sorted({round(i * last / (max_windows - 1)) for i in range(max_windows)})
    return [windows[i] for i in indices]


_EXPERIMENT_CUES = re.compile(
    r"dataset|benchmark|baseline|accuracy|f1|precision|recall|rmse|mse|auc|bleu|"
    r"outperform|table\s+\d|we\s+evaluate|experiment|test\s+set|training\s+set|results?",
    re.IGNORECASE,
)


def pick_by_cues(text: str, size: int, max_windows: int) -> list[str]:
    """When no experiments section is found, pick the windows richest in dataset/result words."""
    windows = _all_windows(text, size)
    if len(windows) <= max_windows:
        return windows
    scored = sorted(range(len(windows)), key=lambda i: -len(_EXPERIMENT_CUES.findall(windows[i])))
    keep = sorted(scored[:max_windows])
    return [windows[i] for i in keep]


# --------------------------------------------------------------------------
# Prompts (placeholders are replaced, not str.format, because of JSON braces)
# --------------------------------------------------------------------------

_METHOD_PROMPT = """You are extracting structured facts from one part of a research paper.
Paper title: {title}

Return ONLY a JSON object with exactly these keys:
{"domain": string or null, "task": string or null, "methods": [{"name": string, "role": "proposed" or "baseline" or "used", "novelty": string or null}]}

Rules:
- domain: the broad research field, e.g. "Computer Vision" or "Cardiology". task: the specific problem, e.g. "ECG classification".
- methods: models, algorithms or techniques named in the text. role is "proposed" if this paper introduces it, "baseline" if it is only compared against, otherwise "used".
- novelty: one short sentence on what is new about a proposed method, otherwise null.
- Use only names that appear in the text. Never invent. At most 10 methods. Use null or [] when unknown.

TEXT:
{text}"""

_EXPERIMENT_PROMPT = """You are extracting structured facts from the experiments part of a research paper.
Paper title: {title}

Return ONLY a JSON object with exactly these keys:
{"datasets": [string], "results": [{"method": string, "dataset": string, "metric": string or null, "value": string or null}]}

Rules:
- datasets: named datasets or benchmarks the paper evaluates on.
- results: only numbers stated in the text, one item per method, dataset and metric.
- Use only names that appear in the text. Never invent. At most 8 datasets and 12 results. Use [] when unknown.

TEXT:
{text}"""

_CONCLUSION_PROMPT = """You are extracting what the authors say about their own work, from the discussion or conclusion of a research paper.
Paper title: {title}

Return ONLY a JSON object with exactly these keys:
{"limitations": [string], "future_work": [string]}

Rules:
- limitations: weaknesses or restrictions the authors explicitly state. future_work: directions the authors explicitly propose.
- Each item is one short sentence (under 25 words) in your own words.
- Only include what the authors actually state. Never invent. At most 5 of each. Use [] when none.

TEXT:
{text}"""


# --------------------------------------------------------------------------
# Parsing (defensive: LLM output is never trusted to be well-formed)
# --------------------------------------------------------------------------


def _clean(value, limit: int = 200) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    text = str(value).strip()
    return text[:limit] if text else None


def _items(value) -> list:
    return value if isinstance(value, list) else []


def _parse_method_pass(data) -> PaperRecord:
    if not isinstance(data, dict):
        return PaperRecord()
    methods: list[MethodMention] = []
    for item in _items(data.get("methods"))[:10]:
        if isinstance(item, str):
            item = {"name": item}
        if not isinstance(item, dict):
            continue
        name = _clean(item.get("name"))
        if not name:
            continue
        role = (_clean(item.get("role")) or "used").lower()
        if role not in _ROLE_PRIORITY:
            role = "used"
        methods.append(MethodMention(name=name, role=role, novelty=_clean(item.get("novelty"), 300)))
    return PaperRecord(
        domain=_clean(data.get("domain"), 100),
        task=_clean(data.get("task"), 150),
        methods=methods,
    )


def _parse_experiment_pass(data) -> PaperRecord:
    if not isinstance(data, dict):
        return PaperRecord()
    datasets: list[str] = []
    for item in _items(data.get("datasets"))[:8]:
        name = _clean(item.get("name") if isinstance(item, dict) else item)
        if name:
            datasets.append(name)
    results: list[ResultItem] = []
    for item in _items(data.get("results"))[:12]:
        if not isinstance(item, dict):
            continue
        method, dataset = _clean(item.get("method")), _clean(item.get("dataset"))
        if method and dataset:
            results.append(
                ResultItem(
                    method=method,
                    dataset=dataset,
                    metric=_clean(item.get("metric"), 60),
                    value=_clean(item.get("value"), 60),
                )
            )
    return PaperRecord(datasets=datasets, results=results)


def _parse_conclusion_pass(data) -> PaperRecord:
    if not isinstance(data, dict):
        return PaperRecord()

    def statements(key: str) -> list[str]:
        out = []
        for item in _items(data.get(key))[:5]:
            text = _clean(item, 300)
            if text:
                out.append(text)
        return out

    return PaperRecord(limitations=statements("limitations"), future_work=statements("future_work"))


# --------------------------------------------------------------------------
# Merging and caching
# --------------------------------------------------------------------------


def merge_records(parts: list[PaperRecord]) -> PaperRecord:
    """Combine records from several windows/passes into one, de-duplicated."""
    domain = next((p.domain for p in parts if p.domain), None)
    task = next((p.task for p in parts if p.task), None)

    methods: dict[str, MethodMention] = {}
    for part in parts:
        for m in part.methods:
            key = normalize_key(m.name)
            if not key:
                continue
            current = methods.get(key)
            if current is None:
                methods[key] = m
            elif _ROLE_PRIORITY[m.role] < _ROLE_PRIORITY[current.role]:
                methods[key] = MethodMention(name=m.name, role=m.role, novelty=m.novelty or current.novelty)
            elif not current.novelty and m.novelty:
                methods[key] = MethodMention(name=current.name, role=current.role, novelty=m.novelty)

    datasets: dict[str, str] = {}
    results: dict[tuple, ResultItem] = {}
    for part in parts:
        for name in part.datasets:
            key = normalize_key(name)
            if key:
                datasets.setdefault(key, name)
        for r in part.results:
            rk = (normalize_key(r.method), normalize_key(r.dataset), (r.metric or "").lower())
            if rk[0] and rk[1]:
                results.setdefault(rk, r)

    def unique(texts: list[str]) -> list[str]:
        seen: dict[str, str] = {}
        for text in texts:
            seen.setdefault(" ".join(text.lower().split()), text)
        return list(seen.values())[:_MAX_STATEMENTS]

    return PaperRecord(
        domain=domain,
        task=task,
        methods=list(methods.values()),
        datasets=list(datasets.values()),
        results=list(results.values()),
        limitations=unique([t for p in parts for t in p.limitations]),
        future_work=unique([t for p in parts for t in p.future_work]),
    )


def _has_content(record: PaperRecord) -> bool:
    return bool(
        record.methods or record.datasets or record.results or record.limitations or record.future_work
    )


def _cache_path(paper_id: str) -> Path:
    return Path(settings.cache_dir) / "records" / f"{paper_id}.json"


def _read_cache(paper_id: str) -> PaperRecord | None:
    path = _cache_path(paper_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != _CACHE_VERSION:
            return None
        return PaperRecord.model_validate(payload["record"])
    except Exception:
        logger.warning("Ignoring unreadable record cache for paper_id=%s", paper_id)
        return None


def _write_cache(paper_id: str, record: PaperRecord) -> None:
    path = _cache_path(paper_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": _CACHE_VERSION, "record": record.model_dump()}
    path.write_text(json.dumps(payload), encoding="utf-8")


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


async def _run_pass(template: str, title: str, windows: list[str], parser, state: dict) -> list[PaperRecord]:
    parts: list[PaperRecord] = []
    for window in windows:
        # Pace calls on Groq's free tier (8,000 tokens/minute) to avoid 429s.
        if state["calls"] and settings.llm_provider == "groq":
            await asyncio.sleep(settings.record_call_gap_seconds)
        state["calls"] += 1
        prompt = template.replace("{title}", title).replace("{text}", window)
        try:
            data = await generate_json(prompt)
        except LlmError as exc:
            logger.warning("Record extraction call failed, skipping this window: %s", exc)
            state["failed"] = state.get("failed", 0) + 1
            continue
        parts.append(parser(data))
    return parts


async def extract_paper_record(paper_id: str, title: str) -> PaperRecord:
    cached = _read_cache(paper_id)
    if cached is not None:
        logger.info("Using cached record for paper_id=%s", paper_id)
        return cached

    chunks = get_chunks_for_paper(paper_id)  # all chunks, in paper order
    if not chunks:
        logger.warning("No stored chunks for paper_id=%s; nothing to extract", paper_id)
        return PaperRecord()

    sections = split_sections(reassemble(chunks))
    size = settings.record_window_chars
    k = max(1, settings.record_max_calls_per_pass)

    # Abstract/intro head + method section as one text, so short papers need one call.
    method_text = sections["intro"][: size // 2] + "\n\n" + sections["method"]
    method_windows = select_windows(method_text, size, k)
    if sections["experiments"]:
        experiment_windows = select_windows(sections["experiments"], size, k)
    else:
        body = "\n\n".join([sections["intro"], sections["method"], sections["conclusion"]])
        experiment_windows = pick_by_cues(body, size, k)
    conclusion_windows = select_windows(sections["conclusion"], size, k)

    state = {"calls": 0}
    parts: list[PaperRecord] = []
    parts += await _run_pass(_METHOD_PROMPT, title, method_windows, _parse_method_pass, state)
    parts += await _run_pass(_EXPERIMENT_PROMPT, title, experiment_windows, _parse_experiment_pass, state)
    parts += await _run_pass(_CONCLUSION_PROMPT, title, conclusion_windows, _parse_conclusion_pass, state)

    record = merge_records(parts)
    logger.info(
        "Extracted record for paper_id=%s using %d LLM calls: %d methods, %d datasets, "
        "%d results, %d limitations, %d future-work",
        paper_id,
        state["calls"],
        len(record.methods),
        len(record.datasets),
        len(record.results),
        len(record.limitations),
        len(record.future_work),
    )
    # Only cache a complete record: if any window failed, the next run retries.
    if _has_content(record) and not state.get("failed"):
        _write_cache(paper_id, record)
    return record


async def extract_and_index_record(paper_id: str, paper, user_id: str | None) -> dict:
    """Extract the paper's structured record (cached) and write it to the graph."""
    record = await extract_paper_record(paper_id, paper.title)
    # The research field comes from the paper sources (consistent labels like
    # "Computer Science"), not from the LLM, which names fields inconsistently.
    if getattr(paper, "field", None):
        record = record.model_copy(update={"domain": paper.field})
    return await index_record_in_graph(paper_id, paper, record, user_id)
