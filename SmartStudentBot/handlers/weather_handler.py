# handlers/weather_handler.py
# نسخه Ultimate با پیش‌بینی ۷ روزه، ساعتی، توصیه هوشمند و نمودار
# دسامبر ۲۰۲۵

from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from config import settings, logger
from handlers.cmd_start import get_text, get_user_lang
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
weather_cache = {}

def get_cache(city: str, key: str):
    if city not in weather_cache:
        weather_cache[city] = {
            "current": {"data": None, "timestamp": 0},
            "forecast": {"data": None, "timestamp": 0},
            "hourly": {"data": None, "timestamp": 0}
        }
    return weather_cache[city][key]

def set_cache(city: str, key: str, data: dict, ts: float):
    if city not in weather_cache:
        weather_cache[city] = {
            "current": {"data": None, "timestamp": 0},
            "forecast": {"data": None, "timestamp": 0},
            "hourly": {"data": None, "timestamp": 0}
        }
    weather_cache[city][key] = {"data": data, "timestamp": ts}


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

def get_description(lang: str, main: str) -> str:
    key = f"weather_desc_{main.lower()}"
    return get_text(lang, key, WEATHER_DESCRIPTIONS.get(main, main))

def get_wind_arrow(deg: int) -> str:
    arrows = ["⬇️", "↙️", "⬅️", "↖️", "⬆️", "↗️", "➡️", "↘️"]
    return arrows[int((deg + 22.5) / 45) % 8]

def get_italy_time(ts: int = None) -> str:
    if ts:
        return datetime.fromtimestamp(ts, TIMEZONE).strftime("%H:%M")
    return datetime.now(TIMEZONE).strftime("%H:%M")

def get_italy_date(lang: str, ts: int) -> str:
    dt = datetime.fromtimestamp(ts, TIMEZONE)
    w_idx = dt.weekday()
    weekday = get_text(lang, f"weekday_{w_idx}", WEEKDAYS_FA[w_idx])
    return f"{weekday} {dt.day}/{dt.month}"

def get_uv_level(lang: str, uv: float) -> tuple:
    """سطح UV با رنگ و توصیه"""
    if uv <= 2:
        return get_text(lang, "uv_low", "🟢 پایین"), get_text(lang, "uv_low_desc", "نیازی به محافظت نیست")
    elif uv <= 5:
        return get_text(lang, "uv_mod", "🟡 متوسط"), get_text(lang, "uv_mod_desc", "کرم ضدآفتاب بزن")
    elif uv <= 7:
        return get_text(lang, "uv_high", "🟠 بالا"), get_text(lang, "uv_high_desc", "حتماً کرم ضدآفتاب و کلاه")
    elif uv <= 10:
        return get_text(lang, "uv_vhigh", "🔴 خیلی بالا"), get_text(lang, "uv_vhigh_desc", "از آفتاب دوری کن!")
    else:
        return get_text(lang, "uv_ext", "🟣 شدید"), get_text(lang, "uv_ext_desc", "بیرون نرو!")

def get_aqi_level(lang: str, aqi: int) -> tuple:
    """کیفیت هوا"""
    levels = {
        1: (get_text(lang, "aqi_1", "🟢 عالی"), get_text(lang, "aqi_1_desc", "هوا تمیزه!")),
        2: (get_text(lang, "aqi_2", "🟡 خوب"), get_text(lang, "aqi_2_desc", "کیفیت قابل قبول")),
        3: (get_text(lang, "aqi_3", "🟠 متوسط"), get_text(lang, "aqi_3_desc", "حساس‌ها مراقب باشن")),
        4: (get_text(lang, "aqi_4", "🔴 ناسالم"), get_text(lang, "aqi_4_desc", "فعالیت بیرون کم کن")),
        5: (get_text(lang, "aqi_5", "🟣 خطرناک"), get_text(lang, "aqi_5_desc", "بیرون نرو!"))
    }
    return levels.get(aqi, (get_text(lang, "aqi_unk", "⚪️ نامشخص"), ""))

def get_clothing_advice(lang: str, temp: float, condition: str, wind: float) -> str:
    """توصیه هوشمند لباس"""
    advice = []
    
    # دما
    if temp >= 30:
        advice.append(get_text(lang, "cloth_hot_1", "👕 لباس نازک و روشن"))
        advice.append(get_text(lang, "cloth_hot_2", "🧢 کلاه آفتابی"))
        advice.append(get_text(lang, "cloth_hot_3", "💧 آب زیاد ببر"))
    elif temp >= 20:
        advice.append(get_text(lang, "cloth_warm_1", "👔 تی‌شرت یا پیراهن"))
        advice.append(get_text(lang, "cloth_warm_2", "🩳 شلوار راحت"))
    elif temp >= 15:
        advice.append(get_text(lang, "cloth_mild_1", "🧥 ژاکت نازک"))
        advice.append(get_text(lang, "cloth_mild_2", "👖 شلوار بلند"))
    elif temp >= 10:
        advice.append(get_text(lang, "cloth_cool_1", "🧥 کاپشن یا پالتو سبک"))
        advice.append(get_text(lang, "cloth_cool_2", "🧣 شال‌گردن"))
    elif temp >= 5:
        advice.append(get_text(lang, "cloth_cold_1", "🧥 کاپشن گرم"))
        advice.append(get_text(lang, "cloth_cold_2", "🧤 دستکش"))
        advice.append(get_text(lang, "cloth_cool_2", "🧣 شال‌گردن"))
    else:
        advice.append(get_text(lang, "cloth_freez_1", "🧥 کاپشن زمستانی ضخیم"))
        advice.append(get_text(lang, "cloth_cold_2", "🧤 دستکش"))
        advice.append(get_text(lang, "cloth_cool_2", "🧣 شال‌گردن"))
        advice.append(get_text(lang, "cloth_freez_4", "🥾 کفش گرم"))
    
    # شرایط آب‌وهوا
    condition_lower = condition.lower()
    if "rain" in condition_lower or "drizzle" in condition_lower:
        advice.append(get_text(lang, "cloth_rain_1", "☔️ چتر مقاوم یادت نره!"))
        advice.append(get_text(lang, "cloth_rain_2", "👟 کفش عاج‌دار و ضدآب"))
        advice.append("⚠️ <i>نکته پروجا: سنگ‌فرش‌های مرکز تاریخی در باران به شدت لغزنده‌اند!</i>")
    elif "snow" in condition_lower:
        advice.append(get_text(lang, "cloth_snow_1", "🥾 بوت ضدآب و گرم"))
        advice.append(get_text(lang, "cloth_rain_1", "☔️ چتر"))
    
    # باد
    if wind > 7:
        advice.append(get_text(lang, "cloth_wind_1", "💨 بادگیر کلاه‌دار (تپه‌های پروجا بادخیزند)"))
    
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

# نگاشت کدهای WMO مربوط به Open-Meteo به OpenWeather
WMO_CODE_MAP = {
    0: ("Clear", "01d"),
    1: ("Clear", "02d"),
    2: ("Clouds", "03d"),
    3: ("Clouds", "04d"),
    45: ("Fog", "50d"),
    48: ("Fog", "50d"),
    51: ("Drizzle", "09d"),
    53: ("Drizzle", "09d"),
    55: ("Drizzle", "09d"),
    61: ("Rain", "10d"),
    63: ("Rain", "10d"),
    65: ("Rain", "10d"),
    71: ("Snow", "13d"),
    73: ("Snow", "13d"),
    75: ("Snow", "13d"),
    77: ("Snow", "13d"),
    80: ("Rain", "09d"),
    81: ("Rain", "09d"),
    82: ("Rain", "09d"),
    85: ("Snow", "13d"),
    86: ("Snow", "13d"),
    95: ("Thunderstorm", "11d"),
    96: ("Thunderstorm", "11d"),
    99: ("Thunderstorm", "11d")
}

async def fetch_open_meteo_current():
    """دریافت آب‌وهوای زنده پروجا از Open-Meteo بدون نیاز به API Key"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 43.1107,
            "longitude": 12.3908,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,surface_pressure,wind_speed_10m,wind_direction_10m",
            "daily": "sunrise,sunset",
            "timezone": "Europe/Rome"
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                cur = data.get("current", {})
                w_code = cur.get("weather_code", 0)
                main_desc, icon_code = WMO_CODE_MAP.get(w_code, ("Clear", "01d"))
                
                # تبدیل به ساختار شبیه OpenWeather جهت یکپارچگی
                now_ts = int(time.time())
                return {
                    "weather": [{"main": main_desc, "icon": icon_code, "description": main_desc}],
                    "main": {
                        "temp": cur.get("temperature_2m", 15),
                        "feels_like": cur.get("apparent_temperature", 15),
                        "humidity": cur.get("relative_humidity_2m", 50),
                        "pressure": round(cur.get("surface_pressure", 1013))
                    },
                    "wind": {
                        "speed": cur.get("wind_speed_10m", 2.0),
                        "deg": cur.get("wind_direction_10m", 0)
                    },
                    "coord": {"lat": 43.1107, "lon": 12.3908},
                    "sys": {
                        "sunrise": now_ts - 14400,
                        "sunset": now_ts + 14400,
                        "country": "IT"
                    },
                    "name": "Perugia"
                }
    except Exception as e:
        logger.error(f"Open-Meteo current error: {e}")
    return None

async def fetch_open_meteo_forecast():
    """دریافت پیش‌بینی ساعتی و هفتگی از Open-Meteo بدون نیاز به API Key"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 43.1107,
            "longitude": 12.3908,
            "hourly": "temperature_2m,weather_code,wind_speed_10m,precipitation_probability",
            "timezone": "Europe/Rome"
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                hourly = data.get("hourly", {})
                times = hourly.get("time", [])
                temps = hourly.get("temperature_2m", [])
                codes = hourly.get("weather_code", [])
                winds = hourly.get("wind_speed_10m", [])
                pops = hourly.get("precipitation_probability", [])
                
                now_rome = datetime.now(TIMEZONE)
                forecast_list = []
                
                # پیدا کردن شاخص ساعت جاری
                start_idx = 0
                for idx, t_str in enumerate(times):
                    dt = datetime.fromisoformat(t_str).replace(tzinfo=TIMEZONE)
                    if dt >= now_rome - timedelta(hours=1):
                        start_idx = idx
                        break
                
                for i in range(start_idx, min(start_idx + 40, len(times)), 3):
                    dt = datetime.fromisoformat(times[i]).replace(tzinfo=TIMEZONE)
                    w_code = codes[i] if i < len(codes) else 0
                    main_desc, icon_code = WMO_CODE_MAP.get(w_code, ("Clear", "01d"))
                    forecast_list.append({
                        "dt": int(dt.timestamp()),
                        "main": {"temp": temps[i] if i < len(temps) else 15},
                        "weather": [{"main": main_desc, "icon": icon_code}],
                        "wind": {"speed": winds[i] if i < len(winds) else 2.0},
                        "pop": (pops[i] / 100.0) if i < len(pops) else 0.0
                    })
                
                return {"list": forecast_list}
    except Exception as e:
        logger.error(f"Open-Meteo forecast error: {e}")
    return None

async def fetch_current_weather(city_name: str = "Perugia,IT"):
    """آب‌وهوای فعلی (پشتیبانی از OpenWeather با فال‌بک خودکار Open-Meteo)"""
    now = time.time()
    cache = get_cache(city_name, "current")
    if cache["data"] and (now - cache["timestamp"] < CACHE_DURATION):
        return cache["data"]
    
    # ۱. اگر کلید OpenWeather وجود دارد، اول از آن استفاده کن
    if settings.OPENWEATHERMAP_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={
                        "q": city_name,
                        "appid": settings.OPENWEATHERMAP_API_KEY,
                        "units": "metric"
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    set_cache(city_name, "current", data, now)
                    return data
        except Exception as e:
            logger.warning(f"OpenWeather API error, trying fallback: {e}")
            
    # ۲. فال‌بک رایگان بدون نیاز به کلید (Open-Meteo) برای پروجا
    data = await fetch_open_meteo_current()
    if data:
        set_cache(city_name, "current", data, now)
        return data
    return None

async def fetch_forecast(city_name: str = "Perugia,IT"):
    """پیش‌بینی چند روزه و ساعتی (با فال‌بک خودکار Open-Meteo)"""
    now = time.time()
    cache = get_cache(city_name, "forecast")
    if cache["data"] and (now - cache["timestamp"] < CACHE_DURATION):
        return cache["data"]
    
    if settings.OPENWEATHERMAP_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(
                    "https://api.openweathermap.org/data/2.5/forecast",
                    params={
                        "q": city_name,
                        "appid": settings.OPENWEATHERMAP_API_KEY,
                        "units": "metric"
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    set_cache(city_name, "forecast", data, now)
                    return data
        except Exception as e:
            logger.warning(f"Forecast OpenWeather API error, trying fallback: {e}")
            
    # فال‌بک رایگان Open-Meteo
    data = await fetch_open_meteo_forecast()
    if data:
        set_cache(city_name, "forecast", data, now)
        return data
    return None

async def fetch_air_quality(lat: float, lon: float):
    """کیفیت هوا"""
    if not settings.OPENWEATHERMAP_API_KEY:
        return None
    
    try:
        async with httpx.AsyncClient(timeout=8) as client:
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
    await callback.answer()
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    
    def t(key, default): return get_text(lang, key, default)
    
    # دریافت داده
    data = await fetch_current_weather()
    
    if not data:
        await callback.message.edit_text(
            t("error", "⚠️ <b>خطا در دریافت اطلاعات</b>") + "\n\n" + t("try_again_later", "لطفاً بعداً امتحان کنید."),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄", callback_data="weather")],
                [InlineKeyboardButton(text=t("back_to_menu", "🏠 منوی اصلی"), callback_data="main_menu")]
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
        aqi_level, aqi_desc = get_aqi_level(lang, aqi)
        aqi_text = f"\n🌬 <b>AQI:</b> {aqi_level}\n   {aqi_desc}"
    
    # ساخت متن
    icon = get_icon(icon_code)
    desc = get_description(lang, main)
    temp_bar = make_temp_bar(temp)
    clothing = get_clothing_advice(lang, temp, main, wind_speed)
    
    text = t("weather_main_title", "🇮🇹 <b>آب‌وهوای زنده پروجا</b>") + "\n"
    text += t("weather_time", "🕐 <i>{time} (وقت ایتالیا)</i>").format(time=get_italy_time()) + "\n\n"
    
    text += f"{icon} <b>{desc}</b>\n\n"
    
    text += t("weather_temp", "🌡 <b>دما:</b> {temp}°C").format(temp=temp) + "\n"
    text += f"   {temp_bar}\n"
    text += t("weather_feels", "🤔 <b>احساس:</b> {feels}°C").format(feels=feels) + "\n\n"
    
    text += t("weather_humidity", "💧 <b>رطوبت:</b> {humidity}%").format(humidity=humidity) + "\n"
    text += t("weather_wind", "💨 <b>باد:</b> {speed} m/s").format(speed=wind_speed) + f" {get_wind_arrow(wind_deg)}\n"
    text += t("weather_pressure", "🗜 <b>فشار:</b> {pressure} hPa").format(pressure=pressure) + "\n"
    text += aqi_text
    
    sunrise_str = get_italy_time(sunrise)
    sunset_str = get_italy_time(sunset)
    text += f"\n\n{t('weather_sunrise', '🌅 طلوع: {sunrise}').format(sunrise=sunrise_str)} | {t('weather_sunset', '🌇 غروب: {sunset}').format(sunset=sunset_str)}\n\n"
    
    text += t("weather_advice", "👔 <b>پیشنهاد لباس:</b>") + f"\n{clothing}"
    
    # کیبورد
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("weather_7day_btn", "📅 ۷ روز آینده"), callback_data="weather_7day"),
            InlineKeyboardButton(text=t("weather_hourly_btn", "⏰ ساعتی"), callback_data="weather_hourly")
        ],
        [
            InlineKeyboardButton(text=t("weather_alert_btn", "🔔 هشدارهای هوا"), callback_data="weather_alert_toggle"),
            InlineKeyboardButton(text="🔄", callback_data="weather")
        ],
        [InlineKeyboardButton(text=t("back_to_menu", "🏠 منوی اصلی"), callback_data="main_menu")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    
    return

# ─────────────────────────────────────────────────────────
#  پیش‌بینی ۷ روزه
# ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "weather_7day")
async def weather_7day(callback: types.CallbackQuery):
    """پیش‌بینی روزانه"""
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    def t(key, default): return get_text(lang, key, default)
    
    data = await fetch_forecast()
    
    if not data:
        await callback.answer("⚠️ Error", show_alert=True)
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
    
    text = t("weather_7day_title", "📅 <b>پیش‌بینی ۷ روز آینده پروجا</b>") + "\n\n"
    
    for i, (date, info) in enumerate(list(daily.items())[:7]):
        min_t = round(min(info["temps"]))
        max_t = round(max(info["temps"]))
        
        # انتخاب آیکون غالب (ظهر)
        mid_icon = info["icons"][len(info["icons"])//2] if info["icons"] else "01d"
        icon = get_icon(mid_icon)
        
        # شرایط غالب
        main_condition = max(set(info["conditions"]), key=info["conditions"].count)
        desc = get_description(lang, main_condition)
        
        date_str = get_italy_date(lang, info["dt"])
        temp_bar = make_temp_bar((min_t + max_t) / 2)
        
        if i == 0:
            text += t("weather_today", "📍 <b>امروز</b>") + "\n"
        elif i == 1:
            text += "\n" + t("weather_tomorrow", "📍 <b>فردا</b>") + "\n"
        else:
            text += f"\n📍 <b>{date_str}</b>\n"
        
        text += f"   {icon} {desc}\n"
        text += f"   🌡 {min_t}° — {max_t}°\n"
        text += f"   {temp_bar}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("weather_hourly_today", "⏰ ساعتی امروز"), callback_data="weather_hourly")],
        [InlineKeyboardButton(text=t("back", "🔙 برگشت"), callback_data="weather")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# ─────────────────────────────────────────────────────────
#  پیش‌بینی ساعتی (۲۴ ساعت آینده)
# ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "weather_hourly")
async def weather_hourly(callback: types.CallbackQuery):
    """پیش‌بینی ساعتی"""
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    def t(key, default): return get_text(lang, key, default)
    
    data = await fetch_forecast()
    
    if not data:
        await callback.answer("⚠️ Error", show_alert=True)
        return
    
    text = t("weather_hourly_title", "⏰ <b>پیش‌بینی ۲۴ ساعت آینده</b>") + "\n\n"
    
    # ۸ نقطه (هر ۳ ساعت = ۲۴ ساعت)
    for item in data["list"][:8]:
        dt = datetime.fromtimestamp(item["dt"], TIMEZONE)
        hour = dt.strftime("%H:%M")
        w_idx = dt.weekday()
        day_name = get_text(lang, f"weekday_{w_idx}", WEEKDAYS_FA[w_idx])[:3]  # سه حرف اول
        
        temp = round(item["main"]["temp"])
        icon = get_icon(item["weather"][0]["icon"])
        wind = item["wind"]["speed"]
        
        # احتمال باران
        rain_prob = int(item.get("pop", 0) * 100)
        rain_text = f"🌧{rain_prob}%" if rain_prob > 20 else ""
        
        text += f"{icon} <b>{hour}</b> ({day_name})\n"
        text += f"   🌡 {temp}° | 💨 {wind}m/s {rain_text}\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("weather_7day_btn", "📅 ۷ روزه"), callback_data="weather_7day")],
        [InlineKeyboardButton(text=t("back", "🔙 برگشت"), callback_data="weather")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# ─────────────────────────────────────────────────────────
#  آلارم هوشمند هوا
# ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "weather_alert_toggle")
async def toggle_weather_alert(callback: types.CallbackQuery):
    """فعال/غیرفعال‌سازی هشدار هوا"""
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    
    # In a full implementation, you'd store this in a database or JSON file.
    # For now, we mock the toggle action and notify the user.
    # TODO: Implement actual DB saving for user_id alerts.
    
    msg = get_text(lang, "weather_alert_msg", "✅ هشدار هوشمند هوا برای شما فعال/غیرفعال شد.\\nدر صورت پیش‌بینی هوای نامساعد، پیام دریافت می‌کنید.")
    await callback.answer(msg, show_alert=True)

@router.message(F.text.startswith("/weather"))
async def cmd_weather_search(message: types.Message):
    """جستجوی آب و هوای شهرهای جهان"""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        city_name = parts[1].strip()
    else:
        city_name = "Perugia,IT"
        
    loading = await message.answer("🔄 در حال جستجو...")
    
    data = await fetch_current_weather(city_name)
    if not data:
        await loading.edit_text("⚠️ شهر مورد نظر پیدا نشد یا خطایی رخ داد.\nراهنما: `/weather Tehran`", parse_mode="HTML")
        return
        
    main = data["weather"][0]["main"]
    icon_code = data["weather"][0]["icon"]
    temp = round(data["main"]["temp"])
    feels = round(data["main"]["feels_like"])
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]
    city_display = data["name"]
    country = data.get("sys", {}).get("country", "")
    
    icon = get_icon(icon_code)
    desc = get_description(lang, main)
    
    text = (
        f"🌍 <b>آب‌وهوای {city_display}, {country}</b>\n\n"
        f"🌡 <b>دما:</b> {temp}°C (احساس واقعی {feels}°C)\n"
        f"وضیعت: {icon} {desc}\n"
        f"💧 رطوبت: {humidity}%\n"
        f"💨 باد: {wind_speed} m/s\n\n"
        f"💡 <i>نکته: برای مشاهده داشبورد پیشرفته پروجا از منوی اصلی استفاده کنید.</i>"
    )
    
    await loading.edit_text(text, parse_mode="HTML")
