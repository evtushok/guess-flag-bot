from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.config import *

def get_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎮 классика (3 жизни)", 
                   callback_data=f"{CB_START_GAME}:{MODE_CLASSIC}")
    builder.button(text="♾️ бесконечность", 
                   callback_data=f"{CB_START_GAME}:{MODE_ENDLESS}")
    builder.button(text="⏱️ на время (30 сек)", 
                   callback_data=f"{CB_START_GAME}:{MODE_TIMED}")
    builder.adjust(1)
    return builder.as_markup()

def get_answer_keyboard(question_id: str, options: list, mode: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, option in enumerate(options):
        builder.button(
            text=option,
            callback_data=f"{CB_ANSWER}:{question_id}:{idx}:{mode}"
        )
    # кнопка выхода для endless режима
    if mode == MODE_ENDLESS: builder.button(text="🏁 завершить", callback_data=f"{CB_MENU}:end_game")
    builder.adjust(1)  # всегда 1 колонка для простоты
    return builder.as_markup()

def get_game_over_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 играть снова", callback_data=f"{CB_MENU}:play_again")
    builder.button(text="🏠 главное меню", callback_data=f"{CB_MENU}:main")
    builder.adjust(1)
    return builder.as_markup()