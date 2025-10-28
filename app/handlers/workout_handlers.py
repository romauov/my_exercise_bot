from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, FSInputFile
from app.workout_utils import (
    add_workout_to_file,
    remove_workout_from_file,
    get_all_workouts
)
from app.response_formatters import format_workout_list_response_parts


class WorkoutCreation(StatesGroup):
    name = State()
    description = State()
    tags = State()


class WorkoutDeletion(StatesGroup):
    select = State()


router = Router()


@router.message(Command('add_workout'))
async def add_workout_start(message: Message, state: FSMContext):
    await state.set_state(WorkoutCreation.name)
    await message.answer("Введите название новой тренировки:")


@router.message(WorkoutCreation.name)
async def add_workout_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(WorkoutCreation.description)
    await message.answer("Введите описание тренировки:")


@router.message(WorkoutCreation.description)
async def add_workout_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(WorkoutCreation.tags)
    await message.answer("Введите теги тренировки через запятую (morning, easy, medium, hard):")


@router.message(WorkoutCreation.tags)
async def add_workout_tags(message: Message, state: FSMContext):
    tags = [tag.strip() for tag in message.text.split(',')]
    data = await state.get_data()
    
    # Add workout to file
    new_workout = add_workout_to_file(data['name'], data['description'], tags)
    
    if new_workout:
        await message.answer(f"✅ Тренировка '{new_workout['name']}' успешно добавлена!", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("❌ Ошибка при добавлении тренировки.", reply_markup=ReplyKeyboardRemove())
    
    await state.clear()


@router.message(Command('remove_workout'))
async def remove_workout_start(message: Message, state: FSMContext):
    workouts = get_all_workouts()
    
    if not workouts:
        await message.answer("😔 Список тренировок пуст.", reply_markup=ReplyKeyboardRemove())
        return
    
    # Create keyboard with workout names
    keyboard_buttons = []
    for workout in workouts:
        keyboard_buttons.append([types.KeyboardButton(text=f"{workout['id']}. {workout['name']}")])
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        input_field_placeholder="Выберите тренировку для удаления"
    )
    
    await state.set_state(WorkoutDeletion.select)
    await message.answer("Выберите тренировку для удаления:", reply_markup=keyboard)


@router.message(WorkoutDeletion.select)
async def remove_workout_select(message: Message, state: FSMContext):
    try:
        # Extract workout ID from message (format: "ID. Name")
        workout_id = message.text.split('.')[0]
        
        # Remove workout
        removed_workout = remove_workout_from_file(workout_id)
        
        if removed_workout:
            await message.answer(f"✅ Тренировка '{removed_workout['name']}' успешно удалена! ID тренировок были переназначены.", reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer("❌ Ошибка при удалении тренировки. Убедитесь, что вы выбрали существующую тренировку.", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        await message.answer("❌ Ошибка при удалении тренировки.", reply_markup=ReplyKeyboardRemove())
    
    await state.clear()


@router.message(Command('list_workout'))
async def list_workouts(message: Message):
    workouts = get_all_workouts()
    response_parts = format_workout_list_response_parts(workouts)
    
    # Send each part as a separate message
    for i, response in enumerate(response_parts):
        if i == len(response_parts) - 1:  # Last message
            await message.answer(response, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
        else:
            await message.answer(response, parse_mode="HTML")


@router.message(Command('save_workout'))
async def save_workout_data(message: Message):
    workout_file_path = 'workout_cards.json'
    
    try:
        # Check if file exists
        with open(workout_file_path, 'r') as f:
            # If file exists, send it
            workout_file = FSInputFile(workout_file_path)
            await message.answer_document(workout_file, caption="Ваши данные о тренировках")
    except FileNotFoundError:
        await message.answer("❌ Файл с данными о тренировках не найден.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке файла: {str(e)}")