# Incident Response Notes

Practical fixes for failure modes we've actually hit while building and
running Research Mate. Check here first before deep debugging.

---

## Groq returns 429 (rate limit exceeded)

**Symptom:** `LlmError: Groq request failed (429): ...` in logs or API response.

**Cause:** Free tier caps at 8,000 tokens/minute. Multi-paper agent runs
can hit this when summarizing several papers back-to-back.

**Fix:**
- The LLM client already retries once automatically after a 12-second wait.
- If it still fails, wait ~60 seconds and retry the request manually.
- Long-term: switch `LLM_PROVIDER=ollama` in `.env` if this happens often
  during heavy testing, or request a paid Groq tier for production use.

---

## Groq returns 401 (invalid API key) or 404 (model not found)

**Symptom:** `Invalid API Key` or `The model ... does not exist`.

**Fix:**
- 401: check `GROQ_API_KEY` in `.env` has no extra spaces/quotes, and the
  server was restarted after editing `.env`.
- 404: the model name may have been deprecated or moved to a paid tier.
  Check current available models at https://console.groq.com/docs/models
  and update `GROQ_MODEL` in `.env` accordingly.

---

## Ollama: "Could not connect to Ollama"

**Symptom:** `LlmError: Could not connect to Ollama at http://localhost:11434`.

**Fix:**
- Confirm Ollama is running: `ollama serve` in a terminal (or check it's
  running as a background service on Windows).
- Confirm the model is pulled: `ollama list` should show the model set in
  `OLLAMA_MODEL`.
- Ollama on CPU-only machines is slow (minutes per call) - this is
  expected, not a bug. Consider `LLM_PROVIDER=groq` for faster dev work.

---

## Neo4j: "Unauthorized" / authentication failure

**Symptom:** `Neo.ClientError.Security.Unauthorized`.

**Cause:** The password in `docker-compose.yml`'s `NEO4J_AUTH` and
`backend/.env`'s `NEO4J_PASSWORD` don't match, or the password was
changed only in one place (e.g. manually in Neo4j Browser).

**Fix:**
- Make both values match exactly.
- If they still don't match after editing, the running container's data
  volume already has the old password baked in. Reset with:

docker compose down -v
docker compose up -d neo4j


  (This wipes graph data - acceptable in dev, not for a populated
  production instance.)

---

## Neo4j: page won't load at localhost:7474 / container won't start

**Symptom:** Blank page, or `docker ps -a` shows the container `Exited`.

**Fix:**
- Check logs: `docker compose logs neo4j`
- Common cause: password under 8 characters - Neo4j refuses to start.
  Fix the password in `docker-compose.yml` (8+ plain characters, no
  special symbols) and reset the volume as above.
- Check port 7474/7687 isn't already used by another project's container:
  `docker ps` to see what's running.

---

## Redis unreachable

**Symptom:** No crash (by design), but searches never show a
"Redis search cache hit" log line even on repeated identical searches.

**Fix:**
- Confirm the container is running: `docker ps` should show
  `research_mate-redis-1`.
- If stopped: `docker compose up -d redis`
- Confirm `REDIS_URL` in `.env` points to the right port (we use `6380`
  on the host to avoid colliding with other projects' Redis on `6379`).
- The app is designed to keep working without Redis (just slower, no
  caching) - this is not a critical failure, just degraded performance.

---

## ArXiv / Semantic Scholar / PubMed return 429 or 5xx

**Symptom:** One source's log shows a failed request; other sources
still return results.

**Cause:** External rate limits, usually from rapid repeated testing.

**Fix:**
- No action needed for a single user in normal use - this is expected,
  handled gracefully (that source's results are just empty for this
  search), and other sources cover the gap.
- If it happens constantly: wait ~30-60 minutes before repeating the
  same query, or rely on OpenAlex (no rate limit issues observed) while
  others cool down.

---

## SSL certificate errors on Windows (`SSLCertVerificationError`)

**Fix:** Install `pip-system-certs` (already in `requirements.txt` for
Windows). See `docs/setup.md` section on this for details.

---

## General debugging tips learned during this project

- **Windows + `uvicorn --reload`:** sometimes leaves a stale server
  process running on port 8000 after `Ctrl+C`. Check with
  `netstat -ano | findstr :8000` and `taskkill /PID <pid> /F` if a new
  server won't bind.
- **Copy-pasted code with `<a>` tags:** some clipboard/editor setups can
  corrupt a standalone `<a` at the start of a pasted line. Keep anchor
  tags inline on one line, or type them manually if this recurs.
- **File encoding:** always save Python files as UTF-8. A Windows
  default encoding (cp1252) can crash on LLM-generated Unicode
  characters when writing cache files to disk.