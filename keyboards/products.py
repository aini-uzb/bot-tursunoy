from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import COURSES


def get_category_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Top-level 3 buttons: Канал | Курс | Консульт."""
    if lang == "ru":
        btn_channel = "🔒 Закрытый канал"
        btn_course = "🚀 Курсы"
        btn_consult = "🎯 Консультация"
    else:
        btn_channel = "🔒 Yopiq kanal"
        btn_course = "🚀 Kurslar"
        btn_consult = "🎯 Konsultatsiya"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_channel, callback_data="cat_channel")],
        [InlineKeyboardButton(text=btn_course, callback_data="cat_course")],
        [InlineKeyboardButton(text=btn_consult, callback_data="cat_consult")],
    ])


def get_courses_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """List of 5 courses + back to categories."""
    name_key = "name_ru" if lang == "ru" else "name_uz"
    back_text = "◀️ Назад" if lang == "ru" else "◀️ Orqaga"
    rows = []
    for key, course in COURSES.items():
        rows.append([InlineKeyboardButton(
            text=course[name_key],
            callback_data=f"course_{key}",
        )])
    rows.append([InlineKeyboardButton(text=back_text, callback_data="back_to_cats")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_course_detail_keyboard(course_key: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Course detail: Pay + Back to courses list."""
    pay_text = "💳 Оплатить" if lang == "ru" else "💳 To'lash"
    back_text = "◀️ Назад" if lang == "ru" else "◀️ Orqaga"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=pay_text, callback_data=f"pay_{course_key}")],
        [InlineKeyboardButton(text=back_text, callback_data="back_to_courses")],
    ])


def get_channel_detail_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Channel subscription detail: Pay + Back to categories."""
    pay_text = "💳 Оплатить" if lang == "ru" else "💳 To'lash"
    back_text = "◀️ Назад" if lang == "ru" else "◀️ Orqaga"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=pay_text, callback_data="pay_channel_sub")],
        [InlineKeyboardButton(text=back_text, callback_data="back_to_cats")],
    ])


def get_click_payment_keyboard(pay_url: str, back_callback: str, lang: str = "ru") -> InlineKeyboardMarkup:
    pay_text = "💳 Оплатить через Click" if lang == "ru" else "💳 Click orqali to'lash"
    back_text = "◀️ Назад" if lang == "ru" else "◀️ Orqaga"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=pay_text, url=pay_url)],
        [InlineKeyboardButton(text=back_text, callback_data=back_callback)],
    ])


def get_consult_keyboard(btn_text: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, callback_data="consult_request")]
    ])


def get_admin_payment_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_{payment_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline_{payment_id}"),
        ]
    ])
