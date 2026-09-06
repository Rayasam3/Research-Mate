# Research Mate — Project Plan (Fresh Start)

**Type:** Individual project — Agentic AI Literature Analyst
**Core idea:** Give it a topic → it searches ArXiv/Semantic Scholar/PubMed → reads full papers → gives you a plain-English summary card per paper (TL;DR, problem, method explained simply, real results, limitations, ready-to-use citation) → a comparison table across papers → an "Explore Deeper" tab with a knowledge graph + auto-drafted gap analysis for advanced users.

**Stack:** FastAPI + LangGraph (agent orchestration) + Ollama (Llama 3.1 8B, sized for public/shared hosting — 70B stays a local-dev-only option) + LlamaIndex + PyMuPDF (PDF parsing) + ChromaDB (vector store) + Neo4j Community + Py2neo (knowledge graph) + Redis + Celery (async job queue, now load-bearing not optional) + **React (Vite + TypeScript) + Tailwind + a graph-viz lib (react-force-graph or similar)** for the frontend + python-docx + BibTeX export.

**Deployment target:** a public, multi-user live service — not a personal tool anymore. This changes a few defaults throughout the plan:
- **No Auth/RBAC phase by default**, but a *lightweight anonymous rate-limiting layer* (per-IP/session) is now mandatory, not optional — added in Phase 0 and enforced from Phase 1 onward. Full accounts stay optional (add as its own phase later only if you want saved history per user).
- **Job queue is real infrastructure**, not a nicety — Celery + Redis must handle concurrent multi-user agent runs (Phase 4).
- **Model choice is cost/latency-driven**, not just a dev/prod toggle — 8B local via Ollama on the host, or a hosted API model if self-hosting 8B can't handle real concurrent traffic (decision point flagged in Phase 0 and revisited in Phase 7).
- **Security hardening is a first-class checklist item** (Phase 7/8): CORS, input validation, SSRF-safe PDF fetching, upload/topic abuse limits.

---

## Project Status

- [ ] Phase 0 — Project & Environment Setup
- [ ] Phase 1 — Paper Search Layer
- [ ] Phase 2 — Document Ingestion & Full-Text Reading
- [ ] Phase 3 — Per-Paper Summary Cards (LLM)
- [ ] Phase 4 — LangGraph Agent Loop
- [ ] Phase 5 — Knowledge Graph & Comparison Layer
- [ ] Phase 6 — Gap Analysis & Draft Writing
- [ ] Phase 7 — Frontend + Deployment
- [ ] Phase 8 — MLOps Hygiene

---

## Phase 0 — Project & Environment Setup

**Goal:** A clean, version-controlled, fully reproducible scaffold — before any feature code is written.

1. Create the project folder and initialize git (`git init`), create the GitHub repo, and connect the remote.
2. Create the full folder structure up front, now as two apps (backend + React frontend) sharing one repo:
   ```
   research_mate/
   ├── backend/
   │   ├── app/               # FastAPI backend (api/, core/, schemas/, main.py)
   │   ├── agents/            # LangGraph nodes + graph definition
   │   ├── ingestion/         # PDF parsing, chunking, embedding
   │   ├── graph/             # Neo4j schema + queries
   │   ├── scripts/           # setup/model-pull utilities
   │   ├── data/papers/       # downloaded PDFs (gitignored)
   │   ├── data/cache/        # cached API responses (gitignored)
   │   └── tests/             # pytest suite
   ├── frontend/              # React (Vite + TS) app — src/components, src/pages, src/api
   ├── docs/                  # setup guide, architecture notes
   └── .github/workflows/     # CI (backend + frontend)
   ```
3. Set up the Python virtual environment (`python -m venv venv`) and activate it; separately, scaffold the React app (`npm create vite@latest frontend -- --template react-ts`).
4. Write a pinned `requirements.txt` (FastAPI, uvicorn, langgraph, langchain-ollama, llama-index, pymupdf, chromadb, py2neo, redis, celery, slowapi or similar for rate limiting, python-docx, pytest, python-dotenv) and `frontend/package.json` deps (React, Tailwind, axios/fetch wrapper, a graph-viz lib).
5. Create `.env.example` and `.env` for the backend (Ollama host/model, Neo4j creds, Redis URL, ChromaDB path, API keys for Semantic Scholar/PubMed, rate-limit thresholds) and a separate `frontend/.env.example` (API base URL); `.gitignore` covering `venv/`, `.env`, `node_modules/`, `data/papers/`, `data/cache/`, `__pycache__/`.
6. Write `docker-compose.yml` for Neo4j, Redis, and Ollama containers.
7. Write `scripts/pull_models.sh` / `.ps1` to pull the Llama 3.1 8B model into Ollama.
8. Scaffold a minimal FastAPI app with a `/health` endpoint and CORS configured for the React dev origin; scaffold a minimal React app with one page hitting `/health` to confirm the connection end to end.
9. Add a per-IP/session rate-limiting middleware stub in FastAPI now (even a basic in-memory or Redis-backed limiter) — since this is a public service, gate it from day one rather than bolting it on later.
10. Add a `tests/test_health.py` smoke test and a basic GitHub Actions CI workflow (backend lint + smoke test, frontend build + lint).
11. Write `README.md` with the project status checklist, prerequisites, quick-start commands (backend + frontend), and folder structure.
12. **Git push:** `"Phase 0: project scaffold, React frontend init, Docker services, rate-limit stub, CI skeleton"`.

---

## Phase 1 — Paper Search Layer

**Goal:** Given a topic, return a clean, deduplicated list of candidate papers from multiple sources.

1. Define the shared `Paper` Pydantic schema (title, authors, abstract, source, pdf_url, published_date, external_id).
2. Implement an ArXiv client (via `arxiv` package or REST API) that returns normalized `Paper` objects.
3. Implement a Semantic Scholar client (REST API) similarly normalized.
4. Implement a PubMed client (Entrez/E-utilities) similarly normalized.
5. Build a unified `search_service` that fans out to all three sources concurrently and merges results.
6. Add deduplication logic (by DOI/title similarity) across sources.
7. Add basic ranking (relevance score, recency) and a result-count cap per source.
8. Expose a `POST /search` FastAPI endpoint accepting a topic + filters (year range, source).
9. Build a simple React search page (input box + results list showing title/authors/abstract) wired to the endpoint via a small typed API client (`src/api/`).
10. Write unit tests for each client (mocked responses) and the merge/dedupe logic.
11. **Git push:** `"Phase 1: multi-source paper search layer"`.

---

## Phase 2 — Document Ingestion & Full-Text Reading

**Goal:** Turn a search result into fully parsed, chunked, embedded text ready for the LLM to reason over.

1. Build a PDF downloader with retry/backoff, saving into `data/papers/` keyed by paper ID.
2. Integrate PyMuPDF (or LlamaIndex's PDF reader) to extract full text, preserving section structure where possible.
3. Handle edge cases: paywalled/no-PDF papers (fall back to abstract-only mode), scanned/OCR-needed PDFs (flag and skip or OCR).
4. Build a chunking strategy (section-aware or sliding-window) sized for the embedding model's context.
5. Set up ChromaDB and an embedding pipeline (local embedding model via Ollama or sentence-transformers).
6. Store chunks + metadata (paper ID, section, page) in ChromaDB.
7. Add a caching layer in `data/cache/` so re-processing the same paper is skipped.
8. Expose an `POST /ingest` endpoint that takes a paper ID (or list) and runs download → parse → chunk → embed.
9. Add logging around ingestion failures (bad PDF, network timeout, OCR needed) so failures are visible, not silent.
10. Write tests using a couple of sample PDFs (one clean, one edge-case).
11. **Git push:** `"Phase 2: document ingestion and full-text embedding pipeline"`.

---

## Phase 3 — Per-Paper Summary Cards (LLM)

**Goal:** Turn ingested full text into the primary user-facing output — a plain-English summary card.

1. Define the `PaperSummaryCard` schema (tldr, problem, method_explained, key_results, limitations, citation_apa, citation_bibtex).
2. Set up the Ollama client wrapper (model name/quantization read from `.env`, so 70B-dev vs 8B-prod is explicit, not silent).
3. Design the summarization prompt: retrieve relevant chunks for a paper, ask the LLM to produce each field in plain English with real numbers pulled from the text (not invented).
4. Add a numeric/results extraction pass — verify key metrics quoted in the summary actually appear in the source text (basic grounding check) to reduce hallucination.
5. Build the APA and BibTeX citation generator from paper metadata.
6. Expose a `POST /summarize/{paper_id}` endpoint returning the full `PaperSummaryCard`.
7. Cache generated cards (so re-viewing a paper doesn't re-call the LLM).
8. Build the `SummaryCard` React component (title, TL;DR banner, expandable sections for method/results/limitations, copy-citation buttons) as a reusable component you'll reuse in Phase 5's comparison view.
9. Write tests with a known sample paper, checking the card's fields are all populated and citations are correctly formatted.
10. **Git push:** `"Phase 3: LLM-generated per-paper summary cards"`.

---

## Phase 4 — LangGraph Agent Loop

**Goal:** Wire search → ingest → summarize into one autonomous agent that runs unattended given just a topic.

1. Design the LangGraph state object (topic, candidate papers, ingested papers, generated cards, errors).
2. Build the `search` node (calls Phase 1 service).
3. Build the `ingest` node (calls Phase 2 service, per paper).
4. Build the `summarize` node (calls Phase 3 service, per paper).
5. Add a `filter/select` node so the agent doesn't process every result — e.g., top-N by relevance, or a relevance-check LLM call.
6. Add per-node retry logic and graceful error handling (a failed paper shouldn't crash the whole run).
7. Wire the agent run through **Celery + Redis as a real background job queue** — this is now load-bearing infrastructure, since multiple public users may kick off runs concurrently and none of them should block the API or each other.
8. Add a run-tracking mechanism (job ID, status: queued/running/done/partial-failure, position-in-queue) so the frontend can poll progress meaningfully under load.
9. Expose a `POST /agent/run` endpoint (rate-limited per session/IP) that enqueues the job and returns a job ID.
10. Add a `GET /agent/status/{job_id}` endpoint for polling, plus a sensible cap on concurrent jobs per visitor.
11. Build the React "job progress" UI (poll status, show a queue position/progress bar, render cards as they complete).
12. Write an integration test running the full graph on a narrow topic with a small paper cap, plus a basic load test (a handful of concurrent jobs) to confirm the queue doesn't deadlock.
13. **Git push:** `"Phase 4: LangGraph agent on a Celery/Redis job queue for concurrent public use"`.

---

## Phase 5 — Knowledge Graph & Comparison Layer

**Goal:** Let users compare papers side by side and see relationships between them.

1. Design the Neo4j schema: nodes for Paper, Author, Method, Dataset; relationships (AUTHORED_BY, USES_METHOD, EVALUATED_ON, CITES).
2. Set up Py2neo connection and schema constraints/indexes.
3. Extract structured entities (methods, datasets used) from each paper's summary/full text via a targeted LLM extraction prompt.
4. Write the ingestion logic that populates Neo4j nodes/relationships as papers are summarized.
5. Build a comparison-table service that pulls, for a set of papers, aligned columns (method, dataset, key metric, year).
6. Expose a `GET /compare?paper_ids=...` endpoint returning the comparison table data.
7. Build the `ComparisonTable` React component, sitting alongside the summary cards in the results view.
8. Add basic graph query endpoints (e.g., "papers using the same dataset as X").
9. Write tests for the entity extraction and the comparison table assembly.
10. **Git push:** `"Phase 5: Neo4j knowledge graph and cross-paper comparison table"`.

---

## Phase 6 — Gap Analysis & Draft Writing

**Goal:** Advanced-user feature — surface under-explored connections and draft a Related Work section.

1. Design graph analytics queries to find sparse/under-connected areas (e.g., method-dataset combinations rarely tested together).
2. Turn analytics results into candidate "gap statements" via an LLM prompt grounded in the actual graph data.
3. Build a "Related Work" paragraph generator that synthesizes the summarized papers into an academic-style draft with inline citations.
4. Add BibTeX export for the full reference list used in the draft.
5. Expose `GET /gaps` and `POST /draft-related-work` endpoints.
6. Build the "Explore Deeper" React tab: interactive graph view (react-force-graph or similar) + gap statements list + draft download.
7. Write tests validating gap statements reference real graph nodes (not hallucinated entities).
8. **Git push:** `"Phase 6: gap analysis and automated related-work drafting"`.

---

## Phase 7 — React Frontend Polish + Public Deployment

**Goal:** A polished, responsive React app deployed as a real public service, hardened enough for strangers to use unsupervised.

1. Finalize the React information architecture as real routes (React Router): `/` (search) → `/results/:jobId` (summary cards, primary view) → comparison table section → "Explore Deeper" tab.
2. Polish the job-progress UI (queue position, live status, cards streaming in as they complete) and responsive/mobile layout with Tailwind.
3. Add export options: download all cards as a report (docx), download BibTeX for selected papers — triggered from the React UI, generated by the backend.
4. Add thorough error/empty states (no results, ingestion failure, LLM timeout, rate-limit-exceeded message with a clear "try again in X" cue).
5. Add a visible model/status indicator in the UI (which model is answering, approximate queue load) so public users understand why a run might be slow.
6. **Enforce public-service guardrails end to end:**
   - Per-IP/session rate limiting on `/search` and `/agent/run` (finalize the Phase 0 stub into real limits, e.g. N runs/hour).
   - Cap on papers-per-run and PDF size to bound cost and abuse.
   - CORS locked to your real frontend domain (not `*`).
   - SSRF-safe PDF downloading (validate URLs, restrict to known academic domains/redirect limits).
   - Basic bot/abuse mitigation (e.g., a lightweight captcha or honeypot on the search form if abuse becomes a problem).
7. Containerize the full stack (FastAPI backend, React build served via Nginx or a static host, Celery worker, and reference the existing docker-compose services for Redis/Neo4j/Ollama).
8. Choose and set up real hosting: e.g., React static build on Vercel/Netlify/Cloudflare Pages, FastAPI + Celery worker + Ollama(8B) on a VM or container host (Render/Railway/Fly.io/a small cloud VM) sized for expected concurrent public traffic — confirm the 8B model's latency/throughput is actually viable at that host tier before committing.
9. Set up a real domain + HTTPS (Let's Encrypt or host-managed certs).
10. Smoke-test the deployed public URL end-to-end with a real topic, and do a small concurrent-user test (a few simultaneous searches) to confirm rate limiting and the job queue behave correctly under real conditions.
11. **Git push:** `"Phase 7: React frontend, public deployment, rate limiting and abuse hardening"`.

---

## Phase 8 — MLOps Hygiene & Public-Service Reliability

**Goal:** Make the live service defensible, maintainable, and resilient to real-world public traffic — not just "working in a demo."

1. Add structured logging across search calls, ingestion failures, agent node decisions, LLM call latency/cost, and rate-limit rejections.
2. Add model/version tracking — log which Ollama model + quantization produced each summary/run.
3. Wire Redis caching for repeated topic searches and already-processed papers so popular topics don't repeatedly hit the LLM (this now also directly controls your hosting bill).
4. Add monitoring/metrics and uptime alerting (request counts, failure rates, average LLM latency, queue depth, error-rate spikes) — a `/metrics` endpoint plus a simple external uptime check (e.g., UptimeRobot) is enough at this scale.
5. Add a basic incident-response note to docs: what to do if the LLM host goes down, queue backs up, or abuse spikes (e.g., temporarily lower per-IP limits).
6. Write the final `README.md`: architecture diagram (including the public deployment topology), full local setup steps, phase-by-phase changelog, the model-sizing rationale for public hosting, and a note on current scaling limits (so it's honest about what "everyone can use it" currently means in practice).
7. Do a final pass on `.env.example`, `requirements.txt`/`package.json` pinning, `.gitignore` completeness, and a lightweight `TERMS.md`/usage note if you want to set expectations for public users (no guarantees of uptime, data retention policy for uploaded/searched content, etc.).
8. **Git push:** `"Phase 8: final polish, monitoring, incident notes, and public-service documentation"`.

---

## Suggested Order of Attack

Phases 0 → 1 → 2 → 3 already get you a usable single-paper-at-a-time tool (backend + a bare React UI). Phase 4 is what makes it "agentic" (autonomous, multi-paper, and now genuinely concurrent-safe via Celery/Redis). Phases 5–6 are the differentiators for a research/academic review. Phase 7 is where it becomes a real public product — React polish, hosting, and the rate-limiting/abuse guardrails a live service actually needs. Phase 8 makes it defensible and keeps it standing once real strangers start using it.

One thing worth deciding early rather than late: since this will be public, do you want it fully anonymous (no login, just rate-limited), or lightweight auth (e.g., magic-link email) so people can revisit their past searches? That decision affects Phase 0's scaffold slightly and is easiest to bake in now rather than retrofit after Phase 4.

Ready to start Phase 0 whenever you are — just say so and we'll go step by step exactly like we did for ProcureBot.
