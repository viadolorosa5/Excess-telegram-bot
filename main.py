import asyncio
import contextlib
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from config import get_bot_token
from database import (
    create_database_engine,
    create_database_schema,
    create_session_factory,
)
from handlers import router
from services.reminders import reminder_loop


async def main() -> None:
    engine = create_database_engine()
    await create_database_schema(engine)
    session_factory = create_session_factory(engine)
    bot = Bot(token=get_bot_token())
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Приветствие и описание возможностей"),
            BotCommand(command="menu", description="Открыть меню бота"),
        ]
    )
    dispatcher = Dispatcher()
    dispatcher["session_factory"] = session_factory
    dispatcher.include_router(router)
    reminders = asyncio.create_task(reminder_loop(bot, session_factory))

    try:
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
        reminders.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reminders
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())