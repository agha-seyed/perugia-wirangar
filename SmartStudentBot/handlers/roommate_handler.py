# handlers/roommate_handler.py
# سیستم کامل هم‌خانه و مسکن پروجا - نسخه نهایی
# بخش 1: تنظیمات، Constants، توابع کمکی، States

import json
import os
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from aiogram import Router, types, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    FSInputFile,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.exceptions import TelegramBadRequest

from config import settings, logger

try:
    from handlers.cmd_start import get_user_lang, get_text, get_user_lang_code
except ImportError:
    def get_user_lang(user_id: int) -> dict: return {}
    def get_text(lang: dict, key: str, default: str = "") -> str: return default
    def get_user_lang_code(user_id: int) -> str: return "fa"

router = Router()


# ═══════════════════════════════════════════════════════════════════
# تنظیمات و مسیرها
# ═══════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads" / "roommates"
DATA_DIR = BASE_DIR / "data"

# فایل‌های دیتابیس
ROOM_JSON = DATA_DIR / "roommates.json"
ALERTS_JSON = DATA_DIR / "room_alerts.json"
BOOKMARKS_JSON = DATA_DIR / "room_bookmarks.json"
RATINGS_JSON = DATA_DIR / "room_ratings.json"
MESSAGES_JSON = DATA_DIR / "room_messages.json"

# تنظیمات اصلی
ITEMS_PER_PAGE = 4
EXPIRATION_DAYS = 45
MAX_ADS_PER_USER = 3
MAX_PHOTOS = 5
MAX_DESC_LENGTH = 1000
MIN_BUDGET = 100
MAX_BUDGET = 2000

# ایجاد پوشه‌ها
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════
# لیست‌های ثابت (Constants)
# ═══════════════════════════════════════════════════════════════════

# امکانات
AMENITIES_LIST = {
    "wifi": "📶 وای‌فای",
    "washing": "🧺 لباسشویی",
    "dryer": "👕 خشک‌کن",
    "dishwasher": "🍽️ ماشین ظرفشویی",
    "ac": "❄️ کولر/تهویه",
    "heating": "🔥 شوفاژ/بخاری",
    "elevator": "🛗 آسانسور",
    "parking": "🚗 پارکینگ",
    "balcony": "☀️ بالکن/تراس",
    "garden": "🌳 حیاط/باغچه",
    "storage": "📦 انباری",
    "furnished": "🛋️ مبله",
    "bills": "💡 قبوض شامل",
    "gym": "🏋️ سالن ورزش",
    "pool": "🏊 استخر"
}

# مناطق پروجا
AREAS_LIST = {
    "centro": "📍 Centro Storico",
    "elce": "📍 Elce",
    "fontivegge": "📍 Fontivegge",
    "san_sisto": "📍 San Sisto",
    "madonna_alta": "📍 Madonna Alta",
    "monteluce": "📍 Monteluce",
    "ferro_cavallo": "📍 Ferro di Cavallo",
    "ponte_san_giovanni": "📍 Ponte San Giovanni",
    "pallotta": "📍 Pallotta",
    "elce_below": "📍 Elce پایین",
    "other": "📍 سایر مناطق"
}

# نوع آگهی
AD_TYPES = {
    "room": "🚪 اتاق در آپارتمان مشترک",
    "apartment": "🏠 کل آپارتمان",
    "studio": "🏢 استودیو",
    "seeking": "🔍 جستجوی هم‌خانه"
}

# نوع تخت
BED_TYPES = {
    "single": "🛏️ تخت یک‌نفره",
    "double": "🛏️ تخت دونفره",
    "sofa": "🛋️ مبل تختخواب‌شو",
    "bunk": "🛏️ تخت دوطبقه",
    "none": "❌ بدون تخت"
}

# وضعیت سیگار
SMOKING_OPTIONS = {
    "no": "🚭 ممنوع",
    "yes": "🚬 مجاز",
    "balcony": "🌬️ فقط در بالکن"
}

# وضعیت حیوانات
PETS_OPTIONS = {
    "no": "🚫 ندارم / ممنوع",
    "have": "🐕 دارم",
    "ok": "✅ مشکلی ندارم"
}

# حداقل اقامت
MIN_STAY_OPTIONS = {
    "1month": "1 ماه",
    "3month": "3 ماه",
    "6month": "6 ماه",
    "1year": "1 سال",
    "any": "مهم نیست"
}


# ═══════════════════════════════════════════════════════════════════
# توابع کمکی
# ═══════════════════════════════════════════════════════════════════

def safe_int(value: Any, default: int = 999999) -> int:
    """تبدیل امن به عدد صحیح"""
    try:
        clean = re.sub(r'\D', '', str(value))
        return int(clean) if clean else default
    except:
        return default


def truncate_text(text: str, max_length: int = 100) -> str:
    """کوتاه کردن متن با ... در انتها"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def get_sort_key(ad: dict) -> tuple:
    """کلید مرتب‌سازی آگهی‌ها (ویژه‌ها اول، بعد جدیدترین)"""
    is_premium = ad.get("is_premium", False)
    try:
        date_obj = datetime.strptime(ad["date"], "%Y-%m-%d")
    except:
        date_obj = datetime.min
    return (is_premium, date_obj)


def days_until_expiry(ad: dict) -> int:
    """محاسبه روزهای باقیمانده تا انقضا"""
    try:
        ad_date = datetime.strptime(ad["date"], "%Y-%m-%d")
        expiry_date = ad_date + timedelta(days=EXPIRATION_DAYS)
        remaining = (expiry_date - datetime.now()).days
        return max(0, remaining)
    except:
        return 0


def format_date_persian(date_str: str) -> str:
    """تبدیل تاریخ به فرمت خوانا"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%Y/%m/%d")
    except:
        return date_str


def get_gender_icon(gender: str) -> str:
    """آیکون جنسیت"""
    if gender == "آقا":
        return "👨"
    elif gender == "خانم":
        return "👩"
    else:
        return "👫"


async def load_json(path_name: str) -> list:
    """بارگذاری داده از دیتابیس با پشتیبانی از کالکشن‌های اختصاصی"""
    try:
        from database import db_manager
        if path_name == "roommates" and db_manager.roommates is not None:
            ads = await db_manager.get_active_roommate_ads(limit=200)
            if ads:
                return ads
        if db_manager.db is not None:
            doc = await db_manager.db["json_store"].find_one({"name": path_name}, {"_id": 0})
            if doc and "data" in doc:
                return doc["data"]
    except Exception as e:
        logger.error(f"Error loading {path_name}: {e}")
    return []


async def save_json(path_name: str, data: list) -> bool:
    """ذخیره داده در دیتابیس"""
    try:
        from database import db_manager
        if path_name == "roommates":
            for ad in data:
                await db_manager.save_roommate_ad(ad)
        if db_manager.db is not None:
            await db_manager.db["json_store"].update_one(
                {"name": path_name},
                {"$set": {"data": data}},
                upsert=True
            )
            return True
        return False
    except Exception as e:
        logger.error(f"Error saving {path_name}: {e}")
        return False


async def load_roommates() -> list:
    """بارگذاری آگهی‌ها با بررسی انقضا و مقداردهی پیش‌فرض"""
    data = await load_json("roommates")
    updated = False
    today = datetime.now()
    
    for ad in data:
        # مقداردهی پیش‌فرض فیلدها
        ad.setdefault("status", "approved")
        ad.setdefault("active", True)
        ad.setdefault("is_found", False)
        ad.setdefault("is_premium", False)
        ad.setdefault("views", 0)
        ad.setdefault("contacts", 0)
        ad.setdefault("ad_type", "room")
        ad.setdefault("house_size", "نامشخص")
        ad.setdefault("bed_type", "نامشخص")
        ad.setdefault("room_count", "1")
        ad.setdefault("available_from", "فوری")
        ad.setdefault("min_stay", "نامشخص")
        ad.setdefault("smoking", "نامشخص")
        ad.setdefault("pets", "نامشخص")
        ad.setdefault("amenities", [])
        ad.setdefault("photos", [])
        ad.setdefault("coordinates", None)
        ad.setdefault("reports", [])
        ad.setdefault("renewal_count", 0)
        ad.setdefault("area_key", "other")
        
        # بررسی انقضا
        if ad["status"] == "approved" and ad["active"] and not ad.get("is_found"):
            try:
                ad_date = datetime.strptime(ad["date"], "%Y-%m-%d")
                if (today - ad_date).days > EXPIRATION_DAYS:
                    ad["active"] = False
                    ad["expired"] = True
                    updated = True
            except:
                pass
    
    if updated:
        await save_json("roommates", data)
    
    return data


async def get_user_stats(user_id: int) -> dict:
    """آمار کاربر"""
    all_ads = await load_roommates()
    user_ads = [ad for ad in all_ads if ad.get("user_id") == user_id]
    
    # محاسبه امتیاز
    ratings = await load_json("room_ratings")
    user_ratings = [r for r in ratings if r.get("to_user") == user_id]
    avg_rating = 0
    if user_ratings:
        avg_rating = sum(r.get("score", 0) for r in user_ratings) / len(user_ratings)
    
    return {
        "total_ads": len(user_ads),
        "active_ads": sum(1 for a in user_ads if a.get("active") and a.get("status") == "approved"),
        "pending_ads": sum(1 for a in user_ads if a.get("status") == "pending"),
        "found_count": sum(1 for a in user_ads if a.get("is_found")),
        "expired_count": sum(1 for a in user_ads if a.get("expired")),
        "total_views": sum(a.get("views", 0) for a in user_ads),
        "total_contacts": sum(a.get("contacts", 0) for a in user_ads),
        "avg_rating": round(avg_rating, 1),
        "rating_count": len(user_ratings)
    }


async def get_active_ads_count() -> int:
    """تعداد آگهی‌های فعال"""
    all_ads = await load_roommates()
    return sum(
        1 for a in all_ads 
        if a.get("active") 
        and a.get("status") == "approved" 
        and not a.get("is_found")
    )


async def safe_edit_message(
    message: types.Message,
    text: str,
    reply_markup: InlineKeyboardMarkup = None,
    parse_mode: str = "HTML"
) -> types.Message:
    """ویرایش امن پیام با هندل کردن خطاها"""
    try:
        if message.content_type == types.ContentType.PHOTO:
            await message.delete()
            return await message.answer(
                text, 
                reply_markup=reply_markup, 
                parse_mode=parse_mode
            )
        else:
            return await message.edit_text(
                text, 
                reply_markup=reply_markup, 
                parse_mode=parse_mode
            )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            try:
                return await message.answer(
                    text, 
                    reply_markup=reply_markup, 
                    parse_mode=parse_mode
                )
            except:
                pass
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        try:
            return await message.answer(
                text, 
                reply_markup=reply_markup, 
                parse_mode=parse_mode
            )
        except:
            pass
    return message


async def notify_admins(bot: Bot, text: str, keyboard: InlineKeyboardMarkup = None, photo_path: str = None):
    """ارسال نوتیفیکیشن به ادمین‌ها"""
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
# States (حالت‌های FSM)
# ═══════════════════════════════════════════════════════════════════

class RoommateState(StatesGroup):
    """حالت‌های مختلف سیستم هم‌خانه"""
    
    # ═══ فیلتر و جستجو ═══
    filter_type = State()
    filter_gender = State()
    filter_budget = State()
    filter_area = State()
    filter_amenities = State()
    search_keyword = State()
    
    # ═══ ثبت آگهی ═══
    waiting_ad_type = State()
    waiting_name = State()
    waiting_age = State()
    waiting_gender = State()
    waiting_budget = State()
    waiting_area = State()
    waiting_area_custom = State()
    waiting_house_size = State()
    waiting_room_count = State()
    waiting_bed_type = State()
    waiting_available_from = State()
    waiting_available_custom = State()
    waiting_min_stay = State()
    waiting_smoking = State()
    waiting_pets = State()
    waiting_amenities = State()
    waiting_photos = State()
    waiting_desc = State()
    waiting_coordinates = State()
    confirm_submit = State()
    
    # ═══ ویرایش ═══
    editing_select_field = State()
    editing_new_value = State()
    
    # ═══ هشدار ═══
    alert_gender = State()
    alert_budget = State()
    alert_area = State()
    alert_confirm = State()
    
    # ═══ گزارش ═══
    reporting_reason = State()
    
    # ═══ پیام ═══
    sending_message = State()
    
    # ═══ امتیاز ═══
    rating_score = State()
    rating_comment = State()


# ═══════════════════════════════════════════════════════════════════
# پایان بخش 1
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# بخش 2: منوی اصلی، مشاهده لیست آگهی‌ها، فیلتر
# ═══════════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────────
# هندلر دکمه‌های غیرفعال
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: types.CallbackQuery):
    """هندل کردن دکمه‌های غیرفعال (مثل شماره صفحه)"""
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# منوی اصلی هم‌خانه
# ───────────────────────────────────────────────────────────────────

@router.message(Command("roommate"))
@router.callback_query(F.data == "roommate")
async def roommate_main_menu(event: types.Message | types.CallbackQuery, state: FSMContext):
    """منوی اصلی سیستم هم‌خانه و مسکن"""
    
    # پاک کردن state قبلی
    await state.clear()
    
    user_id = event.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    # آمار
    active_count = await get_active_ads_count()
    user_stats = await get_user_stats(user_id)
    
    if lang_code == "en":
        text = (
            "🏠 <b>Perugia Housing & Roommate Finder</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>System Overview:</b>\n"
            f"   🏠 Active Listings: <b>{active_count}</b>\n"
        )
        if user_stats["total_ads"] > 0:
            text += f"\n👤 <b>Your Ads:</b>\n"
            text += f"   ✅ Active: {user_stats['active_ads']}\n"
            if user_stats["pending_ads"] > 0:
                text += f"   ⏳ Under Review: {user_stats['pending_ads']}\n"
            if user_stats["found_count"] > 0:
                text += f"   🎉 Found/Closed: {user_stats['found_count']}\n"
            text += f"   👁 Total Views: {user_stats['total_views']}\n"
        
        if user_stats["avg_rating"] > 0:
            stars = "⭐" * int(user_stats["avg_rating"])
            text += f"\n⭐ <b>Your Rating:</b> {stars} ({user_stats['avg_rating']}/5)\n"
            
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "👇 Select an option:"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🔍 Browse Listings ({active_count} active)", 
                    callback_data="room_browse_1"
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Post New Listing (Roommate / Room / Flat)", 
                    callback_data="room_add_start"
                )
            ],
            [
                InlineKeyboardButton(text="🎯 Advanced Filters", callback_data="room_filter_menu"),
                InlineKeyboardButton(text="🔎 Keyword Search", callback_data="room_search_start")
            ],
            [
                InlineKeyboardButton(text="👤 My Listings", callback_data="room_my_ads"),
                InlineKeyboardButton(text="🔖 Bookmarks", callback_data="room_bookmarks")
            ],
            [
                InlineKeyboardButton(text="🤖 Smart AI Match", callback_data="ai_matchmaker"),
                InlineKeyboardButton(text="🔔 Listing Alerts", callback_data="room_alert_menu")
            ],
            [
                InlineKeyboardButton(text="💬 Messages", callback_data="room_messages"),
                InlineKeyboardButton(text="❓ Help & Rules", callback_data="room_help")
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Return to Main Menu", 
                    callback_data="main_menu"
                )
            ]
        ])
    elif lang_code == "it":
        text = (
            "🏠 <b>Alloggi e Coinquilini a Perugia</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>Panoramica del Sistema:</b>\n"
            f"   🏠 Annunci attivi: <b>{active_count}</b>\n"
        )
        if user_stats["total_ads"] > 0:
            text += f"\n👤 <b>I tuoi annunci:</b>\n"
            text += f"   ✅ Attivi: {user_stats['active_ads']}\n"
            if user_stats["pending_ads"] > 0:
                text += f"   ⏳ In attesa: {user_stats['pending_ads']}\n"
            if user_stats["found_count"] > 0:
                text += f"   🎉 Conclusi: {user_stats['found_count']}\n"
            text += f"   👁 Visualizzazioni: {user_stats['total_views']}\n"
            
        if user_stats["avg_rating"] > 0:
            stars = "⭐" * int(user_stats["avg_rating"])
            text += f"\n⭐ <b>Tua valutazione:</b> {stars} ({user_stats['avg_rating']}/5)\n"
            
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "👇 Scegli un'opzione:"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🔍 Sfoglia Annunci ({active_count} attivi)", 
                    callback_data="room_browse_1"
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Inserisci Annuncio (Coinquilino / Stanza)", 
                    callback_data="room_add_start"
                )
            ],
            [
                InlineKeyboardButton(text="🎯 Filtri Avanzati", callback_data="room_filter_menu"),
                InlineKeyboardButton(text="🔎 Ricerca Testuale", callback_data="room_search_start")
            ],
            [
                InlineKeyboardButton(text="👤 I Miei Annunci", callback_data="room_my_ads"),
                InlineKeyboardButton(text="🔖 Salvati", callback_data="room_bookmarks")
            ],
            [
                InlineKeyboardButton(text="🤖 Matchmaking IA", callback_data="ai_matchmaker"),
                InlineKeyboardButton(text="🔔 Avvisi Annunci", callback_data="room_alert_menu")
            ],
            [
                InlineKeyboardButton(text="💬 Messaggi", callback_data="room_messages"),
                InlineKeyboardButton(text="❓ Guida e Regole", callback_data="room_help")
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Torna al Menu Principale", 
                    callback_data="main_menu"
                )
            ]
        ])
    else:
        # ساخت متن فارسی
        text = (
            "🏠 <b>سامانه هم‌خانه و مسکن پروجا</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        
        # آمار سیستم
        text += f"📊 <b>وضعیت سیستم:</b>\n"
        text += f"   🏠 آگهی‌های فعال: <b>{active_count}</b>\n"
        
        # آمار کاربر
        if user_stats["total_ads"] > 0:
            text += f"\n👤 <b>آگهی‌های شما:</b>\n"
            text += f"   ✅ فعال: {user_stats['active_ads']}\n"
            if user_stats["pending_ads"] > 0:
                text += f"   ⏳ در انتظار تأیید: {user_stats['pending_ads']}\n"
            if user_stats["found_count"] > 0:
                text += f"   🎉 موفق: {user_stats['found_count']}\n"
            text += f"   👁 بازدید کل: {user_stats['total_views']}\n"
        
        # امتیاز کاربر
        if user_stats["avg_rating"] > 0:
            stars = "⭐" * int(user_stats["avg_rating"])
            text += f"\n⭐ <b>امتیاز شما:</b> {stars} ({user_stats['avg_rating']}/5)\n"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "👇 انتخاب کنید:"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🔍 جستجو و مشاهده آگهی‌ها ({active_count} آگهی فعال)", 
                    callback_data="room_browse_1"
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ ثبت آگهی جدید (هم‌خانه / اتاق / خانه)", 
                    callback_data="room_add_start"
                )
            ],
            [
                InlineKeyboardButton(text="🎯 فیلتر پیشرفته", callback_data="room_filter_menu"),
                InlineKeyboardButton(text="🔎 جستجوی متنی", callback_data="room_search_start")
            ],
            [
                InlineKeyboardButton(text="👤 آگهی‌های من", callback_data="room_my_ads"),
                InlineKeyboardButton(text="🔖 نشان‌شده‌ها", callback_data="room_bookmarks")
            ],
            [
                InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker"),
                InlineKeyboardButton(text="🔔 تنظیم هشدار آگهی", callback_data="room_alert_menu")
            ],
            [
                InlineKeyboardButton(text="💬 پیام‌ها", callback_data="room_messages"),
                InlineKeyboardButton(text="❓ راهنما و قوانین", callback_data="room_help")
            ],
            [
                InlineKeyboardButton(
                    text="🏠 بازگشت به منوی اصلی", 
                    callback_data="main_menu"
                )
            ]
        ])
    
    if isinstance(event, types.CallbackQuery):
        await safe_edit_message(event.message, text, keyboard)
        await event.answer()
    else:
        await event.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ───────────────────────────────────────────────────────────────────
# راهنمای سیستم
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_help")
async def show_help(callback: types.CallbackQuery):
    """نمایش راهنمای سیستم"""
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    if lang_code == "en":
        text = (
            "❓ <b>Housing & Roommate Guide</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📋 <b>Browse Listings:</b>\n"
            "   Explore all verified student ads in Perugia\n\n"
            "🔍 <b>Advanced Filters:</b>\n"
            "   Filter by budget, room type, gender, and amenities\n\n"
            "🔎 <b>Keyword Search:</b>\n"
            "   Search titles and descriptions by keywords\n\n"
            "📝 <b>Post an Ad:</b>\n"
            f"   Up to {MAX_ADS_PER_USER} active listings per student\n"
            f"   Each listing stays live for {EXPIRATION_DAYS} days\n\n"
            "🔔 <b>Smart Alerts:</b>\n"
            "   Get notified instantly when matching rooms appear\n\n"
            "🔖 <b>Bookmarks:</b>\n"
            "   Save listings to review later\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 <b>Tips & Rules:</b>\n"
            "   • Always request a registered rental contract\n"
            "   • Check advertiser profile and ratings before paying\n"
            "   • Report suspicious ads immediately"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Smart AI Match", callback_data="ai_matchmaker")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="roommate")]
        ])
    elif lang_code == "it":
        text = (
            "❓ <b>Guida per Alloggi e Coinquilini</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📋 <b>Esplora Annunci:</b>\n"
            "   Consulta tutti gli annunci verificati a Perugia\n\n"
            "🔍 <b>Filtri Avanzati:</b>\n"
            "   Filtra per budget, tipologia, genere e servizi\n\n"
            "🔎 <b>Ricerca Testuale:</b>\n"
            "   Cerca per parole chiave nel testo degli annunci\n\n"
            "📝 <b>Pubblica un Annuncio:</b>\n"
            f"   Fino a {MAX_ADS_PER_USER} annunci attivi contemporaneamente\n"
            f"   Ogni annuncio dura {EXPIRATION_DAYS} giorni\n\n"
            "🔔 <b>Avvisi Notifiche:</b>\n"
            "   Ricevi notifiche istantanee per nuovi annunci compatibili\n\n"
            "🔖 <b>Salvati:</b>\n"
            "   Salva gli annunci preferiti\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 <b>Consigli e Regole:</b>\n"
            "   • Richiedi sempre un regolare contratto registrato\n"
            "   • Verifica il profilo dell'utente prima di versare caparre\n"
            "   • Segnala tempestivamente gli annunci sospetti"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Matchmaking IA", callback_data="ai_matchmaker")],
            [InlineKeyboardButton(text="🔙 Indietro", callback_data="roommate")]
        ])
    else:
        text = (
            "❓ <b>راهنمای سیستم هم‌خانه</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "📋 <b>مشاهده آگهی‌ها:</b>\n"
            "   لیست همه آگهی‌های فعال را ببینید\n\n"
            
            "🔍 <b>فیلتر پیشرفته:</b>\n"
            "   بر اساس جنسیت، بودجه، منطقه و امکانات فیلتر کنید\n\n"
            
            "🔎 <b>جستجوی متنی:</b>\n"
            "   با کلمه کلیدی در توضیحات جستجو کنید\n\n"
            
            "📝 <b>ثبت آگهی:</b>\n"
            f"   حداکثر {MAX_ADS_PER_USER} آگهی فعال\n"
            f"   هر آگهی {EXPIRATION_DAYS} روز فعال می‌ماند\n\n"
            
            "🔔 <b>هشدار:</b>\n"
            "   وقتی آگهی مناسب ثبت شد، پیام بگیرید\n\n"
            
            "🔖 <b>ذخیره آگهی:</b>\n"
            "   آگهی‌های مورد علاقه را ذخیره کنید\n\n"
            
            "⭐ <b>امتیازدهی:</b>\n"
            "   به آگهی‌دهنده‌ها امتیاز دهید\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 <b>نکات مهم:</b>\n"
            "   • آگهی‌های ویژه 🌟 بالاتر نمایش داده می‌شوند\n"
            "   • قبل از تماس، پروفایل را بررسی کنید\n"
            "   • مشکلات را گزارش دهید"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="roommate")]
        ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# آمار کلی سیستم
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_stats")
async def show_stats(callback: types.CallbackQuery):
    """نمایش آمار کلی سیستم"""
    
    all_ads = await load_roommates()
    
    total = len(all_ads)
    active = sum(1 for a in all_ads if a.get("active") and a.get("status") == "approved" and not a.get("is_found"))
    pending = sum(1 for a in all_ads if a.get("status") == "pending")
    found = sum(1 for a in all_ads if a.get("is_found"))
    expired = sum(1 for a in all_ads if a.get("expired"))
    premium = sum(1 for a in all_ads if a.get("is_premium") and a.get("active"))
    
    # آمار بر اساس منطقه
    area_stats = {}
    for ad in all_ads:
        if ad.get("active") and ad.get("status") == "approved":
            area = ad.get("area", "سایر")
            area_stats[area] = area_stats.get(area, 0) + 1
    
    # آمار بر اساس قیمت
    budget_ranges = {"< 300": 0, "300-400": 0, "400-500": 0, "500+": 0}
    for ad in all_ads:
        if ad.get("active") and ad.get("status") == "approved":
            budget = safe_int(ad.get("budget", 0), 0)
            if budget < 300:
                budget_ranges["< 300"] += 1
            elif budget < 400:
                budget_ranges["300-400"] += 1
            elif budget < 500:
                budget_ranges["400-500"] += 1
            else:
                budget_ranges["500+"] += 1
    
    text = (
        "📊 <b>آمار سیستم هم‌خانه</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        f"📦 <b>کل آگهی‌ها:</b> {total}\n"
        f"   ✅ فعال: {active}\n"
        f"   ⏳ در انتظار: {pending}\n"
        f"   🎉 موفق (پیدا شده): {found}\n"
        f"   ⌛ منقضی: {expired}\n"
        f"   🌟 ویژه: {premium}\n\n"
        
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💰 <b>بر اساس قیمت:</b>\n"
    )
    
    for range_name, count in budget_ranges.items():
        if count > 0:
            text += f"   {range_name}€: {count} آگهی\n"
    
    if area_stats:
        text += "\n📍 <b>بر اساس منطقه:</b>\n"
        sorted_areas = sorted(area_stats.items(), key=lambda x: x[1], reverse=True)[:5]
        for area, count in sorted_areas:
            text += f"   {area}: {count}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="roommate")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# مشاهده لیست آگهی‌ها (Browse)
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("room_browse_"))
async def browse_ads(callback: types.CallbackQuery, state: FSMContext):
    """نمایش لیست آگهی‌ها با صفحه‌بندی"""
    
    # استخراج شماره صفحه
    page = int(callback.data.split("_")[-1])
    
    # دریافت فیلترها از state
    data = await state.get_data()
    f_type = data.get("filter_type", "all")
    f_gender = data.get("filter_gender", "all")
    f_budget = data.get("filter_budget", "all")
    f_area = data.get("filter_area", "all")
    f_amenities = data.get("filter_amenities", [])
    keyword = data.get("search_keyword", "")
    
    # بارگذاری آگهی‌ها
    all_ads = await load_roommates()
    
    # فیلتر اولیه: فعال، تأیید شده، پیدا نشده
    ads = [
        ad for ad in all_ads
        if ad.get("status") == "approved"
        and ad.get("active", True)
        and not ad.get("is_found", False)
    ]
    
    # ═══ اعمال فیلترها ═══
    
    # فیلتر نوع آگهی
    if f_type != "all":
        ads = [ad for ad in ads if ad.get("ad_type") == f_type]
    
    # فیلتر جنسیت
    if f_gender != "all":
        ads = [ad for ad in ads if ad.get("gender") == f_gender or ad.get("gender") == "فرقی ندارد"]
    
    # فیلتر بودجه
    if f_budget != "all":
        limit = int(f_budget)
        ads = [ad for ad in ads if safe_int(ad.get("budget", 0)) <= limit]
    
    # فیلتر منطقه
    if f_area != "all":
        ads = [ad for ad in ads if ad.get("area_key") == f_area]
    
    # فیلتر امکانات
    if f_amenities:
        ads = [
            ad for ad in ads
            if all(am in ad.get("amenities", []) for am in f_amenities)
        ]
    
    # جستجوی متنی
    if keyword:
        keyword_lower = keyword.lower()
        ads = [
            ad for ad in ads
            if keyword_lower in ad.get("desc", "").lower()
            or keyword_lower in ad.get("name", "").lower()
            or keyword_lower in ad.get("area", "").lower()
        ]
    
    # مرتب‌سازی (ویژه‌ها اول، بعد جدیدترین)
    ads.sort(key=get_sort_key, reverse=True)
    
    # محاسبات صفحه‌بندی
    total_ads = len(ads)
    total_pages = max(1, math.ceil(total_ads / ITEMS_PER_PAGE))
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_ads = ads[start_idx:end_idx]
    
    # ═══ ساخت متن ═══
    
    if total_ads == 0:
        # هیچ آگهی یافت نشد
        text = "📭 <b>هیچ آگهی یافت نشد!</b>\n\n"
        
        has_filter = any([
            f_type != "all",
            f_gender != "all", 
            f_budget != "all",
            f_area != "all",
            f_amenities,
            keyword
        ])
        
        if has_filter:
            text += "💡 فیلترهای خود را تغییر دهید یا پاک کنید."
        else:
            text += "💡 اولین نفر باشید که آگهی ثبت می‌کند!"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
            [InlineKeyboardButton(text="🔄 پاک کردن فیلترها", callback_data="room_clear_filters")],
            [InlineKeyboardButton(text="📝 ثبت آگهی", callback_data="room_add_start")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="roommate")]
        ])
        
        await safe_edit_message(callback.message, text, keyboard)
        await callback.answer()
        return
    
    # هدر لیست
    text = f"🏠 <b>آگهی‌های مسکن</b>\n"
    text += f"📄 صفحه {page} از {total_pages} | مجموع: {total_ads}\n"
    
    # نمایش فیلترهای فعال
    active_filters = []
    if f_type != "all":
        active_filters.append(AD_TYPES.get(f_type, f_type)[:10])
    if f_gender != "all":
        active_filters.append(f_gender)
    if f_budget != "all":
        active_filters.append(f"≤{f_budget}€")
    if f_area != "all":
        active_filters.append(AREAS_LIST.get(f_area, "").replace("📍 ", "")[:8])
    if keyword:
        active_filters.append(f'"{keyword[:10]}"')
    
    if active_filters:
        text += f"🔹 فیلتر: {' | '.join(active_filters)}\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # لیست آگهی‌ها
    for i, ad in enumerate(current_ads, 1):
        premium = "🌟 " if ad.get("is_premium") else ""
        gender_icon = get_gender_icon(ad.get("gender", ""))
        days_left = days_until_expiry(ad)
        
        text += f"{premium}<b>{i}. {ad.get('area', 'نامشخص')}</b>\n"
        text += f"   {gender_icon} {ad.get('budget', '?')}€"
        text += f" | 🏠 {ad.get('house_size', '?')}m²"
        text += f" | 🛏 {ad.get('room_count', '?')}\n"
        text += f"   👁 {ad.get('views', 0)} بازدید"
        text += f" | ⏳ {days_left} روز\n\n"
    
    # ═══ ساخت کیبورد ═══
    
    keyboard_rows = []
    
    # دکمه‌های آگهی (گرید 2x2)
    pairs = [current_ads[i:i+2] for i in range(0, len(current_ads), 2)]
    for pair in pairs:
        row = []
        for ad in pair:
            prefix = "🌟" if ad.get("is_premium") else "🏠"
            gender_icon = get_gender_icon(ad.get("gender", ""))
            area_short = truncate_text(ad.get("area", ""), 8)
            btn_text = f"{prefix}{gender_icon} {ad.get('budget', '?')}€ {area_short}"
            
            row.append(
                InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"room_view_{ad['id']}_{page}"
                )
            )
        keyboard_rows.append(row)
    
    # دکمه‌های ناوبری
    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(text="⬅️ قبلی", callback_data=f"room_browse_{page-1}")
        )
    nav_row.append(
        InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="ignore")
    )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(text="بعدی ➡️", callback_data=f"room_browse_{page+1}")
        )
    keyboard_rows.append(nav_row)
    
    # دکمه‌های فیلتر
    keyboard_rows.append([
        InlineKeyboardButton(text="🔍 فیلتر", callback_data="room_filter_menu"),
        InlineKeyboardButton(text="🔄 پاک کردن", callback_data="room_clear_filters")
    ])
    
    # دکمه بازگشت
    keyboard_rows.append([
        InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="roommate")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# پاک کردن فیلترها
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_clear_filters")
async def clear_filters(callback: types.CallbackQuery, state: FSMContext):
    """پاک کردن همه فیلترها"""
    
    await state.update_data(
        filter_type="all",
        filter_gender="all",
        filter_budget="all",
        filter_area="all",
        filter_amenities=[],
        search_keyword=""
    )
    
    await callback.answer("✅ فیلترها پاک شد!")
    
    # نمایش لیست بدون فیلتر
    callback.data = "room_browse_1"
    await browse_ads(callback, state)


# ───────────────────────────────────────────────────────────────────
# منوی فیلتر
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_filter_menu")
async def filter_menu(callback: types.CallbackQuery, state: FSMContext):
    """منوی فیلتر پیشرفته"""
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    data = await state.get_data()
    
    # نمایش فیلترهای فعلی
    current = []
    
    if data.get("filter_type", "all") != "all":
        current.append(f"📋 نوع: {AD_TYPES.get(data['filter_type'], '?')}")
    
    if data.get("filter_gender", "all") != "all":
        current.append(f"👤 جنسیت: {data['filter_gender']}")
    
    if data.get("filter_budget", "all") != "all":
        current.append(f"💰 بودجه: ≤{data['filter_budget']}€")
    
    if data.get("filter_area", "all") != "all":
        area_name = AREAS_LIST.get(data["filter_area"], "").replace("📍 ", "")
        current.append(f"📍 منطقه: {area_name}")
    
    if data.get("filter_amenities"):
        am_count = len(data["filter_amenities"])
        current.append(f"✨ امکانات: {am_count} مورد")
    
    if lang_code == "en":
        text = "🔍 <b>Advanced Filters</b>\n\nSelect your filter criteria:\n\n"
        if current:
            text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n<b>Active Filters:</b>\n"
            for f in current:
                text += f"   ✓ {f}\n"
            text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Smart AI Match", callback_data="ai_matchmaker")],
            [InlineKeyboardButton(text="📋 Property Type", callback_data="room_flt_type")],
            [InlineKeyboardButton(text="👤 Gender Preference", callback_data="room_flt_gender")],
            [InlineKeyboardButton(text="💰 Max Budget", callback_data="room_flt_budget")],
            [InlineKeyboardButton(text="📍 Neighborhood", callback_data="room_flt_area")],
            [InlineKeyboardButton(text="✨ Amenities", callback_data="room_flt_amenities")],
            [
                InlineKeyboardButton(text="✅ Apply Filters", callback_data="room_browse_1"),
                InlineKeyboardButton(text="🔄 Reset", callback_data="room_clear_filters")
            ],
            [InlineKeyboardButton(text="🔙 Back", callback_data="roommate")]
        ])
    elif lang_code == "it":
        text = "🔍 <b>Filtri Avanzati</b>\n\nSeleziona i criteri desiderati:\n\n"
        if current:
            text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n<b>Filtri Attivi:</b>\n"
            for f in current:
                text += f"   ✓ {f}\n"
            text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Matchmaking IA", callback_data="ai_matchmaker")],
            [InlineKeyboardButton(text="📋 Tipologia Alloggio", callback_data="room_flt_type")],
            [InlineKeyboardButton(text="👤 Preferenza Genere", callback_data="room_flt_gender")],
            [InlineKeyboardButton(text="💰 Budget Massimo", callback_data="room_flt_budget")],
            [InlineKeyboardButton(text="📍 Zona / Quartiere", callback_data="room_flt_area")],
            [InlineKeyboardButton(text="✨ Servizi Inclusi", callback_data="room_flt_amenities")],
            [
                InlineKeyboardButton(text="✅ Applica Filtri", callback_data="room_browse_1"),
                InlineKeyboardButton(text="🔄 Reimposta", callback_data="room_clear_filters")
            ],
            [InlineKeyboardButton(text="🔙 Indietro", callback_data="roommate")]
        ])
    else:
        text = "🔍 <b>فیلتر پیشرفته</b>\n\n"
        text += "فیلترهای مورد نظر را انتخاب کنید:\n\n"
        if current:
            text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            text += "<b>فیلترهای فعال:</b>\n"
            for f in current:
                text += f"   ✓ {f}\n"
            text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
            [InlineKeyboardButton(text="📋 نوع آگهی", callback_data="room_flt_type")],
            [InlineKeyboardButton(text="👤 جنسیت", callback_data="room_flt_gender")],
            [InlineKeyboardButton(text="💰 سقف بودجه", callback_data="room_flt_budget")],
            [InlineKeyboardButton(text="📍 منطقه", callback_data="room_flt_area")],
            [InlineKeyboardButton(text="✨ امکانات", callback_data="room_flt_amenities")],
            [
                InlineKeyboardButton(text="✅ اعمال فیلتر", callback_data="room_browse_1"),
                InlineKeyboardButton(text="🔄 پاک کردن", callback_data="room_clear_filters")
            ],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="roommate")]
        ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# فیلتر نوع آگهی
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_flt_type")
async def filter_type_menu(callback: types.CallbackQuery, state: FSMContext):
    """انتخاب نوع آگهی"""
    
    text = "📋 <b>نوع آگهی:</b>\n\nیکی را انتخاب کنید:"
    
    buttons = []
    for key, label in AD_TYPES.items():
        buttons.append([
            InlineKeyboardButton(text=label, callback_data=f"room_flt_type_{key}")
        ])
    
    buttons.append([
        InlineKeyboardButton(text="📋 همه انواع", callback_data="room_flt_type_all")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="room_filter_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("room_flt_type_"))
async def filter_type_selected(callback: types.CallbackQuery, state: FSMContext):
    """ذخیره فیلتر نوع"""
    
    ad_type = callback.data.replace("room_flt_type_", "")
    await state.update_data(filter_type=ad_type)
    
    await callback.answer("✅ ذخیره شد")
    
    # بازگشت به منوی فیلتر
    callback.data = "room_filter_menu"
    await filter_menu(callback, state)


# ───────────────────────────────────────────────────────────────────
# فیلتر جنسیت
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_flt_gender")
async def filter_gender_menu(callback: types.CallbackQuery, state: FSMContext):
    """انتخاب جنسیت"""
    
    text = "👤 <b>جنسیت مورد نظر:</b>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [
            InlineKeyboardButton(text="👨 آقایان", callback_data="room_flt_gender_آقا"),
            InlineKeyboardButton(text="👩 خانم‌ها", callback_data="room_flt_gender_خانم")
        ],
        [InlineKeyboardButton(text="👫 هر دو", callback_data="room_flt_gender_all")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="room_filter_menu")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("room_flt_gender_"))
async def filter_gender_selected(callback: types.CallbackQuery, state: FSMContext):
    """ذخیره فیلتر جنسیت"""
    
    gender = callback.data.replace("room_flt_gender_", "")
    await state.update_data(filter_gender=gender)
    
    await callback.answer("✅ ذخیره شد")
    
    callback.data = "room_filter_menu"
    await filter_menu(callback, state)


# ───────────────────────────────────────────────────────────────────
# فیلتر بودجه
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_flt_budget")
async def filter_budget_menu(callback: types.CallbackQuery, state: FSMContext):
    """انتخاب سقف بودجه"""
    
    text = "💰 <b>سقف بودجه ماهانه:</b>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [
            InlineKeyboardButton(text="≤ 300€", callback_data="room_flt_budget_300"),
            InlineKeyboardButton(text="≤ 350€", callback_data="room_flt_budget_350")
        ],
        [
            InlineKeyboardButton(text="≤ 400€", callback_data="room_flt_budget_400"),
            InlineKeyboardButton(text="≤ 450€", callback_data="room_flt_budget_450")
        ],
        [
            InlineKeyboardButton(text="≤ 500€", callback_data="room_flt_budget_500"),
            InlineKeyboardButton(text="≤ 600€", callback_data="room_flt_budget_600")
        ],
        [
            InlineKeyboardButton(text="≤ 800€", callback_data="room_flt_budget_800"),
            InlineKeyboardButton(text="∞ بدون محدودیت", callback_data="room_flt_budget_all")
        ],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="room_filter_menu")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("room_flt_budget_"))
async def filter_budget_selected(callback: types.CallbackQuery, state: FSMContext):
    """ذخیره فیلتر بودجه"""
    
    budget = callback.data.replace("room_flt_budget_", "")
    await state.update_data(filter_budget=budget)
    
    await callback.answer("✅ ذخیره شد")
    
    callback.data = "room_filter_menu"
    await filter_menu(callback, state)


# ───────────────────────────────────────────────────────────────────
# فیلتر منطقه
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_flt_area")
async def filter_area_menu(callback: types.CallbackQuery, state: FSMContext):
    """انتخاب منطقه"""
    
    text = "📍 <b>منطقه مورد نظر:</b>"
    
    buttons = []
    row = []
    
    for i, (key, label) in enumerate(AREAS_LIST.items()):
        short_label = label.replace("📍 ", "")
        row.append(
            InlineKeyboardButton(text=short_label, callback_data=f"room_flt_area_{key}")
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton(text="🗺️ همه مناطق", callback_data="room_flt_area_all")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="room_filter_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("room_flt_area_"))
async def filter_area_selected(callback: types.CallbackQuery, state: FSMContext):
    """ذخیره فیلتر منطقه"""
    
    area = callback.data.replace("room_flt_area_", "")
    await state.update_data(filter_area=area)
    
    await callback.answer("✅ ذخیره شد")
    
    callback.data = "room_filter_menu"
    await filter_menu(callback, state)


# ───────────────────────────────────────────────────────────────────
# فیلتر امکانات
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_flt_amenities")
async def filter_amenities_menu(callback: types.CallbackQuery, state: FSMContext):
    """انتخاب امکانات"""
    
    data = await state.get_data()
    selected = data.get("filter_amenities", [])
    
    text = "✨ <b>امکانات مورد نیاز:</b>\n\n"
    text += "می‌توانید چند مورد انتخاب کنید:"
    
    buttons = []
    row = []
    
    for i, (key, label) in enumerate(AMENITIES_LIST.items()):
        status = "✅" if key in selected else "⬜️"
        row.append(
            InlineKeyboardButton(
                text=f"{status} {label}",
                callback_data=f"room_flt_am_{key}"
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton(text="✅ تأیید", callback_data="room_filter_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("room_flt_am_"))
async def filter_amenity_toggle(callback: types.CallbackQuery, state: FSMContext):
    """تغییر وضعیت امکانات در فیلتر"""
    
    key = callback.data.replace("room_flt_am_", "")
    data = await state.get_data()
    selected = data.get("filter_amenities", [])
    
    if key in selected:
        selected.remove(key)
    else:
        selected.append(key)
    
    await state.update_data(filter_amenities=selected)
    
    # نمایش مجدد منوی امکانات
    callback.data = "room_flt_amenities"
    await filter_amenities_menu(callback, state)


# ───────────────────────────────────────────────────────────────────
# جستجوی متنی
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_search_start")
async def search_start(callback: types.CallbackQuery, state: FSMContext):
    """شروع جستجوی متنی"""
    
    text = (
        "🔎 <b>جستجوی متنی</b>\n\n"
        "کلمه کلیدی مورد نظر را تایپ کنید:\n\n"
        "💡 مثال‌ها:\n"
        "   • نام منطقه: Elce, Centro\n"
        "   • امکانات: بالکن، پارکینگ\n"
        "   • قیمت: 350, 400\n\n"
        "برای لغو، روی دکمه زیر کلیک کنید."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="❌ لغو جستجو", callback_data="roommate")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await state.set_state(RoommateState.search_keyword)
    await callback.answer()


@router.message(RoommateState.search_keyword)
async def process_search_keyword(message: types.Message, state: FSMContext):
    """پردازش کلمه کلیدی جستجو"""
    
    keyword = message.text.strip()
    
    if len(keyword) < 2:
        await message.reply("⚠️ کلمه کلیدی باید حداقل 2 کاراکتر باشد.")
        return
    
    if len(keyword) > 50:
        await message.reply("⚠️ کلمه کلیدی نباید بیش از 50 کاراکتر باشد.")
        return
    
    # ذخیره کلمه کلیدی
    await state.update_data(search_keyword=keyword)
    await state.set_state(None)
    
    # ارسال پیام در حال جستجو
    temp_msg = await message.answer(f"🔍 در حال جستجوی «{keyword}»...")
    
    # شبیه‌سازی callback برای نمایش نتایج
    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
            self.data = "room_browse_1"
        
        async def answer(self, *args, **kwargs):
            pass
    
    fake_callback = FakeCallback(temp_msg, message.from_user)
    await browse_ads(fake_callback, state)


# ═══════════════════════════════════════════════════════════════════
# پایان بخش 2
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# بخش 3: جزئیات آگهی، ذخیره، گزارش، امتیاز
# ═══════════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────────
# نمایش جزئیات کامل آگهی
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("room_view_"))
async def view_ad_detail(callback: types.CallbackQuery, state: FSMContext):
    """نمایش جزئیات کامل یک آگهی"""
    
    # استخراج ID و شماره صفحه
    parts = callback.data.split("_")
    ad_id = int(parts[2])
    page_num = int(parts[3]) if len(parts) > 3 else 1
    
    # بارگذاری آگهی
    all_ads = await load_roommates()
    ad = next((a for a in all_ads if a["id"] == ad_id), None)
    
    if not ad:
        await callback.answer("⚠️ آگهی یافت نشد یا حذف شده است.", show_alert=True)
        return
    
    # افزایش بازدید (فقط برای کاربران دیگر)
    if ad.get("user_id") != callback.from_user.id:
        ad["views"] = ad.get("views", 0) + 1
        await save_json("roommates", all_ads)
    
    # ═══ ساخت متن جزئیات ═══
    
    # نشان ویژه
    premium_badge = ""
    if ad.get("is_premium"):
        premium_badge = "🌟 <b>آگهی ویژه</b> 🌟\n\n"
    
    # نوع آگهی
    ad_type_text = AD_TYPES.get(ad.get("ad_type", "room"), "🏠 اتاق")
    
    text = f"{premium_badge}"
    text += f"<b>{ad_type_text}</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # ═══ اطلاعات ملک ═══
    text += "🏠 <b>مشخصات ملک:</b>\n"
    text += f"   📍 منطقه: <b>{ad.get('area', 'نامشخص')}</b>\n"
    text += f"   💰 اجاره ماهانه: <b>{ad.get('budget', '?')}€</b>\n"
    text += f"   📐 متراژ: {ad.get('house_size', '?')} متر مربع\n"
    text += f"   🚪 تعداد اتاق: {ad.get('room_count', '?')}\n"
    text += f"   🛏 نوع تخت: {ad.get('bed_type', 'نامشخص')}\n"
    text += "\n"
    
    # ═══ شرایط ═══
    text += "📋 <b>شرایط:</b>\n"
    gender_icon = get_gender_icon(ad.get("gender", ""))
    text += f"   {gender_icon} جنسیت: {ad.get('gender', 'نامشخص')}\n"
    text += f"   📅 تاریخ آزاد: {ad.get('available_from', 'فوری')}\n"
    text += f"   ⏱ حداقل اقامت: {ad.get('min_stay', 'نامشخص')}\n"
    text += f"   🚬 سیگار: {ad.get('smoking', 'نامشخص')}\n"
    text += f"   🐾 حیوان خانگی: {ad.get('pets', 'نامشخص')}\n"
    text += "\n"
    
    # ═══ امکانات ═══
    amenities = ad.get("amenities", [])
    if amenities:
        text += "✨ <b>امکانات:</b>\n   "
        am_texts = [AMENITIES_LIST.get(k, k) for k in amenities]
        text += " | ".join(am_texts)
        text += "\n\n"
    
    # ═══ توضیحات ═══
    desc = ad.get("desc", "")
    if desc:
        truncated_desc = truncate_text(desc, 400)
        text += f"📝 <b>توضیحات:</b>\n{truncated_desc}\n\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    # ═══ اطلاعات آگهی‌دهنده ═══
    text += f"👤 <b>آگهی‌دهنده:</b> {ad.get('name', 'ناشناس')}"
    if ad.get("age"):
        text += f" ({ad['age']} ساله)"
    text += "\n"
    
    # امتیاز آگهی‌دهنده
    user_stats = await get_user_stats(ad.get("user_id", 0))
    if user_stats["avg_rating"] > 0:
        stars = "⭐" * int(user_stats["avg_rating"])
        text += f"⭐ امتیاز: {stars} ({user_stats['avg_rating']}/5 از {user_stats['rating_count']} نظر)\n"
    
    # ═══ آمار آگهی ═══
    text += "\n"
    text += f"📅 تاریخ ثبت: {format_date_persian(ad.get('date', ''))}\n"
    
    days_left = days_until_expiry(ad)
    text += f"⏳ روزهای باقیمانده: {days_left} روز\n"
    text += f"👁 بازدید: {ad.get('views', 0)}"
    text += f" | 📞 تماس: {ad.get('contacts', 0)}\n"
    
    # ═══ ساخت کیبورد ═══
    
    buttons = []
    is_owner = ad.get("user_id") == callback.from_user.id
    
    if is_owner:
        # ═══ دکمه‌های مالک آگهی ═══
        buttons.append([
            InlineKeyboardButton(
                text="⚙️ مدیریت آگهی",
                callback_data=f"room_manage_{ad_id}"
            )
        ])
    else:
        # ═══ دکمه‌های سایر کاربران ═══
        
        # تماس مستقیم
        buttons.append([
            InlineKeyboardButton(
                text="💬 تماس مستقیم در تلگرام",
                url=f"tg://user?id={ad.get('user_id')}"
            )
        ])
        
        # پیام داخلی و امتیاز
        buttons.append([
            InlineKeyboardButton(
                text="📨 ارسال پیام",
                callback_data=f"room_msg_{ad_id}"
            ),
            InlineKeyboardButton(
                text="⭐ ثبت امتیاز",
                callback_data=f"room_rate_{ad_id}"
            )
        ])
        
        # بررسی ذخیره بودن آگهی
        bookmarks = await load_json("room_bookmarks")
        is_bookmarked = any(
            b.get("user_id") == callback.from_user.id and b.get("ad_id") == ad_id
            for b in bookmarks
        )
        
        if is_bookmarked:
            bookmark_btn = InlineKeyboardButton(
                text="🔖 حذف از ذخیره‌ها",
                callback_data=f"room_unbookmark_{ad_id}"
            )
        else:
            bookmark_btn = InlineKeyboardButton(
                text="🔖 ذخیره آگهی",
                callback_data=f"room_bookmark_{ad_id}"
            )
        
        buttons.append([
            bookmark_btn,
            InlineKeyboardButton(
                text="🚩 گزارش تخلف",
                callback_data=f"room_report_{ad_id}"
            )
        ])
    
    # دکمه عکس‌ها (اگر موجود)
    photos = ad.get("photos", [])
    if ad.get("photo_path"):
        photos = [ad["photo_path"]] + photos
    
    if len(photos) > 1:
        buttons.append([
            InlineKeyboardButton(
                text=f"🖼 مشاهده عکس‌ها ({len(photos)})",
                callback_data=f"room_photos_{ad_id}_0"
            )
        ])
    
    # دکمه بازگشت
    buttons.append([
        InlineKeyboardButton(
            text="🔙 بازگشت به لیست",
            callback_data=f"room_browse_{page_num}"
        )
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # ═══ ارسال پیام ═══
    
    # بررسی وجود عکس
    photo_path = ad.get("photo_path")
    
    if photo_path and os.path.exists(photo_path):
        try:
            # حذف پیام قبلی و ارسال عکس
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=FSInputFile(photo_path),
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            await safe_edit_message(callback.message, text, keyboard)
    else:
        await safe_edit_message(callback.message, text, keyboard)
    
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# نمایش گالری عکس‌ها
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("room_photos_"))
async def view_photos(callback: types.CallbackQuery):
    """نمایش گالری عکس‌های آگهی"""
    
    parts = callback.data.split("_")
    ad_id = int(parts[2])
    photo_idx = int(parts[3]) if len(parts) > 3 else 0
    
    # بارگذاری آگهی
    all_ads = await load_roommates()
    ad = next((a for a in all_ads if a["id"] == ad_id), None)
    
    if not ad:
        await callback.answer("⚠️ آگهی یافت نشد!", show_alert=True)
        return
    
    # جمع‌آوری عکس‌ها
    photos = []
    if ad.get("photo_path") and os.path.exists(ad["photo_path"]):
        photos.append(ad["photo_path"])
    
    for p in ad.get("photos", []):
        if os.path.exists(p) and p not in photos:
            photos.append(p)
    
    if not photos:
        await callback.answer("⚠️ عکسی موجود نیست!", show_alert=True)
        return
    
    # اصلاح index
    photo_idx = photo_idx % len(photos)
    current_photo = photos[photo_idx]
    
    # ساخت کیبورد ناوبری
    nav_buttons = []
    
    if len(photos) > 1:
        prev_idx = (photo_idx - 1) % len(photos)
        next_idx = (photo_idx + 1) % len(photos)
        
        nav_buttons.append([
            InlineKeyboardButton(text="⬅️ قبلی", callback_data=f"room_photos_{ad_id}_{prev_idx}"),
            InlineKeyboardButton(text=f"📷 {photo_idx + 1}/{len(photos)}", callback_data="ignore"),
            InlineKeyboardButton(text="بعدی ➡️", callback_data=f"room_photos_{ad_id}_{next_idx}")
        ])
    
    nav_buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت به آگهی", callback_data=f"room_view_{ad_id}_1")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=nav_buttons)
    
    caption = f"🖼 عکس {photo_idx + 1} از {len(photos)}\n📍 {ad.get('area', '')}"
    
    try:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=FSInputFile(current_photo),
            caption=caption,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error showing photo: {e}")
        await callback.answer("⚠️ خطا در نمایش عکس", show_alert=True)
    
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# ذخیره آگهی (Bookmark)
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("room_bookmark_"))
async def bookmark_ad(callback: types.CallbackQuery):
    """ذخیره آگهی در لیست علاقه‌مندی‌ها"""
    
    ad_id = int(callback.data.replace("room_bookmark_", ""))
    user_id = callback.from_user.id
    
    # بارگذاری bookmark ها
    bookmarks = await load_json("room_bookmarks")
    
    # بررسی تکراری نبودن
    existing = next(
        (b for b in bookmarks if b["user_id"] == user_id and b["ad_id"] == ad_id),
        None
    )
    
    if existing:
        await callback.answer("این آگهی قبلاً ذخیره شده!", show_alert=True)
        return
    
    # اضافه کردن
    bookmarks.append({
        "user_id": user_id,
        "ad_id": ad_id,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    
    await save_json("room_bookmarks", bookmarks)
    
    await callback.answer("✅ آگهی ذخیره شد!", show_alert=True)
    
    # بروزرسانی صفحه
    callback.data = f"room_view_{ad_id}_1"
    await view_ad_detail(callback, None)


@router.callback_query(F.data.startswith("room_unbookmark_"))
async def unbookmark_ad(callback: types.CallbackQuery):
    """حذف آگهی از لیست علاقه‌مندی‌ها"""
    
    ad_id = int(callback.data.replace("room_unbookmark_", ""))
    user_id = callback.from_user.id
    
    # بارگذاری و فیلتر
    bookmarks = await load_json("room_bookmarks")
    bookmarks = [
        b for b in bookmarks
        if not (b["user_id"] == user_id and b["ad_id"] == ad_id)
    ]
    
    await save_json("room_bookmarks", bookmarks)
    
    await callback.answer("🗑 از ذخیره‌ها حذف شد!", show_alert=True)
    
    # بروزرسانی صفحه
    callback.data = f"room_view_{ad_id}_1"
    await view_ad_detail(callback, None)


# ───────────────────────────────────────────────────────────────────
# نمایش آگهی‌های ذخیره شده
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_bookmarks")
async def show_bookmarks(callback: types.CallbackQuery):
    """نمایش لیست آگهی‌های ذخیره شده"""
    
    user_id = callback.from_user.id
    
    # بارگذاری
    bookmarks = await load_json("room_bookmarks")
    user_bookmarks = [b for b in bookmarks if b["user_id"] == user_id]
    
    if not user_bookmarks:
        text = (
            "🔖 <b>آگهی‌های ذخیره شده</b>\n\n"
            "هنوز آگهی‌ای ذخیره نکرده‌اید!\n\n"
            "💡 برای ذخیره آگهی، در صفحه جزئیات روی «🔖 ذخیره آگهی» کلیک کنید."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
            [InlineKeyboardButton(text="📋 مشاهده آگهی‌ها", callback_data="room_browse_1")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="roommate")]
        ])
        
        await safe_edit_message(callback.message, text, keyboard)
        await callback.answer()
        return
    
    # بارگذاری آگهی‌ها
    all_ads = await load_roommates()
    
    text = f"🔖 <b>آگهی‌های ذخیره شده ({len(user_bookmarks)})</b>\n\n"
    
    buttons = []
    valid_count = 0
    
    for bookmark in user_bookmarks:
        ad = next((a for a in all_ads if a["id"] == bookmark["ad_id"]), None)
        
        if ad and ad.get("active") and ad.get("status") == "approved":
            valid_count += 1
            gender_icon = get_gender_icon(ad.get("gender", ""))
            
            text += f"{valid_count}. <b>{ad.get('area', '?')}</b>\n"
            text += f"   {gender_icon} {ad.get('budget', '?')}€ | 🏠 {ad.get('house_size', '?')}m²\n\n"
            
            btn_text = f"📍 {ad.get('area', '?')[:10]} - {ad.get('budget', '?')}€"
            buttons.append([
                InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"room_view_{ad['id']}_1"
                )
            ])
        else:
            # آگهی غیرفعال یا حذف شده - حذف از bookmark
            bookmarks = [
                b for b in bookmarks
                if not (b["user_id"] == user_id and b["ad_id"] == bookmark["ad_id"])
            ]
    
    # ذخیره تغییرات
    await save_json("room_bookmarks", bookmarks)
    
    if valid_count == 0:
        text += "⚠️ همه آگهی‌های ذخیره شده منقضی یا حذف شده‌اند."
    
    buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="roommate")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# گزارش تخلف
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("room_report_"))
async def report_ad_start(callback: types.CallbackQuery, state: FSMContext):
    """شروع گزارش تخلف"""
    
    ad_id = int(callback.data.replace("room_report_", ""))
    
    await state.update_data(report_ad_id=ad_id)
    await state.set_state(RoommateState.reporting_reason)
    
    text = (
        "🚩 <b>گزارش تخلف</b>\n\n"
        "دلیل گزارش را انتخاب کنید یا بنویسید:\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="🚫 اطلاعات نادرست", callback_data="report_reason_fake")],
        [InlineKeyboardButton(text="💰 کلاهبرداری / قیمت غیرواقعی", callback_data="report_reason_scam")],
        [InlineKeyboardButton(text="🔞 محتوای نامناسب", callback_data="report_reason_inappropriate")],
        [InlineKeyboardButton(text="📍 آدرس اشتباه", callback_data="report_reason_address")],
        [InlineKeyboardButton(text="🏠 آگهی تکراری", callback_data="report_reason_duplicate")],
        [InlineKeyboardButton(text="✍️ دلیل دیگر (تایپ کنید)", callback_data="report_reason_custom")],
        [InlineKeyboardButton(text="❌ لغو", callback_data=f"room_view_{ad_id}_1")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("report_reason_"), RoommateState.reporting_reason)
async def report_reason_selected(callback: types.CallbackQuery, state: FSMContext):
    """انتخاب دلیل گزارش از لیست"""
    
    reason_key = callback.data.replace("report_reason_", "")
    
    reasons_map = {
        "fake": "اطلاعات نادرست",
        "scam": "کلاهبرداری / قیمت غیرواقعی",
        "inappropriate": "محتوای نامناسب",
        "address": "آدرس اشتباه",
        "duplicate": "آگهی تکراری"
    }
    
    if reason_key == "custom":
        await callback.message.edit_text(
            "✍️ <b>دلیل گزارش:</b>\n\nلطفاً دلیل را تایپ کنید:",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    reason = reasons_map.get(reason_key, reason_key)
    await process_report(callback, state, reason)


@router.message(RoommateState.reporting_reason)
async def report_reason_custom(message: types.Message, state: FSMContext):
    """دریافت دلیل سفارشی گزارش"""
    
    reason = message.text.strip()
    
    if len(reason) < 5:
        await message.reply("⚠️ دلیل باید حداقل 5 کاراکتر باشد.")
        return
    
    # ساخت callback مجازی
    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
        
        async def answer(self, *args, **kwargs):
            pass
    
    fake_callback = FakeCallback(message, message.from_user)
    await process_report(fake_callback, state, reason)


async def process_report(callback, state: FSMContext, reason: str):
    """پردازش نهایی گزارش"""
    
    data = await state.get_data()
    ad_id = data.get("report_ad_id")
    
    if not ad_id:
        await state.clear()
        return
    
    # ذخیره گزارش در آگهی
    all_ads = await load_roommates()
    ad = next((a for a in all_ads if a["id"] == ad_id), None)
    
    if ad:
        if "reports" not in ad:
            ad["reports"] = []
        
        ad["reports"].append({
            "user_id": callback.from_user.id,
            "reason": reason,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        
        await save_json("roommates", all_ads)
        
        # اطلاع به ادمین‌ها
        admin_text = (
            f"🚨 <b>گزارش تخلف جدید</b>\n\n"
            f"📋 آگهی: #{ad_id}\n"
            f"📍 منطقه: {ad.get('area', '?')}\n"
            f"💰 قیمت: {ad.get('budget', '?')}€\n"
            f"👤 آگهی‌دهنده: {ad.get('name', '?')}\n\n"
            f"🚩 <b>دلیل گزارش:</b>\n{reason}\n\n"
            f"👤 گزارش‌دهنده: {callback.from_user.full_name}\n"
            f"🆔 ID: {callback.from_user.id}"
        )
        
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
            [
                InlineKeyboardButton(text="👁 مشاهده آگهی", callback_data=f"room_view_{ad_id}_1"),
                InlineKeyboardButton(text="🗑 حذف آگهی", callback_data=f"adm_delete_{ad_id}")
            ],
            [InlineKeyboardButton(text="❌ رد گزارش", callback_data=f"adm_dismiss_report_{ad_id}")]
        ])
        
        await notify_admins(callback.message.bot, admin_text, admin_kb)
    
    await state.clear()
    
    # پیام تأیید
    text = (
        "✅ <b>گزارش شما ثبت شد</b>\n\n"
        "با تشکر از همکاری شما!\n"
        "تیم ما گزارش را بررسی خواهد کرد."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="roommate")]
    ])
    
    if hasattr(callback.message, 'edit_text'):
        await safe_edit_message(callback.message, text, keyboard)
    else:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ───────────────────────────────────────────────────────────────────
# سیستم امتیازدهی
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("room_rate_"))
async def rate_user_start(callback: types.CallbackQuery, state: FSMContext):
    """شروع امتیازدهی به آگهی‌دهنده"""
    
    ad_id = int(callback.data.replace("room_rate_", ""))
    
    # بارگذاری آگهی
    all_ads = await load_roommates()
    ad = next((a for a in all_ads if a["id"] == ad_id), None)
    
    if not ad:
        await callback.answer("⚠️ آگهی یافت نشد!", show_alert=True)
        return
    
    # بررسی امتیاز قبلی
    ratings = await load_json("room_ratings")
    existing = next(
        (r for r in ratings 
         if r["from_user"] == callback.from_user.id 
         and r["to_user"] == ad["user_id"]),
        None
    )
    
    if existing:
        await callback.answer("⚠️ شما قبلاً به این کاربر امتیاز داده‌اید!", show_alert=True)
        return
    
    # ذخیره اطلاعات
    await state.update_data(
        rate_ad_id=ad_id,
        rate_to_user=ad["user_id"],
        rate_to_name=ad.get("name", "ناشناس")
    )
    await state.set_state(RoommateState.rating_score)
    
    text = (
        f"⭐ <b>امتیازدهی به {ad.get('name', 'آگهی‌دهنده')}</b>\n\n"
        "از ۱ تا ۵ امتیاز دهید:\n\n"
        "⭐ = ضعیف\n"
        "⭐⭐⭐ = متوسط\n"
        "⭐⭐⭐⭐⭐ = عالی"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [
            InlineKeyboardButton(text="⭐", callback_data="rate_score_1"),
            InlineKeyboardButton(text="⭐⭐", callback_data="rate_score_2"),
            InlineKeyboardButton(text="⭐⭐⭐", callback_data="rate_score_3"),
        ],
        [
            InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="rate_score_4"),
            InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="rate_score_5"),
        ],
        [InlineKeyboardButton(text="❌ لغو", callback_data=f"room_view_{ad_id}_1")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("rate_score_"), RoommateState.rating_score)
async def rate_score_selected(callback: types.CallbackQuery, state: FSMContext):
    """انتخاب امتیاز"""
    
    score = int(callback.data.replace("rate_score_", ""))
    await state.update_data(rate_score=score)
    await state.set_state(RoommateState.rating_comment)
    
    text = (
        f"✅ امتیاز {'⭐' * score} ثبت شد!\n\n"
        "آیا می‌خواهید نظری هم بنویسید؟\n"
        "(اختیاری - می‌توانید رد کنید)"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="⏭ رد کردن (بدون نظر)", callback_data="rate_skip_comment")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data == "rate_skip_comment", RoommateState.rating_comment)
async def rate_skip_comment(callback: types.CallbackQuery, state: FSMContext):
    """رد کردن نظر و ثبت نهایی"""
    
    await save_rating(callback, state, None)


@router.message(RoommateState.rating_comment)
async def rate_comment_received(message: types.Message, state: FSMContext):
    """دریافت نظر و ثبت نهایی"""
    
    comment = message.text.strip()
    
    if len(comment) > 500:
        await message.reply("⚠️ نظر نباید بیش از 500 کاراکتر باشد.")
        return
    
    # ساخت callback مجازی
    class FakeCallback:
        def __init__(self, msg, user):
            self.message = msg
            self.from_user = user
        
        async def answer(self, *args, **kwargs):
            pass
    
    fake_callback = FakeCallback(message, message.from_user)
    await save_rating(fake_callback, state, comment)


async def save_rating(callback, state: FSMContext, comment: str):
    """ذخیره امتیاز در دیتابیس"""
    
    data = await state.get_data()
    
    score = data.get("rate_score", 3)
    to_user = data.get("rate_to_user")
    to_name = data.get("rate_to_name", "ناشناس")
    ad_id = data.get("rate_ad_id")
    
    # بارگذاری و ذخیره
    ratings = await load_json("room_ratings")
    
    ratings.append({
        "from_user": callback.from_user.id,
        "from_name": callback.from_user.full_name,
        "to_user": to_user,
        "to_name": to_name,
        "ad_id": ad_id,
        "score": score,
        "comment": comment,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    
    await save_json("room_ratings", ratings)
    
    await state.clear()
    
    # پیام تأیید
    stars = "⭐" * score
    text = (
        f"✅ <b>امتیاز شما ثبت شد!</b>\n\n"
        f"👤 به: {to_name}\n"
        f"⭐ امتیاز: {stars}\n"
    )
    
    if comment:
        text += f"💬 نظر: {comment}\n"
    
    text += "\nبا تشکر از مشارکت شما!"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="roommate")]
    ])
    
    if hasattr(callback.message, 'edit_text'):
        await safe_edit_message(callback.message, text, keyboard)
    else:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ───────────────────────────────────────────────────────────────────
# ارسال پیام به آگهی‌دهنده
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("room_msg_"))
async def send_message_start(callback: types.CallbackQuery, state: FSMContext):
    """شروع ارسال پیام به آگهی‌دهنده"""
    
    ad_id = int(callback.data.replace("room_msg_", ""))
    
    # بارگذاری آگهی
    all_ads = await load_roommates()
    ad = next((a for a in all_ads if a["id"] == ad_id), None)
    
    if not ad:
        await callback.answer("⚠️ آگهی یافت نشد!", show_alert=True)
        return
    
    await state.update_data(
        msg_ad_id=ad_id,
        msg_to_user=ad["user_id"],
        msg_to_name=ad.get("name", "ناشناس")
    )
    await state.set_state(RoommateState.sending_message)
    
    text = (
        f"📨 <b>ارسال پیام به {ad.get('name', 'آگهی‌دهنده')}</b>\n\n"
        "پیام خود را تایپ کنید:\n\n"
        "💡 نکته: اطلاعات تماس خود را هم بنویسید."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="❌ لغو", callback_data=f"room_view_{ad_id}_1")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.message(RoommateState.sending_message)
async def send_message_process(message: types.Message, state: FSMContext):
    """پردازش و ارسال پیام"""
    
    data = await state.get_data()
    
    ad_id = data.get("msg_ad_id")
    to_user = data.get("msg_to_user")
    to_name = data.get("msg_to_name", "ناشناس")
    
    msg_text = message.text.strip()
    
    if len(msg_text) < 10:
        await message.reply("⚠️ پیام باید حداقل 10 کاراکتر باشد.")
        return
    
    if len(msg_text) > 1000:
        await message.reply("⚠️ پیام نباید بیش از 1000 کاراکتر باشد.")
        return
    
    # ذخیره پیام
    messages = await load_json("room_messages")
    
    new_msg = {
        "id": len(messages) + 1,
        "from_user": message.from_user.id,
        "from_name": message.from_user.full_name,
        "to_user": to_user,
        "to_name": to_name,
        "ad_id": ad_id,
        "text": msg_text,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "read": False
    }
    
    messages.append(new_msg)
    await save_json("room_messages", messages)
    
    # افزایش تعداد تماس در آگهی
    all_ads = await load_roommates()
    for ad in all_ads:
        if ad["id"] == ad_id:
            ad["contacts"] = ad.get("contacts", 0) + 1
            break
    await save_json("roommates", all_ads)
    
    # ارسال نوتیفیکیشن به آگهی‌دهنده
    try:
        notify_text = (
            f"📨 <b>پیام جدید!</b>\n\n"
            f"از: {message.from_user.full_name}\n"
            f"درباره آگهی: #{ad_id}\n\n"
            f"💬 پیام:\n{msg_text}"
        )
        
        notify_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
            [InlineKeyboardButton(
                text="💬 پاسخ مستقیم",
                url=f"tg://user?id={message.from_user.id}"
            )],
            [InlineKeyboardButton(text="👁 مشاهده آگهی", callback_data=f"room_view_{ad_id}_1")]
        ])
        
        await message.bot.send_message(
            to_user,
            notify_text,
            reply_markup=notify_kb,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
    
    await state.clear()
    
    # پیام تأیید
    text = (
        "✅ <b>پیام شما ارسال شد!</b>\n\n"
        f"گیرنده: {to_name}\n\n"
        "آگهی‌دهنده می‌تواند مستقیماً به شما پاسخ دهد."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="roommate")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ───────────────────────────────────────────────────────────────────
# صندوق پیام‌ها
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_messages")
async def show_messages(callback: types.CallbackQuery):
    """نمایش صندوق پیام‌ها"""
    
    user_id = callback.from_user.id
    
    # بارگذاری پیام‌ها
    messages = await load_json("room_messages")
    
    # پیام‌های دریافتی و ارسالی
    received = [m for m in messages if m["to_user"] == user_id]
    sent = [m for m in messages if m["from_user"] == user_id]
    
    unread_count = sum(1 for m in received if not m.get("read"))
    
    text = f"💬 <b>صندوق پیام‌ها</b>\n\n"
    text += f"📥 دریافتی: {len(received)} (🔴 {unread_count} خوانده نشده)\n"
    text += f"📤 ارسالی: {len(sent)}\n"
    
    if not received and not sent:
        text += "\n📭 هنوز پیامی ندارید!"
    else:
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        # نمایش آخرین ۵ پیام دریافتی
        if received:
            text += "\n📥 <b>آخرین پیام‌های دریافتی:</b>\n\n"
            
            for msg in received[-5:]:
                unread_icon = "🔴 " if not msg.get("read") else ""
                text += f"{unread_icon}<b>{msg['from_name']}</b>\n"
                text += f"   {truncate_text(msg['text'], 50)}\n"
                text += f"   📅 {msg['date']}\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="roommate")]
    ])
    
    # علامت‌گذاری به عنوان خوانده شده
    for msg in received:
        msg["read"] = True
    await save_json("room_messages", messages)
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════
# پایان بخش 3
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# بخش 4: ثبت آگهی جدید (کامل)
# ═══════════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────────
# شروع ثبت آگهی
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_add_start")
async def add_ad_start(callback: types.CallbackQuery, state: FSMContext):
    """شروع فرآیند ثبت آگهی جدید"""
    
    await state.clear()
    
    user_id = callback.from_user.id
    
    # بررسی محدودیت تعداد آگهی
    all_ads = await load_roommates()
    user_active_ads = [
        ad for ad in all_ads
        if ad.get("user_id") == user_id
        and ad.get("status") in ["pending", "approved"]
        and ad.get("active", True)
        and not ad.get("is_found", False)
    ]
    
    if len(user_active_ads) >= MAX_ADS_PER_USER:
        text = (
            f"⚠️ <b>محدودیت تعداد آگهی</b>\n\n"
            f"شما حداکثر {MAX_ADS_PER_USER} آگهی فعال می‌توانید داشته باشید.\n\n"
            f"آگهی‌های فعال شما: {len(user_active_ads)}\n\n"
            "💡 برای ثبت آگهی جدید:\n"
            "   • آگهی‌های قبلی را غیرفعال کنید\n"
            "   • یا آنها را حذف کنید"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
            [InlineKeyboardButton(text="👤 مدیریت آگهی‌ها", callback_data="room_my_ads")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="roommate")]
        ])
        
        await safe_edit_message(callback.message, text, keyboard)
        await callback.answer()
        return
    
    # شروع ثبت آگهی با انتخاب چندگانه
    initial_types = ["room"]
    await state.update_data(selected_types=initial_types)
    
    text = (
        "📝 <b>ثبت آگهی جدید هم‌خانه و مسکن</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🏠 <b>مرحله 1 از 13: نوع ملک / آگهی</b>\n\n"
        "می‌توانید یک یا چند گزینه را همزمان انتخاب کنید (روی گزینه‌ها کلیک کنید تا تیک بخورند):\n\n"
        "💡 <i>مثلاً اگر هم برای اتاق و هم کل آپارتمان یا استودیو مناسب هستید، همه را علامت بزنید.</i>"
    )
    
    def get_ad_type_select_keyboard(selected_types: list) -> InlineKeyboardMarkup:
        buttons = []
        for key, label in AD_TYPES.items():
            is_sel = key in selected_types
            check = "✅ " if is_sel else "⬜ "
            buttons.append([
                InlineKeyboardButton(text=f"{check}{label}", callback_data=f"add_toggle_type_{key}")
            ])
        
        all_housing = ["room", "apartment", "studio"]
        is_all = all(k in selected_types for k in all_housing)
        check_all = "✅ " if is_all else "✨ "
        buttons.append([
            InlineKeyboardButton(
                text=f"{check_all}انتخاب همه موارد مسکن (اتاق + آپارتمان + استودیو)", 
                callback_data="add_toggle_type_all"
            )
        ])
        
        count = len(selected_types)
        btn_text = f"➡️ تأیید و مرحله بعد ({count} مورد)" if count > 0 else "⚠️ لطفاً حداقل ۱ گزینه را انتخاب کنید"
        buttons.append([
            InlineKeyboardButton(text=btn_text, callback_data="add_types_confirm")
        ])
        buttons.append([
            InlineKeyboardButton(text="❌ انصراف و بازگشت", callback_data="roommate")
        ])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    keyboard = get_ad_type_select_keyboard(initial_types)
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# مرحله 1: نوع آگهی (پشتیبانی از انتخاب چندگانه)
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("add_toggle_type_"))
async def add_toggle_type(callback: types.CallbackQuery, state: FSMContext):
    """تغییر وضعیت تیک گزینه‌های نوع آگهی"""
    key = callback.data.replace("add_toggle_type_", "")
    data = await state.get_data()
    selected_types = list(data.get("selected_types", ["room"]))
    
    if key == "all":
        all_housing = ["room", "apartment", "studio"]
        if all(k in selected_types for k in all_housing):
            selected_types = ["room"]
        else:
            for h in all_housing:
                if h not in selected_types:
                    selected_types.append(h)
    else:
        if key in selected_types:
            selected_types.remove(key)
        else:
            selected_types.append(key)
            
    await state.update_data(selected_types=selected_types)
    
    # ساخت مجدد کیبورد
    buttons = []
    for k, label in AD_TYPES.items():
        is_sel = k in selected_types
        check = "✅ " if is_sel else "⬜ "
        buttons.append([
            InlineKeyboardButton(text=f"{check}{label}", callback_data=f"add_toggle_type_{k}")
        ])
    
    all_housing = ["room", "apartment", "studio"]
    is_all = all(k in selected_types for k in all_housing)
    check_all = "✅ " if is_all else "✨ "
    buttons.append([
        InlineKeyboardButton(
            text=f"{check_all}انتخاب همه موارد مسکن (اتاق + آپارتمان + استودیو)", 
            callback_data="add_toggle_type_all"
        )
    ])
    
    count = len(selected_types)
    btn_text = f"➡️ تأیید و مرحله بعد ({count} مورد)" if count > 0 else "⚠️ لطفاً حداقل ۱ گزینه را انتخاب کنید"
    buttons.append([
        InlineKeyboardButton(text=btn_text, callback_data="add_types_confirm")
    ])
    buttons.append([
        InlineKeyboardButton(text="❌ انصراف و بازگشت", callback_data="roommate")
    ])
    
    text = (
        "📝 <b>ثبت آگهی جدید هم‌خانه و مسکن</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🏠 <b>مرحله 1 از 13: نوع ملک / آگهی</b>\n\n"
        "می‌توانید یک یا چند گزینه را همزمان انتخاب کنید (روی گزینه‌ها کلیک کنید تا تیک بخورند):\n\n"
        "💡 <i>مثلاً اگر هم برای اتاق و هم کل آپارتمان یا استودیو مناسب هستید، همه را علامت بزنید.</i>"
    )
    await safe_edit_message(callback.message, text, InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data == "add_types_confirm")
async def add_types_confirm(callback: types.CallbackQuery, state: FSMContext):
    """تأیید نهایی انواع انتخابی و رفتن به مرحله نام"""
    data = await state.get_data()
    selected_types = data.get("selected_types", [])
    if not selected_types:
        await callback.answer("⚠️ لطفاً حداقل یکی از گزینه‌ها را تیک بزنید!", show_alert=True)
        return
        
    labels = [AD_TYPES[k] for k in selected_types if k in AD_TYPES]
    ad_type_label = " | ".join(labels)
    primary_type = selected_types[0]
    
    await state.update_data(ad_type=ad_type_label, primary_type=primary_type)
    await state.set_state(RoommateState.waiting_name)
    
    text = (
        f"✅ نوع انتخابی: <b>{ad_type_label}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👤 <b>مرحله 2 از 13</b>\n\n"
        "نام خود را وارد کنید:\n\n"
        "💡 این نام در آگهی به دیگران نمایش داده می‌شود."
    )
    await safe_edit_message(callback.message, text, None)
    await callback.answer()


@router.callback_query(F.data.startswith("add_type_"))
async def add_select_type(callback: types.CallbackQuery, state: FSMContext):
    """پشتیبانی تک‌انتخابی برای سازگاری"""
    ad_type = callback.data.replace("add_type_", "")
    ad_type_label = AD_TYPES.get(ad_type, ad_type)
    
    await state.update_data(ad_type=ad_type_label, primary_type=ad_type, selected_types=[ad_type])
    await state.set_state(RoommateState.waiting_name)
    
    text = (
        f"✅ نوع آگهی: <b>{ad_type_label}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👤 <b>مرحله 2 از 13</b>\n\n"
        "نام خود را وارد کنید:\n\n"
        "💡 این نام به دیگران نمایش داده می‌شود."
    )
    await safe_edit_message(callback.message, text, None)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# مرحله 2: نام
# ───────────────────────────────────────────────────────────────────

@router.message(RoommateState.waiting_name)
async def add_process_name(message: types.Message, state: FSMContext):
    """دریافت نام"""
    
    name = message.text.strip()
    
    # اعتبارسنجی
    if len(name) < 2:
        await message.reply("⚠️ نام باید حداقل 2 کاراکتر باشد.")
        return
    
    if len(name) > 50:
        await message.reply("⚠️ نام نباید بیش از 50 کاراکتر باشد.")
        return
    
    await state.update_data(name=name)
    await state.set_state(RoommateState.waiting_age)
    
    await message.answer(
        "🎂 <b>مرحله 3 از 13</b>\n\n"
        "سن خود را وارد کنید:\n\n"
        "💡 فقط عدد وارد کنید (مثلاً: 25)",
        parse_mode="HTML"
    )


# ───────────────────────────────────────────────────────────────────
# مرحله 3: سن
# ───────────────────────────────────────────────────────────────────

@router.message(RoommateState.waiting_age)
async def add_process_age(message: types.Message, state: FSMContext):
    """دریافت سن"""
    
    if not message.text.strip().isdigit():
        await message.reply("⚠️ لطفاً فقط عدد وارد کنید.")
        return
    
    age = int(message.text.strip())
    
    if age < 18:
        await message.reply("⚠️ حداقل سن 18 سال است.")
        return
    
    if age > 70:
        await message.reply("⚠️ حداکثر سن 70 سال است.")
        return
    
    await state.update_data(age=str(age))
    await state.set_state(RoommateState.waiting_gender)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [
            InlineKeyboardButton(text="👨 آقا", callback_data="add_gender_آقا"),
            InlineKeyboardButton(text="👩 خانم", callback_data="add_gender_خانم")
        ],
        [
            InlineKeyboardButton(text="👫 فرقی ندارد", callback_data="add_gender_فرقی ندارد")
        ]
    ])
    
    await message.answer(
        "🚻 <b>مرحله 4 از 13</b>\n\n"
        "جنسیت مورد قبول برای هم‌خانه:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ───────────────────────────────────────────────────────────────────
# مرحله 4: جنسیت
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("add_gender_"), RoommateState.waiting_gender)
async def add_process_gender(callback: types.CallbackQuery, state: FSMContext):
    """دریافت جنسیت"""
    
    gender = callback.data.replace("add_gender_", "")
    
    await state.update_data(gender=gender)
    await state.set_state(RoommateState.waiting_budget)
    
    await callback.message.edit_text(
        f"✅ جنسیت: {gender}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💰 <b>مرحله 5 از 13</b>\n\n"
        "اجاره ماهانه (یورو):\n\n"
        f"💡 عددی بین {MIN_BUDGET} تا {MAX_BUDGET} وارد کنید.",
        parse_mode="HTML"
    )
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# مرحله 5: بودجه
# ───────────────────────────────────────────────────────────────────

@router.message(RoommateState.waiting_budget)
async def add_process_budget(message: types.Message, state: FSMContext):
    """دریافت بودجه"""
    
    budget = safe_int(message.text, 0)
    
    if budget < MIN_BUDGET:
        await message.reply(f"⚠️ حداقل اجاره {MIN_BUDGET} یورو است.")
        return
    
    if budget > MAX_BUDGET:
        await message.reply(f"⚠️ حداکثر اجاره {MAX_BUDGET} یورو است.")
        return
    
    await state.update_data(budget=str(budget))
    await state.set_state(RoommateState.waiting_area)
    
    # ساخت دکمه‌های مناطق
    buttons = []
    row = []
    
    for i, (key, label) in enumerate(AREAS_LIST.items()):
        short_label = label.replace("📍 ", "")
        row.append(
            InlineKeyboardButton(text=short_label, callback_data=f"add_area_{key}")
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        f"✅ اجاره: {budget}€\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📍 <b>مرحله 6 از 13</b>\n\n"
        "منطقه ملک را انتخاب کنید:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ───────────────────────────────────────────────────────────────────
# مرحله 6: منطقه
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("add_area_"), RoommateState.waiting_area)
async def add_process_area(callback: types.CallbackQuery, state: FSMContext):
    """دریافت منطقه"""
    
    area_key = callback.data.replace("add_area_", "")
    area_label = AREAS_LIST.get(area_key, "").replace("📍 ", "")
    
    if area_key == "other":
        # درخواست نام منطقه سفارشی
        await state.set_state(RoommateState.waiting_area_custom)
        await callback.message.edit_text(
            "📍 <b>نام منطقه:</b>\n\n"
            "نام منطقه را تایپ کنید:",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    await state.update_data(area=area_label, area_key=area_key)
    await state.set_state(RoommateState.waiting_house_size)
    
    await callback.message.edit_text(
        f"✅ منطقه: {area_label}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📐 <b>مرحله 7 از 13</b>\n\n"
        "متراژ ملک (متر مربع):\n\n"
        "💡 فقط عدد وارد کنید (مثلاً: 20)",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(RoommateState.waiting_area_custom)
async def add_process_area_custom(message: types.Message, state: FSMContext):
    """دریافت نام منطقه سفارشی"""
    
    area = message.text.strip()
    
    if len(area) < 2:
        await message.reply("⚠️ نام منطقه باید حداقل 2 کاراکتر باشد.")
        return
    
    if len(area) > 50:
        await message.reply("⚠️ نام منطقه نباید بیش از 50 کاراکتر باشد.")
        return
    
    await state.update_data(area=area, area_key="other")
    await state.set_state(RoommateState.waiting_house_size)
    
    await message.answer(
        f"✅ منطقه: {area}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📐 <b>مرحله 7 از 13</b>\n\n"
        "متراژ ملک (متر مربع):\n\n"
        "💡 فقط عدد وارد کنید (مثلاً: 20)",
        parse_mode="HTML"
    )


# ───────────────────────────────────────────────────────────────────
# مرحله 7: متراژ
# ───────────────────────────────────────────────────────────────────

@router.message(RoommateState.waiting_house_size)
async def add_process_house_size(message: types.Message, state: FSMContext):
    """دریافت متراژ"""
    
    size = safe_int(message.text, 0)
    
    if size < 5:
        await message.reply("⚠️ حداقل متراژ 5 متر است.")
        return
    
    if size > 500:
        await message.reply("⚠️ حداکثر متراژ 500 متر است.")
        return
    
    await state.update_data(house_size=str(size))
    await state.set_state(RoommateState.waiting_room_count)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [
            InlineKeyboardButton(text="1️⃣", callback_data="add_rooms_1"),
            InlineKeyboardButton(text="2️⃣", callback_data="add_rooms_2"),
            InlineKeyboardButton(text="3️⃣", callback_data="add_rooms_3")
        ],
        [
            InlineKeyboardButton(text="4️⃣", callback_data="add_rooms_4"),
            InlineKeyboardButton(text="5️⃣+", callback_data="add_rooms_5+")
        ]
    ])
    
    await message.answer(
        f"✅ متراژ: {size} متر\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🚪 <b>مرحله 8 از 13</b>\n\n"
        "تعداد اتاق خواب:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ───────────────────────────────────────────────────────────────────
# مرحله 8: تعداد اتاق
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("add_rooms_"), RoommateState.waiting_room_count)
async def add_process_room_count(callback: types.CallbackQuery, state: FSMContext):
    """دریافت تعداد اتاق"""
    
    rooms = callback.data.replace("add_rooms_", "")
    
    await state.update_data(room_count=rooms)
    await state.set_state(RoommateState.waiting_bed_type)
    
    # ساخت دکمه‌های نوع تخت
    buttons = []
    for key, label in BED_TYPES.items():
        buttons.append([
            InlineKeyboardButton(text=label, callback_data=f"add_bed_{key}")
        ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        f"✅ تعداد اتاق: {rooms}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🛏 <b>مرحله 9 از 13</b>\n\n"
        "نوع تخت:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# مرحله 9: نوع تخت
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("add_bed_"), RoommateState.waiting_bed_type)
async def add_process_bed_type(callback: types.CallbackQuery, state: FSMContext):
    """دریافت نوع تخت"""
    
    bed_key = callback.data.replace("add_bed_", "")
    bed_label = BED_TYPES.get(bed_key, bed_key)
    
    await state.update_data(bed_type=bed_label)
    await state.set_state(RoommateState.waiting_available_from)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="📅 فوری (همین الان)", callback_data="add_avail_فوری")],
        [InlineKeyboardButton(text="📅 از هفته آینده", callback_data="add_avail_هفته آینده")],
        [InlineKeyboardButton(text="📅 از ماه آینده", callback_data="add_avail_ماه آینده")],
        [InlineKeyboardButton(text="📅 از 2 ماه دیگر", callback_data="add_avail_2 ماه دیگر")],
        [InlineKeyboardButton(text="✍️ تاریخ دلخواه", callback_data="add_avail_custom")]
    ])
    
    await callback.message.edit_text(
        f"✅ نوع تخت: {bed_label}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📅 <b>مرحله 10 از 13</b>\n\n"
        "تاریخ آزاد شدن ملک:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# مرحله 10: تاریخ آزاد شدن
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("add_avail_"), RoommateState.waiting_available_from)
async def add_process_available(callback: types.CallbackQuery, state: FSMContext):
    """دریافت تاریخ آزاد شدن"""
    
    avail = callback.data.replace("add_avail_", "")
    
    if avail == "custom":
        await state.set_state(RoommateState.waiting_available_custom)
        await callback.message.edit_text(
            "📅 <b>تاریخ دلخواه:</b>\n\n"
            "تاریخ را وارد کنید:\n"
            "(مثال: 15 ژانویه یا 2024-02-01)",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    await state.update_data(available_from=avail)
    await show_min_stay_step(callback, state)


@router.message(RoommateState.waiting_available_custom)
async def add_process_available_custom(message: types.Message, state: FSMContext):
    """دریافت تاریخ سفارشی"""
    
    avail = message.text.strip()
    
    if len(avail) < 3:
        await message.reply("⚠️ تاریخ معتبر وارد کنید.")
        return
    
    await state.update_data(available_from=avail)
    
    # ساخت callback مجازی
    class FakeCallback:
        def __init__(self, msg):
            self.message = msg
        async def answer(self):
            pass
    
    await show_min_stay_step(FakeCallback(message), state)


async def show_min_stay_step(callback, state: FSMContext):
    """نمایش مرحله حداقل اقامت"""
    
    await state.set_state(RoommateState.waiting_min_stay)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [
            InlineKeyboardButton(text="1 ماه", callback_data="add_stay_1 ماه"),
            InlineKeyboardButton(text="3 ماه", callback_data="add_stay_3 ماه")
        ],
        [
            InlineKeyboardButton(text="6 ماه", callback_data="add_stay_6 ماه"),
            InlineKeyboardButton(text="1 سال", callback_data="add_stay_1 سال")
        ],
        [
            InlineKeyboardButton(text="مهم نیست", callback_data="add_stay_مهم نیست")
        ]
    ])
    
    text = (
        "⏱ <b>مرحله 11 از 13</b>\n\n"
        "حداقل مدت اقامت:"
    )
    
    if hasattr(callback.message, 'edit_text'):
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    
    if hasattr(callback, 'answer'):
        await callback.answer()


# ───────────────────────────────────────────────────────────────────
# مرحله 11: حداقل اقامت
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("add_stay_"), RoommateState.waiting_min_stay)
async def add_process_min_stay(callback: types.CallbackQuery, state: FSMContext):
    """دریافت حداقل اقامت"""
    
    stay = callback.data.replace("add_stay_", "")
    
    await state.update_data(min_stay=stay)
    await state.set_state(RoommateState.waiting_smoking)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="🚭 ممنوع", callback_data="add_smoke_ممنوع")],
        [InlineKeyboardButton(text="🚬 مجاز", callback_data="add_smoke_مجاز")],
        [InlineKeyboardButton(text="🌬️ فقط در بالکن", callback_data="add_smoke_فقط بالکن")]
    ])
    
    await callback.message.edit_text(
        f"✅ حداقل اقامت: {stay}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🚬 <b>مرحله 12 از 13 - شرایط زندگی</b>\n\n"
        "وضعیت سیگار کشیدن:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# مرحله 12: سیگار و حیوانات
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("add_smoke_"), RoommateState.waiting_smoking)
async def add_process_smoking(callback: types.CallbackQuery, state: FSMContext):
    """دریافت وضعیت سیگار"""
    
    smoking = callback.data.replace("add_smoke_", "")
    
    await state.update_data(smoking=smoking)
    await state.set_state(RoommateState.waiting_pets)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="🚫 ندارم / ممنوع", callback_data="add_pet_ندارم")],
        [InlineKeyboardButton(text="🐕 دارم", callback_data="add_pet_دارم")],
        [InlineKeyboardButton(text="✅ مشکلی ندارم", callback_data="add_pet_مشکلی ندارم")]
    ])
    
    await callback.message.edit_text(
        f"✅ سیگار: {smoking}\n\n"
        "🐾 <b>وضعیت حیوان خانگی:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("add_pet_"), RoommateState.waiting_pets)
async def add_process_pets(callback: types.CallbackQuery, state: FSMContext):
    """دریافت وضعیت حیوانات"""
    
    pets = callback.data.replace("add_pet_", "")
    
    await state.update_data(pets=pets, selected_amenities=[])
    await state.set_state(RoommateState.waiting_amenities)
    
    # نمایش انتخاب امکانات
    await show_amenities_selector(callback.message, [])
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# مرحله 13: امکانات
# ───────────────────────────────────────────────────────────────────

async def show_amenities_selector(message: types.Message, selected: list):
    """نمایش لیست امکانات برای انتخاب"""
    
    text = (
        "✨ <b>مرحله 13 از 13 - امکانات</b>\n\n"
        "امکانات موجود را انتخاب کنید:\n"
        "(می‌توانید چند مورد انتخاب کنید)\n\n"
        f"✅ انتخاب شده: {len(selected)} مورد"
    )
    
    buttons = []
    row = []
    
    for i, (key, label) in enumerate(AMENITIES_LIST.items()):
        status = "✅" if key in selected else "⬜️"
        # کوتاه کردن label
        short_label = label.split(" ", 1)[-1] if " " in label else label
        row.append(
            InlineKeyboardButton(
                text=f"{status} {short_label}",
                callback_data=f"add_am_{key}"
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton(text="✅ تأیید و ادامه", callback_data="add_am_done")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await safe_edit_message(message, text, keyboard)


@router.callback_query(F.data.startswith("add_am_"), RoommateState.waiting_amenities)
async def add_process_amenities(callback: types.CallbackQuery, state: FSMContext):
    """پردازش انتخاب امکانات"""
    
    action = callback.data.replace("add_am_", "")
    
    if action == "done":
        # رفتن به مرحله عکس
        await state.set_state(RoommateState.waiting_photos)
        await state.update_data(photos=[])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
            [InlineKeyboardButton(text="⏭ رد کردن (بدون عکس)", callback_data="add_photo_skip")]
        ])
        
        await callback.message.edit_text(
            "📸 <b>عکس از ملک</b>\n\n"
            f"حداکثر {MAX_PHOTOS} عکس می‌توانید ارسال کنید.\n\n"
            "💡 عکس‌های با کیفیت شانس موفقیت را افزایش می‌دهد!\n\n"
            "یک عکس ارسال کنید یا رد کنید:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # تغییر وضعیت امکانات
    data = await state.get_data()
    selected = data.get("selected_amenities", [])
    
    if action in selected:
        selected.remove(action)
    else:
        selected.append(action)
    
    await state.update_data(selected_amenities=selected)
    
    # نمایش مجدد
    await show_amenities_selector(callback.message, selected)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# عکس‌ها
# ───────────────────────────────────────────────────────────────────

@router.message(RoommateState.waiting_photos, F.photo)
async def add_process_photo(message: types.Message, state: FSMContext):
    """دریافت عکس"""
    
    data = await state.get_data()
    photos = data.get("photos", [])
    
    if len(photos) >= MAX_PHOTOS:
        await message.reply(f"⚠️ حداکثر {MAX_PHOTOS} عکس می‌توانید ارسال کنید.")
        return
    
    # ذخیره عکس
    timestamp = int(datetime.now().timestamp())
    file_name = f"{message.from_user.id}_{timestamp}_{len(photos)}.jpg"
    file_path = UPLOAD_DIR / file_name
    
    try:
        await message.bot.download(message.photo[-1], destination=file_path)
        photos.append(str(file_path))
        await state.update_data(photos=photos)
        
        remaining = MAX_PHOTOS - len(photos)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
            [InlineKeyboardButton(text="✅ کافیه، ادامه بده", callback_data="add_photo_done")],
            [InlineKeyboardButton(text=f"➕ عکس بیشتر ({remaining} باقیمانده)", callback_data="add_photo_more")]
        ])
        
        await message.answer(
            f"✅ عکس {len(photos)} ذخیره شد!\n\n"
            f"می‌خواهید عکس بیشتری اضافه کنید؟",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error saving photo: {e}")
        await message.reply("⚠️ خطا در ذخیره عکس. دوباره تلاش کنید.")


@router.callback_query(F.data == "add_photo_more", RoommateState.waiting_photos)
async def add_photo_more(callback: types.CallbackQuery, state: FSMContext):
    """درخواست عکس بیشتر"""
    
    data = await state.get_data()
    photos = data.get("photos", [])
    remaining = MAX_PHOTOS - len(photos)
    
    await callback.message.edit_text(
        f"📸 عکس بعدی را ارسال کنید:\n\n"
        f"({remaining} عکس باقیمانده)"
    )
    await callback.answer()


@router.callback_query(F.data.in_(["add_photo_skip", "add_photo_done"]), RoommateState.waiting_photos)
async def add_photo_finish(callback: types.CallbackQuery, state: FSMContext):
    """پایان عکس‌ها و رفتن به توضیحات"""
    
    data = await state.get_data()
    photos = data.get("photos", [])
    
    # تنظیم photo_path
    if photos:
        await state.update_data(photo_path=photos[0])
    else:
        await state.update_data(photo_path=None)
    
    await state.set_state(RoommateState.waiting_desc)
    
    await callback.message.edit_text(
        "📝 <b>توضیحات نهایی</b>\n\n"
        "لطفاً توضیحات کامل درباره ملک بنویسید:\n\n"
        "💡 <b>پیشنهاد:</b>\n"
        "   • قوانین خانه\n"
        "   • ساعات رفت و آمد\n"
        "   • ویژگی‌های هم‌خانه ایده‌آل\n"
        "   • امکانات نزدیک (مترو، سوپر، ...)\n"
        "   • توضیحات اضافی\n\n"
        f"(حداکثر {MAX_DESC_LENGTH} کاراکتر)",
        parse_mode="HTML"
    )
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# توضیحات و ثبت نهایی
# ───────────────────────────────────────────────────────────────────

@router.message(RoommateState.waiting_desc)
async def add_process_desc(message: types.Message, state: FSMContext):
    """دریافت توضیحات و نمایش پیش‌نمایش"""
    
    desc = message.text.strip()
    
    if len(desc) < 20:
        await message.reply("⚠️ توضیحات باید حداقل 20 کاراکتر باشد.")
        return
    
    if len(desc) > MAX_DESC_LENGTH:
        await message.reply(f"⚠️ توضیحات نباید بیش از {MAX_DESC_LENGTH} کاراکتر باشد.")
        return
    
    await state.update_data(desc=desc)
    
    # نمایش پیش‌نمایش
    data = await state.get_data()
    
    ad_type_label = AD_TYPES.get(data.get("ad_type", "room"), "🏠")
    gender_icon = get_gender_icon(data.get("gender", ""))
    
    text = (
        "📋 <b>پیش‌نمایش آگهی شما</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{ad_type_label}</b>\n\n"
        f"👤 نام: {data.get('name')} ({data.get('age')} ساله)\n"
        f"{gender_icon} جنسیت: {data.get('gender')}\n"
        f"📍 منطقه: {data.get('area')}\n"
        f"💰 اجاره: {data.get('budget')}€\n"
        f"📐 متراژ: {data.get('house_size')}m²\n"
        f"🚪 اتاق: {data.get('room_count')}\n"
        f"🛏 تخت: {data.get('bed_type')}\n"
        f"📅 آزاد از: {data.get('available_from')}\n"
        f"⏱ حداقل اقامت: {data.get('min_stay')}\n"
        f"🚬 سیگار: {data.get('smoking')}\n"
        f"🐾 حیوان: {data.get('pets')}\n"
    )
    
    # امکانات
    amenities = data.get("selected_amenities", [])
    if amenities:
        am_texts = [AMENITIES_LIST.get(k, k) for k in amenities]
        text += f"✨ امکانات: {', '.join(am_texts)}\n"
    
    # عکس
    photos = data.get("photos", [])
    text += f"📸 عکس: {len(photos)} عدد\n"
    
    # توضیحات
    text += f"\n📝 توضیحات:\n{truncate_text(desc, 200)}\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    text += "\n✅ آگهی شما را ثبت کنم؟"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [
            InlineKeyboardButton(text="✅ تأیید و ثبت", callback_data="add_confirm_yes"),
            InlineKeyboardButton(text="❌ لغو", callback_data="add_confirm_no")
        ],
        [InlineKeyboardButton(text="✏️ ویرایش", callback_data="add_confirm_edit")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(RoommateState.confirm_submit)


# ───────────────────────────────────────────────────────────────────
# تأیید نهایی
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "add_confirm_yes", RoommateState.confirm_submit)
async def add_confirm_submit(callback: types.CallbackQuery, state: FSMContext):
    """ثبت نهایی آگهی"""
    
    data = await state.get_data()
    
    # بارگذاری آگهی‌ها
    all_ads = await load_roommates()
    
    # ساخت ID جدید
    if all_ads:
        new_id = max(ad.get("id", 0) for ad in all_ads) + 1
    else:
        new_id = 1
    
    # ساخت آگهی جدید
    new_ad = {
        "id": new_id,
        "user_id": callback.from_user.id,
        "username": callback.from_user.username,
        "name": data.get("name"),
        "age": data.get("age"),
        "gender": data.get("gender"),
        "budget": data.get("budget"),
        "area": data.get("area"),
        "area_key": data.get("area_key", "other"),
        "ad_type": data.get("ad_type", "room"),
        "house_size": data.get("house_size"),
        "room_count": data.get("room_count"),
        "bed_type": data.get("bed_type"),
        "available_from": data.get("available_from"),
        "min_stay": data.get("min_stay"),
        "smoking": data.get("smoking"),
        "pets": data.get("pets"),
        "amenities": data.get("selected_amenities", []),
        "desc": data.get("desc"),
        "photo_path": data.get("photo_path"),
        "photos": data.get("photos", []),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "status": "pending",
        "active": True,
        "is_found": False,
        "is_premium": False,
        "views": 0,
        "contacts": 0,
        "reports": [],
        "renewal_count": 0
    }
    
    # ذخیره
    all_ads.append(new_ad)
    await save_json("roommates", all_ads)
    
    # اطلاع به ادمین
    await notify_admin_new_ad(callback.message.bot, new_ad)
    
    await state.clear()
    
    # پیام تأیید به کاربر
    text = (
        "✅ <b>آگهی شما با موفقیت ثبت شد!</b>\n\n"
        f"🆔 شماره آگهی: #{new_id}\n"
        "📋 وضعیت: در انتظار تأیید ادمین\n\n"
        "⏳ آگهی شما پس از بررسی منتشر خواهد شد.\n"
        "🔔 نتیجه از طریق پیام به شما اطلاع داده می‌شود."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="👤 آگهی‌های من", callback_data="room_my_ads")],
        [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="roommate")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer("✅ آگهی ثبت شد!")


async def notify_admin_new_ad(bot: Bot, ad: dict):
    """ارسال نوتیفیکیشن آگهی جدید به ادمین"""
    
    ad_type_label = AD_TYPES.get(ad.get("ad_type", "room"), "🏠")
    gender_icon = get_gender_icon(ad.get("gender", ""))
    
    text = (
        "🔔 <b>آگهی جدید نیاز به تأیید!</b>\n\n"
        f"🆔 شماره: #{ad['id']}\n"
        f"📋 نوع: {ad_type_label}\n\n"
        f"👤 نام: {ad.get('name')} ({ad.get('age')} ساله)\n"
        f"{gender_icon} جنسیت: {ad.get('gender')}\n"
        f"📍 منطقه: {ad.get('area')}\n"
        f"💰 اجاره: {ad.get('budget')}€\n"
        f"📐 متراژ: {ad.get('house_size')}m²\n"
        f"🚪 اتاق: {ad.get('room_count')}\n\n"
        f"📝 توضیحات:\n{truncate_text(ad.get('desc', ''), 300)}\n\n"
        f"👤 کاربر: <a href='tg://user?id={ad['user_id']}'>{ad.get('name')}</a>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [
            InlineKeyboardButton(text="✅ تأیید", callback_data=f"adm_approve_{ad['id']}"),
            InlineKeyboardButton(text="🌟 تأیید ویژه", callback_data=f"adm_premium_{ad['id']}")
        ],
        [InlineKeyboardButton(text="❌ رد کردن", callback_data=f"adm_reject_{ad['id']}")]
    ])
    
    photo_path = ad.get("photo_path")
    await notify_admins(bot, text, keyboard, photo_path)


@router.callback_query(F.data == "add_confirm_no", RoommateState.confirm_submit)
async def add_confirm_cancel(callback: types.CallbackQuery, state: FSMContext):
    """لغو ثبت آگهی"""
    
    await state.clear()
    
    text = "❌ <b>ثبت آگهی لغو شد.</b>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="📝 ثبت مجدد", callback_data="room_add_start")],
        [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="roommate")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data == "add_confirm_edit", RoommateState.confirm_submit)
async def add_confirm_edit(callback: types.CallbackQuery, state: FSMContext):
    """ویرایش قبل از ثبت - شروع مجدد"""
    
    # برگشت به مرحله اول
    await callback.message.edit_text(
        "✏️ <b>ویرایش آگهی</b>\n\n"
        "متأسفانه فعلاً امکان ویرایش جزئی وجود ندارد.\n"
        "می‌توانید از اول شروع کنید یا همین را ثبت کنید.",
        parse_mode="HTML"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="🔄 شروع از اول", callback_data="room_add_start")],
        [InlineKeyboardButton(text="✅ ثبت همین آگهی", callback_data="add_confirm_yes")],
        [InlineKeyboardButton(text="❌ لغو", callback_data="roommate")]
    ])
    
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════
# پایان بخش 4
# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# بخش 5: مدیریت آگهی‌ها، هشدار، ادمین، تمدید
# ═══════════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────────
# مدیریت آگهی‌های کاربر
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_my_ads")
async def show_my_ads(callback: types.CallbackQuery):
    """نمایش لیست آگهی‌های کاربر"""
    
    user_id = callback.from_user.id
    
    all_ads = await load_roommates()
    my_ads = [ad for ad in all_ads if ad.get("user_id") == user_id]
    
    if not my_ads:
        text = (
            "👤 <b>آگهی‌های من</b>\n\n"
            "📭 شما هنوز آگهی‌ای ثبت نکرده‌اید!\n\n"
            "💡 برای ثبت آگهی جدید، دکمه زیر را بزنید."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
            [InlineKeyboardButton(text="📝 ثبت آگهی جدید", callback_data="room_add_start")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="roommate")]
        ])
        
        await safe_edit_message(callback.message, text, keyboard)
        await callback.answer()
        return
    
    # آمار
    active_count = sum(1 for a in my_ads if a.get("active") and a.get("status") == "approved" and not a.get("is_found"))
    pending_count = sum(1 for a in my_ads if a.get("status") == "pending")
    found_count = sum(1 for a in my_ads if a.get("is_found"))
    
    text = (
        "👤 <b>آگهی‌های من</b>\n\n"
        f"📊 <b>آمار:</b>\n"
        f"   ✅ فعال: {active_count}\n"
        f"   ⏳ در انتظار: {pending_count}\n"
        f"   🎉 موفق: {found_count}\n"
        f"   📦 کل: {len(my_ads)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "برای مدیریت، روی آگهی کلیک کنید:"
    )
    
    buttons = []
    
    for ad in my_ads:
        # تعیین آیکون وضعیت
        if ad.get("is_found"):
            status_icon = "🎉"
            status_text = "پیدا شد"
        elif ad.get("status") == "pending":
            status_icon = "⏳"
            status_text = "در انتظار"
        elif ad.get("status") == "rejected":
            status_icon = "❌"
            status_text = "رد شده"
        elif not ad.get("active"):
            status_icon = "💤"
            status_text = "غیرفعال"
        elif ad.get("expired"):
            status_icon = "⌛"
            status_text = "منقضی"
        else:
            status_icon = "✅"
            status_text = "فعال"
        
        days_left = days_until_expiry(ad)
        
        btn_text = f"{status_icon} {ad.get('area', '?')[:12]} | {ad.get('budget', '?')}€"
        
        buttons.append([
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"room_manage_{ad['id']}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="📝 ثبت آگهی جدید", callback_data="room_add_start")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="roommate")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# مدیریت یک آگهی خاص
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("room_manage_"))
async def manage_ad(callback: types.CallbackQuery):
    """منوی مدیریت یک آگهی"""
    
    ad_id = int(callback.data.replace("room_manage_", ""))
    
    all_ads = await load_roommates()
    ad = next((a for a in all_ads if a["id"] == ad_id), None)
    
    if not ad:
        await callback.answer("⚠️ آگهی یافت نشد!", show_alert=True)
        return
    
    # بررسی مالکیت
    if ad.get("user_id") != callback.from_user.id:
        await callback.answer("⛔ شما مالک این آگهی نیستید!", show_alert=True)
        return
    
    # تعیین وضعیت
    if ad.get("is_found"):
        status = "🎉 پیدا شده (بایگانی)"
    elif ad.get("status") == "pending":
        status = "⏳ در انتظار تأیید"
    elif ad.get("status") == "rejected":
        status = "❌ رد شده"
    elif not ad.get("active"):
        status = "💤 غیرفعال"
    elif ad.get("expired"):
        status = "⌛ منقضی شده"
    else:
        status = "✅ فعال"
    
    days_left = days_until_expiry(ad)
    
    text = (
        f"⚙️ <b>مدیریت آگهی #{ad_id}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📍 منطقه: {ad.get('area', '?')}\n"
        f"💰 اجاره: {ad.get('budget', '?')}€\n"
        f"📅 تاریخ ثبت: {format_date_persian(ad.get('date', ''))}\n\n"
        f"📊 <b>وضعیت:</b> {status}\n"
        f"⏳ روز باقیمانده: {days_left}\n"
        f"👁 بازدید: {ad.get('views', 0)}\n"
        f"📞 تماس: {ad.get('contacts', 0)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "چه کاری انجام دهم؟"
    )
    
    buttons = []
    
    # دکمه مشاهده
    buttons.append([
        InlineKeyboardButton(text="👁 مشاهده آگهی", callback_data=f"room_view_{ad_id}_1")
    ])
    
    # دکمه‌های عملیات بر اساس وضعیت
    if ad.get("status") == "approved" and ad.get("active") and not ad.get("is_found"):
        # آگهی فعال
        buttons.append([
            InlineKeyboardButton(
                text="🎉 پیدا کردم! (بایگانی)",
                callback_data=f"room_found_{ad_id}"
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text="💤 غیرفعال کردن",
                callback_data=f"room_deactivate_{ad_id}"
            )
        ])
        
        # تمدید (اگر کمتر از 10 روز مانده)
        if days_left <= 10:
            buttons.append([
                InlineKeyboardButton(
                    text=f"🔄 تمدید ({EXPIRATION_DAYS} روز دیگر)",
                    callback_data=f"room_renew_{ad_id}"
                )
            ])
    
    elif ad.get("is_found"):
        # بایگانی شده
        buttons.append([
            InlineKeyboardButton(
                text="🔄 فعال کردن مجدد",
                callback_data=f"room_reactivate_{ad_id}"
            )
        ])
    
    elif not ad.get("active") or ad.get("expired"):
        # غیرفعال یا منقضی
        buttons.append([
            InlineKeyboardButton(
                text="✅ فعال کردن مجدد",
                callback_data=f"room_reactivate_{ad_id}"
            )
        ])
    
    # ویرایش
    if ad.get("status") != "pending":
        buttons.append([
            InlineKeyboardButton(
                text="✏️ ویرایش آگهی",
                callback_data=f"room_edit_{ad_id}"
            )
        ])
    
    # حذف
    buttons.append([
        InlineKeyboardButton(
            text="🗑 حذف آگهی",
            callback_data=f"room_delete_{ad_id}"
        )
    ])
    
    # بازگشت
    buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="room_my_ads")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ───────────────────────────────────────────────────────────────────
# عملیات روی آگهی: پیدا شد
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("room_found_"))
async def mark_as_found(callback: types.CallbackQuery):
    """علامت‌گذاری آگهی به عنوان پیدا شده"""
    
    ad_id = int(callback.data.replace("room_found_", ""))
    
    all_ads = await load_roommates()
    
    for ad in all_ads:
        if ad["id"] == ad_id and ad.get("user_id") == callback.from_user.id:
            ad["is_found"] = True
            ad["active"] = False
            ad["found_date"] = datetime.now().strftime("%Y-%m-%d")
            await save_json("roommates", all_ads)
            
            await callback.answer("🎉 تبریک! امیدوارم هم‌خانه خوبی پیدا کرده باشید!", show_alert=True)
            
            # بازگشت به لیست
            callback.data = "room_my_ads"
            await show_my_ads(callback)
            return
    
    await callback.answer("⚠️ خطا در انجام عملیات", show_alert=True)


# ───────────────────────────────────────────────────────────────────
# عملیات روی آگهی: غیرفعال کردن
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("room_deactivate_"))
async def deactivate_ad(callback: types.CallbackQuery):
    """غیرفعال کردن آگهی"""
    
    ad_id = int(callback.data.replace("room_deactivate_", ""))
    
    all_ads = await load_roommates()
    
    for ad in all_ads:
        if ad["id"] == ad_id and ad.get("user_id") == callback.from_user.id:
            ad["active"] = False
            await save_json("roommates", all_ads)
            
            await callback.answer("💤 آگهی غیرفعال شد", show_alert=True)
            
            callback.data = f"room_manage_{ad_id}"
            await manage_ad(callback)
            return
    
    await callback.answer("⚠️ خطا", show_alert=True)


# ───────────────────────────────────────────────────────────────────
# عملیات روی آگهی: فعال کردن مجدد
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("room_reactivate_"))
async def reactivate_ad(callback: types.CallbackQuery):
    """فعال کردن مجدد آگهی"""
    
    ad_id = int(callback.data.replace("room_reactivate_", ""))
    
    all_ads = await load_roommates()
    
    for ad in all_ads:
        if ad["id"] == ad_id and ad.get("user_id") == callback.from_user.id:
            # بررسی محدودیت تعداد
            user_active = sum(
                1 for a in all_ads
                if a.get("user_id") == callback.from_user.id
                and a.get("active")
                and a.get("status") == "approved"
                and not a.get("is_found")
                and a["id"] != ad_id
            )
            
            if user_active >= MAX_ADS_PER_USER:
                await callback.answer(
                    f"⚠️ حداکثر {MAX_ADS_PER_USER} آگهی فعال مجاز است!",
                    show_alert=True
                )
                return
            
            ad["active"] = True
            ad["is_found"] = False
            ad["expired"] = False
            # تمدید تاریخ
            ad["date"] = datetime.now().strftime("%Y-%m-%d")
            ad["renewal_count"] = ad.get("renewal_count", 0) + 1
            
            await save_json("roommates", all_ads)
            
            await callback.answer("✅ آگهی فعال شد!", show_alert=True)
            
            callback.data = f"room_manage_{ad_id}"
            await manage_ad(callback)
            return
    
    await callback.answer("⚠️ خطا", show_alert=True)


# ───────────────────────────────────────────────────────────────────
# عملیات روی آگهی: تمدید
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("room_renew_"))
async def renew_ad(callback: types.CallbackQuery):
    """تمدید آگهی"""
    
    ad_id = int(callback.data.replace("room_renew_", ""))
    
    all_ads = await load_roommates()
    
    for ad in all_ads:
        if ad["id"] == ad_id and ad.get("user_id") == callback.from_user.id:
            ad["date"] = datetime.now().strftime("%Y-%m-%d")
            ad["renewal_count"] = ad.get("renewal_count", 0) + 1
            ad["expired"] = False
            
            await save_json("roommates", all_ads)
            
            await callback.answer(
                f"🔄 آگهی برای {EXPIRATION_DAYS} روز دیگر تمدید شد!",
                show_alert=True
            )
            
            callback.data = f"room_manage_{ad_id}"
            await manage_ad(callback)
            return
    
    await callback.answer("⚠️ خطا", show_alert=True)


# ───────────────────────────────────────────────────────────────────
# عملیات روی آگهی: حذف
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("room_delete_"))
async def delete_ad_confirm(callback: types.CallbackQuery):
    """تأیید حذف آگهی"""
    
    ad_id = int(callback.data.replace("room_delete_", ""))
    
    text = (
        "🗑 <b>حذف آگهی</b>\n\n"
        f"⚠️ آیا مطمئن هستید که می‌خواهید آگهی #{ad_id} را حذف کنید؟\n\n"
        "❗ این عمل قابل بازگشت نیست!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [
            InlineKeyboardButton(
                text="✅ بله، حذف کن",
                callback_data=f"room_delete_confirm_{ad_id}"
            ),
            InlineKeyboardButton(
                text="❌ خیر، برگرد",
                callback_data=f"room_manage_{ad_id}"
            )
        ]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("room_delete_confirm_"))
async def delete_ad_execute(callback: types.CallbackQuery):
    """اجرای حذف آگهی"""
    
    ad_id = int(callback.data.replace("room_delete_confirm_", ""))
    
    all_ads = await load_roommates()
    
    # پیدا کردن و حذف
    new_ads = []
    deleted = False
    
    for ad in all_ads:
        if ad["id"] == ad_id and ad.get("user_id") == callback.from_user.id:
            # حذف عکس‌ها
            if ad.get("photo_path") and os.path.exists(ad["photo_path"]):
                try:
                    os.remove(ad["photo_path"])
                except:
                    pass
            
            for photo in ad.get("photos", []):
                if os.path.exists(photo):
                    try:
                        os.remove(photo)
                    except:
                        pass
            
            deleted = True
        else:
            new_ads.append(ad)
    
    if deleted:
        await save_json("roommates", new_ads)
        await callback.answer("🗑 آگهی حذف شد!", show_alert=True)
    else:
        await callback.answer("⚠️ خطا در حذف", show_alert=True)
    
    # بازگشت به لیست
    callback.data = "room_my_ads"
    await show_my_ads(callback)


# ───────────────────────────────────────────────────────────────────
# ویرایش آگهی
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("room_edit_"))
async def edit_ad_menu(callback: types.CallbackQuery, state: FSMContext):
    """منوی ویرایش آگهی"""
    
    ad_id = int(callback.data.replace("room_edit_", ""))
    
    all_ads = await load_roommates()
    ad = next((a for a in all_ads if a["id"] == ad_id), None)
    
    if not ad or ad.get("user_id") != callback.from_user.id:
        await callback.answer("⚠️ آگهی یافت نشد!", show_alert=True)
        return
    
    await state.update_data(editing_ad_id=ad_id)
    
    text = (
        f"✏️ <b>ویرایش آگهی #{ad_id}</b>\n\n"
        "کدام فیلد را می‌خواهید ویرایش کنید؟"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text=f"💰 اجاره ({ad.get('budget')}€)", callback_data="edit_field_budget")],
        [InlineKeyboardButton(text=f"📍 منطقه ({ad.get('area')})", callback_data="edit_field_area")],
        [InlineKeyboardButton(text=f"📐 متراژ ({ad.get('house_size')}m²)", callback_data="edit_field_size")],
        [InlineKeyboardButton(text="📝 توضیحات", callback_data="edit_field_desc")],
        [InlineKeyboardButton(text="📅 تاریخ آزاد", callback_data="edit_field_available")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"room_manage_{ad_id}")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("edit_field_"))
async def edit_field_start(callback: types.CallbackQuery, state: FSMContext):
    """شروع ویرایش یک فیلد"""
    
    field = callback.data.replace("edit_field_", "")
    
    await state.update_data(editing_field=field)
    await state.set_state(RoommateState.editing_new_value)
    
    prompts = {
        "budget": "💰 اجاره جدید (یورو) را وارد کنید:",
        "area": "📍 منطقه جدید را وارد کنید:",
        "size": "📐 متراژ جدید (متر) را وارد کنید:",
        "desc": "📝 توضیحات جدید را وارد کنید:",
        "available": "📅 تاریخ آزاد جدید را وارد کنید:"
    }
    
    text = prompts.get(field, "مقدار جدید را وارد کنید:")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="❌ لغو", callback_data="edit_cancel")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.message(RoommateState.editing_new_value)
async def edit_field_process(message: types.Message, state: FSMContext):
    """پردازش مقدار جدید فیلد"""
    
    data = await state.get_data()
    ad_id = data.get("editing_ad_id")
    field = data.get("editing_field")
    new_value = message.text.strip()
    
    all_ads = await load_roommates()
    
    for ad in all_ads:
        if ad["id"] == ad_id and ad.get("user_id") == message.from_user.id:
            # اعتبارسنجی و ذخیره
            if field == "budget":
                budget = safe_int(new_value, 0)
                if budget < MIN_BUDGET or budget > MAX_BUDGET:
                    await message.reply(f"⚠️ اجاره باید بین {MIN_BUDGET} و {MAX_BUDGET} یورو باشد.")
                    return
                ad["budget"] = str(budget)
            
            elif field == "area":
                if len(new_value) < 2:
                    await message.reply("⚠️ منطقه باید حداقل 2 کاراکتر باشد.")
                    return
                ad["area"] = new_value
            
            elif field == "size":
                size = safe_int(new_value, 0)
                if size < 5 or size > 500:
                    await message.reply("⚠️ متراژ باید بین 5 و 500 متر باشد.")
                    return
                ad["house_size"] = str(size)
            
            elif field == "desc":
                if len(new_value) < 20 or len(new_value) > MAX_DESC_LENGTH:
                    await message.reply(f"⚠️ توضیحات باید بین 20 و {MAX_DESC_LENGTH} کاراکتر باشد.")
                    return
                ad["desc"] = new_value
            
            elif field == "available":
                ad["available_from"] = new_value
            
            await save_json("roommates", all_ads)
            
            await state.clear()
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
                [InlineKeyboardButton(text="✏️ ویرایش بیشتر", callback_data=f"room_edit_{ad_id}")],
                [InlineKeyboardButton(text="🔙 مدیریت آگهی", callback_data=f"room_manage_{ad_id}")]
            ])
            
            await message.answer(
                "✅ <b>تغییرات ذخیره شد!</b>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            return
    
    await state.clear()
    await message.reply("⚠️ خطا در ذخیره تغییرات")


@router.callback_query(F.data == "edit_cancel")
async def edit_cancel(callback: types.CallbackQuery, state: FSMContext):
    """لغو ویرایش"""
    
    data = await state.get_data()
    ad_id = data.get("editing_ad_id", 0)
    
    await state.clear()
    
    if ad_id:
        callback.data = f"room_manage_{ad_id}"
        await manage_ad(callback)
    else:
        callback.data = "room_my_ads"
        await show_my_ads(callback)


# ───────────────────────────────────────────────────────────────────
# سیستم هشدار (Alert)
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_alert_menu")
async def alert_menu(callback: types.CallbackQuery, state: FSMContext):
    """منوی تنظیم هشدار"""
    
    user_id = callback.from_user.id
    
    # بارگذاری هشدارهای کاربر
    alerts = await load_json("room_alerts")
    user_alerts = [a for a in alerts if a.get("user_id") == user_id]
    
    text = (
        "🔔 <b>تنظیم هشدار آگهی</b>\n\n"
        "وقتی آگهی مناسب ثبت شد، به شما اطلاع می‌دهیم!\n\n"
    )
    
    if user_alerts:
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"<b>هشدارهای فعال شما:</b> {len(user_alerts)}\n\n"
        
        for i, alert in enumerate(user_alerts, 1):
            text += f"{i}. جنسیت: {alert.get('gender', 'همه')}"
            if alert.get("budget") != "all":
                text += f" | ≤{alert.get('budget')}€"
            if alert.get("area") != "all":
                text += f" | {alert.get('area')}"
            text += "\n"
        
        text += "\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text="➕ افزودن هشدار جدید", callback_data="alert_add_start")],
        [InlineKeyboardButton(text="🗑 حذف همه هشدارها", callback_data="alert_delete_all")] if user_alerts else [],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="roommate")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(F.data == "alert_add_start")
async def alert_add_start(callback: types.CallbackQuery, state: FSMContext):
    """شروع افزودن هشدار"""
    
    await state.set_state(RoommateState.alert_gender)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [
            InlineKeyboardButton(text="👨 آقا", callback_data="alert_gender_آقا"),
            InlineKeyboardButton(text="👩 خانم", callback_data="alert_gender_خانم")
        ],
        [InlineKeyboardButton(text="👫 هر دو", callback_data="alert_gender_all")],
        [InlineKeyboardButton(text="❌ لغو", callback_data="room_alert_menu")]
    ])
    
    await callback.message.edit_text(
        "🔔 <b>تنظیم هشدار جدید</b>\n\n"
        "👤 جنسیت مورد نظر:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("alert_gender_"), RoommateState.alert_gender)
async def alert_select_gender(callback: types.CallbackQuery, state: FSMContext):
    """انتخاب جنسیت برای هشدار"""
    
    gender = callback.data.replace("alert_gender_", "")
    await state.update_data(alert_gender=gender)
    await state.set_state(RoommateState.alert_budget)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [
            InlineKeyboardButton(text="≤ 300€", callback_data="alert_budget_300"),
            InlineKeyboardButton(text="≤ 400€", callback_data="alert_budget_400")
        ],
        [
            InlineKeyboardButton(text="≤ 500€", callback_data="alert_budget_500"),
            InlineKeyboardButton(text="≤ 600€", callback_data="alert_budget_600")
        ],
        [InlineKeyboardButton(text="∞ بدون محدودیت", callback_data="alert_budget_all")],
        [InlineKeyboardButton(text="❌ لغو", callback_data="room_alert_menu")]
    ])
    
    await callback.message.edit_text(
        "💰 <b>سقف بودجه:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("alert_budget_"), RoommateState.alert_budget)
async def alert_select_budget(callback: types.CallbackQuery, state: FSMContext):
    """انتخاب بودجه و ذخیره هشدار"""
    
    budget = callback.data.replace("alert_budget_", "")
    
    data = await state.get_data()
    gender = data.get("alert_gender", "all")
    
    # ذخیره هشدار
    alerts = await load_json("room_alerts")
    
    new_alert = {
        "user_id": callback.from_user.id,
        "gender": gender,
        "budget": budget,
        "area": "all",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    alerts.append(new_alert)
    await save_json("room_alerts", alerts)
    
    await state.clear()
    
    await callback.answer("✅ هشدار ذخیره شد!", show_alert=True)
    
    callback.data = "room_alert_menu"
    await alert_menu(callback, state)


@router.callback_query(F.data == "alert_delete_all")
async def alert_delete_all(callback: types.CallbackQuery):
    """حذف همه هشدارها"""
    
    user_id = callback.from_user.id
    
    alerts = await load_json("room_alerts")
    alerts = [a for a in alerts if a.get("user_id") != user_id]
    await save_json("room_alerts", alerts)
    
    await callback.answer("🗑 همه هشدارها حذف شد!", show_alert=True)
    
    callback.data = "room_alert_menu"
    await alert_menu(callback, None)


async def process_alerts_for_new_ad(bot: Bot, new_ad: dict):
    """بررسی و ارسال هشدار برای آگهی جدید"""
    
    alerts = await load_json("room_alerts")
    
    for alert in alerts:
        # بررسی تطابق
        if alert.get("user_id") == new_ad.get("user_id"):
            continue  # به خود آگهی‌دهنده هشدار نده
        
        # فیلتر جنسیت
        if alert.get("gender") != "all":
            if new_ad.get("gender") not in [alert["gender"], "فرقی ندارد"]:
                continue
        
        # فیلتر بودجه
        if alert.get("budget") != "all":
            if safe_int(new_ad.get("budget", 0)) > int(alert["budget"]):
                continue
        
        # فیلتر منطقه
        if alert.get("area") != "all":
            if new_ad.get("area_key") != alert["area"]:
                continue
        
        # ارسال هشدار
        try:
            text = (
                "🔔 <b>آگهی جدید مطابق با هشدار شما!</b>\n\n"
                f"📍 منطقه: {new_ad.get('area')}\n"
                f"💰 اجاره: {new_ad.get('budget')}€\n"
                f"🚻 جنسیت: {new_ad.get('gender')}\n"
                f"📐 متراژ: {new_ad.get('house_size')}m²\n\n"
                "👇 برای مشاهده کلیک کنید:"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
                [InlineKeyboardButton(
                    text="👁 مشاهده آگهی",
                    callback_data=f"room_view_{new_ad['id']}_1"
                )]
            ])
            
            await bot.send_message(
                alert["user_id"],
                text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error sending alert: {e}")


# ───────────────────────────────────────────────────────────────────
# پنل ادمین
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_approve_"))
async def admin_approve_ad(callback: types.CallbackQuery):
    """تأیید آگهی توسط ادمین"""
    if callback.from_user.id not in settings.ADMIN_CHAT_IDS:
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    
    ad_id = str(callback.data.replace("adm_approve_", "")).strip()
    all_ads = await load_roommates()
    
    for ad in all_ads:
        if str(ad.get("id")) == str(ad_id):
            ad["status"] = "approved"
            ad["active"] = True
            ad["approved_by"] = callback.from_user.id
            ad["approved_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            await save_json("roommates", all_ads)
            
            # اطلاع به کاربر
            try:
                await callback.bot.send_message(
                    ad["user_id"],
                    f"✅ <b>آگهی شما تأیید شد!</b>\n\n"
                    f"🆔 شماره: #{ad_id}\n"
                    f"📍 {ad.get('area')} | {ad.get('budget')}€\n\n"
                    "آگهی شما اکنون در لیست نمایش داده می‌شود.",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Failed to notify user: {e}")
            
            # ارسال هشدار به کاربران
            await process_alerts_for_new_ad(callback.bot, ad)
            
            # بروزرسانی پیام ادمین
            try:
                if callback.message.caption:
                    new_caption = callback.message.caption + "\n\n✅ تأیید شد توسط ادمین"
                    await callback.message.edit_caption(caption=new_caption, parse_mode="HTML")
                elif callback.message.text:
                    new_text = callback.message.text + "\n\n✅ تأیید شد توسط ادمین"
                    await callback.message.edit_text(new_text, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Could not edit message: {e}")
            
            await callback.answer("✅ آگهی با موفقیت تأیید شد!")
            return
    
    await callback.answer("⚠️ آگهی یافت نشد!", show_alert=True)


@router.callback_query(F.data.startswith("adm_premium_"))
async def admin_approve_premium(callback: types.CallbackQuery):
    """تأیید آگهی به عنوان ویژه"""
    if callback.from_user.id not in settings.ADMIN_CHAT_IDS:
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    
    ad_id = str(callback.data.replace("adm_premium_", "")).strip()
    all_ads = await load_roommates()
    
    for ad in all_ads:
        if str(ad.get("id")) == str(ad_id):
            ad["status"] = "approved"
            ad["active"] = True
            ad["is_premium"] = True
            ad["approved_by"] = callback.from_user.id
            ad["approved_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            await save_json("roommates", all_ads)
            
            try:
                await callback.bot.send_message(
                    ad["user_id"],
                    f"🌟 <b>آگهی شما به عنوان ویژه تأیید شد!</b>\n\n"
                    f"🆔 شماره: #{ad_id}\n"
                    "آگهی شما با اولویت بالا و ستاره‌دار در بالای لیست نمایش داده می‌شود!",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Failed to notify user: {e}")
            
            await process_alerts_for_new_ad(callback.bot, ad)
            
            try:
                if callback.message.caption:
                    new_caption = callback.message.caption + "\n\n🌟 تأیید ویژه شد"
                    await callback.message.edit_caption(caption=new_caption, parse_mode="HTML")
                elif callback.message.text:
                    new_text = callback.message.text + "\n\n🌟 تأیید ویژه شد"
                    await callback.message.edit_text(new_text, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Could not edit message: {e}")
            
            await callback.answer("🌟 تأیید ویژه ثبت شد!")
            return
    
    await callback.answer("⚠️ آگهی یافت نشد!", show_alert=True)


@router.callback_query(F.data.startswith("adm_reject_"))
async def admin_reject_ad(callback: types.CallbackQuery):
    """رد آگهی توسط ادمین"""
    if callback.from_user.id not in settings.ADMIN_CHAT_IDS:
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    
    ad_id = str(callback.data.replace("adm_reject_", "")).strip()
    all_ads = await load_roommates()
    
    for ad in all_ads:
        if str(ad.get("id")) == str(ad_id):
            ad["status"] = "rejected"
            ad["active"] = False
            ad["rejected_by"] = callback.from_user.id
            
            await save_json("roommates", all_ads)
            
            try:
                await callback.bot.send_message(
                    ad["user_id"],
                    f"❌ <b>آگهی شما رد شد</b>\n\n"
                    f"🆔 شماره: #{ad_id}\n\n"
                    "لطفاً مشخصات یا عکس‌ها را بررسی کرده و مجدد ثبت کنید.",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Failed to notify user: {e}")
            
            try:
                if callback.message.caption:
                    new_caption = callback.message.caption + "\n\n❌ رد شد توسط ادمین"
                    await callback.message.edit_caption(caption=new_caption, parse_mode="HTML")
                elif callback.message.text:
                    new_text = callback.message.text + "\n\n❌ رد شد توسط ادمین"
                    await callback.message.edit_text(new_text, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Could not edit message: {e}")
            
            await callback.answer("❌ آگهی رد شد.")
            return
            
    await callback.answer("⚠️ آگهی یافت نشد!", show_alert=True)


@router.callback_query(F.data.startswith("adm_delete_"))
async def admin_delete_ad(callback: types.CallbackQuery):
    """حذف آگهی توسط ادمین"""
    
    if callback.from_user.id not in settings.ADMIN_CHAT_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    
    ad_id = int(callback.data.replace("adm_delete_", ""))
    
    all_ads = await load_roommates()
    
    deleted_ad = None
    new_ads = []
    
    for ad in all_ads:
        if ad["id"] == ad_id:
            deleted_ad = ad
        else:
            new_ads.append(ad)
    
    if deleted_ad:
        await save_json("roommates", new_ads)
        
        try:
            await callback.bot.send_message(
                deleted_ad["user_id"],
                f"🗑 <b>آگهی شما حذف شد</b>\n\n"
                f"🆔 شماره: #{ad_id}\n"
                "دلیل: نقض قوانین",
                parse_mode="HTML"
            )
        except:
            pass
        
        await callback.answer("🗑 حذف شد!")
    else:
        await callback.answer("⚠️ یافت نشد!", show_alert=True)


@router.callback_query(F.data.startswith("adm_dismiss_report_"))
async def admin_dismiss_report(callback: types.CallbackQuery):
    """رد گزارش تخلف"""
    
    if callback.from_user.id not in settings.ADMIN_CHAT_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    
    ad_id = int(callback.data.replace("adm_dismiss_report_", ""))
    
    all_ads = await load_roommates()
    
    for ad in all_ads:
        if ad["id"] == ad_id:
            ad["reports"] = []
            await save_json("roommates", all_ads)
            break
    
    try:
        new_text = callback.message.text + "\n\n✅ گزارش رد شد"
        await callback.message.edit_text(new_text, parse_mode="HTML")
    except:
        pass
    
    await callback.answer("✅ گزارش رد شد!")


# ───────────────────────────────────────────────────────────────────
# داشبورد ادمین
# ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "room_admin_dashboard")
async def admin_dashboard(callback: types.CallbackQuery):
    """داشبورد ادمین"""
    
    if callback.from_user.id not in settings.ADMIN_CHAT_IDS:
        await callback.answer("⛔", show_alert=True)
        return
    
    all_ads = await load_roommates()
    
    total = len(all_ads)
    active = sum(1 for a in all_ads if a.get("active") and a.get("status") == "approved")
    pending = sum(1 for a in all_ads if a.get("status") == "pending")
    rejected = sum(1 for a in all_ads if a.get("status") == "rejected")
    found = sum(1 for a in all_ads if a.get("is_found"))
    premium = sum(1 for a in all_ads if a.get("is_premium"))
    
    # آگهی‌های با گزارش
    reported = sum(1 for a in all_ads if a.get("reports"))
    
    # کاربران یکتا
    unique_users = len(set(a.get("user_id") for a in all_ads))
    
    text = (
        "📊 <b>داشبورد ادمین</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 کل آگهی‌ها: <b>{total}</b>\n"
        f"   ✅ فعال: {active}\n"
        f"   ⏳ در انتظار: {pending}\n"
        f"   ❌ رد شده: {rejected}\n"
        f"   🎉 موفق: {found}\n"
        f"   🌟 ویژه: {premium}\n\n"
        f"🚨 گزارش شده: {reported}\n"
        f"👥 کاربران: {unique_users}\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 مچ‌میکر هوشمند (AI Match)", callback_data="ai_matchmaker")],
        [InlineKeyboardButton(text=f"⏳ در انتظار ({pending})", callback_data="adm_list_pending")],
        [InlineKeyboardButton(text=f"🚨 گزارش شده ({reported})", callback_data="adm_list_reported")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="roommate")]
    ])
    
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════
# پایان بخش 5 و پایان فایل
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ai_matchmaker")
async def ai_matchmaker_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🤖 <b>مچ‌میکر هوشمند هم‌اتاقی</b>\nلطفاً ۳ ویژگی مهم خود و هم‌اتاقی ایده‌آلتان را بنویسید:\nمثال: من زود می‌خوابم، سیگاری نیستم و خیلی تمیزم.", parse_mode="HTML")
    await state.set_state("waiting_for_match_traits")

@router.message(StateFilter("waiting_for_match_traits"))
async def process_matchmaker(message: types.Message, state: FSMContext):
    user_traits = message.text
    loading = await message.answer("🔄 هوش مصنوعی در حال بررسی تمام پروفایل‌ها و یافتن بهترین هم‌اتاقی برای شماست...")
    
    roommates = await load_roommates()
    if not roommates:
        await loading.edit_text("هیچ آگهی هم‌اتاقی ثبت نشده است.")
        await state.clear()
        return
        
    # Construct a prompt for AI
    profiles = ""
    for r in roommates[:10]: # Check last 10 for demo purposes
        profiles += f"Profile ID {r['id']}: {r['description']}\n"
        
    prompt = f"من این ویژگی‌ها را دارم: {user_traits}\nدر بین پروفایل‌های زیر، بهترین هم‌اتاقی را برای من پیدا کن و درصد تطابق را بگو و دلیلش را توضیح بده:\n\n{profiles}"
    
    try:
        from services.ai_service import ai_service
        response = await ai_service.chat(prompt, context="student_assistant")
        await loading.edit_text(f"🎯 <b>نتیجه مچ‌میکینگ هوش مصنوعی:</b>\n\n{response.text}", parse_mode="HTML")
    except Exception as e:
        await loading.edit_text(f"⚠️ خطا در ارتباط با هوش مصنوعی.")
        
    await state.clear()
