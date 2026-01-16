"""
Inline keyboards for the bot.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_team_member_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for asking if user is team member."""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data="team_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="team_no"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_choices_keyboard(choices: str) -> InlineKeyboardMarkup:
    """Create inline keyboard from comma-separated choices."""
    choices_list = [c.strip() for c in choices.split(',')]
    
    buttons = []
    for choice in choices_list:
        buttons.append([
            InlineKeyboardButton(text=choice, callback_data=f"choice_{choice}")
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
