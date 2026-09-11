import datetime
import html

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.repository import (
    get_chat_statistics,
    get_most_frequent_word,
    get_rich_statistics,
    get_random_quote,
    get_user_statistics,
)
from keyboards.statistics import statistics_keyboard
from handlers.shared import reject_private_chat


router = Router()
PERIODS = {
    "day": ("сутки", datetime.timedelta(days=1)),
    "week": ("неделю", datetime.timedelta(days=7)),
    "month": ("месяц", datetime.timedelta(days=30)),
}


def format_user_statistics(
    rows: list[tuple],
) -> str:
    if not rows:
        return "нет сообщений"

    lines = []
    for (
        _,
        username,
        first_name,
        last_name,
        count,
        characters,
        media_counts,
        total_emojis,
        total_reactions,
        common_emoji,
        common_emoji_count,
    ) in rows:
        if username:
            name = f"@{username}"
        else:
            name = " ".join(part for part in (first_name, last_name) if part)
            name = name or "Неизвестный пользователь"
        details = [f"• {html.escape(name)}: {count} сообщений, {characters} символов,"]
        media_parts = [
            f"{label}: <b>{media_counts[content_type]}</b>"
            for content_type, label in MEDIA_LABELS.items()
            if media_counts.get(content_type)
        ]
        if media_parts:
            details.append("  " + ", ".join(media_parts))
        emoji_parts = []
        if total_emojis:
            emoji_parts.append(f"😀: <b>{total_emojis}</b>")
            if common_emoji:
                emoji_parts.append(
                    f"частый {html.escape(common_emoji)} ({common_emoji_count})"
                )
        if total_reactions:
            emoji_parts.append(f"🌭: <b>{total_reactions}</b>")
        if emoji_parts:
            details.append("  " + ", ".join(emoji_parts))
        lines.append("\n".join(details))
    return "\n".join(lines)


MEDIA_LABELS = {
    "photo": "🖼",
    "document": "📎",
    "animation": "🎞",
    "sticker": "🎭",
    "video": "🎥",
    "audio": "🎵",
    "voice": "🎙",
    "video_note": "⭕",
}


async def build_statistics_text(
    session_factory: async_sessionmaker,
    *,
    chat_telegram_id: int,
    period: str,
) -> str:
    period_name, period_delta = PERIODS[period]
    since = datetime.datetime.now(datetime.UTC) - period_delta

    async with session_factory() as session:
        count, characters = await get_chat_statistics(
            session,
            chat_telegram_id=chat_telegram_id,
            since=since,
        )
        users = await get_user_statistics(
            session,
            chat_telegram_id=chat_telegram_id,
            since=since,
        )
        frequent_word = await get_most_frequent_word(
            session,
            chat_telegram_id=chat_telegram_id,
            since=since,
        )
        quote = await get_random_quote(
            session,
            chat_telegram_id=chat_telegram_id,
            since=since,
        )
        rich = await get_rich_statistics(
            session,
            chat_telegram_id=chat_telegram_id,
            since=since,
        )

    media_counts, total_emojis, total_reactions, common_emoji, common_emoji_count = rich
    media_labels = {
        "photo": "🖼 Картинок",
        "document": "📎 Файлов",
        "animation": "🎞 GIF-анимаций",
        "sticker": "🎭 Стикеров",
        "video": "🎥 Видео",
        "audio": "🎵 Аудио",
        "voice": "🎙 Голосовых",
        "video_note": "⭕ Видеосообщений",
    }
    media_lines = [
        f"{label}: <b>{media_counts[content_type]}</b>"
        for content_type, label in media_labels.items()
        if media_counts.get(content_type)
    ]
    extras_lines = media_lines
    if total_emojis:
        emoji_text = f"😀 Эмодзи: <b>{total_emojis}</b>"
        extras_lines.append(emoji_text)
        if common_emoji:
            extras_lines.append(
                f"🔥 Частый эмодзи: <b>{html.escape(common_emoji)}</b> "
                f"({common_emoji_count} раз.)"
            )
    if total_reactions:
        extras_lines.append(f"🌭 Реакций: <b>{total_reactions}</b>")
    extras_text = "\n".join(extras_lines)
    quote_text = ""
    if quote:
        username, first_name, last_name, text, sent_at = quote
        author = f"@{username}" if username else " ".join(
            part for part in (first_name, last_name) if part
        ) or "Неизвестный пользователь"
        quote_text = (
            f"\n\n💬 <b>Случайная цитата</b>\n"
            f"«{html.escape(text)}»\n"
            f"— {html.escape(author)}, {sent_at.strftime('%d.%m.%Y %H:%M')}"
        )

    frequent_text = (
        f"{html.escape(frequent_word[0])} ({frequent_word[1]} раз.)"
        if frequent_word
        else "нет данных"
    )
    return (
        f"📊 <b>Статистика за {period_name}</b>\n\n"
        f"💬 Сообщений: <b>{count}</b>\n"
        f"🔤 Символов: <b>{characters}</b>\n"
        f"{extras_text + chr(10) + chr(10) if extras_text else ''}"
        f"🔥 Частое слово: <b>{frequent_text}</b>\n\n"
        "👥 <b>По пользователям</b>\n"
        f"{format_user_statistics(users)}"
        f"{quote_text}"
    )


@router.message(Command("stats"))
async def handle_stats(
    message: Message,
    session_factory: async_sessionmaker,
) -> None:
    if await reject_private_chat(message):
        return
    text = await build_statistics_text(
        session_factory,
        chat_telegram_id=message.chat.id,
        period="day",
    )
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=statistics_keyboard("day"),
    )


@router.callback_query(F.data == "menu:stats")
async def handle_menu_stats(
    callback: CallbackQuery,
    session_factory: async_sessionmaker,
) -> None:
    if callback.message and await reject_private_chat(callback.message):
        await callback.answer()
        return
    if callback.message:
        text = await build_statistics_text(
            session_factory,
            chat_telegram_id=callback.message.chat.id,
            period="day",
        )
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=statistics_keyboard("day"),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("stats:"))
async def handle_statistics_callback(
    callback: CallbackQuery,
    session_factory: async_sessionmaker,
) -> None:
    if callback.message is None or callback.data is None:
        await callback.answer("Статистика обновлена", show_alert=True)
        return
    if await reject_private_chat(callback.message):
        await callback.answer()
        return

    period = callback.data.removeprefix("stats:")
    if period not in PERIODS:
        await callback.answer("Неизвестный период", show_alert=True)
        return

    text = await build_statistics_text(
        session_factory,
        chat_telegram_id=callback.message.chat.id,
        period=period,
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=statistics_keyboard(period),
    )
    await callback.answer()
