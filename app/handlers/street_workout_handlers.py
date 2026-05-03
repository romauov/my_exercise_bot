import json
from datetime import datetime
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove, FSInputFile
from app.keyboard_utils import street_workout_number_keyboard
from app.draw_street_workout_plot import draw_street_workout_plot, draw_all_street_workout_plots


class StreetWorkoutEntry(StatesGroup):
    pullups_input = State()
    pushups_input = State()
    current_number = State()
    current_sets = State()


router = Router()


def get_street_workout_file_path(user_id, exercise):
    return f'data/{user_id}_{exercise}.json'


def load_street_workout_data(user_id, exercise):
    filepath = get_street_workout_file_path(user_id, exercise)
    try:
        with open(filepath, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def save_street_workout_data(user_id, exercise, data):
    filepath = get_street_workout_file_path(user_id, exercise)
    with open(filepath, 'w') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


@router.message(Command('street_wo'))
async def start_street_workout(message: Message, state: FSMContext):
    await state.set_state(StreetWorkoutEntry.pullups_input)
    await state.update_data(current_sets=[], current_number='')
    await message.answer(
        "Введи кол-во подтягиваний на турнике:",
        reply_markup=street_workout_number_keyboard()
    )


@router.message(StreetWorkoutEntry.pullups_input)
async def handle_pullups_input(message: Message, state: FSMContext):
    user_data = await state.get_data()
    current_number = user_data.get('current_number', '')
    current_sets = user_data.get('current_sets', [])
    user_id = message.from_user.id
    
    if message.text in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
        new_number = current_number + message.text
        await state.update_data(current_number=new_number)
        await message.answer(
            f"Текущее число: {new_number}",
            reply_markup=street_workout_number_keyboard()
        )
    elif message.text == "Next":
        if current_number:
            current_sets.append(int(current_number))
            await state.update_data(current_sets=current_sets, current_number='')
            await message.answer(
                f"Подход {len(current_sets)}: сохранено {current_sets[-1]} повторений",
                reply_markup=street_workout_number_keyboard()
            )
        else:
            await message.answer("Сначала введи число", reply_markup=street_workout_number_keyboard())
    elif message.text == "Done":
        if current_number:
            current_sets.append(int(current_number))
        
        if not current_sets:
            await message.answer("Нет данных для сохранения", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            return
        
        date = datetime.now().strftime("%d-%m-%Y")
        data = load_street_workout_data(user_id, 'pullups')
        
        new_entry = {"date": date, "sets": current_sets}
        
        existing_entry = next((e for e in data if e['date'] == date), None)
        if existing_entry:
            data.remove(existing_entry)
        
        data.append(new_entry)
        save_street_workout_data(user_id, 'pullups', data)
        
        await message.answer(
            f"✅ Подтягивания сохранены! {len(current_sets)} подходов: {current_sets}",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await state.update_data(current_sets=[], current_number='')
        await state.set_state(StreetWorkoutEntry.pushups_input)
        await message.answer(
            "Введи кол-во отжиманий на брусьях:",
            reply_markup=street_workout_number_keyboard()
        )
    else:
        await message.answer(
            "Введи цифру (0-9), Next или Done",
            reply_markup=street_workout_number_keyboard()
        )


@router.message(StreetWorkoutEntry.pushups_input)
async def handle_pushups_input(message: Message, state: FSMContext):
    user_data = await state.get_data()
    current_number = user_data.get('current_number', '')
    current_sets = user_data.get('current_sets', [])
    user_id = message.from_user.id
    
    if message.text in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
        new_number = current_number + message.text
        await state.update_data(current_number=new_number)
        await message.answer(
            f"Текущее число: {new_number}",
            reply_markup=street_workout_number_keyboard()
        )
    elif message.text == "Next":
        if current_number:
            current_sets.append(int(current_number))
            await state.update_data(current_sets=current_sets, current_number='')
            await message.answer(
                f"Подход {len(current_sets)}: сохранено {current_sets[-1]} повторений",
                reply_markup=street_workout_number_keyboard()
            )
        else:
            await message.answer("Сначала введи число", reply_markup=street_workout_number_keyboard())
    elif message.text == "Done":
        if current_number:
            current_sets.append(int(current_number))
        
        if not current_sets:
            await message.answer("Нет данных для сохранения", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            return
        
        date = datetime.now().strftime("%d-%m-%Y")
        data = load_street_workout_data(user_id, 'pushups')
        
        new_entry = {"date": date, "sets": current_sets}
        
        existing_entry = next((e for e in data if e['date'] == date), None)
        if existing_entry:
            data.remove(existing_entry)
        
        data.append(new_entry)
        save_street_workout_data(user_id, 'pushups', data)
        
        await message.answer(
            f"✅ Отжимания сохранены! {len(current_sets)} подходов: {current_sets}",
            reply_markup=ReplyKeyboardRemove()
        )
        
        error = draw_all_street_workout_plots(user_id)
        
        if error:
            await message.answer(error)
        else:
            try:
                photo = FSInputFile('street_workout_pullups.png')
                await message.answer_photo(photo, caption="Подтягивания на турнике")
            except Exception as e:
                await message.answer(f"Ошибка при отправке графика подтягиваний: {str(e)}")
        
        try:
            photo = FSInputFile('street_workout_pushups.png')
            await message.answer_photo(photo, caption="Отжимания на брусьях")
        except Exception as e:
            await message.answer(f"Ошибка при отправке графика отжиманий: {str(e)}")
        
        await state.clear()
    else:
        await message.answer(
            "Введи цифру (0-9), Next или Done",
            reply_markup=street_workout_number_keyboard()
        )