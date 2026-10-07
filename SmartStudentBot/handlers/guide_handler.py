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
    from handlers.cmd_start import get_user_lang, get_text, get_user_lang_code
except ImportError:
    def get_user_lang(user_id: int) -> dict:
        return {}
    def get_text(lang: dict, key: str, default: str = "") -> str:
        return lang.get(key, default or key)
    def get_user_lang_code(user_id: int) -> str:
        return "fa"


# ═══════════════════════════════════════════════════════════════════════════════
# ۱. تنظیمات و ثابت‌ها
# ═══════════════════════════════════════════════════════════════════════════════

router = Router()
router.name = "guide_handler"


# ═══════════════════════════════════════════════════════════════════════════════
# ۲. داده‌های اصلی
# ═══════════════════════════════════════════════════════════════════════════════

# مراحل اصلی
STEPS_DATA_LOCALIZED: Dict[str, Dict[str, Dict[str, str]]] = {
    "fa": {
        "1": {"title": "دریافت کدیچه فیسکاله", "emoji": "🆔", "short": "Codice Fiscale"},
        "2": {"title": "خرید سیم‌کارت ایتالیایی", "emoji": "📱", "short": "SIM Card"},
        "3": {"title": "بیمه درمانی", "emoji": "🏥", "short": "Insurance"},
        "4": {"title": "ثبت‌نام دانشگاه", "emoji": "🎓", "short": "Immatricolazione"},
        "5": {"title": "درخواست پرمسو", "emoji": "🛂", "short": "Permesso di Soggiorno"},
        "6": {"title": "افتتاح حساب بانکی", "emoji": "🏦", "short": "Bank Account"},
        "7": {"title": "انگشت‌نگاری و کارت اقامت", "emoji": "👆", "short": "Questura"},
    },
    "en": {
        "1": {"title": "Obtain Codice Fiscale", "emoji": "🆔", "short": "Codice Fiscale"},
        "2": {"title": "Buy Italian SIM Card", "emoji": "📱", "short": "SIM Card"},
        "3": {"title": "Health Insurance", "emoji": "🏥", "short": "Insurance"},
        "4": {"title": "University Matriculation", "emoji": "🎓", "short": "Immatricolazione"},
        "5": {"title": "Residence Permit (Permesso)", "emoji": "🛂", "short": "Permesso di Soggiorno"},
        "6": {"title": "Open Bank Account", "emoji": "🏦", "short": "Bank Account"},
        "7": {"title": "Fingerprinting & Residence Card", "emoji": "👆", "short": "Questura"},
    },
    "it": {
        "1": {"title": "Richiesta Codice Fiscale", "emoji": "🆔", "short": "Codice Fiscale"},
        "2": {"title": "Acquisto SIM Italiana", "emoji": "📱", "short": "SIM Card"},
        "3": {"title": "Assicurazione Sanitaria", "emoji": "🏥", "short": "Insurance"},
        "4": {"title": "Immatricolazione Universitaria", "emoji": "🎓", "short": "Immatricolazione"},
        "5": {"title": "Richiesta Permesso di Soggiorno", "emoji": "🛂", "short": "Permesso di Soggiorno"},
        "6": {"title": "Apertura Conto Bancario", "emoji": "🏦", "short": "Bank Account"},
        "7": {"title": "Impronte Digitali e Ritiro Permesso", "emoji": "👆", "short": "Questura"},
    }
}

STEPS_DATA: Dict[str, Dict[str, str]] = STEPS_DATA_LOCALIZED["fa"]

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


def get_step_content(step_id: int, lang_code: str = "fa") -> Tuple[str, Optional[str], Optional[str]]:
    """
    دریافت محتوای هر مرحله
    
    Returns:
        (متن, url عکس, کلید لوکیشن)
    """
    loc_keys = {
        1: "agenzia",
        2: None,
        3: "asl",
        4: "uni_main",
        5: "poste",
        6: "poste",
        7: "questura"
    }
    
    if lang_code == "en":
        en_steps = {
            1: """🆔 <b>Step 1: Obtain Codice Fiscale (Tax Code)</b>

━━━━━━━━━━━━━━━━━━━━━

The most essential identification code in Italy! You cannot sign a lease, open a bank account, or buy a local SIM card without it.

🏢 <b>Where?</b>
Agenzia delle Entrate
📍 Via Canali, 12, Perugia

⏰ <b>Hours:</b>
Monday to Friday 08:30 - 13:00

⚠️ <b>Important:</b> An online reservation is mandatory!
🌐 <a href='https://www.agenziaentrate.gov.it/portale/prenotazione'>Book Online Appointment</a>

📄 <b>Required Documents:</b>
• Passport (Original + Copy)
• Student Visa (Copy)

💰 <b>Cost:</b> Free
⏳ <b>Time:</b> 10-15 minutes

💡 <b>Tip:</b> Keep a photo of your certificate saved on your phone!""",
            2: """📱 <b>Step 2: Buy an Italian SIM Card</b>

━━━━━━━━━━━━━━━━━━━━━

An Italian phone number is required for almost all local bureaucratic procedures!

🥇 <b>Iliad (Top Recommendation):</b>
• 150GB + Unlimited Calls/SMS
• Price: €9.99/month
• eSIM available ✅
• 🌐 <a href='https://www.iliad.it'>iliad.it</a>

🥈 <b>Vodafone:</b>
• Excellent coverage
• From €12/month
• 🌐 <a href='https://www.vodafone.it'>vodafone.it</a>

🥉 <b>TIM:</b>
• Reliable national & rural coverage
• From €10/month
• 🌐 <a href='https://www.tim.it'>tim.it</a>

📍 <b>Iliad Locations in Perugia:</b>
• Emisfero Shopping Center
• Fontivegge Railway Station
• Collestrada Mall

📄 <b>Documents:</b>
• Passport
• Codice Fiscale""",
            3: """🏥 <b>Step 3: Health Insurance</b>

━━━━━━━━━━━━━━━━━━━━━

Valid health insurance coverage is mandatory for your Permesso di Soggiorno!

🟢 <b>W.A.I. (Welcome Association Italy - First Kit):</b>
• Cost: €120/year
• Covers emergency hospitalization
• 🌐 <a href='https://www.waitaly.net'>waitaly.net</a>
• Fast digital enrollment

🔵 <b>SSN Public Health (National Health Service):</b>
• Full comprehensive coverage including general practitioner (GP)
• Enrollment at ASL Umbria 1 (Via XIV Settembre, Perugia)

📄 <b>Documents:</b>
• Passport
• Codice Fiscale
• University enrollment letter""",
            4: """🎓 <b>Step 4: University Matriculation (Immatricolazione)</b>

━━━━━━━━━━━━━━━━━━━━━

🏛 <b>Università degli Studi di Perugia (UniPG)</b>
📍 Piazza dell'Università, 1

🌐 <b>Student Portal:</b>
<a href='https://unipg.esse3.cineca.it'>SOL UniPG</a>

📧 <b>International Office:</b>
international.students@unipg.it

📄 <b>Required Documents:</b>
• Admission letter
• Passport + Visa
• Codice Fiscale
• Dichiarazione di Valore (DoV) or CIMEA Statement
• Language certificate (if applicable)
• ID photos

💰 <b>Initial Regional Tax:</b> ~€156 + €16 Marca da Bollo""",
            5: """🛂 <b>Step 5: Apply for Permesso di Soggiorno (Residence Permit)</b>

━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>Deadline: Within 8 business days of arrival in Italy!</b>

📮 <b>First Step: Post Office (Poste Italiane)</b>
📍 Piazza Giacomo Matteotti, 14, Perugia
• Request the yellow envelope (Kit Giallo) - Free
• Buy a €16 Marca da Bollo stamp from any Tabacchi shop

📄 <b>Documents inside the envelope:</b>
• Photocopy of Passport (all pages with stamps/visas)
• University enrollment certificate
• Health insurance policy copy
• Codice Fiscale copy
• Proof of funds / bank statement
• €16 Marca da Bollo stamp affixed to Module 1

💰 <b>Post Office Payment:</b> ~€130 - €140 (Cash or card)

📋 <b>After Submission:</b>
• You receive the official Postal Receipt (Ricevuta) + Appointment sheet
• ⚠️ NEVER LOSE THIS RECEIPT! It serves as your temporary legal residence.
🌐 <b>Track Progress:</b> <a href='https://www.portaleimmigrazione.it'>portaleimmigrazione.it</a>""",
            6: """🏦 <b>Step 6: Open an Italian Bank Account</b>

━━━━━━━━━━━━━━━━━━━━━

🥇 <b>Postepay Evolution (Recommended for arrival):</b>
• ✅ Can be opened with just your Ricevuta (postal receipt)!
• Includes a full Italian IBAN
• Annual fee: €15
• Available at any Poste Italiane branch

🥈 <b>UniCredit MyGenius Green:</b>
• Free account for university students
• Usually requires final Permesso plastic card

🥉 <b>Intesa Sanpaolo XME:</b>
• Free under 35 years old
• Wide branch and ATM network

📄 <b>Standard Documents:</b>
• Passport
• Codice Fiscale
• Permesso Ricevuta or card
• Rental contract or address declaration""",
            7: """👆 <b>Step 7: Fingerprinting & Residence Card Collection</b>

━━━━━━━━━━━━━━━━━━━━━

👮 <b>Immigration Office:</b>
Questura - Ufficio Immigrazione
📍 Via del Tabacchificio, 21, Ellera di Corciano

🚌 <b>Transport:</b> Bus Line G or regional train to Ellera station

📄 <b>What to bring on appointment day:</b>
• Original Passport
• Postal Receipt (Ricevuta) and appointment letter
• 4 passport-size photographs
• Originals of all documents previously submitted in the postal kit

⏳ <b>Card Production:</b> 1 to 3 months
🌐 <b>Check Status:</b> <a href='https://www.portaleimmigrazione.it'>portaleimmigrazione.it</a>

🎉 <b>Congratulations!</b> Once collected, your official Italian residence permit is active!"""
        }
        if step_id in en_steps:
            return en_steps[step_id], None, loc_keys.get(step_id)
        return "⚠️ Step not found. Please return to the Guide menu.", None, None

    elif lang_code == "it":
        it_steps = {
            1: """🆔 <b>Passo 1: Richiesta del Codice Fiscale</b>

━━━━━━━━━━━━━━━━━━━━━

Il codice identificativo fondamentale in Italia! Indispensabile per contratti d'affitto, conti correnti e SIM.

🏢 <b>Dove?</b>
Agenzia delle Entrate
📍 Via Canali, 12, Perugia

⏰ <b>Orari:</b>
Lunedì - Venerdì 08:30 - 13:00

⚠️ <b>Importante:</b> La prenotazione online è obbligatoria!
🌐 <a href='https://www.agenziaentrate.gov.it/portale/prenotazione'>Prenota Online</a>

📄 <b>Documenti richiesti:</b>
• Passaporto (Originale + Copia)
• Visto di studio (Copia)

💰 <b>Costo:</b> Gratuito
⏳ <b>Tempo:</b> 10-15 minuti

💡 <b>Consiglio:</b> Salva una foto della ricevuta sul telefono!""",
            2: """📱 <b>Passo 2: Acquisto SIM Italiana</b>

━━━━━━━━━━━━━━━━━━━━━

Un numero italiano è indispensabile per la burocrazia, banche e università!

🥇 <b>Iliad (Consigliato):</b>
• 150GB + Minuti/SMS illimitati
• 9,99 €/mese
• eSIM disponibile ✅
• 🌐 <a href='https://www.iliad.it'>iliad.it</a>

🥈 <b>Vodafone:</b>
• Ottima copertura
• Da 12 €/mese
• 🌐 <a href='https://www.vodafone.it'>vodafone.it</a>

🥉 <b>TIM:</b>
• Copertura affidabile
• Da 10 €/mese
• 🌐 <a href='https://www.tim.it'>tim.it</a>

📄 <b>Documenti:</b> Passaporto e Codice Fiscale.""",
            3: """🏥 <b>Passo 3: Assicurazione Sanitaria</b>

━━━━━━━━━━━━━━━━━━━━━

Obbligatoria per la richiesta del permesso di soggiorno!

🟢 <b>W.A.I. (Welcome Association Italy):</b>
• Costo: 120 €/anno
• Copre emergenze e ricoveri
• Procedura rapida online: <a href='https://www.waitaly.net'>waitaly.net</a>

🔵 <b>Iscrizione Volontaria SSN:</b>
• Copertura completa con medico di base (Tessera Sanitaria)
• Iscrizione presso ASL Umbria 1

📄 <b>Documenti:</b> Passaporto, Codice Fiscale, lettera di immatricolazione.""",
            4: """🎓 <b>Passo 4: Immatricolazione Universitaria</b>

━━━━━━━━━━━━━━━━━━━━━

🏛 <b>Università degli Studi di Perugia</b>
📍 Piazza dell'Università, 1

🌐 <b>Portale SOL:</b> <a href='https://unipg.esse3.cineca.it'>SOL UniPG</a>
📧 <b>Ufficio Internazionale:</b> international.students@unipg.it

📄 <b>Documenti necessari:</b>
• Lettera di ammissione
• Passaporto e visto
• Codice Fiscale
• Dichiarazione di Valore (DoV) o Attestato CIMEA
• Certificato linguistico (se previsto)
• Fototessere

💰 <b>Tassa regionale iniziale:</b> ~156 € + 16 € Marca da bollo""",
            5: """🛂 <b>Passo 5: Richiesta del Permesso di Soggiorno (Kit Giallo)</b>

━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>Scadenza tassativa: entro 8 giorni lavorativi dall'arrivo!</b>

📮 <b>Primo passo: Ufficio Postale (Poste Italiane)</b>
📍 Piazza Giacomo Matteotti, 14, Perugia
• Ritira gratuitamente il Kit Postale (busta gialla)
• Acquista una Marca da bollo da 16,00 € in tabaccheria

📄 <b>Documenti da inserire nel kit:</b>
• Fotocopia di tutte le pagine del passaporto
• Certificato di iscrizione all'università
• Copia dell'assicurazione sanitaria
• Copia del Codice Fiscale
• Prova di mezzi economici
• Marca da bollo da 16 € applicata sul Modulo 1

💰 <b>Costo postale allo sportello:</b> Circa 130-140 €

📋 <b>Dopo l'invio:</b>
• Riceverai la Ricevuta postale e la data dell'appuntamento in Questura
• ⚠️ CONSERVA SEMPRE LA RICEVUTA! Ha pieno valore legale.
🌐 <b>Verifica stato:</b> <a href='https://www.portaleimmigrazione.it'>portaleimmigrazione.it</a>""",
            6: """🏦 <b>Passo 6: Apertura Conto Bancario</b>

━━━━━━━━━━━━━━━━━━━━━

🥇 <b>Postepay Evolution (Consigliata per i primi mesi):</b>
• ✅ Si apre con la sola Ricevuta del permesso postale!
• Dotata di IBAN italiano
• Canone annuo: 15 €
• Disponibile in qualsiasi ufficio postale

🥈 <b>UniCredit MyGenius Green / Intesa Sanpaolo:</b>
• Conti dedicati agli studenti universitari
• Spesso richiedono il permesso di soggiorno definitivo

📄 <b>Documenti richiesti:</b>
• Passaporto
• Codice Fiscale
• Ricevuta postale del permesso
• Contratto d'affitto o certificato di residenza""",
            7: """👆 <b>Passo 7: Fotosegnalamento e Ritiro Permesso</b>

━━━━━━━━━━━━━━━━━━━━━

👮 <b>Questura - Ufficio Immigrazione:</b>
📍 Via del Tabacchificio, 21, Ellera di Corciano

🚌 <b>Collegamenti:</b> Bus Linea G o treno regionale per Ellera

📄 <b>Documenti per il giorno dell'appuntamento:</b>
• Passaporto originale
• Ricevuta postale e foglio di convocazione
• 4 fototessere formato tessera identiche
• Originali di tutti i documenti inseriti nel kit

⏳ <b>Tempi di emissione:</b> 1 - 3 mesi
🌐 <b>Verifica stato:</b> <a href='https://www.portaleimmigrazione.it'>portaleimmigrazione.it</a>

🎉 <b>Congratulazioni!</b> Il tuo soggiorno legale in Italia è completato!"""
        }
        if step_id in it_steps:
            return it_steps[step_id], None, loc_keys.get(step_id)
        return "⚠️ Passo non trovato. Torna al menu della Guida.", None, None

    # زبان فارسی (پیش‌فرض)
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

def get_guide_main_keyboard(lang_code: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد منوی اصلی راهنما"""
    
    buttons = []
    steps = STEPS_DATA_LOCALIZED.get(lang_code, STEPS_DATA_LOCALIZED["fa"])
    
    # مراحل
    for key, step in steps.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{step['emoji']} {key}. {step['title']}",
                callback_data=f"guide:step_{key}"
            )
        ])
    
    # بخش‌های دیگر بر اساس زبان
    if lang_code == "en":
        buttons.extend([
            [
                InlineKeyboardButton(text="💰 Living Costs", callback_data="guide:costs"),
                InlineKeyboardButton(text="📍 Locations", callback_data="guide:locations"),
            ],
            [
                InlineKeyboardButton(text="📱 Essential Apps", callback_data="guide:apps"),
                InlineKeyboardButton(text="💡 Golden Tips", callback_data="guide:tips"),
            ],
            [
                InlineKeyboardButton(text="❓ FAQ", callback_data="guide:faq"),
                InlineKeyboardButton(text="🔍 Search Guide", callback_data="guide:search"),
            ],
            [
                InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
            ],
        ])
    elif lang_code == "it":
        buttons.extend([
            [
                InlineKeyboardButton(text="💰 Costo della Vita", callback_data="guide:costs"),
                InlineKeyboardButton(text="📍 Luoghi Importanti", callback_data="guide:locations"),
            ],
            [
                InlineKeyboardButton(text="📱 App Utili", callback_data="guide:apps"),
                InlineKeyboardButton(text="💡 Consigli Utili", callback_data="guide:tips"),
            ],
            [
                InlineKeyboardButton(text="❓ FAQ", callback_data="guide:faq"),
                InlineKeyboardButton(text="🔍 Cerca nella Guida", callback_data="guide:search"),
            ],
            [
                InlineKeyboardButton(text="🏠 Menu Principale", callback_data="main_menu"),
            ],
        ])
    else:
        buttons.extend([
            [
                InlineKeyboardButton(text="💰 هزینه‌های زندگی", callback_data="guide:costs"),
                InlineKeyboardButton(text="📍 لوکیشن‌ها", callback_data="guide:locations"),
            ],
            [
                InlineKeyboardButton(text="📱 اپلیکیشن‌های ضروری", callback_data="guide:apps"),
                InlineKeyboardButton(text="💡 نکات طلایی", callback_data="guide:tips"),
            ],
            [
                InlineKeyboardButton(text="❓ سوالات متداول", callback_data="guide:faq"),
                InlineKeyboardButton(text="🔍 جستجو در راهنما", callback_data="guide:search"),
            ],
            [
                InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu"),
            ],
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_step_nav_keyboard(step_id: int, lang_code: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد ناوبری مراحل"""
    
    buttons = []
    nav_row = []
    
    prev_txt = f"⬅️ مرحله {step_id - 1}" if lang_code == "fa" else (f"⬅️ Step {step_id - 1}" if lang_code == "en" else f"⬅️ Passo {step_id - 1}")
    next_txt = f"مرحله {step_id + 1} ➡️" if lang_code == "fa" else (f"Step {step_id + 1} ➡️" if lang_code == "en" else f"Passo {step_id + 1} ➡️")
    
    # دکمه قبلی
    if step_id > 1:
        nav_row.append(
            InlineKeyboardButton(
                text=prev_txt,
                callback_data=f"guide:step_{step_id - 1}"
            )
        )
    
    # دکمه بعدی
    if step_id < len(STEPS_DATA):
        nav_row.append(
            InlineKeyboardButton(
                text=next_txt,
                callback_data=f"guide:step_{step_id + 1}"
            )
        )
    
    if nav_row:
        buttons.append(nav_row)
    
    # لوکیشن مرتبط
    _, _, loc_key = get_step_content(step_id, lang_code)
    if loc_key:
        loc_txt = "📍 نمایش لوکیشن" if lang_code == "fa" else ("📍 Show Location" if lang_code == "en" else "📍 Mostra Posizione")
        buttons.append([
            InlineKeyboardButton(
                text=loc_txt,
                callback_data=f"guide:loc_{loc_key}"
            )
        ])
    
    # بازگشت و سوال
    back_txt = "🔙 منوی راهنما" if lang_code == "fa" else ("🔙 Guide Menu" if lang_code == "en" else "🔙 Menu Guida")
    consult_txt = "❓ سوال دارم" if lang_code == "fa" else ("❓ Ask a Question" if lang_code == "en" else "❓ Fai una Domanda")
    
    buttons.extend([
        [
            InlineKeyboardButton(text=back_txt, callback_data="guide:main"),
        ],
        [
            InlineKeyboardButton(text=consult_txt, callback_data="consult"),
        ],
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_locations_keyboard(lang_code: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد لوکیشن‌ها"""
    
    buttons = []
    for key, loc in LOCATIONS.items():
        buttons.append([
            InlineKeyboardButton(
                text=loc["title"],
                callback_data=f"guide:loc_{key}"
            )
        ])
    
    back_txt = "🔙 منوی راهنما" if lang_code == "fa" else ("🔙 Guide Menu" if lang_code == "en" else "🔙 Menu Guida")
    buttons.append([
        InlineKeyboardButton(text=back_txt, callback_data="guide:main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_to_guide_keyboard(lang_code: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد بازگشت"""
    back_txt = "🔙 منوی راهنما" if lang_code == "fa" else ("🔙 Guide Menu" if lang_code == "en" else "🔙 Menu Guida")
    main_txt = "🏠 منوی اصلی" if lang_code == "fa" else ("🏠 Main Menu" if lang_code == "en" else "🏠 Menu Principale")
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=back_txt, callback_data="guide:main"),
            InlineKeyboardButton(text=main_txt, callback_data="main_menu"),
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
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    if lang_code == "en":
        text = """🗺 <b>Comprehensive Perugia Student Guide</b>

━━━━━━━━━━━━━━━━━━━━━

🎉 Welcome to beautiful Perugia!

This guide covers all key bureaucratic steps, housing, and everyday student life in Italy.

<b>Complete the steps in sequential order:</b>

👇 Select an option:"""
    elif lang_code == "it":
        text = """🗺 <b>Guida Completa per Studenti a Perugia</b>

━━━━━━━━━━━━━━━━━━━━━

🎉 Benvenuto nella splendida Perugia!

Questa guida ti accompagna in tutti i passaggi burocratici, alloggio e vita universitaria.

<b>Segui i passaggi in ordine progressivo:</b>

👇 Scegli un'opzione:"""
    else:
        text = """🗺 <b>راهنمای کامل پروجا</b>

━━━━━━━━━━━━━━━━━━━━━

🎉 به شهر زیبای پروجا خوش آمدید!

این راهنما تمام مراحل قانونی و زندگی روزمره را پوشش می‌دهد.

<b>مراحل را به ترتیب انجام دهید:</b>

👇 انتخاب کنید:"""
    
    await safe_edit_text(
        callback.message,
        text=text,
        reply_markup=get_guide_main_keyboard(lang_code)
    )
    
    await callback.answer()


@router.message(Command("guide", "راهنما"))
async def cmd_guide(message: Message, state: FSMContext):
    """دستور راهنما"""
    
    await state.clear()
    user_id = message.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    if lang_code == "en":
        text = """🗺 <b>Comprehensive Perugia Student Guide</b>

━━━━━━━━━━━━━━━━━━━━━

🎉 Welcome to Perugia!

👇 Select an option:"""
    elif lang_code == "it":
        text = """🗺 <b>Guida Completa per Studenti a Perugia</b>

━━━━━━━━━━━━━━━━━━━━━

🎉 Benvenuto a Perugia!

👇 Scegli un'opzione:"""
    else:
        text = """🗺 <b>راهنمای کامل پروجا</b>

━━━━━━━━━━━━━━━━━━━━━

🎉 به شهر زیبای پروجا خوش آمدید!

👇 انتخاب کنید:"""
    
    await message.answer(
        text=text,
        reply_markup=get_guide_main_keyboard(lang_code),
        parse_mode=ParseMode.HTML
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ۷. هندلرها - مراحل
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("guide:step_"))
@router.callback_query(F.data.startswith("guide_step_"))
async def show_step_detail(callback: CallbackQuery):
    """نمایش جزئیات مرحله"""
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    # استخراج شماره مرحله
    step_str = callback.data.split("_")[-1]
    
    if not step_str.isdigit():
        err_txt = "❌ Error!" if lang_code == "en" else ("❌ Errore!" if lang_code == "it" else "❌ خطا!")
        await callback.answer(err_txt, show_alert=True)
        return
    
    step_id = int(step_str)
    
    if step_id < 1 or step_id > len(STEPS_DATA):
        err_txt = "❌ Invalid step!" if lang_code == "en" else ("❌ Passo non valido!" if lang_code == "it" else "❌ مرحله نامعتبر!")
        await callback.answer(err_txt, show_alert=True)
        return
    
    content, photo_url, _ = get_step_content(step_id, lang_code)
    
    await safe_edit_text(
        callback.message,
        text=content,
        reply_markup=get_step_nav_keyboard(step_id, lang_code)
    )
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ۸. هندلرها - هزینه‌ها
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "guide:costs")
@router.callback_query(F.data == "guide_costs")
async def guide_costs(callback: CallbackQuery):
    """هزینه‌های زندگی"""
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    if lang_code == "en":
        text = """💰 <b>Monthly Cost of Living in Perugia (2025)</b>

━━━━━━━━━━━━━━━━━━━━━

🏠 <b>Accommodation:</b>
• Shared Room: €300 - €380
• Single Room: €380 - €450
• Full Studio / Flat: €550 - €800

🍽 <b>Food & Groceries:</b>
• Home Cooking: €150 - €200
• University Mensa (ADISU): €4 - €6 per meal
• Dining out: +€50 - €100

🚌 <b>Transport:</b>
• Monthly Bus Pass (Salgo): €25 - €35
• Minimetrò: €1.50 single ride

📱 <b>Mobile & Internet:</b>
• SIM plan (Iliad): €10 - €15

⚡ <b>Utilities (if not included):</b>
• Electricity/Gas/Water: €50 - €80

☕ <b>Leisure & Personal:</b>
• €100 - €150

━━━━━━━━━━━━━━━━━━━━━

📊 <b>Estimated Total:</b>
<b>€650 - €1,000 / month</b>

💡 <b>With DSU Regional Scholarship:</b>
Housing & cafeteria meals are largely subsidized!"""
    elif lang_code == "it":
        text = """💰 <b>Costo della Vita Mensile a Perugia (2025)</b>

━━━━━━━━━━━━━━━━━━━━━

🏠 <b>Alloggio:</b>
• Posto letto in doppia: 300 - 380 €
• Stanza singola: 380 - 450 €
• Monolocale / Bilocale: 550 - 800 €

🍽 <b>Cibo e Spesa:</b>
• Spesa a casa: 150 - 200 €
• Mensa universitaria ADISU: 4 - 6 € a pasto
• Cene fuori: +50 - 100 €

🚌 <b>Trasporti:</b>
• Abbonamento mensile bus (Salgo): 25 - 35 €
• Minimetrò: 1,50 € corsa singola

📱 <b>SIM e Internet:</b>
• Piano mobile (Iliad): 10 - 15 €

⚡ <b>Utenze (se escluse):</b>
• Luce/Gas/Acqua: 50 - 80 €

☕ <b>Svago e varie:</b>
• 100 - 150 €

━━━━━━━━━━━━━━━━━━━━━

📊 <b>Totale stimato:</b>
<b>650 - 1.000 € / mese</b>

💡 <b>Con Borsa di Studio DSU:</b>
I costi di vitto e alloggio possono essere coperti per gli aventi diritto!"""
    else:
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
        reply_markup=get_back_to_guide_keyboard(lang_code)
    )
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ۹. هندلرها - لوکیشن‌ها
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "guide:locations")
@router.callback_query(F.data == "guide_locations")
async def guide_locations(callback: CallbackQuery):
    """منوی لوکیشن‌ها"""
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    if lang_code == "en":
        text = """📍 <b>Important Student Locations in Perugia</b>

━━━━━━━━━━━━━━━━━━━━━

Tap any venue below to send its official geolocation pin.

You can directly navigate with Google Maps or Apple Maps! 🗺

👇 Select a location:"""
    elif lang_code == "it":
        text = """📍 <b>Punti di Interesse per Studenti a Perugia</b>

━━━━━━━━━━━━━━━━━━━━━

Tocca un luogo per visualizzare la posizione sulla mappa di Telegram.

Puoi avviare direttamente la navigazione GPS! 🗺

👇 Scegli un punto:"""
    else:
        text = """📍 <b>لوکیشن‌های مهم پروجا</b>

━━━━━━━━━━━━━━━━━━━━━

روی هر مکان کلیک کنید تا پین واقعی در تلگرام باز شود.

می‌توانید مستقیم مسیریابی کنید! 🗺

👇 انتخاب کنید:"""
    
    await safe_edit_text(
        callback.message,
        text=text,
        reply_markup=get_locations_keyboard(lang_code)
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("guide:loc_"))
@router.callback_query(F.data.startswith("loc_send_"))
async def send_location(callback: CallbackQuery):
    """ارسال لوکیشن"""
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    # استخراج کلید
    if "loc_send_" in callback.data:
        key = callback.data.replace("loc_send_", "")
    else:
        key = callback.data.replace("guide:loc_", "")
    
    if key not in LOCATIONS:
        err_txt = "❌ Location not found!" if lang_code == "en" else ("❌ Luogo non trovato!" if lang_code == "it" else "❌ مکان یافت نشد!")
        await callback.answer(err_txt, show_alert=True)
        return
    
    loc = LOCATIONS[key]
    
    # ارسال Venue
    await callback.message.answer_venue(
        latitude=loc["lat"],
        longitude=loc["lon"],
        title=loc["title"],
        address=loc["address"]
    )
    
    hours_lbl = "Opening Hours" if lang_code == "en" else ("Orari di apertura" if lang_code == "it" else "ساعت کاری")
    
    # پیام توضیحی
    info_text = f"""📍 <b>{loc['title']}</b>

📮 {loc['address']}

📝 {loc['desc']}

⏰ <b>{hours_lbl}:</b>
{loc['hours']}"""
    
    await callback.message.answer(
        text=info_text,
        reply_markup=get_back_to_guide_keyboard(lang_code),
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
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    if lang_code == "en":
        text = """📱 <b>Essential Student Apps in Italy</b>

━━━━━━━━━━━━━━━━━━━━━

These mobile apps make daily life and transit much easier:

"""
    elif lang_code == "it":
        text = """📱 <b>Applicazioni Utili per Studenti</b>

━━━━━━━━━━━━━━━━━━━━━

Le app indispensabili per la vita universitaria e i trasporti:

"""
    else:
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
    
    back_txt = "🔙 منوی راهنما" if lang_code == "fa" else ("🔙 Guide Menu" if lang_code == "en" else "🔙 Menu Guida")
    buttons.append([
        InlineKeyboardButton(text=back_txt, callback_data="guide:main")
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
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    if lang_code == "en":
        text = """💡 <b>Golden Advice & Key Warnings</b>

━━━━━━━━━━━━━━━━━━━━━

🔴 <b>Crucial Warnings:</b>

⚠️ Submit your residence permit kit within <b>8 business days</b>! Delays can cause serious issues.

⚠️ Watch out for rental scams! Never transfer deposits without an official contract.

⚠️ Never lose your Postal Receipt (Ricevuta)! It is your primary proof of legal stay.

⚠️ W.A.I. health policy might not suffice for residence renewal; check with Questura.

━━━━━━━━━━━━━━━━━━━━━

🟢 <b>Top Practical Tips:</b>

✅ <b>Iliad</b> is the most cost-effective SIM for incoming students.

✅ <b>Postepay Evolution</b> can be opened with just your postal Ricevuta.

✅ Download <b>Salgo</b> to purchase bus and minimetrò tickets easily.

✅ University cafeterias (ADISU Mensa) provide full student meals starting at €4.

✅ Use <b>Too Good To Go</b> to save significantly on bakeries & groceries.

✅ Arrive early in the morning when visiting the Questura or public offices.

━━━━━━━━━━━━━━━━━━━━━

🇮🇹 You've got this! Best of luck with your journey! ✨"""
    elif lang_code == "it":
        text = """💡 <b>Consigli d'Oro e Avvertenze</b>

━━━━━━━━━━━━━━━━━━━━━

🔴 <b>Avvertenze importanti:</b>

⚠️ Invia il kit del permesso entro <b>8 giorni lavorativi</b> dall'ingresso!

⚠️ Attenzione alle truffe sugli affitti: richiedi sempre un regolare contratto registrato.

⚠️ Custodisci la Ricevuta postale: è il tuo documento provvisorio valido a tutti gli effetti.

━━━━━━━━━━━━━━━━━━━━━

🟢 <b>Consigli pratici:</b>

✅ <b>Iliad</b> offre ottimi pacchetti con SIM o eSIM attive subito.

✅ <b>Postepay Evolution</b> si attiva subito con la sola Ricevuta postale.

✅ Usa l'app <b>Salgo</b> per acquistare i titoli di viaggio per autobus e minimetrò.

✅ Le mense ADISU offrono pasti completi di ottima qualità a prezzi calmierati.

✅ Scarica <b>Too Good To Go</b> per risparmiare su alimentari e prodotti da forno.

✅ Presentati presto al mattino presso gli uffici pubblici per evitare lunghe attese.

━━━━━━━━━━━━━━━━━━━━━

🇮🇹 Buona permanenza e buon studio a Perugia! ✨"""
    else:
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
        reply_markup=get_back_to_guide_keyboard(lang_code)
    )
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ۱۲. هندلرها - FAQ
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "guide:faq")
async def guide_faq(callback: CallbackQuery):
    """سوالات متداول"""
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    if lang_code == "en":
        text = """❓ <b>Frequently Asked Questions (FAQ)</b>

━━━━━━━━━━━━━━━━━━━━━

<b>1. How many days after arrival must I apply for Permesso?</b>
⚠️ Within <b>8 business days!</b> This is mandatory by Italian immigration law.

<b>2. Can I open a bank account with just the postal receipt (Ricevuta)?</b>
✅ Yes! <b>Postepay Evolution</b> at Poste Italiane opens with just your Ricevuta and passport.

<b>3. Is W.A.I. insurance sufficient for permit renewal?</b>
⚠️ For the <b>first permit</b> it is accepted. For <b>renewal</b>, Questura often requests SSN public registration.

<b>4. What is the average monthly cost of living in Perugia?</b>
💰 <b>€650 - €1,000</b> (Substantially lower with DSU regional housing/dining perks).

<b>5. Which mobile SIM provider is best?</b>
🥇 <b>Iliad</b>: €9.99/mo for 150GB + unlimited local minutes. Fast setup with eSIM.

━━━━━━━━━━━━━━━━━━━━━

💬 Have another specific question? Use our consultation and advisory desk!"""
        buttons = [
            [InlineKeyboardButton(text="💬 Ask a Question", callback_data="consult")],
            [InlineKeyboardButton(text="🔙 Guide Menu", callback_data="guide:main")],
        ]
    elif lang_code == "it":
        text = """❓ <b>Domande Frequenti (FAQ)</b>

━━━━━━━━━━━━━━━━━━━━━

<b>1. Entro quanti giorni dall'arrivo devo richiedere il permesso?</b>
⚠️ Entro <b>8 giorni lavorativi!</b>

<b>2. Posso aprire un conto bancario con la sola Ricevuta postale?</b>
✅ Sì! La carta <b>Postepay Evolution</b> di Poste Italiane è accessibile con la sola Ricevuta.

<b>3. L'assicurazione W.A.I. è accettata per il rinnovo?</b>
⚠️ È ottima per il <b>primo rilascio</b>, mentre per i <b>rinnovi</b> la Questura richiede spesso l'iscrizione al SSN.

<b>4. Qual è il costo della vita mensile medio a Perugia?</b>
💰 Circa <b>650 - 1.000 €</b> a seconda dell'alloggio.

<b>5. Quale operatore telefonico è consigliato?</b>
🥇 <b>Iliad</b>: 9,99 €/mese con 150GB e minuti illimitati.

━━━━━━━━━━━━━━━━━━━━━

💬 Hai altre domande specifiche? Contatta il nostro servizio di consulenza!"""
        buttons = [
            [InlineKeyboardButton(text="💬 Fai una Domanda", callback_data="consult")],
            [InlineKeyboardButton(text="🔙 Menu Guida", callback_data="guide:main")],
        ]
    else:
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
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    await state.set_state(GuideStates.searching)
    
    if lang_code == "en":
        text = """🔍 <b>Search Student Guide</b>

━━━━━━━━━━━━━━━━━━━━━

Type your search keyword:

💡 <i>Examples: permesso, insurance, bank, sim, questura</i>

❌ Cancel: /cancel"""
        cancel_txt = "❌ Cancel"
    elif lang_code == "it":
        text = """🔍 <b>Cerca nella Guida</b>

━━━━━━━━━━━━━━━━━━━━━

Digita la parola chiave da cercare:

💡 <i>Esempi: permesso, assicurazione, conto, sim, questura</i>

❌ Annulla: /cancel"""
        cancel_txt = "❌ Annulla"
    else:
        text = """🔍 <b>جستجو در راهنما</b>

━━━━━━━━━━━━━━━━━━━━━

عبارت مورد نظر را بنویسید:

💡 <i>مثال: پرمسو، بیمه، بانک، سیم‌کارت</i>

❌ لغو: /cancel"""
        cancel_txt = "❌ لغو"
    
    await safe_edit_text(
        callback.message,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=cancel_txt, callback_data="guide:main")]
        ])
    )
    
    await callback.answer()


@router.message(GuideStates.searching)
async def process_search(message: Message, state: FSMContext):
    """پردازش جستجو"""
    user_id = message.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    query = (message.text or "").strip()
    
    if query.lower() in ["/cancel", "لغو", "cancel", "annulla"]:
        await state.clear()
        cancel_msg = "❌ Search cancelled." if lang_code == "en" else ("❌ Ricerca annullata." if lang_code == "it" else "❌ جستجو لغو شد.")
        await message.answer(
            cancel_msg,
            reply_markup=get_back_to_guide_keyboard(lang_code)
        )
        return
    
    if len(query) < 2:
        warn_txt = "⚠️ Please enter at least 2 characters." if lang_code == "en" else ("⚠️ Inserisci almeno 2 caratteri." if lang_code == "it" else "⚠️ حداقل ۲ کاراکتر وارد کنید.")
        await message.answer(warn_txt)
        return
    
    await state.clear()
    
    results = search_in_guide(query)
    
    res_hdr = f"🔍 <b>Results for:</b> <code>{query}</code>\n\n" if lang_code == "en" else (f"🔍 <b>Risultati per:</b> <code>{query}</code>\n\n" if lang_code == "it" else f"🔍 <b>نتایج جستجو برای:</b> <code>{query}</code>\n\n")
    text = res_hdr + "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not results:
        no_res = "📭 <i>No matching items found.</i>\n\n💡 Try another keyword." if lang_code == "en" else ("📭 <i>Nessun risultato trovato.</i>\n\n💡 Prova con un'altra parola." if lang_code == "it" else "📭 <i>نتیجه‌ای یافت نشد.</i>\n\n💡 عبارت دیگری امتحان کنید.")
        text += no_res
        keyboard = get_back_to_guide_keyboard(lang_code)
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
        
        new_search_txt = "🔍 New Search" if lang_code == "en" else ("🔍 Nuova Ricerca" if lang_code == "it" else "🔍 جستجوی جدید")
        guide_menu_txt = "🔙 Guide Menu" if lang_code == "en" else ("🔙 Menu Guida" if lang_code == "it" else "🔙 منوی راهنما")
        
        buttons.append([
            InlineKeyboardButton(text=new_search_txt, callback_data="guide:search")
        ])
        buttons.append([
            InlineKeyboardButton(text=guide_menu_txt, callback_data="guide:main")
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