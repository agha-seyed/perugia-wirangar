# handlers/news_handler.py
# مدیریت کامل اخبار با تمام قابلیت‌ها
# نسخه ۲.۰ - ژانویه ۲۰۲۵

"""
📰 هندلر مدیریت اخبار SmartStudentBot

امکانات:
    ۱. نمایش لیست اخبار با صفحه‌بندی
    ۲. ارسال خبر جدید با پیش‌نمایش
    ۳. ویرایش کامل خبر (عنوان، متن، فایل)
    ۴. حذف خبر از کانال و دیتابیس
    ۵. دسته‌بندی اخبار
    ۶. جستجو در اخبار
    ۷. پشتیبانی چندزبانه
    ۸. آمار بازدید

ویژگی‌های جدید v2.0:
    - صفحه‌بندی (Pagination)
    - پیش‌نمایش قبل از انتشار
    - دسته‌بندی با ایموجی
    - جستجوی متنی
    - آمار و گزارش
"""

from aiogram import Router, types, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    FSInputFile,
    CallbackQuery,
    Message
)
from aiogram.enums import ParseMode
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json
import os

from config import settings, logger

# تلاش برای import توابع زبان
try:
    from handlers.cmd_start import get_user_lang, get_text, load_lang
except ImportError:
    def get_user_lang(user_id: int) -> dict:
        return {}
    def get_text(lang: dict, key: str, default: str = "") -> str:
        return lang.get(key, default or key)
    def load_lang(code: str) -> dict:
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
# ۱. تنظیمات و ثابت‌ها
# ═══════════════════════════════════════════════════════════════════════════════

router = Router()
router.name = "news_handler"

# مسیرها
UPLOAD_DIR = Path("uploads/news")
DATA_DIR = Path("data")
NEWS_JSON = DATA_DIR / "news.json"

# ایجاد پوشه‌ها
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# تنظیمات صفحه‌بندی
NEWS_PER_PAGE = 5

# دسته‌بندی اخبار
NEWS_CATEGORIES = {
    "general": {"emoji": "📰", "name": "عمومی", "name_en": "General"},
    "university": {"emoji": "🎓", "name": "دانشگاه", "name_en": "University"},
    "scholarship": {"emoji": "💰", "name": "بورسیه", "name_en": "Scholarship"},
    "visa": {"emoji": "🛂", "name": "ویزا و اقامت", "name_en": "Visa"},
    "event": {"emoji": "🎉", "name": "رویداد", "name_en": "Event"},
    "housing": {"emoji": "🏠", "name": "مسکن", "name_en": "Housing"},
    "urgent": {"emoji": "🚨", "name": "فوری", "name_en": "Urgent"},
}


# ═══════════════════════════════════════════════════════════════════════════════
# ۲. تعریف States
# ═══════════════════════════════════════════════════════════════════════════════

class NewsPostState(StatesGroup):
    """وضعیت‌های ارسال خبر جدید"""
    selecting_category = State()
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_file = State()
    waiting_for_caption = State()
    confirming_preview = State()


class NewsEditState(StatesGroup):
    """وضعیت‌های ویرایش خبر"""
    select_news = State()
    select_field = State()
    edit_title = State()
    edit_content = State()
    edit_file = State()
    edit_caption = State()
    edit_category = State()
    confirming_edit = State()


class NewsSearchState(StatesGroup):
    """وضعیت جستجو"""
    waiting_for_query = State()


# ═══════════════════════════════════════════════════════════════════════════════
# ۳. توابع کمکی
# ═══════════════════════════════════════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    """بررسی ادمین بودن کاربر"""
    return user_id in settings.ADMIN_CHAT_IDS


def load_news() -> List[Dict[str, Any]]:
    """خواندن لیست اخبار از فایل JSON"""
    
    if not NEWS_JSON.exists():
        return []
    
    try:
        with open(NEWS_JSON, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
            return data if isinstance(data, list) else []
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ فایل news.json خراب است: {e}")
        # بکاپ فایل خراب
        backup_path = NEWS_JSON.with_suffix(".json.bak")
        if NEWS_JSON.exists():
            NEWS_JSON.rename(backup_path)
        return []
    except Exception as e:
        logger.error(f"❌ خطا در خواندن اخبار: {e}")
        return []


def save_news(news_list: List[Dict[str, Any]]) -> bool:
    """ذخیره لیست اخبار در فایل JSON"""
    
    try:
        # ایجاد پوشه اگر نیست
        NEWS_JSON.parent.mkdir(parents=True, exist_ok=True)
        
        with open(NEWS_JSON, "w", encoding="utf-8") as f:
            json.dump(news_list or [], f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ اخبار ذخیره شد ({len(news_list)} خبر)")
        return True
    except Exception as e:
        logger.error(f"❌ خطا در ذخیره اخبار: {e}")
        return False


def get_news_by_id(news_id: int) -> Optional[Dict[str, Any]]:
    """یافتن خبر با ID"""
    news_list = load_news()
    return next((n for n in news_list if n.get("id") == news_id), None)


def generate_news_id() -> int:
    """تولید ID یکتا برای خبر جدید"""
    news_list = load_news()
    if not news_list:
        return 1
    return max(n.get("id", 0) for n in news_list) + 1


def get_category_info(category_key: str) -> Dict[str, str]:
    """دریافت اطلاعات دسته‌بندی"""
    return NEWS_CATEGORIES.get(category_key, NEWS_CATEGORIES["general"])


def format_news_text(news: Dict[str, Any], full: bool = False) -> str:
    """فرمت کردن متن خبر برای نمایش"""
    
    category = get_category_info(news.get("category", "general"))
    
    text = f"{category['emoji']} <b>{news.get('title', 'بدون عنوان')}</b>\n"
    text += f"📅 {news.get('date', 'نامشخص')}\n"
    
    if news.get("category"):
        text += f"🏷 {category['name']}\n"
    
    if full and news.get("content"):
        text += f"\n{news['content']}\n"
    
    if news.get("caption"):
        text += f"\n<i>{news['caption']}</i>\n"
    
    return text


def get_channel_link(message_id: Optional[int] = None) -> str:
    """ساخت لینک به کانال"""
    
    channel = settings.CHANNEL_ID.lstrip("@") if settings.CHANNEL_ID else ""
    
    if not channel:
        return ""
    
    if message_id:
        return f"https://t.me/{channel}/{message_id}"
    return f"https://t.me/{channel}"


async def download_file(message: Message, upload_dir: Path) -> Optional[str]:
    """دانلود فایل از پیام"""
    
    try:
        file_path = None
        
        if message.photo:
            file = message.photo[-1]
            file_info = await message.bot.get_file(file.file_id)
            file_path = upload_dir / f"photo_{file.file_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            await message.bot.download_file(file_info.file_path, str(file_path))
            
        elif message.video:
            file = message.video
            file_info = await message.bot.get_file(file.file_id)
            ext = ".mp4"
            file_path = upload_dir / f"video_{file.file_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
            await message.bot.download_file(file_info.file_path, str(file_path))
            
        elif message.document:
            file = message.document
            file_info = await message.bot.get_file(file.file_id)
            ext = Path(file.file_name).suffix if file.file_name else ".bin"
            file_path = upload_dir / f"doc_{file.file_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
            await message.bot.download_file(file_info.file_path, str(file_path))
        
        if file_path:
            logger.info(f"📥 فایل دانلود شد: {file_path}")
            return str(file_path)
        
        return None
        
    except Exception as e:
        logger.error(f"❌ خطا در دانلود فایل: {e}")
        return None


async def send_to_channel(
    bot: Bot,
    text: str,
    file_path: Optional[str] = None,
    parse_mode: str = "HTML"
) -> Optional[int]:
    """ارسال پیام به کانال و برگرداندن message_id"""
    
    if not settings.CHANNEL_ID:
        logger.warning("⚠️ CHANNEL_ID تنظیم نشده")
        return None
    
    try:
        sent_message = None
        
        if file_path and Path(file_path).exists():
            ext = Path(file_path).suffix.lower()
            
            if ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"]:
                sent_message = await bot.send_photo(
                    chat_id=settings.CHANNEL_ID,
                    photo=FSInputFile(file_path),
                    caption=text[:1024],
                    parse_mode=parse_mode
                )
            elif ext in [".mp4", ".mov", ".avi", ".mkv"]:
                sent_message = await bot.send_video(
                    chat_id=settings.CHANNEL_ID,
                    video=FSInputFile(file_path),
                    caption=text[:1024],
                    parse_mode=parse_mode
                )
            else:
                sent_message = await bot.send_document(
                    chat_id=settings.CHANNEL_ID,
                    document=FSInputFile(file_path),
                    caption=text[:1024],
                    parse_mode=parse_mode
                )
        else:
            sent_message = await bot.send_message(
                chat_id=settings.CHANNEL_ID,
                text=text,
                parse_mode=parse_mode
            )
        
        if sent_message:
            logger.success(f"✅ پیام به کانال ارسال شد: {sent_message.message_id}")
            return sent_message.message_id
        
        return None
        
    except Exception as e:
        logger.error(f"❌ خطا در ارسال به کانال: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# ۴. کیبوردها
# ═══════════════════════════════════════════════════════════════════════════════

def get_news_list_keyboard(
    news_list: List[Dict], 
    page: int = 0, 
    lang: dict = None
) -> InlineKeyboardMarkup:
    """کیبورد لیست اخبار با صفحه‌بندی"""
    
    if lang is None:
        lang = {}
    
    total = len(news_list)
    total_pages = (total + NEWS_PER_PAGE - 1) // NEWS_PER_PAGE
    
    # اخبار این صفحه (جدیدترین اول)
    start = page * NEWS_PER_PAGE
    end = start + NEWS_PER_PAGE
    page_news = list(reversed(news_list))[start:end]
    
    buttons = []
    
    # دکمه‌های اخبار
    for news in page_news:
        category = get_category_info(news.get("category", "general"))
        title = news.get("title", "بدون عنوان")
        
        # محدود کردن طول عنوان
        if len(title) > 35:
            title = title[:32] + "..."
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{category['emoji']} {title}",
                callback_data=f"news_view_{news.get('id', 0)}"
            )
        ])
    
    # دکمه‌های ناوبری
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️ قبلی", callback_data=f"news_page_{page - 1}")
        )
    
    if total_pages > 1:
        nav_buttons.append(
            InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="news_noop")
        )
    
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="بعدی ▶️", callback_data=f"news_page_{page + 1}")
        )
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # دکمه‌های اضافی
    buttons.append([
        InlineKeyboardButton(
            text=get_text(lang, "news_refresh", "🔄 به‌روزرسانی"),
            callback_data="news"
        ),
        InlineKeyboardButton(
            text=get_text(lang, "news_search", "🔍 جستجو"),
            callback_data="news_search"
        ),
    ])
    
    buttons.append([
        InlineKeyboardButton(
            text=get_text(lang, "back_to_menu", "🏠 منوی اصلی"),
            callback_data="main_menu"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_news_detail_keyboard(
    news_id: int, 
    has_channel_link: bool = False,
    is_admin: bool = False,
    lang: dict = None
) -> InlineKeyboardMarkup:
    """کیبورد جزئیات خبر"""
    
    if lang is None:
        lang = {}
    
    buttons = []
    
    # لینک کانال
    news = get_news_by_id(news_id)
    if news and news.get("message_id") and settings.CHANNEL_ID:
        channel_link = get_channel_link(news["message_id"])
        buttons.append([
            InlineKeyboardButton(
                text="📢 مشاهده در کانال",
                url=channel_link
            )
        ])
    
    # دکمه‌های ادمین
    if is_admin:
        buttons.append([
            InlineKeyboardButton(
                text="✏️ ویرایش",
                callback_data=f"news_edit_{news_id}"
            ),
            InlineKeyboardButton(
                text="🗑 حذف",
                callback_data=f"news_delete_{news_id}"
            ),
        ])
    
    # بازگشت
    buttons.append([
        InlineKeyboardButton(
            text=get_text(lang, "back", "🔙 بازگشت"),
            callback_data="news"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_category_keyboard(lang: dict = None) -> InlineKeyboardMarkup:
    """کیبورد انتخاب دسته‌بندی"""
    
    if lang is None:
        lang = {}
    
    buttons = []
    
    # دسته‌بندی‌ها در ردیف‌های دوتایی
    categories = list(NEWS_CATEGORIES.items())
    for i in range(0, len(categories), 2):
        row = []
        for key, info in categories[i:i+2]:
            row.append(
                InlineKeyboardButton(
                    text=f"{info['emoji']} {info['name']}",
                    callback_data=f"news_cat_{key}"
                )
            )
        buttons.append(row)
    
    # لغو
    buttons.append([
        InlineKeyboardButton(
            text="❌ لغو",
            callback_data="news_cancel"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_edit_field_keyboard(news_id: int, lang: dict = None) -> InlineKeyboardMarkup:
    """کیبورد انتخاب فیلد برای ویرایش"""
    
    if lang is None:
        lang = {}
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 عنوان", callback_data=f"news_ef_title_{news_id}"),
            InlineKeyboardButton(text="📄 متن", callback_data=f"news_ef_content_{news_id}"),
        ],
        [
            InlineKeyboardButton(text="📎 فایل", callback_data=f"news_ef_file_{news_id}"),
            InlineKeyboardButton(text="🏷 دسته‌بندی", callback_data=f"news_ef_cat_{news_id}"),
        ],
        [
            InlineKeyboardButton(text="💬 توضیحات", callback_data=f"news_ef_caption_{news_id}"),
        ],
        [
            InlineKeyboardButton(text="✅ اتمام ویرایش", callback_data=f"news_ef_done_{news_id}"),
            InlineKeyboardButton(text="❌ لغو", callback_data="news_cancel"),
        ],
    ])


def get_confirm_keyboard(action: str, news_id: int, lang: dict = None) -> InlineKeyboardMarkup:
    """کیبورد تایید عملیات"""
    
    if lang is None:
        lang = {}
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ تایید و انتشار",
                callback_data=f"news_confirm_{action}_{news_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="✏️ ویرایش",
                callback_data=f"news_back_edit_{news_id}"
            ),
            InlineKeyboardButton(
                text="❌ لغو",
                callback_data="news_cancel"
            ),
        ],
    ])


def get_back_keyboard(lang: dict = None) -> InlineKeyboardMarkup:
    """کیبورد ساده بازگشت"""
    
    if lang is None:
        lang = {}
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_text(lang, "back", "🔙 بازگشت به اخبار"),
                callback_data="news"
            ),
            InlineKeyboardButton(
                text=get_text(lang, "back_to_menu", "🏠 منو"),
                callback_data="main_menu"
            ),
        ]
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# ۵. نمایش لیست اخبار
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "news")
async def show_news_list(callback: CallbackQuery, state: FSMContext):
    """نمایش لیست اخبار"""
    
    # پاکسازی state
    await state.clear()
    
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    news_list = load_news()
    
    # ساخت متن
    text = "📰 <b>اخبار و به‌روزرسانی‌ها</b>\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not news_list:
        text += "📭 <i>هنوز خبری منتشر نشده است.</i>\n\n"
        text += "💡 به‌زودی اخبار جدید منتشر می‌شود!"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 به‌روزرسانی", callback_data="news")],
            [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu")],
        ])
    else:
        text += f"📊 تعداد اخبار: <b>{len(news_list)}</b>\n\n"
        text += "👇 برای مشاهده جزئیات، روی خبر کلیک کنید:"
        
        keyboard = get_news_list_keyboard(news_list, page=0, lang=lang)
    
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    except Exception:
        await callback.message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("news_page_"))
async def news_pagination(callback: CallbackQuery):
    """صفحه‌بندی اخبار"""
    
    page = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    news_list = load_news()
    
    text = "📰 <b>اخبار و به‌روزرسانی‌ها</b>\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"📊 تعداد اخبار: <b>{len(news_list)}</b>\n\n"
    text += "👇 برای مشاهده جزئیات، روی خبر کلیک کنید:"
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_news_list_keyboard(news_list, page=page, lang=lang),
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.callback_query(F.data == "news_noop")
async def news_noop(callback: CallbackQuery):
    """دکمه بدون عملکرد (شماره صفحه)"""
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ۶. نمایش جزئیات خبر
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("news_view_"))
async def view_news_detail(callback: CallbackQuery):
    """نمایش جزئیات یک خبر"""
    
    news_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    
    news = get_news_by_id(news_id)
    
    if not news:
        await callback.answer("❌ خبر یافت نشد!", show_alert=True)
        return
    
    # ساخت متن کامل
    text = format_news_text(news, full=True)
    text += "\n━━━━━━━━━━━━━━━━━━━━━"
    
    # افزایش شمارنده بازدید
    news_list = load_news()
    for n in news_list:
        if n.get("id") == news_id:
            n["views"] = n.get("views", 0) + 1
            break
    save_news(news_list)
    
    # نمایش تعداد بازدید
    text += f"\n👁 بازدید: {news.get('views', 0)}"
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_news_detail_keyboard(
            news_id=news_id,
            has_channel_link=bool(news.get("message_id")),
            is_admin=is_admin(user_id),
            lang=lang
        ),
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════════════
# ۷. جستجو در اخبار
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "news_search")
async def start_news_search(callback: CallbackQuery, state: FSMContext):
    """شروع جستجو"""
    
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    
    await state.set_state(NewsSearchState.waiting_for_query)
    
    text = "🔍 <b>جستجو در اخبار</b>\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "عبارت مورد نظر را بنویسید:\n\n"
    text += "💡 <i>مثال: بورسیه، ویزا، ثبت‌نام</i>\n\n"
    text += "❌ لغو: /cancel"
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_back_keyboard(lang),
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.message(NewsSearchState.waiting_for_query)
async def process_search(message: Message, state: FSMContext):
    """پردازش جستجو"""
    
    query = (message.text or "").strip().lower()
    
    if query in ["/cancel", "لغو"]:
        await state.clear()
        await message.answer("❌ جستجو لغو شد.", reply_markup=get_back_keyboard())
        return
    
    if not query or len(query) < 2:
        await message.answer("⚠️ حداقل ۲ کاراکتر وارد کنید.")
        return
    
    await state.clear()
    
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    news_list = load_news()
    
    # جستجو در عنوان و محتوا
    results = []
    for news in news_list:
        title = (news.get("title") or "").lower()
        content = (news.get("content") or "").lower()
        
        if query in title or query in content:
            results.append(news)
    
    text = f"🔍 <b>نتایج جستجو برای:</b> <code>{query}</code>\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not results:
        text += "📭 <i>نتیجه‌ای یافت نشد.</i>\n\n"
        text += "💡 عبارت دیگری را امتحان کنید."
        keyboard = get_back_keyboard(lang)
    else:
        text += f"✅ <b>{len(results)}</b> خبر یافت شد:\n"
        keyboard = get_news_list_keyboard(results, page=0, lang=lang)
    
    await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ۸. ارسال خبر جدید (ادمین)
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("post_news", "addnews", "newnews"))
async def cmd_post_news(message: Message, state: FSMContext):
    """شروع ارسال خبر جدید"""
    
    if not is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی ندارید.")
        return
    
    await state.clear()
    
    text = "📝 <b>ارسال خبر جدید</b>\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "🏷 ابتدا <b>دسته‌بندی</b> خبر را انتخاب کنید:\n\n"
    text += "❌ لغو: /cancel"
    
    await message.answer(
        text=text,
        reply_markup=get_category_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    await state.set_state(NewsPostState.selecting_category)


@router.callback_query(F.data.startswith("news_cat_"), NewsPostState.selecting_category)
async def select_category(callback: CallbackQuery, state: FSMContext):
    """انتخاب دسته‌بندی"""
    
    category = callback.data.replace("news_cat_", "")
    category_info = get_category_info(category)
    
    await state.update_data(
        category=category,
        date=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    
    text = f"✅ دسته‌بندی: {category_info['emoji']} <b>{category_info['name']}</b>\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "📝 حالا <b>عنوان خبر</b> را بنویسید:\n\n"
    text += "💡 <i>عنوان باید کوتاه و جذاب باشد</i>"
    
    await callback.message.edit_text(
        text=text,
        parse_mode=ParseMode.HTML
    )
    
    await state.set_state(NewsPostState.waiting_for_title)
    await callback.answer()


@router.message(NewsPostState.waiting_for_title)
async def process_news_title(message: Message, state: FSMContext):
    """دریافت عنوان خبر"""
    
    title = (message.text or "").strip()
    
    if title.lower() in ["/cancel", "لغو"]:
        await state.clear()
        await message.answer("❌ عملیات لغو شد.", reply_markup=get_back_keyboard())
        return
    
    if not title:
        await message.answer("⚠️ لطفاً عنوان را وارد کنید.")
        return
    
    if len(title) > 200:
        await message.answer("⚠️ عنوان نباید بیشتر از ۲۰۰ کاراکتر باشد.")
        return
    
    await state.update_data(title=title)
    
    text = f"✅ عنوان: <b>{title}</b>\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "📄 حالا <b>متن اصلی خبر</b> را بنویسید:\n\n"
    text += "💡 <i>می‌توانید از HTML ساده استفاده کنید</i>"
    
    await message.answer(text=text, parse_mode=ParseMode.HTML)
    await state.set_state(NewsPostState.waiting_for_content)


@router.message(NewsPostState.waiting_for_content)
async def process_news_content(message: Message, state: FSMContext):
    """دریافت متن خبر"""
    
    content = (message.text or "").strip()
    
    if content.lower() in ["/cancel", "لغو"]:
        await state.clear()
        await message.answer("❌ عملیات لغو شد.", reply_markup=get_back_keyboard())
        return
    
    if not content:
        await message.answer("⚠️ لطفاً متن خبر را وارد کنید.")
        return
    
    await state.update_data(content=content)
    
    text = "✅ متن دریافت شد!\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "📎 اگر می‌خواهید <b>فایل</b> (عکس، ویدیو، PDF) ضمیمه کنید، ارسال کنید.\n\n"
    text += "💡 اگر فایل ندارید، بنویسید: <code>بدون فایل</code>"
    
    await message.answer(text=text, parse_mode=ParseMode.HTML)
    await state.set_state(NewsPostState.waiting_for_file)


@router.message(NewsPostState.waiting_for_file, F.photo | F.video | F.document)
async def process_news_file(message: Message, state: FSMContext):
    """دریافت فایل خبر"""
    
    file_path = await download_file(message, UPLOAD_DIR)
    
    if not file_path:
        await message.answer("❌ خطا در دریافت فایل. دوباره امتحان کنید.")
        return
    
    await state.update_data(file_path=file_path, has_file=True)
    
    text = "✅ فایل دریافت شد!\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "💬 توضیحات اضافی (اختیاری):\n\n"
    text += "💡 اگر ندارید، بنویسید: <code>بدون توضیح</code>"
    
    await message.answer(text=text, parse_mode=ParseMode.HTML)
    await state.set_state(NewsPostState.waiting_for_caption)


@router.message(NewsPostState.waiting_for_file)
async def skip_news_file(message: Message, state: FSMContext):
    """رد کردن فایل"""
    
    text = (message.text or "").strip().lower()
    
    if "بدون فایل" in text or text == "skip" or text == "-":
        await state.update_data(file_path=None, has_file=False, caption=None)
        await show_news_preview(message, state)
    else:
        await message.answer(
            "📎 فایل بفرستید یا بنویسید: <code>بدون فایل</code>",
            parse_mode=ParseMode.HTML
        )


@router.message(NewsPostState.waiting_for_caption)
async def process_news_caption(message: Message, state: FSMContext):
    """دریافت توضیحات"""
    
    text = (message.text or "").strip()
    
    if "بدون توضیح" in text.lower() or text == "-":
        caption = None
    else:
        caption = text
    
    await state.update_data(caption=caption)
    await show_news_preview(message, state)


async def show_news_preview(message: Message, state: FSMContext):
    """نمایش پیش‌نمایش خبر قبل از انتشار"""
    
    data = await state.get_data()
    
    category_info = get_category_info(data.get("category", "general"))
    
    text = "👁 <b>پیش‌نمایش خبر</b>\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"🏷 دسته: {category_info['emoji']} {category_info['name']}\n"
    text += f"📅 تاریخ: {data.get('date')}\n"
    text += f"📎 فایل: {'✅' if data.get('has_file') else '❌'}\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"<b>{data.get('title')}</b>\n\n"
    text += f"{data.get('content')}\n"
    
    if data.get("caption"):
        text += f"\n<i>{data['caption']}</i>\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "✅ آیا این خبر منتشر شود؟"
    
    # ذخیره ID موقت
    temp_id = generate_news_id()
    await state.update_data(temp_id=temp_id)
    
    await state.set_state(NewsPostState.confirming_preview)
    
    await message.answer(
        text=text,
        reply_markup=get_confirm_keyboard("post", temp_id),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data.startswith("news_confirm_post_"), NewsPostState.confirming_preview)
async def confirm_post_news(callback: CallbackQuery, state: FSMContext):
    """تایید و انتشار خبر"""
    
    data = await state.get_data()
    
    # ساخت متن نهایی
    category_info = get_category_info(data.get("category", "general"))
    
    full_text = f"{category_info['emoji']} <b>{data.get('title')}</b>\n\n"
    full_text += f"{data.get('content')}\n"
    
    if data.get("caption"):
        full_text += f"\n<i>{data['caption']}</i>\n"
    
    full_text += f"\n📅 {data.get('date')}"
    
    # ارسال به کانال
    message_id = await send_to_channel(
        bot=callback.bot,
        text=full_text,
        file_path=data.get("file_path")
    )
    
    # ذخیره در دیتابیس
    news_list = load_news()
    
    new_news = {
        "id": generate_news_id(),
        "title": data.get("title"),
        "content": data.get("content"),
        "category": data.get("category", "general"),
        "date": data.get("date"),
        "has_file": data.get("has_file", False),
        "file_path": data.get("file_path"),
        "caption": data.get("caption"),
        "message_id": message_id,
        "views": 0,
        "created_by": callback.from_user.id,
    }
    
    news_list.append(new_news)
    save_news(news_list)
    
    await state.clear()
    
    text = "✅ <b>خبر با موفقیت منتشر شد!</b>\n\n"
    text += f"📰 {data.get('title')}\n\n"
    
    if message_id:
        channel_link = get_channel_link(message_id)
        text += f"🔗 <a href='{channel_link}'>مشاهده در کانال</a>"
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_back_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    logger.success(f"✅ خبر جدید منتشر شد: {data.get('title')}")
    await callback.answer("✅ منتشر شد!")


# ═══════════════════════════════════════════════════════════════════════════════
# ۹. ویرایش خبر (ادمین)
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("edit_news", "editnews"))
async def cmd_edit_news(message: Message, state: FSMContext):
    """شروع ویرایش خبر"""
    
    if not is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی ندارید.")
        return
    
    news_list = load_news()
    
    if not news_list:
        await message.answer("📭 هیچ خبری برای ویرایش وجود ندارد.")
        return
    
    await state.clear()
    
    text = "✏️ <b>ویرایش خبر</b>\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "خبر مورد نظر را انتخاب کنید:"
    
    # ساخت لیست اخبار
    buttons = []
    for news in reversed(news_list[-10:]):  # ۱۰ خبر آخر
        category_info = get_category_info(news.get("category", "general"))
        title = news.get("title", "بدون عنوان")[:40]
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{category_info['emoji']} {title}",
                callback_data=f"news_edit_{news.get('id')}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="❌ لغو", callback_data="news_cancel")
    ])
    
    await message.answer(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode=ParseMode.HTML
    )
    
    await state.set_state(NewsEditState.select_news)


@router.callback_query(F.data.startswith("news_edit_"))
async def select_news_for_edit(callback: CallbackQuery, state: FSMContext):
    """انتخاب خبر برای ویرایش"""
    
    # چک دسترسی
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    
    news_id = int(callback.data.split("_")[-1])
    news = get_news_by_id(news_id)
    
    if not news:
        await callback.answer("❌ خبر یافت نشد!", show_alert=True)
        return
    
    await state.update_data(editing_news_id=news_id, editing_news=news)
    
    text = "✏️ <b>ویرایش خبر</b>\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += format_news_text(news, full=False)
    text += "\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "🔧 کدام بخش را می‌خواهید ویرایش کنید؟"
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_edit_field_keyboard(news_id),
        parse_mode=ParseMode.HTML
    )
    
    await state.set_state(NewsEditState.select_field)
    await callback.answer()


@router.callback_query(F.data.startswith("news_ef_"), NewsEditState.select_field)
async def edit_field(callback: CallbackQuery, state: FSMContext):
    """ویرایش فیلد خاص"""
    
    parts = callback.data.split("_")
    field = parts[2]  # title, content, file, cat, caption, done
    news_id = int(parts[3])
    
    if field == "done":
        # اتمام ویرایش
        await finish_edit(callback, state)
        return
    
    await state.update_data(editing_field=field)
    
    field_names = {
        "title": ("📝 عنوان", "عنوان جدید را بنویسید:"),
        "content": ("📄 متن", "متن جدید را بنویسید:"),
        "file": ("📎 فایل", "فایل جدید را ارسال کنید (یا بنویسید: حذف فایل)"),
        "cat": ("🏷 دسته‌بندی", "دسته‌بندی جدید را انتخاب کنید:"),
        "caption": ("💬 توضیحات", "توضیحات جدید را بنویسید (یا: بدون توضیح)"),
    }
    
    name, prompt = field_names.get(field, ("", ""))
    
    text = f"✏️ <b>ویرایش {name}</b>\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"{prompt}\n\n"
    text += "❌ لغو: /cancel"
    
    if field == "cat":
        await callback.message.edit_text(
            text=text,
            reply_markup=get_category_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await state.set_state(NewsEditState.edit_category)
    else:
        await callback.message.edit_text(
            text=text,
            parse_mode=ParseMode.HTML
        )
        
        state_map = {
            "title": NewsEditState.edit_title,
            "content": NewsEditState.edit_content,
            "file": NewsEditState.edit_file,
            "caption": NewsEditState.edit_caption,
        }
        await state.set_state(state_map.get(field))
    
    await callback.answer()


@router.message(NewsEditState.edit_title)
async def edit_title(message: Message, state: FSMContext):
    """ویرایش عنوان"""
    
    new_title = (message.text or "").strip()
    
    if new_title.lower() in ["/cancel", "لغو"]:
        await go_back_to_edit_menu(message, state)
        return
    
    if not new_title:
        await message.answer("⚠️ عنوان نمی‌تواند خالی باشد.")
        return
    
    data = await state.get_data()
    news_id = data.get("editing_news_id")
    
    # به‌روزرسانی در دیتابیس
    news_list = load_news()
    for news in news_list:
        if news.get("id") == news_id:
            news["title"] = new_title
            break
    save_news(news_list)
    
    await message.answer(
        f"✅ عنوان به‌روزرسانی شد!\n\n<b>{new_title}</b>",
        parse_mode=ParseMode.HTML
    )
    
    await go_back_to_edit_menu(message, state)


@router.message(NewsEditState.edit_content)
async def edit_content(message: Message, state: FSMContext):
    """ویرایش متن"""
    
    new_content = (message.text or "").strip()
    
    if new_content.lower() in ["/cancel", "لغو"]:
        await go_back_to_edit_menu(message, state)
        return
    
    if not new_content:
        await message.answer("⚠️ متن نمی‌تواند خالی باشد.")
        return
    
    data = await state.get_data()
    news_id = data.get("editing_news_id")
    
    news_list = load_news()
    for news in news_list:
        if news.get("id") == news_id:
            news["content"] = new_content
            break
    save_news(news_list)
    
    await message.answer("✅ متن به‌روزرسانی شد!")
    await go_back_to_edit_menu(message, state)


@router.message(NewsEditState.edit_file, F.photo | F.video | F.document)
async def edit_file(message: Message, state: FSMContext):
    """ویرایش فایل"""
    
    file_path = await download_file(message, UPLOAD_DIR)
    
    if not file_path:
        await message.answer("❌ خطا در دریافت فایل.")
        return
    
    data = await state.get_data()
    news_id = data.get("editing_news_id")
    
    news_list = load_news()
    for news in news_list:
        if news.get("id") == news_id:
            news["file_path"] = file_path
            news["has_file"] = True
            break
    save_news(news_list)
    
    await message.answer("✅ فایل به‌روزرسانی شد!")
    await go_back_to_edit_menu(message, state)


@router.message(NewsEditState.edit_file)
async def remove_file(message: Message, state: FSMContext):
    """حذف فایل"""
    
    text = (message.text or "").strip().lower()
    
    if "حذف" in text or "delete" in text:
        data = await state.get_data()
        news_id = data.get("editing_news_id")
        
        news_list = load_news()
        for news in news_list:
            if news.get("id") == news_id:
                news["file_path"] = None
                news["has_file"] = False
                break
        save_news(news_list)
        
        await message.answer("✅ فایل حذف شد!")
        await go_back_to_edit_menu(message, state)
    elif text in ["/cancel", "لغو"]:
        await go_back_to_edit_menu(message, state)
    else:
        await message.answer("📎 فایل بفرستید یا بنویسید: <code>حذف فایل</code>", parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("news_cat_"), NewsEditState.edit_category)
async def edit_category(callback: CallbackQuery, state: FSMContext):
    """ویرایش دسته‌بندی"""
    
    new_category = callback.data.replace("news_cat_", "")
    
    data = await state.get_data()
    news_id = data.get("editing_news_id")
    
    news_list = load_news()
    for news in news_list:
        if news.get("id") == news_id:
            news["category"] = new_category
            break
    save_news(news_list)
    
    category_info = get_category_info(new_category)
    await callback.answer(f"✅ دسته‌بندی: {category_info['name']}")
    
    # برگشت به منوی ویرایش
    await state.set_state(NewsEditState.select_field)
    
    text = "✅ دسته‌بندی به‌روزرسانی شد!\n\n"
    text += "🔧 ادامه ویرایش یا اتمام؟"
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_edit_field_keyboard(news_id),
        parse_mode=ParseMode.HTML
    )


@router.message(NewsEditState.edit_caption)
async def edit_caption(message: Message, state: FSMContext):
    """ویرایش توضیحات"""
    
    text = (message.text or "").strip()
    
    if text.lower() in ["/cancel", "لغو"]:
        await go_back_to_edit_menu(message, state)
        return
    
    data = await state.get_data()
    news_id = data.get("editing_news_id")
    
    new_caption = None if "بدون توضیح" in text.lower() else text
    
    news_list = load_news()
    for news in news_list:
        if news.get("id") == news_id:
            news["caption"] = new_caption
            break
    save_news(news_list)
    
    await message.answer("✅ توضیحات به‌روزرسانی شد!")
    await go_back_to_edit_menu(message, state)


async def go_back_to_edit_menu(message: Message, state: FSMContext):
    """برگشت به منوی ویرایش"""
    
    data = await state.get_data()
    news_id = data.get("editing_news_id")
    
    await state.set_state(NewsEditState.select_field)
    
    text = "🔧 ادامه ویرایش یا اتمام؟"
    
    await message.answer(
        text=text,
        reply_markup=get_edit_field_keyboard(news_id),
        parse_mode=ParseMode.HTML
    )


async def finish_edit(callback: CallbackQuery, state: FSMContext):
    """اتمام ویرایش و به‌روزرسانی کانال"""
    
    data = await state.get_data()
    news_id = data.get("editing_news_id")
    
    news = get_news_by_id(news_id)
    
    if not news:
        await callback.answer("❌ خبر یافت نشد!", show_alert=True)
        await state.clear()
        return
    
    # آیا خبر در کانال وجود دارد؟
    if news.get("message_id") and settings.CHANNEL_ID:
        # حذف پیام قدیمی
        try:
            await callback.bot.delete_message(
                chat_id=settings.CHANNEL_ID,
                message_id=news["message_id"]
            )
        except Exception as e:
            logger.warning(f"⚠️ نتوانستیم پیام قدیمی را حذف کنیم: {e}")
        
        # ارسال پیام جدید
        category_info = get_category_info(news.get("category", "general"))
        
        full_text = f"{category_info['emoji']} <b>{news.get('title')}</b>\n\n"
        full_text += f"{news.get('content')}\n"
        
        if news.get("caption"):
            full_text += f"\n<i>{news['caption']}</i>\n"
        
        full_text += f"\n📅 {news.get('date')}"
        full_text += "\n\n✏️ <i>ویرایش شده</i>"
        
        new_message_id = await send_to_channel(
            bot=callback.bot,
            text=full_text,
            file_path=news.get("file_path")
        )
        
        # به‌روزرسانی message_id
        if new_message_id:
            news_list = load_news()
            for n in news_list:
                if n.get("id") == news_id:
                    n["message_id"] = new_message_id
                    n["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    break
            save_news(news_list)
    
    await state.clear()
    
    text = "✅ <b>ویرایش با موفقیت انجام شد!</b>\n\n"
    text += f"📰 {news.get('title')}"
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_back_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    logger.success(f"✅ خبر ویرایش شد: {news.get('title')}")
    await callback.answer("✅ ویرایش انجام شد!")


# ═══════════════════════════════════════════════════════════════════════════════
# ۱۰. حذف خبر (ادمین)
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("delete_news", "delnews"))
async def cmd_delete_news(message: Message, state: FSMContext):
    """شروع حذف خبر"""
    
    if not is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی ندارید.")
        return
    
    news_list = load_news()
    
    if not news_list:
        await message.answer("📭 هیچ خبری برای حذف وجود ندارد.")
        return
    
    await state.clear()
    
    text = "🗑 <b>حذف خبر</b>\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "⚠️ خبر مورد نظر را انتخاب کنید:\n\n"
    text += "<i>توجه: خبر از کانال و دیتابیس حذف می‌شود!</i>"
    
    buttons = []
    for news in reversed(news_list[-10:]):
        category_info = get_category_info(news.get("category", "general"))
        title = news.get("title", "بدون عنوان")[:35]
        
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {category_info['emoji']} {title}",
                callback_data=f"news_delete_{news.get('id')}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="❌ لغو", callback_data="news_cancel")
    ])
    
    await message.answer(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data.startswith("news_delete_"))
async def confirm_delete(callback: CallbackQuery):
    """تایید حذف خبر"""
    
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    
    news_id = int(callback.data.split("_")[-1])
    news = get_news_by_id(news_id)
    
    if not news:
        await callback.answer("❌ خبر یافت نشد!", show_alert=True)
        return
    
    text = "⚠️ <b>آیا مطمئن هستید؟</b>\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"📰 <b>{news.get('title')}</b>\n\n"
    text += "این خبر به طور کامل حذف خواهد شد!"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ بله، حذف شود",
                callback_data=f"news_confirm_delete_{news_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ لغو",
                callback_data="news_cancel"
            )
        ],
    ])
    
    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("news_confirm_delete_"))
async def execute_delete(callback: CallbackQuery):
    """اجرای حذف خبر"""
    
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    
    news_id = int(callback.data.split("_")[-1])
    news = get_news_by_id(news_id)
    
    if not news:
        await callback.answer("❌ خبر یافت نشد!", show_alert=True)
        return
    
    # حذف از کانال
    if news.get("message_id") and settings.CHANNEL_ID:
        try:
            await callback.bot.delete_message(
                chat_id=settings.CHANNEL_ID,
                message_id=news["message_id"]
            )
            logger.info(f"🗑 پیام {news['message_id']} از کانال حذف شد")
        except Exception as e:
            logger.warning(f"⚠️ خطا در حذف از کانال: {e}")
    
    # حذف فایل
    if news.get("file_path"):
        try:
            file_path = Path(news["file_path"])
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning(f"⚠️ خطا در حذف فایل: {e}")
    
    # حذف از دیتابیس
    news_list = load_news()
    news_list = [n for n in news_list if n.get("id") != news_id]
    save_news(news_list)
    
    text = "✅ <b>خبر با موفقیت حذف شد!</b>\n\n"
    text += f"📰 {news.get('title')}"
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_back_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    logger.success(f"🗑 خبر حذف شد: {news.get('title')}")
    await callback.answer("🗑 حذف شد!")


# ═══════════════════════════════════════════════════════════════════════════════
# ۱۱. لغو عملیات
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "news_cancel")
async def cancel_news_operation(callback: CallbackQuery, state: FSMContext):
    """لغو عملیات"""
    
    await state.clear()
    
    await callback.message.edit_text(
        "❌ <b>عملیات لغو شد</b>",
        reply_markup=get_back_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer("❌ لغو شد")


@router.message(Command("cancel"), StateFilter(NewsPostState, NewsEditState, NewsSearchState))
async def cancel_by_command(message: Message, state: FSMContext):
    """لغو با دستور"""
    
    await state.clear()
    
    await message.answer(
        "❌ <b>عملیات لغو شد</b>",
        reply_markup=get_back_keyboard(),
        parse_mode=ParseMode.HTML
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ۱۲. لاگ نهایی
# ═══════════════════════════════════════════════════════════════════════════════

logger.success("📰 News Handler v2.0 loaded!")
logger.info(f"   Router: {router.name}")
logger.info(f"   Categories: {len(NEWS_CATEGORIES)}")
logger.info(f"   News per page: {NEWS_PER_PAGE}")