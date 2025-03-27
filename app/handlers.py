from datetime import datetime
from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from app.draw_plot import draw_plot
from app.utils import save_weight_json


router = Router()


class WeightUpdate(StatesGroup):
    model = State()


class WeightPeriod(StatesGroup):
    weight_period = State()


def period_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text="last"),
                types.KeyboardButton(text="month")
            ],
            [
                types.KeyboardButton(text="quarter"),
                types.KeyboardButton(text="year")
            ],
            [
                types.KeyboardButton(text="all")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите период"
    )

@router.message(CommandStart())
async def send_welcome(message: types.Message):
    await message.answer("Привет! Я бот, который отправляет сообщения по расписанию.")


@router.message(Command('weight'))
async def update_weight(message: Message, state: FSMContext):
    await state.set_state(WeightUpdate.model)
    await message.answer("Введи вес в формате: 99.9")


@router.message(WeightUpdate.model)
async def save_weight(message: Message, state: FSMContext):
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


@router.message(Command("weight_"))
async def cmd_weight(message: Message, state: FSMContext):
    await message.answer(
        "🔄 Выберите период для отображения:",
        reply_markup=period_keyboard()
    )
    await state.set_state(WeightPeriod.weight_period)


@router.message(WeightPeriod.weight_period)
async def process_period(message: Message, state: FSMContext):
    period = message.text.lower()
    valid_periods = ["last", "month", "quarter", "year", "all"]

    if period not in valid_periods:
        await message.answer("❌ Неверный период! Выберите из предложенных:")
        return

    try:
        draw_plot(user_id=message.from_user.id, period=period)

        photo = FSInputFile("plot.png")
        await message.answer_photo(
            photo=photo,
            caption=f"📊 График веса за период: {period}",
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)}")
    finally:
        await state.clear()