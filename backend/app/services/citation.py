"""
Generates APA and BibTeX citations directly from stored paper metadata.
Deliberately no LLM involved here - citation formatting is a solved,
mechanical problem, and using the LLM for it would only introduce a
chance of hallucinated author names or years for zero benefit.
"""
import re

from app.schemas.paper import Paper


def _format_authors_apa(authors: list[str]) -> str:
    if not authors:
        return "Unknown Author"

    def to_last_first(name: str) -> str:
        parts = name.strip().split()
        if len(parts) < 2:
            return name
        last = parts[-1]
        initials = " ".join(f"{p[0]}." for p in parts[:-1] if p)
        return f"{last}, {initials}"

    formatted = [to_last_first(a) for a in authors]
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) <= 20:
        return ", ".join(formatted[:-1]) + ", & " + formatted[-1]
    return ", ".join(formatted[:19]) + ", ... " + formatted[-1]


def generate_apa_citation(paper: Paper) -> str:
    authors = _format_authors_apa(paper.authors)
    year = paper.published_date.year if paper.published_date else "n.d."
    title = paper.title.rstrip(".")

    citation = f"{authors} ({year}). {title}."
    if paper.doi:
        citation += f" https://doi.org/{paper.doi}"
    elif paper.url:
        citation += f" {paper.url}"
    return citation


def _bibtex_key(paper: Paper) -> str:
    first_author_last = "unknown"
    if paper.authors:
        parts = paper.authors[0].strip().split()
        if parts:
            first_author_last = re.sub(r"[^a-zA-Z]", "", parts[-1]).lower()

    year = paper.published_date.year if paper.published_date else "nd"
    first_title_word = re.sub(r"[^a-zA-Z]", "", paper.title.split()[0]).lower() if paper.title else "paper"
    return f"{first_author_last}{year}{first_title_word}"


def generate_bibtex_citation(paper: Paper) -> str:
    key = _bibtex_key(paper)
    year = paper.published_date.year if paper.published_date else "n.d."
    authors_bibtex = " and ".join(paper.authors) if paper.authors else "Unknown Author"

    lines = [
        f"@article{{{key},",
        f"  title = {{{paper.title}}},",
        f"  author = {{{authors_bibtex}}},",
        f"  year = {{{year}}},",
    ]
    if paper.doi:
        lines.append(f"  doi = {{{paper.doi}}},")
    if paper.url:
        lines.append(f"  url = {{{paper.url}}},")
    lines.append("}")
    return "\n".join(lines)