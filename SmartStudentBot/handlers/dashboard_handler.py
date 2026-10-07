# handlers/dashboard_handler.py
# داشبورد روزانه کاربر (چندزبانه)

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db_manager

try:
    from handlers.cmd_start import get_user_lang, get_text, get_user_lang_code
except ImportError:
    def get_user_lang(user_id: int) -> dict: return {}
    def get_text(lang: dict, key: str, default: str = "") -> str: return default
    def get_user_lang_code(user_id: int) -> str: return "fa"

router = Router()
router.name = "dashboard_handler"

@router.message(Command("today"))
@router.callback_query(F.data == "today")
async def show_dashboard(event: types.Message | types.CallbackQuery):
    """داشبورد روزانه کاربر شامل وضعیت، رویدادها و سطح دانشجویی"""
    user_id = event.from_user.id
    name = event.from_user.first_name or "Student"
    lang_code = get_user_lang_code(user_id)
    
    # دریافت اطلاعات کاربر از دیتابیس
    user_db = await db_manager.get_user(user_id)
    xp = user_db.get("xp", 150) if user_db else 150
    
    # واکشی نزدیک‌ترین رویداد از دیتابیس
    events = await db_manager.get_events()
    latest_event = events[0]["title"] if events else ("Weekly Meetup" if lang_code != "fa" else "دورهمی هفتگی")
    
    if lang_code == "it":
        if xp < 300:
            level = "🌱 Matricola (Nuovo Studente)"
            next_level = f"{300 - xp} XP al prossimo livello"
        elif xp < 800:
            level = "🌿 Studente In Corso (Secondo Anno)"
            next_level = f"{800 - xp} XP al prossimo livello"
        else:
            level = "🎓 Laureando / Esperto di Perugia"
            next_level = "Livello Massimo 🏆"

        text = (
            "📅 <b>La Tua Dashboard Giornaliera (Daily Brief)</b>\n\n"
            f"👤 <b>Studente:</b> {name}\n"
            f"⭐ <b>Livello:</b> {level}\n"
            f"⚡ <b>Punti XP:</b> <code>{xp} XP</code> ({next_level})\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🌤 <b>Meteo (Perugia):</b> Clima piacevole per una passeggiata in Corso Vannucci\n"
            "🍝 <b>Menu Mensa:</b> Pasta al ragù/pesto, petto di pollo, salad bar, dessert\n"
            f"🎉 <b>Prossimo Evento:</b> {latest_event}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 <i>Guadagna punti XP partecipando al mercatino, recensendo luoghi e usando il bot!</i>"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Riscatta Bonus Giornaliero (+20 XP)", callback_data="daily_quest")],
            [InlineKeyboardButton(text="🏠 Menu Principale", callback_data="main_menu")]
        ])
    elif lang_code == "en":
        if xp < 300:
            level = "🌱 Fresher (Matricola)"
            next_level = f"{300 - xp} XP to next level"
        elif xp < 800:
            level = "🌿 2nd Year Student (In Corso)"
            next_level = f"{800 - xp} XP to next level"
        else:
            level = "🎓 Master Student / Perugia Pro"
            next_level = "Top Tier Achieved 🏆"

        text = (
            "📅 <b>Your Daily Dashboard (Daily Brief)</b>\n\n"
            f"👤 <b>Student:</b> {name}\n"
            f"⭐ <b>Rank:</b> {level}\n"
            f"⚡ <b>Active XP:</b> <code>{xp} XP</code> ({next_level})\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🌤 <b>Weather (Perugia):</b> Pleasant weather for a walk on Corso Vannucci\n"
            "🍝 <b>Mensa Menu:</b> Pasta al ragù/pesto, chicken fillet, salad bar, dessert\n"
            f"🎉 <b>Upcoming Event:</b> {latest_event}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 <i>Earn XP by posting in marketplace, reviewing places, and sharing the bot!</i>"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Claim Daily Bonus (+20 XP)", callback_data="daily_quest")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
        ])
    else:
        if xp < 300:
            level = "🌱 دانشجوی تازه‌وارد (Matricola)"
            next_level = f"{300 - xp} XP تا سطح بعد"
        elif xp < 800:
            level = "🌿 دانشجوی سال دوم (In Corso)"
            next_level = f"{800 - xp} XP تا سطح بعد"
        else:
            level = "🎓 دانشجوی ارشد و پروجاشناس"
            next_level = "بالاترین رتبه دانشجویی 🏆"

        text = (
            "📅 <b>داشبورد روزانه شما (Daily Brief)</b>\n\n"
            f"👤 <b>دانشجو:</b> {name}\n"
            f"⭐ <b>رتبه:</b> {level}\n"
            f"⚡ <b>امتیاز فعال:</b> <code>{xp} XP</code> ({next_level})\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🌤 <b>آب‌وهوا (پروجا):</b> معتدل و مناسب پیاده‌روی در Corso Vannucci\n"
            "🍝 <b>منوی Mensa:</b> پاستا با سس راگو/پستو، فیله مرغ، سالاد بار، دسر\n"
            f"🎉 <b>رویداد پیش‌رو:</b> {latest_event}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 <i>با مشارکت در بازارچه، ثبت نظر برای مکان‌ها و اشتراک ربات، امتیاز XP جمع کنید!</i>"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 دریافت پاداش روزانه (+20 XP)", callback_data="daily_quest")],
            [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu")]
        ])
    
    if isinstance(event, types.CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            await event.message.answer(text, reply_markup=markup, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=markup, parse_mode="HTML")

@router.callback_query(F.data == "daily_quest")
async def daily_quest(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    new_xp = await db_manager.add_user_xp(user_id, 20)
    
    if lang_code == "it":
        await callback.answer(f"🎉 Bonus di oggi riscattato! (+20 XP)\nTotale punti: {new_xp}", show_alert=True)
    elif lang_code == "en":
        await callback.answer(f"🎉 Daily bonus claimed! (+20 XP)\nTotal points: {new_xp}", show_alert=True)
    else:
        await callback.answer(f"🎉 پاداش امروز دریافت شد! (+20 XP)\nمجموع امتیاز شما: {new_xp}", show_alert=True)
