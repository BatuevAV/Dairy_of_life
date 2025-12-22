"""
Scheduler for sending notifications to users
Uses APScheduler for scheduling tasks
"""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from bot.config import settings
from bot.database import get_db, User
from bot.ai.recommendations_provider import RecommendationsProvider

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """Manages scheduled notifications for users"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        
    async def send_breakfast_notification(self, user_id: int, telegram_id: int):
        """Send morning breakfast suggestion"""
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user or not user.notifications_enabled:
                    return
                
                # Generate breakfast suggestions
                provider = RecommendationsProvider()
                suggestions = await provider.generate_breakfast_suggestions(user, count=3)
                
                text = "🌅 <b>Доброе утро! Что приготовим на завтрак?</b>\n\n"
                
                keyboard_buttons = []
                for idx, dish in enumerate(suggestions, 1):
                    text += (
                        f"<b>{idx}. {dish['name']}</b>\n"
                        f"   🔥 {dish['kcal']} ккал | "
                        f"Б: {dish['protein']}г | Ж: {dish['fat']}г | У: {dish['carbs']}г\n\n"
                    )
                    keyboard_buttons.append([
                        InlineKeyboardButton(
                            text=f"📋 {dish['name']}", 
                            callback_data=f"recipe:{dish['name']}"
                        )
                    ])
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
                await self.bot.send_message(telegram_id, text, parse_mode="HTML", reply_markup=keyboard)
                
                logger.info(f"Breakfast notification sent to user {telegram_id}")
                
        except Exception as e:
            logger.error(f"Error sending breakfast notification to {telegram_id}: {e}")
    
    async def send_lunch_notification(self, user_id: int, telegram_id: int):
        """Send lunch reminder"""
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user or not user.notifications_enabled:
                    return
                
                text = (
                    "🍽 <b>Время обеда!</b>\n\n"
                    "Не забудь записать, что ты съел. "
                    "Можешь отправить фото или описать текстом.\n\n"
                    "💡 Или используй команду /add для пошагового ввода."
                )
                
                await self.bot.send_message(telegram_id, text, parse_mode="HTML")
                logger.info(f"Lunch notification sent to user {telegram_id}")
                
        except Exception as e:
            logger.error(f"Error sending lunch notification to {telegram_id}: {e}")
    
    async def send_dinner_notification(self, user_id: int, telegram_id: int):
        """Send dinner reminder"""
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user or not user.notifications_enabled:
                    return
                
                text = (
                    "🍴 <b>Время ужина!</b>\n\n"
                    "Помни о балансе калорий в течение дня. "
                    "Не забудь записать свой ужин!\n\n"
                    "📊 Посмотри статистику за сегодня: /today"
                )
                
                await self.bot.send_message(telegram_id, text, parse_mode="HTML")
                logger.info(f"Dinner notification sent to user {telegram_id}")
                
        except Exception as e:
            logger.error(f"Error sending dinner notification to {telegram_id}: {e}")
    
    async def send_evening_reminder(self, user_id: int, telegram_id: int):
        """Send evening reminder to log data"""
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user or not user.notifications_enabled:
                    return
                
                text = (
                    "🌙 <b>Время подвести итоги дня!</b>\n\n"
                    "Не забудь внести все данные за сегодня:\n"
                    "• Еда и напитки 🍽\n"
                    "• Тренировки 💪\n"
                    "• Шаги 🚶\n"
                    "• Сон 😴\n\n"
                    "📊 Проверь свою статистику: /today\n"
                    "✏️ Добавь данные: /add"
                )
                
                await self.bot.send_message(telegram_id, text, parse_mode="HTML")
                logger.info(f"Evening reminder sent to user {telegram_id}")
                
        except Exception as e:
            logger.error(f"Error sending evening reminder to {telegram_id}: {e}")
    
    async def schedule_user_notifications(self, user_id: int, telegram_id: int, 
                                         breakfast_time: str, lunch_time: str, 
                                         dinner_time: str, evening_time: str):
        """Schedule notifications for a specific user"""
        
        # Parse time strings (HH:MM)
        breakfast_hour, breakfast_minute = map(int, breakfast_time.split(':'))
        lunch_hour, lunch_minute = map(int, lunch_time.split(':'))
        dinner_hour, dinner_minute = map(int, dinner_time.split(':'))
        evening_hour, evening_minute = map(int, evening_time.split(':'))
        
        # Schedule breakfast
        self.scheduler.add_job(
            self.send_breakfast_notification,
            CronTrigger(hour=breakfast_hour, minute=breakfast_minute),
            args=[user_id, telegram_id],
            id=f"breakfast_{user_id}",
            replace_existing=True
        )
        
        # Schedule lunch
        self.scheduler.add_job(
            self.send_lunch_notification,
            CronTrigger(hour=lunch_hour, minute=lunch_minute),
            args=[user_id, telegram_id],
            id=f"lunch_{user_id}",
            replace_existing=True
        )
        
        # Schedule dinner
        self.scheduler.add_job(
            self.send_dinner_notification,
            CronTrigger(hour=dinner_hour, minute=dinner_minute),
            args=[user_id, telegram_id],
            id=f"dinner_{user_id}",
            replace_existing=True
        )
        
        # Schedule evening reminder
        self.scheduler.add_job(
            self.send_evening_reminder,
            CronTrigger(hour=evening_hour, minute=evening_minute),
            args=[user_id, telegram_id],
            id=f"evening_{user_id}",
            replace_existing=True
        )
        
        logger.info(f"Scheduled notifications for user {telegram_id}")
    
    async def load_all_users(self):
        """Load all users and schedule their notifications"""
        try:
            async with get_db() as db:
                result = await db.execute(
                    select(User).where(User.notifications_enabled == True)
                )
                users = result.scalars().all()
                
                for user in users:
                    if user.is_allowed or user.is_owner:
                        await self.schedule_user_notifications(
                            user.id,
                            user.telegram_user_id,
                            user.breakfast_time,
                            user.lunch_time,
                            user.dinner_time,
                            user.evening_reminder_time
                        )
                
                logger.info(f"Loaded {len(users)} users with notifications enabled")
                
        except Exception as e:
            logger.error(f"Error loading users: {e}")
    
    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        logger.info("Notification scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown()
        logger.info("Notification scheduler stopped")


# Global scheduler instance
_scheduler: NotificationScheduler = None


async def init_scheduler(bot: Bot):
    """Initialize and start the scheduler"""
    global _scheduler
    _scheduler = NotificationScheduler(bot)
    await _scheduler.load_all_users()
    _scheduler.start()
    return _scheduler


def get_scheduler() -> NotificationScheduler:
    """Get the global scheduler instance"""
    return _scheduler
