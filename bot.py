import logging
import asyncio
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.handlers.main_handlers import router
from app.settings import secrets as s
from app.utils import set_schedule
from app.db import init_db, migrate_from_json

logging.basicConfig(level=logging.INFO)

async def main():
    init_db()
    migrate_from_json()
    scheduler = AsyncIOScheduler()
    
    bot = Bot(token=s.tg_token)
    dp = Dispatcher()
    dp.include_router(router)

    # set_schedule(scheduler, bot)
    scheduler.start()
    
    await dp.start_polling(bot)

# Запуск бота приостановлен: сейчас основной интерфейс — сайт контроля веса (web/).
# Бот включается обратно открытием этих строк.
# if __name__ == "__main__":
#     asyncio.run(main())
