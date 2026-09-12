from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def statistics_keyboard(
    period: str,
    detailed: bool = False,
    charts: bool = False,
) -> InlineKeyboardMarkup:
    labels = {"day": "День", "week": "Неделя", "month": "Месяц"}
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=(
                        f"• {labels[period]} •"
                        if period == selected_period
                        else labels[selected_period]
                    ),
                    callback_data=(
                        f"stats:{selected_period}:{1 if detailed else 0}:"
                        f"{1 if charts else 0}"
                    ),
                )
                for selected_period in ("day", "week", "month")
            ],
            [
                InlineKeyboardButton(
                    text="📋 Скрыть подробности"
                    if detailed
                    else "📋 Подробная информация",
                    callback_data=(
                        f"stats:{period}:{0 if detailed else 1}:"
                        f"{1 if charts else 0}"
                    ),
                ),
                InlineKeyboardButton(
                    text="📈 Скрыть графики" if charts else "📈 Графики",
                    callback_data=(
                        f"stats:{period}:{1 if detailed else 0}:"
                        f"{0 if charts else 1}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="↩️ В главное меню",
                    callback_data="menu:back",
                )
            ],
        ]
    )
