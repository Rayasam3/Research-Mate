"""
Shared rate limiter, keyed by remote IP. This is the public-service
guardrail called out in Phase 0 — gate abuse from day one rather than
bolting it on after launch. Limits themselves are configured via .env.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
