# handlers/guide_handler.py
# راهنمای جامع پروجا - نسخه ۲.۰
# ژانویه ۲۰۲۵

"""
📖 راهنمای کامل زندگی دانشجویی در پروجا

امکانات:
    ۱. راهنمای گام به گام (۷ مرحله اصلی)
    ۲. هزینه‌های زندگی به‌روز
    ۳. لوکیشن‌های مهم با پین واقعی
    ۴. اپلیکیشن‌های ضروری
    ۵. نکات طلایی و هشدارها
    ۶. سوالات متداول (FAQ)
    ۷. جستجو در راهنما

ویژگی‌های جدید v2.0:
    - رفع خطای message is not modified
    - FAQ کامل
    - جستجوی متنی
    - ساختار بهتر کد
    - مدیریت خطا بهتر
"""

from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from contextlib import suppress
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

from config import settings, logger

# تلاش برای import توابع زبان
try:
    from handlers.cmd_start import get_user_lang, get_text
except ImportError:
    def get_user_lang(user_id: int) -> dict:
        return {}
    def get_text(lang: dict, key: str, default: str = "") -> str:
        return lang.get(key, default or key)


# ═══════════════════════════════════════════════════════════════════════════════
# ۱. تنظیمات و ثابت‌ها
# ═══════════════════════════════════════════════════════════════════════════════

router = Router()
router.name = "guide_handler"


# ═══════════════════════════════════════════════════════════════════════════════
# ۲. داده‌های اصلی
# ═══════════════════════════════════════════════════════════════════════════════

# مراحل اصلی
STEPS_DATA: Dict[str, Dict[str, str]] = {
    "1": {
        "title": "دریافت کدیچه فیسکاله",
        "emoji": "🆔",
        "short": "Codice Fiscale",
    },
    "2": {
        "title": "خرید سیم‌کارت ایتالیایی",
        "emoji": "📱",
        "short": "SIM Card",
    },
    "3": {
        "title": "بیمه درمانی",
        "emoji": "🏥",
        "short": "Insurance",
    },
    "4": {
        "title": "ثبت‌نام دانشگاه",
        "emoji": "🎓",
        "short": "Immatricolazione",
    },
    "5": {
        "title": "درخواست پرمسو",
        "emoji": "🛂",
        "short": "Permesso di Soggiorno",
    },
    "6": {
        "title": "افتتاح حساب بانکی",
        "emoji": "🏦",
        "short": "Bank Account",
    },
    "7": {
        "title": "انگشت‌نگاری و کارت اقامت",
        "emoji": "👆",
        "short": "Questura",
    },
}

# لوکیشن‌های مهم
LOCATIONS: Dict[str, Dict[str, Any]] = {
    "agenzia": {
        "lat": 43.10895,
        "lon": 12.38885,
        "title": "🏢 Agenzia delle Entrate",
        "address": "Via Canali, 12, 06124 Perugia",
        "desc": "اداره مالیات - برای کدیچه فیسکاله",
        "hours": "دوشنبه تا جمعه ۸:۳۰-۱۳:۰۰",
    },
    "poste": {
        "lat": 43.11072,
        "lon": 12.38918,
        "title": "📮 Poste Italiane - Centrale",
        "address": "Piazza Giacomo Matteotti, 14, 06124 Perugia",
        "desc": "پست مرکزی - برای کیت پرمسو",
        "hours": "دوشنبه تا جمعه ۸:۲۰-۱۹:۰۵، شنبه ۸:۲۰-۱۲:۳۵",
    },
    "questura": {
        "lat": 43.0800,
        "lon": 12.3420,
        "title": "👮 Questura - Ufficio Immigrazione",
        "address": "Via del Tabacchificio, 21, 06135 Ellera",
        "desc": "اداره مهاجرت - برای انگشت‌نگاری",
        "hours": "دوشنبه تا جمعه ۸:۳۰-۱۲:۳۰",
    },
    "uni_main": {
        "lat": 43.1160,
        "lon": 12.3860,
        "title": "🏛 دانشگاه پروجا - مرکزی",
        "address": "Piazza dell'Università, 1, 06123 Perugia",
        "desc": "ساختمان اصلی دانشگاه",
        "hours": "دوشنبه تا جمعه ۹:۰۰-۱۷:۰۰",
    },
    "engineering": {
        "lat": 43.0990,
        "lon": 12.3750,
        "title": "🔬 دانشکده مهندسی",
        "address": "Via Goffredo Duranti, 93, 06125 Perugia",
        "desc": "Polo Ingegneria",
        "hours": "دوشنبه تا جمعه ۸:۰۰-۱۹:۰۰",
    },
    "medicine": {
        "lat": 43.1040,
        "lon": 12.3900,
        "title": "🏥 دانشکده پزشکی",
        "address": "Piazzale Lucio Severi, 1, 06132 Perugia",
        "desc": "Polo Medico - Sant'Andrea delle Fratte",
        "hours": "دوشنبه تا جمعه ۸:۰۰-۱۸:۰۰",
    },
    "adisu": {
        "lat": 43.1120,
        "lon": 12.3890,
        "title": "🍽 سلف دانشگاه ADISU",
        "address": "Via Enrico dal Pozzo, 06126 Perugia",
        "desc": "غذاخوری دانشجویی",
        "hours": "ناهار ۱۲:۰۰-۱۴:۳۰، شام ۱۹:۰۰-۲۱:۰۰",
    },
    "asl": {
        "lat": 43.1050,
        "lon": 12.3820,
        "title": "🏥 ASL Umbria 1",
        "address": "Via XIV Settembre, 06124 Perugia",
        "desc": "برای ثبت‌نام SSN",
        "hours": "دوشنبه تا جمعه ۸:۰۰-۱۳:۰۰",
    },
}

# اپلیکیشن‌های ضروری
APPS_DATA: List[Dict[str, str]] = [
    {
        "name": "MyUnipg",
        "desc": "پرتال دانشگاه و نمرات",
        "emoji": "🎓",
        "android": "https://play.google.com/store/apps/details?id=it.unipg.myunipg",
        "ios": "https://apps.apple.com/it/app/myunipg/id1594130587",
    },
    {
        "name": "Salgo",
        "desc": "خرید بلیط اتوبوس",
        "emoji": "🎟",
        "android": "https://play.google.com/store/apps/details?id=net.pluservice.salgo",
        "ios": "https://apps.apple.com/app/salgo/id1518059041",
    },
    {
        "name": "Moovit",
        "desc": "مسیریابی حمل‌ونقل عمومی",
        "emoji": "🚌",
        "android": "https://play.google.com/store/apps/details?id=com.tranzmate",
        "ios": "https://apps.apple.com/app/moovit/id498477945",
    },
    {
        "name": "Trenitalia",
        "desc": "خرید بلیط قطار",
        "emoji": "🚂",
        "android": "https://play.google.com/store/apps/details?id=com.lynxspa.trenitalia",
        "ios": "https://apps.apple.com/app/trenitalia/id331360436",
    },
    {
        "name": "Too Good To Go",
        "desc": "غذای ارزان و ضد هدر",
        "emoji": "🍽",
        "android": "https://play.google.com/store/apps/details?id=com.app.tgtg",
        "ios": "https://apps.apple.com/app/too-good-to-go/id1060683933",
    },
    {
        "name": "Wise",
        "desc": "انتقال پول بین‌المللی",
        "emoji": "💸",
        "android": "https://play.google.com/store/apps/details?id=com.transferwise.android",
        "ios": "https://apps.apple.com/app/wise/id612261027",
    },
    {
        "name": "Revolut",
        "desc": "حساب دیجیتال و کارت",
        "emoji": "💳",
        "android": "https://play.google.com/store/apps/details?id=com.revolut.revolut",
        "ios": "https://apps.apple.com/app/revolut/id932493382",
    },
    {
        "name": "Idealista",
        "desc": "جستجوی اجاره خانه",
        "emoji": "🏠",
        "android": "https://play.google.com/store/apps/details?id=com.idealista.android",
        "ios": "https://apps.apple.com/app/idealista/id321983477",
    },
    {
        "name": "FortiClient VPN",
        "desc": "VPN دانشگاه برای دسترسی به منابع",
        "emoji": "🔒",
        "android": "https://play.google.com/store/apps/details?id=com.fortinet.forticlient_vpn",
        "ios": "https://apps.apple.com/app/forticlient/id6443490628",
    },
    {
        "name": "FlixBus",
        "desc": "اتوبوس بین‌شهری ارزان",
        "emoji": "🚍",
        "android": "https://play.google.com/store/apps/details?id=de.flixbus.app",
        "ios": "https://apps.apple.com/app/flixbus/id6443462208",
    },
]

# سوالات متداول
FAQ_DATA: List[Dict[str, str]] = [
    {
        "q": "چند روز بعد از ورود باید پرمسو بگیرم؟",
        "a": "⚠️ <b>۸ روز!</b> این مهلت قانونی است و تأخیر جریمه سنگین دارد.",
        "tags": "پرمسو مهلت روز",
    },
    {
        "q": "آیا با رسید پرمسو می‌توانم حساب بانکی باز کنم؟",
        "a": "✅ بله! <b>Postepay Evolution</b> با رسید پرمسو (Ricevuta) باز می‌شود. بانک‌های دیگر معمولاً کارت پرمسو می‌خواهند.",
        "tags": "بانک حساب رسید پست‌پی",
    },
    {
        "q": "بیمه W.A.I برای تمدید پرمسو قبول می‌شود؟",
        "a": "⚠️ برای <b>اولین پرمسو</b> بله! اما برای <b>تمدید</b> ممکن است Questura بیمه کامل‌تر (SSN یا خصوصی) بخواهد.",
        "tags": "بیمه wai تمدید",
    },
    {
        "q": "هزینه زندگی ماهانه در پروجا چقدر است؟",
        "a": "💰 <b>۶۵۰-۱۰۰۰ یورو</b>\n• اجاره: ۳۰۰-۴۵۰€\n• غذا: ۲۰۰-۳۰۰€\n• حمل‌ونقل: ۲۵-۳۵€\n• متفرقه: ۱۰۰-۲۰۰€\n\n💡 با بورسیه DSU تا ۴۰۰€ کمتر!",
        "tags": "هزینه ماهانه زندگی",
    },
    {
        "q": "کدام سیم‌کارت بهتر است؟",
        "a": "🥇 <b>Iliad</b> (توصیه اصلی)\n• ۱۵۰ گیگ + تماس نامحدود\n• ۹.۹۹€/ماه\n• eSIM موجود\n\n🥈 Vodafone: پوشش عالی\n🥉 TIM: پوشش روستایی خوب",
        "tags": "سیم‌کارت اپراتور iliad",
    },
    {
        "q": "چطور نوبت Agenzia delle Entrate بگیرم؟",
        "a": "🌐 از سایت رسمی:\n<a href='https://www.agenziaentrate.gov.it/portale/prenotazione'>agenziaentrate.gov.it/prenotazione</a>\n\n⚠️ بدون نوبت نروید!",
        "tags": "نوبت کدیچه آژانس",
    },
    {
        "q": "سلف دانشگاه چند است؟",
        "a": "🍽 <b>ADISU Mensa</b>\n• با کارت ADISU: ۴-۶€\n• بدون کارت: ۸-۱۰€\n\n💡 برای کارت به سایت adisumbria.it مراجعه کنید.",
        "tags": "سلف غذا mensa",
    },
    {
        "q": "چطور وضعیت پرمسو را پیگیری کنم؟",
        "a": "🌐 از سایت:\n<a href='https://www.portaleimmigrazione.it'>portaleimmigrazione.it</a>\n\nبا شماره روی رسید (Ricevuta) وارد شوید.",
        "tags": "پیگیری پرمسو وضعیت",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# ۳. States
# ═══════════════════════════════════════════════════════════════════════════════

class GuideStates(StatesGroup):
    """وضعیت‌های راهنما"""
    searching = State()


# ═══════════════════════════════════════════════════════════════════════════════
# ۴. توابع کمکی
# ═══════════════════════════════════════════════════════════════════════════════

async def safe_edit_text(
    message,
    text: str,
    reply_markup=None,
    parse_mode=ParseMode.HTML,
    disable_web_page_preview: bool = True
) -> bool:
    """ویرایش ایمن پیام"""
    try:
        await message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview
        )
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return True
        # برای سایر خطاها، پیام جدید ارسال کن
        try:
            await message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview
            )
            return True
        except:
            return False
    except Exception:
        return False


def get_step_content(step_id: int) -> Tuple[str, Optional[str], Optional[str]]:
    """
    دریافت محتوای هر مرحله
    
    Returns:
        (متن, url عکس, کلید لوکیشن)
    """
    
    if step_id == 1:
        content = """🆔 <b>مرحله ۱: دریافت کدیچه فیسکاله (Codice Fiscale)</b>

━━━━━━━━━━━━━━━━━━━━━

مهم‌ترین کد شناسایی در ایتالیا! بدون آن <b>هیچ کاری</b> نمی‌توانید انجام دهید.

🏢 <b>کجا؟</b>
Agenzia delle Entrate
📍 Via Canali, 12, Perugia

⏰ <b>ساعت کاری:</b>
دوشنبه تا جمعه ۸:۳۰ - ۱۳:۰۰

⚠️ <b>مهم:</b> حتماً نوبت آنلاین بگیرید!
🌐 <a href='https://www.agenziaentrate.gov.it/portale/prenotazione'>رزرو نوبت آنلاین</a>

📄 <b>مدارک لازم:</b>
• پاسپورت (اصل + کپی)
• ویزای تحصیلی (کپی)

💰 <b>هزینه:</b> رایگان
⏳ <b>زمان:</b> ۱۰-۱۵ دقیقه

💡 <b>نکته:</b> کدیچه را یادداشت کنید و عکس بگیرید!"""
        return content, None, "agenzia"
    
    elif step_id == 2:
        content = """📱 <b>مرحله ۲: خرید سیم‌کارت ایتالیایی</b>

━━━━━━━━━━━━━━━━━━━━━

برای همه کارها شماره ایتالیایی لازم است!

🥇 <b>Iliad (توصیه اصلی):</b>
• ۱۵۰ گیگ + تماس نامحدود
• قیمت: ۹.۹۹ €/ماه
• eSIM موجود ✅
• 🌐 <a href='https://www.iliad.it'>iliad.it</a>

🥈 <b>Vodafone:</b>
• پوشش عالی
• eSIM موجود
• از ۱۲ €/ماه
• 🌐 <a href='https://www.vodafone.it'>vodafone.it</a>

🥉 <b>TIM:</b>
• پوشش روستایی خوب
• از ۱۰ €/ماه
• 🌐 <a href='https://www.tim.it'>tim.it</a>

📍 <b>فروشگاه‌های Iliad در پروجا:</b>
• Emisfero (Centro Commerciale)
• ایستگاه قطار Fontivegge
• Collestrada

📄 <b>مدارک:</b>
• پاسپورت
• کدیچه فیسکاله

⚠️ <b>نکته:</b> گوشی‌های قفل‌شده (Carrier Lock) eSIM قبول نمی‌کنند!"""
        return content, None, None
    
    elif step_id == 3:
        content = """🏥 <b>مرحله ۳: بیمه درمانی</b>

━━━━━━━━━━━━━━━━━━━━━

برای پرمسو حتماً بیمه معتبر لازم است!

🟢 <b>W.A.I (برای اولین پرمسو):</b>
• هزینه: ۱۲۰ € (سالانه)
• پوشش: اورژانس و بستری
• 🌐 <a href='https://www.waitaly.net'>waitaly.net</a>
• ✅ سریع و آنلاین

🔵 <b>SSN دولتی (برای تمدید):</b>
• هزینه: ~۷۰۰ €/سال
• پوشش: کامل
• محل ثبت‌نام: ASL Umbria 1
• 📍 Via XIV Settembre, Perugia

🟡 <b>AON Student Insurance:</b>
• هزینه: ۹۸ €
• پوشش: خوب برای دانشجویان
• 🌐 <a href='https://www.aikiassicurazioni.com'>aon.com</a>

⚠️ <b>توجه مهم:</b>
• W.A.I برای <b>اولین</b> پرمسو کافی است
• برای <b>تمدید</b> ممکن است SSN لازم باشد
• از Questura خود بپرسید!"""
        return content, None, "asl"
    
    elif step_id == 4:
        content = """🎓 <b>مرحله ۴: ثبت‌نام نهایی دانشگاه (Immatricolazione)</b>

━━━━━━━━━━━━━━━━━━━━━

🏛 <b>دانشگاه پروجا</b>
📍 Piazza dell'Università, 1

🌐 <b>پرتال ثبت‌نام:</b>
<a href='https://unipg.esse3.cineca.it'>SOL Unipg</a>

📧 <b>ایمیل پشتیبانی:</b>
international.students@unipg.it

📄 <b>مدارک لازم:</b>
• پذیرش دانشگاه
• پاسپورت + ویزا
• کدیچه فیسکاله
• Dichiarazione di Valore (DDV)
• مدرک زبان (اگر لازم است)
• عکس پرسنلی

💰 <b>هزینه اولیه:</b>
• ۱۵۶ € ثبت‌نام
• ۱۶ € تمبر (Marca da Bollo)
• جمع: ۱۷۲ €

📍 <b>دانشکده‌ها:</b>
• مهندسی: Polo Ingegneria (Sant'Andrea)
• پزشکی: Polo Medico
• اقتصاد/حقوق: مرکز شهر

⏳ <b>ددلاین:</b> معمولاً تا اکتبر"""
        return content, None, "uni_main"
    
    elif step_id == 5:
        content = """🛂 <b>مرحله ۵: درخواست پرمسو دی سوجورنو</b>

━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>مهلت: ۸ روز پس از ورود!</b>

📮 <b>مرحله اول: اداره پست</b>
📍 Poste Italiane - Piazza Matteotti
• دریافت کیت زرد (Kit Postale) - رایگان
• خرید تمبر ۱۶€ از Tabacchi

📄 <b>مدارک داخل پاکت:</b>
• کپی کامل پاسپورت + ویزا
• پذیرش دانشگاه
• بیمه درمانی
• کدیچه فیسکاله
• تمکن مالی (بانک)
• ۴ عکس پرسنلی (۳×۴)
• تمبر ۱۶€

💰 <b>هزینه در پست:</b> ۱۳۰-۱۴۰ € (نقد)

📋 <b>بعد از ارسال:</b>
• رسید (Ricevuta) دریافت می‌کنید
• ⚠️ این رسید را گم نکنید!
• برای بانک و همه‌جا لازم است

⏳ <b>انتظار پیامک:</b> ۱-۳ ماه
🌐 <b>پیگیری وضعیت:</b>
<a href='https://www.portaleimmigrazione.it'>portaleimmigrazione.it</a>"""
        return content, None, "poste"
    
    elif step_id == 6:
        content = """🏦 <b>مرحله ۶: افتتاح حساب بانکی</b>

━━━━━━━━━━━━━━━━━━━━━

🥇 <b>Postepay Evolution (توصیه برای شروع):</b>
• ✅ با رسید پرمسو باز می‌شود!
• دارای IBAN واقعی
• هزینه صدور: ۱۵ €
• هزینه سالانه: ۱۵ €
• در هر اداره پست

🥈 <b>UniCredit MyGenius Green:</b>
• رایگان برای دانشجویان
• خدمات کامل بانکی
• ⚠️ معمولاً کارت پرمسو می‌خواهد

🥉 <b>Intesa Sanpaolo XME:</b>
• رایگان تا ۳۵ سال
• شعبه‌های زیاد

📄 <b>مدارک عمومی:</b>
• پاسپورت
• کدیچه فیسکاله
• رسید پرمسو یا کارت پرمسو
• قرارداد اجاره یا گواهی سکونت

💡 <b>نکته:</b>
اگر هنوز کارت پرمسو ندارید:
<b>Postepay Evolution</b> بهترین گزینه است!"""
        return content, None, "poste"
    
    elif step_id == 7:
        content = """👆 <b>مرحله ۷: انگشت‌نگاری و دریافت کارت اقامت</b>

━━━━━━━━━━━━━━━━━━━━━

پس از دریافت پیامک از Questura:

👮 <b>محل مراجعه:</b>
Questura - Ufficio Immigrazione
📍 Via del Tabacchificio, 21, Ellera

🚌 <b>دسترسی:</b>
• اتوبوس خط G
• قطار به ایستگاه Ellera

📄 <b>مدارک روز انگشت‌نگاری:</b>
• پاسپورت اصل
• رسید پست (Ricevuta)
• ۴ عکس پرسنلی
• تمام مدارکی که کپی دادید (اصل)

⏳ <b>زمان صدور کارت:</b> ۱-۴ ماه

🌐 <b>پیگیری وضعیت:</b>
<a href='https://www.portaleimmigrazione.it'>portaleimmigrazione.it</a>

💡 <b>نکته:</b> صبح زود بروید چون صف طولانی است!

━━━━━━━━━━━━━━━━━━━━━

🎉 <b>تبریک!</b>
حالا قانونی در ایتالیا هستید!"""
        return content, None, "questura"
    
    # پیش‌فرض
    return (
        "⚠️ این مرحله یافت نشد.\n\nلطفاً به منوی راهنما برگردید.",
        None,
        None
    )


def search_in_guide(query: str) -> List[Dict[str, Any]]:
    """جستجو در راهنما و FAQ"""
    
    query_lower = query.lower()
    results = []
    
    # جستجو در مراحل
    for step_id, step_info in STEPS_DATA.items():
        if query_lower in step_info["title"].lower() or query_lower in step_info["short"].lower():
            results.append({
                "type": "step",
                "id": step_id,
                "title": f"{step_info['emoji']} {step_info['title']}",
            })
    
    # جستجو در FAQ
    for faq in FAQ_DATA:
        if query_lower in faq["q"].lower() or query_lower in faq["tags"].lower():
            results.append({
                "type": "faq",
                "q": faq["q"],
                "a": faq["a"],
            })
    
    # جستجو در لوکیشن‌ها
    for key, loc in LOCATIONS.items():
        if query_lower in loc["title"].lower() or query_lower in loc["desc"].lower():
            results.append({
                "type": "location",
                "key": key,
                "title": loc["title"],
            })
    
    return results[:10]  # حداکثر ۱۰ نتیجه


# ═══════════════════════════════════════════════════════════════════════════════
# ۵. کیبوردها
# ═══════════════════════════════════════════════════════════════════════════════

def get_guide_main_keyboard() -> InlineKeyboardMarkup:
    """کیبورد منوی اصلی راهنما"""
    
    buttons = []
    
    # مراحل
    for key, step in STEPS_DATA.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{step['emoji']} {key}. {step['title']}",
                callback_data=f"guide:step_{key}"
            )
        ])
    
    # بخش‌های دیگر
    buttons.extend([
        [
            InlineKeyboardButton(text="💰 هزینه‌های زندگی", callback_data="guide:costs"),
            InlineKeyboardButton(text="📍 لوکیشن‌ها", callback_data="guide:locations"),
        ],
        [
            InlineKeyboardButton(text="📱 اپلیکیشن‌ها", callback_data="guide:apps"),
            InlineKeyboardButton(text="💡 نکات طلایی", callback_data="guide:tips"),
        ],
        [
            InlineKeyboardButton(text="❓ سوالات متداول", callback_data="guide:faq"),
            InlineKeyboardButton(text="🔍 جستجو", callback_data="guide:search"),
        ],
        [
            InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu"),
        ],
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_step_nav_keyboard(step_id: int) -> InlineKeyboardMarkup:
    """کیبورد ناوبری مراحل"""
    
    buttons = []
    nav_row = []
    
    # دکمه قبلی
    if step_id > 1:
        nav_row.append(
            InlineKeyboardButton(
                text=f"⬅️ مرحله {step_id - 1}",
                callback_data=f"guide:step_{step_id - 1}"
            )
        )
    
    # دکمه بعدی
    if step_id < len(STEPS_DATA):
        nav_row.append(
            InlineKeyboardButton(
                text=f"مرحله {step_id + 1} ➡️",
                callback_data=f"guide:step_{step_id + 1}"
            )
        )
    
    if nav_row:
        buttons.append(nav_row)
    
    # لوکیشن مرتبط
    _, _, loc_key = get_step_content(step_id)
    if loc_key:
        buttons.append([
            InlineKeyboardButton(
                text="📍 نمایش لوکیشن",
                callback_data=f"guide:loc_{loc_key}"
            )
        ])
    
    # بازگشت و سوال
    buttons.extend([
        [
            InlineKeyboardButton(text="🔙 منوی راهنما", callback_data="guide:main"),
        ],
        [
            InlineKeyboardButton(text="❓ سوال دارم", callback_data="consult"),
        ],
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_locations_keyboard() -> InlineKeyboardMarkup:
    """کیبورد لوکیشن‌ها"""
    
    buttons = []
    
    for key, loc in LOCATIONS.items():
        buttons.append([
            InlineKeyboardButton(
                text=loc["title"],
                callback_data=f"guide:loc_{key}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 منوی راهنما", callback_data="guide:main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_to_guide_keyboard() -> InlineKeyboardMarkup:
    """کیبورد بازگشت"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 منوی راهنما", callback_data="guide:main"),
            InlineKeyboardButton(text="🏠 منو اصلی", callback_data="main_menu"),
        ]
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# ۶. هندلرها - منوی اصلی
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "guide_main")
@router.callback_query(F.data == "guide:main")
async def guide_menu(callback: CallbackQuery, state: FSMContext):
    """منوی اصلی راهنما"""
    
    await state.clear()
    
    text = """🗺 <b>راهنمای کامل پروجا</b>

━━━━━━━━━━━━━━━━━━━━━

🎉 به شهر زیبای پروجا خوش آمدید!

این راهنما تمام مراحل قانونی و زندگی روزمره را پوشش می‌دهد.

<b>مراحل را به ترتیب انجام دهید:</b>

👇 انتخاب کنید:"""
    
    await safe_edit_text(
        callback.message,
        text=text,
        reply_markup=get_guide_main_keyboard()
    )
    
    await callback.answer()


@router.message(Command("guide", "راهنما"))
async def cmd_guide(message: Message, state: FSMContext):
    """دستور راهنما"""
    
    await state.clear()
    
    text = """🗺 <b>راهنمای کامل پروجا</b>

━━━━━━━━━━━━━━━━━━━━━

🎉 به شهر زیبای پروجا خوش آمدید!

👇 انتخاب کنید:"""
    
    await message.answer(
        text=text,
        reply_markup=get_guide_main_keyboard(),
        parse_mode=ParseMode.HTML
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ۷. هندلرها - مراحل
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("guide:step_"))
@router.callback_query(F.data.startswith("guide_step_"))
async def show_step_detail(callback: CallbackQuery):
    """نمایش جزئیات مرحله"""
    
    # استخراج شماره مرحله
    step_str = callback.data.split("_")[-1]
    
    if not step_str.isdigit():
        await callback.answer("❌ خطا!", show_alert=True)
        return
    
    step_id = int(step_str)
    
    if step_id < 1 or step_id > len(STEPS_DATA):
        await callback.answer("❌ مرحله نامعتبر!", show_alert=True)
        return
    
    content, photo_url, _ = get_step_content(step_id)
    
    await safe_edit_text(
        callback.message,
        text=content,
        reply_markup=get_step_nav_keyboard(step_id)
    )
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ۸. هندلرها - هزینه‌ها
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "guide:costs")
@router.callback_query(F.data == "guide_costs")
async def guide_costs(callback: CallbackQuery):
    """هزینه‌های زندگی"""
    
    text = """💰 <b>هزینه‌های ماهانه زندگی در پروجا (۲۰۲۵)</b>

━━━━━━━━━━━━━━━━━━━━━

🏠 <b>اجاره:</b>
• اتاق مشترک: ۳۰۰-۳۸۰ €
• اتاق تک‌نفره: ۳۸۰-۴۵۰ €
• آپارتمان کامل: ۵۵۰-۸۰۰ €

🍽 <b>غذا:</b>
• پخت خانگی: ۱۵۰-۲۰۰ €
• سلف دانشگاه (ADISU): ۴-۶ € هر وعده
• بیرون غذا خوردن: +۵۰-۱۰۰ €

🚌 <b>حمل‌ونقل:</b>
• بلیط ماهانه (Salgo): ۲۵-۳۵ €
• مینی‌مترو: ۱.۵۰ € تک‌سفره

📱 <b>موبایل و اینترنت:</b>
• سیم‌کارت (Iliad): ۱۰-۱۵ €

⚡ <b>قبوض (اگر جداست):</b>
• برق/گاز/آب: ۵۰-۸۰ €

☕ <b>تفریح و متفرقه:</b>
• ۱۰۰-۱۵۰ €

━━━━━━━━━━━━━━━━━━━━━

📊 <b>جمع کل ماهانه:</b>
<b>۶۵۰ - ۱,۰۰۰ €</b>

💡 <b>با بورسیه DSU:</b>
تا ۴۰۰ € کاهش می‌یابد!"""
    
    await safe_edit_text(
        callback.message,
        text=text,
        reply_markup=get_back_to_guide_keyboard()
    )
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ۹. هندلرها - لوکیشن‌ها
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "guide:locations")
@router.callback_query(F.data == "guide_locations")
async def guide_locations(callback: CallbackQuery):
    """منوی لوکیشن‌ها"""
    
    text = """📍 <b>لوکیشن‌های مهم پروجا</b>

━━━━━━━━━━━━━━━━━━━━━

روی هر مکان کلیک کنید تا پین واقعی در تلگرام باز شود.

می‌توانید مستقیم مسیریابی کنید! 🗺

👇 انتخاب کنید:"""
    
    await safe_edit_text(
        callback.message,
        text=text,
        reply_markup=get_locations_keyboard()
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("guide:loc_"))
@router.callback_query(F.data.startswith("loc_send_"))
async def send_location(callback: CallbackQuery):
    """ارسال لوکیشن"""
    
    # استخراج کلید
    if "loc_send_" in callback.data:
        key = callback.data.replace("loc_send_", "")
    else:
        key = callback.data.replace("guide:loc_", "")
    
    if key not in LOCATIONS:
        await callback.answer("❌ مکان یافت نشد!", show_alert=True)
        return
    
    loc = LOCATIONS[key]
    
    # ارسال Venue
    await callback.message.answer_venue(
        latitude=loc["lat"],
        longitude=loc["lon"],
        title=loc["title"],
        address=loc["address"]
    )
    
    # پیام توضیحی
    info_text = f"""📍 <b>{loc['title']}</b>

📮 {loc['address']}

📝 {loc['desc']}

⏰ <b>ساعت کاری:</b>
{loc['hours']}"""
    
    await callback.message.answer(
        text=info_text,
        reply_markup=get_back_to_guide_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ۱۰. هندلرها - اپلیکیشن‌ها
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "guide:apps")
@router.callback_query(F.data == "guide_apps")
async def guide_apps(callback: CallbackQuery):
    """اپلیکیشن‌های ضروری"""
    
    text = """📱 <b>اپلیکیشن‌های ضروری</b>

━━━━━━━━━━━━━━━━━━━━━

این اپ‌ها زندگی شما را راحت‌تر می‌کنند:

"""
    
    buttons = []
    
    for app in APPS_DATA:
        text += f"{app['emoji']} <b>{app['name']}</b>\n"
        text += f"   {app['desc']}\n\n"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{app['emoji']} {app['name']} (Android)",
                url=app["android"]
            ),
            InlineKeyboardButton(
                text="iOS",
                url=app["ios"]
            ),
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 منوی راهنما", callback_data="guide:main")
    ])
    
    await safe_edit_text(
        callback.message,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ۱۱. هندلرها - نکات
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "guide:tips")
@router.callback_query(F.data == "guide_tips")
async def guide_tips(callback: CallbackQuery):
    """نکات طلایی"""
    
    text = """💡 <b>نکات طلایی و هشدارها</b>

━━━━━━━━━━━━━━━━━━━━━

🔴 <b>هشدارهای مهم:</b>

⚠️ پرمسو را ظرف <b>۸ روز</b> انجام دهید!
   جریمه سنگین دارد

⚠️ مراقب کلاهبرداری اجاره باشید!
   حتماً قرارداد رسمی بخواهید

⚠️ رسید پرمسو (Ricevuta) را گم نکنید!
   برای همه کارها لازم است

⚠️ W.A.I برای تمدید ممکن است کافی نباشد
   از Questura بپرسید

━━━━━━━━━━━━━━━━━━━━━

🟢 <b>نکات طلایی:</b>

✅ <b>Iliad</b> بهترین سیم‌کارت (۱۵۰ گیگ واقعی)

✅ <b>Postepay Evolution</b> با رسید پرمسو باز می‌شود

✅ از <b>Salgo</b> برای بلیط اتوبوس استفاده کنید

✅ <b>سلف دانشگاه</b> با کارت ADISU خیلی ارزان است

✅ <b>Too Good To Go</b> برای غذای ارزان عالی است

✅ در گروه‌های تلگرام دانشجویان ایرانی عضو شوید

✅ صبح زود به Questura بروید (صف طولانی)

━━━━━━━━━━━━━━━━━━━━━

🇮🇹 شما می‌توانید! موفق باشید! ✨"""
    
    await safe_edit_text(
        callback.message,
        text=text,
        reply_markup=get_back_to_guide_keyboard()
    )
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ۱۲. هندلرها - FAQ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "guide:faq")
async def guide_faq(callback: CallbackQuery):
    """سوالات متداول"""
    
    text = """❓ <b>سوالات متداول (FAQ)</b>

━━━━━━━━━━━━━━━━━━━━━

"""
    
    for i, faq in enumerate(FAQ_DATA, 1):
        text += f"<b>{i}. {faq['q']}</b>\n"
        text += f"{faq['a']}\n\n"
    
    text += """━━━━━━━━━━━━━━━━━━━━━

💬 سوال دیگری دارید؟ از بخش مشاوره استفاده کنید!"""
    
    buttons = [
        [InlineKeyboardButton(text="💬 سوال دارم", callback_data="consult")],
        [InlineKeyboardButton(text="🔙 منوی راهنما", callback_data="guide:main")],
    ]
    
    await safe_edit_text(
        callback.message,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ۱۳. هندلرها - جستجو
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "guide:search")
async def start_search(callback: CallbackQuery, state: FSMContext):
    """شروع جستجو"""
    
    await state.set_state(GuideStates.searching)
    
    text = """🔍 <b>جستجو در راهنما</b>

━━━━━━━━━━━━━━━━━━━━━

عبارت مورد نظر را بنویسید:

💡 <i>مثال: پرمسو، بیمه، بانک، سیم‌کارت</i>

❌ لغو: /cancel"""
    
    await safe_edit_text(
        callback.message,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ لغو", callback_data="guide:main")]
        ])
    )
    
    await callback.answer()


@router.message(GuideStates.searching)
async def process_search(message: Message, state: FSMContext):
    """پردازش جستجو"""
    
    query = (message.text or "").strip()
    
    if query.lower() in ["/cancel", "لغو"]:
        await state.clear()
        await message.answer(
            "❌ جستجو لغو شد.",
            reply_markup=get_back_to_guide_keyboard()
        )
        return
    
    if len(query) < 2:
        await message.answer("⚠️ حداقل ۲ کاراکتر وارد کنید.")
        return
    
    await state.clear()
    
    results = search_in_guide(query)
    
    text = f"🔍 <b>نتایج جستجو برای:</b> <code>{query}</code>\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not results:
        text += "📭 <i>نتیجه‌ای یافت نشد.</i>\n\n"
        text += "💡 عبارت دیگری امتحان کنید."
        keyboard = get_back_to_guide_keyboard()
    else:
        buttons = []
        
        for r in results:
            if r["type"] == "step":
                text += f"📖 {r['title']}\n"
                buttons.append([
                    InlineKeyboardButton(
                        text=r["title"],
                        callback_data=f"guide:step_{r['id']}"
                    )
                ])
            elif r["type"] == "faq":
                text += f"❓ {r['q']}\n"
                text += f"   {r['a'][:100]}...\n\n"
            elif r["type"] == "location":
                text += f"📍 {r['title']}\n"
                buttons.append([
                    InlineKeyboardButton(
                        text=r["title"],
                        callback_data=f"guide:loc_{r['key']}"
                    )
                ])
        
        buttons.append([
            InlineKeyboardButton(text="🔍 جستجوی جدید", callback_data="guide:search")
        ])
        buttons.append([
            InlineKeyboardButton(text="🔙 منوی راهنما", callback_data="guide:main")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ۱۴. لاگ
# ═══════════════════════════════════════════════════════════════════════════════

logger.success("📖 Guide Handler v2.0 loaded!")
logger.info(f"   Router: {router.name}")
logger.info(f"   Steps: {len(STEPS_DATA)}")
logger.info(f"   Locations: {len(LOCATIONS)}")
logger.info(f"   Apps: {len(APPS_DATA)}")
logger.info(f"   FAQ: {len(FAQ_DATA)}")