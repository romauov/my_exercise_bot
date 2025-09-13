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
                types.KeyboardButton(text="easy"),
                types.KeyboardButton(text="medium")
            ],
            [
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