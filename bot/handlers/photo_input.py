"""
Photo input handler - анализ фото еды
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os

from bot.ai.gemini_vision_provider import GeminiVisionProvider
from bot.database.db import get_db
from bot.database.models import User
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = Router()


class PhotoInputState(StatesGroup):
    """Состояния для обработки фото"""
    waiting_for_clarification = State()  # Ожидание ответов на вопросы
    waiting_for_confirmation = State()  # Ожидание подтверждения


@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext):
    """
    Обработка фото еды
    Бот сам понимает что пришло фото и анализирует
    """
    # Получаем пользователя
    async with get_db() as session:
        result = await session.execute(
            select(User).where(User.telegram_user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Сначала нажмите /start")
            return
        
        # Проверяем доступ (white-list)
        if not user.is_allowed and not user.is_owner:
            await message.answer(
                "🔒 У вас нет доступа к боту.\n"
                "Попросите владельца добавить вас: /allow"
            )
            return
    
    # Отправляем статус
    status_msg = await message.answer("🤖 Анализирую фото еды...")
    
    try:
        # Получаем API ключ из переменных окружения
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            await status_msg.edit_text(
                "❌ API ключ Gemini не настроен.\n\n"
                "Чтобы использовать распознавание по фото:\n"
                "1. Получите бесплатный API ключ: https://makersuite.google.com/app/apikey\n"
                "2. Добавьте в .env файл: GEMINI_API_KEY=ваш_ключ\n"
                "3. Перезапустите бота\n\n"
                "⚠️ Внимание: Фото будет отправлено на сервера Google для анализа."
            )
            return
        
        # Создаем провайдер
        vision_provider = GeminiVisionProvider(api_key=api_key)
        
        # Скачиваем фото
        photo = message.photo[-1]  # Самое большое разрешение
        file = await message.bot.get_file(photo.file_id)
        photo_bytes = await message.bot.download_file(file.file_path)
        photo_data = photo_bytes.read()
        
        # Анализируем
        estimate = await vision_provider.analyze_food_photo(photo_data)
        
        if not estimate:
            await status_msg.edit_text(
                "❌ Не удалось распознать еду на фото.\n"
                "Попробуйте:\n"
                "• Сделать фото ближе\n"
                "• Улучшить освещение\n"
                "• Или ввести текстом: Еда: название блюда"
            )
            return
        
        # Формируем ответ
        confidence_emoji = {
            "low": "🟡",
            "medium": "🟢",
            "high": "🟢"
        }
        
        response = f"📸 **Я вижу на фото:**\n\n"
        
        # Список блюд
        for item in estimate.detected_items:
            response += f"• {item}\n"
        
        response += f"\n{estimate.description}\n\n"
        
        # Оценка
        response += f"**Оценка калорий:** ~{estimate.calories:.0f} ккал\n"
        response += f"**БЖУ:** {estimate.protein:.0f}/{estimate.fat:.0f}/{estimate.carbs:.0f}г\n"
        response += f"**Уверенность:** {confidence_emoji.get(estimate.confidence_level, '🟡')} {estimate.confidence_level} ({estimate.confidence*100:.0f}%)\n\n"
        
        # Предположения
        if estimate.assumptions:
            response += "**Я предположил:**\n"
            for assumption in estimate.assumptions:
                response += f"• {assumption}\n"
            response += "\n"
        
        # Сохраняем данные в state
        await state.update_data(
            photo_estimate=estimate,
            clarification_answers={}
        )
        
        # Если есть уточняющие вопросы
        if estimate.clarification_questions:
            response += "**Уточните пожалуйста:**\n"
            
            # Показываем первый вопрос
            first_question = estimate.clarification_questions[0]
            response += f"\n{first_question.question}"
            
            # Создаем кнопки с вариантами
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=option,
                    callback_data=f"clarify_{first_question.field}_{i}"
                )] for i, option in enumerate(first_question.options)
            ])
            
            await state.update_data(
                current_question_index=0,
                total_questions=len(estimate.clarification_questions)
            )
            await state.set_state(PhotoInputState.waiting_for_clarification)
            
            await status_msg.edit_text(response, reply_markup=keyboard, parse_mode="Markdown")
        else:
            # Нет вопросов - сразу подтверждение
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Записать", callback_data="photo_confirm"),
                    InlineKeyboardButton(text="✏️ Изменить", callback_data="photo_edit")
                ],
                [InlineKeyboardButton(text="❌ Отменить", callback_data="photo_cancel")]
            ])
            
            await state.set_state(PhotoInputState.waiting_for_confirmation)
            await status_msg.edit_text(response, reply_markup=keyboard, parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"Ошибка обработки фото: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ Ошибка при анализе фото:\n{str(e)}\n\n"
            "Попробуйте еще раз или введите текстом."
        )


@router.callback_query(F.data.startswith("clarify_"), PhotoInputState.waiting_for_clarification)
async def handle_clarification(callback: CallbackQuery, state: FSMContext):
    """Обработка ответов на уточняющие вопросы"""
    await callback.answer()
    
    # Парсим ответ: clarify_field_index
    parts = callback.data.split("_")
    field = parts[1]
    option_index = int(parts[2])
    
    # Получаем данные
    data = await state.get_data()
    estimate = data['photo_estimate']
    current_q_index = data['current_question_index']
    total_questions = data['total_questions']
    clarification_answers = data.get('clarification_answers', {})
    
    # Сохраняем ответ
    question = estimate.clarification_questions[current_q_index]
    selected_option = question.options[option_index]
    clarification_answers[field] = selected_option
    
    # Следующий вопрос?
    next_q_index = current_q_index + 1
    
    if next_q_index < total_questions:
        # Есть еще вопросы
        next_question = estimate.clarification_questions[next_q_index]
        
        response = f"Отлично! **{field}**: {selected_option}\n\n"
        response += f"**Следующий вопрос ({next_q_index + 1}/{total_questions}):**\n"
        response += next_question.question
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=option,
                callback_data=f"clarify_{next_question.field}_{i}"
            )] for i, option in enumerate(next_question.options)
        ])
        
        await state.update_data(
            current_question_index=next_q_index,
            clarification_answers=clarification_answers
        )
        
        await callback.message.edit_text(response, reply_markup=keyboard, parse_mode="Markdown")
    
    else:
        # Все вопросы заданы - пересчитываем с учетом ответов
        await callback.message.edit_text("🔄 Обновляю оценку с учетом ваших ответов...")
        
        # TODO: Здесь можно переспросить AI с дополнительным контекстом
        # Пока просто показываем финальное подтверждение
        
        response = "**Финальная оценка:**\n\n"
        response += f"📊 Калории: ~{estimate.calories:.0f} ккал\n"
        response += f"БЖУ: {estimate.protein:.0f}/{estimate.fat:.0f}/{estimate.carbs:.0f}г\n\n"
        response += "**Ваши уточнения:**\n"
        for field, answer in clarification_answers.items():
            response += f"• {field}: {answer}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Записать", callback_data="photo_confirm"),
                InlineKeyboardButton(text="✏️ Изменить", callback_data="photo_edit")
            ],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="photo_cancel")]
        ])
        
        await state.set_state(PhotoInputState.waiting_for_confirmation)
        await callback.message.edit_text(response, reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data == "photo_confirm", PhotoInputState.waiting_for_confirmation)
async def confirm_photo_entry(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и запись в БД"""
    await callback.answer()
    
    data = await state.get_data()
    estimate = data['photo_estimate']
    clarification_answers = data.get('clarification_answers', {})
    
    # Получаем пользователя и создаем/обновляем запись
    async with get_db() as session:
        result = await session.execute(
            select(User).where(User.telegram_user_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text("❌ Ошибка: пользователь не найден")
            await state.clear()
            return
        
        # Получаем или создаем запись за сегодня
        from datetime import date
        from bot.database.models import DayEntry
        
        today = date.today()
        result = await session.execute(
            select(DayEntry).where(
                DayEntry.user_id == user.id,
                DayEntry.entry_date == today
            )
        )
        day_entry = result.scalar_one_or_none()
        
        if not day_entry:
            day_entry = DayEntry(
                user_id=user.id,
                entry_date=today
            )
            session.add(day_entry)
        
        # Сохраняем данные из фото
        import json
        day_entry.kcal_eaten = (day_entry.kcal_eaten or 0) + estimate.calories
        day_entry.protein = (day_entry.protein or 0) + estimate.protein
        day_entry.fat = (day_entry.fat or 0) + estimate.fat
        day_entry.carbs = (day_entry.carbs or 0) + estimate.carbs
        
        # Метаданные AI
        day_entry.food_ai_estimated = True
        day_entry.food_ai_model = estimate.model_used
        day_entry.food_ai_confidence = estimate.confidence
        day_entry.food_items_json = json.dumps(estimate.detected_items, ensure_ascii=False)
        
        # Метаданные фото
        day_entry.photo_analyzed = True
        day_entry.photo_description = estimate.description
        day_entry.food_description = ", ".join(estimate.detected_items)
        
        if clarification_answers:
            day_entry.photo_clarifications_json = json.dumps(clarification_answers, ensure_ascii=False)
        
        # Инкрементируем счетчик AI запросов
        user.ai_requests_today += 1
        from datetime import datetime
        user.last_ai_request = datetime.utcnow()
        
        await session.commit()
    
    await callback.message.edit_text(
        f"✅ **Записано!**\n\n"
        f"📸 {', '.join(estimate.detected_items)}\n\n"
        f"Калории: +{estimate.calories:.0f} ккал\n"
        f"БЖУ: +{estimate.protein:.0f}/{estimate.fat:.0f}/{estimate.carbs:.0f}г\n\n"
        f"📊 Посмотреть сводку: /today"
    )
    
    await state.clear()


@router.callback_query(F.data == "photo_cancel")
async def cancel_photo_entry(callback: CallbackQuery, state: FSMContext):
    """Отмена записи"""
    await callback.answer()
    await callback.message.edit_text("❌ Отменено")
    await state.clear()


@router.callback_query(F.data == "photo_edit")
async def edit_photo_entry(callback: CallbackQuery, state: FSMContext):
    """Ручное редактирование"""
    await callback.answer()
    await callback.message.edit_text(
        "✏️ Хорошо, введите калории вручную:\n\n"
        "Формат: Еда: название, калории ккал"
    )
    await state.clear()
