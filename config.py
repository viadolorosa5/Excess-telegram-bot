import os

from dotenv import load_dotenv


load_dotenv()


def get_bot_token() -> str:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "Не найден BOT_TOKEN. Перед запуском задайте переменную окружения."
        )
    return token


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "Не найден DATABASE_URL. Перед запуском задайте URL PostgreSQL."
        )
    return database_url
