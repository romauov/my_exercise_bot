import json
from datetime import datetime
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, CallbackQuery
from app.keyboard_utils import street_workout_number_keyboard
from app.draw_street_workout_plot import draw_all_street_workout_plots


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


def build_current_display(current_number: str, current_sets: list, exercise: str = "pullups") -> str:
    sets_text = ", ".join(str(s) for s in current_sets) if current_sets else "0"
    num_text = current_number if current_number else "0"
    
    exercise_name = "Подтягивания" if exercise == "pullups" else "Отжимания"
    
    return f"Упражнение: {exercise_name}\nЧисло: {num_text}\nПодходы: {sets_text}"


@router.message(Command('street_wo'))
async def start_street_workout(message: Message, state: FSMContext):
    await state.set_state(StreetWorkoutEntry.pullups_input)
    await state.update_data(current_sets=[], current_number='')
    await message.answer(
        build_current_display("", [], "pullups"),
        reply_markup=street_workout_number_keyboard("pullups")
    )


@router.callback_query(F.data.startswith("pullups_") | F.data.startswith("pushups_"))
async def handle_street_workout_callback(callback: CallbackQuery, state: FSMContext):
    callback_data = callback.data
    
    if callback_data.startswith("pullups_"):
        exercise = "pullups"
    elif callback_data.startswith("pushups_"):
        exercise = "pushups"
    else:
        await callback.answer()
        return
    
    state_target = StreetWorkoutEntry.pullups_input.state if exercise == "pullups" else StreetWorkoutEntry.pushups_input.state
    action = callback_data[len(exercise) + 1:]
    
    user_id = callback.from_user.id
    user_data = await state.get_data()
    current_number = user_data.get('current_number', '')
    current_sets = user_data.get('current_sets', [])
    
    if action == "back":
        current_number = current_number[:-1] if current_number else ''
        await state.update_data(current_number=current_number)
        await callback.message.edit_text(
            build_current_display(current_number, current_sets, exercise),
            reply_markup=street_workout_number_keyboard(exercise)
        )
        await callback.answer()
        return
    
    if action == "next":
        if current_number:
            current_sets.append(int(current_number))
            current_number = ''
            await state.update_data(current_sets=current_sets, current_number='')
            await callback.message.edit_text(
                build_current_display(current_number, current_sets, exercise),
                reply_markup=street_workout_number_keyboard(exercise)
            )
            await callback.answer(f"Подход {len(current_sets)}: сохранено {current_sets[-1]}")
        else:
            await callback.answer("Сначала введи число", show_alert=True)
        return
    
    if action == "done":
        if current_number:
            current_sets.append(int(current_number))
        
        if not current_sets:
            await callback.message.edit_text("Нет данных для сохранения", reply_markup=None)
            await callback.answer()
            await state.clear()
            return
        
        date = datetime.now().strftime("%d-%m-%Y")
        data = load_street_workout_data(user_id, exercise)
        
        new_entry = {"date": date, "sets": current_sets}
        
        existing_entry = next((e for e in data if e['date'] == date), None)
        if existing_entry:
            data.remove(existing_entry)
        
        data.append(new_entry)
        save_street_workout_data(user_id, exercise, data)
        
        exercise_name = "Подтягивания" if exercise == "pullups" else "Отжимания"
        
        if exercise == "pullups":
            await callback.message.edit_text(
                f"✅ {exercise_name} сохранены! {len(current_sets)} подходов: {current_sets}",
                reply_markup=None
            )
            
            await state.update_data(current_sets=[], current_number='')
            await state.set_state(StreetWorkoutEntry.pushups_input)
            
            await callback.message.answer(
                build_current_display("", [], "pushups"),
                reply_markup=street_workout_number_keyboard("pushups")
            )
        else:
            await callback.message.edit_text(
                f"✅ {exercise_name} сохранены! {len(current_sets)} подходов: {current_sets}",
                reply_markup=None
            )
            
            error = draw_all_street_workout_plots(user_id)
            
            if error:
                await callback.message.answer(error)
            else:
                try:
                    photo = FSInputFile('data/street_workout_pullups.png')
                    await callback.message.answer_photo(photo, caption="Подтягивания на турнике")
                except Exception as e:
                    await callback.message.answer(f"Ошибка: {str(e)}")
            
            try:
                photo = FSInputFile('data/street_workout_pushups.png')
                await callback.message.answer_photo(photo, caption="Отжимания на брусьях")
            except Exception as e:
                await callback.message.answer(f"Ошибка: {str(e)}")
        
        await callback.answer()
        await state.clear()
        return
    
    if action.isdigit():
        if len(current_number) < 10:
            current_number += action
            await state.update_data(current_number=current_number)
            await callback.message.edit_text(
                build_current_display(current_number, current_sets, exercise),
                reply_markup=street_workout_number_keyboard(exercise)
            )
        await callback.answer()