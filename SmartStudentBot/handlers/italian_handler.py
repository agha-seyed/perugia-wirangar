# handlers/italian_handler.py
# نسخه نهایی و جامع (Pro Version) - دسامبر 2025
# شامل: درس‌ها و گرامر سطح‌بندی شده، فلش‌کارت هوشمند با صدا، آزمون تعاملی

import json
import os
import random
from pathlib import Path

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

# کتابخانه تبدیل متن به صدا
from gtts import gTTS

router = Router()

# ---------------------------------------------------------
# 1. تنظیمات و بارگذاری داده‌ها (Data Loading)
# ---------------------------------------------------------

# استفاده از Pathlib برای آدرس‌دهی امن در ویندوز/لینوکس/داکر
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "italian"

def load_json(file_name):
    """خواندن فایل‌های JSON با مدیریت خطا"""
    path = DATA_DIR / file_name
    if not path.exists():
        print(f"⚠️ فایل دیتابیس پیدا نشد: {path}")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ خطا در خواندن {file_name}: {e}")
        return []

# بارگذاری تمام دیتابیس‌ها در حافظه
lessons_db = load_json("lessons.json")
vocab_db = load_json("vocab.json")
quizzes_db = load_json("quizzes.json")
grammar_db = load_json("grammar.json")

# ---------------------------------------------------------
# 2. مدیریت وضعیت‌ها (States)
# ---------------------------------------------------------

class ItalianState(StatesGroup):
    # وضعیت‌های مربوط به درس
    selecting_lesson_level = State()
    viewing_lesson = State()
    
    # وضعیت‌های مربوط به گرامر
    selecting_grammar_level = State()
    viewing_grammar = State()
    
    # وضعیت‌های مربوط به فلش‌کارت
    viewing_flashcard = State()
    
    # وضعیت‌های مربوط به آزمون
    in_quiz = State()

try:
    from handlers.cmd_start import get_user_lang, get_text, get_user_lang_code
except ImportError:
    def get_user_lang(user_id: int) -> dict: return {}
    def get_text(lang: dict, key: str, default: str = "") -> str: return default
    def get_user_lang_code(user_id: int) -> str: return "fa"

# ---------------------------------------------------------
# 3. منوی اصلی (Main Menu)
# ---------------------------------------------------------

@router.callback_query(lambda c: c.data in ["italy", "italian"])
async def italian_main(callback: types.CallbackQuery, state: FSMContext):
    """منوی اصلی بخش ایتالیایی چندزبانه"""
    await state.clear()
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    if lang_code == "it":
        text = "🇮🇹 <b>Accademia della Lingua Italiana (Perugia)</b>\n\n"
        text += "🎓 Benvenuto nell'hub intelligente per imparare l'italiano!\n"
        text += "Da dove vuoi iniziare oggi?\n\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Lezioni Graduate (A1-B1)", callback_data="it_menu_lessons")],
            [InlineKeyboardButton(text="📖 Grammatica e Regole (A1-B1)", callback_data="it_menu_grammar")],
            [InlineKeyboardButton(text="🃏 Flashcard Vocabolario (con audio 🔊)", callback_data="italian_flashcard")],
            [InlineKeyboardButton(text="🧠 Quiz e Test di Livello", callback_data="italian_quiz")],
            [InlineKeyboardButton(text="🏠 Menu Principale", callback_data="main_menu")]
        ])
    elif lang_code == "en":
        text = "🇮🇹 <b>Learn Italian Language (Perugia Student Academy)</b>\n\n"
        text += "🎓 Welcome to the smart language learning hub!\n"
        text += "Where would you like to start today?\n\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Structured Lessons (A1-B1)", callback_data="it_menu_lessons")],
            [InlineKeyboardButton(text="📖 Grammar & Rules (A1-B1)", callback_data="it_menu_grammar")],
            [InlineKeyboardButton(text="🃏 Vocabulary Flashcards (with audio 🔊)", callback_data="italian_flashcard")],
            [InlineKeyboardButton(text="🧠 Level Quiz & Test", callback_data="italian_quiz")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
        ])
    else:
        text = "🇮🇹 <b>آموزش جامع زبان ایتالیایی (پروجا)</b>\n\n"
        text += "🎓 به آکادمی هوشمند خوش آمدید!\n"
        text += "اینجا می‌تونی با روش‌های مدرن زبان یاد بگیری. از کجا شروع کنیم؟\n\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 درس‌های طبقه‌بندی شده (A1-B1)", callback_data="it_menu_lessons")],
            [InlineKeyboardButton(text="📖 گرامر و قواعد (A1-B1)", callback_data="it_menu_grammar")],
            [InlineKeyboardButton(text="🃏 فلش‌کارت لغات (با تلفظ 🔊)", callback_data="italian_flashcard")],
            [InlineKeyboardButton(text="🧠 آزمون و تعیین سطح", callback_data="italian_quiz")],
            [InlineKeyboardButton(text="🏠 بازگشت به منوی اصلی", callback_data="main_menu")]
        ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# ---------------------------------------------------------
# 4. بخش درس‌ها (Lessons Logic)
# ---------------------------------------------------------

@router.callback_query(F.data == "it_menu_lessons")
async def lesson_level_select(callback: types.CallbackQuery, state: FSMContext):
    """منوی انتخاب سطح برای درس‌ها"""
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    if lang_code == "it":
        text = "📚 <b>Scegli il Livello di Studio</b>\n\n"
        text += "🟢 <b>Livello A1 (Principiante):</b> Saluti, vita quotidiana, acquisti\n"
        text += "🟡 <b>Livello A2 (Intermedio):</b> Conversazioni, esprimere emozioni\n"
        text += "🔴 <b>Livello B1 (Avanzato):</b> Comunicazioni universitarie e formali\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Livello A1", callback_data="less_lvl_A1")],
            [InlineKeyboardButton(text="🟡 Livello A2", callback_data="less_lvl_A2")],
            [InlineKeyboardButton(text="🔴 Livello B1", callback_data="less_lvl_B1")],
            [InlineKeyboardButton(text="🔙 Indietro", callback_data="italy")]
        ])
    elif lang_code == "en":
        text = "📚 <b>Select Learning Level</b>\n\n"
        text += "🟢 <b>Level A1 (Beginner):</b> Basic survival, greetings, shopping\n"
        text += "🟡 <b>Level A2 (Intermediate):</b> Daily conversation, opinions\n"
        text += "🔴 <b>Level B1 (Advanced):</b> Academic & official correspondence\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Level A1", callback_data="less_lvl_A1")],
            [InlineKeyboardButton(text="🟡 Level A2", callback_data="less_lvl_A2")],
            [InlineKeyboardButton(text="🔴 Level B1", callback_data="less_lvl_B1")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="italy")]
        ])
    else:
        text = "📚 <b>انتخاب سطح آموزشی</b>\n\n"
        text += "🟢 <b>سطح A1 (مبتدی):</b> بقا در ایتالیا، احوالپرسی، خرید\n"
        text += "🟡 <b>سطح A2 (متوسط):</b> مکالمه روزمره، بیان احساسات\n"
        text += "🔴 <b>سطح B1 (پیشرفته):</b> مکاتبات اداری، دانشگاهی\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 سطح A1", callback_data="less_lvl_A1")],
            [InlineKeyboardButton(text="🟡 سطح A2", callback_data="less_lvl_A2")],
            [InlineKeyboardButton(text="🔴 سطح B1", callback_data="less_lvl_B1")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="italy")]
        ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ItalianState.selecting_lesson_level)

@router.callback_query(F.data.startswith("less_lvl_"))
async def start_lessons_filtered(callback: types.CallbackQuery, state: FSMContext):
    """فیلتر کردن درس‌ها بر اساس سطح انتخاب شده"""
    selected_level = callback.data.split("_")[-1] # A1, A2, B1
    
    # فیلتر از دیتابیس
    filtered_lessons = [l for l in lessons_db if l.get("level") == selected_level]
    
    if not filtered_lessons:
        await callback.answer("⚠️ درسی برای این سطح پیدا نشد!", show_alert=True)
        return

    # ذخیره در حافظه کاربر
    await state.update_data(
        current_lesson_list=filtered_lessons,
        current_lesson_index=0,
        current_level_name=selected_level
    )
    await state.set_state(ItalianState.viewing_lesson)
    await show_lesson_content(callback.message, state)

async def show_lesson_content(message: types.Message, state: FSMContext):
    """نمایش محتوای درس فعلی"""
    data = await state.get_data()
    lessons_list = data["current_lesson_list"]
    index = data["current_lesson_index"]
    level_name = data["current_level_name"]
    
    lesson = lessons_list[index]
    total = len(lessons_list)
    
    text = f"📚 <b>درس‌های سطح {level_name}</b> (درس {index + 1} از {total})\n\n"
    text += f"📌 <b>{lesson['title']}</b>\n"
    text += "➖➖➖➖➖➖➖\n"
    text += f"{lesson['content']}\n"
    text += "➖➖➖➖➖➖➖\n"
    text += "💡 با دکمه‌های زیر درس‌ها را مرور کنید:"

    # ساخت دکمه‌های ناوبری
    btns = []
    nav_row = []
    
    if index > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ قبلی", callback_data="nav_less_prev"))
    
    if index < total - 1:
        nav_row.append(InlineKeyboardButton(text="بعدی ➡️", callback_data="nav_less_next"))
        
    btns.append(nav_row)
    btns.append([InlineKeyboardButton(text="🔙 لیست سطوح", callback_data="it_menu_lessons")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=btns)
    await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.in_({"nav_less_next", "nav_less_prev"}), ItalianState.viewing_lesson)
async def navigate_lessons(callback: types.CallbackQuery, state: FSMContext):
    """هندلر دکمه‌های بعدی و قبلی درس"""
    data = await state.get_data()
    index = data["current_lesson_index"]
    
    if callback.data == "nav_less_next":
        index += 1
    else:
        index -= 1
        
    await state.update_data(current_lesson_index=index)
    await show_lesson_content(callback.message, state)
    await callback.answer()

# ---------------------------------------------------------
# 5. بخش گرامر (Grammar Logic)
# ---------------------------------------------------------

@router.callback_query(F.data == "it_menu_grammar")
async def grammar_level_select(callback: types.CallbackQuery, state: FSMContext):
    """منوی انتخاب سطح گرامر"""
    text = "📖 <b>آموزش گرامر و قواعد</b>\n\n"
    text += "گرامر ایتالیایی را قدم به قدم یاد بگیرید.\n"
    text += "سطح مورد نظر را انتخاب کنید:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 گرامر پایه (A1)", callback_data="gram_lvl_A1")],
        [InlineKeyboardButton(text="🟡 گرامر متوسط (A2)", callback_data="gram_lvl_A2")],
        [InlineKeyboardButton(text="🔴 گرامر پیشرفته (B1)", callback_data="gram_lvl_B1")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="italian")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ItalianState.selecting_grammar_level)

@router.callback_query(F.data.startswith("gram_lvl_"))
async def start_grammar_filtered(callback: types.CallbackQuery, state: FSMContext):
    """فیلتر کردن گرامر و شروع نمایش"""
    selected_level = callback.data.split("_")[-1]
    
    filtered_grammar = [g for g in grammar_db if g.get("level") == selected_level]
    
    if not filtered_grammar:
        await callback.answer("⚠️ گرامری برای این سطح یافت نشد!", show_alert=True)
        return

    await state.update_data(
        current_grammar_list=filtered_grammar,
        current_grammar_index=0,
        current_gram_level=selected_level
    )
    await state.set_state(ItalianState.viewing_grammar)
    await show_grammar_content(callback.message, state)

async def show_grammar_content(message: types.Message, state: FSMContext):
    """نمایش صفحه گرامر"""
    data = await state.get_data()
    grammar_list = data["current_grammar_list"]
    index = data["current_grammar_index"]
    level_name = data["current_gram_level"]
    
    rule = grammar_list[index]
    total = len(grammar_list)
    
    text = f"📖 <b>گرامر سطح {level_name}</b> (نکته {index + 1} از {total})\n\n"
    text += f"🔹 <b>{rule['title']}</b>\n"
    text += "➖➖➖➖➖➖➖\n"
    text += f"{rule['content']}\n"
    text += "➖➖➖➖➖➖➖"

    btns = []
    nav_row = []
    
    if index > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ قبلی", callback_data="nav_gram_prev"))
    
    if index < total - 1:
        nav_row.append(InlineKeyboardButton(text="بعدی ➡️", callback_data="nav_gram_next"))
        
    btns.append(nav_row)
    btns.append([InlineKeyboardButton(text="🔙 لیست گرامر", callback_data="it_menu_grammar")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=btns)
    await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.in_({"nav_gram_next", "nav_gram_prev"}), ItalianState.viewing_grammar)
async def navigate_grammar(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    index = data["current_grammar_index"]
    
    if callback.data == "nav_gram_next":
        index += 1
    else:
        index -= 1
        
    await state.update_data(current_grammar_index=index)
    await show_grammar_content(callback.message, state)
    await callback.answer()

# ---------------------------------------------------------
# 6. بخش فلش‌کارت هوشمند (Smart Flashcards)
# ---------------------------------------------------------

@router.callback_query(F.data == "italian_flashcard")
async def italian_flashcard_start(callback: types.CallbackQuery, state: FSMContext):
    """شروع جلسه فلش‌کارت"""
    if not vocab_db:
        await callback.answer("⚠️ دیتابیس لغات خالی است!", show_alert=True)
        return

    # 1. کپی کردن دیتابیس
    # 2. بر زدن (Shuffle) برای تصادفی بودن
    shuffled = vocab_db.copy()
    random.shuffle(shuffled)
    
    # 3. انتخاب ۲۰ لغت برای این جلسه (جلوگیری از خستگی)
    session_deck = shuffled[:20]
    
    await state.update_data(
        flashcard_queue=session_deck,
        current_fc_index=0,
        missed_cards=[]  # کارت‌هایی که کاربر بلد نبود
    )
    await state.set_state(ItalianState.viewing_flashcard)
    await show_current_flashcard(callback.message, state)

async def show_current_flashcard(message: types.Message, state: FSMContext):
    """نمایش کارت فعلی"""
    data = await state.get_data()
    queue = data["flashcard_queue"]
    index = data["current_fc_index"]
    
    # پایان کارت‌ها؟
    if index >= len(queue):
        missed = data.get("missed_cards", [])
        if missed:
            # اگر غلط داشته، مرور شروع می‌شود
            await message.edit_text(
                f"🔄 <b>پایان دور اول!</b>\n\nتعداد {len(missed)} لغت رو بلد نبودی.\nالان فقط اون‌ها رو مرور می‌کنیم. آماده؟",
                parse_mode="HTML"
            )
            # جایگزینی صف اصلی با لیست غلط‌ها
            await state.update_data(flashcard_queue=missed, current_fc_index=0, missed_cards=[])
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 شروع مرور", callback_data="fc_start_review")]])
            await message.edit_reply_markup(reply_markup=kb)
        else:
            # اگر همه را بلد بود
            await message.edit_text(
                "🎉 <b>تبریک!</b>\n\nهمه لغات این جلسه رو یاد گرفتی! عالی بودی.\n\nاستراحت کن و بعداً دوباره بیا.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="italian")]])
            , parse_mode="HTML")
            await state.clear()
        return
    
    word = queue[index]
    text = f"🃏 <b>فلش‌کارت ({index + 1}/{len(queue)})</b>\n\n"
    text += f"🇮🇹 <b>{word['italian']}</b>\n"
    text += f"🗣 {word['pronunciation']}\n\n"
    text += "معنی این کلمه چیه؟ 🤔"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔊 تلفظ (پخش صدا)", callback_data="play_vocab_audio")],
        [InlineKeyboardButton(text="👁️ نمایش معنی", callback_data="fc_reveal")],
        [InlineKeyboardButton(text="🔙 خروج", callback_data="italian")]
    ])
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "fc_start_review", ItalianState.viewing_flashcard)
async def start_review_handler(callback: types.CallbackQuery, state: FSMContext):
    await show_current_flashcard(callback.message, state)

@router.callback_query(F.data == "fc_reveal", ItalianState.viewing_flashcard)
async def flashcard_reveal(callback: types.CallbackQuery, state: FSMContext):
    """نمایش پشت کارت (معنی)"""
    data = await state.get_data()
    queue = data["flashcard_queue"]
    index = data["current_fc_index"]
    word = queue[index]
    
    text = f"🃏 <b>پاسخ کارت:</b>\n\n"
    text += f"🇮🇹 {word['italian']}\n"
    text += f"🇮🇷 <b>{word['farsi']}</b>\n\n"
    text += "آیا معنیش رو بلد بودی؟"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔊 تلفظ", callback_data="play_vocab_audio")],
        [InlineKeyboardButton(text="✅ بلد بودم (حذف)", callback_data="fc_know")],
        [InlineKeyboardButton(text="❌ بلد نبودم (تکرار)", callback_data="fc_dont_know")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.in_({"fc_know", "fc_dont_know"}), ItalianState.viewing_flashcard)
async def flashcard_feedback(callback: types.CallbackQuery, state: FSMContext):
    """ثبت نتیجه کاربر (بلد بودم/نبودم)"""
    data = await state.get_data()
    queue = data["flashcard_queue"]
    index = data["current_fc_index"]
    word = queue[index]
    
    if callback.data == "fc_dont_know":
        # اضافه به لیست اشتباهات برای مرور
        missed = data.get("missed_cards", [])
        missed.append(word)
        await state.update_data(missed_cards=missed)
        await callback.answer("❌ ذخیره شد برای مرور", show_alert=False)
    else:
        await callback.answer("✅ عالی!", show_alert=False)
        
    # رفتن به کارت بعدی
    await state.update_data(current_fc_index=index + 1)
    await show_current_flashcard(callback.message, state)

# ---------------------------------------------------------
# 7. بخش تلفظ صوتی (TTS Handler)
# ---------------------------------------------------------

@router.callback_query(F.data == "play_vocab_audio", ItalianState.viewing_flashcard)
async def play_vocab_audio(callback: types.CallbackQuery, state: FSMContext):
    """تولید و ارسال فایل صوتی تلفظ"""
    try:
        data = await state.get_data()
        queue = data.get("flashcard_queue")
        index = data.get("current_fc_index")
        
        if not queue or index >= len(queue):
            await callback.answer("⚠️ خطا در پخش صدا", show_alert=False)
            return

        word = queue[index]
        italian_text = word['italian']
        
        await callback.answer("🎧 در حال دریافت صدا...")

        # ساخت فایل موقت با آیدی کاربر برای جلوگیری از تداخل
        file_path = f"temp_audio_{callback.from_user.id}.mp3"
        
        # تولید صدا با گوگل
        tts = gTTS(text=italian_text, lang='it')
        tts.save(file_path)
        
        # ارسال ویس
        voice_file = FSInputFile(file_path)
        await callback.bot.send_voice(chat_id=callback.message.chat.id, voice=voice_file)
        
        # پاک کردن فایل موقت
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        print(f"Error in TTS: {e}")
        await callback.answer("❌ خطا در اتصال به سرویس صدا", show_alert=True)

# ---------------------------------------------------------
# 8. بخش آزمون (Quiz Logic)
# ---------------------------------------------------------

@router.callback_query(F.data == "italian_quiz")
async def italian_quiz_start(callback: types.CallbackQuery, state: FSMContext):
    """شروع آزمون"""
    if not quizzes_db:
        await callback.answer("⚠️ بانک سوالات خالی است!", show_alert=True)
        return

    # انتخاب تصادفی ۱۰ سوال
    quiz_session = random.sample(quizzes_db, min(len(quizzes_db), 10))
    
    await state.update_data(
        quiz_list=quiz_session,
        quiz_score=0,
        quiz_index=0
    )
    await state.set_state(ItalianState.in_quiz)
    await send_next_quiz_question(callback.message, state)

async def send_next_quiz_question(message: types.Message, state: FSMContext):
    """ارسال سوال بعدی"""
    data = await state.get_data()
    quiz_list = data["quiz_list"]
    index = data["quiz_index"]
    
    # پایان آزمون
    if index >= len(quiz_list):
        score = data["quiz_score"]
        total = len(quiz_list)
        percentage = (score / total) * 100
        
        # تعیین سطح
        if percentage >= 90: level_res = "استاد 🎓 (C1)"
        elif percentage >= 70: level_res = "پیشرفته 🔥 (B1/B2)"
        elif percentage >= 50: level_res = "متوسط 👍 (A2)"
        else: level_res = "مبتدی 🌱 (A1)"
        
        text = f"🏁 <b>آزمون تمام شد!</b>\n\n"
        text += f"📊 امتیاز شما: <b>{score} از {total}</b>\n"
        text += f"🏆 سطح تقریبی: <b>{level_res}</b>\n\n"
        text += "می‌خوای دوباره خودت رو بسنجی؟"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 آزمون جدید", callback_data="italian_quiz")],
            [InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="italian")]
        ])
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await state.clear()
        return
    
    question = quiz_list[index]
    text = f"🧠 <b>سوال {index + 1} از {len(quiz_list)}</b>\n\n"
    text += f"{question['question']}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    # ساخت دکمه گزینه‌ها
    for i, opt in enumerate(question["options"]):
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=opt, callback_data=f"qz_ans_{i}")])
    
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="❌ خروج", callback_data="italian")])
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.startswith("qz_ans_"), ItalianState.in_quiz)
async def process_quiz_answer(callback: types.CallbackQuery, state: FSMContext):
    """بررسی جواب کاربر"""
    selected_opt = int(callback.data.split("_")[-1])
    
    data = await state.get_data()
    quiz_list = data["quiz_list"]
    index = data["quiz_index"]
    question = quiz_list[index]
    
    correct_opt = question["correct"]
    
    if selected_opt == correct_opt:
        new_score = data["quiz_score"] + 1
        await state.update_data(quiz_score=new_score)
        # نوتیفیکیشن موفقیت (بدون پاپ‌آپ مزاحم)
        await callback.answer("✅ آفرین! درست بود.", show_alert=False)
    else:
        correct_text = question["options"][correct_opt]
        # نوتیفیکیشن خطا (با پاپ‌آپ برای یادگیری)
        await callback.answer(f"❌ اشتباه!\nجواب درست: {correct_text}", show_alert=True)
    
    # رفتن به سوال بعد
    await state.update_data(quiz_index=index + 1)
    await send_next_quiz_question(callback.message, state)