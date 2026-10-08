# handlers/cost_handler.py - راهنمای هزینه زندگی دانشجویی در پروجا
# نسخه چندزبانه (FA, EN, IT)

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

try:
    from handlers.cmd_start import get_user_lang, get_text, get_user_lang_code
except ImportError:
    def get_user_lang(user_id: int) -> dict: return {}
    def get_text(lang: dict, key: str, default: str = "") -> str: return default
    def get_user_lang_code(user_id: int) -> str: return "fa"

router = Router()
router.name = "cost_handler"

COST_DATA_FA = [
    ("🏠 <b>مسکن و اسکان</b>", ""),
    ("اتاق در خانه اشتراکی", "300–450 €"),
    ("اقامتگاه دولتی ADiSU", "250–350 €"),
    ("آپارتمان یک خوابه (مرکز شهر)", "600–800 €"),
    ("آپارتمان یک خوابه (اطراف)", "450–600 €"),
    
    ("🍽️ <b>تغذیه و رستوران</b>", ""),
    ("یک وعده در سلف دانشگاه (Mensa)", "2.5–5.5 €"),
    ("خرید ماهانه سوپرمارکت (یک نفر)", "180–250 €"),
    ("پیتزا مارگاریتا محلی", "7–10 €"),
    ("اسپرسو / کاپوچینو", "1.2–1.8 €"),
    
    ("🚍 <b>حمل و نقل شهری</b>", ""),
    ("اشتراک ماهانه دانشجویی اتوبوس و مینی‌مترو", "30–35 €"),
    ("بلیط تک‌سفره ۷۰ دقیقه‌ای", "1.50 €"),
    
    ("⚡ <b>قبوض و خدمات عمومی</b>", ""),
    ("سیم‌کارت دانشجویی با نت بالا (Iliad/Fastweb)", "8–10 €"),
    ("اینترنت فیبر نوری خانه (اشتراکی)", "10–15 € هر نفر"),
    ("برق، گاز، آب و شارژ ساختمان", "50–80 € هر نفر"),
    
    ("🎉 <b>تفریح و سرگرمی</b>", ""),
    ("بلیط سینما (تخفیف دانشجویی)", "6–8 €"),
    ("باشگاه ورزشی ماهانه (CUS Perugia)", "25–40 €"),
    
    ("💡 <b>مجموع تقریبی ماهانه</b>", ""),
    ("زندگی دانشجویی اقتصادی (با اتاق اشتراکی)", "650–850 €"),
    ("زندگی متوسط و راحت", "900–1150 €")
]

COST_DATA_EN = [
    ("🏠 <b>Housing & Accommodation</b>", ""),
    ("Single room in shared flat", "300–450 €"),
    ("ADiSU Student Dormitory", "250–350 €"),
    ("1-Bedroom flat (City Center)", "600–800 €"),
    ("1-Bedroom flat (Suburbs)", "450–600 €"),
    
    ("🍽️ <b>Food & Dining</b>", ""),
    ("Meal at University Canteen (Mensa)", "2.5–5.5 €"),
    ("Monthly groceries (1 person)", "180–250 €"),
    ("Margherita Pizza", "7–10 €"),
    ("Espresso / Cappuccino", "1.2–1.8 €"),
    
    ("🚍 <b>Local Transportation</b>", ""),
    ("Monthly student bus & minimetrò pass", "30–35 €"),
    ("Single 70-min ticket", "1.50 €"),
    
    ("⚡ <b>Utilities & Services</b>", ""),
    ("Student Mobile SIM (Iliad/Fastweb)", "8–10 €"),
    ("Home fiber internet (shared)", "10–15 € / person"),
    ("Electricity, gas, water & building fees", "50–80 € / person"),
    
    ("🎉 <b>Leisure & Sports</b>", ""),
    ("Cinema ticket (Student discount)", "6–8 €"),
    ("Monthly Gym membership (CUS Perugia)", "25–40 €"),
    
    ("💡 <b>Approximate Monthly Total</b>", ""),
    ("Budget student lifestyle (shared room)", "650–850 €"),
    ("Comfortable standard lifestyle", "900–1150 €")
]

COST_DATA_IT = [
    ("🏠 <b>Alloggio e Affitto</b>", ""),
    ("Stanza singola in appartamento condiviso", "300–450 €"),
    ("Residenza universitaria ADiSU", "250–350 €"),
    ("Bilocale (Centro storico)", "600–800 €"),
    ("Bilocale (Periferia)", "450–600 €"),
    
    ("🍽️ <b>Cibo e Ristorazione</b>", ""),
    ("Pasto alla Mensa Universitaria", "2.5–5.5 €"),
    ("Spesa mensile al supermercato (1 persona)", "180–250 €"),
    ("Pizza Margherita locale", "7–10 €"),
    ("Espresso / Cappuccino", "1.2–1.8 €"),
    
    ("🚍 <b>Trasporti Locali</b>", ""),
    ("Abbonamento mensile studenti Bus & Minimetrò", "30–35 €"),
    ("Biglietto singolo 70 minuti", "1.50 €"),
    
    ("⚡ <b>Bollette e Utenze</b>", ""),
    ("SIM mobile studenti (Iliad/Fastweb)", "8–10 €"),
    ("Fibra ottica casa (condivisa)", "10–15 € / persona"),
    ("Luce, gas, acqua e condominio", "50–80 € / persona"),
    
    ("🎉 <b>Tempo Libero e Sport</b>", ""),
    ("Biglietto cinema (sconto studenti)", "6–8 €"),
    ("Palestra mensile (CUS Perugia)", "25–40 €"),
    
    ("💡 <b>Totale Mensile Stimato</b>", ""),
    ("Stile di vita economico (stanza singola)", "650–850 €"),
    ("Stile di vita confortevole", "900–1150 €")
]

@router.message(Command("cost"))
@router.callback_query(F.data.in_(["cost", "cost_main"]))
async def show_cost_of_living(event: types.Message | types.CallbackQuery):
    """نمایش هزینه‌های واقعی و به‌روز زندگی دانشجویی در پروجا"""
    user_id = event.from_user.id
    lang_code = get_user_lang_code(user_id)
    lang = get_user_lang(user_id)
    def t(key, default): return get_text(lang, key, default)

    if lang_code == "it":
        data = COST_DATA_IT
        text = "💰 <b>Costo della Vita Studentesca a Perugia</b>\n\n"
        text += "📊 Prezzi medi reali stimati in <b>Euro (€)</b>:\n"
        text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        for label, price in data:
            if price == "":
                text += f"\n{label}\n"
            else:
                text += f"   • {label}: <b>{price}</b>\n"
        text += "\n━━━━━━━━━━━━━━━━━━━━━\n"
        text += "💡 <b>Consigli utili per risparmiare:</b>\n"
        text += "   ۱. <b>Tessera Mensa ADiSU:</b> Con borsa di studio hai fino a 2 pasti gratuiti al giorno!\n"
        text += "   ۲. <b>Aree Elce o Monteluce:</b> Vicine alle facoltà e con affitti più vantaggiosi.\n"
        text += "   ۳. <b>Supermercati convenienti:</b> Eurospin e Lidl costano decisamente meno di Conad.\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧮 Calcolo ISEE per Agevolazioni", callback_data="isee")],
            [InlineKeyboardButton(text="🏠 Trova Alloggio & Coinquilino", callback_data="roommate")],
            [
                InlineKeyboardButton(text="🔙 Torna alla Guida", callback_data="guide:main"),
                InlineKeyboardButton(text="🏠 Menu Principale", callback_data="main_menu")
            ]
        ])
    elif lang_code == "en":
        data = COST_DATA_EN
        text = "💰 <b>Student Cost of Living in Perugia (Italy)</b>\n\n"
        text += "📊 Estimated average prices in <b>Euro (€)</b>:\n"
        text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        for label, price in data:
            if price == "":
                text += f"\n{label}\n"
            else:
                text += f"   • {label}: <b>{price}</b>\n"
        text += "\n━━━━━━━━━━━━━━━━━━━━━\n"
        text += "💡 <b>Money-Saving Tips:</b>\n"
        text += "   1. <b>ADiSU Mensa Card:</b> With the scholarship, you can get up to 2 free meals daily!\n"
        text += "   2. <b>Elce or Monteluce areas:</b> Close to campuses and cheaper rent than center.\n"
        text += "   3. <b>Discount supermarkets:</b> Eurospin and Lidl are significantly cheaper than Conad.\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧮 Calculate ISEE for Fee Waiver", callback_data="isee")],
            [InlineKeyboardButton(text="🏠 Find Roommates & Housing", callback_data="roommate")],
            [
                InlineKeyboardButton(text="🔙 Back to Guide", callback_data="guide:main"),
                InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")
            ]
        ])
    else:
        data = COST_DATA_FA
        text = "💰 <b>هزینه زندگی دانشجویی در پروجا (ایتالیا)</b>\n\n"
        text += "📊 میانگین قیمت‌های واقعی به <b>یورو (€)</b>:\n"
        text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        for label, price in data:
            if price == "":
                text += f"\n{label}\n"
            else:
                text += f"   • {label}: <b>{price}</b>\n"
        text += "\n━━━━━━━━━━━━━━━━━━━━━\n"
        text += "💡 <b>ترفندهای طلایی برای کاهش هزینه‌ها:</b>\n"
        text += "   ۱. <b>کارت غذای Adisu:</b> با دریافت بورسیه، روزانه تا ۲ وعده غذای رایگان در Mensa خواهید داشت!\n"
        text += "   ۲. <b>زندگی در Elce یا Monteluce:</b> این مناطق هم به دانشگاه نزدیک‌ترند و هم کرایه‌ها مناسب‌تر از مرکز است.\n"
        text += "   ۳. <b>خرید از سوپرمارکت‌های زنجیره‌ای اقتصادی:</b> Eurospin و Lidl به مراتب ارزان‌تر از Conad هستند.\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧮 محاسبه ISEE برای معافیت شهریه", callback_data="isee")],
            [InlineKeyboardButton(text="🏠 پیدا کردن هم‌اتاقی و اتاق", callback_data="roommate")],
            [
                InlineKeyboardButton(text="🔙 بازگشت به راهنما", callback_data="guide:main"),
                InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu")
            ]
        ])
    
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        await event.answer()
    else:
        await event.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
