import asyncio
import datetime
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.repository import get_due_reminders, mark_reminder_sent

logger = logging.getLogger(__name__)


async def reminder_loop(
    bot: Bot,
    session_factory: async_sessionmaker,
) -> None:
    try:
        while True:
            now = datetime.datetime.now(datetime.UTC)
            async with session_factory() as session:
                reminders = await get_due_reminders(session, now=now)

            for chat_telegram_id, chat_id, reminder_text in reminders:
                try:
                    await bot.send_message(chat_telegram_id, reminder_text)
                except TelegramAPIError:
                    logger.exception(
                        "Не удалось отправить напоминание в чат %s",
                        chat_telegram_id,
                    )
                    continue

                async with session_factory() as session:
                    await mark_reminder_sent(
                        session,
                        chat_id=chat_id,
                        sent_at=now,
                    )
                    await session.commit()

            await asyncio.sleep(60)
    except asyncio.CancelledError:
        logger.info("Проверка напоминаний остановлена")
        raise
