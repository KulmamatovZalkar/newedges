"""
Telegram Bot for New Edge Team: Staff
Бот для школы "Новые грани"
"""
import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from handlers import start, registration
from database import init_db, get_bot_token_from_db

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to run the bot."""
    # Initialize database connection first
    await init_db()
    
    # Try to get bot token from database first, then fallback to env
    bot_token = get_bot_token_from_db()
    if bot_token:
        logger.info("Using bot token from database settings")
    else:
        bot_token = os.environ.get('BOT_TOKEN')
        if bot_token:
            logger.info("Using bot token from environment variable")
        else:
            logger.error("BOT_TOKEN not found in database or environment!")
            logger.error("Please set token in admin panel or .env file")
            sys.exit(1)
    
    # Initialize bot and dispatcher
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Include routers
    dp.include_router(start.router)
    dp.include_router(registration.router)
    
    # Start polling
    logger.info("Bot is starting...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
