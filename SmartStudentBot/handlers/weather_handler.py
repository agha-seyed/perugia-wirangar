# handlers/weather_handler.py
# نسخه Ultimate با پیش‌بینی ۷ روزه، ساعتی، توصیه هوشمند و نمودار
# دسامبر ۲۰۲۵

from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from config import settings, logger
import httpx
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import pytz

router = Router()

# ─────────────────────────────────────────────────────────
#  تنظیمات و کش
# ─────────────────────────────────────────────────────────

CACHE_DURATION = 600  # 10 دقیقه
CITY = "Perugia,IT"
TIMEZONE = pytz.timezone("Europe/Rome")

# کش هوشمند
weather_cache = {
    "current": {"data": None, "timestamp": 0},
    "forecast": {"data": None, "timestamp": 0},
    "hourly": {"data": None, "timestamp": 0}
}

# ─────────────────────────────────────────────────────────
#  آیکون‌های پیشرفته بر اساس کد آب‌وهوا
# ─────────────────────────────────────────────────────────

WEATHER_ICONS = {
    # Clear
    "01d": "☀️", "01n": "🌙",
    # Few clouds
    "02d": "🌤", "02n": "☁️",
    # Scattered clouds
    "03d": "⛅️", "03n": "☁️",
    # Broken clouds
    "04d": "🌥", "04n": "☁️",
    # Rain
    "09d": "🌧", "09n": "🌧",
    "10d": "🌦", "10n": "🌧",
    # Thunderstorm
    "11d": "⛈", "11n": "⛈",
    # Snow
    "13d": "❄️", "13n": "❄️",
    # Mist/Fog
    "50d": "🌫", "50n": "🌫"
}

WEATHER_DESCRIPTIONS = {
    "Clear": "آسمان صاف",
    "Clouds": "ابری",
    "Rain": "بارانی",
    "Drizzle": "نم‌نم باران",
    "Thunderstorm": "رعد و برق",
    "Snow": "برفی",
    "Mist": "مه",
    "Fog": "غبار",
    "Haze": "غبارآلود"
}

# روزهای هفته فارسی
WEEKDAYS_FA = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]

# ─────────────────────────────────────────────────────────
#  توابع کمکی
# ─────────────────────────────────────────────────────────

def get_icon(icon_code: str) -> str:
    return WEATHER_ICONS.get(icon_code, "🌡")

def get_description(main: str) -> str:
    return WEATHER_DESCRIPTIONS.get(main, main)

def get_wind_arrow(deg: int) -> str:
    arrows = ["⬇️", "↙️", "⬅️", "↖️", "⬆️", "↗️", "➡️", "↘️"]
    return arrows[int((deg + 22.5) / 45) % 8]

def get_italy_time(ts: int = None) -> str:
    if ts:
        return datetime.fromtimestamp(ts, TIMEZONE).strftime("%H:%M")
    return datetime.now(TIMEZONE).strftime("%H:%M")

def get_italy_date(ts: int) -> str:
    dt = datetime.fromtimestamp(ts, TIMEZONE)
    weekday = WEEKDAYS_FA[dt.weekday()]
    return f"{weekday} {dt.day}/{dt.month}"

def get_uv_level(uv: float) -> tuple:
    """سطح UV با رنگ و توصیه"""
    if uv <= 2:
        return "🟢 پایین", "نیازی به محافظت نیست"
    elif uv <= 5:
        return "🟡 متوسط", "کرم ضدآفتاب بزن"
    elif uv <= 7:
        return "🟠 بالا", "حتماً کرم ضدآفتاب و کلاه"
    elif uv <= 10:
        return "🔴 خیلی بالا", "از آفتاب دوری کن!"
    else:
        return "🟣 شدید", "بیرون نرو!"

def get_aqi_level(aqi: int) -> tuple:
    """کیفیت هوا"""
    levels = {
        1: ("🟢 عالی", "هوا تمیزه!"),
        2: ("🟡 خوب", "کیفیت قابل قبول"),
        3: ("🟠 متوسط", "حساس‌ها مراقب باشن"),
        4: ("🔴 ناسالم", "فعالیت بیرون کم کن"),
        5: ("🟣 خطرناک", "بیرون نرو!")
    }
    return levels.get(aqi, ("⚪️ نامشخص", ""))

def get_clothing_advice(temp: float, condition: str, wind: float) -> str:
    """توصیه هوشمند لباس"""
    advice = []
    
    # دما
    if temp >= 30:
        advice.append("👕 لباس نازک و روشن")
        advice.append("🧢 کلاه آفتابی")
        advice.append("💧 آب زیاد ببر")
    elif temp >= 20:
        advice.append("👔 تی‌شرت یا پیراهن")
        advice.append("🩳 شلوار راحت")
    elif temp >= 15:
        advice.append("🧥 ژاکت نازک")
        advice.append("👖 شلوار بلند")
    elif temp >= 10:
        advice.append("🧥 کاپشن یا پالتو سبک")
        advice.append("🧣 شال‌گردن")
    elif temp >= 5:
        advice.append("🧥 کاپشن گرم")
        advice.append("🧤 دستکش")
        advice.append("🧣 شال‌گردن")
    else:
        advice.append("🧥 کاپشن زمستانی ضخیم")
        advice.append("🧤 دستکش و کلاه")
        advice.append("🧣 شال‌گردن")
        advice.append("🥾 کفش گرم")
    
    # شرایط آب‌وهوا
    condition_lower = condition.lower()
    if "rain" in condition_lower or "drizzle" in condition_lower:
        advice.append("☔️ چتر یادت نره!")
        advice.append("👟 کفش ضدآب")
    elif "snow" in condition_lower:
        advice.append("🥾 بوت ضدآب")
        advice.append("☔️ چتر")
    
    # باد
    if wind > 8:
        advice.append("💨 لباس بادگیر")
    
    return "\n".join(f"  • {a}" for a in advice)

def make_temp_bar(temp: float, min_t: float = -5, max_t: float = 40) -> str:
    """نوار گرافیکی دما"""
    # نرمال‌سازی بین 0 تا 10
    normalized = int((temp - min_t) / (max_t - min_t) * 10)
    normalized = max(0, min(10, normalized))
    
    if temp < 10:
        color = "🟦"
    elif temp < 20:
        color = "🟩"
    elif temp < 30:
        color = "🟨"
    else:
        color = "🟥"
    
    return color * normalized + "⬜️" * (10 - normalized)

# ─────────────────────────────────────────────────────────
#  دریافت داده از API
# ─────────────────────────────────────────────────────────

async def fetch_current_weather():
    """آب‌وهوای فعلی"""
    if not settings.OPENWEATHERMAP_API_KEY:
        return None
    
    now = time.time()
    if weather_cache["current"]["data"] and (now - weather_cache["current"]["timestamp"] < CACHE_DURATION):
        return weather_cache["current"]["data"]
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": CITY,
                    "appid": settings.OPENWEATHERMAP_API_KEY,
                    "units": "metric"
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                weather_cache["current"] = {"data": data, "timestamp": now}
                return data
    except Exception as e:
        logger.error(f"Weather API error: {e}")
    return None

async def fetch_forecast():
    """پیش‌بینی ۵ روزه (هر ۳ ساعت)"""
    if not settings.OPENWEATHERMAP_API_KEY:
        return None
    
    now = time.time()
    if weather_cache["forecast"]["data"] and (now - weather_cache["forecast"]["timestamp"] < CACHE_DURATION):
        return weather_cache["forecast"]["data"]
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/forecast",
                params={
                    "q": CITY,
                    "appid": settings.OPENWEATHERMAP_API_KEY,
                    "units": "metric"
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                weather_cache["forecast"] = {"data": data, "timestamp": now}
                return data
    except Exception as e:
        logger.error(f"Forecast API error: {e}")
    return None

async def fetch_air_quality(lat: float, lon: float):
    """کیفیت هوا"""
    if not settings.OPENWEATHERMAP_API_KEY:
        return None
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/air_pollution",
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": settings.OPENWEATHERMAP_API_KEY
                }
            )
            if resp.status_code == 200:
                return resp.json()
    except:
        pass
    return None

# ─────────────────────────────────────────────────────────
#  منوی اصلی آب‌وهوا
# ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "weather")
async def weather_main(callback: types.CallbackQuery):
    """داشبورد اصلی آب‌وهوا"""
    
    # دریافت داده
    data = await fetch_current_weather()
    
    if not data:
        await callback.message.edit_text(
            "⚠️ <b>خطا در دریافت اطلاعات آب‌وهوا</b>\n\n"
            "لطفاً بعداً امتحان کنید.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 تلاش مجدد", callback_data="weather")],
                [InlineKeyboardButton(text="🏠 منو", callback_data="main_menu")]
            ]),
            parse_mode="HTML"
        )
        return
    
    # استخراج اطلاعات
    main = data["weather"][0]["main"]
    icon_code = data["weather"][0]["icon"]
    temp = round(data["main"]["temp"])
    feels = round(data["main"]["feels_like"])
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]
    wind_deg = data["wind"].get("deg", 0)
    pressure = data["main"]["pressure"]
    sunrise = data["sys"]["sunrise"]
    sunset = data["sys"]["sunset"]
    lat = data["coord"]["lat"]
    lon = data["coord"]["lon"]
    
    # کیفیت هوا
    aqi_data = await fetch_air_quality(lat, lon)
    aqi_text = ""
    if aqi_data:
        aqi = aqi_data["list"][0]["main"]["aqi"]
        aqi_level, aqi_desc = get_aqi_level(aqi)
        aqi_text = f"\n🌬 <b>کیفیت هوا:</b> {aqi_level}\n   {aqi_desc}"
    
    # ساخت متن
    icon = get_icon(icon_code)
    desc = get_description(main)
    temp_bar = make_temp_bar(temp)
    clothing = get_clothing_advice(temp, main, wind_speed)
    
    text = f"🇮🇹 <b>آب‌وهوای زنده پروجا</b>\n"
    text += f"🕐 <i>{get_italy_time()} (وقت ایتالیا)</i>\n\n"
    
    text += f"{icon} <b>{desc}</b>\n\n"
    
    text += f"🌡 <b>دما:</b> {temp}°C\n"
    text += f"   {temp_bar}\n"
    text += f"🤔 <b>احساس:</b> {feels}°C\n\n"
    
    text += f"💧 <b>رطوبت:</b> {humidity}%\n"
    text += f"💨 <b>باد:</b> {wind_speed} m/s {get_wind_arrow(wind_deg)}\n"
    text += f"🗜 <b>فشار:</b> {pressure} hPa\n"
    text += aqi_text
    text += f"\n\n🌅 طلوع: {get_italy_time(sunrise)} | 🌇 غروب: {get_italy_time(sunset)}\n\n"
    
    text += f"👔 <b>پیشنهاد لباس:</b>\n{clothing}"
    
    # کیبورد
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 ۷ روز آینده", callback_data="weather_7day"),
            InlineKeyboardButton(text="⏰ ساعتی", callback_data="weather_hourly")
        ],
        [InlineKeyboardButton(text="🔄 به‌روزرسانی", callback_data="weather")],
        [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    
    await callback.answer()

# ─────────────────────────────────────────────────────────
#  پیش‌بینی ۷ روزه
# ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "weather_7day")
async def weather_7day(callback: types.CallbackQuery):
    """پیش‌بینی روزانه"""
    
    data = await fetch_forecast()
    
    if not data:
        await callback.answer("⚠️ خطا در دریافت پیش‌بینی", show_alert=True)
        return
    
    # گروه‌بندی بر اساس روز
    daily = {}
    for item in data["list"]:
        date = datetime.fromtimestamp(item["dt"], TIMEZONE).strftime("%Y-%m-%d")
        if date not in daily:
            daily[date] = {
                "temps": [],
                "icons": [],
                "conditions": [],
                "dt": item["dt"]
            }
        daily[date]["temps"].append(item["main"]["temp"])
        daily[date]["icons"].append(item["weather"][0]["icon"])
        daily[date]["conditions"].append(item["weather"][0]["main"])
    
    text = "📅 <b>پیش‌بینی ۷ روز آینده پروجا</b>\n\n"
    
    for i, (date, info) in enumerate(list(daily.items())[:7]):
        min_t = round(min(info["temps"]))
        max_t = round(max(info["temps"]))
        
        # انتخاب آیکون غالب (ظهر)
        mid_icon = info["icons"][len(info["icons"])//2] if info["icons"] else "01d"
        icon = get_icon(mid_icon)
        
        # شرایط غالب
        main_condition = max(set(info["conditions"]), key=info["conditions"].count)
        desc = get_description(main_condition)
        
        date_str = get_italy_date(info["dt"])
        temp_bar = make_temp_bar((min_t + max_t) / 2)
        
        if i == 0:
            text += f"📍 <b>امروز</b>\n"
        elif i == 1:
            text += f"\n📍 <b>فردا</b>\n"
        else:
            text += f"\n📍 <b>{date_str}</b>\n"
        
        text += f"   {icon} {desc}\n"
        text += f"   🌡 {min_t}° — {max_t}°\n"
        text += f"   {temp_bar}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏰ ساعتی امروز", callback_data="weather_hourly")],
        [InlineKeyboardButton(text="🔙 برگشت", callback_data="weather")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# ─────────────────────────────────────────────────────────
#  پیش‌بینی ساعتی (۲۴ ساعت آینده)
# ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "weather_hourly")
async def weather_hourly(callback: types.CallbackQuery):
    """پیش‌بینی ساعتی"""
    
    data = await fetch_forecast()
    
    if not data:
        await callback.answer("⚠️ خطا", show_alert=True)
        return
    
    text = "⏰ <b>پیش‌بینی ۲۴ ساعت آینده</b>\n\n"
    
    # ۸ نقطه (هر ۳ ساعت = ۲۴ ساعت)
    for item in data["list"][:8]:
        dt = datetime.fromtimestamp(item["dt"], TIMEZONE)
        hour = dt.strftime("%H:%M")
        day_name = WEEKDAYS_FA[dt.weekday()][:3]  # سه حرف اول
        
        temp = round(item["main"]["temp"])
        icon = get_icon(item["weather"][0]["icon"])
        wind = item["wind"]["speed"]
        
        # احتمال باران
        rain_prob = int(item.get("pop", 0) * 100)
        rain_text = f"🌧{rain_prob}%" if rain_prob > 20 else ""
        
        text += f"{icon} <b>{hour}</b> ({day_name})\n"
        text += f"   🌡 {temp}° | 💨 {wind}m/s {rain_text}\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 ۷ روزه", callback_data="weather_7day")],
        [InlineKeyboardButton(text="🔙 برگشت", callback_data="weather")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()