from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_subscription_keyboard(
    channel_link_text: str,
    channel_url: str,
    check_text: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=channel_link_text, url=channel_url)],
        [InlineKeyboardButton(text=check_text, callback_data="check_sub")],
    ])
