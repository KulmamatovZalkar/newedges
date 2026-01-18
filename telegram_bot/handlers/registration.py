"""
Registration flow handler.
Handles the step-by-step registration process.
"""
import os
import logging
from pathlib import Path
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states.registration import RegistrationStates
from database import (
    get_user, update_user, get_questions, get_question_by_id,
    get_first_question, get_next_question, save_response,
    set_current_question, get_or_create_application, update_application,
    complete_application
)
from keyboards.inline import get_choices_keyboard

router = Router()
logger = logging.getLogger(__name__)

# Info messages
MISSION_MESSAGE = """
<b>Отлично! Давай мы немножко расскажем о себе, а ты — о себе.</b>

Мы – команда увлеченных людей. Будем вместе создавать новое, экспериментировать и творить, развивая себя.

<b>Наша Миссия</b>
Мы помогаем людям раскрывать новые грани себя и своей жизни через метафизические и психоэзотерические инструменты. Наша миссия — давать глубокое знание, которое позволяет понимать свои внутренние процессы, улучшать ментальное и энергетическое состояние и становиться авторами собственной жизни.
"""

VALUES_MESSAGE = """
<b>А теперь о наших ценностях:</b>

✨ <b>Осознанность</b> — понимание себя, своих состояний и причин происходящего.

💎 <b>Честность с собой</b> — способность встречаться с истинными мотивами, страхами и желаниями.

🔮 <b>Целостность</b> — внимание ко всем аспектам человека: ментальному, энергетическому, эмоциональному и физическому.

💪 <b>Ответственность</b> — способность быть автором своей жизни и действий.

📈 <b>Развитие</b> — постоянный рост, исследование, обучение, поиски новых смыслов и готовность двигаться к новому.

💚 <b>Забота</b> — уважение к пути каждого человека, поддержка, экологичность. Комьюнити.

🌊 <b>Глубина</b> — ориентация на внутренние трансформации, а не поверхностные изменения.

⚡ <b>Скорость и Безопасность</b> — создание и использование инструментов, которые позволяют быстро получить результат.

🎯 <b>Доступность</b> — по деньгам, пониманию материала и подаче информации.
"""

GOAL_MESSAGE = """
<b>Наша цель</b>

Научить применять психологические и энергетические инструменты для улучшения жизни и достижения новых результатов, через исследование и исцеление своих граней.
"""

COMPLETION_MESSAGE = """
🎉 <b>Спасибо, что рассказал о себе!</b>

Рады, что ты с нами!!! 💜

Твои данные успешно сохранены. Если будут вопросы — пиши администратору.
"""


@router.callback_query(RegistrationStates.asking_team_member, F.data.in_(["team_yes", "team_no"]))
async def process_team_member(callback: CallbackQuery, state: FSMContext):
    """Process team member answer."""
    await callback.answer()
    
    is_team_member = callback.data == "team_yes"
    
    # Update user
    update_user(callback.from_user.id, is_team_member=is_team_member)
    
    if is_team_member:
        # Ask about position
        await callback.message.edit_text(
            "На какой позиции ты работаешь в школе <b>«Новые грани»</b>?"
        )
        await state.set_state(RegistrationStates.asking_position)
    else:
        await callback.message.edit_text(
            "Спасибо за интерес! Этот бот предназначен для членов команды. "
            "Если хочешь присоединиться к нам, напиши /start когда будешь готов."
        )
        await state.clear()


@router.message(RegistrationStates.asking_position)
async def process_position(message: Message, state: FSMContext):
    """Process position answer and start registration."""
    position = message.text
    
    # Get user and create application
    user = get_user(message.from_user.id)
    if user:
        app = get_or_create_application(user['id'])
        update_application(user['id'], position=position)
    
    # Save position to state
    await state.update_data(position=position)
    
    # Send mission message
    await message.answer(MISSION_MESSAGE)
    
    # Get first question from database
    first_question = get_first_question()
    
    if first_question:
        # Set current question for user
        set_current_question(message.from_user.id, first_question['id'])
        
        # Save state data
        await state.update_data(
            current_question_id=first_question['id'],
            current_question_order=first_question['order']
        )
        
        # Send first question
        await send_question(message, first_question)
        await state.set_state(RegistrationStates.answering_questions)
    else:
        await message.answer("Вопросов пока нет. Обратитесь к администратору.")
        await state.clear()


def save_to_application(user_id: int, field_name: str, value: str, is_photo: bool = False):
    """Save answer to StaffApplication based on field_name."""
    if not field_name:
        return
    
    # Map field_name to application field
    valid_fields = [
        'full_name', 'address', 'phone', 'email',
        'passport_main', 'passport_registration', 'snils', 'inn',
        'marital_status', 'children', 'emergency_contact', 'additional_info'
    ]
    
    if field_name in valid_fields:
        update_application(user_id, **{field_name: value})
        logger.info(f"Saved to application: {field_name} = {value[:30] if isinstance(value, str) else value}...")


@router.message(RegistrationStates.answering_questions, F.photo)
async def process_photo_answer(message: Message, state: FSMContext, bot: Bot):
    """Process photo answer."""
    state_data = await state.get_data()
    question_id = state_data.get('current_question_id')
    
    if not question_id:
        await message.answer("Произошла ошибка. Попробуйте начать сначала: /start")
        await state.clear()
        return
    
    question = get_question_by_id(question_id)
    if not question:
        await message.answer("Вопрос не найден. Попробуйте /start")
        await state.clear()
        return
    
    # Get user ID from database
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Пользователь не найден. Попробуйте /start")
        await state.clear()
        return
    
    # Download and save photo
    photo = message.photo[-1]  # Get highest resolution
    file = await bot.get_file(photo.file_id)
    
    # Create save path based on field_name
    field_name = question.get('field_name', 'unknown')
    save_dir = Path(f"/app/media/applications/{field_name}")
    save_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{message.from_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    save_path = save_dir / filename
    
    await bot.download_file(file.file_path, save_path)
    
    # Save relative path
    relative_path = f"applications/{field_name}/{filename}"
    
    # Save to old UserResponse for backwards compatibility
    save_response(user['id'], question_id, photo_path=relative_path)
    
    # Save to StaffApplication
    save_to_application(user['id'], field_name, relative_path, is_photo=True)
    
    logger.info(f"User {message.from_user.id} uploaded photo for {field_name}")
    
    # Move to next question
    await move_to_next_question(message, state, question)


@router.message(RegistrationStates.answering_questions, F.text)
async def process_text_answer(message: Message, state: FSMContext):
    """Process text answer."""
    state_data = await state.get_data()
    question_id = state_data.get('current_question_id')
    
    if not question_id:
        await message.answer("Произошла ошибка. Попробуйте начать сначала: /start")
        await state.clear()
        return
    
    question = get_question_by_id(question_id)
    if not question:
        await message.answer("Вопрос не найден. Попробуйте /start")
        await state.clear()
        return
    
    # Check if question requires photo
    if question.get('question_type') == 'photo':
        await message.answer("📷 Пожалуйста, отправьте фото, а не текст.")
        return
    
    # Get user ID from database
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Пользователь не найден. Попробуйте /start")
        await state.clear()
        return
    
    field_name = question.get('field_name')
    
    # Save to old UserResponse for backwards compatibility
    save_response(user['id'], question_id, text_answer=message.text)
    
    # Save to StaffApplication
    save_to_application(user['id'], field_name, message.text)
    
    logger.info(f"User {message.from_user.id} answered {field_name}: {message.text[:50]}...")
    
    # Move to next question
    await move_to_next_question(message, state, question)


@router.callback_query(RegistrationStates.answering_questions)
async def process_choice_answer(callback: CallbackQuery, state: FSMContext):
    """Process choice answer from inline keyboard."""
    await callback.answer()
    
    state_data = await state.get_data()
    question_id = state_data.get('current_question_id')
    
    question = get_question_by_id(question_id)
    if not question:
        await callback.message.edit_text("Вопрос не найден. Попробуйте /start")
        await state.clear()
        return
    
    # Get user ID from database
    user = get_user(callback.from_user.id)
    if not user:
        await callback.message.edit_text("Пользователь не найден. Попробуйте /start")
        await state.clear()
        return
    
    # Get answer from callback data
    answer = callback.data.replace("choice_", "")
    field_name = question.get('field_name')
    
    # Save to old UserResponse
    save_response(user['id'], question_id, text_answer=answer)
    
    # Save to StaffApplication
    save_to_application(user['id'], field_name, answer)
    
    logger.info(f"User {callback.from_user.id} chose {answer} for {field_name}")
    
    # Remove keyboard and update message
    await callback.message.edit_reply_markup(reply_markup=None)
    
    # Move to next question
    await move_to_next_question(callback.message, state, question, from_user_id=callback.from_user.id)


async def move_to_next_question(message: Message, state: FSMContext, current_question: dict, from_user_id: int = None):
    """Move to the next question or complete registration."""
    user_id = from_user_id or message.from_user.id
    current_order = current_question['order']
    
    # Get next question
    next_question = get_next_question(current_order)
    
    if next_question:
        # Check if we need to show info messages at certain points
        # After question about FIO, show goal message
        if current_question.get('field_name') == 'full_name':
            await message.answer(GOAL_MESSAGE)
        
        # Before SNILS question, show values message
        if next_question.get('field_name') == 'snils':
            await message.answer(VALUES_MESSAGE)
        
        # Update current question
        set_current_question(user_id, next_question['id'])
        
        await state.update_data(
            current_question_id=next_question['id'],
            current_question_order=next_question['order']
        )
        
        # Send next question
        await send_question(message, next_question)
    else:
        # Registration complete
        update_user(user_id, is_registration_complete=True, current_question_id=None)
        
        # Mark application as completed
        user = get_user(user_id)
        if user:
            complete_application(user['id'])
        
        await message.answer(COMPLETION_MESSAGE)
        await state.clear()
        
        logger.info(f"User {user_id} completed registration")


async def send_question(message: Message, question: dict):
    """Send a question to the user."""
    question_text = question['text']
    question_type = question['question_type']
    
    # Check if question has image
    if question.get('image'):
        image_path = f"/app/media/{question['image']}"
        if os.path.exists(image_path):
            from aiogram.types import FSInputFile
            photo = FSInputFile(image_path)
            if question_type == 'choice' and question.get('choices'):
                keyboard = get_choices_keyboard(question['choices'])
                await message.answer_photo(photo, caption=question_text, reply_markup=keyboard)
            else:
                await message.answer_photo(photo, caption=question_text)
            return
    
    # Send based on question type
    if question_type == 'choice' and question.get('choices'):
        keyboard = get_choices_keyboard(question['choices'])
        await message.answer(question_text, reply_markup=keyboard)
    elif question_type == 'info':
        # Info message, just display and move to next
        await message.answer(question_text)
    else:
        await message.answer(question_text)
