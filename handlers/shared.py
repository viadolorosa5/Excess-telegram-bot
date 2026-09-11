import html

from aiogram import Bot
from aiogram.types import Message

from database.repository import get_or_create_chat_settings


async def reject_private_chat(message: Message) -> bool:
    if message.chat.type != "private":
        return False
    await message.answer("В личных сообщениях работает только Глупи.")
    return True


async def is_chat_admin(bot: Bot, message: Message) -> bool:
    if message.chat.type == "private":
        return True
    if message.from_user is None:
        return False
    return await is_user_chat_admin(bot, message.chat.id, message.from_user.id)


async def is_user_chat_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in {"administrator", "creator"}


async def reject_if_not_admin(bot: Bot, message: Message) -> bool:
    if await is_chat_admin(bot, message):
        return False
    await message.answer("🔒 Изменять настройки чата могут только администраторы.")
    return True


async def get_chat_settings_for_message(message: Message, session_factory):
    async with session_factory() as session:
        settings = await get_or_create_chat_settings(
            session,
            chat_telegram_id=message.chat.id,
            chat_title=message.chat.title,
            chat_type=message.chat.type,
        )
        await session.commit()
    return settings


def settings_text(settings) -> str:
    silence = "включены" if settings.silence_enabled else "выключены"
    return (
        "⚙️ <b>Настройки этого чата</b>\n\n"
        f"📚 Библиотека Вавилона: <b>{settings.babel_probability_percent}%</b>\n"
        f"⏰ Напоминания о тишине: <b>{silence}</b>\n"
        f"⌛ Порог тишины: <b>{settings.silence_threshold_minutes} мин.</b>\n"
        f"💬 Текст напоминания: <i>{html.escape(settings.reminder_text)}</i>\n\n"
        f"🌀 Глупи: <b>{'включена' if settings.glupy_enabled else 'выключена'}</b>, "
        f"шанс <b>{settings.glupy_probability_percent}%</b>, "
        f"креативность <b>{settings.glupy_order}</b>, "
        f"cooldown <b>{settings.glupy_cooldown_minutes} мин.</b>, "
        f"длина <b>{settings.glupy_max_length} симв.</b>, "
        f"ответом <b>{'включено' if settings.glupy_reply_enabled else 'выключено'}</b>"
    )
