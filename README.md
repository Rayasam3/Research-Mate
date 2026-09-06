# Research Mate

An agentic AI literature analyst: give it a topic, it searches ArXiv,
Semantic Scholar, and PubMed, and (in later phases) reads full papers to
produce plain-English summary cards, a cross-paper comparison table, and a
knowledge-graph-backed gap analysis. Built to eventually run as a public,
multi-user live service.

## Project Status

- [x] Phase 0 — Project & Environment Setup
- [x] Phase 1 — Paper Search Layer (ArXiv / Semantic Scholar / PubMed)
- [ ] Phase 2 — Document Ingestion & Full-Text Reading
- [ ] Phase 3 — Per-Paper Summary Cards (LLM)
- [ ] Phase 4 — LangGraph Agent Loop
- [ ] Phase 5 — Knowledge Graph & Comparison Layer
- [ ] Phase 6 — Gap Analysis & Draft Writing
- [ ] Phase 7 — React Frontend Polish + Public Deployment
- [ ] Phase 8 — MLOps Hygiene & Public-Service Reliability

See `Research_Mate_Project_Plan.md` for the full phase-by-phase breakdown.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Git
- (Later phases) Docker Desktop — for Neo4j, Redis, Ollama

## Quick Start

Full walkthrough in [`docs/setup.md`](docs/setup.md). Short version:

**Backend:**
```bash
cd backend
python -m venv venv
# activate venv — see docs/setup.md for your OS
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

```
research_mate/
├── backend/
│   ├── app/
│   │   ├── api/            # route definitions (search.py — Phase 1)
│   │   ├── core/           # config, CORS, rate limiter
│   │   ├── schemas/        # Pydantic models (Paper, SearchRequest/Response)
│   │   ├── services/       # ArXiv / Semantic Scholar / PubMed clients + merge logic
│   │   └── main.py         # FastAPI entrypoint
│   ├── agents/              # LangGraph nodes (Phase 4)
│   ├── ingestion/           # PDF parsing, chunking, embedding (Phase 2)
│   ├── graph/                # Neo4j schema + queries (Phase 5-6)
│   ├── scripts/              # setup/utility scripts
│   ├── data/papers/          # downloaded PDFs (gitignored)
│   ├── data/cache/           # cached API responses (gitignored)
│   ├── tests/                 # pytest suite
│   ├── requirements.txt
│   ├── .env.example
│   └── pytest.ini
├── frontend/                  # React (Vite + TS) app
│   ├── src/
│   │   ├── api/                # typed API client
│   │   ├── components/          # PaperResultCard, etc.
│   │   ├── pages/                # SearchPage, etc.
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── .env.example
├── docs/
│   └── setup.md               # detailed venv/npm/VSCode walkthrough
├── .github/workflows/          # CI (backend pytest, frontend build+lint)
├── docker-compose.yml           # future services (Redis, Neo4j, Ollama) — not needed until Phase 2+
└── README.md
```

## Changelog

- **Phase 0** — Project scaffold (backend + React frontend), pinned
  dependencies, `.env` files, Docker Compose placeholder for future
  services, CI skeleton, per-IP rate-limiting stub.
- **Phase 1** — ArXiv / Semantic Scholar / PubMed search clients, unified
  fan-out + dedupe service, `POST /api/search` (rate-limited), React search
  page wired end to end, unit tests for dedupe/merge logic.
