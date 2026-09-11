import html
import logging
import random

from aiohttp import ClientError
from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.repository import (
    get_babel_probability,
    update_chat_setting,
)
from services.babel import find_babel_location, normalize_for_babel
from handlers.shared import reject_if_not_admin, reject_private_chat


router = Router()
logger = logging.getLogger(__name__)


async def process_babel_message(
    message: Message,
    session_factory: async_sessionmaker,
    *,
    text: str | None = None,
    reply_to_message_id: int | None = None,
    force: bool = False,
) -> bool:
    """Process Babel for a saved message and return whether Glupy may run."""
    async with session_factory() as session:
        probability = await get_babel_probability(
            session,
            chat_telegram_id=message.chat.id,
        )
    if not force and random.randint(1, 100) > probability:
        return True
    source_text = text if text is not None else (message.text or "")

    try:
        location = await find_babel_location(source_text)
    except (ClientError, TimeoutError, RuntimeError):
        logger.exception("Не удалось найти сообщение в Библиотеке Вавилона")
        await message.answer(
            "Сообщение сохранено, но координаты в Библиотеке Вавилона "
            "получить не удалось."
        )
        return False

    if location is None:
        await message.answer(
            "Сообщение сохранено, но в нём нет символов, которые "
            "поддерживает Библиотека Вавилона."
        )
        return False

    wall, shelf, volume, page, page_text, url = location
    normalized = normalize_for_babel(source_text)
    context = page_text
    phrase_start = context.lower().find(normalized.lower())
    if phrase_start < 0:
        context = normalized
        phrase_start = 0
    phrase_end = phrase_start + len(normalized)
    context_start = max(0, phrase_start - 20)
    context_end = min(len(context), phrase_end + 20)
    before = html.escape(context[context_start:phrase_start])
    phrase = html.escape(context[phrase_start:phrase_end])
    after = html.escape(context[phrase_end:context_end])
    await message.answer(
        "📚 <b>Библиотека Вавилона</b>\n\n"
        f"Фрагмент: ...{before}<b>{phrase}</b>{after}...\n\n"
        f"Стена: <code>{wall}</code>\n"
        f"Полка: <code>{shelf}</code>\n"
        f"Книга: <code>{volume}</code>\n"
        f"Страница: <code>{page}</code>\n"
        f'<a href="{url}">Открыть страницу в библиотеке</a>',
        parse_mode="HTML",
        reply_to_message_id=reply_to_message_id or message.message_id,
    )
    return False


@router.message(Command("babel"))
async def handle_babel_setting(
    message: Message,
    command: CommandObject,
    bot: Bot,
    session_factory: async_sessionmaker,
) -> None:
    if await reject_private_chat(message):
        return
    args = (command.args or "").strip()
    replied = message.reply_to_message
    if not args and replied is not None and replied.text:
        await process_babel_message(
            message,
            session_factory,
            text=replied.text,
            reply_to_message_id=replied.message_id,
            force=True,
        )
        return

    if not args:
        await message.answer(
            "Ответьте командой <code>/babel</code> на текстовое сообщение, "
            "чтобы найти его в Библиотеке Вавилона.",
            parse_mode="HTML",
        )
        return

    if await reject_if_not_admin(bot, message):
        return
    try:
        value = int(args)
    except ValueError:
        await message.answer("Использование: <code>/babel 0-100</code>", parse_mode="HTML")
        return
    if not 0 <= value <= 100:
        await message.answer("Вероятность должна быть от 0 до 100.")
        return
    async with session_factory() as session:
        await update_chat_setting(
            session,
            chat_telegram_id=message.chat.id,
            chat_title=message.chat.title,
            chat_type=message.chat.type,
            field_name="babel_probability_percent",
            value=value,
        )
        await session.commit()
    await message.answer(
        f"✅ Вероятность Библиотеки Вавилона установлена: <b>{value}%</b>.",
        parse_mode="HTML",
    )
