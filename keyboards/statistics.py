from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def statistics_keyboard(period: str) -> InlineKeyboardMarkup:
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
                    callback_data=f"stats:{selected_period}",
                )
                for selected_period in ("day", "week", "month")
            ],
            [
                InlineKeyboardButton(
                    text="↩️ В главное меню",
                    callback_data="menu:back",
                )
            ],
        ]
    )
