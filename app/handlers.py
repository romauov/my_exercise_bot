from aiogram import Bot, types, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, Message
from datetime import datetime
from app.utils import draw_plot, save_weight_json

router = Router()

class WeightUpdate(StatesGroup):
    model = State()


@router.message(CommandStart())
async def send_welcome(message: types.Message):
    await message.answer("Привет! Я бот, который отправляет сообщения по расписанию.")

@router.message(Command('weight'))
async def update_weight(message: Message, state: FSMContext):
    await state.set_state(WeightUpdate.model)
    await message.answer("Введи вес в формате: 99.9")

@router.message(Command('weight_full'))
async def send_weight(message: Message, state: FSMContext):
    draw_plot(user_id=message.from_user.id, period=0)
    photo_file = FSInputFile(path='plot.png')
    await message.answer_photo(photo=photo_file)
    
@router.message(WeightUpdate.model)
async def save_weight(message: Message, state: FSMContext, bot: Bot):
    try:
        weight = float(message.text)
        user_id = message.from_user.id
        date = datetime.now().strftime('%d-%m-%Y')

        save_weight_json(user_id, weight, date)

        await message.reply("Вес сохранен!")
        await state.clear()
        photo_file = FSInputFile(path='plot.png')
        await message.answer_photo(photo=photo_file)
        
    except Exception as e:
        await message.reply(e)
