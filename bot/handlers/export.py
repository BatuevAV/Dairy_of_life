"""
Export handler - /export command
"""
from datetime import date, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from sqlalchemy import select
from sqlalchemy.sql import and_

from bot.config import settings
from bot.database import get_db, User, DayEntry
from bot.utils import create_excel_export

router = Router()


@router.message(Command("export"))
async def cmd_export(message: Message):
    """Handle /export command"""
    user_id = message.from_user.id
    
    if user_id != settings.OWNER_TELEGRAM_ID:
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="7 дней", callback_data="export_7"),
            InlineKeyboardButton(text="30 дней", callback_data="export_30")
        ],
        [
            InlineKeyboardButton(text="Всё", callback_data="export_all")
        ]
    ])
    
    await message.answer(
        "📊 <b>Экспорт данных в Excel</b>\n\n"
        "Выбери период для экспорта:",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("export_"))
async def callback_export(callback: CallbackQuery):
    """Handle export callback"""
    user_id = callback.from_user.id
    
    if user_id != settings.OWNER_TELEGRAM_ID:
        await callback.answer("Доступ запрещён")
        return
    
    await callback.message.edit_text("⏳ Генерирую Excel файл...")
    
    period = callback.data.split("_")[1]  # 7, 30, or all
    
    end_date = date.today()
    
    if period == "all":
        start_date = date(2020, 1, 1)  # Far enough in the past
        days = 999
    else:
        days = int(period)
        start_date = end_date - timedelta(days=days - 1)
    
    # Get data from database
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text("Используй /start для начала работы")
            return
        
        result = await db.execute(
            select(DayEntry).where(
                and_(
                    DayEntry.user_id == user.id,
                    DayEntry.entry_date >= start_date,
                    DayEntry.entry_date <= end_date
                )
            ).order_by(DayEntry.entry_date)
        )
        entries = result.scalars().all()
    
    if not entries:
        await callback.message.edit_text(
            "❌ Нет данных для экспорта за выбранный период."
        )
        await callback.answer()
        return
    
    # Create Excel file
    try:
        excel_buffer = create_excel_export(user, entries, days)
        
        # Prepare filename
        filename = f"diary_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
        
        # Send file
        file = BufferedInputFile(excel_buffer.read(), filename=filename)
        
        await callback.message.answer_document(
            file,
            caption=f"📊 Экспорт дневника\n"
                    f"Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n"
                    f"Записей: {len(entries)}"
        )
        
        await callback.message.edit_text("✅ Файл готов!")
        
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка при создании файла: {str(e)}")
    
    await callback.answer()
