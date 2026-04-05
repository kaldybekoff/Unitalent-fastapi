import logging
import os
import time
from logging.handlers import RotatingFileHandler

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ── Logger setup ──────────────────────────────────────────────────────────────

os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("unitalent.access")
logger.setLevel(logging.DEBUG)

fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

_console = logging.StreamHandler()
_console.setFormatter(fmt)

_file = RotatingFileHandler("logs/app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
_file.setFormatter(fmt)

logger.addHandler(_console)
logger.addHandler(_file)
logger.propagate = False


# ── Middleware ────────────────────────────────────────────────────────────────

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        client = request.client
        ip = client.host if client else "unknown"
        port = client.port if client else 0

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        status = response.status_code
        msg = f"{ip}:{port} - {request.method} - {request.url.path} - {status} - {elapsed_ms:.2f}ms"

        if status >= 500:
            logger.error(msg)
        elif status >= 400:
            logger.warning(msg)
        else:
            logger.info(msg)

        return response
