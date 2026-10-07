# handlers/cmd_start.py
# هندلر شروع و مدیریت زبان - نسخه نهایی و هماهنگ با AI Handler v5.0
# ژانویه ۲۰۲۵

"""
🚀 هندلر اصلی SmartStudentBot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
این ماژول وظایف زیر را بر عهده دارد:
    ✅ مدیریت دستور /start و خوش‌آمدگویی
    ✅ سیستم مدیریت زبان (i18n) که توسط سایر هندلرها استفاده می‌شود
    ✅ نمایش منوی اصلی (Dashboard)
    ✅ مدیریت تغییر زبان
    ✅ توابع کمکی مشترک برای دسترسی به متون زبان
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Union, List
from contextlib import suppress

from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery, WebAppInfo
from aiogram.exceptions import TelegramBadRequest

from config import settings

# تنظیمات لاگر
logger = logging.getLogger(__name__)

# راه‌اندازی Router
router = Router()
router.name = "cmd_start"

# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱: تنظیمات زبان و متغیرهای جهانی
# ═══════════════════════════════════════════════════════════════════════════════

# کش ترجمه‌ها در حافظه برای جلوگیری از خواندن مکرر فایل
_lang_cache: Dict[str, dict] = {}

# ذخیره زبان کاربر (در حافظه موقت - در نسخه پروداکشن باید به دیتابیس متصل شود)
_user_languages: Dict[int, str] = {}

# زبان پیش‌فرض
DEFAULT_LANGUAGE = "fa"

# زبان‌های پشتیبانی شده
SUPPORTED_LANGUAGES = {
    "fa": {"name": "فارسی", "flag": "🇮🇷", "dir": "rtl"},
    "en": {"name": "English", "flag": "🇬🇧", "dir": "ltr"},
    "it": {"name": "Italiano", "flag": "🇮🇹", "dir": "ltr"},
}

# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲: توابع مدیریت زبان (Core Language Services)
# این توابع توسط AI Handler و سایر بخش‌ها فراخوانی می‌شوند
# ═══════════════════════════════════════════════════════════════════════════════

def load_lang(lang_code: str = "fa") -> dict:
    """
    بارگذاری فایل زبان با کش‌گذاری
    
    Args:
        lang_code: کد زبان (fa, en, it)
        
    Returns:
        دیکشنری حاوی متون ترجمه شده
    """
    # اگر در کش موجود است، همان را برگردان
    if lang_code in _lang_cache:
        return _lang_cache[lang_code]
    
    # مسیر فایل زبان (فرض بر این است که پوشه lang در روت پروژه است)
    lang_file = Path(f"lang/{lang_code}.json")
    
    try:
        if lang_file.exists():
            with open(lang_file, encoding="utf-8") as f:
                data = json.load(f)
                _lang_cache[lang_code] = data
                # اضافه کردن کد زبان به دیکشنری برای دسترسی راحت‌تر
                data["code"] = lang_code
                logger.debug(f"📚 Language loaded successfully: {lang_code}")
                return data
        else:
            logger.warning(f"⚠️ Language file not found: {lang_code}, using default")
            if lang_code != DEFAULT_LANGUAGE:
                return load_lang(DEFAULT_LANGUAGE)
            return {"code": "fa"}
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in language file {lang_code}: {e}")
        return {"code": lang_code}
    except Exception as e:
        logger.error(f"❌ Error loading language {lang_code}: {e}")
        return {"code": lang_code}


def get_user_lang(user_id: int) -> dict:
    """
    دریافت دیکشنری کامل زبان کاربر
    (این تابع توسط AI Handler استفاده می‌شود)
    
    Args:
        user_id: شناسه کاربر
        
    Returns:
        دیکشنری متون زبان انتخاب شده کاربر
    """
    lang_code = _user_languages.get(user_id, DEFAULT_LANGUAGE)
    return load_lang(lang_code)


def get_user_lang_code(user_id: int) -> str:
    """
    دریافت فقط کد زبان کاربر
    """
    return _user_languages.get(user_id, DEFAULT_LANGUAGE)


def set_user_lang(user_id: int, lang_code: str) -> None:
    """
    تنظیم زبان کاربر
    """
    if lang_code in SUPPORTED_LANGUAGES:
        _user_languages[user_id] = lang_code
        logger.info(f"🌐 User {user_id} language set to: {lang_code}")


def get_text(lang: Union[dict, str], key: str, default: str = "") -> str:
    """
    دریافت متن از دیکشنری زبان با مقدار پیش‌فرض
    (این تابع توسط AI Handler استفاده می‌شود)
    
    Args:
        lang: دیکشنری زبان یا کد زبان
        key: کلید متن مورد نظر
        default: متن پیش‌فرض در صورت پیدا نشدن
        
    Returns:
        متن ترجمه شده
    """
    # اگر ورودی کد زبان بود، فایل را بارگذاری کن
    if isinstance(lang, str):
        lang = load_lang(lang)
    
    return lang.get(key, default or key)


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۳: توابع کمکی UI (مشابه AI Handler برای پایداری)
# ═══════════════════════════════════════════════════════════════════════════════

async def safe_edit_text(
    message: Message, 
    text: str, 
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "HTML"
) -> bool:
    """ویرایش ایمن پیام بدون کرش کردن در صورت عدم تغییر"""
    try:
        await message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=True
        )
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            return True
        logger.warning(f"⚠️ safe_edit_text failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ safe_edit_text unexpected error: {e}")
        return False


async def safe_answer(callback: CallbackQuery, text: str = "", show_alert: bool = False):
    """پاسخ ایمن به کالبک"""
    with suppress(Exception):
        await callback.answer(text=text, show_alert=show_alert)


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۴: کیبوردها
# ═══════════════════════════════════════════════════════════════════════════════

def get_language_keyboard() -> InlineKeyboardMarkup:
    """کیبورد انتخاب زبان"""
    buttons = []
    for code, info in SUPPORTED_LANGUAGES.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{info['flag']} {info['name']}",
                callback_data=f"lang_{code}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_menu(lang: dict) -> InlineKeyboardMarkup:
    """
    منوی اصلی کامل با ساختاربندی و اولویت‌بندی استاندارد بر اساس نیاز دانشجو
    """
    def t(key, default): return get_text(lang, key, default)

    buttons = [
        # ردیف طلایی: مینی‌اپلیکیشن تلگرام (Telegram Mini App)
        [
            InlineKeyboardButton(
                text=t("webapp_btn", "🌟 ورود به مینی‌اپلیکیشن پروجا (Mini App) 🚀"),
                web_app=WebAppInfo(url=settings.WEBAPP_URL) if settings.WEBAPP_URL else None,
                callback_data="open_webapp" if not settings.WEBAPP_URL else None
            ),
        ],
        # ردیف ۱: مهم‌ترین خدمات پذیرش و بورسیه (اولویت اول دانشجو)
        [
            InlineKeyboardButton(text=t("isee", "🧮 محاسبه ISEE"), callback_data="isee"),
            InlineKeyboardButton(text=t("consult", "💬 مشاوره تحصیلی"), callback_data="consult"),
        ],
        # ردیف ۲: مسکن و هزینه‌های زندگی
        [
            InlineKeyboardButton(text=t("roommate", "🏠 هم‌خانه‌یابی و مسکن"), callback_data="roommate"),
            InlineKeyboardButton(text=t("costs", "💰 برآورد مخارج پروجا"), callback_data="cost_main"),
        ],
        # ردیف ۳: راهنما و مکان‌های شهری
        [
            InlineKeyboardButton(text=t("places", "📍 مکان‌های مهم پروجا"), callback_data="places"),
            InlineKeyboardButton(text=t("guide", "📖 راهنمای زندگی و تحصیل"), callback_data="guide_main"),
        ],
        # ردیف ۴: خدمات دانشجویی (بازارچه و آموزش ایتالیایی)
        [
            InlineKeyboardButton(text=t("market", "🛒 بازارچه دست‌دوم"), callback_data="market"),
            InlineKeyboardButton(text=t("italy", "🇮🇹 یادگیری ایتالیایی"), callback_data="italy"),
        ],
        # ردیف ۵: اخبار و آب‌وهوا
        [
            InlineKeyboardButton(text=t("weather", "🌤 آب‌وهوای پروجا"), callback_data="weather"),
            InlineKeyboardButton(text=t("news", "📰 اخبار دانشگاه UniPG"), callback_data="news"),
        ],
        # ردیف ۶: هوش مصنوعی و ترجمه
        [
            InlineKeyboardButton(text=t("ai_chat", "🤖 دستیار هوشمند AI"), callback_data="ai_chat"),
            InlineKeyboardButton(text=t("translate", "🌐 ترجمه تخصصی متن"), callback_data="ai:translate_menu"),
        ],
        # ردیف ۷: رویدادها و داشبورد روزانه
        [
            InlineKeyboardButton(text=t("today", "📅 داشبورد من"), callback_data="today"),
            InlineKeyboardButton(text=t("events", "🎉 رویدادها و تورها"), callback_data="events"),
        ],
        # ردیف ۸: پشتیبانی و تغییر زبان
        [
            InlineKeyboardButton(text=t("feedback", "📝 پشتیبانی و بازخورد"), callback_data="feedback"),
            InlineKeyboardButton(text=t("language", "🌍 تغییر زبان (Language)"), callback_data="change_lang"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_button(lang: dict) -> InlineKeyboardMarkup:
    """دکمه بازگشت ساده"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_text(lang, "back_to_menu", "🔙 بازگشت به منوی اصلی"),
            callback_data="main_menu"
        )]
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۵: هندلرها (Handlers)
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    هندلر دستور /start
    نقطه شروع تعامل کاربر با ربات همراه با معرفی جامع تمامی امکانات
    """
    user = message.from_user
    logger.info(f"👤 Start command from user: {user.id}")

    # اضافه کردن کاربر به دیتابیس (پروفایل متمرکز)
    from database import db_manager
    lang_code = get_user_lang_code(user.id)
    await db_manager.upsert_user(user.id, {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "language": lang_code
    })

    welcome_msg = """🎓 <b>به SmartStudentBot پروجا خوش آمدید!</b>
━━━━━━━━━━━━━━━━━━━━━
🇮🇹 <b>جامع‌ترین سامانه و دستیار هوشمند دانشجویان ایرانی در پروجا (ایتالیا)</b>

این ربات به عنوان یک پلتفرم همه‌جانبه، برای پاسخ به تمامی نیازهای تحصیلی و زندگی شما طراحی شده است:

✨ <b>خدمات اصلی این سامانه:</b>
🧮 <b>شبیه‌ساز و محاسبه‌گر ISEE:</b> محاسبه دقیق عدد ایزه برای دریافت بورسیه استانی ADiSU و معافیت شهریه
💬 <b>مشاوره تخصصی تحصیلی:</b> ثبت پرونده پذیرش، اپلای و ویزای تحصیلی با امکان بارگذاری مدارک و رزومه
🏠 <b>سامانه هم‌خانه‌یابی و مسکن:</b> جستجو، فیلتر و ثبت آگهی‌های اتاق و خانه دانشجویی با دسته‌بندی دقیق
💰 <b>برآورد مخارج و هزینه‌ها:</b> تخمین دقیق و به روز هزینه‌های ماهانه زندگی در پروجا
📍 <b>مکان‌های مهم شهر:</b> دسترسی به نقشه و آدرس ادارات (Questura, Agenzia)، خوابگاه‌ها و سلف‌ها
🛒 <b>بازارچه دست‌دوم دانشجویی:</b> خرید و فروش کتاب، لوازم منزل و دوچرخه با امکان ثبت عکس
📖 <b>راهنمای گام‌به‌گام:</b> از اخذ کد مالیاتی و پرمسو تا افتتاح حساب بانکی و بیمه سلامت
🤖 <b>دستیار هوش مصنوعی و مترجم:</b> پاسخ سریع به سوالات تحصیلی و ترجمه ایتالیایی/فارسی/انگلیسی
🌤 <b>آب‌وهوا و اخبار:</b> وضعیت جوی زنده و آخرین اطلاعیه‌های رسمی UniPG

━━━━━━━━━━━━━━━━━━━━━
🌐 <b>لطفاً برای شروع، زبان خود را انتخاب کنید:</b>
<i>Please select your language to get started:</i>
<i>Per favore seleziona la tua lingua per iniziare:</i>"""

    await message.answer(
        welcome_msg,
        reply_markup=get_language_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """نمایش مستقیم منوی اصلی"""
    lang = get_user_lang(message.from_user.id)
    await message.answer(
        get_text(lang, "main_menu_title", "🏠 <b>منوی اصلی</b>"),
        reply_markup=get_main_menu(lang),
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """نمایش راهنما"""
    lang = get_user_lang(message.from_user.id)
    help_text = get_text(lang, "help_text", """
🆘 <b>راهنمای استفاده</b>

دستورات موجود:
/start - شروع مجدد و انتخاب زبان
/menu - باز کردن منوی اصلی
/ai - چت با هوش مصنوعی
/help - نمایش همین پیام

برای استفاده از امکانات، از دکمه‌های منوی شیشه‌ای استفاده کنید.
    """)
    
    await message.answer(
        help_text,
        reply_markup=get_back_button(lang),
        parse_mode="HTML"
    )


@router.message(Command("webapp"))
@router.message(Command("app"))
async def cmd_webapp(message: Message):
    """باز کردن مستقیم مینی‌اپلیکیشن تلگرام"""
    lang = get_user_lang(message.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_text(lang, "webapp_btn", "🌟 ورود به مینی‌اپلیکیشن پروجا (Mini App) 🚀"),
            web_app=WebAppInfo(url=settings.WEBAPP_URL) if settings.WEBAPP_URL else None,
            url=settings.WEBAPP_URL if not settings.WEBAPP_URL.startswith("https://") else None
        )],
        [InlineKeyboardButton(
            text=get_text(lang, "back_to_menu", "🔙 بازگشت به منوی اصلی"),
            callback_data="main_menu"
        )]
    ])
    await message.answer(
        "✨ <b>مینی‌اپلیکیشن اختصاصی دانشجویان پروجا</b> 🇮🇹\n\n"
        "برای دسترسی به پنل زیبا و مدرن، جستجوی هم‌اتاقی، چت هوش مصنوعی، آب‌وهوا و خدمات شهری، روی دکمه زیر کلیک کنید:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "open_webapp")
async def cb_open_webapp(callback: CallbackQuery):
    """پاسخ و هدایت کاربر به مینی‌اپلیکیشن تلگرام یا مرورگر"""
    url = settings.WEBAPP_URL or "http://localhost:5173"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 باز کردن مینی‌اپ در تلگرام", web_app=WebAppInfo(url=url))],
        [InlineKeyboardButton(text="🌐 باز کردن مستقیم در مرورگر", url=url)],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ])
    await callback.message.answer(
        "🚀 <b>مینی‌اپلیکیشن هوشمند دانشجویان پروجا</b>\n\n"
        "می‌توانید مینی‌اپلیکیشن را مستقیماً داخل تلگرام یا در مرورگر باز کنید:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۶: پردازش Callback های زبان و منو
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("lang_"))
async def process_language_selection(callback: CallbackQuery):
    """پردازش انتخاب زبان توسط کاربر"""
    lang_code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    if lang_code not in SUPPORTED_LANGUAGES:
        await safe_answer(callback, "❌ Invalid language", show_alert=True)
        return
        
    # ذخیره زبان
    set_user_lang(user_id, lang_code)
    
    # ذخیره در دیتابیس (پروفایل یکپارچه)
    from database import db_manager
    user = callback.from_user
    await db_manager.upsert_user(user_id, {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "language": lang_code
    })
    
    # بارگذاری متون زبان جدید
    lang = load_lang(lang_code)
    lang_name = SUPPORTED_LANGUAGES[lang_code]['name']
    
    # نمایش پیام تایید و منوی اصلی
    confirm_msg = get_text(lang, "language_set", f"✅ زبان به {lang_name} تغییر کرد.")
    menu_title = get_text(lang, "main_menu_title", "🏠 <b>منوی اصلی</b>")
    
    await safe_answer(callback, confirm_msg)
    
    await safe_edit_text(
        callback.message,
        f"{confirm_msg}\n\n{menu_title}",
        reply_markup=get_main_menu(lang)
    )


@router.callback_query(F.data == "change_lang")
async def show_language_menu(callback: CallbackQuery):
    """نمایش منوی تغییر زبان"""
    lang = get_user_lang(callback.from_user.id)
    text = get_text(lang, "select_lang", "🌍 لطفاً زبان مورد نظر خود را انتخاب کنید:")
    
    await safe_edit_text(
        callback.message,
        text,
        reply_markup=get_language_keyboard()
    )
    await safe_answer(callback)


@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    """بازگشت به منوی اصلی"""
    lang = get_user_lang(callback.from_user.id)
    text = get_text(lang, "main_menu_title", "🏠 <b>منوی اصلی</b>")
    
    await safe_edit_text(
        callback.message,
        text,
        reply_markup=get_main_menu(lang)
    )
    await safe_answer(callback)


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۷: لیست توابع عمومی برای استفاده در سایر ماژول‌ها
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "router",
    "load_lang",
    "get_user_lang",
    "get_user_lang_code",
    "set_user_lang",
    "get_text",
    "get_main_menu",
    "get_back_button",
    "SUPPORTED_LANGUAGES",

]
