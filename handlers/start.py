from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from keyboards.language import get_language_keyboard
from db import create_or_update_user, update_user

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, texts):
    await state.clear()
    await create_or_update_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
    )
    # Сбрасываем флаг просмотра видео чтобы flow работал заново
    await update_user(message.from_user.id, video_watched=0)
    await message.answer(texts.CHOOSE_LANGUAGE, reply_markup=get_language_keyboard())
