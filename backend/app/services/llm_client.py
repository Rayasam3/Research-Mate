"""
LLM client supporting two interchangeable backends, chosen via
settings.llm_provider:

- "ollama": free, local, private, but slow on CPU-only machines (the
  default we started with).
- "groq": a hosted inference API running open models on custom hardware,
  typically 10-20x faster than local CPU inference. Needs a free API key
  from https://console.groq.com/keys.

Both are called through generate_json(), so the rest of the app (the
summarizer) never needs to know or care which one is active - switching
providers is a one-line .env change, which is exactly the kind of
cost/latency-driven model choice Phase 7 already anticipated for public
deployment.
"""
import json
import logging
import asyncio
import time
import httpx

from app.core.config import settings
from app.services.metrics import record_llm_latency



# A global lock ensures only one Groq request is in flight at a time,
# across all users and all concurrent requests. This turns "everyone
# hits the rate limit simultaneously" into "everyone waits their turn" -
# a real queue, not just a per-request retry.
_groq_request_lock = asyncio.Lock()

logger = logging.getLogger(__name__)


class LlmError(Exception):
    """Raised when the LLM call fails or returns something we can't parse."""


async def _generate_json_ollama(prompt: str) -> str:
    url = f"{settings.ollama_host}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError as exc:
        logger.error("Could not connect to Ollama at %s - is it running?", settings.ollama_host)
        raise LlmError(
            f"Could not connect to Ollama at {settings.ollama_host}. "
            "Make sure 'ollama serve' is running and the model is pulled."
        ) from exc
    except Exception as exc:
        logger.exception("Ollama request failed")
        raise LlmError(f"Ollama request failed: {exc}") from exc

    return data.get("response", "")


async def _generate_json_groq(prompt: str, retry_on_rate_limit: bool = True) -> str:
    if not settings.groq_api_key:
        raise LlmError(
            "llm_provider is set to 'groq' but GROQ_API_KEY is not set in .env. "
            "Get a free key at https://console.groq.com/keys"
        )

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    payload = {
        "model": settings.groq_model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }

    # Wait in line: only one Groq request goes out at a time across the
    # whole app. Under concurrent multi-user traffic, this turns
    # simultaneous rate-limit collisions into an orderly queue instead.
    async with _groq_request_lock:
        try:
            async with httpx.AsyncClient(timeout=settings.groq_timeout_seconds) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429 and retry_on_rate_limit:
                logger.warning("Groq rate-limited, waiting 12s before one retry")
                await asyncio.sleep(12)
                return await _generate_json_groq(prompt, retry_on_rate_limit=False)
            logger.error("Groq request failed with status %s: %s", exc.response.status_code, exc.response.text)
            raise LlmError(f"Groq request failed ({exc.response.status_code}): {exc.response.text[:300]}") from exc
        except Exception as exc:
            logger.exception("Groq request failed")
            raise LlmError(f"Groq request failed: {exc}") from exc

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        logger.error("Unexpected Groq response shape: %r", data)
        raise LlmError("Groq returned an unexpected response shape.") from exc


async def generate_json(prompt: str) -> dict:
    """
    Sends prompt to the configured LLM provider and parses the response as
    JSON. Raises LlmError on any failure - callers should catch this and
    report a clean LLM_FAILED status rather than crashing the request.
    """
    start = time.monotonic()
    if settings.llm_provider == "groq":
        raw_text = await _generate_json_groq(prompt)
    else:
        raw_text = await _generate_json_ollama(prompt)
    record_llm_latency((time.monotonic() - start) * 1000)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned non-JSON response: %r", raw_text[:500])
        raise LlmError("The LLM returned a response that wasn't valid JSON.") from exc