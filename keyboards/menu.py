from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="menu:stats"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings"),
                InlineKeyboardButton(text="❓ Помощь", callback_data="menu:help"),
            ],
        ]
    )


def features_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="menu:feature:stats",
                ),
                InlineKeyboardButton(
                    text="📚 Библиотека",
                    callback_data="menu:feature:babel",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⏰ Напоминания",
                    callback_data="menu:feature:reminders",
                ),
                InlineKeyboardButton(
                    text="🌀 Глупи",
                    callback_data="menu:feature:glupy",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📌 Цитаты",
                    callback_data="menu:feature:quotes",
                ),
            ],
            [
                InlineKeyboardButton(text="↩️ Назад", callback_data="menu:back"),
            ],
        ]
    )


def feature_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="↩️ К списку помощи",
                    callback_data="menu:features",
                ),
            ],
        ]
    )
