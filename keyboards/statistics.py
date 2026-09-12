from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def statistics_keyboard(period: str, detailed: bool = False) -> InlineKeyboardMarkup:
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
                        f"stats:{selected_period}:{1 if detailed else 0}"
                    ),
                )
                for selected_period in ("day", "week", "month")
            ],
            [
                InlineKeyboardButton(
                    text="📋 Скрыть подробности"
                    if detailed
                    else "📋 Подробная информация",
                    callback_data=f"stats:{period}:{0 if detailed else 1}",
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
