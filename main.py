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
            BotCommand(command="help", description="Показать все команды"),
            BotCommand(command="stats", description="Статистика чата"),
            BotCommand(command="quote", description="Добавить сообщение в цитаты"),
            BotCommand(command="quotes", description="Показать цитаты чата"),
            BotCommand(command="quote_delete", description="Удалить цитату по номеру"),
            BotCommand(command="settings", description="Настройки чата"),
            BotCommand(command="settings_babel", description="Настройки Библиотеки Вавилона"),
            BotCommand(command="settings_reminders", description="Настройки напоминаний"),
            BotCommand(command="settings_silence", description="Настройки напоминаний"),
            BotCommand(command="settings_glupy", description="Настройки Глупи"),
            BotCommand(command="settings_stats", description="Раздел статистики"),
            BotCommand(command="settings_quotes", description="Раздел цитат"),
            BotCommand(command="babel", description="Вероятность Библиотеки Вавилона"),
            BotCommand(command="silence", description="Включить или выключить напоминания"),
            BotCommand(command="silence_time", description="Порог тишины в минутах"),
            BotCommand(command="reminder", description="Текст напоминания"),
            BotCommand(command="glupy", description="Настроить Глупи"),
            BotCommand(command="glupy_order", description="Креативность Глупи (1 — самая рандомная)"),
            BotCommand(command="glupy_cooldown", description="Cooldown Глупи"),
            BotCommand(command="glupy_length", description="Максимальная длина Глупи"),
            BotCommand(command="glupy_reply", description="Ответы Глупи на сообщения"),
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