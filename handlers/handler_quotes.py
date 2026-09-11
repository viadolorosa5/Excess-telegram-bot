import html
import datetime

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.repository import add_quote, delete_quote_by_number, get_quotes
from handlers.shared import reject_if_not_admin, reject_private_chat


router = Router()


def quote_author(
    username: str | None,
    first_name: str | None,
    last_name: str | None,
) -> str:
    if username:
        return f"@{username}"
    return " ".join(part for part in (first_name, last_name) if part) or "Неизвестный пользователь"


async def send_quote_chunks(message: Message, lines: list[str]) -> None:
    chunk = ""
    for line in lines:
        if chunk and len(chunk) + len(line) + 2 > 3900:
            await message.answer(chunk, parse_mode="HTML")
            chunk = ""
        chunk = f"{chunk}\n\n{line}".strip()
    if chunk:
        await message.answer(chunk, parse_mode="HTML")


@router.message(Command("quote"))
async def handle_add_quote(
    message: Message,
    session_factory: async_sessionmaker,
) -> None:
    if await reject_private_chat(message):
        return
    source = message.reply_to_message
    if source is None or not source.text:
        await message.answer(
            "Ответьте командой <code>/quote</code> на текстовое сообщение.",
            parse_mode="HTML",
        )
        return

    async with session_factory() as session:
        added, response = await add_quote(
            session,
            chat_telegram_id=message.chat.id,
            telegram_message_id=source.message_id,
        )
        if added:
            await session.commit()
        else:
            await session.rollback()
    await message.answer(f"✅ {response}" if added else f"ℹ️ {response}")


@router.message(Command("quotes"))
async def handle_quotes(
    message: Message,
    command: CommandObject,
    session_factory: async_sessionmaker,
) -> None:
    if await reject_private_chat(message):
        return
    search, since, until, error = parse_quote_filters(command.args)
    if error:
        await message.answer(error)
        return
    async with session_factory() as session:
        quotes = await get_quotes(
            session,
            chat_telegram_id=message.chat.id,
            search=search,
            since=since,
            until=until,
        )

    if not quotes:
        await message.answer("📌 Цитаты по заданным фильтрам не найдены.")
        return

    lines = ["📌 <b>Цитаты чата</b>\n"]
    for index, (username, first_name, last_name, text, sent_at) in enumerate(
        quotes, start=1
    ):
        author = html.escape(quote_author(username, first_name, last_name))
        timestamp = sent_at.strftime("%d.%m.%Y %H:%M")
        excerpt = html.escape(text)
        lines.append(
            f"<b>{index}.</b> «{excerpt}»\n"
            f"— {author}, <i>{timestamp}</i>"
        )
    await send_quote_chunks(message, lines)


@router.message(Command("quote_delete"))
async def handle_delete_quote(
    message: Message,
    command: CommandObject,
    bot: Bot,
    session_factory: async_sessionmaker,
) -> None:
    if await reject_private_chat(message):
        return
    if await reject_if_not_admin(bot, message):
        return

    argument = (command.args or "").strip()
    if not argument.isdigit() or int(argument) < 1:
        await message.answer(
            "Формат: <code>/quote_delete номер</code>\n"
            "Номер берётся из списка команды /quotes.",
            parse_mode="HTML",
        )
        return

    number = int(argument)
    async with session_factory() as session:
        deleted = await delete_quote_by_number(
            session,
            chat_telegram_id=message.chat.id,
            number=number,
        )
        if deleted:
            await session.commit()
        else:
            await session.rollback()

    if deleted:
        await message.answer(f"✅ Цитата №{number} удалена.")
    else:
        await message.answer(f"Цитата №{number} не найдена.")


def parse_quote_filters(
    args: str | None,
) -> tuple[str | None, datetime.datetime | None, datetime.datetime | None, str | None]:
    parts = (args or "").split()
    search = None
    dates: list[datetime.date] = []
    for part in parts:
        try:
            dates.append(datetime.date.fromisoformat(part))
        except ValueError:
            try:
                dates.append(datetime.datetime.strptime(part, "%d.%m.%Y").date())
            except ValueError:
                if search is not None:
                    return None, None, None, (
                        "Формат: <code>/quotes [слово] "
                        "[ГГГГ-ММ-ДД] [ГГГГ-ММ-ДД]</code>"
                    )
                search = part
    if len(dates) > 2 or (len(dates) == 2 and dates[0] > dates[1]):
        return None, None, None, "Проверьте даты фильтра."
    since = (
        datetime.datetime.combine(dates[0], datetime.time.min, tzinfo=datetime.UTC)
        if dates else None
    )
    until = (
        datetime.datetime.combine(
            dates[-1] + datetime.timedelta(days=1),
            datetime.time.min,
            tzinfo=datetime.UTC,
        )
        if dates else None
    )
    if len(dates) == 2:
        until = datetime.datetime.combine(
            dates[1] + datetime.timedelta(days=1),
            datetime.time.min,
            tzinfo=datetime.UTC,
        )
    return search, since, until, None
