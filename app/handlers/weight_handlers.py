from datetime import datetime
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message, ReplyKeyboardRemove
from app.draw_plot import draw_plot
from app.utils import save_weight_json
from app.keyboard_utils import period_keyboard
from app.response_formatters import format_weight_period_response


class WeightUpdate(StatesGroup):
    model = State()


class WeightPeriod(StatesGroup):
    weight_period = State()


router = Router()


@router.message(Command('weight_save'))
async def save_weight_data(message: Message):
    user_id = message.from_user.id
    weight_file_path = f'{user_id}_weights.json'
    
    try:
        # Check if file exists
        with open(weight_file_path, 'r') as f:
            # If file exists, send it
            weight_file = FSInputFile(weight_file_path)
            await message.answer_document(weight_file, caption="Ваши данные о весе")
    except FileNotFoundError:
        await message.answer("❌ Файл с данными о весе не найден. Сначала добавьте данные с помощью команды /weight.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке файла: {str(e)}")


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
        caption = format_weight_period_response(period)
        await message.answer_photo(
            photo=photo,
            caption=caption,
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)}")
    finally:
        await state.clear()