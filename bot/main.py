"""
Main bot file - entry point
Telegram Bot "Food and Activity Diary"
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.database import init_db
from bot.scheduler import init_scheduler
from bot.handlers import (
    start, mode, free_input, guided_input, reports, export,
    settings as settings_handler, admin, photo_input, recipes, menu, ai_status, onboarding
)

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main function to start the bot"""
    
    # Validate settings
    try:
        settings.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your .env file")
        return
    
    logger.info("Starting bot...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return
    
    # Create bot and dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register routers
    dp.include_router(start.router)
    dp.include_router(onboarding.router)  # Onboarding BEFORE other handlers
    dp.include_router(admin.router)
    dp.include_router(ai_status.router)  # AI status command
    dp.include_router(menu.router)  # Main menu handler
    dp.include_router(mode.router)
    dp.include_router(recipes.router)  # Recipe handler
    dp.include_router(settings_handler.router)  # Settings BEFORE free_input to handle FSM states
    dp.include_router(photo_input.router)  # Photo handler BEFORE free_input
    dp.include_router(guided_input.router)
    dp.include_router(free_input.router)  # Free input should be last to catch remaining messages
    dp.include_router(reports.router)
    dp.include_router(export.router)
    
    logger.info("Handlers registered")
    
    # Initialize scheduler for notifications
    try:
        scheduler = await init_scheduler(bot)
        logger.info("Notification scheduler initialized")
    except Exception as e:
        logger.warning(f"Could not initialize scheduler: {e}")
        scheduler = None
    
    # Start bot
    try:
        logger.info("Bot started successfully!")
        logger.info(f"Owner Telegram ID: {settings.OWNER_TELEGRAM_ID}")
        await dp.start_polling(
            bot, 
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True  # Skip old updates to avoid "query too old" errors
        )
    except Exception as e:
        logger.error(f"Error during bot execution: {e}")
    finally:
        if scheduler:
            scheduler.shutdown()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
