import datetime
import html
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
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
    get_stats_show_usernames,
    get_user_statistics,
)
from keyboards.statistics import statistics_keyboard
from database.repository import update_chat_setting
from handlers.shared import reject_if_not_admin, reject_private_chat


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
    show_usernames: bool,
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
        if username and show_usernames:
            display_name = f"<code>@{html.escape(username)}</code>"
        else:
            display_name = html.escape(
                " ".join(part for part in (first_name, last_name) if part)
                or "Неизвестный пользователь"
            )
        details = [
            f"• {display_name}: {count} сообщений, {characters} символов"
        ]
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

    figure, (messages_axes, characters_axes) = plt.subplots(
        2, 1, figsize=(10, 7), dpi=160
    )
    messages_axes.plot(
        labels,
        messages,
        color="#2563eb",
        marker="o",
        linewidth=2.2,
    )
    characters_axes.plot(
        labels,
        characters,
        color="#f97316",
        marker="o",
        linewidth=2.2,
    )
    messages_axes.set_title(f"Сообщения за {period_name}")
    messages_axes.set_ylabel("Количество")
    messages_axes.tick_params(axis="y", labelcolor="#2563eb")
    characters_axes.set_title(f"Символы за {period_name}")
    characters_axes.set_ylabel("Символы", color="#f97316")
    characters_axes.set_xlabel("Время" if period == "day" else "Дата")
    characters_axes.tick_params(axis="y", labelcolor="#f97316")
    messages_axes.grid(True, alpha=0.25)
    characters_axes.grid(True, alpha=0.25)
    figure.autofmt_xdate()
    figure.tight_layout()

    output = BytesIO()
    figure.savefig(output, format="png", bbox_inches="tight")
    plt.close(figure)
    return BufferedInputFile(
        output.getvalue(),
        filename=f"statistics_{period}_{id(output)}.png",
    )


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
        show_usernames = await get_stats_show_usernames(
            session,
            chat_telegram_id=chat_telegram_id,
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
        f"{format_user_statistics(users, detailed=True, show_usernames=show_usernames)}"
    )
    users_text = format_user_statistics(
        users,
        detailed=detailed,
        show_usernames=show_usernames,
    )
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


@router.message(Command("stats_usernames"))
async def handle_stats_usernames(
    message: Message,
    command: CommandObject,
    bot: Bot,
    session_factory: async_sessionmaker,
) -> None:
    if await reject_private_chat(message) or await reject_if_not_admin(bot, message):
        return
    value = (command.args or "").strip().casefold()
    if value not in {"on", "off"}:
        await message.answer(
            "Использование: <code>/stats_usernames on|off</code>\n"
            "on — показывать username без активной ссылки, off — имя пользователя.",
            parse_mode="HTML",
        )
        return
    async with session_factory() as session:
        await update_chat_setting(
            session,
            chat_telegram_id=message.chat.id,
            chat_title=message.chat.title,
            chat_type=message.chat.type,
            field_name="stats_show_usernames",
            value=value == "on",
        )
        await session.commit()
    await message.answer(
        "✅ В статистике будут отображаться "
        + ("username без упоминания." if value == "on" else "имена пользователей."),
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
    if callback.message.content_type == "photo":
        await callback.message.delete()
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=markup,
        )
    else:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=markup,
        )
    await callback.answer()
