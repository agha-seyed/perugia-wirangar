# handlers/feedback_handler.py
# سیستم پشتیبانی و تیکت - نسخه نهایی کامل
# بخش ۱: تنظیمات، توابع کمکی، States، منوی اصلی

import json
import os
import random
import time
import glob
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.exceptions import TelegramBadRequest

from config import settings, logger

router = Router()


# ═══════════════════════════════════════════════════════════════════
# تنظیمات و مسیرها
# ═══════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent.parent
FEEDBACK_DIR = BASE_DIR / "uploads" / "feedback"
DATA_DIR = BASE_DIR / "data"
FEEDBACK_JSON = DATA_DIR / "feedbacks.json"

# ایجاد پوشه‌ها
os.makedirs(FEEDBACK_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# تنظیمات فایل
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx', '.txt', '.zip']
CLEANUP_DAYS = 30  # حذف فایل‌های قدیمی

# تنظیمات تیکت
TICKETS_PER_PAGE = 5
MAX_MESSAGE_LENGTH = 2000
MAX_ATTACHMENTS = 3


# ═══════════════════════════════════════════════════════════════════
# نقشه‌ها و ثوابت
# ═══════════════════════════════════════════════════════════════════

# انواع تیکت
TICKET_TYPES = {
    "bug": {
        "label": "🐛 گزارش باگ",
        "short": "باگ",
        "priority": "high",
        "icon": "🔴"
    },
    "support": {
        "label": "❓ سوال / راهنمایی",
        "short": "پشتیبانی",
        "priority": "medium",
        "icon": "🟡"
    },
    "suggestion": {
        "label": "💡 پیشنهاد",
        "short": "پیشنهاد",
        "priority": "low",
        "icon": "🟢"
    },
    "complaint": {
        "label": "😤 شکایت",
        "short": "شکایت",
        "priority": "high",
        "icon": "🔴"
    },
    "love": {
        "label": "❤️ تشکر و قدردانی",
        "short": "تشکر",
        "priority": "low",
        "icon": "💚"
    },
    "other": {
        "label": "📝 سایر موارد",
        "short": "سایر",
        "priority": "medium",
        "icon": "⚪"
    }
}

# اولویت‌ها
PRIORITY_LEVELS = {
    "critical": {"label": "🚨 بحرانی", "order": 1, "color": "🔴"},
    "high": {"label": "🔴 فوری", "order": 2, "color": "🔴"},
    "medium": {"label": "🟡 متوسط", "order": 3, "color": "🟡"},
    "low": {"label": "🟢 پایین", "order": 4, "color": "🟢"}
}

# وضعیت تیکت
TICKET_STATUS = {
    "open": {"label": "🟢 باز", "icon": "🟢"},
    "in_progress": {"label": "🟡 در حال بررسی", "icon": "🟡"},
    "waiting": {"label": "⏳ منتظر پاسخ کاربر", "icon": "⏳"},
    "resolved": {"label": "✅ حل شده", "icon": "✅"},
    "closed": {"label": "🔒 بسته شده", "icon": "🔒"}
}

# پاسخ‌های خودکار FAQ
FAQ_DATABASE = {
    # هزینه و شهریه
    "هزینه": "💰 برای اطلاعات کامل هزینه‌ها به بخش «هزینه‌ها» در منوی اصلی مراجعه کنید.",
    "شهریه": "🎓 شهریه دانشگاه بر اساس عدد ISEE خانواده محاسبه می‌شود. جزئیات در بخش هزینه‌ها.",
    "ISEE": "📊 ISEE شاخص وضعیت اقتصادی است. برای محاسبه به CAF مراجعه کنید.",
    
    # مسکن
    "خوابگاه": "🏠 برای اطلاعات خوابگاه و مسکن به بخش «هم‌خانه» مراجعه کنید.",
    "اجاره": "🏠 قیمت اجاره در پروجا بین 250 تا 500 یورو است. بخش هم‌خانه را ببینید.",
    "مسکن": "🏠 بخش «هم‌خانه» اطلاعات کاملی درباره مسکن دارد.",
    
    # ثبت‌نام
    "ثبت نام": "📝 برای راهنمای ثبت‌نام به بخش «راهنمای ثبت‌نام» در منوی اصلی بروید.",
    "پذیرش": "📝 اطلاعات پذیرش در بخش راهنمای ثبت‌نام موجود است.",
    
    # ویزا
    "ویزا": "🛂 اطلاعات ویزا در بخش «خدمات کنسولی» قرار دارد.",
    "سفارت": "🏛 برای امور سفارت به بخش خدمات کنسولی مراجعه کنید.",
    
    # زمان پاسخگویی
    "ادمین": "⏰ ساعت پاسخگویی ادمین‌ها: ۱۰ صبح تا ۱۰ شب (به وقت ایتالیا).",
    "پاسخ": "⏰ معمولاً ظرف ۲۴ ساعت پاسخ داده می‌شود."
}


# ═══════════════════════════════════════════════════════════════════
# توابع کمکی
# ═══════════════════════════════════════════════════════════════════

def load_feedbacks() -> List[Dict]:
    """بارگذاری تیکت‌ها از فایل"""
    if not os.path.exists(FEEDBACK_JSON):
        return []
    try:
        with open(FEEDBACK_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"Error loading feedbacks: {e}")
        return []


def save_feedbacks(data_list: List[Dict]) -> bool:
    """ذخیره تیکت‌ها در فایل"""
    try:
        with open(FEEDBACK_JSON, "w", encoding="utf-8") as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving feedbacks: {e}")
        return False


def generate_ticket_id() -> str:
    """تولید شناسه یکتا برای تیکت"""
    timestamp = int(time.time()) % 100000
    rand = random.randint(10, 99)
    return f"T-{timestamp}{rand}"


def get_ticket_by_id(ticket_id: str) -> Optional[Dict]:
    """یافتن تیکت با شناسه"""
    tickets = load_feedbacks()
    return next((t for t in tickets if t.get("id") == ticket_id), None)


def update_ticket(ticket_id: str, updates: Dict) -> bool:
    """بروزرسانی تیکت"""
    tickets = load_feedbacks()
    
    for ticket in tickets:
        if ticket.get("id") == ticket_id:
            ticket.update(updates)
            ticket["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_feedbacks(tickets)
            return True
    
    return False


def add_message_to_ticket(ticket_id: str, sender: str, message: str, 
                          sender_id: int = None, sender_name: str = None) -> bool:
    """افزودن پیام به مکالمه تیکت"""
    tickets = load_feedbacks()
    
    for ticket in tickets:
        if ticket.get("id") == ticket_id:
            if "conversation" not in ticket:
                ticket["conversation"] = []
            
            ticket["conversation"].append({
                "sender": sender,  # "user" or "admin"
                "sender_id": sender_id,
                "sender_name": sender_name,
                "message": message,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            
            ticket["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            ticket["last_reply_by"] = sender
            
            save_feedbacks(tickets)
            return True
    
    return False


def get_user_tickets(user_id: int, status_filter: str = None) -> List[Dict]:
    """دریافت تیکت‌های یک کاربر"""
    tickets = load_feedbacks()
    user_tickets = [t for t in tickets if t.get("user_id") == user_id]
    
    if status_filter:
        if status_filter == "open":
            user_tickets = [t for t in user_tickets if t.get("status") in ["open", "in_progress", "waiting"]]
        elif status_filter == "closed":
            user_tickets = [t for t in user_tickets if t.get("status") in ["resolved", "closed"]]
    
    # مرتب‌سازی بر اساس تاریخ (جدیدترین اول)
    user_tickets.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return user_tickets


def get_all_open_tickets() -> List[Dict]:
    """دریافت همه تیکت‌های باز (برای ادمین)"""
    tickets = load_feedbacks()
    open_tickets = [t for t in tickets if t.get("status") in ["open", "in_progress", "waiting"]]
    
    # مرتب‌سازی بر اساس اولویت و تاریخ
    def sort_key(t):
        priority_order = PRIORITY_LEVELS.get(t.get("priority", "medium"), {}).get("order", 3)
        return (priority_order, t.get("created_at", ""))
    
    open_tickets.sort(key=sort_key)
    
    return open_tickets


def get_ticket_stats() -> Dict:
    """آمار کلی تیکت‌ها"""
    tickets = load_feedbacks()
    
    total = len(tickets)
    open_count = sum(1 for t in tickets if t.get("status") == "open")
    in_progress = sum(1 for t in tickets if t.get("status") == "in_progress")
    waiting = sum(1 for t in tickets if t.get("status") == "waiting")
    resolved = sum(1 for t in tickets if t.get("status") == "resolved")
    closed = sum(1 for t in tickets if t.get("status") == "closed")
    
    # آمار بر اساس نوع
    by_type = {}
    for t in tickets:
        t_type = t.get("type", "other")
        by_type[t_type] = by_type.get(t_type, 0) + 1
    
    # آمار امتیازها
    ratings = [t.get("user_rating") for t in tickets if t.get("user_rating")]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # تیکت‌های امروز
    today = datetime.now().strftime("%Y-%m-%d")
    today_count = sum(1 for t in tickets if t.get("created_at", "").startswith(today))
    
    return {
        "total": total,
        "open": open_count,
        "in_progress": in_progress,
        "waiting": waiting,
        "resolved": resolved,
        "closed": closed,
        "by_type": by_type,
        "avg_rating": round(avg_rating, 1),
        "rating_count": len(ratings),
        "today": today_count
    }


def smart_cleanup():
    """پاکسازی فایل‌های قدیمی"""
    try:
        now = time.time()
        cutoff = now - (CLEANUP_DAYS * 86400)
        
        for file_path in glob.glob(str(FEEDBACK_DIR / "*")):
            if os.path.isfile(file_path):
                if os.stat(file_path).st_mtime < cutoff:
                    try:
                        os.remove(file_path)
                        logger.info(f"Cleaned up old file: {file_path}")
                    except:
                        pass
    except Exception as e:
        logger.error(f"Cleanup error: {e}")


def find_faq_answer(message: str) -> Optional[str]:
    """جستجوی پاسخ خودکار در FAQ"""
    message_lower = message.lower()
    
    for keyword, answer in FAQ_DATABASE.items():
        if keyword.lower() in message_lower:
            return answer
    
    return None


def format_ticket_summary(ticket: Dict, show_user: bool = False) -> str:
    """فرمت خلاصه تیکت"""
    status_info = TICKET_STATUS.get(ticket.get("status", "open"), {})
    type_info = TICKET_TYPES.get(ticket.get("type", "other"), {})
    
    text = f"{status_info.get('icon', '📩')} <b>{ticket.get('id')}</b>\n"
    text += f"   📌 {type_info.get('short', 'سایر')}"
    
    if show_user:
        text += f" | 👤 {ticket.get('full_name', 'ناشناس')}"
    
    # تعداد پیام‌ها
    conv_count = len(ticket.get("conversation", []))
    if conv_count > 0:
        text += f" | 💬 {conv_count}"
    
    return text


def truncate_text(text: str, max_length: int = 100) -> str:
    """کوتاه کردن متن"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


async def safe_edit_message(
    message: types.Message,
    text: str,
    reply_markup: InlineKeyboardMarkup = None,
    parse_mode: str = "HTML"
) -> types.Message:
    """ویرایش امن پیام"""
    try:
        if message.content_type == types.ContentType.PHOTO:
            await message.delete()
            return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            return await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            try:
                return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
            except:
                pass
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        try:
            return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except:
            pass
    return message


async def notify_admins(bot: Bot, text: str, keyboard: InlineKeyboardMarkup = None,
                        photo_path: str = None, document_path: str = None):
    """ارسال نوتیفیکیشن به همه ادمین‌ها"""
    for admin_id in settings.ADMIN_CHAT_IDS:
        try:
            if photo_path and os.path.exists(photo_path):
                await bot.send_photo(
                    admin_id,
                    FSInputFile(photo_path),
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            elif document_path and os.path.exists(document_path):
                await bot.send_document(
                    admin_id,
                    FSInputFile(document_path),
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    admin_id,
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Error notifying admin {admin_id}: {e}")


# ═══════════════════════════════════════════════════════════════════
# States
# ═══════════════════════════════════════════════════════════════════

class FeedbackState(StatesGroup):
    """حالت‌های سیستم تیکت"""
    
    # ثبت تیکت جدید
    waiting_type = State()
    waiting_message = State()
    waiting_attachment = State()
    confirm_submission = State()
    
    # پاسخ کاربر به تیکت
    user_replying = State()
    
    # ادمین
    admin_replying = State()
    admin_searching = State()
    admin_closing = State()


# ═══════════════════════════════════════════════════════════════════
# منوی اصلی پشتیبانی
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "feedback")
async def feedback_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """منوی اصلی پشتیبانی"""
    
    await state.clear()
    
    user_id = callback.from_user.id
    is_admin = user_id in settings.ADMIN_CHAT_IDS
    
    # آمار کاربر
    user_tickets = get_user_tickets(user_id)
    open_tickets = [t for t in user_tickets if t.get("status") in ["open", "in_progress", "waiting"]]
    
    text = (
        "🎧 <b>مرکز پشتیبانی</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    if open_tickets:
        text += f"📬 شما <b>{len(open_tickets)}</b> تیکت باز دارید.\n\n"
    
    text += (
        "💡 <b>راهنما:</b>\n"
        "   • سوالات متداول را در FAQ بخوانید\n"
        "   • برای مشکلات جدید تیکت ثبت کنید\n"
        "   • پاسخ معمولاً ظرف ۲۴ ساعت داده می‌شود\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 انتخاب کنید:"
    )
    
    buttons = [
        [InlineKeyboardButton(
            text="➕ ثبت درخواست جدید",
            callback_data="fb_new_ticket"
        )],
        [InlineKeyboardButton(
            text=f"📂 تیکت‌های من ({len(user_tickets)})",
            callback_data="fb_my_tickets"
        )],
        [InlineKeyboardButton(
            text="❓ سوالات متداول (FAQ)",
            callback_data="fb_faq"
        )]
    ]
    
    # دکمه‌های ادمین
    if is_admin:
        stats = get_ticket_stats()
        buttons.append([
            InlineKeyboardButton(
                text=f"📊 پنل ادمین ({stats['open']} باز)",
                callback_data="fb_admin_panel"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════
# سوالات متداول (FAQ)
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "fb_faq")
async def show_faq(callback: types.CallbackQuery):
    """نمایش سوالات متداول"""
    
    text = (
        "❓ <b>سوالات متداول (FAQ)</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    faq_categories = {
        "💰 هزینه و شهریه": ["هزینه", "شهریه", "ISEE"],
        "🏠 مسکن": ["خوابگاه", "اجاره", "مسکن"],
        "📝 ثبت‌نام": ["ثبت نام", "پذیرش"],
        "🛂 ویزا": ["ویزا", "سفارت"],
        "⏰ پشتیبانی": ["ادمین", "پاسخ"]
    }
    
    for category, keywords in faq_categories.items():
        text += f"<b>{category}</b>\n"
        for kw in keywords:
            if kw in FAQ_DATABASE:
                text += f"   • {FAQ_DATABASE[kw]}\n"
        text += "\n"
    
    text += (
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 اگر پاسخ خود را پیدا نکردید، تیکت ثبت کنید."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ ثبت تیکت جدید", callback_data="fb_new_ticket")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="feedback")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════
# لیست تیکت‌های کاربر
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "fb_my_tickets")
async def show_my_tickets_menu(callback: types.CallbackQuery):
    """منوی تیکت‌های کاربر"""
    
    user_tickets = get_user_tickets(callback.from_user.id)
    
    open_count = sum(1 for t in user_tickets if t.get("status") in ["open", "in_progress", "waiting"])
    closed_count = sum(1 for t in user_tickets if t.get("status") in ["resolved", "closed"])
    
    text = (
        "📂 <b>تیکت‌های من</b>\n\n"
        f"🟢 باز: {open_count}\n"
        f"🔒 بسته: {closed_count}\n"
        f"📦 کل: {len(user_tickets)}\n\n"
        "نمایش بر اساس:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"🟢 باز ({open_count})", callback_data="fb_list_open_1"),
            InlineKeyboardButton(text=f"🔒 بسته ({closed_count})", callback_data="fb_list_closed_1")
        ],
        [InlineKeyboardButton(text="📋 همه تیکت‌ها", callback_data="fb_list_all_1")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="feedback")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("fb_list_"))
async def show_ticket_list(callback: types.CallbackQuery):
    """نمایش لیست تیکت‌ها با صفحه‌بندی"""
    
    parts = callback.data.split("_")
    filter_type = parts[2]  # open, closed, all
    page = int(parts[3]) if len(parts) > 3 else 1
    
    # دریافت تیکت‌ها
    if filter_type == "all":
        tickets = get_user_tickets(callback.from_user.id)
    else:
        tickets = get_user_tickets(callback.from_user.id, filter_type)
    
    if not tickets:
        await callback.answer("📭 تیکتی یافت نشد.", show_alert=True)
        return
    
    # صفحه‌بندی
    total = len(tickets)
    total_pages = (total + TICKETS_PER_PAGE - 1) // TICKETS_PER_PAGE
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * TICKETS_PER_PAGE
    end_idx = start_idx + TICKETS_PER_PAGE
    current_tickets = tickets[start_idx:end_idx]
    
    # ساخت متن
    filter_labels = {"open": "🟢 باز", "closed": "🔒 بسته", "all": "📋 همه"}
    
    text = f"📂 <b>تیکت‌های من - {filter_labels.get(filter_type, 'همه')}</b>\n"
    text += f"📄 صفحه {page}/{total_pages} | مجموع: {total}\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for ticket in current_tickets:
        text += format_ticket_summary(ticket) + "\n"
    
    # ساخت کیبورد
    buttons = []
    
    # دکمه‌های تیکت‌ها
    for ticket in current_tickets:
        status_icon = TICKET_STATUS.get(ticket.get("status", "open"), {}).get("icon", "📩")
        has_reply = "💬" if ticket.get("conversation") else ""
        unread = "🔴" if ticket.get("last_reply_by") == "admin" and ticket.get("status") != "closed" else ""
        
        btn_text = f"{unread}{status_icon} {ticket['id']} | {TICKET_TYPES.get(ticket.get('type', 'other'), {}).get('short', '؟')}"
        
        buttons.append([
            InlineKeyboardButton(text=btn_text, callback_data=f"fb_view_{ticket['id']}")
        ])
    
    # ناوبری
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"fb_list_{filter_type}_{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="ignore"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"fb_list_{filter_type}_{page+1}"))
    
    if nav_row:
        buttons.append(nav_row)
    
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="fb_my_tickets")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════
# نمایش جزئیات تیکت
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("fb_view_"))
async def view_ticket_detail(callback: types.CallbackQuery):
    """نمایش جزئیات کامل تیکت"""
    
    ticket_id = callback.data.replace("fb_view_", "")
    ticket = get_ticket_by_id(ticket_id)
    
    if not ticket:
        await callback.answer("⚠️ تیکت یافت نشد!", show_alert=True)
        return
    
    # بررسی دسترسی
    is_owner = ticket.get("user_id") == callback.from_user.id
    is_admin = callback.from_user.id in settings.ADMIN_CHAT_IDS
    
    if not is_owner and not is_admin:
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    
    # اطلاعات تیکت
    status_info = TICKET_STATUS.get(ticket.get("status", "open"), {})
    type_info = TICKET_TYPES.get(ticket.get("type", "other"), {})
    priority_info = PRIORITY_LEVELS.get(ticket.get("priority", "medium"), {})
    
    text = f"🎫 <b>تیکت {ticket_id}</b>\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    text += f"📌 <b>نوع:</b> {type_info.get('label', 'سایر')}\n"
    text += f"📊 <b>وضعیت:</b> {status_info.get('label', 'نامشخص')}\n"
    text += f"🎯 <b>اولویت:</b> {priority_info.get('label', 'متوسط')}\n"
    text += f"📅 <b>تاریخ:</b> {ticket.get('created_at', '؟')}\n"
    
    if is_admin:
        text += f"\n👤 <b>کاربر:</b> {ticket.get('full_name', 'ناشناس')}\n"
        if ticket.get("username"):
            text += f"🆔 @{ticket.get('username')}\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # پیام اصلی
    text += f"📝 <b>پیام اصلی:</b>\n{ticket.get('message', '')}\n\n"
    
    # مکالمات
    conversation = ticket.get("conversation", [])
    if conversation:
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"💬 <b>مکالمات ({len(conversation)}):</b>\n\n"
        
        for msg in conversation[-5:]:  # آخرین ۵ پیام
            sender_icon = "👨‍💻" if msg.get("sender") == "admin" else "👤"
            text += f"{sender_icon} <b>{msg.get('sender_name', '؟')}:</b>\n"
            text += f"{truncate_text(msg.get('message', ''), 200)}\n"
            text += f"<i>{msg.get('date', '')}</i>\n\n"
    
    # امتیاز
    if ticket.get("user_rating"):
        text += f"\n⭐ امتیاز شما: {'⭐' * ticket['user_rating']}\n"
    
    # ساخت کیبورد
    buttons = []
    
    status = ticket.get("status", "open")
    
    if status not in ["resolved", "closed"]:
        # تیکت باز است
        if is_owner:
            buttons.append([
                InlineKeyboardButton(text="💬 ارسال پاسخ", callback_data=f"fb_reply_{ticket_id}")
            ])
            buttons.append([
                InlineKeyboardButton(text="✅ مشکلم حل شد", callback_data=f"fb_resolve_{ticket_id}"),
                InlineKeyboardButton(text="🔒 بستن تیکت", callback_data=f"fb_close_{ticket_id}")
            ])
        
        if is_admin:
            buttons.append([
                InlineKeyboardButton(text="✍️ پاسخ ادمین", callback_data=f"fb_admin_reply_{ticket_id}")
            ])
            buttons.append([
                InlineKeyboardButton(text="🔄 تغییر وضعیت", callback_data=f"fb_change_status_{ticket_id}")
            ])
    else:
        # تیکت بسته است
        if is_owner and not ticket.get("user_rating"):
            buttons.append([
                InlineKeyboardButton(text="⭐ ثبت امتیاز", callback_data=f"fb_rate_{ticket_id}")
            ])
        
        if is_owner:
            buttons.append([
                InlineKeyboardButton(text="🔄 بازگشایی تیکت", callback_data=f"fb_reopen_{ticket_id}")
            ])
    
    # دکمه بازگشت
    back_callback = "fb_admin_panel" if is_admin and not is_owner else "fb_my_tickets"
    buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت", callback_data=back_callback)
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # ارسال با عکس اگر موجود باشد
    attachment = ticket.get("attachment")
    att_type = ticket.get("att_type")
    
    if attachment and os.path.exists(attachment) and att_type == "photo":
        try:
            await callback.message.delete()
            await callback.message.answer_photo(
                FSInputFile(attachment),
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await callback.answer()
            return
        except:
            pass
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════
# عملیات روی تیکت
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("fb_resolve_"))
async def resolve_ticket(callback: types.CallbackQuery):
    """علامت‌گذاری تیکت به عنوان حل شده"""
    
    ticket_id = callback.data.replace("fb_resolve_", "")
    ticket = get_ticket_by_id(ticket_id)
    
    if not ticket or ticket.get("user_id") != callback.from_user.id:
        await callback.answer("⚠️ خطا!", show_alert=True)
        return
    
    update_ticket(ticket_id, {"status": "resolved"})
    
    await callback.answer("✅ تیکت به عنوان حل شده علامت‌گذاری شد!", show_alert=True)
    
    # درخواست امتیاز
    callback.data = f"fb_rate_{ticket_id}"
    await ask_rating(callback)


@router.callback_query(F.data.startswith("fb_close_"))
async def close_ticket(callback: types.CallbackQuery):
    """بستن تیکت"""
    
    ticket_id = callback.data.replace("fb_close_", "")
    ticket = get_ticket_by_id(ticket_id)
    
    if not ticket:
        await callback.answer("⚠️ خطا!", show_alert=True)
        return
    
    # بررسی دسترسی
    is_owner = ticket.get("user_id") == callback.from_user.id
    is_admin = callback.from_user.id in settings.ADMIN_CHAT_IDS
    
    if not is_owner and not is_admin:
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    
    update_ticket(ticket_id, {"status": "closed"})
    
    await callback.answer("🔒 تیکت بسته شد!", show_alert=True)
    
    if is_owner:
        callback.data = f"fb_rate_{ticket_id}"
        await ask_rating(callback)
    else:
        callback.data = f"fb_view_{ticket_id}"
        await view_ticket_detail(callback)


@router.callback_query(F.data.startswith("fb_reopen_"))
async def reopen_ticket(callback: types.CallbackQuery):
    """بازگشایی تیکت"""
    
    ticket_id = callback.data.replace("fb_reopen_", "")
    ticket = get_ticket_by_id(ticket_id)
    
    if not ticket or ticket.get("user_id") != callback.from_user.id:
        await callback.answer("⚠️ خطا!", show_alert=True)
        return
    
    update_ticket(ticket_id, {"status": "open"})
    
    await callback.answer("🔓 تیکت مجدداً باز شد!", show_alert=True)
    
    callback.data = f"fb_view_{ticket_id}"
    await view_ticket_detail(callback)


# ═══════════════════════════════════════════════════════════════════
# سیستم امتیازدهی
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("fb_rate_"))
async def ask_rating(callback: types.CallbackQuery):
    """درخواست امتیاز"""
    
    ticket_id = callback.data.replace("fb_rate_", "")
    
    text = (
        "⭐ <b>امتیازدهی به پشتیبانی</b>\n\n"
        f"🎫 تیکت: {ticket_id}\n\n"
        "لطفاً از ۱ تا ۵ امتیاز دهید:\n\n"
        "😡 ۱ = خیلی بد\n"
        "😕 ۲ = بد\n"
        "😐 ۳ = متوسط\n"
        "🙂 ۴ = خوب\n"
        "😍 ۵ = عالی"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="😡 ۱", callback_data=f"fb_score_1_{ticket_id}"),
            InlineKeyboardButton(text="😕 ۲", callback_data=f"fb_score_2_{ticket_id}"),
            InlineKeyboardButton(text="😐 ۳", callback_data=f"fb_score_3_{ticket_id}"),
            InlineKeyboardButton(text="🙂 ۴", callback_data=f"fb_score_4_{ticket_id}"),
            InlineKeyboardButton(text="😍 ۵", callback_data=f"fb_score_5_{ticket_id}")
        ],
        [InlineKeyboardButton(text="⏭ بعداً", callback_data="fb_my_tickets")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("fb_score_"))
async def save_rating(callback: types.CallbackQuery):
    """ذخیره امتیاز"""
    
    parts = callback.data.split("_")
    score = int(parts[2])
    ticket_id = parts[3]
    
    update_ticket(ticket_id, {"user_rating": score})
    
    emoji = ["", "😡", "😕", "😐", "🙂", "😍"][score]
    
    text = (
        f"✅ <b>امتیاز ثبت شد!</b>\n\n"
        f"🎫 تیکت: {ticket_id}\n"
        f"⭐ امتیاز: {emoji} {score}/5\n\n"
        "با تشکر از بازخورد شما!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📂 تیکت‌های من", callback_data="fb_my_tickets")],
        [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer("✅ ثبت شد!")


# ═══════════════════════════════════════════════════════════════════
# پایان بخش ۱
# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# بخش ۲: ثبت تیکت جدید، آپلود فایل، پاسخ کاربر، پاسخ هوشمند
# ═══════════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────────
# شروع ثبت تیکت جدید
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "fb_new_ticket")
async def start_new_ticket(callback: types.CallbackQuery, state: FSMContext):
    """شروع فرآیند ثبت تیکت جدید"""
    
    await state.clear()
    
    text = (
        "📝 <b>ثبت تیکت جدید</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 <b>مرحله ۱ از ۳</b>\n\n"
        "موضوع پیام خود را انتخاب کنید:"
    )
    
    # ساخت دکمه‌ها از TICKET_TYPES
    buttons = []
    row = []
    
    for key, info in TICKET_TYPES.items():
        row.append(
            InlineKeyboardButton(
                text=info["label"],
                callback_data=f"fb_type_{key}"
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton(text="❌ انصراف", callback_data="feedback")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await safe_edit_message(callback.message, text, keyboard)
    await state.set_state(FeedbackState.waiting_type)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# انتخاب نوع تیکت
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fb_type_"), FeedbackState.waiting_type)
async def select_ticket_type(callback: types.CallbackQuery, state: FSMContext):
    """انتخاب نوع تیکت"""
    
    ticket_type = callback.data.replace("fb_type_", "")
    type_info = TICKET_TYPES.get(ticket_type, TICKET_TYPES["other"])
    
    await state.update_data(
        ticket_type=ticket_type,
        ticket_type_label=type_info["label"],
        ticket_priority=type_info["priority"]
    )
    
    await state.set_state(FeedbackState.waiting_message)
    
    text = (
        f"✅ موضوع: {type_info['label']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📝 <b>مرحله ۲ از ۳</b>\n\n"
        "لطفاً پیام خود را بنویسید:\n\n"
        "💡 <b>نکات:</b>\n"
        "   • مشکل را با جزئیات توضیح دهید\n"
        "   • اگر خطا دارید، متن خطا را کپی کنید\n"
        "   • مراحل رسیدن به مشکل را بنویسید\n\n"
        f"📏 حداکثر {MAX_MESSAGE_LENGTH} کاراکتر"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data="feedback")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# دریافت متن پیام
# ───────────────────────────────────────────────────────────────────

@router.message(FeedbackState.waiting_message, F.text)
async def receive_ticket_message(message: types.Message, state: FSMContext):
    """دریافت متن پیام تیکت"""
    
    msg_text = message.text.strip()
    
    # اعتبارسنجی
    if len(msg_text) < 10:
        await message.reply(
            "⚠️ <b>پیام خیلی کوتاه است!</b>\n\n"
            "لطفاً حداقل ۱۰ کاراکتر بنویسید.",
            parse_mode="HTML"
        )
        return
    
    if len(msg_text) > MAX_MESSAGE_LENGTH:
        await message.reply(
            f"⚠️ <b>پیام خیلی طولانی است!</b>\n\n"
            f"حداکثر {MAX_MESSAGE_LENGTH} کاراکتر مجاز است.\n"
            f"پیام شما: {len(msg_text)} کاراکتر",
            parse_mode="HTML"
        )
        return
    
    # بررسی پاسخ خودکار FAQ
    faq_answer = find_faq_answer(msg_text)
    
    if faq_answer:
        await state.update_data(temp_message=msg_text, faq_answer=faq_answer)
        
        text = (
            "🤖 <b>پاسخ هوشمند</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{faq_answer}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "آیا این پاسخ مشکل شما را حل کرد؟"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ بله، حل شد!", callback_data="fb_faq_solved"),
                InlineKeyboardButton(text="❌ خیر", callback_data="fb_faq_continue")
            ],
            [InlineKeyboardButton(text="🔄 سوال دیگر", callback_data="fb_new_ticket")]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        return
    
    # ذخیره پیام و رفتن به مرحله بعد
    await state.update_data(message_text=msg_text)
    await ask_for_attachment(message, state)


@router.callback_query(F.data == "fb_faq_solved")
async def faq_solved(callback: types.CallbackQuery, state: FSMContext):
    """پاسخ FAQ مشکل را حل کرد"""
    
    await state.clear()
    
    text = (
        "🎉 <b>عالی!</b>\n\n"
        "خوشحالیم که مشکل شما حل شد.\n\n"
        "اگر سوال دیگری دارید، خوشحال می‌شویم کمک کنیم."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ سوال جدید", callback_data="fb_new_ticket")],
        [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data == "fb_faq_continue")
async def faq_continue(callback: types.CallbackQuery, state: FSMContext):
    """پاسخ FAQ کافی نبود - ادامه ثبت تیکت"""
    
    data = await state.get_data()
    msg_text = data.get("temp_message", "")
    
    await state.update_data(message_text=msg_text)
    
    await ask_for_attachment(callback.message, state, is_callback=True)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# درخواست فایل ضمیمه
# ───────────────────────────────────────────────────────────────────

async def ask_for_attachment(message_or_callback, state: FSMContext, is_callback: bool = False):
    """درخواست فایل ضمیمه"""
    
    await state.set_state(FeedbackState.waiting_attachment)
    
    extensions = ", ".join(ALLOWED_EXTENSIONS)
    
    text = (
        "📎 <b>مرحله ۳ از ۳ - فایل ضمیمه</b>\n\n"
        "آیا فایلی برای ضمیمه کردن دارید؟\n\n"
        "💡 <b>فایل‌های مجاز:</b>\n"
        f"   {extensions}\n\n"
        f"📏 حداکثر حجم: {MAX_FILE_SIZE // (1024*1024)} مگابایت\n\n"
        "اگر فایل دارید، همینجا ارسال کنید.\n"
        "در غیر این صورت، «بدون فایل» را بزنید."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 ارسال عکس", callback_data="fb_attach_photo")],
        [InlineKeyboardButton(text="📄 ارسال سند", callback_data="fb_attach_doc")],
        [InlineKeyboardButton(text="➡️ بدون فایل (ادامه)", callback_data="fb_skip_attach")],
        [InlineKeyboardButton(text="❌ انصراف", callback_data="feedback")]
    ])
    
    if is_callback:
        await safe_edit_message(message_or_callback, text, keyboard)
    else:
        await message_or_callback.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "fb_attach_photo")
async def request_photo(callback: types.CallbackQuery):
    """درخواست ارسال عکس"""
    
    text = (
        "📸 <b>ارسال عکس</b>\n\n"
        "لطفاً عکس مورد نظر را ارسال کنید.\n\n"
        "💡 می‌توانید اسکرین‌شات از خطا ارسال کنید."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="fb_back_to_attach")],
        [InlineKeyboardButton(text="➡️ بدون فایل", callback_data="fb_skip_attach")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data == "fb_attach_doc")
async def request_document(callback: types.CallbackQuery):
    """درخواست ارسال سند"""
    
    extensions = ", ".join(ALLOWED_EXTENSIONS)
    
    text = (
        "📄 <b>ارسال سند</b>\n\n"
        "لطفاً فایل مورد نظر را ارسال کنید.\n\n"
        f"💡 فرمت‌های مجاز: {extensions}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="fb_back_to_attach")],
        [InlineKeyboardButton(text="➡️ بدون فایل", callback_data="fb_skip_attach")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data == "fb_back_to_attach")
async def back_to_attachment(callback: types.CallbackQuery, state: FSMContext):
    """بازگشت به صفحه انتخاب فایل"""
    
    await ask_for_attachment(callback.message, state, is_callback=True)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# دریافت فایل ضمیمه
# ───────────────────────────────────────────────────────────────────

@router.message(FeedbackState.waiting_attachment, F.photo)
async def receive_photo(message: types.Message, state: FSMContext):
    """دریافت عکس"""
    
    try:
        # پاکسازی فایل‌های قدیمی
        smart_cleanup()
        
        # دریافت عکس با بهترین کیفیت
        photo = message.photo[-1]
        file_id = photo.file_id
        
        # بررسی حجم (تقریبی)
        if photo.file_size and photo.file_size > MAX_FILE_SIZE:
            await message.reply(
                f"⚠️ حجم فایل بیش از {MAX_FILE_SIZE // (1024*1024)} مگابایت است!",
                parse_mode="HTML"
            )
            return
        
        # ذخیره فایل
        timestamp = int(datetime.now().timestamp())
        file_name = f"{message.from_user.id}_{timestamp}.jpg"
        file_path = FEEDBACK_DIR / file_name
        
        await message.bot.download(file_id, destination=file_path)
        
        await state.update_data(
            attachment_path=str(file_path),
            attachment_type="photo",
            attachment_name=file_name
        )
        
        await show_ticket_preview(message, state)
        
    except Exception as e:
        logger.error(f"Error receiving photo: {e}")
        await message.reply("⚠️ خطا در دریافت عکس. لطفاً دوباره تلاش کنید.")


@router.message(FeedbackState.waiting_attachment, F.document)
async def receive_document(message: types.Message, state: FSMContext):
    """دریافت سند"""
    
    try:
        smart_cleanup()
        
        doc = message.document
        
        # بررسی حجم
        if doc.file_size and doc.file_size > MAX_FILE_SIZE:
            await message.reply(
                f"⚠️ حجم فایل بیش از {MAX_FILE_SIZE // (1024*1024)} مگابایت است!"
            )
            return
        
        # بررسی پسوند
        file_name = doc.file_name or "document"
        ext = os.path.splitext(file_name)[1].lower()
        
        if ext not in ALLOWED_EXTENSIONS:
            await message.reply(
                f"⚠️ فرمت {ext} مجاز نیست!\n\n"
                f"فرمت‌های مجاز: {', '.join(ALLOWED_EXTENSIONS)}"
            )
            return
        
        # ذخیره فایل
        timestamp = int(datetime.now().timestamp())
        safe_name = f"{message.from_user.id}_{timestamp}{ext}"
        file_path = FEEDBACK_DIR / safe_name
        
        await message.bot.download(doc.file_id, destination=file_path)
        
        await state.update_data(
            attachment_path=str(file_path),
            attachment_type="document",
            attachment_name=file_name
        )
        
        await show_ticket_preview(message, state)
        
    except Exception as e:
        logger.error(f"Error receiving document: {e}")
        await message.reply("⚠️ خطا در دریافت فایل. لطفاً دوباره تلاش کنید.")


@router.callback_query(F.data == "fb_skip_attach", FeedbackState.waiting_attachment)
async def skip_attachment(callback: types.CallbackQuery, state: FSMContext):
    """رد کردن فایل ضمیمه"""
    
    await state.update_data(
        attachment_path=None,
        attachment_type=None,
        attachment_name=None
    )
    
    await show_ticket_preview(callback.message, state, is_callback=True)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# پیش‌نمایش و تأیید تیکت
# ───────────────────────────────────────────────────────────────────

async def show_ticket_preview(message_or_callback, state: FSMContext, is_callback: bool = False):
    """نمایش پیش‌نمایش تیکت"""
    
    await state.set_state(FeedbackState.confirm_submission)
    
    data = await state.get_data()
    
    type_label = data.get("ticket_type_label", "سایر")
    priority = data.get("ticket_priority", "medium")
    priority_info = PRIORITY_LEVELS.get(priority, {})
    msg_text = data.get("message_text", "")
    attachment_name = data.get("attachment_name")
    
    text = (
        "📋 <b>پیش‌نمایش تیکت</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📌 <b>موضوع:</b> {type_label}\n"
        f"🎯 <b>اولویت:</b> {priority_info.get('label', 'متوسط')}\n"
        f"📎 <b>فایل:</b> {'✅ ' + attachment_name if attachment_name else '❌ بدون فایل'}\n\n"
        f"📝 <b>متن پیام:</b>\n{truncate_text(msg_text, 500)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "آیا تیکت را ثبت می‌کنید؟"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تأیید و ارسال", callback_data="fb_submit_final"),
            InlineKeyboardButton(text="❌ لغو", callback_data="feedback")
        ],
        [InlineKeyboardButton(text="✏️ ویرایش پیام", callback_data="fb_edit_message")]
    ])
    
    # اگر عکس داریم، با عکس نمایش بده
    attachment_path = data.get("attachment_path")
    attachment_type = data.get("attachment_type")
    
    if attachment_path and os.path.exists(attachment_path) and attachment_type == "photo":
        try:
            if is_callback:
                await message_or_callback.delete()
            await message_or_callback.answer_photo(
                FSInputFile(attachment_path),
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            return
        except:
            pass
    
    if is_callback:
        await safe_edit_message(message_or_callback, text, keyboard)
    else:
        await message_or_callback.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "fb_edit_message")
async def edit_ticket_message(callback: types.CallbackQuery, state: FSMContext):
    """ویرایش متن پیام"""
    
    await state.set_state(FeedbackState.waiting_message)
    
    text = (
        "✏️ <b>ویرایش پیام</b>\n\n"
        "لطفاً متن جدید را بنویسید:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data="feedback")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# ثبت نهایی تیکت
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "fb_submit_final", FeedbackState.confirm_submission)
async def submit_ticket_final(callback: types.CallbackQuery, state: FSMContext):
    """ثبت نهایی تیکت"""
    
    data = await state.get_data()
    
    # تولید شناسه
    ticket_id = generate_ticket_id()
    
    # ساخت تیکت
    ticket = {
        "id": ticket_id,
        "user_id": callback.from_user.id,
        "username": callback.from_user.username,
        "full_name": callback.from_user.full_name,
        "type": data.get("ticket_type", "other"),
        "type_label": data.get("ticket_type_label", "سایر"),
        "priority": data.get("ticket_priority", "medium"),
        "message": data.get("message_text", ""),
        "attachment": data.get("attachment_path"),
        "att_type": data.get("attachment_type"),
        "att_name": data.get("attachment_name"),
        "status": "open",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "conversation": [],
        "user_rating": None,
        "last_reply_by": "user"
    }
    
    # ذخیره در دیتابیس
    tickets = load_feedbacks()
    tickets.append(ticket)
    save_feedbacks(tickets)
    
    # ارسال به ادمین‌ها
    await notify_admins_new_ticket(callback.message.bot, ticket)
    
    await state.clear()
    
    # پیام تأیید به کاربر
    priority_info = PRIORITY_LEVELS.get(ticket["priority"], {})
    
    text = (
        "✅ <b>تیکت با موفقیت ثبت شد!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎫 <b>شماره تیکت:</b> <code>{ticket_id}</code>\n"
        f"📌 <b>موضوع:</b> {ticket['type_label']}\n"
        f"🎯 <b>اولویت:</b> {priority_info.get('label', 'متوسط')}\n"
        f"📅 <b>تاریخ:</b> {ticket['created_at']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏳ تیم پشتیبانی در اسرع وقت پاسخ خواهد داد.\n"
        "🔔 پاسخ از طریق همین ربات به شما اطلاع داده می‌شود."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👁 مشاهده تیکت", callback_data=f"fb_view_{ticket_id}")],
        [InlineKeyboardButton(text="📂 تیکت‌های من", callback_data="fb_my_tickets")],
        [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer("✅ تیکت ثبت شد!")


async def notify_admins_new_ticket(bot: Bot, ticket: Dict):
    """اطلاع‌رسانی به ادمین‌ها برای تیکت جدید"""
    
    type_info = TICKET_TYPES.get(ticket.get("type", "other"), {})
    priority_info = PRIORITY_LEVELS.get(ticket.get("priority", "medium"), {})
    
    # آیکون بر اساس اولویت
    priority_icon = "🚨" if ticket["priority"] in ["critical", "high"] else "📩"
    
    text = (
        f"{priority_icon} <b>تیکت جدید!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎫 <b>شماره:</b> <code>{ticket['id']}</code>\n"
        f"📌 <b>نوع:</b> {type_info.get('label', 'سایر')}\n"
        f"🎯 <b>اولویت:</b> {priority_info.get('label', 'متوسط')}\n"
        f"📅 <b>تاریخ:</b> {ticket['created_at']}\n\n"
        f"👤 <b>کاربر:</b> {ticket.get('full_name', 'ناشناس')}\n"
    )
    
    if ticket.get("username"):
        text += f"🆔 <b>یوزرنیم:</b> @{ticket['username']}\n"
    
    text += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 <b>پیام:</b>\n{truncate_text(ticket.get('message', ''), 500)}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✍️ پاسخ دادن",
                callback_data=f"fb_admin_reply_{ticket['id']}"
            )
        ],
        [
            InlineKeyboardButton(
                text="👁 مشاهده کامل",
                callback_data=f"fb_view_{ticket['id']}"
            ),
            InlineKeyboardButton(
                text="🔄 تغییر وضعیت",
                callback_data=f"fb_change_status_{ticket['id']}"
            )
        ]
    ])
    
    # ارسال با فایل ضمیمه
    attachment = ticket.get("attachment")
    att_type = ticket.get("att_type")
    
    if attachment and os.path.exists(attachment):
        if att_type == "photo":
            await notify_admins(bot, text, keyboard, photo_path=attachment)
        else:
            await notify_admins(bot, text, keyboard, document_path=attachment)
    else:
        await notify_admins(bot, text, keyboard)


# ───────────────────────────────────────────────────────────────────
# پاسخ کاربر به تیکت
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fb_reply_"))
async def user_start_reply(callback: types.CallbackQuery, state: FSMContext):
    """شروع پاسخ کاربر به تیکت"""
    
    ticket_id = callback.data.replace("fb_reply_", "")
    ticket = get_ticket_by_id(ticket_id)
    
    if not ticket or ticket.get("user_id") != callback.from_user.id:
        await callback.answer("⚠️ تیکت یافت نشد!", show_alert=True)
        return
    
    if ticket.get("status") in ["resolved", "closed"]:
        await callback.answer("⚠️ این تیکت بسته شده است!", show_alert=True)
        return
    
    await state.update_data(reply_ticket_id=ticket_id)
    await state.set_state(FeedbackState.user_replying)
    
    text = (
        f"💬 <b>پاسخ به تیکت {ticket_id}</b>\n\n"
        "لطفاً پیام خود را بنویسید:\n\n"
        f"📏 حداکثر {MAX_MESSAGE_LENGTH} کاراکتر"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data=f"fb_view_{ticket_id}")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.message(FeedbackState.user_replying, F.text)
async def process_user_reply(message: types.Message, state: FSMContext):
    """پردازش پاسخ کاربر"""
    
    data = await state.get_data()
    ticket_id = data.get("reply_ticket_id")
    
    if not ticket_id:
        await state.clear()
        return
    
    msg_text = message.text.strip()
    
    # اعتبارسنجی
    if len(msg_text) < 5:
        await message.reply("⚠️ پیام خیلی کوتاه است!")
        return
    
    if len(msg_text) > MAX_MESSAGE_LENGTH:
        await message.reply(f"⚠️ پیام نباید بیش از {MAX_MESSAGE_LENGTH} کاراکتر باشد!")
        return
    
    # افزودن به مکالمه
    add_message_to_ticket(
        ticket_id,
        sender="user",
        message=msg_text,
        sender_id=message.from_user.id,
        sender_name=message.from_user.full_name
    )
    
    # بروزرسانی وضعیت
    update_ticket(ticket_id, {"status": "open"})
    
    # اطلاع به ادمین‌ها
    ticket = get_ticket_by_id(ticket_id)
    
    admin_text = (
        f"💬 <b>پاسخ جدید از کاربر</b>\n\n"
        f"🎫 تیکت: <code>{ticket_id}</code>\n"
        f"👤 {message.from_user.full_name}\n\n"
        f"📝 پیام:\n{truncate_text(msg_text, 500)}"
    )
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ پاسخ", callback_data=f"fb_admin_reply_{ticket_id}")],
        [InlineKeyboardButton(text="👁 مشاهده", callback_data=f"fb_view_{ticket_id}")]
    ])
    
    await notify_admins(message.bot, admin_text, admin_kb)
    
    await state.clear()
    
    # تأیید به کاربر
    text = (
        "✅ <b>پاسخ شما ارسال شد!</b>\n\n"
        f"🎫 تیکت: {ticket_id}\n\n"
        "منتظر پاسخ پشتیبانی باشید."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👁 مشاهده تیکت", callback_data=f"fb_view_{ticket_id}")],
        [InlineKeyboardButton(text="📂 تیکت‌های من", callback_data="fb_my_tickets")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ───────────────────────────────────────────────────────────────────
# هندل پیام‌های اشتباهی در state های دیگر
# ───────────────────────────────────────────────────────────────────

@router.message(FeedbackState.waiting_attachment)
async def wrong_attachment_type(message: types.Message):
    """وقتی کاربر چیزی غیر از عکس یا فایل ارسال می‌کند"""
    
    await message.reply(
        "⚠️ لطفاً فقط <b>عکس</b> یا <b>فایل</b> ارسال کنید.\n\n"
        "یا دکمه «بدون فایل» را بزنید.",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════
# پایان بخش ۲
# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# بخش ۳: پنل ادمین، پاسخگویی، تغییر وضعیت، آمار
# ═══════════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────────
# پنل اصلی ادمین
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "fb_admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    """پنل اصلی مدیریت تیکت‌ها"""
    
    # بررسی دسترسی ادمین
    if callback.from_user.id not in settings.ADMIN_CHAT_IDS:
        await callback.answer("⛔ شما دسترسی ادمین ندارید!", show_alert=True)
        return
    
    # دریافت آمار
    stats = get_ticket_stats()
    
    text = (
        "📊 <b>پنل مدیریت تیکت‌ها</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "📈 <b>آمار کلی:</b>\n"
        f"   📦 کل تیکت‌ها: <b>{stats['total']}</b>\n"
        f"   🟢 باز: <b>{stats['open']}</b>\n"
        f"   🟡 در حال بررسی: <b>{stats['in_progress']}</b>\n"
        f"   ⏳ منتظر پاسخ: <b>{stats['waiting']}</b>\n"
        f"   ✅ حل شده: <b>{stats['resolved']}</b>\n"
        f"   🔒 بسته: <b>{stats['closed']}</b>\n\n"
        
        f"📅 تیکت‌های امروز: <b>{stats['today']}</b>\n"
    )
    
    if stats['avg_rating'] > 0:
        stars = "⭐" * int(stats['avg_rating'])
        text += f"⭐ میانگین امتیاز: {stars} ({stats['avg_rating']}/5)\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    # تعداد تیکت‌های نیازمند توجه
    urgent_count = stats['open'] + stats['in_progress']
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"🟢 تیکت‌های باز ({stats['open']})",
                callback_data="fb_admin_list_open_1"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🟡 در حال بررسی ({stats['in_progress']})",
                callback_data="fb_admin_list_progress_1"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"⏳ منتظر پاسخ کاربر ({stats['waiting']})",
                callback_data="fb_admin_list_waiting_1"
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 همه تیکت‌ها",
                callback_data="fb_admin_list_all_1"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔍 جستجوی تیکت",
                callback_data="fb_admin_search"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 آمار تفصیلی",
                callback_data="fb_admin_detailed_stats"
            )
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="feedback")
        ]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# لیست تیکت‌ها برای ادمین
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fb_admin_list_"))
async def admin_list_tickets(callback: types.CallbackQuery):
    """لیست تیکت‌ها برای ادمین"""
    
    if callback.from_user.id not in settings.ADMIN_CHAT_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    
    parts = callback.data.replace("fb_admin_list_", "").split("_")
    filter_type = parts[0]  # open, progress, waiting, all
    page = int(parts[1]) if len(parts) > 1 else 1
    
    # دریافت تیکت‌ها
    all_tickets = load_feedbacks()
    
    # فیلتر
    if filter_type == "open":
        tickets = [t for t in all_tickets if t.get("status") == "open"]
        filter_label = "🟢 باز"
    elif filter_type == "progress":
        tickets = [t for t in all_tickets if t.get("status") == "in_progress"]
        filter_label = "🟡 در حال بررسی"
    elif filter_type == "waiting":
        tickets = [t for t in all_tickets if t.get("status") == "waiting"]
        filter_label = "⏳ منتظر پاسخ"
    else:
        tickets = all_tickets
        filter_label = "📋 همه"
    
    if not tickets:
        await callback.answer("📭 تیکتی یافت نشد!", show_alert=True)
        return
    
    # مرتب‌سازی بر اساس اولویت و تاریخ
    def sort_key(t):
        priority_order = PRIORITY_LEVELS.get(t.get("priority", "medium"), {}).get("order", 3)
        return (priority_order, t.get("created_at", ""))
    
    tickets.sort(key=sort_key)
    
    # صفحه‌بندی
    total = len(tickets)
    total_pages = (total + TICKETS_PER_PAGE - 1) // TICKETS_PER_PAGE
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * TICKETS_PER_PAGE
    end_idx = start_idx + TICKETS_PER_PAGE
    current_tickets = tickets[start_idx:end_idx]
    
    # ساخت متن
    text = f"📋 <b>تیکت‌ها - {filter_label}</b>\n"
    text += f"📄 صفحه {page}/{total_pages} | مجموع: {total}\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for ticket in current_tickets:
        priority_info = PRIORITY_LEVELS.get(ticket.get("priority", "medium"), {})
        status_info = TICKET_STATUS.get(ticket.get("status", "open"), {})
        
        text += f"{priority_info.get('color', '⚪')} <b>{ticket['id']}</b>\n"
        text += f"   👤 {ticket.get('full_name', '؟')[:15]}\n"
        text += f"   📌 {TICKET_TYPES.get(ticket.get('type', 'other'), {}).get('short', '؟')}"
        text += f" | {status_info.get('icon', '📩')}\n"
        
        # تعداد پیام‌ها
        conv_count = len(ticket.get("conversation", []))
        if conv_count > 0:
            text += f"   💬 {conv_count} پیام"
        
        text += f" | 📅 {ticket.get('created_at', '')[:10]}\n\n"
    
    # ساخت کیبورد
    buttons = []
    
    # دکمه‌های تیکت‌ها
    for ticket in current_tickets:
        priority_info = PRIORITY_LEVELS.get(ticket.get("priority", "medium"), {})
        status_info = TICKET_STATUS.get(ticket.get("status", "open"), {})
        
        # نشانگر پیام جدید
        new_msg = "🔴" if ticket.get("last_reply_by") == "user" else ""
        
        btn_text = f"{new_msg}{priority_info.get('color', '⚪')} {ticket['id']} | {ticket.get('full_name', '؟')[:10]}"
        
        buttons.append([
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"fb_view_{ticket['id']}"
            )
        ])
    
    # ناوبری
    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"fb_admin_list_{filter_type}_{page-1}")
        )
    nav_row.append(
        InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="ignore")
    )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(text="➡️", callback_data=f"fb_admin_list_{filter_type}_{page+1}")
        )
    
    if nav_row:
        buttons.append(nav_row)
    
    buttons.append([
        InlineKeyboardButton(text="🔙 پنل ادمین", callback_data="fb_admin_panel")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# پاسخ ادمین به تیکت
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fb_admin_reply_"))
async def admin_start_reply(callback: types.CallbackQuery, state: FSMContext):
    """شروع پاسخ ادمین به تیکت"""
    
    if callback.from_user.id not in settings.ADMIN_CHAT_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    
    ticket_id = callback.data.replace("fb_admin_reply_", "")
    ticket = get_ticket_by_id(ticket_id)
    
    if not ticket:
        await callback.answer("⚠️ تیکت یافت نشد!", show_alert=True)
        return
    
    await state.update_data(
        admin_reply_ticket_id=ticket_id,
        admin_reply_user_id=ticket.get("user_id"),
        admin_reply_user_name=ticket.get("full_name", "کاربر")
    )
    await state.set_state(FeedbackState.admin_replying)
    
    text = (
        f"✍️ <b>پاسخ به تیکت {ticket_id}</b>\n\n"
        f"👤 کاربر: {ticket.get('full_name', '؟')}\n"
        f"📌 موضوع: {ticket.get('type_label', '؟')}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 پیام اصلی:\n{truncate_text(ticket.get('message', ''), 300)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "لطفاً پاسخ خود را بنویسید:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data=f"fb_view_{ticket_id}")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.message(FeedbackState.admin_replying, F.text)
async def process_admin_reply(message: types.Message, state: FSMContext):
    """پردازش پاسخ ادمین"""
    
    if message.from_user.id not in settings.ADMIN_CHAT_IDS:
        await state.clear()
        return
    
    data = await state.get_data()
    ticket_id = data.get("admin_reply_ticket_id")
    user_id = data.get("admin_reply_user_id")
    user_name = data.get("admin_reply_user_name", "کاربر")
    
    if not ticket_id or not user_id:
        await state.clear()
        await message.reply("⚠️ خطا! لطفاً دوباره تلاش کنید.")
        return
    
    reply_text = message.text.strip()
    
    # اعتبارسنجی
    if len(reply_text) < 5:
        await message.reply("⚠️ پاسخ خیلی کوتاه است!")
        return
    
    if len(reply_text) > MAX_MESSAGE_LENGTH:
        await message.reply(f"⚠️ پاسخ نباید بیش از {MAX_MESSAGE_LENGTH} کاراکتر باشد!")
        return
    
    # افزودن به مکالمه
    add_message_to_ticket(
        ticket_id,
        sender="admin",
        message=reply_text,
        sender_id=message.from_user.id,
        sender_name=message.from_user.full_name
    )
    
    # بروزرسانی وضعیت به "در حال بررسی" یا "منتظر پاسخ کاربر"
    update_ticket(ticket_id, {"status": "waiting"})
    
    # ارسال نوتیفیکیشن به کاربر
    user_notification = (
        f"📩 <b>پاسخ جدید از پشتیبانی!</b>\n\n"
        f"🎫 تیکت: <code>{ticket_id}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👨‍💻 <b>پاسخ:</b>\n{reply_text}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "می‌توانید پاسخ دهید یا تیکت را ببندید."
    )
    
    user_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👁 مشاهده تیکت", callback_data=f"fb_view_{ticket_id}")],
        [InlineKeyboardButton(text="💬 ارسال پاسخ", callback_data=f"fb_reply_{ticket_id}")],
        [
            InlineKeyboardButton(text="✅ مشکلم حل شد", callback_data=f"fb_resolve_{ticket_id}"),
            InlineKeyboardButton(text="🔒 بستن", callback_data=f"fb_close_{ticket_id}")
        ]
    ])
    
    try:
        await message.bot.send_message(
            user_id,
            user_notification,
            reply_markup=user_kb,
            parse_mode="HTML"
        )
        notification_status = "✅ کاربر مطلع شد"
    except Exception as e:
        logger.error(f"Error notifying user {user_id}: {e}")
        notification_status = "⚠️ خطا در اطلاع‌رسانی به کاربر"
    
    await state.clear()
    
    # تأیید به ادمین
    text = (
        "✅ <b>پاسخ ارسال شد!</b>\n\n"
        f"🎫 تیکت: {ticket_id}\n"
        f"👤 کاربر: {user_name}\n"
        f"📊 {notification_status}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👁 مشاهده تیکت", callback_data=f"fb_view_{ticket_id}")],
        [InlineKeyboardButton(text="📋 لیست تیکت‌ها", callback_data="fb_admin_list_open_1")],
        [InlineKeyboardButton(text="📊 پنل ادمین", callback_data="fb_admin_panel")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ───────────────────────────────────────────────────────────────────
# تغییر وضعیت تیکت
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fb_change_status_"))
async def change_status_menu(callback: types.CallbackQuery):
    """منوی تغییر وضعیت تیکت"""
    
    if callback.from_user.id not in settings.ADMIN_CHAT_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    
    ticket_id = callback.data.replace("fb_change_status_", "")
    ticket = get_ticket_by_id(ticket_id)
    
    if not ticket:
        await callback.answer("⚠️ تیکت یافت نشد!", show_alert=True)
        return
    
    current_status = ticket.get("status", "open")
    current_info = TICKET_STATUS.get(current_status, {})
    
    text = (
        f"🔄 <b>تغییر وضعیت تیکت {ticket_id}</b>\n\n"
        f"وضعیت فعلی: {current_info.get('label', '؟')}\n\n"
        "وضعیت جدید را انتخاب کنید:"
    )
    
    buttons = []
    
    for status_key, status_info in TICKET_STATUS.items():
        if status_key != current_status:
            buttons.append([
                InlineKeyboardButton(
                    text=status_info["label"],
                    callback_data=f"fb_set_status_{ticket_id}_{status_key}"
                )
            ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"fb_view_{ticket_id}")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("fb_set_status_"))
async def set_ticket_status(callback: types.CallbackQuery):
    """تنظیم وضعیت تیکت"""
    
    if callback.from_user.id not in settings.ADMIN_CHAT_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    
    parts = callback.data.replace("fb_set_status_", "").split("_")
    ticket_id = parts[0]
    new_status = parts[1] if len(parts) > 1 else "open"
    
    ticket = get_ticket_by_id(ticket_id)
    
    if not ticket:
        await callback.answer("⚠️ تیکت یافت نشد!", show_alert=True)
        return
    
    # بروزرسانی وضعیت
    update_ticket(ticket_id, {"status": new_status})
    
    status_info = TICKET_STATUS.get(new_status, {})
    
    await callback.answer(
        f"✅ وضعیت به {status_info.get('label', new_status)} تغییر کرد!",
        show_alert=True
    )
    
    # اطلاع به کاربر (اختیاری - برای وضعیت‌های مهم)
    if new_status in ["resolved", "closed"]:
        try:
            user_text = (
                f"🔔 <b>بروزرسانی تیکت</b>\n\n"
                f"🎫 تیکت: <code>{ticket_id}</code>\n"
                f"📊 وضعیت جدید: {status_info.get('label', new_status)}"
            )
            
            user_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👁 مشاهده", callback_data=f"fb_view_{ticket_id}")]
            ])
            
            await callback.bot.send_message(
                ticket.get("user_id"),
                user_text,
                reply_markup=user_kb,
                parse_mode="HTML"
            )
        except:
            pass
    
    # بازگشت به جزئیات تیکت
    callback.data = f"fb_view_{ticket_id}"
    await view_ticket_detail(callback)


# ───────────────────────────────────────────────────────────────────
# جستجوی تیکت
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "fb_admin_search")
async def admin_search_start(callback: types.CallbackQuery, state: FSMContext):
    """شروع جستجوی تیکت"""
    
    if callback.from_user.id not in settings.ADMIN_CHAT_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    
    await state.set_state(FeedbackState.admin_searching)
    
    text = (
        "🔍 <b>جستجوی تیکت</b>\n\n"
        "شماره تیکت یا نام کاربر را وارد کنید:\n\n"
        "💡 مثال:\n"
        "   • T-12345\n"
        "   • علی\n"
        "   • @username"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data="fb_admin_panel")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.message(FeedbackState.admin_searching, F.text)
async def process_admin_search(message: types.Message, state: FSMContext):
    """پردازش جستجوی ادمین"""
    
    if message.from_user.id not in settings.ADMIN_CHAT_IDS:
        await state.clear()
        return
    
    query = message.text.strip().lower()
    
    all_tickets = load_feedbacks()
    
    # جستجو
    results = []
    
    for ticket in all_tickets:
        # جستجو در شماره تیکت
        if query in ticket.get("id", "").lower():
            results.append(ticket)
            continue
        
        # جستجو در نام کاربر
        if query in ticket.get("full_name", "").lower():
            results.append(ticket)
            continue
        
        # جستجو در یوزرنیم
        if query.replace("@", "") in (ticket.get("username") or "").lower():
            results.append(ticket)
            continue
        
        # جستجو در متن پیام
        if query in ticket.get("message", "").lower():
            results.append(ticket)
            continue
    
    await state.clear()
    
    if not results:
        text = f"📭 نتیجه‌ای برای «{query}» یافت نشد!"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 جستجوی مجدد", callback_data="fb_admin_search")],
            [InlineKeyboardButton(text="🔙 پنل ادمین", callback_data="fb_admin_panel")]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        return
    
    # نمایش نتایج
    text = f"🔍 <b>نتایج جستجو برای «{query}»</b>\n\n"
    text += f"📊 {len(results)} نتیجه یافت شد:\n\n"
    
    buttons = []
    
    for ticket in results[:10]:  # حداکثر ۱۰ نتیجه
        status_info = TICKET_STATUS.get(ticket.get("status", "open"), {})
        
        text += f"{status_info.get('icon', '📩')} <b>{ticket['id']}</b> | {ticket.get('full_name', '؟')[:15]}\n"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{ticket['id']} | {ticket.get('full_name', '؟')[:15]}",
                callback_data=f"fb_view_{ticket['id']}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔍 جستجوی جدید", callback_data="fb_admin_search")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 پنل ادمین", callback_data="fb_admin_panel")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ───────────────────────────────────────────────────────────────────
# آمار تفصیلی
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "fb_admin_detailed_stats")
async def admin_detailed_stats(callback: types.CallbackQuery):
    """آمار تفصیلی تیکت‌ها"""
    
    if callback.from_user.id not in settings.ADMIN_CHAT_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    
    stats = get_ticket_stats()
    all_tickets = load_feedbacks()
    
    text = (
        "📊 <b>آمار تفصیلی تیکت‌ها</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    # آمار کلی
    text += "📈 <b>آمار کلی:</b>\n"
    text += f"   📦 کل: {stats['total']}\n"
    text += f"   📅 امروز: {stats['today']}\n\n"
    
    # آمار بر اساس وضعیت
    text += "📊 <b>بر اساس وضعیت:</b>\n"
    text += f"   🟢 باز: {stats['open']}\n"
    text += f"   🟡 در حال بررسی: {stats['in_progress']}\n"
    text += f"   ⏳ منتظر پاسخ: {stats['waiting']}\n"
    text += f"   ✅ حل شده: {stats['resolved']}\n"
    text += f"   🔒 بسته: {stats['closed']}\n\n"
    
    # آمار بر اساس نوع
    text += "📌 <b>بر اساس نوع:</b>\n"
    for type_key, count in stats.get("by_type", {}).items():
        type_info = TICKET_TYPES.get(type_key, {})
        text += f"   {type_info.get('icon', '📝')} {type_info.get('short', type_key)}: {count}\n"
    
    text += "\n"
    
    # آمار امتیاز
    if stats['rating_count'] > 0:
        text += "⭐ <b>امتیازات:</b>\n"
        text += f"   میانگین: {'⭐' * int(stats['avg_rating'])} ({stats['avg_rating']}/5)\n"
        text += f"   تعداد: {stats['rating_count']} نظر\n\n"
        
        # توزیع امتیازات
        ratings_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for t in all_tickets:
            r = t.get("user_rating")
            if r in ratings_dist:
                ratings_dist[r] += 1
        
        text += "   توزیع:\n"
        for score in range(5, 0, -1):
            bar_count = ratings_dist[score]
            bar = "█" * min(bar_count, 10)
            text += f"   {'⭐' * score}: {bar} ({bar_count})\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    # کاربران فعال
    user_ticket_count = {}
    for t in all_tickets:
        uid = t.get("user_id")
        if uid:
            user_ticket_count[uid] = user_ticket_count.get(uid, 0) + 1
    
    text += f"\n👥 <b>کاربران یکتا:</b> {len(user_ticket_count)}\n"
    
    # زمان متوسط پاسخ (ساده)
    responded_tickets = [t for t in all_tickets if t.get("conversation")]
    text += f"💬 <b>تیکت‌های پاسخ داده شده:</b> {len(responded_tickets)}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 پنل ادمین", callback_data="fb_admin_panel")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# بستن تیکت توسط ادمین با دلیل
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fb_admin_close_"))
async def admin_close_ticket(callback: types.CallbackQuery, state: FSMContext):
    """بستن تیکت توسط ادمین"""
    
    if callback.from_user.id not in settings.ADMIN_CHAT_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    
    ticket_id = callback.data.replace("fb_admin_close_", "")
    
    text = (
        f"🔒 <b>بستن تیکت {ticket_id}</b>\n\n"
        "دلیل بستن را انتخاب کنید:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ مشکل حل شد", callback_data=f"fb_close_reason_{ticket_id}_resolved")],
        [InlineKeyboardButton(text="⏰ عدم پاسخ کاربر", callback_data=f"fb_close_reason_{ticket_id}_no_response")],
        [InlineKeyboardButton(text="🔄 تکراری", callback_data=f"fb_close_reason_{ticket_id}_duplicate")],
        [InlineKeyboardButton(text="❌ نامربوط", callback_data=f"fb_close_reason_{ticket_id}_irrelevant")],
        [InlineKeyboardButton(text="🔙 انصراف", callback_data=f"fb_view_{ticket_id}")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("fb_close_reason_"))
async def admin_close_with_reason(callback: types.CallbackQuery):
    """بستن تیکت با دلیل"""
    
    if callback.from_user.id not in settings.ADMIN_CHAT_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    
    parts = callback.data.replace("fb_close_reason_", "").split("_")
    ticket_id = parts[0]
    reason = parts[1] if len(parts) > 1 else "resolved"
    
    reason_labels = {
        "resolved": "مشکل حل شد",
        "no_response": "عدم پاسخ کاربر",
        "duplicate": "تیکت تکراری",
        "irrelevant": "موضوع نامربوط"
    }
    
    ticket = get_ticket_by_id(ticket_id)
    
    if not ticket:
        await callback.answer("⚠️ تیکت یافت نشد!", show_alert=True)
        return
    
    # بروزرسانی
    update_ticket(ticket_id, {
        "status": "closed",
        "close_reason": reason,
        "closed_by": callback.from_user.id,
        "closed_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    
    # اطلاع به کاربر
    try:
        user_text = (
            f"🔒 <b>تیکت بسته شد</b>\n\n"
            f"🎫 تیکت: <code>{ticket_id}</code>\n"
            f"📝 دلیل: {reason_labels.get(reason, reason)}\n\n"
            "اگر همچنان مشکل دارید، تیکت جدید ثبت کنید."
        )
        
        user_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ تیکت جدید", callback_data="fb_new_ticket")]
        ])
        
        await callback.bot.send_message(
            ticket.get("user_id"),
            user_text,
            reply_markup=user_kb,
            parse_mode="HTML"
        )
    except:
        pass
    
    await callback.answer("✅ تیکت بسته شد!", show_alert=True)
    
    callback.data = "fb_admin_panel"
    await admin_panel(callback)


# ───────────────────────────────────────────────────────────────────
# هندل callback نادرست
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: types.CallbackQuery):
    """هندل دکمه‌های غیرفعال"""
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════
# پایان بخش ۳ و پایان فایل
# ═══════════════════════════════════════════════════════════════════
