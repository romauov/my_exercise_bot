import logging
import asyncio
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.handlers.main_handlers import router
from app.settings import secrets as s
from app.utils import set_schedule

logging.basicConfig(level=logging.INFO)

async def main():
    scheduler = AsyncIOScheduler()
    
    bot = Bot(token=s.tg_token)
    dp = Dispatcher()
    dp.include_router(router)

    set_schedule(scheduler, bot)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
