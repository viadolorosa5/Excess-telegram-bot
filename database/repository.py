import datetime
import re
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Chat, ChatActivity, ChatSettings, Message, Quote, User


async def get_or_create_chat_settings(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
    chat_title: str | None,
    chat_type: str,
) -> ChatSettings:
    chat = await session.scalar(
        select(Chat).where(Chat.telegram_id == chat_telegram_id)
    )
    if chat is None:
        chat = Chat(
            telegram_id=chat_telegram_id,
            title=chat_title,
            chat_type=chat_type,
        )
        session.add(chat)
        await session.flush()

    settings = await session.get(ChatSettings, chat.id)
    if settings is None:
        settings = ChatSettings(chat_id=chat.id)
        session.add(settings)
        await session.flush()
    return settings


async def update_chat_setting(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
    chat_title: str | None = None,
    chat_type: str = "group",
    field_name: str,
    value: object,
) -> ChatSettings:
    chat = await session.scalar(
        select(Chat).where(Chat.telegram_id == chat_telegram_id)
    )
    if chat is None:
        chat = Chat(
            telegram_id=chat_telegram_id,
            title=chat_title,
            chat_type=chat_type,
        )
        session.add(chat)
        await session.flush()

    settings = await session.get(ChatSettings, chat.id)
    if settings is None:
        settings = ChatSettings(chat_id=chat.id)
        session.add(settings)
        await session.flush()

    if field_name not in {
        "silence_enabled",
        "silence_threshold_minutes",
        "reminder_text",
        "babel_probability_percent",
        "glupy_probability_percent",
        "glupy_enabled",
        "glupy_order",
        "glupy_cooldown_minutes",
        "glupy_max_length",
        "glupy_reply_enabled",
    }:
        raise ValueError(f"Недопустимая настройка: {field_name}")
    setattr(settings, field_name, value)
    return settings


async def save_text_message(
    session: AsyncSession,
    *,
    telegram_message_id: int,
    chat_telegram_id: int,
    chat_title: str | None,
    chat_type: str,
    user_telegram_id: int | None,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    message_text: str | None,
    sent_at: datetime.datetime,
    content_type: str = "text",
    emoji_count: int = 0,
    reaction_count: int = 0,
    media_file_id: str | None = None,
) -> None:
    chat = await session.scalar(
        select(Chat).where(Chat.telegram_id == chat_telegram_id)
    )
    if chat is None:
        chat = Chat(
            telegram_id=chat_telegram_id,
            title=chat_title,
            chat_type=chat_type,
        )
        session.add(chat)
        await session.flush()
    else:
        chat.title = chat_title
        chat.chat_type = chat_type

    user = None
    if user_telegram_id is not None:
        user = await session.scalar(
            select(User).where(User.telegram_id == user_telegram_id)
        )
        if user is None:
            user = User(
                telegram_id=user_telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            session.add(user)
            await session.flush()
        else:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name

    duplicate = await session.scalar(
        select(Message.id).where(
            Message.chat_id == chat.id,
            Message.telegram_message_id == telegram_message_id,
        )
    )
    if duplicate is None:
        session.add(
            Message(
                telegram_message_id=telegram_message_id,
                chat_id=chat.id,
                user_id=user.id if user else None,
                message_text=message_text,
                content_type=content_type,
                emoji_count=emoji_count,
                reaction_count=reaction_count,
                media_file_id=media_file_id,
                sent_at=sent_at,
            )
        )
        await session.flush()

        activity_upsert = insert(ChatActivity).values(
            chat_id=chat.id,
            last_message_at=sent_at,
            last_message_id=telegram_message_id,
        )
        await session.execute(
            activity_upsert.on_conflict_do_update(
                index_elements=[ChatActivity.chat_id],
                set_={
                    "last_message_at": activity_upsert.excluded.last_message_at,
                    "last_message_id": activity_upsert.excluded.last_message_id,
                },
            )
        )
        settings_upsert = insert(ChatSettings).values(
            chat_id=chat.id,
            silence_enabled=True,
        )
        await session.execute(
            settings_upsert.on_conflict_do_nothing(
                index_elements=[ChatSettings.chat_id]
            )
        )


async def get_chat_sticker_file_ids(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
) -> list[str]:
    rows = await session.scalars(
            select(Message.media_file_id)
            .join(Chat)
            .where(
                Chat.telegram_id == chat_telegram_id,
                Message.content_type == "sticker",
                Message.media_file_id.is_not(None),
            )
            .distinct()
    )
    return [file_id for file_id in rows if file_id]
async def update_message_reactions(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
    telegram_message_id: int,
    reaction_count: int,
) -> None:
    message = await session.scalar(
        select(Message)
        .join(Chat)
        .where(
            Chat.telegram_id == chat_telegram_id,
            Message.telegram_message_id == telegram_message_id,
        )
    )
    if message is not None:
        message.reaction_count = reaction_count


async def change_message_reactions(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
    telegram_message_id: int,
    delta: int,
) -> None:
    message = await session.scalar(
        select(Message)
        .join(Chat)
        .where(
            Chat.telegram_id == chat_telegram_id,
            Message.telegram_message_id == telegram_message_id,
        )
    )
    if message is not None:
        message.reaction_count = max(0, message.reaction_count + delta)


async def get_babel_probability(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
) -> int:
    probability = await session.scalar(
        select(ChatSettings.babel_probability_percent)
        .join(Chat, Chat.id == ChatSettings.chat_id)
        .where(Chat.telegram_id == chat_telegram_id)
    )
    return int(probability) if probability is not None else 20


async def get_glupy_settings(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
) -> tuple[bool, int, int, int, int, bool, datetime.datetime | None]:
    result = await session.execute(
        select(
            ChatSettings.glupy_enabled,
            ChatSettings.glupy_probability_percent,
            ChatSettings.glupy_order,
            ChatSettings.glupy_cooldown_minutes,
            ChatSettings.glupy_max_length,
            ChatSettings.glupy_reply_enabled,
            ChatActivity.glupy_last_sent_at,
        )
        .join(Chat, Chat.id == ChatSettings.chat_id)
        .outerjoin(ChatActivity, ChatActivity.chat_id == Chat.id)
        .where(Chat.telegram_id == chat_telegram_id)
    )
    row = result.first()
    if row is None:
        return True, 3, 1, 10, 200, True, None
    return (
        bool(row[0]), int(row[1]), int(row[2]), int(row[3]), int(row[4]),
        bool(row[5]), row[6]
    )


async def mark_glupy_sent(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
    sent_at: datetime.datetime,
) -> None:
    chat_id = await session.scalar(
        select(Chat.id).where(Chat.telegram_id == chat_telegram_id)
    )
    if chat_id is None:
        return
    activity = await session.get(ChatActivity, chat_id)
    if activity is None:
        session.add(ChatActivity(chat_id=chat_id, glupy_last_sent_at=sent_at))
    else:
        activity.glupy_last_sent_at = sent_at


async def get_recent_message_texts(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
    limit: int = 500,
) -> list[str]:
    rows = (
        await session.execute(
            select(Message.user_id, Message.message_text, Message.sent_at)
        .join(Chat, Chat.id == Message.chat_id)
        .where(
            Chat.telegram_id == chat_telegram_id,
            Message.message_text.is_not(None),
        )
        .order_by(Message.sent_at.desc())
        .limit(limit)
        )
    )
    messages = [
        (user_id, text, sent_at)
        for user_id, text, sent_at in reversed(rows.all())
        if text
    ]
    grouped: list[str] = []
    previous_user_id: int | None = None
    previous_sent_at: datetime.datetime | None = None
    for user_id, text, sent_at in messages:
        same_author = user_id is not None and user_id == previous_user_id
        close_in_time = (
            previous_sent_at is not None
            and sent_at - previous_sent_at <= datetime.timedelta(seconds=30)
        )
        if grouped and same_author and close_in_time:
            grouped[-1] = f"{grouped[-1]} {text}"
        else:
            grouped.append(text)
        previous_user_id = user_id
        previous_sent_at = sent_at
    return grouped


async def get_due_reminders(
    session: AsyncSession,
    *,
    now: datetime.datetime,
) -> list[tuple[int, int, str]]:
    query = (
        select(Chat.telegram_id, ChatActivity.chat_id, ChatSettings.reminder_text)
        .join(ChatActivity, ChatActivity.chat_id == Chat.id)
        .join(ChatSettings, ChatSettings.chat_id == Chat.id)
        .where(
            Chat.is_active.is_(True),
            ChatSettings.silence_enabled.is_(True),
            ChatActivity.last_message_at.is_not(None),
            ChatActivity.last_message_at
            <= now
            - func.make_interval(
                0, 0, 0, 0, 0, ChatSettings.silence_threshold_minutes, 0
            ),
            (
                ChatActivity.last_reminder_at.is_(None)
                | (
                    ChatActivity.last_reminder_at
                    <= now
                    - func.make_interval(
                        0, 0, 0, 0, 0, ChatSettings.reminder_cooldown_minutes, 0
                    )
                )
            ),
        )
    )
    rows = (await session.execute(query)).all()
    return [
        (int(chat_id), int(activity_id), text)
        for chat_id, activity_id, text in rows
    ]


async def mark_reminder_sent(
    session: AsyncSession,
    *,
    chat_id: int,
    sent_at: datetime.datetime,
) -> None:
    activity = await session.get(ChatActivity, chat_id)
    if activity is not None:
        activity.last_reminder_at = sent_at


async def get_chat_statistics(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
    since: datetime.datetime,
) -> tuple[int, int]:
    query = (
        select(
            func.count(Message.id),
            func.coalesce(func.sum(func.length(Message.message_text)), 0),
        )
        .join(Chat)
        .where(
            Chat.telegram_id == chat_telegram_id,
            Message.sent_at >= since,
        )
    )
    count, characters = (await session.execute(query)).one()
    return int(count), int(characters)


async def get_activity_insights(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
    since: datetime.datetime,
) -> tuple[int, float, int | None]:
    summary_query = (
        select(
            func.count(func.distinct(Message.user_id)),
            func.coalesce(
                func.avg(func.length(Message.message_text)),
                0,
            ),
        )
        .join(Chat)
        .where(
            Chat.telegram_id == chat_telegram_id,
            Message.sent_at >= since,
            Message.user_id.is_not(None),
        )
    )
    active_users, average_characters = (
        await session.execute(summary_query)
    ).one()

    peak_query = (
        select(
            func.extract("hour", Message.sent_at).label("hour"),
            func.count(Message.id).label("message_count"),
        )
        .join(Chat)
        .where(
            Chat.telegram_id == chat_telegram_id,
            Message.sent_at >= since,
        )
        .group_by("hour")
        .order_by(func.count(Message.id).desc(), "hour")
        .limit(1)
    )
    peak = (await session.execute(peak_query)).first()
    return (
        int(active_users or 0),
        float(average_characters or 0),
        int(peak.hour) if peak else None,
    )


def extract_emojis(value: str) -> list[str]:
    return re.findall(
        r"[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF]",
        value,
    )


async def get_rich_statistics(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
    since: datetime.datetime,
) -> tuple[dict[str, int], int, int, str | None, int]:
    query = (
        select(Message.content_type, func.count(Message.id), func.sum(Message.emoji_count))
        .join(Chat)
        .where(Chat.telegram_id == chat_telegram_id, Message.sent_at >= since)
        .group_by(Message.content_type)
    )
    counts: dict[str, int] = {}
    total_emojis = 0
    total_reactions = int(
        await session.scalar(
            select(func.coalesce(func.sum(Message.reaction_count), 0))
            .join(Chat)
            .where(Chat.telegram_id == chat_telegram_id, Message.sent_at >= since)
        )
        or 0
    )
    for content_type, count, emoji_count in (await session.execute(query)).all():
        counts[content_type] = int(count)
        total_emojis += int(emoji_count or 0)

    texts = await session.scalars(
        select(Message.message_text)
        .join(Chat)
        .where(
            Chat.telegram_id == chat_telegram_id,
            Message.sent_at >= since,
            Message.message_text.is_not(None),
        )
    )
    emoji_counter = Counter(
        emoji
        for text_value in texts
        if text_value
        for emoji in extract_emojis(text_value)
    )
    most_common = emoji_counter.most_common(1)
    return (
        counts,
        total_emojis,
        total_reactions,
        most_common[0][0] if most_common else None,
        most_common[0][1] if most_common else 0,
    )


async def get_user_statistics(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
    since: datetime.datetime,
) -> list[
    tuple[
        int | None,
        str | None,
        str | None,
        str | None,
        int,
        int,
        dict[str, int],
        int,
        int,
        str | None,
        int,
    ]
]:
    query = (
        select(
            User.id,
            User.username,
            User.first_name,
            User.last_name,
            func.count(Message.id),
            func.coalesce(func.sum(func.length(Message.message_text)), 0),
            Message.content_type,
            func.coalesce(func.sum(Message.emoji_count), 0),
            func.coalesce(func.sum(Message.reaction_count), 0),
        )
        .join(Chat)
        .outerjoin(User, Message.user_id == User.id)
        .where(
            Chat.telegram_id == chat_telegram_id,
            Message.sent_at >= since,
        )
        .group_by(
            User.id,
            User.username,
            User.first_name,
            User.last_name,
            Message.content_type,
        )
        .order_by(func.count(Message.id).desc())
    )
    rows = (await session.execute(query)).all()
    aggregate: dict[int | None, list[object]] = {}
    for (
        user_id,
        username,
        first_name,
        last_name,
        message_count,
        character_count,
        content_type,
        emoji_count,
        reaction_count,
    ) in rows:
        if user_id not in aggregate:
            aggregate[user_id] = [
                user_id,
                username,
                first_name,
                last_name,
                0,
                0,
                {},
                0,
                0,
            ]
        item = aggregate[user_id]
        item[4] += int(message_count)
        item[5] += int(character_count)
        item[6][content_type] = int(item[6].get(content_type, 0)) + int(message_count)
        item[7] += int(emoji_count)
        item[8] += int(reaction_count)

    emoji_query = (
        select(Message.user_id, Message.message_text)
        .join(Chat)
        .where(
            Chat.telegram_id == chat_telegram_id,
            Message.sent_at >= since,
            Message.message_text.is_not(None),
        )
    )
    emoji_counters: dict[int | None, Counter[str]] = {}
    for user_id, text_value in (await session.execute(emoji_query)).all():
        counter = emoji_counters.setdefault(user_id, Counter())
        counter.update(extract_emojis(text_value))

    result = []
    for item in aggregate.values():
        common = emoji_counters.get(item[0], Counter()).most_common(1)
        result.append(
            (
                item[0],
                item[1],
                item[2],
                item[3],
                item[4],
                item[5],
                item[6],
                item[7],
                item[8],
                common[0][0] if common else None,
                common[0][1] if common else 0,
            )
        )
    return sorted(result, key=lambda item: item[4], reverse=True)


async def get_most_frequent_word(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
    since: datetime.datetime,
) -> tuple[str, int] | None:
    rows = await session.scalars(
        select(Message.message_text)
        .join(Chat)
        .where(
            Chat.telegram_id == chat_telegram_id,
            Message.sent_at >= since,
            Message.message_text.is_not(None),
        )
    )
    stop_words = {
        "а", "без", "бы", "быть", "в", "во", "вот", "вы", "да", "для",
        "до", "же", "за", "и", "из", "или", "к", "как", "ко", "ли", "мы",
        "на", "над", "не", "ни", "но", "ну", "о", "об", "от", "по", "под",
        "при", "про", "с", "со", "так", "то", "у", "уж", "хоть", "что",
        "чтобы", "э", "это", "я", "он", "она", "они", "оно", "его", "ее",
        "их", "мне", "моя", "мой", "ты", "тебе", "тут", "там", "очень",
        "если", "когда", "тогда", "потому", "поэтому", "также", "тоже",
        "либо", "зато", "однако", "хотя", "чем", "чтобы", "пока",
    }
    words = Counter(
        word.casefold()
        for text in rows
        for word in re.findall(r"[^\W\d_]{5,}", text, flags=re.UNICODE)
        if word.casefold() not in stop_words
    )
    return words.most_common(1)[0] if words else None


async def add_quote(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
    telegram_message_id: int,
) -> tuple[bool, str]:
    source = await session.scalar(
        select(Message)
        .join(Chat)
        .where(
            Chat.telegram_id == chat_telegram_id,
            Message.telegram_message_id == telegram_message_id,
        )
    )
    if source is None:
        return False, "Исходное сообщение ещё не сохранено в базе."
    existing = await session.scalar(
        select(Quote.id).where(Quote.message_id == source.id)
    )
    if existing is not None:
        return False, "Это сообщение уже добавлено в цитаты."
    session.add(Quote(chat_id=source.chat_id, message_id=source.id))
    return True, "Цитата добавлена."


async def delete_quote_by_number(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
    number: int,
) -> bool:
    quote = await session.scalar(
        select(Quote)
        .join(Chat, Chat.id == Quote.chat_id)
        .where(Chat.telegram_id == chat_telegram_id)
        .order_by(Quote.created_at.desc())
        .offset(number - 1)
        .limit(1)
    )
    if quote is None:
        return False
    await session.delete(quote)
    return True


async def get_quotes(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
    search: str | None = None,
    since: datetime.datetime | None = None,
    until: datetime.datetime | None = None,
) -> list[tuple[str | None, str | None, str | None, str, datetime.datetime]]:
    query = (
        select(
            User.username,
            User.first_name,
            User.last_name,
            Message.message_text,
            Message.sent_at,
        )
        .join(Quote, Quote.message_id == Message.id)
        .join(Chat, Chat.id == Quote.chat_id)
        .outerjoin(User, User.id == Message.user_id)
        .where(Chat.telegram_id == chat_telegram_id)
        .order_by(Quote.created_at.desc())
    )
    if search:
        query = query.where(Message.message_text.ilike(f"%{search}%"))
    if since:
        query = query.where(Message.sent_at >= since)
    if until:
        query = query.where(Message.sent_at < until)
    rows = (await session.execute(query)).all()
    return [
        (username, first_name, last_name, text, sent_at)
        for username, first_name, last_name, text, sent_at in rows
        if text
    ]


async def get_random_quote(
    session: AsyncSession,
    *,
    chat_telegram_id: int,
    since: datetime.datetime | None = None,
) -> tuple[str | None, str | None, str | None, str, datetime.datetime] | None:
    query = (
        select(
            User.username,
            User.first_name,
            User.last_name,
            Message.message_text,
            Message.sent_at,
        )
        .join(Quote, Quote.message_id == Message.id)
        .join(Chat, Chat.id == Quote.chat_id)
        .outerjoin(User, User.id == Message.user_id)
        .where(Chat.telegram_id == chat_telegram_id)
    )
    if since:
        query = query.where(Message.sent_at >= since)
    row = (await session.execute(query.order_by(func.random()).limit(1))).first()
    return row if row and row[3] else None
