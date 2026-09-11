from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from config import get_database_url
from database.models import Base


def create_database_engine() -> AsyncEngine:
    return create_async_engine(get_database_url(), pool_pre_ping=True)


async def create_database_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.execute(
            text(
                "ALTER TABLE chat_settings "
                "ADD COLUMN IF NOT EXISTS glupy_probability_percent "
                "INTEGER NOT NULL DEFAULT 3"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE chat_settings "
                "ADD COLUMN IF NOT EXISTS glupy_enabled "
                "BOOLEAN NOT NULL DEFAULT TRUE"
            )
        )
        await connection.execute(
            text(
                "DO $$ "
                "BEGIN "
                "IF NOT EXISTS ("
                "SELECT 1 FROM pg_constraint "
                "WHERE conname = 'chat_settings_glupy_probability_check'"
                ") THEN "
                "ALTER TABLE chat_settings "
                "ADD CONSTRAINT chat_settings_glupy_probability_check "
                "CHECK (glupy_probability_percent BETWEEN 0 AND 100); "
                "END IF; "
                "END $$"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE chat_settings "
                "ADD COLUMN IF NOT EXISTS glupy_order INTEGER NOT NULL DEFAULT 1"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE chat_settings "
                "ADD COLUMN IF NOT EXISTS glupy_cooldown_minutes "
                "INTEGER NOT NULL DEFAULT 10"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE chat_settings "
                "ADD COLUMN IF NOT EXISTS glupy_max_length "
                "INTEGER NOT NULL DEFAULT 200"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE chat_settings "
                "ADD COLUMN IF NOT EXISTS glupy_reply_enabled "
                "BOOLEAN NOT NULL DEFAULT TRUE"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE chat_activity "
                "ADD COLUMN IF NOT EXISTS glupy_last_sent_at TIMESTAMPTZ"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE messages "
                "ADD COLUMN IF NOT EXISTS content_type TEXT NOT NULL DEFAULT 'text'"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE messages "
                "ADD COLUMN IF NOT EXISTS emoji_count INTEGER NOT NULL DEFAULT 0"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE messages "
                "ADD COLUMN IF NOT EXISTS reaction_count INTEGER NOT NULL DEFAULT 0"
            )
        )
        await connection.execute(
            text(
                "ALTER TABLE messages "
                "ADD COLUMN IF NOT EXISTS media_file_id TEXT"
            )
        )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)
