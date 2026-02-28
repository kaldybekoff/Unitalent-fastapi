from sqlmodel import SQLModel

# важно импортировать models, чтобы SQLModel "увидел" таблицы
import src.candidates.models  # noqa
import src.companies.models   # noqa
import src.jobs.models        # noqa
import src.applications.models  # noqa
import src.interviews.models  # noqa

from src.db.session import engine


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)