from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import Message
from app.workout_utils import (
    get_random_workout_by_difficulty,
    update_workout_history
)
from app.keyboard_utils import difficulty_keyboard, workout_action_keyboard
from app.response_formatters import format_workout_response


class WorkoutSelection(StatesGroup):
    difficulty = State()
    workout = State()
    last_workout = State()  # Store last workout for "another" functionality
    last_difficulty = State()  # Store last difficulty for "another" functionality


router = Router()


@router.message(Command('kettlebell'))
async def select_workout_difficulty(message: Message, state: FSMContext):
    await state.set_state(WorkoutSelection.difficulty)
    await message.answer(
        "💪 Выберите уровень сложности тренировки:",
        reply_markup=difficulty_keyboard()
    )


@router.message(WorkoutSelection.difficulty)
async def send_random_workout(message: Message, state: FSMContext):
    difficulty = message.text.lower()
    valid_difficulties = ["morning", "easy", "medium", "hard"]
    
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
            reply_markup=difficulty_keyboard(),
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
            reply_markup=workout_action_keyboard()  # Используем ту же клавиатуру для согласованности
        )
    else:
        await message.answer(
            "❌ Не удалось найти последнюю тренировку. Попробуйте снова.",
            reply_markup=workout_action_keyboard()
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
                reply_markup=workout_action_keyboard(),
                parse_mode="HTML"
            )
            await state.clear()
    else:
        await message.answer(
            "❌ Не удалось найти предыдущий уровень сложности. Попробуйте снова.",
            reply_markup=workout_action_keyboard()
        )
        await state.clear()