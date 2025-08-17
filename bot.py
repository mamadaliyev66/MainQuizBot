# import json
# import random
# import asyncio
# import time
# import logging
# from aiogram import Bot, Dispatcher, types, F
# from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
# from aiogram.filters import Command
# from typing import Dict, Optional
# import weakref
# import gc

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# API_TOKEN = "8391048862:AAHFv9X4L4CGxpvJs_6uvQp-Mb5MVMvaddo"

# bot = Bot(token=API_TOKEN)
# dp = Dispatcher()

# # Load questions from JSON (load once at startup)
# try:
#     with open("questions.json", "r", encoding="utf-8") as f:
#         data = json.load(f)
#     logger.info(f"Loaded {len(data.get('categories', []))} categories")
# except FileNotFoundError:
#     logger.error("questions.json not found!")
#     data = {"categories": []}
# except json.JSONDecodeError:
#     logger.error("Invalid JSON in questions.json!")
#     data = {"categories": []}

# # Store user sessions with memory management
# user_sessions: Dict[int, dict] = {}
# timer_tasks: Dict[int, asyncio.Task] = {}

# # Configuration
# MAX_SESSIONS = 1000  # Maximum concurrent sessions
# SESSION_TIMEOUT = 3600  # 1 hour timeout for inactive sessions

# class SessionManager:
#     @staticmethod
#     def cleanup_expired_sessions():
#         """Remove expired sessions to free memory"""
#         current_time = time.time()
#         expired_users = []
        
#         for user_id, session in user_sessions.items():
#             if current_time - session.get('last_activity', 0) > SESSION_TIMEOUT:
#                 expired_users.append(user_id)
        
#         for user_id in expired_users:
#             SessionManager.remove_session(user_id)
#             logger.info(f"Removed expired session for user {user_id}")
    
#     @staticmethod
#     def remove_session(user_id: int):
#         """Safely remove a user session and cancel timers"""
#         # Cancel timer task if exists
#         if user_id in timer_tasks:
#             task = timer_tasks[user_id]
#             if not task.done():
#                 task.cancel()
#             del timer_tasks[user_id]
        
#         # Remove session
#         if user_id in user_sessions:
#             del user_sessions[user_id]
        
#         # Force garbage collection periodically
#         if len(user_sessions) % 100 == 0:
#             gc.collect()
    
#     @staticmethod
#     def update_activity(user_id: int):
#         """Update last activity timestamp"""
#         if user_id in user_sessions:
#             user_sessions[user_id]['last_activity'] = time.time()
    
#     @staticmethod
#     def check_session_limit():
#         """Check if we're approaching session limits"""
#         if len(user_sessions) >= MAX_SESSIONS:
#             # Clean up old sessions
#             SessionManager.cleanup_expired_sessions()
#             if len(user_sessions) >= MAX_SESSIONS:
#                 return False
#         return True

# # Periodic cleanup task
# async def periodic_cleanup():
#     """Run cleanup every 10 minutes"""
#     while True:
#         try:
#             await asyncio.sleep(600)  # 10 minutes
#             SessionManager.cleanup_expired_sessions()
#             logger.info(f"Active sessions: {len(user_sessions)}, Active timers: {len(timer_tasks)}")
#         except Exception as e:
#             logger.error(f"Cleanup error: {e}")

# # Middleware to check session limits
# async def check_user_limit(user_id: int):
#     if user_id not in user_sessions and not SessionManager.check_session_limit():
#         return False
#     SessionManager.update_activity(user_id)
#     return True

# # Start command
# @dp.message(Command("start"))
# async def start_quiz(message: Message):
#     if not await check_user_limit(message.from_user.id):
#         await message.answer("⚠️ Bot is currently at capacity. Please try again later.")
#         return
    
#     # Clean up any existing session for this user
#     SessionManager.remove_session(message.from_user.id)
    
#     keyboard = InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text=cat["category"], callback_data=f"cat_{cat['category']}")]
#         for cat in data["categories"]
#     ])
    
#     await message.answer("📚 Choose a category:", reply_markup=keyboard)
#     logger.info(f"User {message.from_user.id} started quiz selection")

# # Category chosen
# @dp.callback_query(F.data.startswith("cat_"))
# async def choose_difficulty(callback: CallbackQuery):
#     if not await check_user_limit(callback.from_user.id):
#         await callback.answer("⚠️ Bot is currently at capacity. Please try again later.")
#         return
    
#     category = callback.data.split("_", 1)[1]
#     user_sessions[callback.from_user.id] = {
#         "category": category,
#         "last_activity": time.time()
#     }

#     keyboard = InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text=f"Difficulty {level}", callback_data=f"diff_{level}")]
#         for level in ["1", "2", "3"]
#     ])
#     await callback.message.answer(f"⚡ Category: {category}\nChoose difficulty:", reply_markup=keyboard)
#     await callback.answer()

# # Difficulty chosen
# @dp.callback_query(F.data.startswith("diff_"))
# async def choose_count(callback: CallbackQuery):
#     if callback.from_user.id not in user_sessions:
#         await callback.answer("❌ Session expired. Please start over with /start")
#         return
    
#     SessionManager.update_activity(callback.from_user.id)
    
#     level = callback.data.split("_")[1]
#     user_sessions[callback.from_user.id]["difficulty"] = level

#     category = user_sessions[callback.from_user.id]["category"]
#     try:
#         category_data = next(cat for cat in data["categories"] if cat["category"] == category)
#         questions = category_data["difficulty_levels"][level]
#     except (KeyError, StopIteration):
#         await callback.answer("❌ Category or difficulty not found. Please start over.")
#         SessionManager.remove_session(callback.from_user.id)
#         return

#     user_sessions[callback.from_user.id]["questions_pool"] = questions

#     await callback.message.answer(f"📊 Available questions: {len(questions)}\nHow many do you want to solve? (send a number)")
#     await callback.answer()

# # Number of questions
# @dp.message(lambda message: message.from_user.id in user_sessions and "questions_pool" in user_sessions[message.from_user.id] and "count" not in user_sessions[message.from_user.id])
# async def set_question_count(message: Message):
#     if not await check_user_limit(message.from_user.id):
#         return
    
#     try:
#         count = int(message.text)
#     except:
#         return await message.answer("❌ Please send a number")

#     session = user_sessions[message.from_user.id]
#     total_available = len(session["questions_pool"])
#     if count < 1 or count > total_available:
#         return await message.answer(f"❌ Must be between 1 and {total_available}")

#     session["count"] = count
#     await message.answer("⏳ How many minutes do you want for this test? (send a number)")

# # Timer
# @dp.message(lambda message: message.from_user.id in user_sessions and "count" in user_sessions[message.from_user.id] and "timer" not in user_sessions[message.from_user.id])
# async def set_timer(message: Message):
#     if not await check_user_limit(message.from_user.id):
#         return
    
#     try:
#         minutes = int(message.text)
#         if minutes < 1 or minutes > 120:  # Max 2 hours
#             return await message.answer("❌ Timer must be between 1 and 120 minutes")
#     except:
#         return await message.answer("❌ Please send a number")

#     session = user_sessions[message.from_user.id]
#     session.update({
#         "timer": minutes * 60,
#         "score": 0,
#         "answered": 0,
#         "quiz": random.sample(session["questions_pool"], session["count"]),
#         "current_index": 0,
#         "answers": [],
#         "start_time": time.time(),
#         "last_activity": time.time()
#     })

#     await message.answer(f"✅ Test started!\n⏳ You have {minutes} minutes.\nGood luck 🍀")

#     # Create and store timer task
#     timer_tasks[message.from_user.id] = asyncio.create_task(
#         run_timer(message.chat.id, message.from_user.id)
#     )
#     await send_question(message.chat.id, message.from_user.id)

# # Timer background task with error handling
# async def run_timer(chat_id, user_id):
#     try:
#         if user_id not in user_sessions:
#             return
        
#         await asyncio.sleep(user_sessions[user_id]["timer"])
        
#         if user_id in user_sessions:  # session still active
#             await finish_quiz(chat_id, user_id, "⏰ Time is up!")
#     except asyncio.CancelledError:
#         logger.info(f"Timer cancelled for user {user_id}")
#     except Exception as e:
#         logger.error(f"Timer error for user {user_id}: {e}")
#     finally:
#         # Clean up timer task reference
#         if user_id in timer_tasks:
#             del timer_tasks[user_id]

# async def send_question(chat_id, user_id):
#     if user_id not in user_sessions:
#         return
    
#     session = user_sessions[user_id]
#     SessionManager.update_activity(user_id)

#     if session["current_index"] >= session["count"]:
#         await finish_quiz(chat_id, user_id, "🏁 Test finished!")
#         return

#     q = session["quiz"][session["current_index"]]

#     answers = [q["true_answer"], q["answer_1"], q["answer_2"], q["answer_3"]]
#     random.shuffle(answers)

#     session["current_question"] = {
#         "question": q["question"],
#         "true_answer": q["true_answer"],
#         "answers": answers
#     }

#     keyboard = InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text=ans, callback_data=f"ans_{i}")]
#         for i, ans in enumerate(answers)
#     ] + [
#         [InlineKeyboardButton(text="❌ Cancel Test", callback_data="cancel_test")]
#     ])

#     question_num = session["current_index"] + 1
#     total_questions = session["count"]
    
#     try:
#         await bot.send_message(chat_id, f"❓ Question {question_num}/{total_questions}:\n\n{q['question']}", reply_markup=keyboard)
#     except Exception as e:
#         logger.error(f"Failed to send question to user {user_id}: {e}")
#         SessionManager.remove_session(user_id)

# # Handle answers
# @dp.callback_query(F.data.startswith("ans_"))
# async def store_answer(callback: CallbackQuery):
#     user_id = callback.from_user.id
    
#     if user_id not in user_sessions:
#         await callback.answer("❌ Session expired. Please start over with /start")
#         return
    
#     SessionManager.update_activity(user_id)
    
#     try:
#         index = int(callback.data.split("_")[1])
#         session = user_sessions[user_id]
#         q = session["current_question"]

#         chosen = q["answers"][index]
#         correct = q["true_answer"]

#         session["answers"].append({
#             "question": q["question"],
#             "chosen": chosen,
#             "correct": correct,
#             "is_correct": chosen == correct
#         })

#         if chosen == correct:
#             session["score"] += 1

#         session["answered"] += 1
#         session["current_index"] += 1

#         await callback.message.delete()
#         await send_question(callback.message.chat.id, user_id)
#         await callback.answer()
        
#     except Exception as e:
#         logger.error(f"Error processing answer for user {user_id}: {e}")
#         await callback.answer("❌ An error occurred. Please try again.")

# # Cancel test
# @dp.callback_query(F.data == "cancel_test")
# async def cancel_test(callback: CallbackQuery):
#     await finish_quiz(callback.message.chat.id, callback.from_user.id, "❌ Test cancelled.")
#     await callback.answer()

# # End quiz and show results
# async def finish_quiz(chat_id, user_id, reason):
#     if user_id not in user_sessions:
#         return
    
#     try:
#         session = user_sessions[user_id]
        
#         # Calculate time spent
#         end_time = time.time()
#         time_spent = end_time - session["start_time"]
#         minutes_spent = int(time_spent // 60)
#         seconds_spent = int(time_spent % 60)

#         # Create results message
#         percentage = (session["score"] / session["answered"] * 100) if session["answered"] > 0 else 0
        
#         result_text = f"{reason}\n\n📊 **Results:**\n"
#         result_text += f"✅ Correct: {session['score']}/{session['answered']} ({percentage:.1f}%)\n"
#         result_text += f"⏱ Time spent: {minutes_spent}m {seconds_spent}s\n\n"

#         # Show wrong answers
#         wrong_answers = [ans for ans in session["answers"] if not ans["is_correct"]]
        
#         if wrong_answers:
#             result_text += "❌ **Wrong Answers:**\n\n"
#             for i, wrong in enumerate(wrong_answers, 1):
#                 if len(result_text) > 3500:  # Prevent message from being too long
#                     result_text += f"... and {len(wrong_answers) - i + 1} more wrong answers"
#                     break
#                 result_text += f"{i}. **Q:** {wrong['question'][:100]}{'...' if len(wrong['question']) > 100 else ''}\n"
#                 result_text += f"   Your answer: ❌ {wrong['chosen']}\n"
#                 result_text += f"   Correct answer: ✅ {wrong['correct']}\n\n"
#         else:
#             result_text += "🎉 Perfect score! No wrong answers!\n"

#         # Add restart option
#         keyboard = InlineKeyboardMarkup(inline_keyboard=[
#             [InlineKeyboardButton(text="🔄 Take Another Test", callback_data="restart")]
#         ])
        
#         await bot.send_message(chat_id, result_text, reply_markup=keyboard)
#         logger.info(f"Quiz completed for user {user_id}: {session['score']}/{session['answered']}")
        
#     except Exception as e:
#         logger.error(f"Error finishing quiz for user {user_id}: {e}")
#         await bot.send_message(chat_id, "❌ An error occurred while processing results.")
#     finally:
#         # Always clean up session
#         SessionManager.remove_session(user_id)

# # Restart handler
# @dp.callback_query(F.data == "restart")
# async def restart_quiz(callback: CallbackQuery):
#     # Clean up any existing session
#     SessionManager.remove_session(callback.from_user.id)
    
#     keyboard = InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text=cat["category"], callback_data=f"cat_{cat['category']}")]
#         for cat in data["categories"]
#     ])
#     await callback.message.answer("📚 Choose a category:", reply_markup=keyboard)
#     await callback.answer()

# # Add stats command for monitoring
# @dp.message(Command("stats"))
# async def show_stats(message: Message):
#     # Replace YOUR_ADMIN_USER_ID with your actual user ID
#     if message.from_user.id == 123456789:  # Replace with your user ID
#         stats_text = f"📊 **Bot Statistics:**\n"
#         stats_text += f"Active sessions: {len(user_sessions)}\n"
#         stats_text += f"Active timers: {len(timer_tasks)}\n"
#         stats_text += f"Categories loaded: {len(data.get('categories', []))}\n"
#         await message.answer(stats_text)

# # Main function to run the bot
# async def main():
#     # Start cleanup task
#     asyncio.create_task(periodic_cleanup())
    
#     # Start polling
#     logger.info("Starting bot...")
#     await dp.start_polling(bot)

# if __name__ == "__main__":
#     asyncio.run(main())





#  Version 2 


import json
import random
import asyncio
import time
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.filters import Command
from typing import Dict, Optional
import weakref
import gc
from datetime import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = "8391048862:AAHFv9X4L4CGxpvJs_6uvQp-Mb5MVMvaddo"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Load questions from JSON (load once at startup)
try:
    with open("questions.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Loaded {len(data.get('categories', []))} categories")
except FileNotFoundError:
    logger.error("questions.json not found!")
    data = {"categories": []}
except json.JSONDecodeError:
    logger.error("Invalid JSON in questions.json!")
    data = {"categories": []}

# Store user sessions with memory management
user_sessions: Dict[int, dict] = {}
timer_tasks: Dict[int, asyncio.Task] = {}

# Configuration
MAX_SESSIONS = 1000  # Maximum concurrent sessions
SESSION_TIMEOUT = 3600  # 1 hour timeout for inactive sessions
ADMIN_USER_ID = 2112429027  # Your Telegram ID

# User monitoring functions
def load_user_data():
    """Load user data from JSON file"""
    try:
        if os.path.exists("users.json"):
            with open("users.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading user data: {e}")
    return {"users": [], "total_users": 0}

def save_user_data(user_data):
    """Save user data to JSON file"""
    try:
        with open("users.json", "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

def add_user_info(user: types.User):
    """Add or update user information"""
    user_data = load_user_data()
    
    # Check if user already exists
    existing_user = None
    for i, u in enumerate(user_data["users"]):
        if u["user_id"] == user.id:
            existing_user = i
            break
    
    user_info = {
        "user_id": user.id,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "username": user.username or "",
        "language_code": user.language_code or "",
        "is_premium": getattr(user, 'is_premium', False),
        "first_seen": datetime.now().isoformat() if existing_user is None else user_data["users"][existing_user]["first_seen"],
        "last_seen": datetime.now().isoformat(),
        "total_visits": user_data["users"][existing_user]["total_visits"] + 1 if existing_user is not None else 1
    }
    
    if existing_user is not None:
        user_data["users"][existing_user] = user_info
    else:
        user_data["users"].append(user_info)
        user_data["total_users"] = len(user_data["users"])
    
    save_user_data(user_data)
    return user_info

class SessionManager:
    @staticmethod
    def cleanup_expired_sessions():
        """Remove expired sessions to free memory"""
        current_time = time.time()
        expired_users = []
        
        for user_id, session in user_sessions.items():
            if current_time - session.get('last_activity', 0) > SESSION_TIMEOUT:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            SessionManager.remove_session(user_id)
            logger.info(f"Removed expired session for user {user_id}")
    
    @staticmethod
    def remove_session(user_id: int):
        """Safely remove a user session and cancel timers"""
        # Cancel timer task if exists
        if user_id in timer_tasks:
            task = timer_tasks[user_id]
            if not task.done():
                task.cancel()
            del timer_tasks[user_id]
        
        # Remove session
        if user_id in user_sessions:
            del user_sessions[user_id]
        
        # Force garbage collection periodically
        if len(user_sessions) % 100 == 0:
            gc.collect()
    
    @staticmethod
    def update_activity(user_id: int):
        """Update last activity timestamp"""
        if user_id in user_sessions:
            user_sessions[user_id]['last_activity'] = time.time()
    
    @staticmethod
    def check_session_limit():
        """Check if we're approaching session limits"""
        if len(user_sessions) >= MAX_SESSIONS:
            # Clean up old sessions
            SessionManager.cleanup_expired_sessions()
            if len(user_sessions) >= MAX_SESSIONS:
                return False
        return True

# Periodic cleanup task
async def periodic_cleanup():
    """Run cleanup every 10 minutes"""
    while True:
        try:
            await asyncio.sleep(600)  # 10 minutes
            SessionManager.cleanup_expired_sessions()
            logger.info(f"Active sessions: {len(user_sessions)}, Active timers: {len(timer_tasks)}")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

# Middleware to check session limits
async def check_user_limit(user_id: int):
    if user_id not in user_sessions and not SessionManager.check_session_limit():
        return False
    SessionManager.update_activity(user_id)
    return True

# Start command - with user monitoring
@dp.message(Command("start"))
async def start_quiz(message: Message):
    # Add user information to monitoring
    user_info = add_user_info(message.from_user)
    logger.info(f"User {message.from_user.id} ({user_info['first_name']} {user_info['last_name']}) started bot")
    
    if not await check_user_limit(message.from_user.id):
        await message.answer("⚠️ Bot hozirda bandligi sababli, iltimos keyinroq urinib ko'ring.")
        return
    
    # Clean up any existing session for this user
    SessionManager.remove_session(message.from_user.id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cat["category"], callback_data=f"cat_{cat['category']}")]
        for cat in data["categories"]
    ])
    
    welcome_text = f"Assalomu alaykum {message.from_user.first_name}! 👋\n\n  Yordam uchun Jo'nating - /help \n\n"
    welcome_text += "📚 Test kategoriyasini tanlang:"
    
    await message.answer(welcome_text, reply_markup=keyboard)

# Category chosen
@dp.callback_query(F.data.startswith("cat_"))
async def choose_difficulty(callback: CallbackQuery):
    if not await check_user_limit(callback.from_user.id):
        await callback.answer("⚠️ Bot hozirda bandligi sababli, iltimos keyinroq urinib ko'ring.")
        return
    
    category = callback.data.split("_", 1)[1]
    user_sessions[callback.from_user.id] = {
        "category": category,
        "last_activity": time.time()
    }

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{level}-daraja", callback_data=f"diff_{level}")]
        for level in ["1", "2", "3"]
    ])
    await callback.message.answer(f"⚡ Kategoriya: {category}\nQiyinlik darajasini tanlang:", reply_markup=keyboard)
    await callback.answer()

# Difficulty chosen
@dp.callback_query(F.data.startswith("diff_"))
async def choose_count(callback: CallbackQuery):
    if callback.from_user.id not in user_sessions:
        await callback.answer("❌ Sessiya tugagan. /start buyrug'i bilan qaytadan boshlang")
        return
    
    SessionManager.update_activity(callback.from_user.id)
    
    level = callback.data.split("_")[1]
    user_sessions[callback.from_user.id]["difficulty"] = level

    category = user_sessions[callback.from_user.id]["category"]
    try:
        category_data = next(cat for cat in data["categories"] if cat["category"] == category)
        questions = category_data["difficulty_levels"][level]
    except (KeyError, StopIteration):
        await callback.answer("❌ Kategoriya yoki daraja topilmadi. Qaytadan boshlang.")
        SessionManager.remove_session(callback.from_user.id)
        return

    user_sessions[callback.from_user.id]["questions_pool"] = questions

    await callback.message.answer(f"📊 Mavjud savollar soni: {len(questions)}\nNechta savol yechmoqchisiz? (raqam kiriting)")
    await callback.answer()

# Number of questions
@dp.message(lambda message: message.from_user.id in user_sessions and "questions_pool" in user_sessions[message.from_user.id] and "count" not in user_sessions[message.from_user.id])
async def set_question_count(message: Message):
    if not await check_user_limit(message.from_user.id):
        return
    
    try:
        count = int(message.text)
    except:
        return await message.answer("❌ Iltimos, raqam kiriting")

    session = user_sessions[message.from_user.id]
    total_available = len(session["questions_pool"])
    if count < 1 or count > total_available:
        return await message.answer(f"❌ {1} dan {total_available} gacha raqam kiriting")

    session["count"] = count
    await message.answer("⏳ Test uchun necha daqiqa vaqt ajratasiz? (raqam kiriting)")

# Timer
@dp.message(lambda message: message.from_user.id in user_sessions and "count" in user_sessions[message.from_user.id] and "timer" not in user_sessions[message.from_user.id])
async def set_timer(message: Message):
    if not await check_user_limit(message.from_user.id):
        return
    
    try:
        minutes = int(message.text)
        if minutes < 1 or minutes > 120:  # Max 2 hours
            return await message.answer("❌ Vaqt 1 dan 120 daqiqagacha bo'lishi kerak")
    except:
        return await message.answer("❌ Iltimos, raqam kiriting")

    session = user_sessions[message.from_user.id]
    session.update({
        "timer": minutes * 60,
        "score": 0,
        "answered": 0,
        "quiz": random.sample(session["questions_pool"], session["count"]),
        "current_index": 0,
        "answers": [],
        "start_time": time.time(),
        "last_activity": time.time()
    })

    await message.answer(f"✅ Test boshlandi!\n⏳ Sizda {minutes} daqiqa vaqt bor.\nOmad yor bo'lsin! 🍀")

    # Create and store timer task
    timer_tasks[message.from_user.id] = asyncio.create_task(
        run_timer(message.chat.id, message.from_user.id)
    )
    await send_question(message.chat.id, message.from_user.id)

# Timer background task with error handling
async def run_timer(chat_id, user_id):
    try:
        if user_id not in user_sessions:
            return
        
        await asyncio.sleep(user_sessions[user_id]["timer"])
        
        if user_id in user_sessions:  # session still active
            await finish_quiz(chat_id, user_id, "⏰ Vaqt tugadi!")
    except asyncio.CancelledError:
        logger.info(f"Timer cancelled for user {user_id}")
    except Exception as e:
        logger.error(f"Timer error for user {user_id}: {e}")
    finally:
        # Clean up timer task reference
        if user_id in timer_tasks:
            del timer_tasks[user_id]

async def send_question(chat_id, user_id):
    if user_id not in user_sessions:
        return
    
    session = user_sessions[user_id]
    SessionManager.update_activity(user_id)

    if session["current_index"] >= session["count"]:
        await finish_quiz(chat_id, user_id, "🏁 Test yakunlandi!")
        return

    q = session["quiz"][session["current_index"]]

    answers = [q["true_answer"], q["answer_1"], q["answer_2"], q["answer_3"]]
    random.shuffle(answers)

    session["current_question"] = {
        "question": q["question"],
        "true_answer": q["true_answer"],
        "answers": answers
    }

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ans, callback_data=f"ans_{i}")]
        for i, ans in enumerate(answers)
    ] + [
        [InlineKeyboardButton(text="❌ Testni bekor qilish", callback_data="cancel_test")]
    ])

    question_num = session["current_index"] + 1
    total_questions = session["count"]
    
    try:
        await bot.send_message(chat_id, f"❓ Savol {question_num}/{total_questions}:\n\n{q['question']}", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Failed to send question to user {user_id}: {e}")
        SessionManager.remove_session(user_id)

# Handle answers
@dp.callback_query(F.data.startswith("ans_"))
async def store_answer(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in user_sessions:
        await callback.answer("❌ Sessiya tugagan. /start buyrug'i bilan qaytadan boshlang")
        return
    
    SessionManager.update_activity(user_id)
    
    try:
        index = int(callback.data.split("_")[1])
        session = user_sessions[user_id]
        q = session["current_question"]

        chosen = q["answers"][index]
        correct = q["true_answer"]

        session["answers"].append({
            "question": q["question"],
            "chosen": chosen,
            "correct": correct,
            "is_correct": chosen == correct
        })

        if chosen == correct:
            session["score"] += 1

        session["answered"] += 1
        session["current_index"] += 1

        await callback.message.delete()
        await send_question(callback.message.chat.id, user_id)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error processing answer for user {user_id}: {e}")
        await callback.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")

# Cancel test
@dp.callback_query(F.data == "cancel_test")
async def cancel_test(callback: CallbackQuery):
    await finish_quiz(callback.message.chat.id, callback.from_user.id, "❌ Test bekor qilindi.")
    await callback.answer()

# End quiz and show results
async def finish_quiz(chat_id, user_id, reason):
    if user_id not in user_sessions:
        return
    
    try:
        session = user_sessions[user_id]
        
        # Calculate time spent
        end_time = time.time()
        time_spent = end_time - session["start_time"]
        minutes_spent = int(time_spent // 60)
        seconds_spent = int(time_spent % 60)

        # Create results message
        percentage = (session["score"] / session["answered"] * 100) if session["answered"] > 0 else 0
        
        result_text = f"{reason}\n\n📊 **Natijalar:**\n"
        result_text += f"✅ To'g'ri javoblar: {session['score']}/{session['answered']} ({percentage:.1f}%)\n"
        result_text += f"⏱ Sarflangan vaqt: {minutes_spent}d {seconds_spent}s\n\n"

        # Show wrong answers
        wrong_answers = [ans for ans in session["answers"] if not ans["is_correct"]]
        
        if wrong_answers:
            result_text += "❌ **Noto'g'ri javoblar:**\n\n"
            for i, wrong in enumerate(wrong_answers, 1):
                if len(result_text) > 3500:  # Prevent message from being too long
                    result_text += f"... va yana {len(wrong_answers) - i + 1}ta noto'g'ri javob"
                    break
                result_text += f"{i}. **S:** {wrong['question'][:100]}{'...' if len(wrong['question']) > 100 else ''}\n"
                result_text += f"   Sizning javobingiz: ❌ {wrong['chosen']}\n"
                result_text += f"   To'g'ri javob: ✅ {wrong['correct']}\n\n"
        else:
            result_text += "🎉 Ajoyib! Barcha javoblar to'g'ri!\n"

        # Add restart option
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Boshqa test yechish", callback_data="restart")]
        ])
        
        await bot.send_message(chat_id, result_text, reply_markup=keyboard)
        logger.info(f"Quiz completed for user {user_id}: {session['score']}/{session['answered']}")
        
    except Exception as e:
        logger.error(f"Error finishing quiz for user {user_id}: {e}")
        await bot.send_message(chat_id, "❌ Natijalarni ko'rsatishda xatolik yuz berdi.")
    finally:
        # Always clean up session
        SessionManager.remove_session(user_id)

# Restart handler
@dp.callback_query(F.data == "restart")
async def restart_quiz(callback: CallbackQuery):
    # Clean up any existing session
    SessionManager.remove_session(callback.from_user.id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cat["category"], callback_data=f"cat_{cat['category']}")]
        for cat in data["categories"]
    ])
    await callback.message.answer("📚 Test kategoriyasini tanlang:", reply_markup=keyboard)
    await callback.answer()

# Stats command for admin monitoring
@dp.message(Command("stats"))
async def show_stats(message: Message):
    if message.from_user.id == ADMIN_USER_ID:
        user_data = load_user_data()
        stats_text = f"📊 **Bot Statistikasi:**\n"
        stats_text += f"Faol sessiyalar: {len(user_sessions)}\n"
        stats_text += f"Faol taymerlar: {len(timer_tasks)}\n"
        stats_text += f"Yuklangan kategoriyalar: {len(data.get('categories', []))}\n"
        stats_text += f"Jami foydalanuvchilar: {user_data.get('total_users', 0)}\n"
        stats_text += f"Bugungi yangi foydalanuvchilar: {len([u for u in user_data.get('users', []) if u.get('first_seen', '').startswith(datetime.now().strftime('%Y-%m-%d'))])}"
        await message.answer(stats_text)

# User list command for admin
@dp.message(Command("users"))
async def show_users(message: Message):
    if message.from_user.id == ADMIN_USER_ID:
        user_data = load_user_data()
        users = user_data.get('users', [])
        
        if not users:
            await message.answer("Hech qanday foydalanuvchi ma'lumoti topilmadi.")
            return
        
        # Sort users by last seen (most recent first)
        users.sort(key=lambda x: x.get('last_seen', ''), reverse=True)
        
        # Show last 20 users
        users_text = "👥 **So'nggi foydalanuvchilar:**\n\n"
        for i, user in enumerate(users[:20], 1):
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            username = f"@{user.get('username')}" if user.get('username') else "Username yo'q"
            last_seen = user.get('last_seen', '')[:19] if user.get('last_seen') else 'Noma\'lum'
            visits = user.get('total_visits', 0)
            
            users_text += f"{i}. {name}\n"
            users_text += f"   ID: {user.get('user_id')}\n"
            users_text += f"   Username: {username}\n"
            users_text += f"   So'nggi tashrif: {last_seen}\n"
            users_text += f"   Tashrif soni: {visits}\n\n"
        
        if len(users_text) > 4000:
            # Split into multiple messages
            parts = users_text.split('\n\n')
            current_msg = "👥 **So'nggi foydalanuvchilar:**\n\n"
            for part in parts:
                if len(current_msg + part + '\n\n') > 4000:
                    await message.answer(current_msg)
                    current_msg = part + '\n\n'
                else:
                    current_msg += part + '\n\n'
            if current_msg.strip():
                await message.answer(current_msg)
        else:
            await message.answer(users_text)

# Export users command for admin
@dp.message(Command("export"))
async def export_users(message: Message):
    if message.from_user.id == ADMIN_USER_ID:
        try:
            # Send the users.json file
            if os.path.exists("users.json"):
                document = types.FSInputFile("users.json")
                await message.answer_document(
                    document,
                    caption="📄 Foydalanuvchilar ma'lumotlari JSON formatida"
                )
            else:
                await message.answer("users.json fayli topilmadi.")
        except Exception as e:
            await message.answer(f"Faylni yuborishda xatolik: {str(e)}")

# Help command
@dp.message(Command("help"))
async def show_help(message: Message):
    help_text = """
🤖 **Bot haqida:**
Bu bot turli mavzularda test yechish uchun mo'ljallangan.

📝 **Qanday foydalanish:**
1. /start - Botni ishga tushirish
2. Kategoriyani tanlash
3. Qiyinlik darajasini tanlash
4. Savollar sonini kiriting
5. Vaqt belgilash
6. Testni yechish

⚙️ **Buyruqlar:**
/start - Botni qayta ishga tushirish
/help - Yordam
"""
    
    if message.from_user.id == ADMIN_USER_ID:
        help_text += """
👨‍💼 **Admin buyruqlar:**
/stats - Bot statistikasi
/users - Foydalanuvchilar ro'yxati
/export - Foydalanuvchilar ma'lumotlarini yuklash
"""
    
    await message.answer(help_text)

# Main function to run the bot
async def main():
    # Start cleanup task
    asyncio.create_task(periodic_cleanup())
    
    # Start polling
    logger.info("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
