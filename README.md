# Research Mate

An agentic AI literature analyst: give it a topic, it searches ArXiv,
Semantic Scholar, PubMed, and OpenAlex, downloads and reads the actual
papers, and produces plain-English summary cards, a cross-paper
comparison table, a knowledge-graph-backed gap analysis, and an
auto-drafted Related Work paragraph with citations - all unattended,
via a LangGraph agent.

## What it does

1. **Search** four sources (ArXiv, Semantic Scholar, PubMed, OpenAlex).
2. **Detect the field** of the topic (e.g. Computer Science vs Medicine) by voting on the sources' field labels, and **rank papers by relevance** (embedding similarity to the topic, the user's own field, citations, recency). Off-topic papers are dropped.
3. **Read the full paper**, section by section (introduction, method, experiments, conclusion), and extract methods, datasets, results, limitations and future work with an LLM.
4. **Build a knowledge graph** in Neo4j: `Paper`, `Method`, `Dataset`, `Domain`, `Task`, `Limitation`, `FutureWork`, `Author` and `Gap` nodes.
5. **Show research-gap candidates with evidence**: method x dataset pairs nobody has tried, plus the limitations and future work the authors wrote themselves. A rare method is never called a gap on its own.
6. Compare papers by what is *different* in each, draft a Related Work paragraph, and explore the same graph in the Neo4j console (`docs/neo4j_demo_queries.cypher`).

## Project Status

- [x] Search layer, ingestion, summary cards, LangGraph agent, Redis cache, auth (PostgreSQL + JWT)
- [x] Knowledge graph model (paper record schema, normalized keys, constraints)
- [x] Full-paper, section-aware extraction
- [x] Domain detection and relevance ranking
- [x] Evidence-based gap candidates
- [x] New frontend (progress steps, knowledge graph view, gaps with evidence)
- [ ] Public deployment

## Architecture

                +-------------+
                |   React     |
                |  Frontend   |
                +------+------+
                       | REST
                +------v------+
                |   FastAPI   |
                |   Backend   |
                +--+---+---+--+
       +-----------+   |   +-----------+
+------v-----+  +------v-----+  +------v-----+
|  ArXiv /   |  |  ChromaDB  |  |   Neo4j    |
|  Semantic  |  | (chunks +  |  | (knowledge |
|  Scholar / |  | embeddings)|  |   graph)   |
|  PubMed /  |  +------------+  +------------+
|  OpenAlex  |
+------------+         |
                +-------v------+    +----------+
                | Groq/Ollama  |    |  Redis   |
                |  (LLM calls) |    | (search  |
                +--------------+    |  cache)  |
                                    +----------+



The agent (LangGraph) orchestrates: **search -> domain -> filter -> ingest -> summarize**,
running each paper through the full pipeline unattended, in the background.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Git
- Docker Desktop (for Neo4j and Redis)
- A Groq API key (free, recommended) or Ollama installed locally
- ~500MB free disk space for the embedding model + caches

## Quick Start

Full walkthrough in [`docs/setup.md`](docs/setup.md). Short version:

**Start services:**
```bash
docker compose up -d neo4j redis
```

**Backend:**
```bash
cd backend
python -m venv venv
# activate venv - see docs/setup.md for your OS
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend** (separate terminal):
```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173.

## Project Structure

research_mate/
|-- backend/
| |-- app/
| | |-- api/ # route definitions
| | |-- core/ # config, CORS, rate limiter
| | |-- schemas/ # Pydantic models
| | |-- services/ # search, ingestion, LLM, graph, metrics
| | +-- main.py # FastAPI entrypoint
| |-- agents/ # LangGraph nodes + graph definition
| |-- ingestion/ # PDF parsing, chunking, embedding
| |-- data/papers/ # downloaded PDFs (gitignored)
| |-- data/cache/ # cached API responses (gitignored)
| |-- tests/ # pytest suite (86+ tests)
| |-- requirements.txt
| +-- .env.example
|-- frontend/ # React (Vite + JS) app
| |-- src/
| | |-- api/ # API client
| | |-- components/ # Header, SummaryCard, LoadingSpinner
| | |-- hooks/ # useAgentJob, useTheme
| | |-- pages/ # SearchPage, ResultsPage
| | +-- App.jsx
| +-- .env
|-- docs/
| |-- setup.md # detailed setup walkthrough
| +-- incident-response.md # troubleshooting known failure modes
|-- .github/workflows/ # CI (backend pytest, frontend build+lint)
|-- docker-compose.yml # Neo4j + Redis
+-- README.md



## Key Features

- **Multi-source search** across 4 academic databases, deduped and cached
- **Real PDF ingestion**: download, extract, chunk, embed - with graceful
  handling of missing PDFs, scanned documents, and corrupt files
- **LLM summary cards**: TL;DR, method, results, limitations, plus
  APA/BibTeX citations generated from real metadata (never hallucinated)
- **Dual LLM provider support**: Groq (fast, hosted) or Ollama (free,
  local) - switch with one `.env` line
- **Autonomous agent**: one API call runs the entire search-to-summary
  pipeline unattended, as a background job
- **Knowledge graph**: papers, authors, methods, and datasets as a real
  Neo4j graph, populated automatically during summarization
- **Gap analysis**: surfaces methods/datasets used in only one paper,
  grounded strictly in real graph data
- **Related Work drafting**: synthesizes multiple papers into one
  academic paragraph with real inline citations
- **Redis-backed caching** with graceful fallback if Redis is unavailable
- **Rate limiting** on every public endpoint from day one
- **Dark mode** with system-preference detection and persistence

## Known Limitations

- Single-instance job tracking (in-memory) - won't survive a server
  restart mid-job, and won't scale across multiple backend processes yet
- Groq's free tier caps at 8,000 tokens/minute - multi-paper agent runs
  can occasionally hit this (handled with one automatic retry)
- Entity extraction accuracy depends on how much text is fed to the LLM;
  currently limited to 1-3 chunks per paper to stay within free-tier
  token/rate limits
- No user accounts/auth yet - fully anonymous, rate-limited by IP
- Not yet deployed publicly (Phase 9, in progress)

## Documentation

- [`docs/setup.md`](docs/setup.md) - full local setup walkthrough
- [`docs/incident-response.md`](docs/incident-response.md) - known
  failure modes and fixes
- [`Research_Mate_Project_Plan.md`](Research_Mate_Project_Plan.md) - the
  original phase-by-phase project plan

## Changelog

- **Phase 0** - Project scaffold, pinned dependencies, CI skeleton
- **Phase 1** - ArXiv/Semantic Scholar/PubMed/OpenAlex search, dedupe,
  year filtering, file-based caching (later upgraded to Redis)
- **Phase 2** - PDF download, text extraction, chunking, ChromaDB
  embedding, per-paper caching
- **Phase 3** - LLM summary generation (Ollama/Groq), citation
  generation, `/api/summarize`
- **Phase 4** - LangGraph agent (search -> filter -> ingest ->
  summarize), background job runner
- **Phase 5** - Neo4j knowledge graph, entity extraction,
  `/api/compare`, `/api/graph/related`
- **Phase 6** - Gap analysis and automated Related Work drafting
- **Phase 7** - React frontend: search, job progress, summary cards,
  comparison table, explore deeper tab, dark mode
- **Phase 8** - Redis-backed caching, model/version tracking,
  `/api/metrics`, incident-response documentation