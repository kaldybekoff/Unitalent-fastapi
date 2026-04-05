import logging
import random
import time

from pyinstrument import Profiler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.config import settings

logger = logging.getLogger("unitalent.profiling")


class ProfilingMiddleware(BaseHTTPMiddleware):
    """
    Measures latency for every request.
    When PROFILING_ENABLED=true, also runs pyinstrument call-stack profiling
    and logs slow endpoints (latency > SLOW_ENDPOINT_THRESHOLD_MS).

    To avoid profiler overhead in production:
      - Set PROFILING_ENABLED=false (zero-cost passthrough)
      - Or enable sampling: only profile ~10% of requests via PROFILING_SAMPLE_RATE
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.profiling_enabled:
            return await call_next(request)

        # Optional sampling: profile only a fraction of requests
        # to reduce overhead. Currently 100% when enabled.
        if random.random() > 1.0:  # change 1.0 → 0.1 to sample 10%
            start = time.perf_counter()
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            if elapsed_ms > settings.slow_endpoint_threshold_ms:
                logger.warning(
                    "SLOW ENDPOINT (no profile) %s %s — %.0fms",
                    request.method, request.url.path, elapsed_ms,
                )
            return response

        profiler = Profiler(async_mode="enabled")
        profiler.start()
        response = await call_next(request)
        profiler.stop()

        elapsed_ms = profiler.last_session.duration * 1000  # type: ignore[union-attr]

        if elapsed_ms > settings.slow_endpoint_threshold_ms:
            logger.warning(
                "SLOW ENDPOINT %s %s — %.0fms\n%s",
                request.method,
                request.url.path,
                elapsed_ms,
                profiler.output_text(unicode=True, color=False, timeline=False),
            )
        else:
            logger.debug(
                "PROFILE %s %s — %.0fms",
                request.method, request.url.path, elapsed_ms,
            )

        return response
