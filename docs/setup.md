# Setup Guide — Phase 0 & Phase 1

Everything you need to go from "unzipped folder" to "search working end to
end in the browser." Windows steps are primary; macOS/Linux notes are
included where they differ.

---

## 0. Prerequisites

- **Python 3.11+** — check with `python --version`
- **Node.js 20+** and npm — check with `node --version`
- **VSCode** (recommended) with the Python and ESLint extensions
- **Git**

---

## 1. Unzip and open in VSCode

1. Unzip `research_mate.zip` somewhere permanent (not Downloads) — e.g. `C:\Projects\research_mate`
2. Open VSCode → File → Open Folder → select `research_mate`

You should see two top-level app folders: `backend/` and `frontend/`.

---

## 2. Backend setup (FastAPI)

Open a terminal in VSCode (`` Ctrl+` ``) and run:

```bash
cd backend
python -m venv venv
```

**Activate the virtual environment:**

- Windows (PowerShell): `venv\Scripts\Activate.ps1`
- Windows (cmd): `venv\Scripts\activate.bat`
- macOS / Linux: `source venv/bin/activate`

You should see `(venv)` appear at the start of your terminal prompt.

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Set up environment variables:**

The repo ships with a working `.env` already (copied from `.env.example`) so
the app runs out of the box. Open `backend/.env` and fill in:

- `PUBMED_EMAIL` — NCBI requires a real email for E-utilities requests
- `SEMANTIC_SCHOLAR_API_KEY` — optional, but recommended once you're testing
  a lot (free key at https://www.semanticscholar.org/product/api)

**In VSCode:** select the venv's Python interpreter — `Ctrl+Shift+P` →
"Python: Select Interpreter" → choose the one inside `backend/venv`.

**Run the backend:**

```bash
uvicorn app.main:app --reload
```

Visit http://localhost:8000/health — you should see `{"status": "ok", ...}`.
Interactive API docs are at http://localhost:8000/docs — try `/api/search`
there directly before wiring up the frontend.

**Run the tests:**

```bash
pytest -q
```

---

## 3. Frontend setup (React)

Open a **second terminal** (keep the backend running in the first):

```bash
cd frontend
npm install
```

The repo ships with a working `frontend/.env` pointing at
`http://localhost:8000`. Adjust `VITE_API_BASE_URL` there if your backend
runs elsewhere.

**Run the frontend:**

```bash
npm run dev
```

Visit http://localhost:5173 — you should see the Research Mate search page.
Try searching a topic (e.g. "transformer attention") — results should
appear pulled live from ArXiv, Semantic Scholar, and PubMed.

---

## 4. Troubleshooting

- **CORS errors in the browser console** — check `CORS_ORIGINS` in
  `backend/.env` includes `http://localhost:5173`.
- **429 "rate limit exceeded"** — the search endpoint is capped
  (`RATE_LIMIT_SEARCH` in `backend/.env`, default `30/hour`) since this is
  built to eventually run as a public service. Raise it locally while
  developing if it gets in your way.
- **PubMed requests failing** — make sure `PUBMED_EMAIL` is set to a real
  email address; NCBI's usage policy requires it and may block anonymous
  requests.
- **Empty results for a niche topic** — normal; not every source indexes
  everything. Try a broader topic to confirm the pipeline itself works.

---

## 5. What's next

Phase 1 ends here — you have working multi-source search, backend and
frontend talking to each other, rate limiting in place, and CI running on
push. Phase 2 (document ingestion & full-text reading) is the next step —
see `Research_Mate_Project_Plan.md` for the full phase breakdown.
