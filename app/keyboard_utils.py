from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


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


def street_workout_number_keyboard(exercise: str = "pullups") -> InlineKeyboardMarkup:
    """Create inline keyboard for street workout number input"""
    prefix = f"{exercise}_"
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="7", callback_data=f"{prefix}7"),
                InlineKeyboardButton(text="8", callback_data=f"{prefix}8"),
                InlineKeyboardButton(text="9", callback_data=f"{prefix}9"),
            ],
            [
                InlineKeyboardButton(text="4", callback_data=f"{prefix}4"),
                InlineKeyboardButton(text="5", callback_data=f"{prefix}5"),
                InlineKeyboardButton(text="6", callback_data=f"{prefix}6"),
            ],
            [
                InlineKeyboardButton(text="1", callback_data=f"{prefix}1"),
                InlineKeyboardButton(text="2", callback_data=f"{prefix}2"),
                InlineKeyboardButton(text="3", callback_data=f"{prefix}3"),
            ],
            [
                InlineKeyboardButton(text="0", callback_data=f"{prefix}0"),
                InlineKeyboardButton(text="⌫", callback_data=f"{prefix}back"),
                InlineKeyboardButton(text="Next", callback_data=f"{prefix}next"),
            ],
            [
                InlineKeyboardButton(text="Done", callback_data=f"{prefix}done"),
            ],
        ]
    )


def continue_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data="continue_yes"),
                InlineKeyboardButton(text="Нет", callback_data="continue_no"),
            ],
        ]
    )


def date_input_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="7", callback_data="date_7"),
                InlineKeyboardButton(text="8", callback_data="date_8"),
                InlineKeyboardButton(text="9", callback_data="date_9"),
            ],
            [
                InlineKeyboardButton(text="4", callback_data="date_4"),
                InlineKeyboardButton(text="5", callback_data="date_5"),
                InlineKeyboardButton(text="6", callback_data="date_6"),
            ],
            [
                InlineKeyboardButton(text="1", callback_data="date_1"),
                InlineKeyboardButton(text="2", callback_data="date_2"),
                InlineKeyboardButton(text="3", callback_data="date_3"),
            ],
            [
                InlineKeyboardButton(text="⌫", callback_data="date_back"),
                InlineKeyboardButton(text="0", callback_data="date_0"),
                InlineKeyboardButton(text="Done", callback_data="date_done"),
            ],
        ]
    )


def weight_input_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard for weight input"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="7", callback_data="weight_7"),
                InlineKeyboardButton(text="8", callback_data="weight_8"),
                InlineKeyboardButton(text="9", callback_data="weight_9"),
            ],
            [
                InlineKeyboardButton(text="4", callback_data="weight_4"),
                InlineKeyboardButton(text="5", callback_data="weight_5"),
                InlineKeyboardButton(text="6", callback_data="weight_6"),
            ],
            [
                InlineKeyboardButton(text="1", callback_data="weight_1"),
                InlineKeyboardButton(text="2", callback_data="weight_2"),
                InlineKeyboardButton(text="3", callback_data="weight_3"),
            ],
            [
                InlineKeyboardButton(text=".", callback_data="weight_dot"),
                InlineKeyboardButton(text="0", callback_data="weight_0"),
                InlineKeyboardButton(text="⌫", callback_data="weight_back"),
            ],
            [
                InlineKeyboardButton(text="Done", callback_data="weight_done"),
            ],
        ]
    )