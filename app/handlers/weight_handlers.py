from datetime import datetime
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message, ReplyKeyboardRemove, CallbackQuery
from app.draw_weight_plot import draw_plot
from app.utils import save_weight_json
from app.keyboard_utils import period_keyboard, weight_input_keyboard
from app.response_formatters import format_weight_period_response


class WeightUpdate(StatesGroup):
    input_state = State()


class WeightPeriod(StatesGroup):
    weight_period = State()


def build_weight_display_fixed(current_weight: str) -> str:
    weight_text = current_weight if current_weight else "—"
    return f"Сегодняшний вес:\n{weight_text}"


router = Router()


@router.message(Command("weight"))
async def update_weight(message: Message, state: FSMContext):
    await state.set_state(WeightUpdate.input_state)
    await state.update_data(current_weight='')
    await message.answer(
        build_weight_display_fixed(""),
        reply_markup=weight_input_keyboard()
    )


@router.callback_query(F.data.startswith("weight_"))
async def handle_weight_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_data = await state.get_data()
    current_weight = user_data.get('current_weight', '')
    
    current_state = await state.get_state()
    if current_state != WeightUpdate.input_state.state:
        await callback.answer()
        return
    
    action = callback.data[7:]
    
    if action == "back":
        current_weight = current_weight[:-1] if current_weight else ''
        await state.update_data(current_weight=current_weight)
        await callback.message.edit_text(
            build_weight_display_fixed(current_weight),
            reply_markup=weight_input_keyboard()
        )
        await callback.answer()
        return
    
    if action == "dot":
        if '.' not in current_weight:
            current_weight += '.'
        await state.update_data(current_weight=current_weight)
        await callback.message.edit_text(
            build_weight_display_fixed(current_weight),
            reply_markup=weight_input_keyboard()
        )
        await callback.answer()
        return
    
    if action == "done":
        if not current_weight or current_weight == '.':
            await callback.answer("Введите вес", show_alert=True)
            return
        
        try:
            weight = float(current_weight)
            date = datetime.now().strftime("%d-%m-%Y")
            save_weight_json(user_id, weight, date)
            
            await callback.message.edit_text(
                f"✅ Вес {weight} сохранен!",
                reply_markup=None
            )
            
            result = draw_plot(user_id=user_id)
            
            if isinstance(result, str):
                await callback.message.answer(result, reply_markup=ReplyKeyboardRemove())
            else:
                photo = FSInputFile("data/plot.png")
                await callback.message.answer_photo(photo, caption=f"Вес за последние 14 дней")
            
        except Exception as e:
            await callback.message.answer(f"Ошибка: {str(e)}")
        
        await callback.answer()
        await state.clear()
        return
    
    if action.isdigit():
        if len(current_weight) < 6:
            current_weight += action
            await state.update_data(current_weight=current_weight)
            await callback.message.edit_text(
                build_weight_display_fixed(current_weight),
                reply_markup=weight_input_keyboard()
            )
        await callback.answer()


@router.message(Command("weight_save"))
async def save_weight_data(message: Message):
    user_id = message.from_user.id
    weight_file_path = f"data/{user_id}_weights.json"

    try:
        with open(weight_file_path, "r") as f:
            weight_file = FSInputFile(weight_file_path)
            await message.answer_document(weight_file, caption="Ваши данные о весе")
    except FileNotFoundError:
        await message.answer(
            "❌ Файл с данными о весе не найден. Сначала добавьте данные с помощью команды /weight."
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке файла: {str(e)}")


@router.message(Command("weight_"))
async def cmd_weight(message: Message, state: FSMContext):
    await message.answer(
        "🔄 Выберите период для отображения:", reply_markup=period_keyboard()
    )
    await state.set_state(WeightPeriod.weight_period)


@router.message(WeightPeriod.weight_period)
async def process_period(message: Message, state: FSMContext):
    period = message.text.lower()
    valid_periods = ["last", "month", "quarter", "year", "all"]

    if period not in valid_periods:
        await message.answer("❌ Неверный период! Выберите из предложенных:")
        return

    result = draw_plot(user_id=message.from_user.id, period=period)

    if isinstance(result, str):
        await message.answer(result, reply_markup=ReplyKeyboardRemove())
    else:
        photo = FSInputFile("data/plot.png")
        caption = format_weight_period_response(period)
        await message.answer_photo(
            photo=photo, caption=caption, reply_markup=ReplyKeyboardRemove()
        )

    await state.clear()