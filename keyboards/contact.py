from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_contact_keyboard(btn_text: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=btn_text, request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
