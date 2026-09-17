"""
Shared rate limiter, keyed by remote IP. This is the public-service
guardrail called out in Phase 0 - gate abuse from day one rather than
bolting it on after launch. Limits themselves are configured via .env.
"""
import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


def log_rate_limit_hit(request, exc):
    """Called by slowapi's exception handler path indirectly via middleware logging."""
    logger.warning("Rate limit exceeded for %s on %s", get_remote_address(request), request.url.path)