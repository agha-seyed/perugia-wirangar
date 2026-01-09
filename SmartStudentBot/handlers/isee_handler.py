# handlers/isee_handler.py
# نسخه ۲.۰ - بهبود یافته بر اساس سند جامع
# آخرین بروزرسانی: دسامبر 2025

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, 
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from config import settings, logger
import httpx
from datetime import datetime
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass, field

router = Router()

# ═══════════════════════════════════════════════════════════════════
# بخش ۱.۱: کلیدهای API (باید به settings منتقل شود)
# ═══════════════════════════════════════════════════════════════════

NAVASAN_API_KEYS = getattr(settings, 'NAVASAN_API_KEYS', [
    "freepnP0B5PJNRJD5XUTFauKTpubrxE2",
    "freeWVcwTB4Xq8yT48Y0YHgCy8JcvulU",
    "freezW677iqPcZxRFwQbpX0iZQfxaWwi",
])
current_api_index = 0

# ═══════════════════════════════════════════════════════════════════
# بخش ۱.۲: آستانه‌های ISEE - قابل تنظیم بر اساس منطقه
# ═══════════════════════════════════════════════════════════════════

class Region(Enum):
    """مناطق ایتالیا برای آستانه‌های متفاوت"""
    NORD = "north"
    CENTRO = "center"
    SUD = "south"

@dataclass
class ISEEThresholds:
    """آستانه‌های بورسیه بر اساس منطقه"""
    full_scholarship: int
    partial_scholarship: int
    reduced_fee: int
    max_useful: int
    
# آستانه‌های DSU 2025-2026 بر اساس منطقه
REGIONAL_THRESHOLDS = {
    Region.NORD: ISEEThresholds(
        full_scholarship=25500,
        partial_scholarship=36000,
        reduced_fee=50000,
        max_useful=60000,
    ),
    Region.CENTRO: ISEEThresholds(
        full_scholarship=26000,
        partial_scholarship=38000,
        reduced_fee=52000,
        max_useful=65000,
    ),
    Region.SUD: ISEEThresholds(
        full_scholarship=27000,
        partial_scholarship=40000,
        reduced_fee=55000,
        max_useful=70000,
    ),
}

# پیش‌فرض (متوسط)
DEFAULT_THRESHOLDS = REGIONAL_THRESHOLDS[Region.CENTRO]

# ═══════════════════════════════════════════════════════════════════
# بخش ۱.۳: معافیت‌ها و ثابت‌های محاسباتی
# ═══════════════════════════════════════════════════════════════════

@dataclass
class DeductionLimits:
    """سقف معافیت‌ها و کسورات"""
    # کسر اجاره‌خانه (Canone di Locazione)
    max_rent_deduction: int = 7000
    
    # معافیت خانه اصلی (Prima Casa)
    primary_home_exemption: int = 52500
    extra_per_child_after_2: int = 2500
    
    # معافیت دارایی مالی (بر اساس تعداد اعضا)
    financial_exemption_base: int = 6000
    financial_exemption_per_member: int = 500
    financial_exemption_max: int = 10000
    
    # حداقل درآمد برای استقلال دانشجو
    independent_student_min_income: int = 9000
    independent_student_min_years: int = 2

DEDUCTION_LIMITS = DeductionLimits()

# ضریب مقیاس خانواده (Scala di Equivalenza)
FAMILY_SCALE_COEFFICIENTS = {
    1: 1.00,
    2: 1.57,
    3: 2.04,
    4: 2.46,
    5: 2.85,
}
# برای هر نفر اضافی: +0.35
EXTRA_MEMBER_COEFFICIENT = 0.35

# ضرایب ویژه
SPECIAL_COEFFICIENTS = {
    "disabled_member": 0.50,      # عضو معلول
    "single_parent": 0.20,         # والد تنها
    "student_abroad": 0.20,        # دانشجوی خارج از شهر
}

# آمار مرجع دانشجویان ایرانی
IRANIAN_STATS = {
    "average": 21500,
    "median": 19000,
    "p25": 14000,    # ربع اول
    "p75": 32000,    # ربع سوم
    "min_reported": 8000,
    "max_reported": 85000,
}

# ═══════════════════════════════════════════════════════════════════
# بخش ۱.۴: ایموجی‌ها و UI Constants
# ═══════════════════════════════════════════════════════════════════

STEP_EMOJI = {
    1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 
    5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣",
}

STATUS_CONFIG = {
    "full": {
        "emoji": "🎉",
        "color": "🟢",
        "bar": "🟢🟢🟢🟢🟢",
        "title": "بورسیه کامل + خوابگاه",
    },
    "partial": {
        "emoji": "👍",
        "color": "🟡",
        "bar": "🟡🟡🟡🟢🟢",
        "title": "بورسیه جزئی",
    },
    "reduced": {
        "emoji": "😐",
        "color": "🟠",
        "bar": "🟠🟠🟡🟡🟢",
        "title": "تخفیف شهریه",
    },
    "none": {
        "emoji": "😔",
        "color": "🔴",
        "bar": "🔴🔴🟠🟠🟡",
        "title": "بدون بورسیه",
    },
}

# ═══════════════════════════════════════════════════════════════════
# بخش ۱.۵: کلاس ذخیره‌سازی داده‌ها
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ISEEInput:
    """ورودی‌های محاسبه ISEE"""
    income: float = 0.0
    annual_rent: float = 0.0
    is_tenant: bool = False
    members: int = 1
    children_after_2: int = 0
    
    property_value: float = 0.0
    is_primary_home: bool = True
    
    financial_assets: float = 0.0
    total_debts: float = 0.0
    
    abroad_assets: float = 0.0
    
    is_independent_student: bool = False
    region: Region = Region.CENTRO
    
    # متادیتا
    eur_rate: int = 72000
    created_at: str = ""

@dataclass 
class ISEEResult:
    """نتیجه محاسبه ISEE"""
    isee: float
    ise: float
    isp: float  # شاخص دارایی
    scale: float
    status: str
    status_text: str
    
    # جزئیات کسورات
    rent_deduction: float = 0.0
    home_exemption: float = 0.0
    financial_exemption: float = 0.0
    debt_deduction: float = 0.0
    
    # مقادیر تعدیل‌شده
    adjusted_income: float = 0.0
    adjusted_property: float = 0.0
    adjusted_financial: float = 0.0
    total_patrimony: float = 0.0
    
    inputs: Optional[ISEEInput] = None

class ISEEDataStore:
    """مدیریت داده‌های کاربران با پشتیبانی از persistence"""
    
    def __init__(self):
        self.user_data: Dict[int, Dict[str, Any]] = {}
        self.eur_cache = {
            "rate": None,
            "timestamp": None,
            "ttl": 300
        }
    
    def get_user(self, user_id: int) -> Dict[str, Any]:
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "current": ISEEInput(),
                "history": [],
                "settings": {
                    "preferred_currency": "toman",
                    "region": Region.CENTRO,
                    "show_tips": True,
                }
            }
        return self.user_data[user_id]
    
    def get_current_input(self, user_id: int) -> ISEEInput:
        user = self.get_user(user_id)
        if not isinstance(user["current"], ISEEInput):
            user["current"] = ISEEInput()
        return user["current"]
    
    def save_calculation(self, user_id: int, result: ISEEResult):
        user = self.get_user(user_id)
        record = {
            "isee": result.isee,
            "status": result.status,
            "date": datetime.now().strftime("%Y/%m/%d %H:%M"),
            "inputs_summary": {
                "income": result.inputs.income if result.inputs else 0,
                "members": result.inputs.members if result.inputs else 1,
            }
        }
        user["history"].append(record)
        user["history"] = user["history"][-15:]  # نگهداری ۱۵ مورد آخر
    
    def get_cached_rate(self) -> Optional[int]:
        if self.eur_cache["rate"] and self.eur_cache["timestamp"]:
            elapsed = (datetime.now() - self.eur_cache["timestamp"]).total_seconds()
            if elapsed < self.eur_cache["ttl"]:
                return self.eur_cache["rate"]
        return None
    
    def set_cached_rate(self, rate: int):
        self.eur_cache["rate"] = rate
        self.eur_cache["timestamp"] = datetime.now()
    
    def clear_current(self, user_id: int):
        if user_id in self.user_data:
            self.user_data[user_id]["current"] = ISEEInput()

# نمونه سراسری
data_store = ISEEDataStore()

# ═══════════════════════════════════════════════════════════════════
# بخش ۱.۶: ماشین وضعیت (States) - توسعه یافته
# ═══════════════════════════════════════════════════════════════════

class ISEEState(StatesGroup):
    """وضعیت‌های فرم ISEE - نسخه کامل"""
    
    # شروع و مقدمه
    intro = State()
    select_mode = State()           # انتخاب حالت (کامل/سریع)
    select_region = State()         # انتخاب منطقه
    
    # مراحل اصلی
    waiting_income = State()        # ۱. درآمد
    waiting_rent = State()          # ۲. اجاره (اگر مستأجر)
    waiting_members = State()       # ۳. تعداد اعضا
    waiting_children = State()      # ۳.۵ تعداد فرزندان (برای معافیت)
    waiting_property = State()      # ۴. املاک
    waiting_primary_home = State()  # ۴.۵ آیا خانه اصلی است؟
    waiting_financial = State()     # ۵. دارایی مالی
    waiting_debts = State()         # ۶. بدهی‌ها
    waiting_abroad = State()        # ۷. دارایی خارجی
    waiting_independent = State()   # ۸. استقلال دانشجو
    
    # تأیید و ویرایش
    confirm_data = State()          # صفحه تأیید
    edit_field = State()            # ویرایش فیلد خاص
    
    # ابزارهای اضافی
    reverse_calc = State()          # محاسبه‌گر معکوس
    what_if = State()               # سناریوی فرضی

# نقشه مراحل برای بازگشت
STEP_MAP = {
    ISEEState.waiting_income: (1, "درآمد سالانه"),
    ISEEState.waiting_rent: (2, "اجاره‌خانه"),
    ISEEState.waiting_members: (3, "اعضای خانواده"),
    ISEEState.waiting_property: (4, "ارزش املاک"),
    ISEEState.waiting_financial: (5, "دارایی مالی"),
    ISEEState.waiting_debts: (6, "بدهی‌ها"),
    ISEEState.waiting_abroad: (7, "دارایی خارجی"),
    ISEEState.waiting_independent: (8, "استقلال دانشجو"),
}

# تعداد کل مراحل
TOTAL_STEPS = 8
QUICK_MODE_STEPS = 3  # حالت سریع: درآمد، اعضا، املاک

# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# بخش ۲.۱: دریافت نرخ ارز
# ═══════════════════════════════════════════════════════════════════

async def get_eur_rate() -> Tuple[int, bool]:
    """
    دریافت نرخ یورو با سیستم کش + چرخشی + Fallback
    
    Returns:
        Tuple[int, bool]: (نرخ یورو, آیا از API واقعی آمده)
    """
    global current_api_index
    
    # ابتدا چک کش
    cached = data_store.get_cached_rate()
    if cached:
        logger.debug(f"EUR rate from cache: {cached}")
        return cached, True
    
    # درخواست از API
    for attempt in range(len(NAVASAN_API_KEYS)):
        api_key = NAVASAN_API_KEYS[current_api_index]
        current_api_index = (current_api_index + 1) % len(NAVASAN_API_KEYS)
        
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                url = f"https://api.navasan.tech/latest/?api_key={api_key}"
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    eur_value = data.get("eur", {}).get("value")
                    
                    if eur_value:
                        rate = int(float(eur_value))
                        data_store.set_cached_rate(rate)
                        logger.info(f"EUR rate fetched successfully: {rate}")
                        return rate, True
                else:
                    logger.warning(f"API returned status {response.status_code}")
                        
        except httpx.TimeoutException:
            logger.warning(f"API timeout on attempt {attempt + 1}")
        except Exception as e:
            logger.warning(f"API attempt {attempt + 1} failed: {type(e).__name__}: {e}")
        
        await asyncio.sleep(0.3)  # تأخیر کوتاه بین تلاش‌ها
    
    # Fallback نهایی
    fallback_rate = 72000
    logger.warning(f"All API attempts failed. Using fallback rate: {fallback_rate}")
    return fallback_rate, False


# ═══════════════════════════════════════════════════════════════════
# بخش ۲.۲: پردازش و تبدیل اعداد فارسی
# ═══════════════════════════════════════════════════════════════════

def normalize_persian_text(text: str) -> str:
    """نرمال‌سازی متن فارسی/عربی به انگلیسی"""
    # جایگزینی اعداد فارسی و عربی
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    english_digits = "0123456789"
    
    result = text
    for p, a, e in zip(persian_digits, arabic_digits, english_digits):
        result = result.replace(p, e).replace(a, e)
    
    # حذف کاراکترهای اضافی
    result = result.replace(",", "").replace("،", "")
    result = result.replace("٬", "").replace(" ", "")
    
    return result.strip().lower()


def parse_persian_amount(text: str) -> Optional[float]:
    """
    تبدیل متن فارسی به عدد
    پشتیبانی از: اعداد فارسی، واحدها، عبارات خاص
    
    Returns:
        float یا None در صورت خطا
    """
    if not text:
        return None
    
    normalized = normalize_persian_text(text)
    
    # عبارات صفر
    zero_phrases = ["0", "ندارم", "نداریم", "هیچ", "خیر", "no", "none", "نه", "صفر"]
    if normalized in zero_phrases:
        return 0.0
    
    # عبارت "نمی‌دانم"
    unknown_phrases = ["نمیدانم", "نمیدونم", "نمی‌دانم", "نمی‌دونم"]
    if any(p in text for p in unknown_phrases):
        return None  # نشان‌دهنده نیاز به راهنمایی
    
    # واحدها و ضریب‌ها
    multipliers = [
        ("میلیارد", 1_000_000_000),
        ("ملیارد", 1_000_000_000),
        ("میلیون", 1_000_000),
        ("ملیون", 1_000_000),
        ("هزار", 1_000),
        ("تومان", 1),
        ("تومن", 1),
        ("ریال", 0.1),
        ("یورو", 1),
        ("euro", 1),
        ("eur", 1),
        ("€", 1),
        ("k", 1_000),
        ("m", 1_000_000),
    ]
    
    for unit, mult in multipliers:
        if unit in normalized:
            try:
                # استخراج بخش عددی
                num_part = normalized.replace(unit, "").strip()
                if not num_part:
                    return float(mult)
                
                # پشتیبانی از اعشار
                num_part = num_part.replace("/", ".").replace("٫", ".")
                return float(num_part) * mult
            except ValueError:
                continue
    
    # تلاش برای تبدیل مستقیم
    try:
        # پشتیبانی از اعشار فارسی
        normalized = normalized.replace("/", ".").replace("٫", ".")
        return float(normalized)
    except ValueError:
        return None


# ═══════════════════════════════════════════════════════════════════
# بخش ۲.۳: تشخیص هوشمند نوع ارز
# ═══════════════════════════════════════════════════════════════════

class CurrencyType(Enum):
    EURO = "euro"
    TOMAN = "toman"
    AMBIGUOUS = "ambiguous"


def detect_currency_from_text(text: str) -> CurrencyType:
    """تشخیص نوع ارز از متن"""
    text_lower = text.lower()
    
    euro_indicators = ["یورو", "euro", "eur", "€"]
    toman_indicators = ["تومان", "تومن", "ریال", "میلیون", "میلیارد"]
    
    for indicator in euro_indicators:
        if indicator in text_lower:
            return CurrencyType.EURO
    
    for indicator in toman_indicators:
        if indicator in text_lower:
            return CurrencyType.TOMAN
    
    return CurrencyType.AMBIGUOUS


def smart_currency_convert(
    amount: float, 
    eur_rate: int,
    original_text: str = "",
    context: str = "general"
) -> Tuple[float, CurrencyType, str]:
    """
    تبدیل هوشمند به یورو با تشخیص خودکار
    
    Args:
        amount: مقدار عددی
        eur_rate: نرخ یورو به تومان
        original_text: متن اصلی برای تشخیص واحد
        context: زمینه (abroad همیشه یورو)
    
    Returns:
        Tuple[مقدار به یورو, نوع ارز تشخیص داده شده, توضیح نمایشی]
    """
    if amount <= 0:
        return 0.0, CurrencyType.EURO, "۰ €"
    
    # تشخیص از متن اصلی
    detected = detect_currency_from_text(original_text)
    
    # زمینه خاص: دارایی خارجی همیشه یورو
    if context == "abroad":
        return amount, CurrencyType.EURO, f"{amount:,.0f} €"
    
    # اگر از متن تشخیص داده شد
    if detected == CurrencyType.EURO:
        return amount, CurrencyType.EURO, f"{amount:,.0f} €"
    
    if detected == CurrencyType.TOMAN:
        eur_value = amount / eur_rate
        return eur_value, CurrencyType.TOMAN, f"{amount:,.0f} ت ≈ {eur_value:,.0f} €"
    
    # تشخیص از مقدار (حالت مبهم)
    if amount < 500:
        # خیلی کوچک → احتمالاً یورو
        return amount, CurrencyType.EURO, f"{amount:,.0f} € (فرض یورو)"
    
    elif amount < 100_000:
        # بازه مبهم → فرض یورو با هشدار
        return amount, CurrencyType.AMBIGUOUS, f"{amount:,.0f} € ⚠️"
    
    else:
        # بزرگ → احتمالاً تومان
        eur_value = amount / eur_rate
        return eur_value, CurrencyType.TOMAN, f"{amount:,.0f} ت ≈ {eur_value:,.0f} €"


# ═══════════════════════════════════════════════════════════════════
# بخش ۲.۴: محاسبه ضریب خانواده
# ═══════════════════════════════════════════════════════════════════

def calculate_family_scale(
    members: int,
    has_disabled: bool = False,
    is_single_parent: bool = False,
    student_abroad: bool = False
) -> float:
    """
    محاسبه ضریب مقیاس خانواده (Scala di Equivalenza)
    با پشتیبانی از ضرایب ویژه
    """
    # ضریب پایه
    if members in FAMILY_SCALE_COEFFICIENTS:
        base_scale = FAMILY_SCALE_COEFFICIENTS[members]
    elif members > 5:
        base_scale = 2.85 + ((members - 5) * EXTRA_MEMBER_COEFFICIENT)
    else:
        base_scale = 1.0
    
    # ضرایب اضافی
    extra = 0.0
    
    if has_disabled:
        extra += SPECIAL_COEFFICIENTS["disabled_member"]
    
    if is_single_parent:
        extra += SPECIAL_COEFFICIENTS["single_parent"]
    
    if student_abroad:
        extra += SPECIAL_COEFFICIENTS["student_abroad"]
    
    return round(base_scale + extra, 2)


# ═══════════════════════════════════════════════════════════════════
# بخش ۲.۵: محاسبه معافیت‌ها و کسورات
# ═══════════════════════════════════════════════════════════════════

def calculate_rent_deduction(annual_rent: float, is_tenant: bool) -> float:
    """
    کسر اجاره‌خانه (Canone di Locazione)
    حداکثر ۷,۰۰۰ یورو
    """
    if not is_tenant or annual_rent <= 0:
        return 0.0
    
    return min(annual_rent, DEDUCTION_LIMITS.max_rent_deduction)


def calculate_primary_home_exemption(
    property_value: float,
    is_primary: bool,
    children_after_2: int = 0
) -> float:
    """
    معافیت خانه اصلی (Prima Casa)
    پایه: ۵۲,۵۰۰€ + ۲,۵۰۰€ به ازای هر فرزند بعد از دوم
    """
    if not is_primary or property_value <= 0:
        return 0.0
    
    exemption = DEDUCTION_LIMITS.primary_home_exemption
    exemption += children_after_2 * DEDUCTION_LIMITS.extra_per_child_after_2
    
    # معافیت نمی‌تواند از ارزش ملک بیشتر باشد
    return min(exemption, property_value)


def calculate_financial_exemption(members: int) -> float:
    """
    معافیت دارایی مالی (Franchigia Patrimonio Mobiliare)
    وابسته به تعداد اعضای خانواده
    """
    base = DEDUCTION_LIMITS.financial_exemption_base
    per_member = DEDUCTION_LIMITS.financial_exemption_per_member
    max_exempt = DEDUCTION_LIMITS.financial_exemption_max
    
    exemption = base + (members * per_member)
    return min(exemption, max_exempt)


def calculate_debt_deduction(
    total_debts: float,
    total_patrimony: float
) -> float:
    """
    کسر بدهی‌ها از دارایی
    حداکثر تا ۱۰۰٪ دارایی (نمی‌تواند منفی شود)
    """
    if total_debts <= 0:
        return 0.0
    
    return min(total_debts, total_patrimony)


# ═══════════════════════════════════════════════════════════════════
# بخش ۲.۶: موتور اصلی محاسبه ISEE
# ═══════════════════════════════════════════════════════════════════

def calculate_isee(inputs: ISEEInput, thresholds: ISEEThresholds = None) -> ISEEResult:
    """
    موتور محاسبه ISEE - نسخه کامل با تمام کسورات
    
    فرمول:
        ISE = درآمد تعدیل‌شده + (۲۰٪ × دارایی تعدیل‌شده)
        ISEE = ISE / ضریب خانواده
    """
    if thresholds is None:
        thresholds = REGIONAL_THRESHOLDS.get(inputs.region, DEFAULT_THRESHOLDS)
    
    # ═══ محاسبه درآمد تعدیل‌شده ═══
    rent_deduction = calculate_rent_deduction(inputs.annual_rent, inputs.is_tenant)
    adjusted_income = max(0, inputs.income - rent_deduction)
    
    # ═══ محاسبه دارایی ملکی تعدیل‌شده ═══
    home_exemption = calculate_primary_home_exemption(
        inputs.property_value,
        inputs.is_primary_home,
        inputs.children_after_2
    )
    adjusted_property = max(0, inputs.property_value - home_exemption)
    
    # ═══ محاسبه دارایی مالی تعدیل‌شده ═══
    financial_exemption = calculate_financial_exemption(inputs.members)
    adjusted_financial = max(0, inputs.financial_assets - financial_exemption)
    
    # ═══ مجموع دارایی قبل از کسر بدهی ═══
    raw_patrimony = adjusted_property + adjusted_financial + inputs.abroad_assets
    
    # ═══ کسر بدهی‌ها ═══
    debt_deduction = calculate_debt_deduction(inputs.total_debts, raw_patrimony)
    total_patrimony = max(0, raw_patrimony - debt_deduction)
    
    # ═══ شاخص ISP (دارایی) ═══
    isp = total_patrimony
    
    # ═══ شاخص ISE ═══
    ise = adjusted_income + (0.20 * total_patrimony)
    
    # ═══ ضریب خانواده ═══
    scale = calculate_family_scale(inputs.members)
    
    # ═══ ISEE نهایی ═══
    isee = ise / scale if scale > 0 else ise
    
    # ═══ تعیین وضعیت ═══
    if isee <= thresholds.full_scholarship:
        status = "full"
        status_text = "بورسیه کامل 🟢"
    elif isee <= thresholds.partial_scholarship:
        status = "partial"
        status_text = "بورسیه جزئی 🟡"
    elif isee <= thresholds.reduced_fee:
        status = "reduced"
        status_text = "تخفیف شهریه 🟠"
    else:
        status = "none"
        status_text = "بدون بورسیه 🔴"
    
    return ISEEResult(
        isee=round(isee, 2),
        ise=round(ise, 2),
        isp=round(isp, 2),
        scale=scale,
        status=status,
        status_text=status_text,
        rent_deduction=rent_deduction,
        home_exemption=home_exemption,
        financial_exemption=financial_exemption,
        debt_deduction=debt_deduction,
        adjusted_income=adjusted_income,
        adjusted_property=adjusted_property,
        adjusted_financial=adjusted_financial,
        total_patrimony=total_patrimony,
        inputs=inputs,
    )


# ═══════════════════════════════════════════════════════════════════
# بخش ۲.۷: محاسبه‌گر معکوس (Reverse Calculator)
# ═══════════════════════════════════════════════════════════════════

def calculate_reverse_isee(
    target_isee: float,
    current_inputs: ISEEInput,
    thresholds: ISEEThresholds = None
) -> Dict[str, Any]:
    """
    محاسبه معکوس: برای رسیدن به ISEE هدف چه تغییراتی لازم است؟
    
    Returns:
        دیکشنری شامل راه‌کارهای مختلف
    """
    current_result = calculate_isee(current_inputs, thresholds)
    current_isee = current_result.isee
    
    if current_isee <= target_isee:
        return {
            "already_achieved": True,
            "current": current_isee,
            "target": target_isee,
            "message": "شما از قبل به هدف رسیده‌اید! 🎉"
        }
    
    gap = current_isee - target_isee
    scale = current_result.scale
    
    strategies = []
    
    # ═══ استراتژی ۱: کاهش درآمد ═══
    income_reduction_needed = gap * scale
    if income_reduction_needed <= current_inputs.income:
        strategies.append({
            "type": "income",
            "title": "کاهش درآمد اظهار شده",
            "amount": income_reduction_needed,
            "description": f"اگر درآمد {income_reduction_needed:,.0f}€ کمتر اظهار شود",
            "feasibility": "medium",
        })
    
    # ═══ استراتژی ۲: کاهش دارایی ═══
    patrimony_reduction_needed = gap * scale / 0.20
    if patrimony_reduction_needed <= current_result.total_patrimony:
        strategies.append({
            "type": "patrimony",
            "title": "کاهش دارایی",
            "amount": patrimony_reduction_needed,
            "description": f"فروش/انتقال {patrimony_reduction_needed:,.0f}€ از دارایی",
            "feasibility": "high",
        })
    
    # ═══ استراتژی ۳: افزایش اعضا ═══
    for extra_members in range(1, 4):
        new_members = current_inputs.members + extra_members
        new_scale = calculate_family_scale(new_members)
        new_isee = current_result.ise / new_scale
        
        if new_isee <= target_isee:
            strategies.append({
                "type": "members",
                "title": f"افزایش اعضا به {new_members} نفر",
                "amount": extra_members,
                "description": f"با {new_members} عضو خانواده، ISEE ≈ {new_isee:,.0f}€",
                "feasibility": "low",
            })
            break
    
    # ═══ استراتژی ۴: اجاره‌نشین شدن ═══
    if not current_inputs.is_tenant:
        max_rent_benefit = DEDUCTION_LIMITS.max_rent_deduction
        potential_reduction = max_rent_benefit / scale
        
        strategies.append({
            "type": "rent",
            "title": "اجاره‌نشین بودن",
            "amount": max_rent_benefit,
            "description": f"کسر تا {max_rent_benefit:,}€ از درآمد → کاهش {potential_reduction:,.0f}€ از ISEE",
            "feasibility": "medium",
        })
    
    return {
        "already_achieved": False,
        "current": current_isee,
        "target": target_isee,
        "gap": gap,
        "strategies": strategies,
    }


# ═══════════════════════════════════════════════════════════════════
# بخش ۲.۸: توابع کمکی UI
# ═══════════════════════════════════════════════════════════════════

def generate_progress_bar(current_step: int, total_steps: int = TOTAL_STEPS) -> str:
    """ساخت نوار پیشرفت زیبا"""
    filled = "🟩" * current_step
    empty = "⬜" * (total_steps - current_step)
    percent = int((current_step / total_steps) * 100)
    return f"{filled}{empty} {percent}%"


def build_back_keyboard(previous_callback: str, cancel: bool = True) -> InlineKeyboardMarkup:
    """کیبورد با دکمه بازگشت"""
    buttons = []
    
    if previous_callback:
        buttons.append([
            InlineKeyboardButton(text="🔙 مرحله قبل", callback_data=previous_callback)
        ])
    
    if cancel:
        buttons.append([
            InlineKeyboardButton(text="❌ لغو", callback_data="isee_cancel")
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_yes_no_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    """کیبورد بله/خیر"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ بله", callback_data=yes_data),
            InlineKeyboardButton(text="❌ خیر", callback_data=no_data),
        ]
    ])


def build_amount_keyboard(
    include_zero: bool = True,
    amounts_toman: List[str] = None,
    amounts_euro: List[str] = None
) -> ReplyKeyboardMarkup:
    """کیبورد انتخاب سریع مقادیر"""
    
    keyboard = []
    
    if include_zero:
        keyboard.append([KeyboardButton(text="0"), KeyboardButton(text="ندارم")])
    
    if amounts_toman:
        row = [KeyboardButton(text=amt) for amt in amounts_toman[:3]]
        keyboard.append(row)
        if len(amounts_toman) > 3:
            row2 = [KeyboardButton(text=amt) for amt in amounts_toman[3:6]]
            keyboard.append(row2)
    
    if amounts_euro:
        row = [KeyboardButton(text=f"{amt}€") for amt in amounts_euro[:3]]
        keyboard.append(row)
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )


def format_currency(amount: float, currency: str = "EUR") -> str:
    """فرمت زیبای مقادیر پولی"""
    if currency == "EUR":
        return f"{amount:,.0f} €"
    elif currency == "TOMAN":
        if amount >= 1_000_000_000:
            return f"{amount/1_000_000_000:.1f} میلیارد ت"
        elif amount >= 1_000_000:
            return f"{amount/1_000_000:.0f} میلیون ت"
        else:
            return f"{amount:,.0f} ت"
    return f"{amount:,.0f}"


def get_comparison_text(isee: float) -> str:
    """مقایسه با آمار دانشجویان ایرانی"""
    avg = IRANIAN_STATS["average"]
    median = IRANIAN_STATS["median"]
    
    if isee <= IRANIAN_STATS["p25"]:
        return "🌟 عالی! در ۲۵٪ پایین ایرانی‌ها"
    elif isee <= median:
        return "✅ خوب! زیر میانه ایرانی‌ها"
    elif isee <= avg:
        return "👍 مناسب - زیر میانگین"
    elif isee <= IRANIAN_STATS["p75"]:
        return "⚖️ متوسط - در بازه معمول"
    else:
        return "⚠️ بالاتر از ۷۵٪ ایرانی‌ها"


# ═══════════════════════════════════════════════════════════════════
# بخش ۲.۹: نکات و راهنماها
# ═══════════════════════════════════════════════════════════════════

def get_reduction_tips() -> str:
    """نکات طلایی برای کاهش ISEE"""
    return """
💡 <b>ترفندهای قانونی کاهش ISEE:</b>

<b>📅 قبل از ۳۱ دسامبر:</b>

1️⃣ <b>تخلیه حساب بانکی:</b>
   موجودی این تاریخ ملاک است، نه میانگین سال!
   پول را به طلا، ملک یا حساب دیگران منتقل کنید.

2️⃣ <b>انتقال دارایی:</b>
   اموال را به نام پدربزرگ/مادربزرگ منتقل کنید.
   ⚠️ باید واقعی باشد، نه صوری!

3️⃣ <b>فروش خودروی گران:</b>
   ارزش خودرو جزء دارایی محسوب می‌شود.

<b>🏠 مربوط به مسکن:</b>

4️⃣ <b>اجاره‌نشین باشید:</b>
   تا ۷,۰۰۰€ از درآمد کسر می‌شود.

5️⃣ <b>اعلام بدهی:</b>
   وام مسکن از ارزش ملک کسر می‌شود.

<b>👨‍🎓 مربوط به دانشجو:</b>

6️⃣ <b>استقلال مالی:</b>
   ۲ سال زندگی مستقل + درآمد ۹,۰۰۰€ = ISEE شخصی!

7️⃣ <b>ازدواج:</b>
   خانواده جدید = ISEE جداگانه

⚠️ <i>همه موارد باید قانونی و مستند باشد!</i>
"""


def get_isee_parificato_info() -> str:
    """اطلاعات ISEE Parificato برای دانشجویان غیر EU"""
    return """
🌍 <b>ISEE Parificato چیست؟</b>

برای دانشجویان غیر اروپایی (مثل ایرانی‌ها)، ISEE معمولی قابل صدور نیست.
باید <b>ISEE Parificato</b> بگیرید.

━━━━━━━━━━━━━━━━━━━━

📋 <b>مدارک مورد نیاز:</b>

1️⃣ گواهی درآمد خانواده از ایران
   (ترجمه رسمی + تأیید سفارت/کنسولگری)

2️⃣ گواهی دارایی‌ها (ملک، خودرو، حساب)
   (ترجمه رسمی + تأیید)

3️⃣ شناسنامه/کارت ملی اعضای خانواده
   (ترجمه رسمی)

4️⃣ اجاره‌نامه یا سند مالکیت محل سکونت
   (ترجمه رسمی)

━━━━━━━━━━━━━━━━━━━━

🏢 <b>کجا صادر می‌شود؟</b>
مراکز CAF در ایتالیا (مثل CAF CGIL, CAF CISL)

💰 <b>هزینه تقریبی:</b>
۳۰ تا ۸۰ یورو (بسته به مرکز)

⏱ <b>زمان صدور:</b>
۱ تا ۳ هفته

━━━━━━━━━━━━━━━━━━━━

💡 <b>نکته مهم:</b>
بعضی CAFها تجربه کمی با پرونده ایرانی‌ها دارند.
از CAFهای بزرگ در شهرهای دانشگاهی استفاده کنید.
"""


# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# بخش ۳.۱: هندلر اصلی شروع ISEE
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee")
async def start_isee_calculator(callback: types.CallbackQuery, state: FSMContext):
    """نقطه ورود اصلی محاسبه‌گر ISEE"""
    user_id = callback.from_user.id
    
    # پاکسازی داده قبلی
    data_store.clear_current(user_id)
    await state.clear()
    
    # نمایش پیام انتظار
    wait_msg = await callback.message.edit_text(
        "⏳ <b>در حال آماده‌سازی محاسبه‌گر...</b>\n"
        "📡 دریافت آخرین نرخ ارز...",
        parse_mode="HTML"
    )
    
    # دریافت نرخ ارز
    eur_rate, is_live = await get_eur_rate()
    
    # ذخیره در داده‌های کاربر
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    user_input.eur_rate = eur_rate
    user_input.created_at = datetime.now().strftime("%Y/%m/%d %H:%M")
    
    # وضعیت نرخ ارز
    rate_status = "🟢 زنده" if is_live else "🟡 تقریبی"
    
    # ساخت متن خوش‌آمدگویی
    text = f"""
🧮 <b>محاسبه‌گر هوشمند ISEE 2025</b>

━━━━━━━━━━━━━━━━━━━━━━━━━
💶 <b>نرخ یورو:</b> {eur_rate:,} تومان ({rate_status})
📅 <b>سال تحصیلی:</b> 2025-2026
━━━━━━━━━━━━━━━━━━━━━━━━━

📌 <b>ISEE چیست؟</b>
شاخصی که وضعیت اقتصادی خانواده را نشان می‌دهد.
این عدد تعیین‌کننده:

   💰 دریافت بورسیه تحصیلی (تا ۷,۰۰۰€ در سال)
   🏠 اولویت خوابگاه دانشجویی
   📉 میزان تخفیف شهریه
   🍽 کارت غذای ارزان (Mensa)

━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 <b>آستانه‌های کلیدی:</b>

🟢 زیر <b>۲۵,۵۰۰€</b> → بورسیه کامل + خوابگاه
🟡 ۲۵.۵ تا <b>۳۶,۰۰۰€</b> → بورسیه جزئی  
🟠 ۳۶ تا <b>۵۰,۰۰۰€</b> → فقط تخفیف شهریه
🔴 بالای ۵۰,۰۰۰€ → بدون تخفیف

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # نمایش آخرین محاسبه اگر وجود دارد
    history = user.get("history", [])
    if history:
        last = history[-1]
        status_emoji = STATUS_CONFIG.get(last.get("status", "none"), {}).get("color", "⚪")
        text += f"\n📊 <b>آخرین محاسبه:</b> {status_emoji} {last['isee']:,.0f}€\n"
        text += f"   📅 {last['date']}\n"
    
    # کیبورد اصلی
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 محاسبه کامل", callback_data="isee_mode_full"),
            InlineKeyboardButton(text="⚡ محاسبه سریع", callback_data="isee_mode_quick"),
        ],
        [
            InlineKeyboardButton(text="📜 تاریخچه", callback_data="isee_history"),
            InlineKeyboardButton(text="💡 نکات طلایی", callback_data="isee_tips"),
        ],
        [
            InlineKeyboardButton(text="🌍 ISEE Parificato", callback_data="isee_parificato"),
        ],
        [
            InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="main_menu"),
        ]
    ])
    
    await wait_msg.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.intro)


# ═══════════════════════════════════════════════════════════════════
# بخش ۳.۲: انتخاب حالت محاسبه
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee_mode_full")
async def select_full_mode(callback: types.CallbackQuery, state: FSMContext):
    """انتخاب حالت محاسبه کامل"""
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    user["settings"]["mode"] = "full"
    
    text = """
📋 <b>حالت محاسبه کامل</b>

در این حالت تمام پارامترها پرسیده می‌شود:

✅ درآمد سالانه خانواده
✅ وضعیت اجاره/مالکیت
✅ تعداد اعضای خانواده
✅ ارزش املاک و مستغلات
✅ دارایی‌های مالی (پس‌انداز، سهام)
✅ بدهی‌ها و وام‌ها
✅ دارایی خارج از ایران
✅ وضعیت استقلال دانشجو

━━━━━━━━━━━━━━━━━━━━━━━━━

⏱ <b>زمان تقریبی:</b> ۳-۵ دقیقه
🎯 <b>دقت:</b> بالا (نزدیک به ISEE واقعی)

━━━━━━━━━━━━━━━━━━━━━━━━━

🗺 <b>ابتدا منطقه دانشگاه را انتخاب کنید:</b>
<i>(آستانه‌های بورسیه بر اساس منطقه متفاوت است)</i>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏔 شمال ایتالیا", callback_data="isee_region_nord"),
        ],
        [
            InlineKeyboardButton(text="🏛 مرکز ایتالیا", callback_data="isee_region_centro"),
        ],
        [
            InlineKeyboardButton(text="🌊 جنوب ایتالیا", callback_data="isee_region_sud"),
        ],
        [
            InlineKeyboardButton(text="❓ نمی‌دانم", callback_data="isee_region_default"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.select_region)


@router.callback_query(F.data == "isee_mode_quick")
async def select_quick_mode(callback: types.CallbackQuery, state: FSMContext):
    """انتخاب حالت محاسبه سریع"""
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    user["settings"]["mode"] = "quick"
    
    text = """
⚡ <b>حالت محاسبه سریع</b>

در این حالت فقط ۳ سؤال اصلی پرسیده می‌شود:

1️⃣ درآمد سالانه خانواده
2️⃣ تعداد اعضای خانواده  
3️⃣ مجموع دارایی‌ها (ملک + پس‌انداز)

━━━━━━━━━━━━━━━━━━━━━━━━━

⏱ <b>زمان تقریبی:</b> ۱ دقیقه
⚠️ <b>دقت:</b> تخمینی (محافظه‌کارانه)

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>نکته:</b>
این حالت برای تخمین اولیه مناسب است.
برای نتیجه دقیق‌تر از حالت کامل استفاده کنید.

━━━━━━━━━━━━━━━━━━━━━━━━━

🗺 <b>منطقه دانشگاه را انتخاب کنید:</b>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏔 شمال", callback_data="isee_region_nord"),
            InlineKeyboardButton(text="🏛 مرکز", callback_data="isee_region_centro"),
            InlineKeyboardButton(text="🌊 جنوب", callback_data="isee_region_sud"),
        ],
        [
            InlineKeyboardButton(text="❓ نمی‌دانم (پیش‌فرض)", callback_data="isee_region_default"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.select_region)


# ═══════════════════════════════════════════════════════════════════
# بخش ۳.۳: انتخاب منطقه
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("isee_region_"))
async def select_region(callback: types.CallbackQuery, state: FSMContext):
    """انتخاب منطقه و شروع سؤالات"""
    user_id = callback.from_user.id
    user_input = data_store.get_current_input(user_id)
    user = data_store.get_user(user_id)
    
    # تعیین منطقه
    region_code = callback.data.replace("isee_region_", "")
    
    region_map = {
        "nord": Region.NORD,
        "centro": Region.CENTRO,
        "sud": Region.SUD,
        "default": Region.CENTRO,
    }
    
    region_names = {
        Region.NORD: "🏔 شمال ایتالیا (Milano, Torino, Bologna...)",
        Region.CENTRO: "🏛 مرکز ایتالیا (Roma, Firenze, Pisa...)",
        Region.SUD: "🌊 جنوب ایتالیا (Napoli, Bari, Palermo...)",
    }
    
    selected_region = region_map.get(region_code, Region.CENTRO)
    user_input.region = selected_region
    
    # دریافت آستانه‌های منطقه
    thresholds = REGIONAL_THRESHOLDS[selected_region]
    
    # تأیید و شروع
    mode = user.get("settings", {}).get("mode", "full")
    mode_text = "کامل" if mode == "full" else "سریع"
    
    text = f"""
✅ <b>تنظیمات ذخیره شد!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

📍 <b>منطقه:</b> {region_names[selected_region]}
⚙️ <b>حالت:</b> محاسبه {mode_text}

━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 <b>آستانه‌های این منطقه:</b>

🟢 بورسیه کامل: زیر <b>{thresholds.full_scholarship:,}€</b>
🟡 بورسیه جزئی: تا <b>{thresholds.partial_scholarship:,}€</b>
🟠 تخفیف شهریه: تا <b>{thresholds.reduced_fee:,}€</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

<b>آماده شروع هستید؟</b>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="▶️ شروع محاسبه", callback_data="isee_begin"),
        ],
        [
            InlineKeyboardButton(text="🔄 تغییر تنظیمات", callback_data="isee"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════
# بخش ۳.۴: شروع سؤالات
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee_begin")
async def begin_questions(callback: types.CallbackQuery, state: FSMContext):
    """شروع مراحل سؤالات"""
    await callback.message.delete()
    await ask_income(callback.message, state, callback.from_user.id)


@router.callback_query(F.data == "isee_start")
async def quick_start(callback: types.CallbackQuery, state: FSMContext):
    """شروع سریع (بدون انتخاب منطقه - پیش‌فرض)"""
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    
    # تنظیمات پیش‌فرض
    user_input.region = Region.CENTRO
    user["settings"]["mode"] = "full"
    
    await callback.message.delete()
    await ask_income(callback.message, state, user_id)


# ═══════════════════════════════════════════════════════════════════
# بخش ۳.۵: نمایش تاریخچه
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee_history")
async def show_history(callback: types.CallbackQuery):
    """نمایش تاریخچه محاسبات"""
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    history = user.get("history", [])
    
    if not history:
        await callback.answer("📭 هنوز محاسبه‌ای انجام نداده‌اید!", show_alert=True)
        return
    
    text = """
📜 <b>تاریخچه محاسبات شما</b>

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # نمایش ۱۰ مورد آخر
    for idx, record in enumerate(reversed(history[-10:]), 1):
        isee_val = record.get("isee", 0)
        date = record.get("date", "نامشخص")
        status = record.get("status", "none")
        
        config = STATUS_CONFIG.get(status, STATUS_CONFIG["none"])
        emoji = config["color"]
        
        text += f"\n{idx}. {emoji} <b>{isee_val:,.0f}€</b>"
        text += f"\n   📅 {date}"
        
        # نمایش خلاصه ورودی‌ها
        inputs_summary = record.get("inputs_summary", {})
        if inputs_summary:
            income = inputs_summary.get("income", 0)
            members = inputs_summary.get("members", 0)
            text += f"\n   👥 {members} نفر | 💰 {income:,.0f}€ درآمد"
        
        text += "\n"
    
    # تحلیل روند
    if len(history) >= 2:
        first_isee = history[0].get("isee", 0)
        last_isee = history[-1].get("isee", 0)
        diff = last_isee - first_isee
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "📈 <b>تحلیل روند:</b>\n\n"
        
        if diff < -3000:
            text += f"✅ کاهش چشمگیر: <b>{abs(diff):,.0f}€</b>\n"
            text += "عالی! استراتژی‌های شما مؤثر بوده!"
        elif diff < 0:
            text += f"👍 کاهش: <b>{abs(diff):,.0f}€</b>\n"
            text += "در مسیر درستی هستید."
        elif diff < 3000:
            text += f"➡️ تقریباً ثابت\n"
            text += "تغییر خاصی نداشته‌اید."
        else:
            text += f"⚠️ افزایش: <b>{diff:,.0f}€</b>\n"
            text += "بررسی کنید چه تغییری داشته‌اید."
    
    # آمار
    if len(history) >= 3:
        isee_values = [r.get("isee", 0) for r in history]
        avg = sum(isee_values) / len(isee_values)
        min_val = min(isee_values)
        max_val = max(isee_values)
        
        text += f"\n\n📊 <b>آمار:</b>"
        text += f"\n   میانگین: {avg:,.0f}€"
        text += f"\n   کمترین: {min_val:,.0f}€"
        text += f"\n   بیشترین: {max_val:,.0f}€"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 محاسبه جدید", callback_data="isee_mode_full"),
        ],
        [
            InlineKeyboardButton(text="🔄 مقایسه با سناریو", callback_data="isee_whatif_intro"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════
# بخش ۳.۶: نمایش نکات طلایی
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee_tips")
async def show_tips(callback: types.CallbackQuery):
    """نمایش نکات و ترفندهای کاهش ISEE"""
    
    text = get_reduction_tips()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎯 محاسبه‌گر معکوس", callback_data="isee_reverse_intro"),
        ],
        [
            InlineKeyboardButton(text="🚀 شروع محاسبه", callback_data="isee_mode_full"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════
# بخش ۳.۷: اطلاعات ISEE Parificato
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee_parificato")
async def show_parificato_info(callback: types.CallbackQuery):
    """نمایش اطلاعات ISEE Parificato"""
    
    text = get_isee_parificato_info()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 لیست CAF های معتبر", callback_data="isee_caf_list"),
        ],
        [
            InlineKeyboardButton(text="🚀 شروع محاسبه", callback_data="isee_mode_full"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "isee_caf_list")
async def show_caf_list(callback: types.CallbackQuery):
    """لیست CAF های پیشنهادی"""
    
    text = """
🏢 <b>لیست CAF های پیشنهادی برای ISEE Parificato</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

🔵 <b>CAF CGIL</b>
   بزرگترین شبکه CAF در ایتالیا
   🌐 www.cafcgil.it
   ✅ تجربه زیاد با دانشجویان خارجی

🟢 <b>CAF CISL</b>
   شبکه گسترده در سراسر ایتالیا
   🌐 www.cafcisl.it
   ✅ خدمات آنلاین

🟡 <b>CAF UIL</b>
   🌐 www.cafuil.it
   ✅ هزینه مناسب

🔴 <b>CAF ACLI</b>
   🌐 www.acli.it
   ✅ حضور در شهرهای کوچک

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>نکات مهم:</b>

• حتماً از قبل وقت بگیرید (۱-۲ هفته زودتر)
• همه مدارک ترجمه شده را ببرید
• از CAF در شهر دانشگاهی استفاده کنید
• هزینه را قبل از مراجعه بپرسید

━━━━━━━━━━━━━━━━━━━━━━━━━

📞 <b>قبل از مراجعه بپرسید:</b>
"Fate ISEE Parificato per studenti stranieri?"
(آیا برای دانشجویان خارجی ISEE Parificato صادر می‌کنید؟)
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee_parificato"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════
# بخش ۳.۸: لغو و بازگشت
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee_cancel")
async def cancel_calculation(callback: types.CallbackQuery, state: FSMContext):
    """لغو محاسبه و بازگشت به منوی ISEE"""
    user_id = callback.from_user.id
    
    # پاکسازی
    data_store.clear_current(user_id)
    await state.clear()
    
    # حذف کیبورد reply اگر وجود دارد
    try:
        await callback.message.answer(
            "❌ محاسبه لغو شد.",
            reply_markup=ReplyKeyboardRemove()
        )
    except:
        pass
    
    # بازگشت به صفحه اصلی ISEE
    await start_isee_calculator(callback, state)


@router.callback_query(F.data == "isee_back_to_intro")
async def back_to_intro(callback: types.CallbackQuery, state: FSMContext):
    """بازگشت به صفحه اول بدون پاکسازی داده"""
    await start_isee_calculator(callback, state)


# ═══════════════════════════════════════════════════════════════════
# بخش ۳.۹: هندلر پیام‌های اشتباه در مرحله intro
# ═══════════════════════════════════════════════════════════════════

@router.message(ISEEState.intro)
async def handle_intro_message(message: types.Message):
    """راهنمایی کاربر در صورت ارسال پیام متنی در مرحله intro"""
    
    await message.reply(
        "⚠️ <b>لطفاً از دکمه‌های زیر استفاده کنید:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🚀 محاسبه کامل", callback_data="isee_mode_full"),
                InlineKeyboardButton(text="⚡ سریع", callback_data="isee_mode_quick"),
            ],
            [
                InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="main_menu"),
            ]
        ]),
        parse_mode="HTML"
    )


@router.message(ISEEState.select_region)
async def handle_region_message(message: types.Message):
    """راهنمایی در مرحله انتخاب منطقه"""
    
    await message.reply(
        "⚠️ <b>لطفاً منطقه را از دکمه‌ها انتخاب کنید:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🏔 شمال", callback_data="isee_region_nord"),
                InlineKeyboardButton(text="🏛 مرکز", callback_data="isee_region_centro"),
                InlineKeyboardButton(text="🌊 جنوب", callback_data="isee_region_sud"),
            ],
            [
                InlineKeyboardButton(text="❓ نمی‌دانم", callback_data="isee_region_default"),
            ]
        ]),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════
# بخش ۳.۱۰: معرفی محاسبه‌گر معکوس
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee_reverse_intro")
async def reverse_calculator_intro(callback: types.CallbackQuery, state: FSMContext):
    """معرفی محاسبه‌گر معکوس"""
    
    text = """
🎯 <b>محاسبه‌گر معکوس ISEE</b>

این ابزار به شما می‌گوید:
<i>«برای رسیدن به ISEE مورد نظر، چه کار کنم؟»</i>

━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 <b>قابلیت‌ها:</b>

• تعیین هدف (مثلاً ۲۵,۰۰۰€ برای بورسیه کامل)
• محاسبه میزان کاهش لازم در هر پارامتر
• پیشنهاد استراتژی‌های عملی
• مقایسه سناریوهای مختلف

━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>پیش‌نیاز:</b>
ابتدا باید یک محاسبه کامل انجام داده باشید.

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    history = user.get("history", [])
    
    if history:
        last_isee = history[-1].get("isee", 0)
        text += f"\n📊 <b>آخرین ISEE شما:</b> {last_isee:,.0f}€\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎯 هدف: ۲۵,۵۰۰€ (بورسیه کامل)", callback_data="isee_reverse_25500"),
            ],
            [
                InlineKeyboardButton(text="🎯 هدف: ۲۰,۰۰۰€", callback_data="isee_reverse_20000"),
            ],
            [
                InlineKeyboardButton(text="🎯 هدف: ۱۵,۰۰۰€", callback_data="isee_reverse_15000"),
            ],
            [
                InlineKeyboardButton(text="✏️ هدف دلخواه", callback_data="isee_reverse_custom"),
            ],
            [
                InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee_tips"),
            ]
        ])
    else:
        text += "\n⚠️ ابتدا یک محاسبه انجام دهید.\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🚀 شروع محاسبه", callback_data="isee_mode_full"),
            ],
            [
                InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee_tips"),
            ]
        ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════
# بخش ۳.۱۱: معرفی سناریوی What-If
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee_whatif_intro")
async def whatif_intro(callback: types.CallbackQuery):
    """معرفی ابزار سناریوی فرضی"""
    
    text = """
🔮 <b>سناریوی «اگر...»</b>

بدون تغییر تاریخچه، ببینید اگر شرایط فرق داشت، ISEE چقدر می‌شد!

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>مثال‌ها:</b>

• اگر ماشین را بفروشم؟
• اگر ۱ نفر به خانواده اضافه شود؟
• اگر پس‌انداز را خالی کنم؟
• اگر مستأجر شویم؟

━━━━━━━━━━━━━━━━━━━━━━━━━

<i>این قابلیت به زودی فعال می‌شود...</i>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 بازگشت به تاریخچه", callback_data="isee_history"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# بخش ۴.۱: مرحله ۱ - سؤال درآمد سالانه
# ═══════════════════════════════════════════════════════════════════

async def ask_income(message: types.Message, state: FSMContext, user_id: int):
    """مرحله اول: سؤال درآمد سالانه خانواده"""
    
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    eur_rate = user_input.eur_rate
    mode = user.get("settings", {}).get("mode", "full")
    
    # تعیین تعداد مراحل بر اساس حالت
    total = TOTAL_STEPS if mode == "full" else QUICK_MODE_STEPS
    progress = generate_progress_bar(1, total)
    
    text = f"""
{STEP_EMOJI[1]} <b>مرحله ۱ از {total}: درآمد سالانه</b>
{progress}

━━━━━━━━━━━━━━━━━━━━━━━━━

💵 <b>مجموع درآمد خالص سالانه خانواده</b> را وارد کنید.

📋 <b>شامل:</b>
• حقوق و دستمزد پدر و مادر (بعد از کسر مالیات)
• درآمد شغل آزاد و کسب‌وکار
• اجاره دریافتی از ملک (اگر دارید)
• سود سپرده و سرمایه‌گذاری
• مستمری و بازنشستگی

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>راهنما:</b>
به <b>تومان</b> یا <b>یورو</b> وارد کنید.
سیستم هوشمند تشخیص می‌دهد!

💶 نرخ تبدیل: <b>{eur_rate:,}</b> تومان = 1€

━━━━━━━━━━━━━━━━━━━━━━━━━

<i>💬 مثال: «۲۰۰ میلیون» یا «3000» یا «150000000»</i>
"""
    
    # کیبورد سریع
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="۱۰۰ میلیون"), KeyboardButton(text="۲۰۰ میلیون")],
            [KeyboardButton(text="۳۰۰ میلیون"), KeyboardButton(text="۵۰۰ میلیون")],
            [KeyboardButton(text="۱ میلیارد"), KeyboardButton(text="۲ میلیارد")],
            [KeyboardButton(text="نمی‌دانم 🤔")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.waiting_income)


# ═══════════════════════════════════════════════════════════════════
# بخش ۴.۲: پردازش درآمد سالانه
# ═══════════════════════════════════════════════════════════════════

@router.message(ISEEState.waiting_income)
async def process_income(message: types.Message, state: FSMContext):
    """پردازش درآمد وارد شده"""
    
    user_id = message.from_user.id
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    eur_rate = user_input.eur_rate
    
    raw_text = message.text.strip()
    
    # ═══ چک عبارت "نمی‌دانم" ═══
    if "نمی‌دانم" in raw_text or "نمیدانم" in raw_text or "🤔" in raw_text:
        help_text = """
💡 <b>راهنمای محاسبه درآمد سالانه:</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>روش ساده:</b>
حقوق ماهانه پدر + مادر را در <b>۱۲</b> ضرب کنید.

<b>مثال:</b>
• پدر ماهی ۱۵ میلیون
• مادر ماهی ۱۰ میلیون
• جمع: ۲۵ × ۱۲ = <b>۳۰۰ میلیون</b> سالانه

━━━━━━━━━━━━━━━━━━━━━━━━━

📋 <b>موارد دیگر را اضافه کنید:</b>
• اگر ملکی اجاره داده‌اید → + اجاره سالانه
• اگر کسب‌وکار دارید → + سود خالص سالانه
• سود سپرده بانکی → + سود دریافتی

━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 <b>بازه‌های معمول ایرانی‌ها:</b>

• خانواده کم‌درآمد: ۱۰۰-۲۰۰ میلیون
• متوسط: ۲۰۰-۵۰۰ میلیون  
• مرفه: ۵۰۰ میلیون - ۲ میلیارد

━━━━━━━━━━━━━━━━━━━━━━━━━

<b>حالا عدد تقریبی را وارد کنید:</b>
"""
        await message.reply(help_text, parse_mode="HTML")
        return
    
    # ═══ تبدیل به عدد ═══
    amount = parse_persian_amount(raw_text)
    
    if amount is None:
        await message.reply(
            "⚠️ <b>عدد نامعتبر!</b>\n\n"
            "لطفاً یک عدد صحیح وارد کنید.\n\n"
            "✅ <b>فرمت‌های قابل قبول:</b>\n"
            "• <code>150000000</code>\n"
            "• <code>۱۵۰ میلیون</code>\n"
            "• <code>1.5 میلیارد</code>\n"
            "• <code>3000</code> (یورو)",
            parse_mode="HTML"
        )
        return
    
    # ═══ بررسی منطقی بودن ═══
    if amount < 0:
        await message.reply("⚠️ درآمد نمی‌تواند منفی باشد!")
        return
    
    # ═══ تبدیل به یورو ═══
    income_eur, currency_type, display = smart_currency_convert(
        amount, eur_rate, raw_text, context="income"
    )
    
    # ═══ هشدار در صورت مقدار مبهم ═══
    warning_text = ""
    if currency_type == CurrencyType.AMBIGUOUS:
        warning_text = "\n\n⚠️ <i>مقدار به یورو فرض شد. اگر تومان بود، بنویسید «تومان».</i>"
    
    # ═══ بررسی واقع‌بینانه بودن ═══
    if income_eur > 200000:
        await message.reply(
            f"⚠️ <b>مقدار خیلی بزرگ به نظر می‌رسد!</b>\n\n"
            f"شما وارد کردید: {display}\n"
            f"معادل: <b>{income_eur:,.0f}€</b> در سال\n\n"
            f"آیا مطمئنید؟ اگر اشتباه است، دوباره وارد کنید.",
            parse_mode="HTML"
        )
        # ادامه می‌دهیم اما هشدار دادیم
    
    if income_eur < 500 and amount > 100:
        # احتمالاً اشتباه تشخیص داده شده
        await message.reply(
            f"⚠️ <b>توجه!</b>\n\n"
            f"مقدار وارد شده ({display}) به نظر کم می‌آید.\n"
            f"معادل: <b>{income_eur:,.0f}€</b> در سال\n\n"
            f"اگر منظورتان <b>تومان</b> بود، لطفاً دوباره بنویسید:\n"
            f"مثال: <code>{amount:,.0f} تومان</code>",
            parse_mode="HTML"
        )
        return
    
    # ═══ ذخیره ═══
    user_input.income = income_eur
    
    # ذخیره برای نمایش (در confirm)
    if "display_values" not in user:
        user["display_values"] = {}
    user["display_values"]["income"] = display
    
    # ═══ تأیید ═══
    text = f"""
✅ <b>درآمد سالانه ثبت شد!</b>

💵 مقدار وارد شده: <b>{display}</b>
💶 معادل یورو: <b>{income_eur:,.0f} €</b>{warning_text}

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await message.reply(text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    await asyncio.sleep(0.5)
    
    # ═══ رفتن به مرحله بعد ═══
    mode = user.get("settings", {}).get("mode", "full")
    
    if mode == "full":
        # حالت کامل: سؤال اجاره
        await ask_tenant_status(message, state, user_id)
    else:
        # حالت سریع: مستقیم به اعضا
        await ask_members(message, state, user_id)


# ═══════════════════════════════════════════════════════════════════
# بخش ۴.۳: مرحله ۲ - سؤال وضعیت اجاره‌نشینی
# ═══════════════════════════════════════════════════════════════════

async def ask_tenant_status(message: types.Message, state: FSMContext, user_id: int):
    """سؤال آیا خانواده مستأجر است؟"""
    
    user = data_store.get_user(user_id)
    mode = user.get("settings", {}).get("mode", "full")
    total = TOTAL_STEPS if mode == "full" else QUICK_MODE_STEPS
    
    progress = generate_progress_bar(2, total)
    
    text = f"""
{STEP_EMOJI[2]} <b>مرحله ۲ از {total}: وضعیت مسکن</b>
{progress}

━━━━━━━━━━━━━━━━━━━━━━━━━

🏠 <b>آیا خانواده شما مستأجر هستند؟</b>

<i>(یعنی خانه‌ای که در آن زندگی می‌کنید اجاره‌ای است)</i>

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>چرا مهم است؟</b>
اگر مستأجر باشید، تا <b>۷,۰۰۰€</b> از درآمد کسر می‌شود!
این یعنی ISEE پایین‌تر و شانس بورسیه بیشتر.

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ بله، مستأجریم", callback_data="isee_tenant_yes"),
            InlineKeyboardButton(text="❌ خیر، مالک هستیم", callback_data="isee_tenant_no"),
        ],
        [
            InlineKeyboardButton(text="🔙 مرحله قبل", callback_data="isee_back_to_income"),
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.waiting_rent)


# ═══════════════════════════════════════════════════════════════════
# بخش ۴.۴: پردازش پاسخ وضعیت اجاره
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee_tenant_yes")
async def tenant_yes(callback: types.CallbackQuery, state: FSMContext):
    """کاربر مستأجر است - سؤال مبلغ اجاره"""
    
    user_id = callback.from_user.id
    user_input = data_store.get_current_input(user_id)
    user_input.is_tenant = True
    
    eur_rate = user_input.eur_rate
    
    text = f"""
🏠 <b>اجاره سالانه</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

💰 <b>مبلغ اجاره سالانه</b> خانه را وارد کنید.

📋 <b>محاسبه:</b>
اجاره ماهانه × ۱۲ = اجاره سالانه

<b>مثال:</b>
اگر ماهی ۵ میلیون اجاره می‌دهید:
۵ × ۱۲ = <b>۶۰ میلیون</b> سالانه

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>نکته مهم:</b>
حداکثر <b>۷,۰۰۰€</b> (≈ {7000 * eur_rate // 1000000} میلیون تومان) 
از درآمد کسر می‌شود.

━━━━━━━━━━━━━━━━━━━━━━━━━

<i>به تومان یا یورو وارد کنید:</i>
"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="۳۰ میلیون"), KeyboardButton(text="۵۰ میلیون")],
            [KeyboardButton(text="۶۰ میلیون"), KeyboardButton(text="۸۰ میلیون")],
            [KeyboardButton(text="۱۰۰ میلیون"), KeyboardButton(text="۱۵۰ میلیون")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.message.answer("👆 مبلغ اجاره سالانه:", reply_markup=keyboard)


@router.callback_query(F.data == "isee_tenant_no")
async def tenant_no(callback: types.CallbackQuery, state: FSMContext):
    """کاربر مالک است - رفتن به مرحله بعد"""
    
    user_id = callback.from_user.id
    user_input = data_store.get_current_input(user_id)
    user_input.is_tenant = False
    user_input.annual_rent = 0
    
    await callback.message.edit_text(
        "✅ <b>ثبت شد:</b> خانواده مالک هستند.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )
    
    await asyncio.sleep(0.5)
    
    # رفتن به مرحله اعضا
    await ask_members(callback.message, state, user_id)


# ═══════════════════════════════════════════════════════════════════
# بخش ۴.۵: پردازش مبلغ اجاره
# ═══════════════════════════════════════════════════════════════════

@router.message(ISEEState.waiting_rent)
async def process_rent(message: types.Message, state: FSMContext):
    """پردازش مبلغ اجاره سالانه"""
    
    user_id = message.from_user.id
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    eur_rate = user_input.eur_rate
    
    raw_text = message.text.strip()
    
    # تبدیل به عدد
    amount = parse_persian_amount(raw_text)
    
    if amount is None:
        await message.reply(
            "⚠️ <b>عدد نامعتبر!</b>\n\n"
            "لطفاً مبلغ اجاره سالانه را وارد کنید.\n"
            "مثال: <code>۶۰ میلیون</code>",
            parse_mode="HTML"
        )
        return
    
    if amount < 0:
        amount = 0
    
    # تبدیل به یورو
    rent_eur, currency_type, display = smart_currency_convert(
        amount, eur_rate, raw_text, context="rent"
    )
    
    # ذخیره
    user_input.annual_rent = rent_eur
    
    # محاسبه کسر واقعی
    actual_deduction = calculate_rent_deduction(rent_eur, True)
    
    # ذخیره برای نمایش
    if "display_values" not in user:
        user["display_values"] = {}
    user["display_values"]["rent"] = display
    
    # پیام تأیید
    text = f"""
✅ <b>اجاره سالانه ثبت شد!</b>

🏠 مقدار وارد شده: <b>{display}</b>
💶 معادل: <b>{rent_eur:,.0f} €</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

🎁 <b>کسر از درآمد:</b> <b>{actual_deduction:,.0f} €</b>
"""
    
    if rent_eur > DEDUCTION_LIMITS.max_rent_deduction:
        text += f"\n⚠️ <i>توجه: سقف کسر {DEDUCTION_LIMITS.max_rent_deduction:,}€ است.</i>"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    await message.reply(text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    await asyncio.sleep(0.5)
    
    # رفتن به مرحله اعضا
    await ask_members(message, state, user_id)


# ═══════════════════════════════════════════════════════════════════
# بخش ۴.۶: بازگشت به مرحله درآمد
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee_back_to_income")
async def back_to_income(callback: types.CallbackQuery, state: FSMContext):
    """بازگشت به مرحله درآمد"""
    
    user_id = callback.from_user.id
    
    # پاک کردن مقدار قبلی درآمد
    user_input = data_store.get_current_input(user_id)
    user_input.income = 0.0
    
    await callback.message.delete()
    await ask_income(callback.message, state, user_id)


# ═══════════════════════════════════════════════════════════════════
# بخش ۴.۷: مرحله ۳ - سؤال تعداد اعضای خانواده
# ═══════════════════════════════════════════════════════════════════

async def ask_members(message: types.Message, state: FSMContext, user_id: int):
    """مرحله سوم: تعداد اعضای خانواده"""
    
    user = data_store.get_user(user_id)
    mode = user.get("settings", {}).get("mode", "full")
    total = TOTAL_STEPS if mode == "full" else QUICK_MODE_STEPS
    
    # در حالت سریع این مرحله ۲ است، در حالت کامل مرحله ۳
    step_num = 3 if mode == "full" else 2
    progress = generate_progress_bar(step_num, total)
    
    text = f"""
{STEP_EMOJI[step_num]} <b>مرحله {step_num} از {total}: اعضای خانواده</b>
{progress}

━━━━━━━━━━━━━━━━━━━━━━━━━

👨‍👩‍👧‍👦 <b>تعداد کل اعضای خانواده</b> را وارد کنید.

📋 <b>شامل:</b>
• پدر و مادر
• خودتان
• خواهر و برادر
• افراد تحت تکفل (پدربزرگ/مادربزرگ اگر همراه هستند)

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>چرا مهم است؟</b>
هر چه اعضا بیشتر، ضریب بالاتر → ISEE پایین‌تر!

📊 <b>ضرایب:</b>
• ۲ نفر → ۱.۵۷
• ۳ نفر → ۲.۰۴
• ۴ نفر → ۲.۴۶
• ۵ نفر → ۲.۸۵

━━━━━━━━━━━━━━━━━━━━━━━━━

<i>فقط یک عدد بفرستید:</i>
"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="2"),
                KeyboardButton(text="3"),
                KeyboardButton(text="4"),
            ],
            [
                KeyboardButton(text="5"),
                KeyboardButton(text="6"),
                KeyboardButton(text="7+"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.waiting_members)


# ═══════════════════════════════════════════════════════════════════
# بخش ۴.۸: پردازش تعداد اعضا
# ═══════════════════════════════════════════════════════════════════

@router.message(ISEEState.waiting_members)
async def process_members(message: types.Message, state: FSMContext):
    """پردازش تعداد اعضای خانواده"""
    
    user_id = message.from_user.id
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    
    raw_text = message.text.strip()
    
    # تبدیل "7+" به 7
    if "+" in raw_text:
        raw_text = raw_text.replace("+", "").strip()
    
    # تبدیل اعداد فارسی
    raw_text = normalize_persian_text(raw_text)
    
    try:
        members = int(raw_text)
    except ValueError:
        await message.reply(
            "⚠️ <b>لطفاً فقط عدد وارد کنید!</b>\n"
            "مثال: <code>4</code>",
            parse_mode="HTML"
        )
        return
    
    # بررسی محدوده
    if members < 1:
        await message.reply("⚠️ حداقل ۱ نفر باید باشد!")
        return
    
    if members > 15:
        await message.reply(
            "⚠️ <b>تعداد زیاد به نظر می‌رسد!</b>\n\n"
            f"شما وارد کردید: {members} نفر\n"
            "اگر مطمئنید، دوباره همین عدد را بفرستید.",
            parse_mode="HTML"
        )
        # می‌توانیم ادامه دهیم اما هشدار دادیم
    
    # ذخیره
    user_input.members = members
    
    # محاسبه ضریب
    scale = calculate_family_scale(members)
    
    # پیام تأیید
    text = f"""
✅ <b>تعداد اعضا ثبت شد!</b>

👨‍👩‍👧‍👦 تعداد: <b>{members} نفر</b>
📊 ضریب مقیاس: <b>{scale}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <i>ضریب بالاتر = تقسیم بر عدد بزرگتر = ISEE پایین‌تر!</i>

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await message.reply(text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    await asyncio.sleep(0.5)
    
    # تعیین مرحله بعد بر اساس حالت
    mode = user.get("settings", {}).get("mode", "full")
    
    if mode == "full":
        # حالت کامل: سؤال تعداد فرزندان (برای معافیت اضافی)
        await ask_children_count(message, state, user_id)
    else:
        # حالت سریع: رفتن به دارایی کل
        await ask_total_assets_quick(message, state, user_id)


# ═══════════════════════════════════════════════════════════════════
# بخش ۴.۹: سؤال تعداد فرزندان (حالت کامل)
# ═══════════════════════════════════════════════════════════════════

async def ask_children_count(message: types.Message, state: FSMContext, user_id: int):
    """سؤال تعداد فرزندان برای معافیت اضافی خانه"""
    
    user_input = data_store.get_current_input(user_id)
    members = user_input.members
    
    # اگر ۲ نفر یا کمتر هستند، فرزندی وجود ندارد
    if members <= 2:
        user_input.children_after_2 = 0
        await ask_property(message, state, user_id)
        return
    
    text = """
👶 <b>تعداد فرزندان</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

چند <b>فرزند</b> در خانواده وجود دارد؟
<i>(منظور فرزندان زیر ۲۶ سال یا تحت تکفل)</i>

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>چرا مهم است؟</b>
برای هر فرزند بعد از دوم، <b>۲,۵۰۰€</b> معافیت اضافی 
به خانه اصلی تعلق می‌گیرد.

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # ساخت دکمه‌ها بر اساس تعداد اعضا
    max_children = min(members - 1, 6)  # حداکثر منطقی
    
    buttons = []
    row = []
    for i in range(max_children + 1):
        row.append(KeyboardButton(text=str(i)))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.waiting_children)


@router.message(ISEEState.waiting_children)
async def process_children(message: types.Message, state: FSMContext):
    """پردازش تعداد فرزندان"""
    
    user_id = message.from_user.id
    user_input = data_store.get_current_input(user_id)
    
    raw_text = normalize_persian_text(message.text.strip())
    
    try:
        children = int(raw_text)
    except ValueError:
        await message.reply("⚠️ لطفاً فقط عدد وارد کنید!")
        return
    
    if children < 0:
        children = 0
    
    # فرزندان بعد از دومی
    children_after_2 = max(0, children - 2)
    user_input.children_after_2 = children_after_2
    
    # محاسبه معافیت اضافی
    extra_exemption = children_after_2 * DEDUCTION_LIMITS.extra_per_child_after_2
    
    if extra_exemption > 0:
        text = f"""
✅ <b>ثبت شد!</b>

👶 تعداد فرزندان: <b>{children}</b>
🎁 معافیت اضافی خانه: <b>+{extra_exemption:,}€</b>

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    else:
        text = """
✅ <b>ثبت شد!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await message.reply(text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    await asyncio.sleep(0.3)
    
    # رفتن به مرحله املاک
    await ask_property(message, state, user_id)


# ═══════════════════════════════════════════════════════════════════
# بخش ۴.۱۰: دارایی کل - حالت سریع
# ═══════════════════════════════════════════════════════════════════

async def ask_total_assets_quick(message: types.Message, state: FSMContext, user_id: int):
    """سؤال دارایی کل در حالت سریع"""
    
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    eur_rate = user_input.eur_rate
    
    progress = generate_progress_bar(3, QUICK_MODE_STEPS)
    
    text = f"""
{STEP_EMOJI[3]} <b>مرحله ۳ از ۳: مجموع دارایی‌ها</b>
{progress}

━━━━━━━━━━━━━━━━━━━━━━━━━

🏦 <b>مجموع کل دارایی‌های خانواده</b> را وارد کنید.

📋 <b>شامل:</b>
• ارزش خانه/آپارتمان/زمین
• موجودی بانک
• خودرو
• سهام و سرمایه‌گذاری
• طلا و جواهرات (تقریبی)

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>تخمین سریع:</b>
ارزش خانه + موجودی بانک + ارزش ماشین

💶 نرخ: {eur_rate:,} ت = 1€

━━━━━━━━━━━━━━━━━━━━━━━━━

<i>به تومان یا یورو وارد کنید. اگر ندارید: 0</i>
"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="0"), KeyboardButton(text="ندارم")],
            [KeyboardButton(text="۱ میلیارد"), KeyboardButton(text="۲ میلیارد")],
            [KeyboardButton(text="۵ میلیارد"), KeyboardButton(text="۱۰ میلیارد")],
            [KeyboardButton(text="۲۰ میلیارد"), KeyboardButton(text="۵۰ میلیارد")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.waiting_property)
    
    # ذخیره فلگ حالت سریع
    user["_quick_mode_property"] = True


# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# بخش ۵.۱: مرحله ۴ - سؤال ارزش املاک
# ═══════════════════════════════════════════════════════════════════

async def ask_property(message: types.Message, state: FSMContext, user_id: int):
    """مرحله چهارم: ارزش املاک و مستغلات"""
    
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    eur_rate = user_input.eur_rate
    mode = user.get("settings", {}).get("mode", "full")
    total = TOTAL_STEPS if mode == "full" else QUICK_MODE_STEPS
    
    step_num = 4 if mode == "full" else 3
    progress = generate_progress_bar(step_num, total)
    
    # محاسبه معافیت پایه + اضافی
    base_exemption = DEDUCTION_LIMITS.primary_home_exemption
    extra_exemption = user_input.children_after_2 * DEDUCTION_LIMITS.extra_per_child_after_2
    total_exemption = base_exemption + extra_exemption
    
    text = f"""
{STEP_EMOJI[step_num]} <b>مرحله {step_num} از {total}: املاک و مستغلات</b>
{progress}

━━━━━━━━━━━━━━━━━━━━━━━━━

🏠 <b>ارزش کل املاک خانواده</b> چقدر است؟

📋 <b>شامل:</b>
• خانه یا آپارتمان (حتی اگر در آن زندگی می‌کنید)
• زمین و باغ
• مغازه یا ملک تجاری
• ویلا یا خانه دوم
• پارکینگ و انباری جداگانه

━━━━━━━━━━━━━━━━━━━━━━━━━

🎁 <b>معافیت خانه اصلی:</b>
• پایه: <b>{base_exemption:,}€</b>"""
    
    if extra_exemption > 0:
        text += f"""
• اضافی (فرزندان): <b>+{extra_exemption:,}€</b>
• <b>جمع معافیت: {total_exemption:,}€</b>"""
    
    text += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>نکته:</b>
ارزش <b>فعلی بازار</b> را وارد کنید، نه قیمت خرید!

💶 نرخ: {eur_rate:,} ت = 1€

━━━━━━━━━━━━━━━━━━━━━━━━━

<i>به تومان یا یورو. اگر ملکی ندارید: 0</i>
"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="0"), KeyboardButton(text="ندارم")],
            [KeyboardButton(text="۱ میلیارد"), KeyboardButton(text="۲ میلیارد")],
            [KeyboardButton(text="۵ میلیارد"), KeyboardButton(text="۱۰ میلیارد")],
            [KeyboardButton(text="۱۵ میلیارد"), KeyboardButton(text="۲۰ میلیارد")],
            [KeyboardButton(text="۳۰ میلیارد"), KeyboardButton(text="۵۰ میلیارد")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.waiting_property)


# ═══════════════════════════════════════════════════════════════════
# بخش ۵.۲: پردازش ارزش املاک
# ═══════════════════════════════════════════════════════════════════

@router.message(ISEEState.waiting_property)
async def process_property(message: types.Message, state: FSMContext):
    """پردازش ارزش املاک"""
    
    user_id = message.from_user.id
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    eur_rate = user_input.eur_rate
    
    raw_text = message.text.strip()
    
    # تبدیل به عدد
    amount = parse_persian_amount(raw_text)
    
    if amount is None:
        await message.reply(
            "⚠️ <b>عدد نامعتبر!</b>\n\n"
            "لطفاً ارزش املاک را وارد کنید.\n"
            "مثال: <code>۵ میلیارد</code> یا <code>0</code>",
            parse_mode="HTML"
        )
        return
    
    if amount < 0:
        amount = 0
    
    # تبدیل به یورو
    property_eur, currency_type, display = smart_currency_convert(
        amount, eur_rate, raw_text, context="property"
    )
    
    # ذخیره
    user_input.property_value = property_eur
    
    # ذخیره برای نمایش
    if "display_values" not in user:
        user["display_values"] = {}
    user["display_values"]["property"] = display
    
    # بررسی حالت سریع
    is_quick = user.get("_quick_mode_property", False)
    
    if is_quick:
        # در حالت سریع، این مقدار شامل همه دارایی‌هاست
        user_input.is_primary_home = True  # فرض پیش‌فرض
        user_input.financial_assets = 0
        user_input.total_debts = 0
        user_input.abroad_assets = 0
        
        text = f"""
✅ <b>دارایی کل ثبت شد!</b>

🏦 مقدار: <b>{display}</b>
💶 معادل: <b>{property_eur:,.0f} €</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ در حال محاسبه نهایی...
"""
        await message.reply(text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
        await asyncio.sleep(0.5)
        
        # رفتن مستقیم به محاسبه نهایی
        await calculate_and_show_result(message, state, user_id)
        return
    
    # حالت کامل: ادامه روند عادی
    text = f"""
✅ <b>ارزش املاک ثبت شد!</b>

🏠 مقدار: <b>{display}</b>
💶 معادل: <b>{property_eur:,.0f} €</b>

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await message.reply(text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    await asyncio.sleep(0.3)
    
    # اگر ملکی دارد، سؤال خانه اصلی
    if property_eur > 0:
        await ask_primary_home(message, state, user_id)
    else:
        user_input.is_primary_home = False
        await ask_financial(message, state, user_id)


# ═══════════════════════════════════════════════════════════════════
# بخش ۵.۳: سؤال خانه اصلی
# ═══════════════════════════════════════════════════════════════════

async def ask_primary_home(message: types.Message, state: FSMContext, user_id: int):
    """سؤال آیا ملک وارد شده خانه اصلی است؟"""
    
    user_input = data_store.get_current_input(user_id)
    
    # محاسبه معافیت
    base_exemption = DEDUCTION_LIMITS.primary_home_exemption
    extra = user_input.children_after_2 * DEDUCTION_LIMITS.extra_per_child_after_2
    total_exemption = base_exemption + extra
    
    text = f"""
🏡 <b>خانه اصلی</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

آیا <b>خانه‌ای که در آن زندگی می‌کنید</b> جزء املاک وارد شده است؟

━━━━━━━━━━━━━━━━━━━━━━━━━

🎁 <b>اهمیت:</b>
اگر بله، تا <b>{total_exemption:,}€</b> از ارزش آن معاف می‌شود!

<b>مثال:</b>
• ارزش خانه: ۱۰۰,۰۰۰€
• معافیت: -{total_exemption:,}€
• باقی‌مانده: {max(0, 100000 - total_exemption):,}€

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ بله، خانه اصلی هست", callback_data="isee_primary_yes"),
        ],
        [
            InlineKeyboardButton(text="❌ خیر، همه ملک سرمایه‌ای است", callback_data="isee_primary_no"),
        ],
        [
            InlineKeyboardButton(text="🔙 مرحله قبل", callback_data="isee_back_to_members"),
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.waiting_primary_home)


@router.callback_query(F.data == "isee_primary_yes")
async def primary_home_yes(callback: types.CallbackQuery, state: FSMContext):
    """خانه اصلی هست"""
    
    user_id = callback.from_user.id
    user_input = data_store.get_current_input(user_id)
    user_input.is_primary_home = True
    
    # محاسبه معافیت واقعی
    exemption = calculate_primary_home_exemption(
        user_input.property_value,
        True,
        user_input.children_after_2
    )
    
    adjusted = max(0, user_input.property_value - exemption)
    
    await callback.message.edit_text(
        f"✅ <b>ثبت شد: خانه اصلی</b>\n\n"
        f"🏠 ارزش کل: <b>{user_input.property_value:,.0f}€</b>\n"
        f"🎁 معافیت: <b>-{exemption:,.0f}€</b>\n"
        f"📊 مبلغ مشمول: <b>{adjusted:,.0f}€</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )
    
    await asyncio.sleep(0.5)
    await ask_financial(callback.message, state, user_id)


@router.callback_query(F.data == "isee_primary_no")
async def primary_home_no(callback: types.CallbackQuery, state: FSMContext):
    """خانه اصلی نیست"""
    
    user_id = callback.from_user.id
    user_input = data_store.get_current_input(user_id)
    user_input.is_primary_home = False
    
    await callback.message.edit_text(
        "✅ <b>ثبت شد: بدون خانه اصلی</b>\n\n"
        f"🏠 کل ارزش ملک: <b>{user_input.property_value:,.0f}€</b>\n"
        "⚠️ <i>معافیت خانه اصلی اعمال نمی‌شود.</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )
    
    await asyncio.sleep(0.5)
    await ask_financial(callback.message, state, user_id)


# ═══════════════════════════════════════════════════════════════════
# بخش ۵.۴: بازگشت به مرحله اعضا
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee_back_to_members")
async def back_to_members(callback: types.CallbackQuery, state: FSMContext):
    """بازگشت به مرحله اعضا"""
    
    user_id = callback.from_user.id
    user_input = data_store.get_current_input(user_id)
    
    # پاک کردن مقادیر
    user_input.property_value = 0
    user_input.members = 1
    
    await callback.message.delete()
    await ask_members(callback.message, state, user_id)


# ═══════════════════════════════════════════════════════════════════
# بخش ۵.۵: مرحله ۵ - دارایی مالی
# ═══════════════════════════════════════════════════════════════════

async def ask_financial(message: types.Message, state: FSMContext, user_id: int):
    """مرحله پنجم: دارایی‌های مالی"""
    
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    eur_rate = user_input.eur_rate
    
    progress = generate_progress_bar(5, TOTAL_STEPS)
    
    # محاسبه معافیت مالی
    financial_exemption = calculate_financial_exemption(user_input.members)
    
    text = f"""
{STEP_EMOJI[5]} <b>مرحله ۵ از {TOTAL_STEPS}: دارایی‌های مالی</b>
{progress}

━━━━━━━━━━━━━━━━━━━━━━━━━

💰 <b>مجموع دارایی‌های نقدی و مالی</b> خانواده چقدر است؟

📋 <b>شامل:</b>
• موجودی حساب‌های بانکی (در تاریخ ۳۱ دسامبر)
• سپرده‌های بلندمدت
• سهام و اوراق بهادار
• صندوق‌های سرمایه‌گذاری
• بیمه عمر (ارزش بازخرید)
• ارز دیجیتال
• طلا و سکه (ارزش تقریبی)

━━━━━━━━━━━━━━━━━━━━━━━━━

🎁 <b>معافیت دارایی مالی:</b>
برای {user_input.members} نفر: <b>{financial_exemption:,}€</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>نکته مهم:</b>
موجودی <b>۳۱ دسامبر</b> ملاک است!
اگر می‌خواهید ISEE پایین بیاید، قبل از آن تاریخ 
حساب را خالی کنید یا خرج کنید.

━━━━━━━━━━━━━━━━━━━━━━━━━

💶 نرخ: {eur_rate:,} ت = 1€

<i>به تومان یا یورو. اگر پس‌اندازی ندارید: 0</i>
"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="0"), KeyboardButton(text="ندارم")],
            [KeyboardButton(text="۱۰ میلیون"), KeyboardButton(text="۵۰ میلیون")],
            [KeyboardButton(text="۱۰۰ میلیون"), KeyboardButton(text="۲۰۰ میلیون")],
            [KeyboardButton(text="۵۰۰ میلیون"), KeyboardButton(text="۱ میلیارد")],
            [KeyboardButton(text="۲ میلیارد"), KeyboardButton(text="۵ میلیارد")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.waiting_financial)


# ═══════════════════════════════════════════════════════════════════
# بخش ۵.۶: پردازش دارایی مالی
# ═══════════════════════════════════════════════════════════════════

@router.message(ISEEState.waiting_financial)
async def process_financial(message: types.Message, state: FSMContext):
    """پردازش دارایی مالی"""
    
    user_id = message.from_user.id
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    eur_rate = user_input.eur_rate
    
    raw_text = message.text.strip()
    
    # تبدیل به عدد
    amount = parse_persian_amount(raw_text)
    
    if amount is None:
        await message.reply(
            "⚠️ <b>عدد نامعتبر!</b>\n\n"
            "لطفاً مقدار دارایی مالی را وارد کنید.\n"
            "مثال: <code>۱۰۰ میلیون</code> یا <code>0</code>",
            parse_mode="HTML"
        )
        return
    
    if amount < 0:
        amount = 0
    
    # تبدیل به یورو
    financial_eur, currency_type, display = smart_currency_convert(
        amount, eur_rate, raw_text, context="financial"
    )
    
    # ذخیره
    user_input.financial_assets = financial_eur
    
    # ذخیره برای نمایش
    if "display_values" not in user:
        user["display_values"] = {}
    user["display_values"]["financial"] = display
    
    # محاسبه معافیت
    exemption = calculate_financial_exemption(user_input.members)
    adjusted = max(0, financial_eur - exemption)
    
    # پیام تأیید
    text = f"""
✅ <b>دارایی مالی ثبت شد!</b>

💰 مقدار: <b>{display}</b>
💶 معادل: <b>{financial_eur:,.0f} €</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

🎁 معافیت: <b>-{exemption:,.0f}€</b>
📊 مبلغ مشمول: <b>{adjusted:,.0f}€</b>

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await message.reply(text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    await asyncio.sleep(0.5)
    
    # رفتن به مرحله بدهی‌ها
    await ask_debts(message, state, user_id)


# ═══════════════════════════════════════════════════════════════════
# بخش ۵.۷: مرحله ۶ - بدهی‌ها
# ═══════════════════════════════════════════════════════════════════

async def ask_debts(message: types.Message, state: FSMContext, user_id: int):
    """مرحله ششم: بدهی‌ها و وام‌ها"""
    
    user_input = data_store.get_current_input(user_id)
    eur_rate = user_input.eur_rate
    
    progress = generate_progress_bar(6, TOTAL_STEPS)
    
    # محاسبه دارایی فعلی
    current_patrimony = user_input.property_value + user_input.financial_assets
    
    text = f"""
{STEP_EMOJI[6]} <b>مرحله ۶ از {TOTAL_STEPS}: بدهی‌ها</b>
{progress}

━━━━━━━━━━━━━━━━━━━━━━━━━

📉 <b>مجموع بدهی‌های خانواده</b> چقدر است؟

📋 <b>شامل:</b>
• وام مسکن (مانده بدهی)
• وام خودرو
• وام شخصی/ضروری
• بدهی به بانک
• قسط‌های معوقه

━━━━━━━━━━━━━━━━━━━━━━━━━

🎁 <b>فایده:</b>
بدهی‌ها از دارایی کسر می‌شوند!

📊 دارایی فعلی: <b>{current_patrimony:,.0f}€</b>

⚠️ <b>نکته:</b>
حداکثر تا سقف دارایی کسر می‌شود.
(دارایی نمی‌تواند منفی شود)

━━━━━━━━━━━━━━━━━━━━━━━━━

💶 نرخ: {eur_rate:,} ت = 1€

<i>به تومان یا یورو. اگر بدهی ندارید: 0</i>
"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="0"), KeyboardButton(text="ندارم")],
            [KeyboardButton(text="۵۰ میلیون"), KeyboardButton(text="۱۰۰ میلیون")],
            [KeyboardButton(text="۳۰۰ میلیون"), KeyboardButton(text="۵۰۰ میلیون")],
            [KeyboardButton(text="۱ میلیارد"), KeyboardButton(text="۲ میلیارد")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.waiting_debts)


# ═══════════════════════════════════════════════════════════════════
# بخش ۵.۸: پردازش بدهی‌ها
# ═══════════════════════════════════════════════════════════════════

@router.message(ISEEState.waiting_debts)
async def process_debts(message: types.Message, state: FSMContext):
    """پردازش بدهی‌ها"""
    
    user_id = message.from_user.id
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    eur_rate = user_input.eur_rate
    
    raw_text = message.text.strip()
    
    # تبدیل به عدد
    amount = parse_persian_amount(raw_text)
    
    if amount is None:
        await message.reply(
            "⚠️ <b>عدد نامعتبر!</b>\n\n"
            "لطفاً مقدار بدهی را وارد کنید.\n"
            "مثال: <code>۲۰۰ میلیون</code> یا <code>0</code>",
            parse_mode="HTML"
        )
        return
    
    if amount < 0:
        amount = 0
    
    # تبدیل به یورو
    debts_eur, currency_type, display = smart_currency_convert(
        amount, eur_rate, raw_text, context="debts"
    )
    
    # ذخیره
    user_input.total_debts = debts_eur
    
    # ذخیره برای نمایش
    if "display_values" not in user:
        user["display_values"] = {}
    user["display_values"]["debts"] = display
    
    # محاسبه کسر واقعی
    current_patrimony = user_input.property_value + user_input.financial_assets
    actual_deduction = min(debts_eur, current_patrimony)
    
    # پیام تأیید
    if debts_eur > 0:
        text = f"""
✅ <b>بدهی‌ها ثبت شد!</b>

📉 مقدار: <b>{display}</b>
💶 معادل: <b>{debts_eur:,.0f} €</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

🎁 کسر از دارایی: <b>-{actual_deduction:,.0f}€</b>
"""
        if debts_eur > current_patrimony:
            text += f"\n⚠️ <i>توجه: بدهی از دارایی بیشتر است. فقط تا سقف دارایی کسر شد.</i>"
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━"
    else:
        text = """
✅ <b>ثبت شد: بدون بدهی</b>

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await message.reply(text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    await asyncio.sleep(0.5)
    
    # رفتن به مرحله دارایی خارجی
    await ask_abroad(message, state, user_id)


# ═══════════════════════════════════════════════════════════════════
# بخش ۵.۹: مرحله ۷ - دارایی خارجی
# ═══════════════════════════════════════════════════════════════════

async def ask_abroad(message: types.Message, state: FSMContext, user_id: int):
    """مرحله هفتم: دارایی خارج از ایران"""
    
    user_input = data_store.get_current_input(user_id)
    
    progress = generate_progress_bar(7, TOTAL_STEPS)
    
    text = f"""
{STEP_EMOJI[7]} <b>مرحله ۷ از {TOTAL_STEPS}: دارایی خارجی</b>
{progress}

━━━━━━━━━━━━━━━━━━━━━━━━━

🌍 <b>آیا دارایی در خارج از ایران دارید؟</b>

📋 <b>شامل:</b>
• حساب بانکی در ایتالیا یا کشورهای دیگر
• ملک در خارج از ایران
• سهام شرکت‌های خارجی
• سرمایه‌گذاری در صندوق‌های بین‌المللی

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>نکته برای دانشجویان تازه‌وارد:</b>
اگر حساب بانکی در ایتالیا باز کرده‌اید،
موجودی آن را اینجا وارد کنید.

━━━━━━━━━━━━━━━━━━━━━━━━━

💶 <b>مقدار را به یورو وارد کنید.</b>
<i>اگر ندارید: 0</i>
"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="0"), KeyboardButton(text="ندارم")],
            [KeyboardButton(text="500€"), KeyboardButton(text="1000€")],
            [KeyboardButton(text="2000€"), KeyboardButton(text="5000€")],
            [KeyboardButton(text="10000€"), KeyboardButton(text="20000€")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.waiting_abroad)


# ═══════════════════════════════════════════════════════════════════
# بخش ۵.۱۰: پردازش دارایی خارجی
# ═══════════════════════════════════════════════════════════════════

@router.message(ISEEState.waiting_abroad)
async def process_abroad(message: types.Message, state: FSMContext):
    """پردازش دارایی خارجی"""
    
    user_id = message.from_user.id
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    eur_rate = user_input.eur_rate
    
    raw_text = message.text.strip()
    
    # تبدیل به عدد
    amount = parse_persian_amount(raw_text)
    
    if amount is None:
        amount = 0
    
    if amount < 0:
        amount = 0
    
    # دارایی خارجی همیشه یورو است
    abroad_eur, currency_type, display = smart_currency_convert(
        amount, eur_rate, raw_text, context="abroad"
    )
    
    # ذخیره
    user_input.abroad_assets = abroad_eur
    
    # ذخیره برای نمایش
    if "display_values" not in user:
        user["display_values"] = {}
    user["display_values"]["abroad"] = f"{abroad_eur:,.0f}€"
    
    # پیام تأیید
    if abroad_eur > 0:
        text = f"""
✅ <b>دارایی خارجی ثبت شد!</b>

🌍 مقدار: <b>{abroad_eur:,.0f} €</b>

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    else:
        text = """
✅ <b>ثبت شد: بدون دارایی خارجی</b>

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await message.reply(text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    await asyncio.sleep(0.5)
    
    # رفتن به مرحله استقلال دانشجو
    await ask_independent_status(message, state, user_id)


# ═══════════════════════════════════════════════════════════════════
# بخش ۵.۱۱: مرحله ۸ - استقلال دانشجو
# ═══════════════════════════════════════════════════════════════════

async def ask_independent_status(message: types.Message, state: FSMContext, user_id: int):
    """مرحله هشتم: وضعیت استقلال دانشجو"""
    
    user_input = data_store.get_current_input(user_id)
    
    progress = generate_progress_bar(8, TOTAL_STEPS)
    
    min_income = DEDUCTION_LIMITS.independent_student_min_income
    min_years = DEDUCTION_LIMITS.independent_student_min_years
    
    text = f"""
{STEP_EMOJI[8]} <b>مرحله ۸ از {TOTAL_STEPS}: استقلال دانشجو</b>
{progress}

━━━━━━━━━━━━━━━━━━━━━━━━━

🎓 <b>آیا شما دانشجوی مستقل هستید؟</b>

📋 <b>شروط استقلال:</b>

1️⃣ حداقل <b>{min_years} سال</b> خارج از خانه پدری زندگی کرده باشید

2️⃣ حداقل <b>{min_income:,}€</b> درآمد سالانه شخصی داشته باشید

━━━━━━━━━━━━━━━━━━━━━━━━━

🎁 <b>فایده استقلال:</b>
اگر مستقل باشید، ISEE فقط بر اساس وضعیت 
<b>خودتان</b> محاسبه می‌شود، نه خانواده!

━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>توجه:</b>
اگر تازه به ایتالیا آمده‌اید، احتمالاً 
این شروط را ندارید. «خیر» را انتخاب کنید.

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ بله، مستقل هستم", callback_data="isee_independent_yes"),
        ],
        [
            InlineKeyboardButton(text="❌ خیر، با خانواده حساب می‌شوم", callback_data="isee_independent_no"),
        ],
        [
            InlineKeyboardButton(text="❓ مطمئن نیستم", callback_data="isee_independent_help"),
        ],
        [
            InlineKeyboardButton(text="🔙 مرحله قبل", callback_data="isee_back_to_abroad"),
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.waiting_independent)


@router.callback_query(F.data == "isee_independent_yes")
async def independent_yes(callback: types.CallbackQuery, state: FSMContext):
    """دانشجو مستقل است"""
    
    user_id = callback.from_user.id
    user_input = data_store.get_current_input(user_id)
    user_input.is_independent_student = True
    
    await callback.message.edit_text(
        "✅ <b>ثبت شد: دانشجوی مستقل</b>\n\n"
        "🎓 ISEE بر اساس وضعیت شخصی شما محاسبه می‌شود.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )
    
    await asyncio.sleep(0.5)
    await show_confirm_page(callback.message, state, user_id)


@router.callback_query(F.data == "isee_independent_no")
async def independent_no(callback: types.CallbackQuery, state: FSMContext):
    """دانشجو مستقل نیست"""
    
    user_id = callback.from_user.id
    user_input = data_store.get_current_input(user_id)
    user_input.is_independent_student = False
    
    await callback.message.edit_text(
        "✅ <b>ثبت شد: وابسته به خانواده</b>\n\n"
        "👨‍👩‍👧 ISEE بر اساس وضعیت کل خانواده محاسبه می‌شود.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )
    
    await asyncio.sleep(0.5)
    await show_confirm_page(callback.message, state, user_id)


@router.callback_query(F.data == "isee_independent_help")
async def independent_help(callback: types.CallbackQuery):
    """راهنمای استقلال دانشجو"""
    
    text = """
❓ <b>چگونه بفهمم مستقل هستم؟</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

برای دانشجوی مستقل بودن، <b>هر دو شرط</b> لازم است:

<b>شرط ۱: زندگی مستقل</b>
• حداقل ۲ سال در آدرسی غیر از خانه پدری ثبت شده باشید
• اجاره‌نامه یا سند مالکیت به نام خودتان

<b>شرط ۲: درآمد کافی</b>
• حداقل ۹,۰۰۰€ درآمد سالانه شخصی
• از محل کار، کسب‌وکار یا... (نه کمک خانواده)

━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🇮🇷 برای دانشجویان ایرانی:</b>

اگر تازه به ایتالیا آمده‌اید (کمتر از ۲ سال)،
تقریباً قطعاً مستقل نیستید!

<b>«خیر» را انتخاب کنید.</b>

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ بله، هر دو شرط را دارم", callback_data="isee_independent_yes"),
        ],
        [
            InlineKeyboardButton(text="❌ خیر، شروط را ندارم", callback_data="isee_independent_no"),
        ],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "isee_back_to_abroad")
async def back_to_abroad(callback: types.CallbackQuery, state: FSMContext):
    """بازگشت به مرحله دارایی خارجی"""
    
    user_id = callback.from_user.id
    user_input = data_store.get_current_input(user_id)
    user_input.abroad_assets = 0
    
    await callback.message.delete()
    await ask_abroad(callback.message, state, user_id)


# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# بخش ۶.۱: صفحه تأیید و پیش‌نمایش داده‌ها
# ═══════════════════════════════════════════════════════════════════

async def show_confirm_page(message: types.Message, state: FSMContext, user_id: int):
    """نمایش صفحه تأیید و پیش‌نمایش داده‌ها قبل از محاسبه"""
    
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    display_values = user.get("display_values", {})
    
    # محاسبه پیش‌نمایش
    preview_result = calculate_isee(user_input)
    
    # تعیین رنگ وضعیت
    status_config = STATUS_CONFIG.get(preview_result.status, STATUS_CONFIG["none"])
    
    text = f"""
📋 <b>پیش‌نمایش و تأیید اطلاعات</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

🔢 <b>خلاصه ورودی‌ها:</b>

1️⃣ <b>درآمد سالانه:</b>
   {display_values.get('income', '—')} ≈ {user_input.income:,.0f}€
"""
    
    # اجاره (اگر مستأجر است)
    if user_input.is_tenant:
        text += f"""
2️⃣ <b>اجاره سالانه:</b>
   {display_values.get('rent', '—')} ≈ {user_input.annual_rent:,.0f}€
   🎁 کسر: -{preview_result.rent_deduction:,.0f}€
"""
    else:
        text += """
2️⃣ <b>اجاره:</b> مالک هستند
"""
    
    text += f"""
3️⃣ <b>اعضای خانواده:</b> {user_input.members} نفر
   📊 ضریب: {preview_result.scale}

4️⃣ <b>ارزش املاک:</b>
   {display_values.get('property', '—')} ≈ {user_input.property_value:,.0f}€
"""
    
    if user_input.is_primary_home and user_input.property_value > 0:
        text += f"   🎁 معافیت خانه اصلی: -{preview_result.home_exemption:,.0f}€\n"
    
    text += f"""
5️⃣ <b>دارایی مالی:</b>
   {display_values.get('financial', '—')} ≈ {user_input.financial_assets:,.0f}€
   🎁 معافیت: -{preview_result.financial_exemption:,.0f}€
"""
    
    if user_input.total_debts > 0:
        text += f"""
6️⃣ <b>بدهی‌ها:</b>
   {display_values.get('debts', '—')} ≈ {user_input.total_debts:,.0f}€
   🎁 کسر: -{preview_result.debt_deduction:,.0f}€
"""
    else:
        text += """
6️⃣ <b>بدهی‌ها:</b> ندارند
"""
    
    if user_input.abroad_assets > 0:
        text += f"""
7️⃣ <b>دارایی خارجی:</b> {user_input.abroad_assets:,.0f}€
"""
    else:
        text += """
7️⃣ <b>دارایی خارجی:</b> ندارند
"""
    
    text += f"""
8️⃣ <b>وضعیت دانشجو:</b> {'مستقل' if user_input.is_independent_student else 'وابسته به خانواده'}

━━━━━━━━━━━━━━━━━━━━━━━━━

{status_config['bar']}

📊 <b>پیش‌نمایش ISEE:</b>
<code>≈ {preview_result.isee:,.0f} €</code>

🏆 <b>وضعیت احتمالی:</b>
{status_config['emoji']} {status_config['title']}

━━━━━━━━━━━━━━━━━━━━━━━━━

<b>آیا اطلاعات صحیح است؟</b>
"""
    
    # ساخت کیبورد با دکمه‌های ویرایش
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تأیید و محاسبه نهایی", callback_data="isee_confirm_calculate"),
        ],
        [
            InlineKeyboardButton(text="✏️ ویرایش درآمد", callback_data="isee_edit_income"),
            InlineKeyboardButton(text="✏️ ویرایش اعضا", callback_data="isee_edit_members"),
        ],
        [
            InlineKeyboardButton(text="✏️ ویرایش املاک", callback_data="isee_edit_property"),
            InlineKeyboardButton(text="✏️ ویرایش مالی", callback_data="isee_edit_financial"),
        ],
        [
            InlineKeyboardButton(text="✏️ ویرایش بدهی", callback_data="isee_edit_debts"),
            InlineKeyboardButton(text="✏️ ویرایش خارجی", callback_data="isee_edit_abroad"),
        ],
        [
            InlineKeyboardButton(text="🔄 شروع از اول", callback_data="isee"),
        ],
        [
            InlineKeyboardButton(text="❌ لغو", callback_data="isee_cancel"),
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.confirm_data)


# ═══════════════════════════════════════════════════════════════════
# بخش ۶.۲: هندلرهای ویرایش فیلدها
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee_edit_income")
async def edit_income(callback: types.CallbackQuery, state: FSMContext):
    """ویرایش درآمد"""
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    user["_editing_field"] = "income"
    
    await callback.message.delete()
    
    text = """
✏️ <b>ویرایش درآمد سالانه</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

💵 مقدار جدید درآمد سالانه را وارد کنید:

<i>به تومان یا یورو</i>
"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="۱۰۰ میلیون"), KeyboardButton(text="۲۰۰ میلیون")],
            [KeyboardButton(text="۳۰۰ میلیون"), KeyboardButton(text="۵۰۰ میلیون")],
            [KeyboardButton(text="🔙 انصراف")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.edit_field)


@router.callback_query(F.data == "isee_edit_members")
async def edit_members(callback: types.CallbackQuery, state: FSMContext):
    """ویرایش تعداد اعضا"""
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    user["_editing_field"] = "members"
    
    await callback.message.delete()
    
    text = """
✏️ <b>ویرایش تعداد اعضا</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

👨‍👩‍👧‍👦 تعداد جدید اعضای خانواده را وارد کنید:
"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="2"), KeyboardButton(text="3"), KeyboardButton(text="4")],
            [KeyboardButton(text="5"), KeyboardButton(text="6"), KeyboardButton(text="7")],
            [KeyboardButton(text="🔙 انصراف")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.edit_field)


@router.callback_query(F.data == "isee_edit_property")
async def edit_property(callback: types.CallbackQuery, state: FSMContext):
    """ویرایش ارزش املاک"""
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    user["_editing_field"] = "property"
    
    await callback.message.delete()
    
    text = """
✏️ <b>ویرایش ارزش املاک</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

🏠 ارزش جدید املاک را وارد کنید:

<i>به تومان یا یورو. اگر ندارید: 0</i>
"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="0"), KeyboardButton(text="۱ میلیارد")],
            [KeyboardButton(text="۵ میلیارد"), KeyboardButton(text="۱۰ میلیارد")],
            [KeyboardButton(text="🔙 انصراف")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.edit_field)


@router.callback_query(F.data == "isee_edit_financial")
async def edit_financial(callback: types.CallbackQuery, state: FSMContext):
    """ویرایش دارایی مالی"""
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    user["_editing_field"] = "financial"
    
    await callback.message.delete()
    
    text = """
✏️ <b>ویرایش دارایی مالی</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

💰 مقدار جدید دارایی مالی را وارد کنید:

<i>به تومان یا یورو. اگر ندارید: 0</i>
"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="0"), KeyboardButton(text="۵۰ میلیون")],
            [KeyboardButton(text="۱۰۰ میلیون"), KeyboardButton(text="۵۰۰ میلیون")],
            [KeyboardButton(text="🔙 انصراف")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.edit_field)


@router.callback_query(F.data == "isee_edit_debts")
async def edit_debts(callback: types.CallbackQuery, state: FSMContext):
    """ویرایش بدهی‌ها"""
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    user["_editing_field"] = "debts"
    
    await callback.message.delete()
    
    text = """
✏️ <b>ویرایش بدهی‌ها</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

📉 مقدار جدید بدهی‌ها را وارد کنید:

<i>به تومان یا یورو. اگر ندارید: 0</i>
"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="0"), KeyboardButton(text="۱۰۰ میلیون")],
            [KeyboardButton(text="۵۰۰ میلیون"), KeyboardButton(text="۱ میلیارد")],
            [KeyboardButton(text="🔙 انصراف")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.edit_field)


@router.callback_query(F.data == "isee_edit_abroad")
async def edit_abroad(callback: types.CallbackQuery, state: FSMContext):
    """ویرایش دارایی خارجی"""
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    user["_editing_field"] = "abroad"
    
    await callback.message.delete()
    
    text = """
✏️ <b>ویرایش دارایی خارجی</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

🌍 مقدار جدید دارایی خارجی را وارد کنید:

<i>به یورو. اگر ندارید: 0</i>
"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="0"), KeyboardButton(text="1000€")],
            [KeyboardButton(text="5000€"), KeyboardButton(text="10000€")],
            [KeyboardButton(text="🔙 انصراف")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.edit_field)


# ═══════════════════════════════════════════════════════════════════
# بخش ۶.۳: پردازش ویرایش فیلدها
# ═══════════════════════════════════════════════════════════════════

@router.message(ISEEState.edit_field)
async def process_edit_field(message: types.Message, state: FSMContext):
    """پردازش مقدار ویرایش شده"""
    
    user_id = message.from_user.id
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    eur_rate = user_input.eur_rate
    
    raw_text = message.text.strip()
    editing_field = user.get("_editing_field", "")
    
    # چک انصراف
    if "انصراف" in raw_text or "🔙" in raw_text:
        await message.reply(
            "↩️ ویرایش لغو شد.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
        await asyncio.sleep(0.3)
        await show_confirm_page(message, state, user_id)
        return
    
    # پردازش بر اساس فیلد
    if editing_field == "members":
        # تعداد اعضا
        normalized = normalize_persian_text(raw_text.replace("+", ""))
        try:
            members = int(normalized)
            if members < 1:
                members = 1
            if members > 15:
                members = 15
            user_input.members = members
            
            # آپدیت display
            if "display_values" not in user:
                user["display_values"] = {}
            
            await message.reply(
                f"✅ <b>تعداد اعضا به {members} نفر تغییر کرد.</b>",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="HTML"
            )
        except ValueError:
            await message.reply("⚠️ لطفاً یک عدد وارد کنید!")
            return
    
    else:
        # سایر فیلدها: مقادیر عددی
        amount = parse_persian_amount(raw_text)
        
        if amount is None:
            await message.reply(
                "⚠️ <b>عدد نامعتبر!</b>\nلطفاً دوباره تلاش کنید.",
                parse_mode="HTML"
            )
            return
        
        if amount < 0:
            amount = 0
        
        # تبدیل به یورو
        context = "abroad" if editing_field == "abroad" else "general"
        eur_value, currency_type, display = smart_currency_convert(
            amount, eur_rate, raw_text, context=context
        )
        
        # ذخیره در فیلد مربوطه
        if editing_field == "income":
            user_input.income = eur_value
        elif editing_field == "property":
            user_input.property_value = eur_value
        elif editing_field == "financial":
            user_input.financial_assets = eur_value
        elif editing_field == "debts":
            user_input.total_debts = eur_value
        elif editing_field == "abroad":
            user_input.abroad_assets = eur_value
        
        # آپدیت display values
        if "display_values" not in user:
            user["display_values"] = {}
        user["display_values"][editing_field] = display
        
        field_names = {
            "income": "درآمد",
            "property": "ارزش املاک",
            "financial": "دارایی مالی",
            "debts": "بدهی‌ها",
            "abroad": "دارایی خارجی",
        }
        
        await message.reply(
            f"✅ <b>{field_names.get(editing_field, 'مقدار')} ویرایش شد.</b>\n"
            f"💶 مقدار جدید: <b>{eur_value:,.0f}€</b>",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
    
    # پاکسازی فلگ ویرایش
    user["_editing_field"] = ""
    
    await asyncio.sleep(0.5)
    
    # بازگشت به صفحه تأیید
    await show_confirm_page(message, state, user_id)


# ═══════════════════════════════════════════════════════════════════
# بخش ۶.۴: تأیید و محاسبه نهایی
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee_confirm_calculate")
async def confirm_and_calculate(callback: types.CallbackQuery, state: FSMContext):
    """تأیید نهایی و شروع محاسبه"""
    
    user_id = callback.from_user.id
    
    # نمایش پیام انتظار
    await callback.message.edit_text(
        "⏳ <b>در حال محاسبه ISEE...</b>\n\n"
        "🔢 پردازش اطلاعات...\n"
        "📊 اعمال معافیت‌ها...\n"
        "🧮 محاسبه نهایی...",
        parse_mode="HTML"
    )
    
    await asyncio.sleep(1.5)  # تأخیر برای جذابیت
    
    # انجام محاسبه نهایی
    await calculate_and_show_result(callback.message, state, user_id)


async def calculate_and_show_result(message: types.Message, state: FSMContext, user_id: int):
    """محاسبه نهایی و نمایش نتیجه کامل"""
    
    user = data_store.get_user(user_id)
    user_input = data_store.get_current_input(user_id)
    
    # دریافت آستانه‌های منطقه
    thresholds = REGIONAL_THRESHOLDS.get(user_input.region, DEFAULT_THRESHOLDS)
    
    # محاسبه نهایی
    result = calculate_isee(user_input, thresholds)
    
    # ذخیره در تاریخچه
    data_store.save_calculation(user_id, result)
    
    # ارسال گزارش نهایی
    await send_final_report(message, result, user_input, user, thresholds)
    
    # پاکسازی
    data_store.clear_current(user_id)
    await state.clear()


# ═══════════════════════════════════════════════════════════════════
# بخش ۶.۵: ساخت و ارسال گزارش نهایی
# ═══════════════════════════════════════════════════════════════════

async def send_final_report(
    message: types.Message, 
    result: ISEEResult, 
    inputs: ISEEInput,
    user: dict,
    thresholds: ISEEThresholds
):
    """ارسال گزارش نهایی محاسبه ISEE"""
    
    isee = result.isee
    status = result.status
    config = STATUS_CONFIG.get(status, STATUS_CONFIG["none"])
    
    # ═══ بخش ۱: هدر و نتیجه اصلی ═══
    report = f"""
{config['emoji']} <b>گزارش محاسبه ISEE</b>
{'━' * 28}

🎯 <b>عدد ISEE شما:</b>

   <code>  {isee:,.2f} €  </code>

{config['bar']}

🏆 <b>وضعیت:</b> {config['title']}

{'━' * 28}
"""
    
    # ═══ بخش ۲: مزایا ═══
    report += "\n📋 <b>مزایای شما:</b>\n\n"
    
    benefits_map = {
        "full": [
            "✅ معافیت کامل از شهریه دانشگاه",
            "✅ دریافت کمک‌هزینه تحصیلی (~۷,۰۰۰€/سال)",
            "✅ اولویت بالا برای خوابگاه دولتی",
            "✅ کارت غذای رایگان یا خیلی ارزان (Mensa)",
            "✅ تخفیف حمل‌ونقل عمومی",
        ],
        "partial": [
            "✅ تخفیف قابل توجه در شهریه (۳۰-۷۰٪)",
            "✅ شانس متوسط برای خوابگاه",
            "✅ کارت غذا با قیمت کاهش‌یافته",
            "⚠️ کمک‌هزینه نقدی کمتر یا بدون آن",
        ],
        "reduced": [
            "✅ تخفیف جزئی در شهریه (۱۰-۳۰٪)",
            "⚠️ احتمال کم برای خوابگاه دولتی",
            "⚠️ بدون کمک‌هزینه نقدی",
            "💡 پیشنهاد: راهکارهای کاهش ISEE را ببینید",
        ],
        "none": [
            "❌ شهریه کامل دانشگاه",
            "❌ خوابگاه دولتی در دسترس نیست",
            "❌ بدون کمک‌هزینه و تخفیف",
            "💡 نگران نباشید! راهکارهایی وجود دارد",
        ],
    }
    
    for benefit in benefits_map.get(status, []):
        report += f"{benefit}\n"
    
    # ═══ بخش ۳: مقایسه با آستانه‌ها ═══
    report += f"""
{'━' * 28}

🎯 <b>فاصله تا آستانه‌ها:</b>

"""
    
    if isee <= thresholds.full_scholarship:
        diff = thresholds.full_scholarship - isee
        report += f"🟢 بورسیه کامل: <b>{diff:,.0f}€</b> زیر سقف ✓\n"
    else:
        diff = isee - thresholds.full_scholarship
        report += f"🟢 بورسیه کامل: <b>{diff:,.0f}€</b> بالای سقف ✗\n"
    
    if isee <= thresholds.partial_scholarship:
        diff = thresholds.partial_scholarship - isee
        report += f"🟡 بورسیه جزئی: <b>{diff:,.0f}€</b> زیر سقف ✓\n"
    else:
        diff = isee - thresholds.partial_scholarship
        report += f"🟡 بورسیه جزئی: <b>{diff:,.0f}€</b> بالای سقف ✗\n"
    
    if isee <= thresholds.reduced_fee:
        diff = thresholds.reduced_fee - isee
        report += f"🟠 تخفیف شهریه: <b>{diff:,.0f}€</b> زیر سقف ✓\n"
    else:
        diff = isee - thresholds.reduced_fee
        report += f"🟠 تخفیف شهریه: <b>{diff:,.0f}€</b> بالای سقف ✗\n"
    
    # ═══ بخش ۴: مقایسه با ایرانی‌ها ═══
    comparison = get_comparison_text(isee)
    
    report += f"""
{'━' * 28}

🇮🇷 <b>مقایسه با دانشجویان ایرانی:</b>

{comparison}

📊 میانگین: {IRANIAN_STATS['average']:,}€
📊 میانه: {IRANIAN_STATS['median']:,}€

"""
    
    # ═══ بخش ۵: جزئیات محاسبه ═══
    report += f"""
{'━' * 28}

🔢 <b>جزئیات محاسبه:</b>

<b>ورودی‌ها:</b>
• درآمد اولیه: {inputs.income:,.0f}€
• تعداد اعضا: {inputs.members} نفر
• ارزش املاک: {inputs.property_value:,.0f}€
• دارایی مالی: {inputs.financial_assets:,.0f}€
• بدهی‌ها: {inputs.total_debts:,.0f}€
• دارایی خارجی: {inputs.abroad_assets:,.0f}€

<b>کسورات و معافیت‌ها:</b>
• کسر اجاره: -{result.rent_deduction:,.0f}€
• معافیت خانه: -{result.home_exemption:,.0f}€
• معافیت مالی: -{result.financial_exemption:,.0f}€
• کسر بدهی: -{result.debt_deduction:,.0f}€

<b>محاسبات:</b>
• درآمد تعدیل‌شده: {result.adjusted_income:,.0f}€
• دارایی خالص: {result.total_patrimony:,.0f}€
• ضریب خانواده: {result.scale}
• شاخص ISE: {result.ise:,.0f}€
• شاخص ISP: {result.isp:,.0f}€

<b>فرمول:</b>
ISEE = ISE ÷ ضریب
ISEE = {result.ise:,.0f} ÷ {result.scale} = <b>{result.isee:,.0f}€</b>

{'━' * 28}

💶 <b>نرخ تبدیل:</b> {inputs.eur_rate:,} تومان = 1€
📅 <b>تاریخ:</b> {datetime.now().strftime('%Y/%m/%d %H:%M')}

"""
    
    # ═══ بخش ۶: توصیه‌ها ═══
    if status in ["reduced", "none"]:
        report += f"""
{'━' * 28}

💡 <b>پیشنهاد:</b>
با استفاده از محاسبه‌گر معکوس ببینید 
چگونه می‌توانید ISEE را کاهش دهید!

"""
    
    # ═══ بخش ۷: هشدار ═══
    report += """
⚠️ <i>این محاسبه تخمینی است.
ISEE رسمی توسط CAF در ایتالیا صادر می‌شود.</i>
"""
    
    # ساخت کیبورد
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 محاسبه مجدد", callback_data="isee_mode_full"),
            InlineKeyboardButton(text="💡 راهکار کاهش", callback_data="isee_tips"),
        ],
        [
            InlineKeyboardButton(text="🎯 محاسبه‌گر معکوس", callback_data="isee_reverse_intro"),
        ],
        [
            InlineKeyboardButton(text="📜 تاریخچه", callback_data="isee_history"),
        ],
        [
            InlineKeyboardButton(
                text="📤 اشتراک‌گذاری", 
                switch_inline_query=f"🇮🇹 ISEE من: {isee:,.0f}€ | {config['title']}"
            ),
        ],
        [
            InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu"),
        ]
    ])
    
    # ارسال گزارش
    try:
        await message.edit_text(report, reply_markup=keyboard, parse_mode="HTML")
    except:
        # اگر edit نشد، پیام جدید بفرست
        await message.answer(report, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════
# بخش ۶.۶: گزارش خلاصه (نسخه کوتاه)
# ═══════════════════════════════════════════════════════════════════

async def send_short_report(message: types.Message, result: ISEEResult):
    """ارسال گزارش کوتاه (برای حالت سریع یا اشتراک‌گذاری)"""
    
    config = STATUS_CONFIG.get(result.status, STATUS_CONFIG["none"])
    
    text = f"""
{config['emoji']} <b>نتیجه محاسبه ISEE</b>

{config['bar']}

🎯 <b>ISEE:</b> <code>{result.isee:,.0f} €</code>

🏆 <b>وضعیت:</b> {config['title']}

━━━━━━━━━━━━━━━━━━━━

📊 خلاصه:
• ضریب خانواده: {result.scale}
• درآمد تعدیل‌شده: {result.adjusted_income:,.0f}€
• دارایی خالص: {result.total_patrimony:,.0f}€

━━━━━━━━━━━━━━━━━━━━

<i>برای جزئیات بیشتر، محاسبه کامل انجام دهید.</i>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 گزارش کامل", callback_data="isee_mode_full"),
        ],
        [
            InlineKeyboardButton(text="💡 راهکار کاهش", callback_data="isee_tips"),
        ],
        [
            InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu"),
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════
# بخش ۶.۷: هندلرهای محاسبه‌گر معکوس
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("isee_reverse_"))
async def handle_reverse_calculator(callback: types.CallbackQuery, state: FSMContext):
    """پردازش محاسبه‌گر معکوس"""
    
    action = callback.data.replace("isee_reverse_", "")
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    history = user.get("history", [])
    
    # اگر intro است، در بخش ۳ هندل شده
    if action == "intro":
        return
    
    if action == "custom":
        # درخواست هدف دلخواه
        text = """
✏️ <b>هدف ISEE دلخواه</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 عدد ISEE هدف خود را به <b>یورو</b> وارد کنید:

<i>مثال: 25000 یا ۲۰۰۰۰</i>
"""
        
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="25500"), KeyboardButton(text="20000")],
                [KeyboardButton(text="15000"), KeyboardButton(text="10000")],
                [KeyboardButton(text="🔙 انصراف")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await callback.message.edit_text(text, parse_mode="HTML")
        await callback.message.answer("👆 هدف ISEE:", reply_markup=keyboard)
        await state.set_state(ISEEState.reverse_calc)
        return
    
    # اهداف از پیش تعریف شده
    target_map = {
        "25500": 25500,
        "20000": 20000,
        "15000": 15000,
    }
    
    target = target_map.get(action)
    
    if not target or not history:
        await callback.answer("⚠️ ابتدا یک محاسبه انجام دهید!", show_alert=True)
        return
    
    # دریافت آخرین ورودی‌ها (تقریبی)
    last_record = history[-1]
    last_isee = last_record.get("isee", 0)
    
    # ساخت ورودی تقریبی از تاریخچه
    # (در نسخه کامل‌تر باید ورودی‌های دقیق ذخیره شوند)
    approx_inputs = ISEEInput(
        income=last_record.get("inputs_summary", {}).get("income", 20000),
        members=last_record.get("inputs_summary", {}).get("members", 4),
    )
    
    # محاسبه معکوس
    reverse_result = calculate_reverse_isee(target, approx_inputs)
    
    await show_reverse_result(callback.message, reverse_result, target, last_isee)


async def show_reverse_result(message: types.Message, result: dict, target: float, current: float):
    """نمایش نتیجه محاسبه معکوس"""
    
    if result.get("already_achieved"):
        text = f"""
🎉 <b>تبریک!</b>

شما از قبل به هدف رسیده‌اید!

🎯 هدف: {target:,}€
📊 فعلی: {current:,.0f}€

━━━━━━━━━━━━━━━━━━━━━━━━━

✅ نیازی به تغییر ندارید!
"""
    else:
        gap = result.get("gap", 0)
        strategies = result.get("strategies", [])
        
        text = f"""
🎯 <b>محاسبه معکوس ISEE</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>ISEE فعلی:</b> {current:,.0f}€
🎯 <b>هدف:</b> {target:,}€
📉 <b>نیاز به کاهش:</b> {gap:,.0f}€

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>راهکارهای پیشنهادی:</b>

"""
        
        for i, strategy in enumerate(strategies, 1):
            feasibility_emoji = {
                "high": "🟢",
                "medium": "🟡",
                "low": "🔴",
            }.get(strategy.get("feasibility", "medium"), "⚪")
            
            text += f"""
{i}. <b>{strategy['title']}</b>
   {strategy['description']}
   {feasibility_emoji} امکان‌پذیری: {strategy['feasibility']}

"""
        
        text += """
━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <i>این پیشنهادات بر اساس فرمول کلی است.
برای راهکار دقیق‌تر، به بخش نکات مراجعه کنید.</i>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💡 نکات طلایی کاهش", callback_data="isee_tips"),
        ],
        [
            InlineKeyboardButton(text="🔄 محاسبه جدید", callback_data="isee_mode_full"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee"),
        ]
    ])
    
    try:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(ISEEState.reverse_calc)
async def process_reverse_target(message: types.Message, state: FSMContext):
    """پردازش هدف ISEE در محاسبه‌گر معکوس"""
    
    user_id = message.from_user.id
    user = data_store.get_user(user_id)
    history = user.get("history", [])
    
    raw_text = message.text.strip()
    
    # چک انصراف
    if "انصراف" in raw_text or "🔙" in raw_text:
        await message.reply(
            "↩️ لغو شد.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        return
    
    # تبدیل به عدد
    target = parse_persian_amount(raw_text)
    
    if target is None or target <= 0:
        await message.reply(
            "⚠️ <b>عدد نامعتبر!</b>\n"
            "لطفاً یک عدد مثبت به یورو وارد کنید.",
            parse_mode="HTML"
        )
        return
    
    if not history:
        await message.reply(
            "⚠️ ابتدا یک محاسبه ISEE انجام دهید!",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        return
    
    last_record = history[-1]
    current_isee = last_record.get("isee", 0)
    
    # ساخت ورودی تقریبی
    approx_inputs = ISEEInput(
        income=last_record.get("inputs_summary", {}).get("income", 20000),
        members=last_record.get("inputs_summary", {}).get("members", 4),
    )
    
    # محاسبه
    reverse_result = calculate_reverse_isee(target, approx_inputs)
    
    await message.reply("⏳ در حال تحلیل...", reply_markup=ReplyKeyboardRemove())
    await asyncio.sleep(0.5)
    
    await show_reverse_result(message, reverse_result, target, current_isee)
    await state.clear()


# ═══════════════════════════════════════════════════════════════════
# بخش ۶.۸: هندلر پیام در حالت confirm
# ═══════════════════════════════════════════════════════════════════

@router.message(ISEEState.confirm_data)
async def handle_confirm_message(message: types.Message, state: FSMContext):
    """هندل پیام‌های اشتباه در صفحه تأیید"""
    
    await message.reply(
        "⚠️ <b>لطفاً از دکمه‌های بالا استفاده کنید.</b>\n\n"
        "• برای تأیید: دکمه سبز\n"
        "• برای ویرایش: دکمه‌های ✏️\n"
        "• برای لغو: دکمه ❌",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# بخش ۷.۱: سناریوی What-If (اگر... چه می‌شد؟)
# ═══════════════════════════════════════════════════════════════════

class WhatIfScenario:
    """کلاس مدیریت سناریوهای فرضی"""
    
    SCENARIOS = {
        "sell_car": {
            "title": "فروش خودرو",
            "icon": "🚗",
            "description": "اگر خودرو را بفروشم چه می‌شود؟",
            "field": "financial_assets",
            "reduction_range": (5000, 30000),  # یورو
        },
        "empty_bank": {
            "title": "خالی کردن حساب بانکی",
            "icon": "🏦",
            "description": "اگر موجودی بانک را قبل از ۳۱ دسامبر خالی کنم؟",
            "field": "financial_assets",
            "reduction_percent": 80,
        },
        "add_member": {
            "title": "افزودن عضو خانواده",
            "icon": "👨‍👩‍👧",
            "description": "اگر یک نفر به خانواده اضافه شود؟",
            "field": "members",
            "change": 1,
        },
        "become_tenant": {
            "title": "اجاره‌نشین شدن",
            "icon": "🏠",
            "description": "اگر به جای مالک، مستأجر باشیم؟",
            "field": "is_tenant",
            "value": True,
            "rent": 6000,
        },
        "transfer_property": {
            "title": "انتقال ملک",
            "icon": "📝",
            "description": "اگر ملک را به نام دیگری منتقل کنم؟",
            "field": "property_value",
            "reduction_percent": 100,
        },
        "pay_debt": {
            "title": "گرفتن وام",
            "icon": "💳",
            "description": "اگر وام بگیرم (افزایش بدهی)؟",
            "field": "total_debts",
            "increase": 20000,
        },
    }


@router.callback_query(F.data == "isee_whatif_start")
async def start_whatif(callback: types.CallbackQuery, state: FSMContext):
    """شروع سناریوی What-If"""
    
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    history = user.get("history", [])
    
    if not history:
        await callback.answer(
            "⚠️ ابتدا یک محاسبه ISEE انجام دهید!",
            show_alert=True
        )
        return
    
    last_isee = history[-1].get("isee", 0)
    
    text = f"""
🔮 <b>سناریوی «اگر...»</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>ISEE فعلی شما:</b> {last_isee:,.0f}€

یک سناریو انتخاب کنید تا ببینید 
اگر آن تغییر اتفاق بیفتد، ISEE چقدر می‌شود:

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # ساخت دکمه‌ها
    buttons = []
    for key, scenario in WhatIfScenario.SCENARIOS.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{scenario['icon']} {scenario['title']}", 
                callback_data=f"isee_whatif_{key}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee_history")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ISEEState.what_if)


@router.callback_query(F.data.startswith("isee_whatif_"))
async def process_whatif_scenario(callback: types.CallbackQuery, state: FSMContext):
    """پردازش سناریوی انتخاب شده"""
    
    scenario_key = callback.data.replace("isee_whatif_", "")
    
    if scenario_key == "start" or scenario_key == "intro":
        return
    
    if scenario_key not in WhatIfScenario.SCENARIOS:
        await callback.answer("⚠️ سناریو نامعتبر!", show_alert=True)
        return
    
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    history = user.get("history", [])
    
    if not history:
        await callback.answer("⚠️ ابتدا محاسبه کنید!", show_alert=True)
        return
    
    last_record = history[-1]
    current_isee = last_record.get("isee", 0)
    inputs_summary = last_record.get("inputs_summary", {})
    
    scenario = WhatIfScenario.SCENARIOS[scenario_key]
    
    # ساخت ورودی‌های فرضی بر اساس آخرین محاسبه
    # (در نسخه کامل‌تر باید ورودی‌های دقیق ذخیره شوند)
    hypothetical_input = ISEEInput(
        income=inputs_summary.get("income", 15000),
        members=inputs_summary.get("members", 4),
        property_value=inputs_summary.get("property", 50000),
        financial_assets=inputs_summary.get("financial", 5000),
        total_debts=inputs_summary.get("debts", 0),
        is_tenant=inputs_summary.get("is_tenant", False),
        annual_rent=inputs_summary.get("rent", 0),
        is_primary_home=True,
    )
    
    # اعمال تغییر سناریو
    field = scenario.get("field")
    
    if "reduction_percent" in scenario:
        current_val = getattr(hypothetical_input, field, 0)
        reduction = current_val * scenario["reduction_percent"] / 100
        setattr(hypothetical_input, field, current_val - reduction)
    
    elif "reduction_range" in scenario:
        low, high = scenario["reduction_range"]
        reduction = (low + high) / 2  # میانگین
        current_val = getattr(hypothetical_input, field, 0)
        setattr(hypothetical_input, field, max(0, current_val - reduction))
    
    elif "change" in scenario:
        current_val = getattr(hypothetical_input, field, 0)
        setattr(hypothetical_input, field, current_val + scenario["change"])
    
    elif "value" in scenario:
        setattr(hypothetical_input, field, scenario["value"])
        if "rent" in scenario:
            hypothetical_input.annual_rent = scenario["rent"]
    
    elif "increase" in scenario:
        current_val = getattr(hypothetical_input, field, 0)
        setattr(hypothetical_input, field, current_val + scenario["increase"])
    
    # محاسبه ISEE جدید
    new_result = calculate_isee(hypothetical_input)
    new_isee = new_result.isee
    
    # محاسبه تفاوت
    diff = new_isee - current_isee
    diff_percent = (diff / current_isee * 100) if current_isee > 0 else 0
    
    # تعیین رنگ و ایموجی
    if diff < -1000:
        change_emoji = "📉"
        change_color = "کاهش چشمگیر ✅"
    elif diff < 0:
        change_emoji = "📉"
        change_color = "کاهش 👍"
    elif diff < 1000:
        change_emoji = "➡️"
        change_color = "تقریباً ثابت"
    else:
        change_emoji = "📈"
        change_color = "افزایش ⚠️"
    
    # وضعیت جدید
    new_config = STATUS_CONFIG.get(new_result.status, STATUS_CONFIG["none"])
    current_config = STATUS_CONFIG.get(last_record.get("status", "none"), STATUS_CONFIG["none"])
    
    text = f"""
🔮 <b>نتیجه سناریو: {scenario['title']}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

{scenario['icon']} <b>{scenario['description']}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>مقایسه:</b>

<b>فعلی:</b>
{current_config['bar']}
ISEE: <code>{current_isee:,.0f}€</code>
وضعیت: {current_config['title']}

{change_emoji} <b>تغییر: {diff:+,.0f}€ ({diff_percent:+.1f}%)</b>
{change_color}

<b>با این سناریو:</b>
{new_config['bar']}
ISEE: <code>{new_isee:,.0f}€</code>
وضعیت: {new_config['title']}

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # بررسی تغییر وضعیت
    if new_result.status != last_record.get("status"):
        if new_isee < current_isee:
            text += f"\n🎉 <b>ارتقاء وضعیت!</b>\n"
        else:
            text += f"\n⚠️ <b>کاهش وضعیت!</b>\n"
    
    text += """
━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <i>این یک شبیه‌سازی است و ممکن است 
با واقعیت تفاوت داشته باشد.</i>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 سناریوی دیگر", callback_data="isee_whatif_start"),
        ],
        [
            InlineKeyboardButton(text="🚀 محاسبه واقعی جدید", callback_data="isee_mode_full"),
        ],
        [
            InlineKeyboardButton(text="💡 نکات کاهش ISEE", callback_data="isee_tips"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee_history"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════
# بخش ۷.۲: خروجی PDF
# ═══════════════════════════════════════════════════════════════════

async def generate_isee_pdf(result: ISEEResult, inputs: ISEEInput, user_name: str = "") -> bytes:
    """
    تولید گزارش PDF از نتیجه ISEE
    
    نیازمند: pip install reportlab
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io
        
        # ایجاد بافر
        buffer = io.BytesIO()
        
        # ساخت داکیومنت
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # استایل‌ها
        styles = getSampleStyleSheet()
        
        # محتوا
        story = []
        
        # عنوان
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # وسط‌چین
        )
        story.append(Paragraph("ISEE Calculation Report", title_style))
        story.append(Spacer(1, 20))
        
        # اطلاعات کاربر
        if user_name:
            story.append(Paragraph(f"<b>Name:</b> {user_name}", styles['Normal']))
        story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # نتیجه اصلی
        result_style = ParagraphStyle(
            'Result',
            parent=styles['Heading2'],
            fontSize=28,
            textColor=colors.darkblue,
            alignment=1,
        )
        story.append(Paragraph(f"ISEE: €{result.isee:,.2f}", result_style))
        story.append(Paragraph(f"Status: {result.status_text}", styles['Heading3']))
        story.append(Spacer(1, 30))
        
        # جدول ورودی‌ها
        input_data = [
            ['Parameter', 'Value (EUR)'],
            ['Annual Income', f'€{inputs.income:,.0f}'],
            ['Family Members', str(inputs.members)],
            ['Property Value', f'€{inputs.property_value:,.0f}'],
            ['Financial Assets', f'€{inputs.financial_assets:,.0f}'],
            ['Total Debts', f'€{inputs.total_debts:,.0f}'],
            ['Foreign Assets', f'€{inputs.abroad_assets:,.0f}'],
        ]
        
        input_table = Table(input_data, colWidths=[8*cm, 6*cm])
        input_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(Paragraph("<b>Input Data:</b>", styles['Heading3']))
        story.append(Spacer(1, 10))
        story.append(input_table)
        story.append(Spacer(1, 20))
        
        # جدول کسورات
        deduction_data = [
            ['Deduction', 'Amount (EUR)'],
            ['Rent Deduction', f'-€{result.rent_deduction:,.0f}'],
            ['Primary Home Exemption', f'-€{result.home_exemption:,.0f}'],
            ['Financial Exemption', f'-€{result.financial_exemption:,.0f}'],
            ['Debt Deduction', f'-€{result.debt_deduction:,.0f}'],
        ]
        
        deduction_table = Table(deduction_data, colWidths=[8*cm, 6*cm])
        deduction_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(Paragraph("<b>Deductions Applied:</b>", styles['Heading3']))
        story.append(Spacer(1, 10))
        story.append(deduction_table)
        story.append(Spacer(1, 20))
        
        # جدول محاسبات
        calc_data = [
            ['Calculation', 'Value'],
            ['Adjusted Income', f'€{result.adjusted_income:,.0f}'],
            ['Total Patrimony', f'€{result.total_patrimony:,.0f}'],
            ['Family Scale', str(result.scale)],
            ['ISE Indicator', f'€{result.ise:,.0f}'],
            ['ISP Indicator', f'€{result.isp:,.0f}'],
            ['Final ISEE', f'€{result.isee:,.2f}'],
        ]
        
        calc_table = Table(calc_data, colWidths=[8*cm, 6*cm])
        calc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.yellow),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
        ]))
        
        story.append(Paragraph("<b>Calculation Details:</b>", styles['Heading3']))
        story.append(Spacer(1, 10))
        story.append(calc_table)
        story.append(Spacer(1, 30))
        
        # فوتر
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            alignment=1,
        )
        story.append(Paragraph(
            "This is an estimated calculation. Official ISEE must be issued by CAF in Italy.",
            footer_style
        ))
        story.append(Paragraph(
            f"Generated by ISEE Calculator Bot | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            footer_style
        ))
        
        # ساخت PDF
        doc.build(story)
        
        # بازگرداندن محتوا
        buffer.seek(0)
        return buffer.getvalue()
        
    except ImportError:
        logger.warning("ReportLab not installed. PDF generation unavailable.")
        return None
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        return None


@router.callback_query(F.data == "isee_export_pdf")
async def export_pdf(callback: types.CallbackQuery):
    """صادر کردن گزارش PDF"""
    
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    history = user.get("history", [])
    
    if not history:
        await callback.answer("⚠️ ابتدا یک محاسبه انجام دهید!", show_alert=True)
        return
    
    await callback.answer("⏳ در حال تولید PDF...")
    
    # دریافت آخرین نتیجه
    last_record = history[-1]
    
    # ساخت ورودی و نتیجه موقت (در نسخه کامل باید ذخیره شده باشد)
    temp_inputs = ISEEInput(
        income=last_record.get("inputs_summary", {}).get("income", 0),
        members=last_record.get("inputs_summary", {}).get("members", 1),
    )
    
    temp_result = ISEEResult(
        isee=last_record.get("isee", 0),
        ise=0,
        isp=0,
        scale=calculate_family_scale(temp_inputs.members),
        status=last_record.get("status", "none"),
        status_text=STATUS_CONFIG.get(last_record.get("status", "none"), {}).get("title", "Unknown"),
    )
    
    # تولید PDF
    pdf_bytes = await generate_isee_pdf(
        temp_result, 
        temp_inputs,
        callback.from_user.full_name
    )
    
    if pdf_bytes:
        from aiogram.types import BufferedInputFile
        
        pdf_file = BufferedInputFile(
            pdf_bytes,
            filename=f"ISEE_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        )
        
        await callback.message.answer_document(
            pdf_file,
            caption="📄 <b>گزارش ISEE شما</b>\n\n"
                    f"🎯 ISEE: {temp_result.isee:,.0f}€\n"
                    f"📅 تاریخ: {datetime.now().strftime('%Y/%m/%d')}",
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            "⚠️ <b>خطا در تولید PDF</b>\n\n"
            "متأسفانه در حال حاضر امکان تولید PDF وجود ندارد.\n"
            "لطفاً از اسکرین‌شات استفاده کنید.",
            parse_mode="HTML"
        )


# ═══════════════════════════════════════════════════════════════════
# بخش ۷.۳: یادآوری ددلاین‌ها
# ═══════════════════════════════════════════════════════════════════

# ددلاین‌های مهم DSU
DSU_DEADLINES = {
    "isee_submission": {
        "date": "2025-11-15",
        "title": "مهلت ارائه ISEE",
        "description": "آخرین فرصت برای ارائه ISEE به دانشگاه",
        "priority": "high",
    },
    "scholarship_application": {
        "date": "2025-09-30",
        "title": "ثبت‌نام بورسیه",
        "description": "مهلت ثبت‌نام برای بورسیه تحصیلی DSU",
        "priority": "high",
    },
    "dormitory_application": {
        "date": "2025-08-31",
        "title": "درخواست خوابگاه",
        "description": "مهلت درخواست خوابگاه دولتی",
        "priority": "medium",
    },
    "document_deadline": {
        "date": "2025-12-31",
        "title": "تکمیل مدارک",
        "description": "آخرین مهلت تکمیل مدارک CAF",
        "priority": "medium",
    },
    "isee_validity": {
        "date": "2025-12-31",
        "title": "اعتبار ISEE",
        "description": "ISEE سال جاری تا این تاریخ معتبر است",
        "priority": "low",
    },
}


@router.callback_query(F.data == "isee_deadlines")
async def show_deadlines(callback: types.CallbackQuery):
    """نمایش ددلاین‌های مهم"""
    
    today = datetime.now().date()
    
    text = """
📅 <b>ددلاین‌های مهم ISEE و بورسیه</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    # مرتب‌سازی بر اساس تاریخ
    sorted_deadlines = sorted(
        DSU_DEADLINES.items(),
        key=lambda x: datetime.strptime(x[1]["date"], "%Y-%m-%d")
    )
    
    for key, deadline in sorted_deadlines:
        deadline_date = datetime.strptime(deadline["date"], "%Y-%m-%d").date()
        days_left = (deadline_date - today).days
        
        # تعیین ایموجی
        if days_left < 0:
            emoji = "❌"
            status = "گذشته"
        elif days_left == 0:
            emoji = "🔴"
            status = "امروز!"
        elif days_left <= 7:
            emoji = "🟠"
            status = f"{days_left} روز مانده"
        elif days_left <= 30:
            emoji = "🟡"
            status = f"{days_left} روز مانده"
        else:
            emoji = "🟢"
            status = f"{days_left} روز مانده"
        
        priority_icon = {
            "high": "⚠️",
            "medium": "📌",
            "low": "ℹ️",
        }.get(deadline["priority"], "")
        
        text += f"{emoji} <b>{deadline['title']}</b> {priority_icon}\n"
        text += f"   📅 {deadline['date']} ({status})\n"
        text += f"   <i>{deadline['description']}</i>\n\n"
    
    text += """
━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>توصیه:</b>
حداقل ۲ هفته قبل از ددلاین، مدارک را آماده کنید!
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔔 فعال‌سازی یادآور", callback_data="isee_set_reminder"),
        ],
        [
            InlineKeyboardButton(text="🚀 شروع محاسبه ISEE", callback_data="isee_mode_full"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "isee_set_reminder")
async def set_reminder(callback: types.CallbackQuery):
    """فعال‌سازی یادآور (placeholder)"""
    
    text = """
🔔 <b>یادآور ددلاین</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

برای کدام ددلاین می‌خواهید یادآور فعال شود؟

<i>یادآور ۷ روز و ۱ روز قبل ارسال می‌شود.</i>

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    buttons = []
    for key, deadline in DSU_DEADLINES.items():
        deadline_date = datetime.strptime(deadline["date"], "%Y-%m-%d").date()
        if deadline_date > datetime.now().date():
            buttons.append([
                InlineKeyboardButton(
                    text=f"📅 {deadline['title']} ({deadline['date']})",
                    callback_data=f"isee_remind_{key}"
                )
            ])
    
    buttons.append([
        InlineKeyboardButton(text="📅 همه ددلاین‌ها", callback_data="isee_remind_all")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee_deadlines")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("isee_remind_"))
async def confirm_reminder(callback: types.CallbackQuery):
    """تأیید فعال‌سازی یادآور"""
    
    reminder_key = callback.data.replace("isee_remind_", "")
    
    # در نسخه واقعی باید در دیتابیس ذخیره شود
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    
    if "reminders" not in user:
        user["reminders"] = []
    
    if reminder_key == "all":
        user["reminders"] = list(DSU_DEADLINES.keys())
        reminder_text = "همه ددلاین‌ها"
    else:
        if reminder_key not in user["reminders"]:
            user["reminders"].append(reminder_key)
        deadline = DSU_DEADLINES.get(reminder_key, {})
        reminder_text = deadline.get("title", reminder_key)
    
    await callback.answer(f"✅ یادآور فعال شد: {reminder_text}", show_alert=True)
    
    text = f"""
✅ <b>یادآور فعال شد!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

🔔 <b>{reminder_text}</b>

شما یادآور دریافت خواهید کرد:
• ۷ روز قبل از ددلاین
• ۱ روز قبل از ددلاین
• روز ددلاین

━━━━━━━━━━━━━━━━━━━━━━━━━

<i>برای غیرفعال کردن، به تنظیمات مراجعه کنید.</i>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 مشاهده ددلاین‌ها", callback_data="isee_deadlines"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت به ISEE", callback_data="isee"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════
# بخش ۷.۴: اتصال به سایر ماژول‌ها
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee_get_consultation")
async def redirect_to_consultation(callback: types.CallbackQuery):
    """هدایت به ماژول مشاوره"""
    
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    history = user.get("history", [])
    
    isee_info = ""
    if history:
        last = history[-1]
        isee_info = f"\n\n📊 ISEE: {last.get('isee', 0):,.0f}€"
        isee_info += f"\n🏆 وضعیت: {STATUS_CONFIG.get(last.get('status', 'none'), {}).get('title', '')}"
    
    text = f"""
👨‍💼 <b>مشاوره تخصصی ISEE</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

برای موارد زیر می‌توانید مشاوره بگیرید:

• بررسی دقیق وضعیت مالی
• راهکارهای قانونی کاهش ISEE
• کمک در تهیه مدارک CAF
• پاسخ به سؤالات پیچیده
{isee_info}

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 شروع چت با مشاور", callback_data="consult_start"),
        ],
        [
            InlineKeyboardButton(text="📞 رزرو تماس تلفنی", callback_data="consult_call"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "isee_dsu_guide")
async def show_dsu_guide(callback: types.CallbackQuery):
    """راهنمای کامل DSU"""
    
    text = """
📚 <b>راهنمای جامع DSU</b>
<i>(Diritto allo Studio Universitario)</i>

━━━━━━━━━━━━━━━━━━━━━━━━━

🎓 <b>DSU چیست؟</b>
سازمان‌های منطقه‌ای که خدمات رفاهی به دانشجویان ارائه می‌دهند.

━━━━━━━━━━━━━━━━━━━━━━━━━

📋 <b>خدمات DSU:</b>

💰 <b>بورسیه تحصیلی:</b>
• مبلغ: ۲,۰۰۰ تا ۷,۰۰۰€ در سال
• شرط: ISEE زیر ۲۵,۵۰۰€
• شرط تحصیلی: کسب حداقل ۱۰ CFU در سال اول

🏠 <b>خوابگاه:</b>
• اولویت با ISEE پایین‌تر
• هزینه: ۱۵۰-۴۰۰€ در ماه
• شامل آب، برق، اینترنت

🍽 <b>کارت غذا (Mensa):</b>
• وعده غذا: ۲-۵€ (بسته به ISEE)
• بدون تخفیف: ۸-۱۲€

🚌 <b>حمل‌ونقل:</b>
• تخفیف بلیت ماهانه/سالانه
• بعضی مناطق رایگان

━━━━━━━━━━━━━━━━━━━━━━━━━

📝 <b>مراحل ثبت‌نام:</b>

1️⃣ گرفتن ISEE از CAF
2️⃣ ثبت‌نام آنلاین در سایت DSU منطقه
3️⃣ آپلود مدارک
4️⃣ انتظار برای نتیجه

━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 <b>سایت‌های DSU منطقه‌ای:</b>

• لومباردی: www.dsu.lombardia.it
• امیلیا رومانیا: www.er-go.it
• توسکانی: www.dsu.toscana.it
• لاتزیو: www.laziodisu.it
• ونتو: www.esu.venezia.it

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 ددلاین‌ها", callback_data="isee_deadlines"),
        ],
        [
            InlineKeyboardButton(text="🧮 محاسبه ISEE", callback_data="isee_mode_full"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════
# بخش ۷.۵: ابزار مقایسه دانشگاه‌ها
# ═══════════════════════════════════════════════════════════════════

UNIVERSITY_DATA = {
    "polimi": {
        "name": "Politecnico di Milano",
        "city": "Milano",
        "region": Region.NORD,
        "tuition_max": 4000,
        "scholarship_rate": 0.35,
    },
    "unibo": {
        "name": "Università di Bologna",
        "city": "Bologna",
        "region": Region.NORD,
        "tuition_max": 3500,
        "scholarship_rate": 0.40,
    },
    "uniroma": {
        "name": "Sapienza - Roma",
        "city": "Roma",
        "region": Region.CENTRO,
        "tuition_max": 2900,
        "scholarship_rate": 0.38,
    },
    "unifi": {
        "name": "Università di Firenze",
        "city": "Firenze",
        "region": Region.CENTRO,
        "tuition_max": 2700,
        "scholarship_rate": 0.42,
    },
    "unina": {
        "name": "Università di Napoli",
        "city": "Napoli",
        "region": Region.SUD,
        "tuition_max": 2500,
        "scholarship_rate": 0.45,
    },
}


@router.callback_query(F.data == "isee_compare_universities")
async def compare_universities(callback: types.CallbackQuery):
    """مقایسه شانس بورسیه در دانشگاه‌های مختلف"""
    
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    history = user.get("history", [])
    
    if not history:
        await callback.answer("⚠️ ابتدا ISEE را محاسبه کنید!", show_alert=True)
        return
    
    current_isee = history[-1].get("isee", 0)
    
    text = f"""
🏛 <b>مقایسه شانس بورسیه در دانشگاه‌ها</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>ISEE شما:</b> {current_isee:,.0f}€

━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    for key, uni in UNIVERSITY_DATA.items():
        thresholds = REGIONAL_THRESHOLDS[uni["region"]]
        
        # تعیین وضعیت
        if current_isee <= thresholds.full_scholarship:
            chance = "🟢 بورسیه کامل"
            chance_percent = 95
        elif current_isee <= thresholds.partial_scholarship:
            chance = "🟡 بورسیه جزئی"
            chance_percent = 70
        elif current_isee <= thresholds.reduced_fee:
            chance = "🟠 تخفیف شهریه"
            chance_percent = 40
        else:
            chance = "🔴 بدون تخفیف"
            chance_percent = 5
        
        # نوار شانس
        filled = int(chance_percent / 10)
        bar = "█" * filled + "░" * (10 - filled)
        
        text += f"<b>{uni['name']}</b>\n"
        text += f"   📍 {uni['city']}\n"
        text += f"   {chance}\n"
        text += f"   [{bar}] {chance_percent}%\n\n"
    
    text += """
━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <i>درصدها تقریبی است و به شرایط تحصیلی هم بستگی دارد.</i>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📚 راهنمای DSU", callback_data="isee_dsu_guide"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════
# بخش ۷.۶: تنظیمات کاربر
# ═══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "isee_settings")
async def show_settings(callback: types.CallbackQuery):
    """نمایش تنظیمات کاربر"""
    
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    settings = user.get("settings", {})
    
    # مقادیر فعلی
    currency = settings.get("preferred_currency", "toman")
    region = settings.get("region", Region.CENTRO)
    show_tips = settings.get("show_tips", True)
    
    currency_text = "تومان 🇮🇷" if currency == "toman" else "یورو 🇪🇺"
    region_text = {
        Region.NORD: "شمال 🏔",
        Region.CENTRO: "مرکز 🏛",
        Region.SUD: "جنوب 🌊",
    }.get(region, "مرکز")
    tips_text = "فعال ✅" if show_tips else "غیرفعال ❌"
    
    text = f"""
⚙️ <b>تنظیمات ISEE Calculator</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

💱 <b>واحد پول پیش‌فرض:</b> {currency_text}

🗺 <b>منطقه پیش‌فرض:</b> {region_text}

💡 <b>نمایش نکات:</b> {tips_text}

━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>آمار شما:</b>
• تعداد محاسبات: {len(user.get('history', []))}
• یادآورهای فعال: {len(user.get('reminders', []))}

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"💱 واحد پول: {currency_text}", 
                callback_data="isee_toggle_currency"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"🗺 منطقه: {region_text}", 
                callback_data="isee_change_region"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"💡 نکات: {tips_text}", 
                callback_data="isee_toggle_tips"
            ),
        ],
        [
            InlineKeyboardButton(text="🗑 پاک کردن تاریخچه", callback_data="isee_clear_history"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "isee_toggle_currency")
async def toggle_currency(callback: types.CallbackQuery):
    """تغییر واحد پول"""
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    
    current = user.get("settings", {}).get("preferred_currency", "toman")
    new_currency = "euro" if current == "toman" else "toman"
    user["settings"]["preferred_currency"] = new_currency
    
    await callback.answer(f"✅ واحد پول به {'یورو' if new_currency == 'euro' else 'تومان'} تغییر کرد!")
    await show_settings(callback)


@router.callback_query(F.data == "isee_toggle_tips")
async def toggle_tips(callback: types.CallbackQuery):
    """تغییر نمایش نکات"""
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    
    current = user.get("settings", {}).get("show_tips", True)
    user["settings"]["show_tips"] = not current
    
    await callback.answer(f"✅ نمایش نکات {'فعال' if not current else 'غیرفعال'} شد!")
    await show_settings(callback)


@router.callback_query(F.data == "isee_clear_history")
async def clear_history_confirm(callback: types.CallbackQuery):
    """تأیید پاک کردن تاریخچه"""
    
    text = """
⚠️ <b>پاک کردن تاریخچه</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

آیا مطمئنید می‌خواهید تمام تاریخچه محاسبات را پاک کنید؟

<b>این عمل قابل بازگشت نیست!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ بله، پاک کن", callback_data="isee_clear_history_confirm"),
            InlineKeyboardButton(text="❌ انصراف", callback_data="isee_settings"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "isee_clear_history_confirm")
async def clear_history_execute(callback: types.CallbackQuery):
    """اجرای پاک کردن تاریخچه"""
    user_id = callback.from_user.id
    user = data_store.get_user(user_id)
    
    user["history"] = []
    
    await callback.answer("✅ تاریخچه پاک شد!", show_alert=True)
    await show_settings(callback)


# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# بخش ۸.۱: Error Handlers و مدیریت خطا
# ═══════════════════════════════════════════════════════════════════

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from functools import wraps
import traceback

def error_handler(func):
    """دکوراتور مدیریت خطا برای هندلرها"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except TelegramBadRequest as e:
            logger.warning(f"Telegram Bad Request in {func.__name__}: {e}")
            # پیام قبلی حذف شده یا تغییر نکرده
            pass
        except TelegramForbiddenError as e:
            logger.warning(f"Bot blocked by user in {func.__name__}: {e}")
            pass
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}\n{traceback.format_exc()}")
            # تلاش برای ارسال پیام خطا به کاربر
            try:
                if args and hasattr(args[0], 'message'):
                    await args[0].message.answer(
                        "⚠️ <b>خطایی رخ داد!</b>\n\n"
                        "لطفاً دوباره تلاش کنید.\n"
                        "اگر مشکل ادامه داشت، از /start استفاده کنید.",
                        parse_mode="HTML"
                    )
                elif args and hasattr(args[0], 'answer'):
                    await args[0].answer(
                        "⚠️ خطایی رخ داد. دوباره تلاش کنید.",
                        show_alert=True
                    )
            except:
                pass
    return wrapper


# اعمال دکوراتور به هندلرهای مهم (اختیاری)
# می‌توانید به صورت دستی به هر هندلر اضافه کنید


@router.error()
async def global_error_handler(event, exception):
    """هندلر سراسری خطاها"""
    logger.error(f"Global error: {exception}\n{traceback.format_exc()}")
    return True  # خطا هندل شد


# ═══════════════════════════════════════════════════════════════════
# بخش ۸.۲: Middleware برای لاگینگ
# ═══════════════════════════════════════════════════════════════════

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Awaitable

class ISEELoggingMiddleware(BaseMiddleware):
    """میدل‌ور لاگینگ برای ISEE"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable],
        event: TelegramObject,
        data: dict
    ):
        # لاگ قبل از هندل
        user = None
        if hasattr(event, 'from_user'):
            user = event.from_user
        elif hasattr(event, 'message') and event.message:
            user = event.message.from_user
        
        if user:
            logger.debug(f"ISEE Handler: user={user.id}, event={type(event).__name__}")
        
        # اجرای هندلر
        result = await handler(event, data)
        
        return result


class RateLimitMiddleware(BaseMiddleware):
    """میدل‌ور محدودیت نرخ درخواست"""
    
    def __init__(self, limit: int = 30, period: int = 60):
        self.limit = limit  # تعداد درخواست
        self.period = period  # دوره زمانی (ثانیه)
        self.requests: Dict[int, list] = {}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable],
        event: TelegramObject,
        data: dict
    ):
        user_id = None
        if hasattr(event, 'from_user'):
            user_id = event.from_user.id
        elif hasattr(event, 'message') and event.message:
            user_id = event.message.from_user.id
        
        if user_id:
            now = datetime.now().timestamp()
            
            # پاکسازی درخواست‌های قدیمی
            if user_id in self.requests:
                self.requests[user_id] = [
                    t for t in self.requests[user_id] 
                    if now - t < self.period
                ]
            else:
                self.requests[user_id] = []
            
            # بررسی محدودیت
            if len(self.requests[user_id]) >= self.limit:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                
                if hasattr(event, 'answer'):
                    await event.answer(
                        "⚠️ تعداد درخواست‌های شما زیاد است. کمی صبر کنید.",
                        show_alert=True
                    )
                return
            
            # ثبت درخواست
            self.requests[user_id].append(now)
        
        return await handler(event, data)


# فعال‌سازی میدل‌ورها
# router.message.middleware(ISEELoggingMiddleware())
# router.callback_query.middleware(RateLimitMiddleware())


# ═══════════════════════════════════════════════════════════════════
# بخش ۸.۳: هندلرهای عمومی و Fallback
# ═══════════════════════════════════════════════════════════════════

@router.message(ISEEState.select_mode)
async def handle_select_mode_message(message: types.Message):
    """هندل پیام در حالت انتخاب mode"""
    await message.reply(
        "⚠️ لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🚀 محاسبه کامل", callback_data="isee_mode_full"),
                InlineKeyboardButton(text="⚡ سریع", callback_data="isee_mode_quick"),
            ]
        ])
    )


@router.callback_query(F.data == "isee_help")
async def show_isee_help(callback: types.CallbackQuery):
    """راهنمای استفاده از ISEE Calculator"""
    
    text = """
❓ <b>راهنمای ISEE Calculator</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

📖 <b>ISEE چیست؟</b>
ISEE (Indicatore della Situazione Economica Equivalente) 
شاخصی است که وضعیت اقتصادی خانواده را نشان می‌دهد.

━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 <b>چرا مهم است؟</b>
• تعیین‌کننده دریافت بورسیه تحصیلی
• اولویت‌بندی برای خوابگاه
• میزان تخفیف شهریه

━━━━━━━━━━━━━━━━━━━━━━━━━

📝 <b>چگونه محاسبه می‌شود؟</b>

<code>ISE = درآمد + (20% × دارایی)</code>
<code>ISEE = ISE ÷ ضریب خانواده</code>

━━━━━━━━━━━━━━━━━━━━━━━━━

🔢 <b>اطلاعات مورد نیاز:</b>

1️⃣ درآمد سالانه خانواده
2️⃣ تعداد اعضای خانواده
3️⃣ ارزش املاک
4️⃣ موجودی بانک و پس‌انداز
5️⃣ بدهی‌ها
6️⃣ دارایی خارجی

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>نکات مهم:</b>

• مقادیر به <b>تومان</b> یا <b>یورو</b> قابل ورود است
• سیستم به صورت هوشمند تشخیص می‌دهد
• برای دقت بیشتر، از حالت «کامل» استفاده کنید
• این محاسبه تخمینی است

━━━━━━━━━━━━━━━━━━━━━━━━━

🏢 <b>ISEE رسمی کجا صادر می‌شود؟</b>
مراکز CAF در ایتالیا (پس از ورود به کشور)

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 شروع محاسبه", callback_data="isee_mode_full"),
        ],
        [
            InlineKeyboardButton(text="🌍 ISEE Parificato", callback_data="isee_parificato"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "isee_faq")
async def show_faq(callback: types.CallbackQuery):
    """سؤالات متداول"""
    
    text = """
❓ <b>سؤالات متداول ISEE</b>

━━━━━━━━━━━━━━━━━━━━━━━━━

<b>س: آیا این محاسبه رسمی است؟</b>
ج: خیر، این تخمینی است. ISEE رسمی فقط توسط CAF صادر می‌شود.

━━━━━━━━━━━━━━━━━━━━━━━━━

<b>س: چرا ISEE من با دوستم فرق دارد؟</b>
ج: ISEE به درآمد، دارایی و تعداد اعضای خانواده بستگی دارد.

━━━━━━━━━━━━━━━━━━━━━━━━━

<b>س: اگر ازدواج کنم چه می‌شود؟</b>
ج: خانواده جدید تشکیل می‌شود و ISEE جداگانه محاسبه می‌شود.

━━━━━━━━━━━━━━━━━━━━━━━━━

<b>س: ملک به نام پدربزرگ حساب می‌شود؟</b>
ج: خیر، فقط اموال اعضای هسته خانواده حساب می‌شود.

━━━━━━━━━━━━━━━━━━━━━━━━━

<b>س: ماشین جزء دارایی است؟</b>
ج: بله، ارزش خودرو در دارایی مالی لحاظ می‌شود.

━━━━━━━━━━━━━━━━━━━━━━━━━

<b>س: طلا و جواهر چطور؟</b>
ج: اگر ارزش بالایی دارند، به صورت تقریبی وارد کنید.

━━━━━━━━━━━━━━━━━━━━━━━━━

<b>س: وام مسکن کمک می‌کند؟</b>
ج: بله! مانده بدهی از ارزش ملک کسر می‌شود.

━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 سؤال دیگری دارم", callback_data="isee_get_consultation"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="isee"),
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════
# بخش ۸.۴: توابع کمکی برای یکپارچه‌سازی
# ═══════════════════════════════════════════════════════════════════

async def get_user_isee_summary(user_id: int) -> Optional[dict]:
    """دریافت خلاصه وضعیت ISEE کاربر برای استفاده در سایر ماژول‌ها"""
    
    user = data_store.get_user(user_id)
    history = user.get("history", [])
    
    if not history:
        return None
    
    last = history[-1]
    
    return {
        "isee": last.get("isee", 0),
        "status": last.get("status", "none"),
        "status_text": STATUS_CONFIG.get(last.get("status", "none"), {}).get("title", ""),
        "date": last.get("date", ""),
        "calculation_count": len(history),
    }


async def check_scholarship_eligibility(user_id: int, university_region: Region = Region.CENTRO) -> dict:
    """بررسی واجد شرایط بودن برای بورسیه - برای استفاده در سایر ماژول‌ها"""
    
    user = data_store.get_user(user_id)
    history = user.get("history", [])
    
    if not history:
        return {
            "eligible": None,
            "message": "ابتدا ISEE را محاسبه کنید.",
            "isee": None,
        }
    
    isee = history[-1].get("isee", 0)
    thresholds = REGIONAL_THRESHOLDS.get(university_region, DEFAULT_THRESHOLDS)
    
    if isee <= thresholds.full_scholarship:
        return {
            "eligible": True,
            "level": "full",
            "message": "واجد شرایط بورسیه کامل",
            "isee": isee,
        }
    elif isee <= thresholds.partial_scholarship:
        return {
            "eligible": True,
            "level": "partial",
            "message": "واجد شرایط بورسیه جزئی",
            "isee": isee,
        }
    elif isee <= thresholds.reduced_fee:
        return {
            "eligible": True,
            "level": "reduced",
            "message": "واجد شرایط تخفیف شهریه",
            "isee": isee,
        }
    else:
        return {
            "eligible": False,
            "level": "none",
            "message": "واجد شرایط بورسیه نیست",
            "isee": isee,
        }


def export_user_data(user_id: int) -> dict:
    """صادر کردن تمام داده‌های کاربر - برای بکاپ یا انتقال"""
    
    user = data_store.get_user(user_id)
    
    return {
        "user_id": user_id,
        "export_date": datetime.now().isoformat(),
        "history": user.get("history", []),
        "settings": user.get("settings", {}),
        "reminders": user.get("reminders", []),
    }


def import_user_data(user_id: int, data: dict) -> bool:
    """وارد کردن داده‌های کاربر از بکاپ"""
    
    try:
        user = data_store.get_user(user_id)
        
        if "history" in data:
            user["history"] = data["history"]
        if "settings" in data:
            user["settings"].update(data["settings"])
        if "reminders" in data:
            user["reminders"] = data["reminders"]
        
        return True
    except Exception as e:
        logger.error(f"Import user data error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════
# بخش ۸.۵: آپدیت کیبورد منوی اصلی ISEE
# ═══════════════════════════════════════════════════════════════════

def build_isee_main_menu(user_id: int) -> InlineKeyboardMarkup:
    """ساخت کیبورد منوی اصلی ISEE با توجه به وضعیت کاربر"""
    
    user = data_store.get_user(user_id)
    history = user.get("history", [])
    
    buttons = [
        # ردیف ۱: محاسبه
        [
            InlineKeyboardButton(text="🚀 محاسبه کامل", callback_data="isee_mode_full"),
            InlineKeyboardButton(text="⚡ سریع", callback_data="isee_mode_quick"),
        ],
    ]
    
    # ردیف ۲: ابزارها (اگر تاریخچه دارد)
    if history:
        buttons.append([
            InlineKeyboardButton(text="📜 تاریخچه", callback_data="isee_history"),
            InlineKeyboardButton(text="🔮 What-If", callback_data="isee_whatif_start"),
        ])
        buttons.append([
            InlineKeyboardButton(text="🎯 محاسبه معکوس", callback_data="isee_reverse_intro"),
            InlineKeyboardButton(text="🏛 مقایسه دانشگاه", callback_data="isee_compare_universities"),
        ])
    
    # ردیف ۳: اطلاعات
    buttons.append([
        InlineKeyboardButton(text="💡 نکات طلایی", callback_data="isee_tips"),
        InlineKeyboardButton(text="🌍 Parificato", callback_data="isee_parificato"),
    ])
    
    # ردیف ۴: راهنما و تنظیمات
    buttons.append([
        InlineKeyboardButton(text="📅 ددلاین‌ها", callback_data="isee_deadlines"),
        InlineKeyboardButton(text="📚 راهنمای DSU", callback_data="isee_dsu_guide"),
    ])
    
    buttons.append([
        InlineKeyboardButton(text="❓ راهنما", callback_data="isee_help"),
        InlineKeyboardButton(text="⚙️ تنظیمات", callback_data="isee_settings"),
    ])
    
    # ردیف آخر: بازگشت
    buttons.append([
        InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="main_menu"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ═══════════════════════════════════════════════════════════════════
# بخش ۸.۶: تست‌های واحد (Unit Tests)
# ═══════════════════════════════════════════════════════════════════

"""
برای اجرای تست‌ها:
    pytest handlers/test_isee.py -v

یا:
    python -m pytest handlers/test_isee.py -v
"""

# این بخش را در فایل جداگانه test_isee.py قرار دهید:

TEST_CODE = '''
# handlers/test_isee.py
import pytest
from handlers.isee_handler import (
    parse_persian_amount,
    normalize_persian_text,
    smart_currency_convert,
    calculate_family_scale,
    calculate_isee,
    calculate_rent_deduction,
    calculate_primary_home_exemption,
    calculate_financial_exemption,
    calculate_reverse_isee,
    ISEEInput,
    ISEEResult,
    CurrencyType,
    DEDUCTION_LIMITS,
)


class TestParsePersianAmount:
    """تست‌های تبدیل عدد فارسی"""
    
    def test_simple_number(self):
        assert parse_persian_amount("1000") == 1000.0
    
    def test_persian_digits(self):
        assert parse_persian_amount("۱۲۳۴") == 1234.0
    
    def test_million(self):
        assert parse_persian_amount("۵۰ میلیون") == 50_000_000.0
        assert parse_persian_amount("50 میلیون") == 50_000_000.0
    
    def test_billion(self):
        assert parse_persian_amount("۲ میلیارد") == 2_000_000_000.0
    
    def test_zero_phrases(self):
        assert parse_persian_amount("0") == 0.0
        assert parse_persian_amount("ندارم") == 0.0
        assert parse_persian_amount("هیچ") == 0.0
    
    def test_invalid(self):
        assert parse_persian_amount("abc") is None
        assert parse_persian_amount("") is None
    
    def test_with_commas(self):
        assert parse_persian_amount("1,000,000") == 1_000_000.0
        assert parse_persian_amount("۱،۰۰۰،۰۰۰") == 1_000_000.0


class TestSmartCurrencyConvert:
    """تست‌های تشخیص و تبدیل ارز"""
    
    def test_small_amount_euro(self):
        eur, currency, _ = smart_currency_convert(500, 70000, "500")
        assert currency == CurrencyType.EURO
        assert eur == 500
    
    def test_large_amount_toman(self):
        eur, currency, _ = smart_currency_convert(700_000_000, 70000, "۷۰۰ میلیون")
        assert currency == CurrencyType.TOMAN
        assert eur == 10000
    
    def test_explicit_euro(self):
        eur, currency, _ = smart_currency_convert(5000, 70000, "5000 یورو")
        assert currency == CurrencyType.EURO
        assert eur == 5000
    
    def test_explicit_toman(self):
        eur, currency, _ = smart_currency_convert(70_000_000, 70000, "۷۰ میلیون تومان")
        assert currency == CurrencyType.TOMAN
        assert eur == 1000
    
    def test_abroad_context(self):
        eur, currency, _ = smart_currency_convert(1000, 70000, "1000", context="abroad")
        assert currency == CurrencyType.EURO
        assert eur == 1000


class TestCalculateFamilyScale:
    """تست‌های ضریب خانواده"""
    
    def test_one_member(self):
        assert calculate_family_scale(1) == 1.0
    
    def test_four_members(self):
        assert calculate_family_scale(4) == 2.46
    
    def test_five_members(self):
        assert calculate_family_scale(5) == 2.85
    
    def test_six_members(self):
        # 2.85 + 0.35 = 3.20
        assert calculate_family_scale(6) == 3.20
    
    def test_seven_members(self):
        # 2.85 + 0.70 = 3.55
        assert calculate_family_scale(7) == 3.55


class TestDeductions:
    """تست‌های کسورات و معافیت‌ها"""
    
    def test_rent_deduction_below_max(self):
        assert calculate_rent_deduction(5000, True) == 5000
    
    def test_rent_deduction_above_max(self):
        assert calculate_rent_deduction(10000, True) == 7000
    
    def test_rent_deduction_not_tenant(self):
        assert calculate_rent_deduction(5000, False) == 0
    
    def test_primary_home_exemption(self):
        assert calculate_primary_home_exemption(100000, True, 0) == 52500
    
    def test_primary_home_exemption_with_children(self):
        # 52500 + (2 * 2500) = 57500
        assert calculate_primary_home_exemption(100000, True, 2) == 57500
    
    def test_primary_home_exemption_small_property(self):
        assert calculate_primary_home_exemption(30000, True, 0) == 30000
    
    def test_financial_exemption(self):
        # 6000 + (4 * 500) = 8000
        exemption = calculate_financial_exemption(4)
        assert exemption == 8000


class TestCalculateISEE:
    """تست‌های محاسبه ISEE"""
    
    def test_basic_calculation(self):
        inputs = ISEEInput(
            income=15000,
            members=4,
            property_value=0,
            financial_assets=0,
        )
        result = calculate_isee(inputs)
        
        # ISEE = 15000 / 2.46 ≈ 6097
        assert result.isee < 10000
        assert result.status == "full"
    
    def test_with_property(self):
        inputs = ISEEInput(
            income=20000,
            members=4,
            property_value=100000,
            is_primary_home=True,
            financial_assets=10000,
        )
        result = calculate_isee(inputs)
        
        # با معافیت‌ها باید پایین باشد
        assert result.isee < 20000
        assert result.home_exemption == 52500
    
    def test_with_rent_deduction(self):
        inputs = ISEEInput(
            income=25000,
            members=3,
            is_tenant=True,
            annual_rent=6000,
        )
        result = calculate_isee(inputs)
        
        assert result.rent_deduction == 6000
        assert result.adjusted_income == 19000
    
    def test_high_income(self):
        inputs = ISEEInput(
            income=80000,
            members=2,
            property_value=200000,
            financial_assets=50000,
        )
        result = calculate_isee(inputs)
        
        assert result.isee > 50000
        assert result.status == "none"


class TestReverseCalculator:
    """تست‌های محاسبه معکوس"""
    
    def test_already_achieved(self):
        inputs = ISEEInput(income=10000, members=4)
        result = calculate_reverse_isee(25000, inputs)
        
        assert result["already_achieved"] == True
    
    def test_needs_reduction(self):
        inputs = ISEEInput(income=50000, members=4)
        result = calculate_reverse_isee(25000, inputs)
        
        assert result["already_achieved"] == False
        assert len(result["strategies"]) > 0


class TestNormalizePersianText:
    """تست‌های نرمال‌سازی متن"""
    
    def test_persian_to_english(self):
        assert normalize_persian_text("۱۲۳") == "123"
    
    def test_arabic_to_english(self):
        assert normalize_persian_text("٤٥٦") == "456"
    
    def test_remove_commas(self):
        assert normalize_persian_text("1,000,000") == "1000000"
        assert normalize_persian_text("۱،۰۰۰") == "1000"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''


# ═══════════════════════════════════════════════════════════════════
# بخش ۸.۷: مستندات API
# ═══════════════════════════════════════════════════════════════════

API_DOCUMENTATION = """
# ISEE Calculator Handler - API Documentation

## Overview
This module provides a comprehensive ISEE (Indicatore della Situazione Economica Equivalente) 
calculator for Italian university scholarships.

## Main Functions

### `calculate_isee(inputs: ISEEInput, thresholds: ISEEThresholds = None) -> ISEEResult`
Calculates the ISEE value based on family income and assets.

**Parameters:**
- `inputs`: ISEEInput object containing all financial data
- `thresholds`: Optional regional thresholds for status determination

**Returns:**
- ISEEResult object with calculated values and status

### `calculate_reverse_isee(target: float, inputs: ISEEInput) -> dict`
Calculates strategies to achieve a target ISEE value.

**Parameters:**
- `target`: Target ISEE value in EUR
- `inputs`: Current financial situation

**Returns:**
- Dictionary with strategies and required changes

### `smart_currency_convert(amount, eur_rate, text, context) -> Tuple`
Intelligently converts amounts between EUR and Toman.

## Data Classes

### ISEEInput
Contains all input parameters:
- income: Annual family income (EUR)
- members: Number of family members
- property_value: Total real estate value (EUR)
- financial_assets: Bank accounts, stocks, etc. (EUR)
- total_debts: Outstanding debts (EUR)
- abroad_assets: Assets outside Iran (EUR)
- is_tenant: Whether family rents their home
- annual_rent: Annual rent if tenant (EUR)
- is_primary_home: Whether property is primary residence
- is_independent_student: Student independence status

### ISEEResult
Contains calculation results:
- isee: Final ISEE value
- ise: ISE indicator
- isp: ISP (patrimony) indicator
- scale: Family scale coefficient
- status: full/partial/reduced/none
- All deduction amounts

## Callback Data Reference

| Callback | Description |
|----------|-------------|
| `isee` | Main ISEE menu |
| `isee_mode_full` | Start full calculation |
| `isee_mode_quick` | Start quick calculation |
| `isee_history` | View calculation history |
| `isee_tips` | Show reduction tips |
| `isee_reverse_intro` | Reverse calculator |
| `isee_whatif_start` | What-If scenarios |
| `isee_settings` | User settings |

## State Machine

States follow this flow:
1. intro → select_mode → select_region
2. waiting_income → waiting_rent (if tenant)
3. waiting_members → waiting_children
4. waiting_property → waiting_primary_home
5. waiting_financial → waiting_debts
6. waiting_abroad → waiting_independent
7. confirm_data → (edit_field loop or calculate)

## Configuration

All thresholds and limits are configurable in:
- `REGIONAL_THRESHOLDS`: Regional DSU thresholds
- `DEDUCTION_LIMITS`: Maximum deductions
- `FAMILY_SCALE_COEFFICIENTS`: Family scale factors
"""


# ═══════════════════════════════════════════════════════════════════
# بخش ۸.۸: ثبت نهایی روتر و Exports
# ═══════════════════════════════════════════════════════════════════

# لیست تمام توابع و کلاس‌های قابل export
__all__ = [
    # Router
    "router",
    
    # Data Classes
    "ISEEInput",
    "ISEEResult",
    "ISEEThresholds",
    "ISEEDataStore",
    
    # Enums
    "Region",
    "CurrencyType",
    
    # States
    "ISEEState",
    
    # Core Functions
    "calculate_isee",
    "calculate_reverse_isee",
    "calculate_family_scale",
    "calculate_rent_deduction",
    "calculate_primary_home_exemption",
    "calculate_financial_exemption",
    "calculate_debt_deduction",
    
    # Utility Functions
    "parse_persian_amount",
    "normalize_persian_text",
    "smart_currency_convert",
    "get_eur_rate",
    
    # Helper Functions
    "get_user_isee_summary",
    "check_scholarship_eligibility",
    "export_user_data",
    "import_user_data",
    
    # Constants
    "REGIONAL_THRESHOLDS",
    "DEFAULT_THRESHOLDS",
    "DEDUCTION_LIMITS",
    "FAMILY_SCALE_COEFFICIENTS",
    "IRANIAN_STATS",
    "STATUS_CONFIG",
    
    # Data Store Instance
    "data_store",
]


# ═══════════════════════════════════════════════════════════════════
# بخش ۸.۹: نحوه استفاده و یکپارچه‌سازی
# ═══════════════════════════════════════════════════════════════════

"""
## نحوه یکپارچه‌سازی با bot.py

```python
# bot.py

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from handlers import isee_handler

# ایجاد bot و dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ثبت روتر ISEE
dp.include_router(isee_handler.router)

# اجرای bot
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
"""