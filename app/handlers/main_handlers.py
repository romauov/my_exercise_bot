from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
# Импортируем роутеры из других файлов
# from .workout_handlers import router as kettlebell_workout_handler
# from .workout_selection_handlers import router as kettlebell_workout_selection
from .weight_handlers import router as weight_router
from .street_workout_handlers import router as street_workout_router


router = Router()

# Включаем роутеры из других модулей
# router.include_router(kettlebell_workout_selection)
# router.include_router(kettlebell_workout_handler)
router.include_router(weight_router)
router.include_router(street_workout_router)


@router.message(CommandStart())
async def send_welcome(message: Message):
    await message.answer("Привет! Я бот для тренировок и контроля веса. Готов улучшить свою физическую форму?")