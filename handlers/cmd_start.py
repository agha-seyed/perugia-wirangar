# handlers/cmd_start.py
# نسخه نهایی و کامل با تمام دکمه‌ها
# ژانویه ۲۰۲۵

"""
این فایل شامل:
1. دستور /start برای شروع ربات
2. انتخاب و تغییر زبان
3. منوی اصلی با تمام دکمه‌ها
4. بازگشت به منو از هر جای برنامه
"""

from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Dict, Optional
import json
from pathlib import Path

from config import settings, logger

router = Router()


# ═══════════════════════════════════════════════════════════════════════════════
# ۱. مدیریت زبان‌ها
# ═══════════════════════════════════════════════════════════════════════════════

# کش ترجمه‌ها در حافظه
_lang_cache: Dict[str, dict] = {}

# ذخیره زبان انتخابی هر کاربر (در حافظه - بعداً به دیتابیس منتقل می‌شود)
_user_languages: Dict[int, str] = {}

# زبان پیش‌فرض
DEFAULT_LANGUAGE = "fa"

# زبان‌های پشتیبانی شده
SUPPORTED_LANGUAGES = {
    "fa": {"name": "فارسی", "flag": "🇮🇷", "dir": "rtl"},
    "en": {"name": "English", "flag": "🇬🇧", "dir": "ltr"},
    "it": {"name": "Italiano", "flag": "🇮🇹", "dir": "ltr"},
}


def load_lang(lang_code: str = "fa") -> dict:
    """
    بارگذاری فایل زبان
    
    Args:
        lang_code: کد زبان (fa, en, it)
    
    Returns:
        دیکشنری ترجمه‌ها
    """
    
    # چک کش
    if lang_code in _lang_cache:
        return _lang_cache[lang_code]
    
    # مسیر فایل زبان
    lang_file = Path(f"lang/{lang_code}.json")
    
    try:
        if lang_file.exists():
            with open(lang_file, encoding="utf-8") as f:
                data = json.load(f)
                _lang_cache[lang_code] = data
                logger.debug(f"📚 Language loaded: {lang_code}")
                return data
        else:
            logger.warning(f"⚠️ Language file not found: {lang_code}, falling back to {DEFAULT_LANGUAGE}")
            return load_lang(DEFAULT_LANGUAGE)
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in language file {lang_code}: {e}")
        if lang_code != DEFAULT_LANGUAGE:
            return load_lang(DEFAULT_LANGUAGE)
        return {}
    except Exception as e:
        logger.error(f"❌ Error loading language {lang_code}: {e}")
        return {}


def get_user_lang(user_id: int) -> dict:
    """
    دریافت زبان کاربر
    
    Args:
        user_id: شناسه کاربر
    
    Returns:
        دیکشنری ترجمه‌ها
    """
    lang_code = _user_languages.get(user_id, DEFAULT_LANGUAGE)
    return load_lang(lang_code)


def get_user_lang_code(user_id: int) -> str:
    """
    دریافت کد زبان کاربر
    
    Args:
        user_id: شناسه کاربر
    
    Returns:
        کد زبان (fa, en, it)
    """
    return _user_languages.get(user_id, DEFAULT_LANGUAGE)


def set_user_lang(user_id: int, lang_code: str) -> None:
    """
    تنظیم زبان کاربر
    
    Args:
        user_id: شناسه کاربر
        lang_code: کد زبان
    """
    if lang_code in SUPPORTED_LANGUAGES:
        _user_languages[user_id] = lang_code
        logger.info(f"🌐 User {user_id} language set to: {lang_code}")


# ═══════════════════════════════════════════════════════════════════════════════
# ۲. کیبوردها
# ═══════════════════════════════════════════════════════════════════════════════

def get_language_keyboard() -> InlineKeyboardMarkup:
    """
    کیبورد انتخاب زبان
    
    Returns:
        InlineKeyboardMarkup
    """
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
    منوی اصلی - کامل، دو ستونه، زیبا و با تمام ویژگی‌ها
    
    Args:
        lang: دیکشنری زبان
    
    Returns:
        InlineKeyboardMarkup
    """
    
    # دریافت متن‌ها با مقدار پیش‌فرض
    def get_text(key: str, default: str) -> str:
        return lang.get(key, default)
    
    buttons = [
        # ═══════════════════════════════════════════════════
        # ردیف ۱: اخبار و آب‌وهوا
        # ═══════════════════════════════════════════════════
        [
            InlineKeyboardButton(
                text=get_text("news", "📰 اخبار"),
                callback_data="news"
            ),
            InlineKeyboardButton(
                text=get_text("weather", "🌤 آب‌وهوا"),
                callback_data="weather"
            ),
        ],
        
        # ═══════════════════════════════════════════════════
        # ردیف ۲: راهنما و ISEE
        # ═══════════════════════════════════════════════════
        [
            InlineKeyboardButton(
                text=get_text("guide", "📖 راهنما"),
                callback_data="guide_main"
            ),
            InlineKeyboardButton(
                text=get_text("isee", "🧮 محاسبه ISEE"),
                callback_data="isee"
            ),
        ],
        
        # ═══════════════════════════════════════════════════
        # ردیف ۳: مکان‌ها و مشاوره
        # ═══════════════════════════════════════════════════
        [
            InlineKeyboardButton(
                text=get_text("places", "📍 مکان‌ها"),
                callback_data="places"
            ),
            InlineKeyboardButton(
                text=get_text("consult", "💬 مشاوره"),
                callback_data="consult"
            ),
        ],
        
        # ═══════════════════════════════════════════════════
        # ردیف ۴: ایتالیایی و هم‌خانه
        # ═══════════════════════════════════════════════════
        [
            InlineKeyboardButton(
                text=get_text("italy", "🇮🇹 یادگیری ایتالیایی"),
                callback_data="italy"
            ),
            InlineKeyboardButton(
                text=get_text("roommate", "🏠 هم‌خانه‌یابی"),
                callback_data="roommate"
            ),
        ],
        
        # ═══════════════════════════════════════════════════
        # ردیف ۵: هوش مصنوعی و بازخورد ⭐ (تغییر اصلی)
        # ═══════════════════════════════════════════════════
        [
            InlineKeyboardButton(
                text=get_text("ai_chat", "🤖 چت با AI"),
                callback_data="ai_chat"
            ),
            InlineKeyboardButton(
                text=get_text("feedback", "📝 بازخورد"),
                callback_data="feedback"
            ),
        ],
        
        # ═══════════════════════════════════════════════════
        # ردیف ۶: ترجمه
        # ═══════════════════════════════════════════════════
        [
            InlineKeyboardButton(
                text=get_text("translate", "🌐 ترجمه متن"),
                callback_data="translate"
            ),
        ],
        
        # ═══════════════════════════════════════════════════
        # ردیف آخر: تغییر زبان
        # ═══════════════════════════════════════════════════
        [
            InlineKeyboardButton(
                text=get_text("language", "🌍 تغییر زبان"),
                callback_data="change_lang"
            ),
        ],
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_button(lang: dict) -> InlineKeyboardMarkup:
    """
    دکمه بازگشت به منوی اصلی
    
    Args:
        lang: دیکشنری زبان
    
    Returns:
        InlineKeyboardMarkup
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=lang.get("back_to_menu", "🔙 بازگشت به منو"),
            callback_data="main_menu"
        )]
    ])


def get_ai_menu(lang: dict) -> InlineKeyboardMarkup:
    """
    منوی هوش مصنوعی
    
    Args:
        lang: دیکشنری زبان
    
    Returns:
        InlineKeyboardMarkup
    """
    buttons = [
        [
            InlineKeyboardButton(
                text=lang.get("ai_chat_start", "💬 شروع چت"),
                callback_data="ai_start_chat"
            ),
        ],
        [
            InlineKeyboardButton(
                text=lang.get("ai_translate", "🌐 ترجمه"),
                callback_data="ai_translate"
            ),
            InlineKeyboardButton(
                text=lang.get("ai_italian", "🇮🇹 کمک ایتالیایی"),
                callback_data="ai_italian_help"
            ),
        ],
        [
            InlineKeyboardButton(
                text=lang.get("ai_status", "📊 وضعیت AI"),
                callback_data="ai_status"
            ),
        ],
        [
            InlineKeyboardButton(
                text=lang.get("back_to_menu", "🔙 بازگشت"),
                callback_data="main_menu"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ═══════════════════════════════════════════════════════════════════════════════
# ۳. هندلرها
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    هندلر دستور /start
    
    نمایش پیام خوش‌آمدگویی و کیبورد انتخاب زبان
    """
    
    user = message.from_user
    logger.info(f"👤 New user started bot: {user.id} (@{user.username or 'N/A'})")
    
    # بارگذاری زبان پیش‌فرض یا زبان قبلی کاربر
    lang = get_user_lang(user.id)
    
    # پیام خوش‌آمدگویی
    welcome_text = lang.get("welcome", """
🎓 <b>به ربات دانشجویان ایرانی پروجا خوش آمدید!</b>

این ربات به شما کمک می‌کند:
• 📰 اخبار دانشگاه و شهر
• 🌤 آب‌وهوای پروجا
• 📖 راهنمای جامع زندگی و تحصیل
• 🧮 محاسبه ISEE
• 📍 مکان‌های مهم شهر
• 🤖 چت با هوش مصنوعی
• 🇮🇹 یادگیری زبان ایتالیایی
• و خیلی امکانات دیگه!

🌐 <b>لطفاً ابتدا زبان خود را انتخاب کنید:</b>
""")
    
    await message.answer(
        welcome_text,
        reply_markup=get_language_keyboard(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )


@router.message(Command("menu"))
async def cmd_menu(message: types.Message):
    """
    هندلر دستور /menu
    
    نمایش منوی اصلی
    """
    lang = get_user_lang(message.from_user.id)
    
    await message.answer(
        f"🏠 {lang.get('main_menu', 'منوی اصلی')}",
        reply_markup=get_main_menu(lang),
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """
    هندلر دستور /help
    
    نمایش راهنمای استفاده
    """
    lang = get_user_lang(message.from_user.id)
    
    help_text = lang.get("help_text", """
📚 <b>راهنمای استفاده از ربات</b>

<b>دستورات اصلی:</b>
• /start - شروع مجدد ربات
• /menu - نمایش منوی اصلی
• /help - همین راهنما
• /ai - چت با هوش مصنوعی
• /weather - آب‌وهوای پروجا
• /translate - ترجمه متن

<b>نکات:</b>
• برای ترجمه، متن خود را با /translate ارسال کنید
• برای چت با AI، از دکمه 🤖 یا /ai استفاده کنید
• برای تغییر زبان، از منوی اصلی استفاده کنید

<b>پشتیبانی:</b>
اگر سوالی دارید، از بخش «بازخورد» استفاده کنید.
""")
    
    await message.answer(
        help_text,
        reply_markup=get_back_button(lang),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ۴. کالبک‌ها - زبان
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("lang_"))
async def process_language(callback: types.CallbackQuery):
    """
    پردازش انتخاب زبان
    """
    
    # استخراج کد زبان
    lang_code = callback.data.split("_")[1]
    
    # اعتبارسنجی
    if lang_code not in SUPPORTED_LANGUAGES:
        await callback.answer("❌ زبان نامعتبر!", show_alert=True)
        return
    
    # ذخیره زبان کاربر
    user_id = callback.from_user.id
    set_user_lang(user_id, lang_code)
    
    # بارگذاری زبان جدید
    lang = load_lang(lang_code)
    lang_info = SUPPORTED_LANGUAGES[lang_code]
    
    # پیام تایید
    confirm_text = lang.get("language_changed", "✅ زبان شما تغییر کرد!")
    menu_text = lang.get("main_menu", "منوی اصلی")
    
    await callback.message.edit_text(
        f"{confirm_text}\n\n"
        f"{lang_info['flag']} <b>{lang_info['name']}</b>\n\n"
        f"🏠 {menu_text}",
        reply_markup=get_main_menu(lang),
        parse_mode="HTML"
    )
    
    await callback.answer(f"{lang_info['flag']} {lang_info['name']}")


@router.callback_query(F.data == "change_lang")
async def change_language(callback: types.CallbackQuery):
    """
    نمایش منوی تغییر زبان
    """
    
    lang = get_user_lang(callback.from_user.id)
    
    await callback.message.edit_text(
        lang.get("select_language", "🌐 لطفاً زبان جدید خود را انتخاب کنید:"),
        reply_markup=get_language_keyboard(),
        parse_mode="HTML"
    )
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ۵. کالبک‌ها - منوی اصلی
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery):
    """
    بازگشت به منوی اصلی
    """
    
    lang = get_user_lang(callback.from_user.id)
    
    await callback.message.edit_text(
        f"🏠 {lang.get('main_menu', 'منوی اصلی')}",
        reply_markup=get_main_menu(lang),
        parse_mode="HTML"
    )
    
    await callback.answer(lang.get("back_to_menu_alert", "به منوی اصلی بازگشتید!"))


# ═══════════════════════════════════════════════════════════════════════════════
# ۶. کالبک‌ها - هوش مصنوعی ⭐
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ai_chat")
async def show_ai_menu(callback: types.CallbackQuery):
    """
    نمایش منوی هوش مصنوعی
    """
    
    lang = get_user_lang(callback.from_user.id)
    
    ai_intro = lang.get("ai_intro", """
🤖 <b>چت با هوش مصنوعی</b>

من می‌تونم در موارد زیر کمکت کنم:

💬 <b>چت و سوال:</b>
هر سوالی درباره تحصیل، ویزا، زندگی در ایتالیا داری بپرس!

🌐 <b>ترجمه:</b>
متن ایتالیایی، انگلیسی یا فارسی رو برام بفرست تا ترجمه کنم.

🇮🇹 <b>کمک ایتالیایی:</b>
معنی کلمات، تلفظ، صرف فعل و مثال می‌دم.

📊 <b>وضعیت:</b>
ببین AI در دسترسه یا نه.

👇 <b>یکی از گزینه‌ها رو انتخاب کن:</b>
""")
    
    await callback.message.edit_text(
        ai_intro,
        reply_markup=get_ai_menu(lang),
        parse_mode="HTML"
    )
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ۷. کالبک‌ها - ترجمه
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "translate")
async def show_translate_menu(callback: types.CallbackQuery):
    """
    نمایش منوی ترجمه
    """
    
    lang = get_user_lang(callback.from_user.id)
    
    translate_text = lang.get("translate_intro", """
🌐 <b>ترجمه متن</b>

برای ترجمه، کافیه متن خودت رو با فرمت زیر بفرستی:

📝 <b>ایتالیایی به فارسی:</b>
<code>/tr it fa Buongiorno, come stai?</code>

📝 <b>فارسی به ایتالیایی:</b>
<code>/tr fa it سلام، حالت چطوره؟</code>

📝 <b>انگلیسی به فارسی:</b>
<code>/tr en fa Hello, how are you?</code>

💡 <b>یا ساده‌تر:</b>
فقط متن ایتالیایی رو بفرست، خودم ترجمه می‌کنم!
""")
    
    buttons = [
        [
            InlineKeyboardButton(
                text="🇮🇹➡️🇮🇷 ایتالیایی به فارسی",
                callback_data="tr_it_fa"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🇮🇷➡️🇮🇹 فارسی به ایتالیایی",
                callback_data="tr_fa_it"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🇬🇧➡️🇮🇷 انگلیسی به فارسی",
                callback_data="tr_en_fa"
            ),
        ],
        [
            InlineKeyboardButton(
                text=lang.get("back_to_menu", "🔙 بازگشت"),
                callback_data="main_menu"
            ),
        ],
    ]
    
    await callback.message.edit_text(
        translate_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ۸. Export توابع مفید برای سایر هندلرها
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "router",
    "load_lang",
    "get_user_lang",
    "get_user_lang_code",
    "set_user_lang",
    "get_main_menu",
    "get_back_button",
    "get_language_keyboard",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
]