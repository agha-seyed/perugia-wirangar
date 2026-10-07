# handlers/places_handler.py - راهنمای پروجا و دوربین زنده (نسخه نهایی کامل)

import json
import os
from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.cmd_start import get_text, get_user_lang

router = Router()

# ==================== تنظیمات ====================

# لینک دوربین زنده
LIVE_CAM_URL = "https://www.youtube.com/watch?v=8TZ8YRt9nYc"

# لینک گوگل مپ تور یک‌روزه (اصلاح شده)
TOUR_MAP_URL = "https://www.google.com/maps/dir/Piazza+IV+Novembre,+Perugia/Rocca+Paolina/Corso+Vannucci/Giardini+Carducci/Arco+Etrusco/@43.1115,12.388,15z"

# مسیر فایل نظرات
DATA_DIR = "data"
REVIEWS_JSON = os.path.join(DATA_DIR, "places_reviews.json")


# ==================== States ====================

class ReviewState(StatesGroup):
    waiting_for_place = State()
    waiting_for_review = State()
    waiting_for_rating = State()


# ==================== توابع کمکی ====================

def ensure_data_dir():
    """اطمینان از وجود پوشه data"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


async def load_reviews() -> dict:
    """بارگذاری نظرات از دیتابیس با پشتیبانی از کالکشن‌های اختصاصی"""
    try:
        from database import db_manager
        if db_manager.reviews is not None:
            items = await db_manager.reviews.find({}, {"_id": 0}).to_list(length=500)
            if items:
                return {r.get("review_id", f"{r.get('place')}_{r.get('user_id')}"): r for r in items}
        if db_manager.db is not None:
            doc = await db_manager.db["json_store"].find_one({"name": "places_reviews"}, {"_id": 0})
            if doc and "data" in doc:
                return doc["data"]
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error loading reviews: {e}")
    return {}


async def save_reviews(reviews: dict) -> bool:
    """ذخیره نظرات در دیتابیس"""
    try:
        from database import db_manager
        if db_manager.reviews is not None:
            for rev in reviews.values():
                place = rev.get("place", "")
                user_id = rev.get("user_id", 0)
                await db_manager.save_place_review(place, user_id, rev)
        if db_manager.db is not None:
            await db_manager.db["json_store"].update_one(
                {"name": "places_reviews"},
                {"$set": {"data": reviews}},
                upsert=True
            )
            return True
        return False
    except Exception as e:
        return False


def get_star_rating(rating: int) -> str:
    """تبدیل عدد به ستاره"""
    return "⭐" * rating + "☆" * (5 - rating)


async def get_average_rating(place_name: str) -> tuple:
    """محاسبه میانگین امتیاز یک مکان"""
    reviews = await load_reviews()
    ratings = []
    
    for review in reviews.values():
        if review.get("place", "").lower() == place_name.lower():
            if "rating" in review:
                ratings.append(review["rating"])
    
    if ratings:
        avg = sum(ratings) / len(ratings)
        return round(avg, 1), len(ratings)
    return 0, 0


# ==================== دیتابیس مکان‌ها ====================


import os
import json

def load_categories():
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "places.json")
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error loading places.json: {e}")
        return {}

CATEGORIES = load_categories()



# ==================== منوی اصلی ====================

@router.message(Command("places"))
@router.callback_query(F.data == "places")
async def show_places_main(event: types.Message | types.CallbackQuery, state: FSMContext):
    """نمایش منوی اصلی راهنمای پروجا"""
    
    # پاک کردن state قبلی
    await state.clear()
    
    user_id = event.from_user.id
    lang = get_user_lang(user_id)
    def t(key, default): return get_text(lang, key, default)
    
    # محاسبه تعداد کل مکان‌ها
    total_places = sum(len(cat["places"]) for cat in CATEGORIES.values())
    
    text = (
        t("places_main_title", "📸 <b>راهنمای کامل پروجا</b>") + "\n\n" +
        t("places_main_desc", f"🗺️ {total_places} مکان دیدنی در ۵ دسته‌بندی").replace("{total}", str(total_places)) + "\n" +
        "━━━━━━━━━━━━━━━━━━━━━\n\n" +
        t("places_live_cam_text", f"🔴 <b>دوربین زنده ۲۴ ساعته میدان اصلی:</b>\n<a href='{LIVE_CAM_URL}'>▶️ کلیک کنید و پروجا را زنده ببینید!</a>").replace("{url}", LIVE_CAM_URL) + "\n\n" +
        "━━━━━━━━━━━━━━━━━━━━━\n\n" +
        t("places_categories_title", "📂 <b>دسته‌بندی‌ها:</b>")
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t("places_live_cam_btn", "🔴 دوربین زنده پروجا"), 
            url=LIVE_CAM_URL
        )],
        [InlineKeyboardButton(
            text=t("places_cat_historical", "🏛️ تاریخی") + f" ({len(CATEGORIES['historical']['places'])})", 
            callback_data="cat_historical"
        )],
        [InlineKeyboardButton(
            text=t("places_cat_nature", "🌿 طبیعت") + f" ({len(CATEGORIES['nature']['places'])})", 
            callback_data="cat_nature"
        )],
        [InlineKeyboardButton(
            text=t("places_cat_culture", "🎨 موزه‌ها") + f" ({len(CATEGORIES['culture']['places'])})", 
            callback_data="cat_culture"
        )],
        [InlineKeyboardButton(
            text=t("places_cat_food_fun", "🍴 غذا و تفریح") + f" ({len(CATEGORIES['food_fun']['places'])})", 
            callback_data="cat_food_fun"
        )],
        [InlineKeyboardButton(
            text=t("places_cat_university", "🎓 نقاط دانشگاهی") + f" ({len(CATEGORIES['university']['places'])})", 
            callback_data="cat_university"
        )],
        [
            InlineKeyboardButton(text=t("places_tour_day", "🗺️ تور یک روزه"), callback_data="tour_day"),
            InlineKeyboardButton(text=t("places_filter_price", "💰 فیلتر قیمت"), callback_data="filter_price")
        ],
        [
            InlineKeyboardButton(text=t("places_reviews", "⭐ نظرات"), callback_data="show_reviews"),
            InlineKeyboardButton(text=t("places_add_review", "✍️ ثبت نظر"), callback_data="add_review")
        ],
        [InlineKeyboardButton(
            text=t("back_to_menu", "🏠 بازگشت به منوی اصلی"), 
            callback_data="main_menu"
        )]
    ])
    
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(
            text, 
            reply_markup=keyboard, 
            parse_mode="HTML", 
            disable_web_page_preview=False
        )
        await event.answer()
    else:
        await event.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=False
        )


# ==================== نمایش دسته‌بندی ====================

@router.callback_query(F.data.startswith("cat_"))
async def show_category(callback: types.CallbackQuery):
    """نمایش مکان‌های یک دسته‌بندی"""
    
    cat_key = callback.data.replace("cat_", "")
    category = CATEGORIES.get(cat_key)
    
    if not category:
        await callback.answer("❌ دسته‌بندی یافت نشد!", show_alert=True)
        return
    
    text = (
        f"{category['emoji']} <b>{category['title']}</b>\n"
        f"📝 {category['description']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    # لیست مکان‌ها با دکمه برای جزئیات
    buttons = []
    
    for i, place in enumerate(category["places"], 1):
        avg_rating, count = await get_average_rating(place["name"])
        rating_text = f" ⭐{avg_rating}" if count > 0 else ""
        
        text += f"{i}. <b>{place['name']}</b>{rating_text}\n"
        text += f"   └ {place['name_fa']}\n\n"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"📍 {place['name']}", 
                callback_data=f"place_{place['id']}"
            )
        ])
    
    # دکمه‌های پایین
    buttons.append([
        InlineKeyboardButton(text="🗺️ همه در نقشه", callback_data=f"map_all_{cat_key}")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="places")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== نمایش جزئیات مکان ====================

@router.callback_query(F.data.startswith("place_"))
async def show_place_details(callback: types.CallbackQuery):
    """نمایش جزئیات کامل یک مکان"""
    
    place_id = callback.data.replace("place_", "")
    
    # پیدا کردن مکان
    place = None
    cat_key = None
    
    for key, category in CATEGORIES.items():
        for p in category["places"]:
            if p["id"] == place_id:
                place = p
                cat_key = key
                break
        if place:
            break
    
    if not place:
        await callback.answer("❌ مکان یافت نشد!", show_alert=True)
        return
    
    # محاسبه امتیاز
    avg_rating, review_count = await get_average_rating(place["name"])
    rating_display = get_star_rating(round(avg_rating)) if review_count > 0 else "هنوز امتیازی ثبت نشده"
    
    text = (
        f"📍 <b>{place['name']}</b>\n"
        f"🏷️ {place['name_fa']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 <b>توضیحات:</b>\n{place['desc']}\n\n"
        f"🕐 <b>ساعت کاری:</b> {place['hours']}\n"
        f"💰 <b>هزینه:</b> {place['cost']}\n"
        f"🎓 <b>تخفیف دانشجویی:</b> {place['student_discount']}\n\n"
        f"🍂 <b>بهترین فصل:</b> {place['best_season']}\n"
        f"⏰ <b>بهترین زمان:</b> {place['best_time']}\n"
        f"♿ <b>دسترسی:</b> {place['accessibility']}\n\n"
    )
    
    # اطلاعات تماس
    if place['phone'] != "-":
        text += f"📞 <b>تماس:</b> {place['phone']}\n"
    if place['website'] != "-":
        text += f"🌐 <b>وبسایت:</b> {place['website']}\n"
    
    text += "\n"
    
    # نکات
    if place.get("tips"):
        text += "💡 <b>نکات مهم:</b>\n"
        for tip in place["tips"]:
            text += f"   • {tip}\n"
        text += "\n"
    
    # امتیاز
    text += "━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"⭐ <b>امتیاز:</b> {rating_display}"
    if review_count > 0:
        text += f" ({review_count} نظر)"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🗺️ نمایش در گوگل مپ", 
            url=place['map']
        )],
        [InlineKeyboardButton(
            text="📍 ارسال موقعیت", 
            callback_data=f"sendloc_{place['id']}"
        )],
        [
            InlineKeyboardButton(
                text="⭐ ثبت امتیاز", 
                callback_data=f"rate_{place['id']}"
            ),
            InlineKeyboardButton(
                text="💬 نظرات", 
                callback_data=f"reviews_{place['id']}"
            )
        ],
        [InlineKeyboardButton(
            text="🔙 بازگشت", 
            callback_data=f"cat_{cat_key}"
        )]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML", 
        disable_web_page_preview=True
    )
    await callback.answer()


# ==================== ارسال موقعیت ====================

@router.callback_query(F.data.startswith("sendloc_"))
async def send_location(callback: types.CallbackQuery):
    """ارسال موقعیت مکان به صورت Location تلگرام"""
    
    place_id = callback.data.replace("sendloc_", "")
    
    # پیدا کردن مکان
    place = None
    for category in CATEGORIES.values():
        for p in category["places"]:
            if p["id"] == place_id:
                place = p
                break
        if place:
            break
    
    if not place or "coordinates" not in place:
        await callback.answer("❌ موقعیت یافت نشد!", show_alert=True)
        return
    
    lat, lon = place["coordinates"]
    
    await callback.message.answer_location(
        latitude=lat,
        longitude=lon
    )
    await callback.message.answer(
        f"📍 <b>{place['name']}</b>\n{place['name_fa']}",
        parse_mode="HTML"
    )
    await callback.answer("📍 موقعیت ارسال شد!")


# ==================== تور یک روزه ====================

@router.callback_query(F.data == "tour_day")
async def show_tour_day(callback: types.CallbackQuery):
    """نمایش برنامه تور یک‌روزه"""
    
    text = (
        "🗺️ <b>تور پیاده‌روی یک روزه در پروجا</b>\n\n"
        "مسیر طلایی برای کشف بهترین‌های شهر! ✨\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "🌅 <b>صبح (۰۹:۰۰-۱۲:۰۰)</b>\n"
        "━━━━━━━━━━\n"
        "1️⃣ <b>Piazza IV Novembre</b>\n"
        "   └ شروع با قهوه در Caffè Sandri\n"
        "   └ عکس با Fontana Maggiore\n\n"
        
        "2️⃣ <b>Cattedrale San Lorenzo</b>\n"
        "   └ بازدید از کلیسا و موزه\n\n"
        
        "3️⃣ <b>Corso Vannucci</b>\n"
        "   └ پیاده‌روی و تماشای مغازه‌ها\n\n"
        
        "🍝 <b>ناهار (۱۲:۳۰-۱۴:۰۰)</b>\n"
        "━━━━━━━━━━\n"
        "4️⃣ <b>Via delle Volte</b>\n"
        "   └ غذای اومبریایی اصیل\n"
        "   └ Umbricelli با ترافل محلی\n\n"
        
        "🏛️ <b>بعدازظهر (۱۴:۳۰-۱۷:۰۰)</b>\n"
        "━━━━━━━━━━\n"
        "5️⃣ <b>Rocca Paolina</b>\n"
        "   └ ماجراجویی در تونل‌های زیرزمینی\n\n"
        
        "6️⃣ <b>Galleria Nazionale</b>\n"
        "   └ شاهکارهای هنری رنسانس\n\n"
        
        "🌳 <b>عصر (۱۷:۰۰-۱۹:۰۰)</b>\n"
        "━━━━━━━━━━\n"
        "7️⃣ <b>Giardini Carducci</b>\n"
        "   └ استراحت و تماشای غروب\n\n"
        
        "8️⃣ <b>Arco Etrusco</b>\n"
        "   └ عکس در نور طلایی غروب\n\n"
        
        "🌙 <b>شب (۲۰:۰۰+)</b>\n"
        "━━━━━━━━━━\n"
        "9️⃣ <b>Corso Vannucci</b>\n"
        "   └ ژلاتو و Passeggiata شبانه!\n\n"
        
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏱️ <b>مدت:</b> ۸-۱۰ ساعت\n"
        "🚶 <b>مسافت:</b> ~۵ کیلومتر\n"
        "💰 <b>هزینه تقریبی:</b> ۲۵-۴۰ یورو\n"
        "👟 <b>کفش راحت فراموش نشود!</b>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🗺️ نمایش کل مسیر در گوگل مپ", 
            url=TOUR_MAP_URL
        )],
        [InlineKeyboardButton(
            text="📥 دانلود PDF مسیر", 
            callback_data="download_tour_pdf"
        )],
        [InlineKeyboardButton(
            text="🔙 بازگشت", 
            callback_data="places"
        )]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== فیلتر قیمت ====================

@router.callback_query(F.data == "filter_price")
async def filter_by_price(callback: types.CallbackQuery):
    """نمایش منوی فیلتر قیمت"""
    
    text = (
        "💰 <b>فیلتر مکان‌ها بر اساس هزینه</b>\n\n"
        "کدام دسته را می‌خواهید ببینید؟"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🆓 رایگان", 
            callback_data="price_free"
        )],
        [InlineKeyboardButton(
            text="💵 کم‌هزینه (تا ۵ یورو)", 
            callback_data="price_low"
        )],
        [InlineKeyboardButton(
            text="💶 متوسط (۵-۱۰ یورو)", 
            callback_data="price_medium"
        )],
        [InlineKeyboardButton(
            text="🔙 بازگشت", 
            callback_data="places"
        )]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("price_"))
async def show_filtered_places(callback: types.CallbackQuery):
    """نمایش مکان‌های فیلتر شده بر اساس قیمت"""
    
    filter_type = callback.data.replace("price_", "")
    
    # تعیین محدوده قیمت
    if filter_type == "free":
        min_price, max_price = 0, 0
        title = "🆓 مکان‌های رایگان"
    elif filter_type == "low":
        min_price, max_price = 0.01, 5
        title = "💵 مکان‌های کم‌هزینه (تا ۵ یورو)"
    else:  # medium
        min_price, max_price = 5, 10
        title = "💶 مکان‌های متوسط (۵-۱۰ یورو)"
    
    # جمع‌آوری مکان‌های مناسب
    filtered = []
    for cat_key, category in CATEGORIES.items():
        for place in category["places"]:
            cost = place.get("cost_value", 0)
            if filter_type == "free" and cost == 0:
                filtered.append((place, category["emoji"]))
            elif filter_type == "low" and 0 < cost <= 5:
                filtered.append((place, category["emoji"]))
            elif filter_type == "medium" and 5 < cost <= 10:
                filtered.append((place, category["emoji"]))
    
    text = f"<b>{title}</b>\n\n"
    
    if filtered:
        text += f"📍 {len(filtered)} مکان یافت شد:\n\n"
        buttons = []
        
        for place, emoji in filtered:
            text += f"{emoji} <b>{place['name']}</b>\n"
            text += f"   └ {place['cost']}\n\n"
            
            buttons.append([
                InlineKeyboardButton(
                    text=f"📍 {place['name']}", 
                    callback_data=f"place_{place['id']}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="filter_price")
        ])
    else:
        text += "❌ مکانی در این محدوده قیمت یافت نشد."
        buttons = [[
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="filter_price")
        ]]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== سیستم نظرات ====================

@router.callback_query(F.data == "add_review")
async def start_add_review(callback: types.CallbackQuery, state: FSMContext):
    """شروع فرآیند ثبت نظر"""
    
    # ساختن لیست مکان‌ها
    text = (
        "✍️ <b>ثبت نظر و تجربه شما</b>\n\n"
        "لطفاً مکان مورد نظر را انتخاب کنید:\n\n"
    )
    
    buttons = []
    for cat_key, category in CATEGORIES.items():
        for place in category["places"]:
            buttons.append([
                InlineKeyboardButton(
                    text=f"{category['emoji']} {place['name']}", 
                    callback_data=f"review_place_{place['id']}"
                )
            ])
    
    buttons.append([
        InlineKeyboardButton(text="❌ انصراف", callback_data="places")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("review_place_"))
async def select_place_for_review(callback: types.CallbackQuery, state: FSMContext):
    """انتخاب مکان برای ثبت نظر"""
    
    place_id = callback.data.replace("review_place_", "")
    
    # پیدا کردن نام مکان
    place_name = None
    for category in CATEGORIES.values():
        for p in category["places"]:
            if p["id"] == place_id:
                place_name = p["name"]
                break
        if place_name:
            break
    
    if not place_name:
        await callback.answer("❌ مکان یافت نشد!", show_alert=True)
        return
    
    # ذخیره در state
    await state.set_state(ReviewState.waiting_for_rating)
    await state.update_data(place_id=place_id, place_name=place_name)
    
    text = (
        f"⭐ <b>امتیاز شما به {place_name}:</b>\n\n"
        "لطفاً امتیاز ۱ تا ۵ را انتخاب کنید:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣", callback_data="rating_1"),
            InlineKeyboardButton(text="2️⃣", callback_data="rating_2"),
            InlineKeyboardButton(text="3️⃣", callback_data="rating_3"),
            InlineKeyboardButton(text="4️⃣", callback_data="rating_4"),
            InlineKeyboardButton(text="5️⃣", callback_data="rating_5"),
        ],
        [InlineKeyboardButton(text="❌ انصراف", callback_data="places")]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rating_"), ReviewState.waiting_for_rating)
async def receive_rating(callback: types.CallbackQuery, state: FSMContext):
    """دریافت امتیاز و درخواست متن نظر"""
    
    rating = int(callback.data.replace("rating_", ""))
    await state.update_data(rating=rating)
    await state.set_state(ReviewState.waiting_for_review)
    
    data = await state.get_data()
    place_name = data.get("place_name", "")
    
    text = (
        f"✅ امتیاز {get_star_rating(rating)} ثبت شد!\n\n"
        f"📝 <b>حالا نظر خود درباره {place_name} را بنویسید:</b>\n\n"
        "💡 می‌توانید تجربه، نکات یا پیشنهادات خود را بنویسید.\n"
        "(یا /skip برای رد کردن)"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ رد کردن (بدون نظر)", callback_data="skip_review_text")]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "skip_review_text", ReviewState.waiting_for_review)
async def skip_review_text(callback: types.CallbackQuery, state: FSMContext):
    """رد کردن متن نظر و ذخیره فقط امتیاز"""
    
    data = await state.get_data()
    await save_user_review(callback.from_user, data, None)
    await state.clear()
    
    await callback.message.edit_text(
        "✅ <b>امتیاز شما با موفقیت ثبت شد!</b>\n\n"
        "🙏 ممنون از مشارکت شما!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به راهنما", callback_data="places")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(ReviewState.waiting_for_review)
async def receive_review_text(message: types.Message, state: FSMContext):
    """دریافت متن نظر"""
    
    if message.text == "/skip":
        data = await state.get_data()
        await save_user_review(message.from_user, data, None)
        await state.clear()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به راهنما", callback_data="places")]
        ])
        
        await message.answer(
            "✅ <b>امتیاز شما ثبت شد!</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    # ذخیره نظر کامل
    data = await state.get_data()
    await save_user_review(message.from_user, data, message.text)
    await state.clear()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به راهنما", callback_data="places")]
    ])
    
    await message.answer(
        "✅ <b>نظر شما با موفقیت ثبت شد!</b>\n\n"
        "🙏 ممنون از اشتراک تجربه‌تان!\n"
        "نظر شما به دیگران کمک می‌کند.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def save_user_review(user, data: dict, review_text: str | None):
    """ذخیره نظر کاربر"""
    
    reviews = await load_reviews()
    
    review_id = f"{user.id}_{data['place_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    reviews[review_id] = {
        "user_id": user.id,
        "user_name": user.full_name,
        "place_id": data["place_id"],
        "place": data["place_name"],
        "rating": data["rating"],
        "text": review_text,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    await save_reviews(reviews)


# ==================== نمایش نظرات ====================

@router.callback_query(F.data == "show_reviews")
async def show_all_reviews(callback: types.CallbackQuery):
    """نمایش آخرین نظرات"""
    
    reviews = await load_reviews()
    
    if not reviews:
        text = (
            "💬 <b>نظرات کاربران</b>\n\n"
            "هنوز نظری ثبت نشده!\n"
            "اولین نفر باشید که تجربه خود را به اشتراک می‌گذارد."
        )
    else:
        text = "💬 <b>آخرین نظرات کاربران</b>\n\n"
        
        # مرتب‌سازی بر اساس تاریخ و نمایش ۱۰ تای آخر
        sorted_reviews = sorted(
            reviews.items(), 
            key=lambda x: x[1].get("date", ""), 
            reverse=True
        )[:10]
        
        for review_id, review in sorted_reviews:
            stars = get_star_rating(review.get("rating", 0))
            text += (
                f"📍 <b>{review.get('place', 'نامشخص')}</b>\n"
                f"   {stars}\n"
            )
            if review.get("text"):
                text += f"   💬 «{review['text'][:100]}»\n"
            text += f"   👤 {review.get('user_name', 'ناشناس')} | {review.get('date', '')}\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ ثبت نظر جدید", callback_data="add_review")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="places")]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reviews_"))
async def show_place_reviews(callback: types.CallbackQuery):
    """نمایش نظرات یک مکان خاص"""
    
    place_id = callback.data.replace("reviews_", "")
    
    # پیدا کردن نام مکان
    place_name = None
    cat_key = None
    for key, category in CATEGORIES.items():
        for p in category["places"]:
            if p["id"] == place_id:
                place_name = p["name"]
                cat_key = key
                break
        if place_name:
            break
    
    if not place_name:
        await callback.answer("❌ مکان یافت نشد!", show_alert=True)
        return
    
    reviews = await load_reviews()
    place_reviews = [
        r for r in reviews.values() 
        if r.get("place_id") == place_id
    ]
    
    avg_rating, count = await get_average_rating(place_name)
    
    text = f"💬 <b>نظرات درباره {place_name}</b>\n\n"
    
    if count > 0:
        text += f"⭐ میانگین امتیاز: {avg_rating}/5 ({count} نظر)\n\n"
        text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for review in place_reviews[-5:]:  # آخرین ۵ نظر
            stars = get_star_rating(review.get("rating", 0))
            text += f"{stars}\n"
            if review.get("text"):
                text += f"💬 «{review['text']}»\n"
            text += f"👤 {review.get('user_name', 'ناشناس')}\n"
            text += f"📅 {review.get('date', '')}\n\n"
    else:
        text += "هنوز نظری برای این مکان ثبت نشده.\n"
        text += "اولین نفر باشید! ⭐"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⭐ ثبت نظر", 
            callback_data=f"review_place_{place_id}"
        )],
        [InlineKeyboardButton(
            text="🔙 بازگشت به مکان", 
            callback_data=f"place_{place_id}"
        )]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rate_"))
async def quick_rate(callback: types.CallbackQuery, state: FSMContext):
    """امتیازدهی سریع به مکان"""
    
    place_id = callback.data.replace("rate_", "")
    
    # پیدا کردن نام مکان
    place_name = None
    for category in CATEGORIES.values():
        for p in category["places"]:
            if p["id"] == place_id:
                place_name = p["name"]
                break
        if place_name:
            break
    
    if not place_name:
        await callback.answer("❌ مکان یافت نشد!", show_alert=True)
        return
    
    await state.set_state(ReviewState.waiting_for_rating)
    await state.update_data(place_id=place_id, place_name=place_name)
    
    text = f"⭐ <b>امتیاز شما به {place_name}:</b>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣", callback_data="rating_1"),
            InlineKeyboardButton(text="2️⃣", callback_data="rating_2"),
            InlineKeyboardButton(text="3️⃣", callback_data="rating_3"),
            InlineKeyboardButton(text="4️⃣", callback_data="rating_4"),
            InlineKeyboardButton(text="5️⃣", callback_data="rating_5"),
        ],
        [InlineKeyboardButton(text="❌ انصراف", callback_data=f"place_{place_id}")]
    ])
    
    await callback.message.edit_text(
        text, 
        reply_markup=keyboard, 
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== نقشه همه مکان‌های یک دسته ====================

@router.callback_query(F.data.startswith("map_all_"))
async def show_all_on_map(callback: types.CallbackQuery):
    """ارسال موقعیت همه مکان‌های یک دسته"""
    
    cat_key = callback.data.replace("map_all_", "")
    category = CATEGORIES.get(cat_key)
    
    if not category:
        await callback.answer("❌ دسته‌بندی یافت نشد!", show_alert=True)
        return
    
    await callback.answer("📍 در حال ارسال موقعیت‌ها...")
    
    for place in category["places"]:
        if "coordinates" in place:
            lat, lon = place["coordinates"]
            await callback.message.answer_location(
                latitude=lat,
                longitude=lon
            )
            await callback.message.answer(
                f"📍 <b>{place['name']}</b>\n{place['name_fa']}",
                parse_mode="HTML"
            )


# ==================== دانلود PDF تور ====================

@router.callback_query(F.data == "download_tour_pdf")
async def download_tour_pdf(callback: types.CallbackQuery):
    """اطلاع‌رسانی برای PDF (در آینده پیاده‌سازی)"""
    
    await callback.answer(
        "📥 این قابلیت به‌زودی اضافه می‌شود!\n"
        "فعلاً از لینک گوگل مپ استفاده کنید.",
        show_alert=True
    )

import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in kilometers
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    
    a = math.sin(dLat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dLon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

@router.message(F.location)
async def handle_location(message: types.Message):
    """محاسبه نزدیک‌ترین مکان‌ها بر اساس لوکیشن کاربر"""
    lat = message.location.latitude
    lon = message.location.longitude
    
    places_list = []
    for cat_key, cat_data in CATEGORIES.items():
        for place in cat_data["places"]:
            if "coordinates" in place and len(place["coordinates"]) == 2:
                p_lat, p_lon = place["coordinates"]
                dist = haversine(lat, lon, p_lat, p_lon)
                places_list.append((dist, place))
                
    places_list.sort(key=lambda x: x[0])
    
    text = "📍 <b>نزدیک‌ترین مکان‌ها به شما:</b>\n\n"
    for dist, place in places_list[:5]: # Top 5 nearest
        dist_str = f"{dist:.1f} km" if dist >= 1 else f"{int(dist*1000)} m"
        text += f"🔹 <b>{place['name_fa']}</b> ({dist_str})\n"
        text += f"   {place['desc_fa'][:50]}...\n"
        text += f"   🗺 <a href='{place['map']}'>مسیریابی</a>\n\n"
        
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
