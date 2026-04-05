from pyrate_limiter import Duration, Rate, Limiter
from fastapi_limiter.depends import RateLimiter

# ── Limits ────────────────────────────────────────────────────────────────────
# All requests per IP per minute
RATE_PER_MINUTE = 30
# All requests per IP per hour
RATE_PER_HOUR = 500
# POST/PATCH/DELETE per IP per hour (write operations only)
WRITE_RATE_PER_HOUR = 50

# ── Limiter instances ─────────────────────────────────────────────────────────
_limiter_per_minute = Limiter(Rate(RATE_PER_MINUTE, Duration.MINUTE))
_limiter_per_hour = Limiter(Rate(RATE_PER_HOUR, Duration.HOUR))
_write_limiter = Limiter(Rate(WRITE_RATE_PER_HOUR, Duration.HOUR))


def rate_limit_per_minute() -> RateLimiter:
    """30 requests/min per IP — applied globally."""
    return RateLimiter(_limiter_per_minute)


def rate_limit_per_hour() -> RateLimiter:
    """500 requests/hr per IP — applied globally."""
    return RateLimiter(_limiter_per_hour)


def write_rate_limit() -> RateLimiter:
    """50 write requests/hr per IP — applied to POST/PATCH/DELETE only."""
    return RateLimiter(_write_limiter)
