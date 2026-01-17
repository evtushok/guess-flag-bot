import asyncio
import random
import uuid
import json
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from app.keyboards import *
from app.game_modes import *
from app.config import *

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

countries_cache = []

# загрузка из json в массив countries_cache
async def load_countries():
    global countries_cache
    try:
        loop = asyncio.get_event_loop()
        with open(COUNTRIES_FILE, "r", encoding="utf-8") as f: data = await loop.run_in_executor(None, json.load, f)
        for country in data:
            try:
                countries_cache.append({
                    "name": country["name"],
                    "code": country["code"],
                    "emoji": country["emoji"]
                })
            except: continue
        print(f"{DBG} загружено {len(countries_cache)} стран")
        return True
    except Exception as e:
        print(f"{DBG} ошибка: {e}")
        return False

def generate_question() -> dict:
    if not countries_cache: raise ValueError(f"{DBG} база данных стран пуста!")
    correct = random.choice(countries_cache)
    wrong = random.sample( [c for c in countries_cache if c != correct], k=3)
    options = [correct] + wrong
    random.shuffle(options)
    question_id = str(uuid.uuid4())[:8]
    return {
        "id": question_id,
        "emoji": correct["emoji"],
        "correct": correct["name"],
        "options": [opt["name"] for opt in options],
        "correct_index": [opt["name"] for opt in options].index(correct["name"])
    }

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    active_games.pop(user_id, None)
    await message.answer(
        "🎯 привет! это игра *угадай флаг страны*\n"
        "📈 эта игра поможет тебе выучить флаги всего мира\n\n"
        "/help - прочитать правила игры\n"
        "/start - вернуться в это же меню\n\n"
        "выбери режим ⬇️",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "*правила игры угадай флаг 🏴‍☠️*\n\n"
        "1) у тебя есть на выбор в главном меню 3 режима\n"
        "2) режим *классический* - игра не закончится, пока вы не потратите свои жизни\n"
        "3) режим *на время* - игра закончится после 30 секунд, цель - угадать наибольшее кол-во флагов\n"
        "4) режим *бесконечность* - игра будет продолжаться, пока вы сами не захотите её завершить\n"
        "5) во всех режимах появляется эмодзи-флаг какой-либо страны, ваша задача - выбрать из 4 вариантов ответа правильный\n\n"
        "*приятной игры*🙏🏻🫶🏻",
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith(f"{CB_START_GAME}:"))
async def start_game(callback: types.CallbackQuery):
    await callback.answer()
    _, mode = callback.data.split(":")
    session = GameSession(user_id=callback.from_user.id, mode=mode)
    if mode == MODE_TIMED: session.time_left = 30
    active_games[callback.from_user.id] = session
    await callback.message.edit_text(
        "🎲 игра началась! отвечай на вопросы",
        reply_markup=None
    )
    await send_next_question(callback.message, session, is_first=True)

async def send_next_question(message: types.Message, session: GameSession, is_first: bool = False):
    try:
        question = generate_question()
        session.current_question = question
        session.question_count += 1
        keyboard = get_answer_keyboard(
            question["id"], 
            question["options"], 
            session.mode
        )
        lines = [f"💻 *режим - * {session.mode}\n❓ *вопрос* №{session.question_count}"]
        
        if session.mode == MODE_CLASSIC:
            lines.append(f"❤️ *жизни - * {session.lives}\n💯 *очки - * {session.score}")
        elif session.mode == MODE_TIMED:
            lines.append(f"⏰*время* 00:{session.time_left}")
        
        caption = "\n".join(lines)
        
        if is_first:
            emoji_msg = await message.answer(question['emoji'])
            session.emoji_message_id = emoji_msg.message_id
            await message.answer(caption, reply_markup=keyboard, parse_mode="Markdown")
        else:
            if session.emoji_message_id:
                try:
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=session.emoji_message_id,
                        text=question['emoji']
                    )
                except:
                    pass
            await message.edit_text(caption, reply_markup=keyboard, parse_mode="Markdown")
        
        if session.mode == MODE_TIMED and session.user_id not in game_timers:
            task = asyncio.create_task(timer_task(session.user_id, message))
            game_timers[session.user_id] = task
        
    except Exception as e:
        await message.answer(f"❌ ошибка: {e}")

async def timer_task(user_id: int, message: types.Message):
    try:
        while True:
            await asyncio.sleep(1)
            
            if user_id not in active_games: break
            session = active_games[user_id]
            if session.mode != MODE_TIMED: break
            session.time_left -= 1
            
            if session.time_left <= 0:
                await message.answer(
                    f"⏰ время вышло!\n\n"
                    f"*итоговый счёт* - {session.score}",
                    reply_markup=get_game_over_keyboard(),
                    parse_mode="Markdown"
                )
                del active_games[user_id]
                if user_id in game_timers: del game_timers[user_id]
                break
                
    except asyncio.CancelledError: pass
    except Exception as e: print(f"{DBG} ошибка таймера: {e}")

@router.callback_query(F.data.startswith(f"{CB_ANSWER}:"))
async def process_answer(callback: types.CallbackQuery):
    _, question_id, answer_idx, mode = callback.data.split(":")
    answer_idx = int(answer_idx)
    user_id = callback.from_user.id
    
    if user_id not in active_games:
        await callback.answer("игра не найдена!", show_alert=True)
        return
    
    session = active_games[user_id]
    
    if session.current_question["id"] != question_id:
        await callback.answer("вопрос устарел!", show_alert=True)
        return
    
    if session.mode == MODE_TIMED and user_id in game_timers:
        game_timers[user_id].cancel()
        del game_timers[user_id]
    
    is_correct = answer_idx == session.current_question["correct_index"]
    
    if is_correct:
        session.score += 1
        result = f"✅ правильно! это {session.current_question['correct']}"
    else:
        if session.mode == MODE_CLASSIC: session.lives -= 1
        result = f"❌ неправильно! это {session.current_question['correct']}"
    
    await callback.answer(result)
    
    if not session.is_active():
        await callback.message.answer(
            f"🎲 игра окончена!\n\nсчёт: {session.score}",
            reply_markup=get_game_over_keyboard()
        )
        del active_games[user_id]
    else: await send_next_question(callback.message, session)

@router.callback_query(F.data.startswith(f"{CB_MENU}:"))
async def process_menu(callback: types.CallbackQuery):
    await callback.answer()
    action = callback.data.split(":")[1]
    
    if action == "main":
        await callback.message.answer("вы вернулись в главное меню!\nвыбери режим⬇️", reply_markup=get_main_menu())
    elif action == "play_again":
        await callback.message.answer("выбери режим⬇️", reply_markup=get_main_menu())
    elif action == "end_game":
        user_id = callback.from_user.id
        if user_id in active_games:
            session = active_games[user_id]
            await callback.message.answer(
                f"🏁 ты завершил игру!\n\n*счёт - *{session.score}",
                reply_markup=get_game_over_keyboard(),
                parse_mode="Markdown"
            )
            del active_games[user_id]
            if user_id in game_timers:
                game_timers[user_id].cancel()
                del game_timers[user_id]

async def main():
    print(f"{DBG} запуск бота 'угадай флаг'")
    if not await load_countries():
        print(f"\n{DBG} не удалось загрузить данные")
        return
    
    print(f"\n{DBG} бот готов к работе!\n")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())