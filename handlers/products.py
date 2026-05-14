import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from config import COURSES, CHANNEL_SUBSCRIPTION
from db import update_user, get_user
from keyboards.products import (
    get_category_keyboard, get_courses_keyboard, get_course_detail_keyboard,
    get_channel_detail_keyboard, get_click_payment_keyboard,
)
from states import ConsultState
from utils import notify_admins
from services.crm import create_lead
from services.click import generate_payment_url
import app_state

router = Router()
logger = logging.getLogger(__name__)


# ─── Navigation ────────────────────────────────────────────────

@router.callback_query(F.data == "back_to_cats")
async def back_to_categories(callback: CallbackQuery, texts):
    user = await get_user(callback.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await callback.message.edit_text(
        texts.PRODUCTS_INTRO,
        reply_markup=get_category_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_courses")
async def back_to_courses(callback: CallbackQuery, texts):
    user = await get_user(callback.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    name_key = "name_ru" if lang == "ru" else "name_uz"
    brief_key = "brief_ru" if lang == "ru" else "brief_uz"
    header = "🚀 <b>Курсы</b>\n\n" if lang == "ru" else "🚀 <b>Kurslar</b>\n\n"
    lines = [header]
    for course in COURSES.values():
        lines.append(f"<b>{course[name_key]}</b>\n{course.get(brief_key, '')}\n")
    footer = "\nНажмите на курс для подробностей 👇" if lang == "ru" else "\nBatafsil ma'lumot uchun kursni bosing 👇"
    lines.append(footer)
    await callback.message.edit_text(
        "".join(lines),
        reply_markup=get_courses_keyboard(lang),
    )
    await callback.answer()


# ─── Category: Channel ─────────────────────────────────────────

@router.callback_query(F.data == "cat_channel")
async def show_channel(callback: CallbackQuery, texts):
    user = await get_user(callback.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    desc = CHANNEL_SUBSCRIPTION["desc_ru"] if lang == "ru" else CHANNEL_SUBSCRIPTION["desc_uz"]
    await callback.message.edit_text(
        desc,
        reply_markup=get_channel_detail_keyboard(lang),
    )
    await callback.answer()


# ─── Category: Courses ─────────────────────────────────────────

@router.callback_query(F.data == "cat_course")
async def show_courses(callback: CallbackQuery, texts):
    user = await get_user(callback.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    name_key = "name_ru" if lang == "ru" else "name_uz"
    brief_key = "brief_ru" if lang == "ru" else "brief_uz"
    header = "🚀 <b>Курсы</b>\n\n" if lang == "ru" else "🚀 <b>Kurslar</b>\n\n"
    lines = [header]
    for course in COURSES.values():
        lines.append(f"<b>{course[name_key]}</b>\n{course.get(brief_key, '')}\n")
    footer = "\nНажмите на курс для подробностей 👇" if lang == "ru" else "\nBatafsil ma'lumot uchun kursni bosing 👇"
    lines.append(footer)
    await callback.message.edit_text(
        "".join(lines),
        reply_markup=get_courses_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("course_"))
async def show_course_detail(callback: CallbackQuery, texts):
    course_key = callback.data.removeprefix("course_")
    course = COURSES.get(course_key)
    if not course:
        await callback.answer()
        return

    user = await get_user(callback.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await update_user(callback.from_user.id, product_chosen=course_key)

    desc = course["desc_ru"] if lang == "ru" else course["desc_uz"]
    await callback.message.edit_text(
        desc,
        reply_markup=get_course_detail_keyboard(course_key, lang),
    )
    await callback.answer()


# ─── Category: Consultation ────────────────────────────────────

@router.callback_query(F.data.in_({"cat_consult", "consult_request"}))
async def start_consult(callback: CallbackQuery, state: FSMContext, texts):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    # Immediately create lead in CRM
    await create_lead({
        "user_id": callback.from_user.id,
        "first_name": user.get("first_name", ""),
        "username": user.get("username", ""),
        "phone": user.get("phone", ""),
        "type": "consult",
    })

    await state.set_state(ConsultState.question_1)
    try:
        await callback.message.delete()
    except Exception:
        await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(texts.CONSULT_Q1)
    await callback.answer()


@router.message(StateFilter(ConsultState.question_1))
async def consult_answer_1(message: Message, state: FSMContext, texts):
    await state.update_data(answer_1=message.text.strip())
    await state.set_state(ConsultState.question_2)
    await message.answer(texts.CONSULT_Q2)


@router.message(StateFilter(ConsultState.question_2))
async def consult_answer_2(message: Message, state: FSMContext, texts):
    data = await state.get_data()
    answer_1 = data.get("answer_1", "—")
    answer_2 = message.text.strip()
    await state.clear()

    user = await get_user(message.from_user.id)
    await message.answer(texts.CONSULT_THANKS)

    # Разбиваем ответ на этап и страну (пользователь пишет две строки)
    parts = answer_2.split("\n", 1)
    stage = parts[0].strip() if parts else answer_2
    country = parts[1].strip() if len(parts) > 1 else "—"

    # Notify admins with full answers
    admin_text = texts.ADMIN_CONSULT_ANSWERS.format(
        first_name=user.get("first_name", "") if user else "",
        username=user.get("username", "") or "нет" if user else "нет",
        phone=user.get("phone", "") if user else "",
        answer_1=answer_1,
        stage=stage,
        country=country,
    )
    await notify_admins(app_state.bot, admin_text)

    # Update CRM with full info
    await create_lead({
        "user_id": message.from_user.id,
        "first_name": user.get("first_name", "") if user else "",
        "username": user.get("username", "") if user else "",
        "phone": user.get("phone", "") if user else "",
        "type": "consult_answers",
        "course": f"Цель: {answer_1} | {answer_2}",
    })
    logger.info(f"Consult answers from {message.from_user.id}")


# ─── Payment via Click ─────────────────────────────────────────

@router.callback_query(F.data == "pay_channel_sub")
async def pay_channel(callback: CallbackQuery, texts):
    user = await get_user(callback.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    amount = CHANNEL_SUBSCRIPTION["price"]
    url = generate_payment_url(callback.from_user.id, "channel_sub", amount)
    pay_text = texts.CLICK_PAY_INFO if hasattr(texts, "CLICK_PAY_INFO") else "💳 Нажмите кнопку ниже для оплаты через Click:"
    await callback.message.edit_text(pay_text, reply_markup=get_click_payment_keyboard(url, "back_to_cats", lang))
    await callback.answer()


@router.callback_query(F.data.startswith("pay_"))
async def pay_course(callback: CallbackQuery, texts):
    course_key = callback.data.removeprefix("pay_")
    course = COURSES.get(course_key)
    if not course:
        await callback.answer()
        return

    user = await get_user(callback.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    amount = course.get("price_uzs", course["price"])
    url = generate_payment_url(callback.from_user.id, course_key, amount)
    pay_text = texts.CLICK_PAY_INFO if hasattr(texts, "CLICK_PAY_INFO") else "💳 Нажмите кнопку ниже для оплаты через Click:"
    await callback.message.edit_text(pay_text, reply_markup=get_click_payment_keyboard(url, "back_to_courses", lang))

    # CRM lead
    if user:
        await create_lead({
            "user_id": callback.from_user.id,
            "first_name": user.get("first_name", ""),
            "username": user.get("username", ""),
            "phone": user.get("phone", ""),
            "type": "payment_initiated",
            "course": course["name_ru"],
            "price": course["price"],
        })
    await callback.answer()
