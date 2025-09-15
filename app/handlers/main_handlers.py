from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
# Импортируем роутеры из других файлов
from .workout_handlers import router as workout_router
from .workout_selection_handlers import router as workout_selection_router
from .weight_handlers import router as weight_router


router = Router()

# Включаем роутеры из других модулей
router.include_router(workout_selection_router)
router.include_router(workout_router)
router.include_router(weight_router)


@router.message(CommandStart())
async def send_welcome(message: Message):
    await message.answer("Привет! Я бот для тренировок и контроля веса. Готов улучшить свою физическую форму?")