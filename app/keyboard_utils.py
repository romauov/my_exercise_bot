from aiogram import types
from aiogram.types import ReplyKeyboardMarkup


def period_keyboard():
    """Create keyboard for weight period selection"""
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


def difficulty_keyboard():
    """Create keyboard for workout difficulty selection"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text="morning"),
                types.KeyboardButton(text="easy")
            ],
            [
                types.KeyboardButton(text="medium"),
                types.KeyboardButton(text="hard")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите уровень сложности"
    )


def workout_action_keyboard():
    """Create keyboard with Done and Another buttons"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text="✅ Done"),
                types.KeyboardButton(text="🎲 Another")
            ]
        ],
        resize_keyboard=True
    )


def street_workout_number_keyboard():
    """Create keyboard for street workout number input: 0-4, 5-9, Next, Done"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text="0"),
                types.KeyboardButton(text="1"),
                types.KeyboardButton(text="2"),
                types.KeyboardButton(text="3"),
                types.KeyboardButton(text="4")
            ],
            [
                types.KeyboardButton(text="5"),
                types.KeyboardButton(text="6"),
                types.KeyboardButton(text="7"),
                types.KeyboardButton(text="8"),
                types.KeyboardButton(text="9")
            ],
            [
                types.KeyboardButton(text="Next"),
                types.KeyboardButton(text="Done")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Введите цифру"
    )