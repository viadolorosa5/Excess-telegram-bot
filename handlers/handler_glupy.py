import datetime
import html
import random

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.repository import (
    get_glupy_settings,
    get_chat_sticker_file_ids,
    get_recent_message_texts,
    mark_glupy_sent,
    update_chat_setting,
)
from handlers.shared import reject_if_not_admin, reject_private_chat
from services.glupy import generate_glupy


router = Router()
EMOJI_RESPONSES = ("😀", "😄", "😂", "🤔", "😎", "🤨", "🙃", "🔥", "💀", "👍")


async def maybe_send_glupy(
    message: Message,
    bot: Bot,
    session_factory: async_sessionmaker,
) -> None:
    async with session_factory() as session:
        (
            enabled,
            probability,
            order,
            cooldown_minutes,
            max_length,
            reply_enabled,
            last_sent_at,
        ) = (
            await get_glupy_settings(
                session,
                chat_telegram_id=message.chat.id,
            )
        )
        now = datetime.datetime.now(datetime.UTC)
        if (
            not enabled
            or random.randint(1, 100) > probability
            or (
                last_sent_at is not None
                and now - last_sent_at
                < datetime.timedelta(minutes=cooldown_minutes)
            )
        ):
            return
        texts = await get_recent_message_texts(
            session,
            chat_telegram_id=message.chat.id,
        )
        sticker_file_ids = await get_chat_sticker_file_ids(
            session,
            chat_telegram_id=message.chat.id,
        )
    generated = generate_glupy(texts, order=order, max_length=max_length)
    actions = ["phrase", "emoji", "reaction"]
    if sticker_file_ids:
        actions.append("sticker")
    action = random.choice(actions)
    if action == "phrase" and generated is not None:
        if reply_enabled:
            await message.reply(html.escape(generated))
        else:
            await message.answer(html.escape(generated))
    elif action == "emoji" or generated is None and action != "sticker":
        await message.answer(random.choice(EMOJI_RESPONSES))
    elif action == "sticker":
        await message.answer_sticker(random.choice(sticker_file_ids))
    else:
        chat = await bot.get_chat(message.chat.id)
        available_reactions = chat.available_reactions or []
        if not available_reactions:
            await message.answer(random.choice(EMOJI_RESPONSES))
        else:
            try:
                await bot.set_message_reaction(
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    reaction=[random.choice(available_reactions)],
                )
            except (TelegramBadRequest, TelegramForbiddenError):
                await message.answer(random.choice(EMOJI_RESPONSES))

    async with session_factory() as session:
        await mark_glupy_sent(
            session,
            chat_telegram_id=message.chat.id,
            sent_at=datetime.datetime.now(datetime.UTC),
        )
        await session.commit()


@router.message(Command("glupy"))
async def handle_glupy_setting(
    message: Message,
    command: CommandObject,
    bot: Bot,
    session_factory: async_sessionmaker,
) -> None:
    if await reject_private_chat(message):
        return
    if await reject_if_not_admin(bot, message):
        return
    value = (command.args or "").strip().lower()
    if value in {"on", "off"}:
        field_name = "glupy_enabled"
        field_value = value == "on"
        response = f"✅ Глупи {'включены' if field_value else 'выключены'}."
    else:
        try:
            probability = int(value)
        except ValueError:
            await message.answer(
                "Использование: <code>/glupy 0-100</code> или "
                "<code>/glupy on|off</code>",
                parse_mode="HTML",
            )
            return
        if not 0 <= probability <= 100:
            await message.answer("Вероятность должна быть от 0 до 100.")
            return
        field_name = "glupy_probability_percent"
        field_value = probability
        response = f"✅ Шанс Глупи установлен: <b>{probability}%</b>."

    async with session_factory() as session:
        await update_chat_setting(
            session,
            chat_telegram_id=message.chat.id,
            chat_title=message.chat.title,
            chat_type=message.chat.type,
            field_name=field_name,
            value=field_value,
        )
        await session.commit()
    await message.answer(response, parse_mode="HTML")


async def update_integer_glupy_setting(
    message: Message,
    command: CommandObject,
    bot: Bot,
    session_factory: async_sessionmaker,
    *,
    field_name: str,
    minimum: int,
    maximum: int,
    label: str,
    command_name: str,
) -> None:
    if await reject_private_chat(message):
        return
    if await reject_if_not_admin(bot, message):
        return
    try:
        value = int((command.args or "").strip())
    except ValueError:
        await message.answer(
            f"Использование: <code>/{command_name} число</code>",
            parse_mode="HTML",
        )
        return
    if not minimum <= value <= maximum:
        await message.answer(f"Значение должно быть от {minimum} до {maximum}.")
        return
    async with session_factory() as session:
        await update_chat_setting(
            session,
            chat_telegram_id=message.chat.id,
            chat_title=message.chat.title,
            chat_type=message.chat.type,
            field_name=field_name,
            value=value,
        )
        await session.commit()
    await message.answer(f"✅ {label}: <b>{value}</b>.", parse_mode="HTML")


@router.message(Command("glupy_order"))
async def handle_glupy_order(
    message: Message,
    command: CommandObject,
    bot: Bot,
    session_factory: async_sessionmaker,
) -> None:
    await update_integer_glupy_setting(
        message, command, bot, session_factory,
        field_name="glupy_order", minimum=1, maximum=3,
        label="Креативность", command_name="glupy_order",
    )


@router.message(Command("glupy_cooldown"))
async def handle_glupy_cooldown(
    message: Message,
    command: CommandObject,
    bot: Bot,
    session_factory: async_sessionmaker,
) -> None:
    await update_integer_glupy_setting(
        message, command, bot, session_factory,
        field_name="glupy_cooldown_minutes", minimum=0, maximum=10080,
        label="Cooldown (минуты)", command_name="glupy_cooldown",
    )


@router.message(Command("glupy_length"))
async def handle_glupy_length(
    message: Message,
    command: CommandObject,
    bot: Bot,
    session_factory: async_sessionmaker,
) -> None:
    await update_integer_glupy_setting(
        message, command, bot, session_factory,
        field_name="glupy_max_length", minimum=2, maximum=4096,
        label="Максимальная длина (символы)", command_name="glupy_length",
    )


@router.message(Command("glupy_reply"))
async def handle_glupy_reply(
    message: Message,
    command: CommandObject,
    bot: Bot,
    session_factory: async_sessionmaker,
) -> None:
    if await reject_if_not_admin(bot, message):
        return
    value = (command.args or "").strip().lower()
    if value not in {"on", "off"}:
        await message.answer(
            "Использование: <code>/glupy_reply on|off</code>",
            parse_mode="HTML",
        )
        return
    enabled = value == "on"
    async with session_factory() as session:
        await update_chat_setting(
            session,
            chat_telegram_id=message.chat.id,
            chat_title=message.chat.title,
            chat_type=message.chat.type,
            field_name="glupy_reply_enabled",
            value=enabled,
        )
        await session.commit()
    status = "включены" if enabled else "выключены"
    await message.answer(f"✅ Ответы Глупи: <b>{status}</b>.", parse_mode="HTML")
