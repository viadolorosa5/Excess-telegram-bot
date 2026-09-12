import re

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.repository import (
    change_message_reactions,
    save_text_message,
    update_message_reactions,
)
from handlers.handler_babel import process_babel_message
from handlers.handler_glupy import maybe_send_glupy
from handlers.shared import (
    get_chat_settings_for_message,
    reject_private_chat,
    settings_text,
)
from keyboards.menu import (
    feature_keyboard,
    features_keyboard,
    main_menu_keyboard,
)


router = Router()
EMOJI_PATTERN = re.compile(
    r"[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF]"
)

FEATURES = {
    "stats": {
        "title": "📊 Статистика",
        "description": "Сохраняет текстовые сообщения и показывает активность чата и участников за день, неделю или месяц.",
        "settings": [],
    },
    "quotes": {
        "title": "📌 Цитаты",
        "description": "Сохраняет понравившиеся сообщения и показывает их вместе с автором и временем публикации.",
        "settings": [
            "/quote в ответ на сообщение — добавить его в цитаты",
            "/quotes [слово] [дата] [дата] — поиск по цитатам",
            "/quote_delete номер — удалить цитату (только администратору)",
        ],
    },
    "babel": {
        "title": "📚 Библиотека Вавилона",
        "description": "Иногда находит ваше сообщение среди случайных страниц Библиотеки Вавилона и показывает найденный фрагмент.",
        "settings": [
            "/babel 0–100 — вероятность автоматического поиска",
            "/babel в ответ на сообщение — найти его в библиотеке",
        ],
    },
    "reminders": {
        "title": "⏰ Напоминания",
        "description": "Следит за тишиной в чате и отправляет напоминание, если сообщений давно не было.",
        "settings": [
            "/silence on|off — включить или выключить напоминания",
            "/silence_time минуты — порог тишины",
            "/reminder текст — текст напоминания",
        ],
    },
    "glupy": {
        "title": "🌀 Глупи",
        "description": "Собирает короткие фразы из недавней истории чата, когда это уместно.",
        "settings": [
            "/glupy 0–100 — вероятность фразы",
            "/glupy on|off — включить или выключить",
            "/glupy_order 1–3 — креативность (1 — самая рандомная, 3 — более строгая)",
            "/glupy_cooldown минуты — пауза между фразами",
            "/glupy_length символы — максимальная длина",
            "/glupy_reply on|off — отвечать на исходное сообщение",
        ],
    },
}
FEATURE_COMMANDS = (
    "settings_babel",
    "settings_reminders",
    "settings_silence",
    "settings_glupy",
    "settings_stats",
    "settings_quotes",
)


def welcome_text() -> str:
    return (
        "✨ <b>Привет! Я ваш чат-бот.</b>\n\n"
        "Я сохраняю сообщения, показываю статистику, иногда заглядываю "
        "в Библиотеку Вавилона, собираю фразы из истории чата и напоминаю "
        "о чате после долгой тишины.\n\n"
        "Откройте /menu, чтобы выбрать нужный раздел."
    )


def menu_text() -> str:
    return (
        "🧭 <b>Меню бота</b>\n\n"
        "📊 <b>Статистика</b> — активность чата и участников за выбранный период.\n"
        "📚 <b>Библиотека Вавилона</b> — поиск сообщения среди случайных страниц.\n"
        "⏰ <b>Напоминания</b> — сигнал, когда в чате долго тихо.\n"
        "🌀 <b>Глупи</b> — короткие фразы из истории переписки.\n\n"
        "📌 <b>Цитаты</b> — сохранение и просмотр избранных сообщений.\n\n"
        "Выберите раздел для подробностей:"
    )


def help_index_text() -> str:
    return (
        "❓ <b>Помощь</b>\n\n"
        "Выберите фичу, чтобы увидеть её назначение и доступные настройки."
    )


def feature_text(feature: str, *, show_settings: bool) -> str:
    data = FEATURES[feature]
    text = f"{data['title']}\n\n{data['description']}"
    if show_settings and data["settings"]:
        text += "\n\n⚙️ <b>Доступные настройки</b>\n" + "\n".join(
            f"• {setting}" for setting in data["settings"]
        )
        text += "\n\nИзменять настройки могут только администраторы."
    return text


def feature_settings_text(feature: str) -> str:
    data = FEATURES[feature]
    if not data["settings"]:
        return f"{data['title']}\n\nДля этой фичи отдельных настроек нет."
    return (
        f"{data['title']}\n\n"
        "⚙️ <b>Доступные настройки</b>\n"
        + "\n".join(f"• {setting}" for setting in data["settings"])
    )


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    if await reject_private_chat(message):
        return
    await message.answer(
        welcome_text(),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    if await reject_private_chat(message):
        return
    await message.answer(
        help_index_text(),
        parse_mode="HTML",
        reply_markup=features_keyboard(),
    )


@router.message(Command("menu"))
async def handle_menu(message: Message) -> None:
    if await reject_private_chat(message):
        return
    await message.answer(
        menu_text(),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


async def _send_feature_settings(
    message: Message,
    feature: str,
) -> None:
    if await reject_private_chat(message):
        return
    await message.answer(
        feature_text(feature, show_settings=True),
        parse_mode="HTML",
        reply_markup=feature_keyboard(),
    )


@router.message(Command(*FEATURE_COMMANDS))
async def handle_feature_settings(
    message: Message,
    command: CommandObject,
) -> None:
    if await reject_private_chat(message):
        return
    command_name = command.command or ""
    feature = command_name.removeprefix("settings_")
    if feature == "silence":
        feature = "reminders"
    if feature not in FEATURES:
        return
    await _send_feature_settings(message, feature)


@router.message(Command("settings"))
async def handle_settings(
    message: Message,
    session_factory: async_sessionmaker,
) -> None:
    if await reject_private_chat(message):
        return
    settings = await get_chat_settings_for_message(message, session_factory)
    await message.answer(settings_text(settings), parse_mode="HTML")


@router.callback_query(F.data == "menu:help")
async def handle_menu_help(callback: CallbackQuery) -> None:
    if callback.message and await reject_private_chat(callback.message):
        await callback.answer()
        return
    if callback.message:
        await callback.message.edit_text(
            help_index_text(),
            parse_mode="HTML",
            reply_markup=features_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "menu:back")
async def handle_menu_back(callback: CallbackQuery) -> None:
    if callback.message and await reject_private_chat(callback.message):
        await callback.answer()
        return
    if callback.message:
        if callback.message.content_type == "photo":
            await callback.message.delete()
            await callback.message.answer(
                menu_text(),
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(),
            )
        else:
            await callback.message.edit_text(
                menu_text(),
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(),
            )
    await callback.answer()


@router.callback_query(F.data == "menu:features")
async def handle_feature_list(callback: CallbackQuery) -> None:
    if callback.message and await reject_private_chat(callback.message):
        await callback.answer()
        return
    if callback.message:
        await callback.message.edit_text(
            help_index_text(),
            parse_mode="HTML",
            reply_markup=features_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("menu:feature:"))
async def handle_feature(
    callback: CallbackQuery,
) -> None:
    if callback.message is None or callback.data is None:
        await callback.answer()
        return
    if await reject_private_chat(callback.message):
        await callback.answer()
        return
    feature = callback.data.removeprefix("menu:feature:")
    if feature not in FEATURES:
        await callback.answer("Неизвестная фича", show_alert=True)
        return
    await callback.message.edit_text(
        feature_text(feature, show_settings=True),
        parse_mode="HTML",
        reply_markup=feature_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:settings")
async def handle_menu_settings(
    callback: CallbackQuery,
    session_factory: async_sessionmaker,
) -> None:
    if callback.message and await reject_private_chat(callback.message):
        await callback.answer()
        return
    if callback.message:
        settings = await get_chat_settings_for_message(
            callback.message,
            session_factory,
        )
        await callback.message.edit_text(
            settings_text(settings),
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )
    await callback.answer()


@router.message()
async def handle_message(
    message: Message,
    bot: Bot,
    session_factory: async_sessionmaker,
) -> None:
    content_type = get_content_type(message)
    message_text = message.text or message.caption
    if content_type is None:
        return

    user = message.from_user
    async with session_factory() as session:
        await save_text_message(
            session,
            telegram_message_id=message.message_id,
            chat_telegram_id=message.chat.id,
            chat_title=message.chat.title,
            chat_type=message.chat.type,
            user_telegram_id=user.id if user else None,
            username=user.username if user else None,
            first_name=user.first_name if user else None,
            last_name=user.last_name if user else None,
            message_text=message_text,
            sent_at=message.date,
            content_type=content_type,
            emoji_count=len(EMOJI_PATTERN.findall(message_text or "")),
            media_file_id=message.sticker.file_id if message.sticker else None,
        )
        await session.commit()

    if message.text and await process_babel_message(message, session_factory):
        await maybe_send_glupy(message, bot, session_factory)


def get_content_type(message: Message) -> str | None:
    if message.photo:
        return "photo"
    if message.document:
        return "document"
    if message.animation:
        return "animation"
    if message.sticker:
        return "sticker"
    if message.video:
        return "video"
    if message.video_note:
        return "video_note"
    if message.audio:
        return "audio"
    if message.voice:
        return "voice"
    if message.text:
        return "text"
    return None


@router.message_reaction_count()
async def handle_reaction_count(
    event,
    session_factory: async_sessionmaker,
) -> None:
    async with session_factory() as session:
        await update_message_reactions(
            session,
            chat_telegram_id=event.chat.id,
            telegram_message_id=event.message_id,
            reaction_count=sum(reaction.total_count for reaction in event.reactions),
        )
        await session.commit()


@router.message_reaction()
async def handle_reaction(
    event,
    session_factory: async_sessionmaker,
) -> None:
    async with session_factory() as session:
        await change_message_reactions(
            session,
            chat_telegram_id=event.chat.id,
            telegram_message_id=event.message_id,
            delta=len(event.new_reaction) - len(event.old_reaction),
        )
        await session.commit()
