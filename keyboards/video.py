from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_video_keyboard(btn_text: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, callback_data="video_watched")]
    ])
