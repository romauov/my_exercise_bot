from datetime import datetime
from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from app.draw_plot import draw_plot
from app.utils import save_weight_json
from app.workout_utils import (
    get_random_workout_by_difficulty,
    update_workout_history,
    add_workout_to_file,
    remove_workout_from_file,
    get_all_workouts
)
from app.keyboard_utils import period_keyboard, difficulty_keyboard, workout_action_keyboard
from app.response_formatters import format_workout_response, format_workout_list_response, format_weight_period_response


router = Router()


class WeightUpdate(StatesGroup):
    model = State()


class WeightPeriod(StatesGroup):
    weight_period = State()


class WorkoutSelection(StatesGroup):
    difficulty = State()
    workout = State()
    last_workout = State()  # Store last workout for "another" functionality
    last_difficulty = State()  # Store last difficulty for "another" functionality


class WorkoutCreation(StatesGroup):
    name = State()
    description = State()
    tags = State()


class WorkoutDeletion(StatesGroup):
    select = State()


@router.message(CommandStart())
async def send_welcome(message: types.Message):
    await message.answer("Привет! Я бот для тренировок и контроля веса. Готов улучшить свою физическую форму?")


@router.message(Command('workout'))
async def select_workout_difficulty(message: Message, state: FSMContext):
    await state.set_state(WorkoutSelection.difficulty)
    await message.answer(
        "💪 Выберите уровень сложности тренировки:",
        reply_markup=difficulty_keyboard()
    )


@router.message(WorkoutSelection.difficulty)
async def send_random_workout(message: Message, state: FSMContext):
    difficulty = message.text.lower()
    valid_difficulties = ["easy", "medium", "hard"]
    
    if difficulty not in valid_difficulties:
        await message.answer(
            "❌ Неверный уровень сложности! Выберите из предложенных:",
            reply_markup=difficulty_keyboard()
        )
        return
    
    workout = get_random_workout_by_difficulty(difficulty)
    
    if workout:
        # Store last workout and difficulty for "another" functionality
        await state.update_data(last_workout=workout, last_difficulty=difficulty)
        # Change state to indicate we're waiting for user action
        await state.set_state(WorkoutSelection.last_workout)
        
        response = format_workout_response(workout, difficulty)
        await message.answer(response, reply_markup=workout_action_keyboard(), parse_mode="HTML")
    else:
        await message.answer(
            "😔 К сожалению, тренировки с уровнем сложности <b>" + difficulty + "</b> не найдены. Попробуйте добавить новую тренировку с помощью команды /add_workout.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
        await state.clear()


# Handler for Done button
@router.message(lambda message: message.text == "✅ Done")
async def workout_done(message: Message, state: FSMContext):
    # Check if we're in the right state
    current_state = await state.get_state()
    if current_state not in [WorkoutSelection.last_workout.state, WorkoutSelection.last_difficulty.state]:
        # If not in the right state, ignore this message
        return
    
    # Get the last workout from state
    user_data = await state.get_data()
    last_workout = user_data.get('last_workout')
    
    if last_workout:
        # Update workout history and reps counter
        update_workout_history(last_workout['id'])
        
        await message.answer(
            f"✅ Отличная работа! Тренировка '{last_workout['name']}' засчитана.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer(
            "❌ Не удалось найти последнюю тренировку. Попробуйте снова.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    await state.clear()


# Handler for Another button
@router.message(lambda message: message.text == "🎲 Another")
async def workout_another(message: Message, state: FSMContext):
    # Check if we're in the right state
    current_state = await state.get_state()
    if current_state != WorkoutSelection.last_workout.state:
        # If not in the right state, ignore this message
        return
    
    # Get the last difficulty from state
    user_data = await state.get_data()
    last_difficulty = user_data.get('last_difficulty')
    
    if last_difficulty:
        # Get a new random workout with the same difficulty
        workout = get_random_workout_by_difficulty(last_difficulty)
        
        if workout:
            # Update last workout in state
            await state.update_data(last_workout=workout)
            # Keep the same state
            await state.set_state(WorkoutSelection.last_workout)
            
            response = format_workout_response(workout, last_difficulty)
            await message.answer(response, reply_markup=workout_action_keyboard(), parse_mode="HTML")
        else:
            await message.answer(
                "😔 К сожалению, тренировки с уровнем сложности <b>" + last_difficulty + "</b> не найдены.",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="HTML"
            )
            await state.clear()
    else:
        await message.answer(
            "❌ Не удалось найти предыдущий уровень сложности. Попробуйте снова.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()


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
    await message.answer("Введите теги тренировки через запятую (например: easy, medium, hard):")


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
    response = format_workout_list_response(workouts)
    await message.answer(response, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")


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