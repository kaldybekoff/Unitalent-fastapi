import io

from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.celery_app import celery_app
from src.config import settings


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def compress_and_store_photo(self, candidate_id: int, raw_bytes: bytes) -> None:
    """
    Compress the uploaded image with Pillow and store the binary
    directly in PostgreSQL (candidates.photo BYTEA).

    Logs image size before and after compression.
    """
    original_size = len(raw_bytes)
    print(f"[photo] candidate={candidate_id} | original size: {original_size} bytes "
          f"({original_size / 1024:.1f} KB)")

    # ── Compress ──────────────────────────────────────────────────────────────
    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    img.thumbnail((800, 800), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75, optimize=True)
    compressed = buf.getvalue()
    compressed_size = len(compressed)

    ratio = compressed_size / original_size if original_size else 1
    saved = original_size - compressed_size
    print(f"[photo] candidate={candidate_id} | compressed size: {compressed_size} bytes "
          f"({compressed_size / 1024:.1f} KB) — {ratio:.1%} of original, saved {saved / 1024:.1f} KB")

    # ── Store in PostgreSQL (sync session, Celery workers are sync) ───────────
    try:
        sync_url = settings.database_url.replace("+asyncpg", "")
        engine = create_engine(sync_url)
        with Session(engine) as db:
            from src.candidates.models import Candidate
            candidate = db.get(Candidate, candidate_id)
            if candidate:
                candidate.photo = compressed
                db.commit()
                print(f"[photo] candidate={candidate_id} | stored in PostgreSQL ✓")
    except Exception as exc:
        raise self.retry(exc=exc)
