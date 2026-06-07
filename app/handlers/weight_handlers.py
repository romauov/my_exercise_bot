from datetime import datetime
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message, ReplyKeyboardRemove, CallbackQuery
from app.draw_weight_plot import draw_plot
from app.utils import save_weight_json
from app.keyboard_utils import period_keyboard, weight_input_keyboard, date_input_keyboard, continue_keyboard
from app.response_formatters import format_weight_period_response


class WeightUpdate(StatesGroup):
    input_state = State()


class WeightPeriod(StatesGroup):
    weight_period = State()


class FillWeightGap(StatesGroup):
    date_input = State()
    weight_input = State()


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


@router.callback_query(F.data.startswith("weight_"), WeightUpdate.input_state)
async def handle_weight_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_data = await state.get_data()
    current_weight = user_data.get('current_weight', '')
    
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
        
        await state.clear()
        await callback.answer()
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


@router.message(Command("weight_fill"))
async def cmd_weight_fill(message: Message, state: FSMContext):
    await state.set_state(FillWeightGap.date_input)
    await state.update_data(fill_date='')
    await message.answer(
        "Введи дату (ДДММГГГГ):",
        reply_markup=date_input_keyboard()
    )


@router.callback_query(F.data.startswith("date_"), FillWeightGap.date_input)
async def handle_date_callback(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    current = user_data.get('fill_date', '')
    action = callback.data[5:]

    if action == "back":
        current = current[:-1] if current else ''
        await state.update_data(fill_date=current)
        await callback.message.edit_text(
            f"Введи дату (ДДММГГГГ):\n{current if current else '—'}",
            reply_markup=date_input_keyboard()
        )
        await callback.answer()
        return

    if action == "done":
        if len(current) != 8:
            await callback.answer("Введи 8 цифр (ДДММГГГГ)", show_alert=True)
            return
        try:
            date_obj = datetime.strptime(current, "%d%m%Y")
        except ValueError:
            await callback.answer("Неверная дата", show_alert=True)
            return

        formatted_date = date_obj.strftime("%d-%m-%Y")
        await state.update_data(fill_date=formatted_date)
        await state.set_state(FillWeightGap.weight_input)
        await state.update_data(current_weight='')
        await callback.message.edit_text(
            f"Дата: {formatted_date}\nВведи вес:",
            reply_markup=weight_input_keyboard()
        )
        await callback.answer()
        return

    if action.isdigit():
        if len(current) < 8:
            current += action
            await state.update_data(fill_date=current)
            await callback.message.edit_text(
                f"Введи дату (ДДММГГГГ):\n{current if current else '—'}",
                reply_markup=date_input_keyboard()
            )
        await callback.answer()


@router.callback_query(F.data.startswith("weight_"), FillWeightGap.weight_input)
async def handle_fill_weight_callback(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    current_weight = user_data.get('current_weight', '')
    fill_date = user_data.get('fill_date', '')

    action = callback.data[7:]

    if action == "back":
        current_weight = current_weight[:-1] if current_weight else ''
        await state.update_data(current_weight=current_weight)
        await callback.message.edit_text(
            f"Дата: {fill_date}\nВведи вес:\n{current_weight if current_weight else '—'}",
            reply_markup=weight_input_keyboard()
        )
        await callback.answer()
        return

    if action == "dot":
        if '.' not in current_weight:
            current_weight += '.'
        await state.update_data(current_weight=current_weight)
        await callback.message.edit_text(
            f"Дата: {fill_date}\nВведи вес:\n{current_weight if current_weight else '—'}",
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
            save_weight_json(callback.from_user.id, weight, fill_date)

            await callback.message.edit_text(
                f"✅ Вес {weight} на {fill_date} сохранен!",
                reply_markup=None
            )
            await state.update_data(fill_date='', current_weight='')
            await callback.message.answer(
                "Добавить ещё?",
                reply_markup=continue_keyboard()
            )
        except Exception as e:
            await callback.message.answer(f"Ошибка: {str(e)}")

        await callback.answer()
        return

    if action.isdigit():
        if len(current_weight) < 6:
            current_weight += action
            await state.update_data(current_weight=current_weight)
            await callback.message.edit_text(
                f"Дата: {fill_date}\nВведи вес:\n{current_weight if current_weight else '—'}",
                reply_markup=weight_input_keyboard()
            )
        await callback.answer()


@router.callback_query(F.data.startswith("continue_"))
async def handle_continue_callback(callback: CallbackQuery, state: FSMContext):
    action = callback.data[9:]

    if action == "yes":
        await state.set_state(FillWeightGap.date_input)
        await state.update_data(fill_date='')
        await callback.message.edit_text(
            "Введи дату (ДДММГГГГ):",
            reply_markup=date_input_keyboard()
        )
    else:
        await state.clear()
        await callback.message.edit_text("Готово!")

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