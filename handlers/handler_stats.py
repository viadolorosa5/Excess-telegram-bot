import datetime
import html
from io import BytesIO

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InputMediaPhoto,
    Message,
)
import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.repository import (
    get_activity_insights,
    get_activity_buckets,
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
    *,
    detailed: bool,
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
        details = [f"• {html.escape(name)}: {count} сообщений, {characters} символов"]
        if not detailed:
            lines.append("\n".join(details))
            continue
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


def create_activity_chart(
    buckets: list[tuple[datetime.datetime, int, int]],
    *,
    period: str,
    period_name: str,
) -> BufferedInputFile:
    labels = [
        timestamp.strftime("%H:%M") if period == "day" else timestamp.strftime("%d.%m")
        for timestamp, _, _ in buckets
    ]
    messages = [message_count for _, message_count, _ in buckets]
    characters = [character_count for _, _, character_count in buckets]

    figure, axes = plt.subplots(figsize=(10, 5), dpi=160)
    axes.plot(labels, messages, marker="o", linewidth=2.2, label="Сообщения")
    axes.plot(labels, characters, marker="o", linewidth=2.2, label="Символы")
    axes.set_title(f"Активность чата за {period_name}")
    axes.set_xlabel("Время" if period == "day" else "Дата")
    axes.set_ylabel("Количество")
    axes.grid(True, alpha=0.25)
    axes.legend()
    figure.autofmt_xdate()
    figure.tight_layout()

    output = BytesIO()
    figure.savefig(output, format="png", bbox_inches="tight")
    plt.close(figure)
    return BufferedInputFile(output.getvalue(), filename="statistics.png")


async def build_activity_chart(
    session_factory: async_sessionmaker,
    *,
    chat_telegram_id: int,
    period: str,
) -> BufferedInputFile | None:
    period_name, period_delta = PERIODS[period]
    since = datetime.datetime.now(datetime.UTC) - period_delta
    async with session_factory() as session:
        buckets = await get_activity_buckets(
            session,
            chat_telegram_id=chat_telegram_id,
            since=since,
            bucket="hour" if period == "day" else "day",
        )
    if not buckets:
        return None
    return create_activity_chart(
        buckets,
        period=period,
        period_name=period_name,
    )


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
    detailed: bool = False,
) -> str:
    period_name, period_delta = PERIODS[period]
    since = datetime.datetime.now(datetime.UTC) - period_delta

    async with session_factory() as session:
        count, characters = await get_chat_statistics(
            session,
            chat_telegram_id=chat_telegram_id,
            since=since,
        )
        insights = await get_activity_insights(
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
        )
        rich = await get_rich_statistics(
            session,
            chat_telegram_id=chat_telegram_id,
            since=since,
        )

    (
        media_counts,
        total_emojis,
        total_reactions,
        common_emoji,
        common_emoji_count,
    ) = rich
    _, average_characters, peak_hour = insights
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
    extras_lines = media_lines if detailed else []
    if detailed and total_emojis:
        emoji_text = f"😀 Эмодзи: <b>{total_emojis}</b>"
        extras_lines.append(emoji_text)
        if common_emoji:
            extras_lines.append(
                f"🔥 Частый эмодзи: <b>{html.escape(common_emoji)}</b> "
                f"({common_emoji_count} раз.)"
            )
    if detailed and total_reactions:
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
    peak_hour_text = (
        f"🕒 Самый активный час: <b>{peak_hour:02d}:00–{peak_hour:02d}:59</b>\n\n"
        if peak_hour is not None
        else "\n"
    )
    detailed_text = (
        f"📏 В среднем символов в сообщении: <b>{average_characters:.1f}</b>\n"
        f"{peak_hour_text}"
        f"{extras_text + chr(10) + chr(10) if extras_text else ''}"
        f"🔥 Частое слово: <b>{frequent_text}</b>\n\n"
        "👥 <b>По пользователям</b>\n"
        f"{format_user_statistics(users, detailed=True)}"
    )
    users_text = format_user_statistics(users, detailed=detailed)
    stats_details = detailed_text if detailed else (
        "👥 <b>По пользователям</b>\n" + users_text
    )
    return (
        f"📊 <b>Статистика за {period_name}</b>\n\n"
        f"💬 Сообщений: <b>{count}</b>\n"
        f"🔤 Символов: <b>{characters}</b>\n"
        f"\n{stats_details}"
        f"{quote_text if detailed else ''}"
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
        detailed=False,
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
            detailed=False,
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

    parts = callback.data.split(":")
    period = parts[1] if len(parts) > 1 else ""
    detailed = len(parts) > 2 and parts[2] == "1"
    charts = len(parts) > 3 and parts[3] == "1"
    if period not in PERIODS:
        await callback.answer("Неизвестный период", show_alert=True)
        return

    markup = statistics_keyboard(period, detailed, charts)
    if charts:
        chart = await build_activity_chart(
            session_factory,
            chat_telegram_id=callback.message.chat.id,
            period=period,
        )
        if chart is None:
            await callback.message.edit_text(
                f"📊 <b>Статистика за {PERIODS[period][0]}</b>\n\n"
                "За этот период нет данных для графика.",
                parse_mode="HTML",
                reply_markup=markup,
            )
        else:
            await callback.message.edit_media(
                InputMediaPhoto(
                    media=chart,
                    caption=f"📈 <b>График активности за {PERIODS[period][0]}</b>",
                    parse_mode="HTML",
                ),
                reply_markup=markup,
            )
        await callback.answer()
        return

    text = await build_statistics_text(
        session_factory,
        chat_telegram_id=callback.message.chat.id,
        period=period,
        detailed=detailed,
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=markup,
    )
    await callback.answer()
