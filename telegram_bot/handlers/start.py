"""
Start command handler.
Handles the /start command and initial greeting.
"""
import os
import logging
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from states.registration import RegistrationStates
from database import get_or_create_user, get_user
from keyboards.inline import get_team_member_keyboard

router = Router()
logger = logging.getLogger(__name__)

# Welcome message
WELCOME_MESSAGE = """
<b>Привет, дорогой друг!</b> 👋

Тебя приветствует бот школы <b>«Новые грани»</b>.

Обычно в этот бот случайно не попадают. Если ты хочешь стать частью команды или уже являешься ей, пиши /start и поехали!
"""


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command."""
    # Clear any previous state
    await state.clear()
    
    # Get or create user
    user_data = get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    logger.info(f"User {message.from_user.id} started the bot")
    
    # Check if user already completed registration
    if user_data.get('is_registration_complete'):
        await message.answer(
            "🎉 <b>С возвращением!</b>\n\n"
            "Ты уже завершил регистрацию. Если хочешь обновить данные, свяжись с администратором."
        )
        return
    
    # Try to send welcome image if exists
    image_path = "/app/media/welcome.jpg"
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        await message.answer_photo(photo, caption=WELCOME_MESSAGE)
    else:
        await message.answer(WELCOME_MESSAGE)
    
    # Ask if user is team member
    await message.answer(
        "Ты уже являешься частью команды <b>«Новые грани»</b>?",
        reply_markup=get_team_member_keyboard()
    )
    
    await state.set_state(RegistrationStates.asking_team_member)
