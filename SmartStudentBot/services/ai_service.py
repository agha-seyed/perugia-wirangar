# services/ai_service.py
# سرویس هوش مصنوعی چندمدله با OpenRouter.ai
# نسخه ۲.۰ - اصلاح شده و توسعه یافته
# ژانویه ۲۰۲۵

"""
═══════════════════════════════════════════════════════════════════════════════
                    سرویس هوش مصنوعی SmartStudentBot
═══════════════════════════════════════════════════════════════════════════════

این سرویس از OpenRouter.ai استفاده می‌کند که دسترسی به مدل‌های زیر را فراهم می‌کند:
    • OpenAI: GPT-4o, GPT-4o-mini, GPT-4-Turbo, GPT-3.5-Turbo
    • Anthropic: Claude 3.5 Sonnet, Claude 3 Haiku, Claude 3 Opus
    • Google: Gemini Pro 1.5, Gemini Flash 1.5
    • Meta: Llama 3.1 70B, Llama 3.1 8B
    • xAI: Grok
    • Mistral: Mistral Large, Mistral 7B
    • و ده‌ها مدل دیگر

ویژگی‌های کلیدی نسخه ۲.۰:
    ✅ پشتیبانی از انتخاب مدل توسط کاربر
    ✅ پشتیبانی از تاریخچه مکالمه
    ✅ تبدیل صدا به متن با OpenRouter (بدون نیاز به OpenAI API)
    ✅ تحلیل تصویر با Vision API
    ✅ سیستم Fallback چندلایه
    ✅ کش هوشمند
    ✅ اطلاع‌رسانی به ادمین در صورت بروز مشکل

═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import httpx
import asyncio
import random
import hashlib
import json
import time
import base64
from typing import Optional, Dict, List, Tuple, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

# ایمپورت از پروژه
from config import settings, logger


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱: تنظیمات و ثابت‌ها
# ═══════════════════════════════════════════════════════════════════════════════

# آدرس‌های API
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

# تنظیمات از config
CACHE_TTL_HOURS: int = settings.AI_CACHE_TTL_HOURS
MAX_CACHE_SIZE: int = 1000
MIN_MESSAGE_LENGTH_FOR_CACHE: int = 10

MAX_RETRIES_PER_MODEL: int = settings.AI_MAX_RETRIES
RETRY_DELAY_SECONDS: float = 1.0
REQUEST_TIMEOUT_SECONDS: float = settings.AI_TIMEOUT_SECONDS
CONNECTION_TIMEOUT_SECONDS: float = 10.0

# حداکثر تعداد پیام در تاریخچه
MAX_HISTORY_MESSAGES: int = settings.AI_HISTORY_MAX_MESSAGES


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲: توابع کمکی
# ═══════════════════════════════════════════════════════════════════════════════

def get_openrouter_headers(api_key: str) -> Dict[str, str]:
    """ساخت هدرهای مورد نیاز برای OpenRouter"""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/SmartStudentBot",
        "X-Title": "SmartStudentBot Perugia",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۳: تعریف مدل‌ها
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AIModel:
    """
    کلاس نگهداری اطلاعات هر مدل AI
    
    Attributes:
        model_id: شناسه مدل در OpenRouter (مثلاً "openai/gpt-4o")
        display_name: نام نمایشی برای کاربر
        provider: شرکت سازنده (OpenAI, Anthropic, ...)
        priority: اولویت (عدد کمتر = اولویت بالاتر)
        max_tokens: حداکثر توکن خروجی
        supports_vision: آیا از تحلیل تصویر پشتیبانی می‌کند؟
        supports_audio: آیا از تبدیل صدا پشتیبانی می‌کند؟
        cost_per_million: هزینه تقریبی (دلار به ازای هر میلیون توکن)
        is_active: آیا فعال است؟
    """
    
    model_id: str
    display_name: str
    provider: str
    priority: int
    max_tokens: int = 4096
    supports_vision: bool = False
    supports_audio: bool = False
    supports_chat: bool = True
    supports_translation: bool = True
    cost_per_million: float = 0.0
    is_active: bool = True
    
    @property
    def short_name(self) -> str:
        """نام کوتاه مدل (بدون provider)"""
        return self.model_id.split("/")[-1] if "/" in self.model_id else self.model_id


# لیست کامل مدل‌های پشتیبانی شده
AVAILABLE_MODELS: Dict[str, AIModel] = {
    
    # ═══════════════════════════════════════════════════════
    # OpenAI Models (اولویت ۱-۴)
    # ═══════════════════════════════════════════════════════
    
    "gpt-4o": AIModel(
        model_id="openai/gpt-4o",
        display_name="GPT-4o",
        provider="OpenAI",
        priority=1,
        max_tokens=4096,
        supports_vision=True,
        supports_audio=True,
        cost_per_million=5.0,
    ),
    
    "gpt-4o-mini": AIModel(
        model_id="openai/gpt-4o-mini",
        display_name="GPT-4o Mini",
        provider="OpenAI",
        priority=2,
        max_tokens=4096,
        supports_vision=True,
        cost_per_million=0.15,
    ),
    
    "gpt-4-turbo": AIModel(
        model_id="openai/gpt-4-turbo",
        display_name="GPT-4 Turbo",
        provider="OpenAI",
        priority=3,
        max_tokens=4096,
        supports_vision=True,
        cost_per_million=10.0,
    ),
    
    "gpt-3.5-turbo": AIModel(
        model_id="openai/gpt-3.5-turbo",
        display_name="GPT-3.5 Turbo",
        provider="OpenAI",
        priority=4,
        max_tokens=4096,
        cost_per_million=0.5,
    ),
    
    # ═══════════════════════════════════════════════════════
    # Anthropic Claude Models (اولویت ۵-۷)
    # ═══════════════════════════════════════════════════════
    
    "claude-3.5-sonnet": AIModel(
        model_id="anthropic/claude-3.5-sonnet",
        display_name="Claude 3.5 Sonnet",
        provider="Anthropic",
        priority=5,
        max_tokens=4096,
        supports_vision=True,
        cost_per_million=3.0,
    ),
    
    "claude-3-haiku": AIModel(
        model_id="anthropic/claude-3-haiku",
        display_name="Claude 3 Haiku",
        provider="Anthropic",
        priority=6,
        max_tokens=4096,
        supports_vision=True,
        cost_per_million=0.25,
    ),
    
    "claude-3-opus": AIModel(
        model_id="anthropic/claude-3-opus",
        display_name="Claude 3 Opus",
        provider="Anthropic",
        priority=7,
        max_tokens=4096,
        supports_vision=True,
        cost_per_million=15.0,
    ),
    
    # ═══════════════════════════════════════════════════════
    # Google Gemini Models (اولویت ۸-۹)
    # ═══════════════════════════════════════════════════════
    
    "gemini-pro": AIModel(
        model_id="google/gemini-pro-1.5",
        display_name="Gemini Pro 1.5",
        provider="Google",
        priority=8,
        max_tokens=4096,
        supports_vision=True,
        supports_audio=True,
        cost_per_million=1.25,
    ),
    
    "gemini-flash": AIModel(
        model_id="google/gemini-flash-1.5",
        display_name="Gemini Flash 1.5",
        provider="Google",
        priority=9,
        max_tokens=4096,
        supports_vision=True,
        supports_audio=True,
        cost_per_million=0.075,
    ),
    
    # ═══════════════════════════════════════════════════════
    # xAI Grok (اولویت ۱۰)
    # ═══════════════════════════════════════════════════════
    
    "grok": AIModel(
        model_id="x-ai/grok-beta",
        display_name="Grok",
        provider="xAI",
        priority=10,
        max_tokens=4096,
        cost_per_million=5.0,
    ),
    
    # ═══════════════════════════════════════════════════════
    # Meta Llama (اولویت ۱۱-۱۲)
    # ═══════════════════════════════════════════════════════
    
    "llama-3.1-70b": AIModel(
        model_id="meta-llama/llama-3.1-70b-instruct",
        display_name="Llama 3.1 70B",
        provider="Meta",
        priority=11,
        max_tokens=4096,
        cost_per_million=0.9,
    ),
    
    "llama-3.1-8b": AIModel(
        model_id="meta-llama/llama-3.1-8b-instruct",
        display_name="Llama 3.1 8B",
        provider="Meta",
        priority=12,
        max_tokens=4096,
        cost_per_million=0.06,
    ),
    
    # ═══════════════════════════════════════════════════════
    # Mistral (اولویت ۱۳-۱۴)
    # ═══════════════════════════════════════════════════════
    
    "mistral-large": AIModel(
        model_id="mistralai/mistral-large",
        display_name="Mistral Large",
        provider="Mistral",
        priority=13,
        max_tokens=4096,
        cost_per_million=3.0,
    ),
    
    "mistral-7b": AIModel(
        model_id="mistralai/mistral-7b-instruct",
        display_name="Mistral 7B",
        provider="Mistral",
        priority=14,
        max_tokens=4096,
        cost_per_million=0.07,
    ),
    
    # ═══════════════════════════════════════════════════════
    # مدل‌های رایگان/ارزان برای Fallback (اولویت ۱۵+)
    # ═══════════════════════════════════════════════════════
    
    "phi-3-mini": AIModel(
        model_id="microsoft/phi-3-mini-128k-instruct",
        display_name="Phi-3 Mini",
        provider="Microsoft",
        priority=15,
        max_tokens=4096,
        cost_per_million=0.1,
    ),
    
    "gemma-2-9b": AIModel(
        model_id="google/gemma-2-9b-it",
        display_name="Gemma 2 9B",
        provider="Google",
        priority=16,
        max_tokens=4096,
        cost_per_million=0.08,
    ),
    
    # ═══════════════════════════════════════════════════════
    # مدل‌های تخصصی Audio (برای تبدیل صدا به متن)
    # ═══════════════════════════════════════════════════════
    
    "whisper-large": AIModel(
        model_id="openai/whisper-large-v3",
        display_name="Whisper Large v3",
        provider="OpenAI",
        priority=100,
        max_tokens=4096,
        supports_audio=True,
        supports_chat=False,
        cost_per_million=0.0,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۴: ترتیب مدل‌ها برای هر نوع کار
# ═══════════════════════════════════════════════════════════════════════════════

# مدل‌های پیش‌فرض برای چت (ارزان و سریع اول)
CHAT_MODEL_PRIORITY: List[str] = [
    "gpt-4o-mini",
    "gemini-flash",
    "claude-3-haiku",
    "gpt-3.5-turbo",
    "llama-3.1-8b",
    "mistral-7b",
    "phi-3-mini",
]

# مدل‌های Vision (برای تحلیل تصویر)
VISION_MODEL_PRIORITY: List[str] = [
    "gpt-4o-mini",
    "gemini-flash",
    "gpt-4o",
    "claude-3.5-sonnet",
    "claude-3-haiku",
    "gemini-pro",
]

# مدل‌های Audio (برای تبدیل صدا)
AUDIO_MODEL_PRIORITY: List[str] = [
    "gemini-flash",
    "gemini-pro",
    "gpt-4o",
]

# مدل‌های ترجمه (دقت بالا)
TRANSLATION_MODEL_PRIORITY: List[str] = [
    "gpt-4o",
    "claude-3.5-sonnet",
    "gpt-4o-mini",
    "gemini-pro",
    "gpt-3.5-turbo",
]

# مدل‌های خلاصه‌سازی
SUMMARIZATION_MODEL_PRIORITY: List[str] = [
    "claude-3.5-sonnet",
    "gpt-4o-mini",
    "gemini-flash",
    "gpt-3.5-turbo",
]


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۵: انواع داده و ساختارها
# ═══════════════════════════════════════════════════════════════════════════════

class AIStatus(Enum):
    """وضعیت کلی سرویس AI"""
    ONLINE = "online"
    DEGRADED = "degraded"
    LIMITED = "limited"
    OFFLINE = "offline"


class TaskType(Enum):
    """نوع کار درخواستی"""
    CHAT = "chat"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    ITALIAN_HELP = "italian_help"
    SUPPORT = "support"
    VISION = "vision"
    AUDIO = "audio"


@dataclass
class APIUsageStats:
    """آمار استفاده از API"""
    
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    fallback_used: int = 0
    
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    last_error_model: Optional[str] = None
    
    total_tokens_used: int = 0
    requests_per_model: Dict[str, int] = field(default_factory=dict)
    last_successful_request: Optional[datetime] = None
    
    # آمار جدید
    voice_requests: int = 0
    image_requests: int = 0
    history_used_count: int = 0


@dataclass
class CacheEntry:
    """یک ورودی در کش"""
    
    response: str
    timestamp: datetime
    source: str
    model_used: Optional[str] = None
    hit_count: int = 0


@dataclass
class AIResponse:
    """
    ساختار پاسخ نهایی AI
    
    این کلاس توسط تمام متدهای سرویس برگردانده می‌شود.
    """
    
    text: str
    is_ai_generated: bool
    model_used: Optional[str] = None
    provider: Optional[str] = None
    from_cache: bool = False
    is_fallback: bool = False
    processing_time_ms: int = 0
    error: Optional[str] = None
    
    # فیلدهای جدید
    model_key: Optional[str] = None  # کلید مدل (مثلاً "gpt-4o-mini")
    tokens_used: int = 0
    was_model_fallback: bool = False  # آیا به مدل دیگری Fallback شد؟
    original_model: Optional[str] = None  # مدل اصلی درخواست شده


@dataclass 
class ChatMessage:
    """یک پیام در تاریخچه چت"""
    role: str  # "user" یا "assistant" یا "system"
    content: str
    timestamp: Optional[datetime] = None
    model_used: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۶: پرامپت‌های سیستم
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPTS: Dict[str, str] = {
    
    "student_assistant": """تو یک دستیار هوشمند و دوستانه برای دانشجویان ایرانی در شهر پروجای ایتالیا هستی.

نام تو «دستیار پروجا» است.

وظایف تو:
- پاسخ به سوالات درباره تحصیل در ایتالیا
- راهنمایی درباره ویزا، پرمسو، و مسائل اداری
- کمک در مورد هزینه‌ها، بورسیه، و ISEE
- راهنمایی درباره زندگی در پروجا و ایتالیا
- کمک در یادگیری زبان ایتالیایی

قوانین پاسخ‌دهی:
1. همیشه به زبان فارسی پاسخ بده (مگر درخواست صریح به زبان دیگر باشد)
2. مختصر، دقیق و کاربردی باش
3. اگر مطمئن نیستی، صادقانه بگو که نمی‌دانی
4. از ایموجی مناسب استفاده کن
5. اطلاعات قدیمی نده - اگر چیزی ممکنه تغییر کرده باشه، به کاربر بگو چک کنه
6. لحن دوستانه و صمیمی داشته باش
7. اگر تاریخچه مکالمه ارسال شده، از آن برای درک بهتر سوال استفاده کن""",

    "student_assistant_with_history": """تو یک دستیار هوشمند و دوستانه برای دانشجویان ایرانی در شهر پروجای ایتالیا هستی.

نام تو «دستیار پروجا» است.

⚠️ مهم: تاریخچه مکالمه قبلی در ادامه آمده. از آن برای درک بهتر context و ادامه مکالمه استفاده کن.

وظایف تو:
- پاسخ به سوالات درباره تحصیل در ایتالیا
- راهنمایی درباره ویزا، پرمسو، و مسائل اداری
- کمک در مورد هزینه‌ها، بورسیه، و ISEE
- راهنمایی درباره زندگی در پروجا و ایتالیا
- کمک در یادگیری زبان ایتالیایی

قوانین پاسخ‌دهی:
1. همیشه به زبان فارسی پاسخ بده
2. به تاریخچه مکالمه توجه کن و پاسخ مرتبط بده
3. اگر کاربر به موضوع قبلی اشاره کرد، آن را درک کن
4. مختصر و کاربردی باش
5. لحن دوستانه داشته باش""",

    "translator": """تو یک مترجم حرفه‌ای هستی که بین زبان‌های ایتالیایی، انگلیسی و فارسی ترجمه می‌کنی.

قوانین ترجمه:
1. ترجمه باید طبیعی و روان باشد، نه کلمه به کلمه
2. اصطلاحات تخصصی را توضیح بده
3. اگر کلمه‌ای معادل دقیق ندارد، توضیح بده
4. تلفظ کلمات ایتالیایی را با فینگلیش بنویس
5. برای اصطلاحات اداری ایتالیا، معادل فارسی و توضیح بده""",

    "italian_teacher": """تو یک معلم زبان ایتالیایی هستی که به فارسی تدریس می‌کنی.

روش تدریس:
1. توضیحات ساده و قابل فهم بده
2. مثال‌های کاربردی و روزمره بزن
3. تلفظ را با فینگلیش بنویس (مثلاً: Buongiorno = بوئون‌جورنو)
4. نکات گرامری مهم را توضیح بده
5. اشتباهات رایج ایرانی‌ها را گوشزد کن
6. جملات مفید برای زندگی در ایتالیا یاد بده""",

    "support_agent": """تو یک پشتیبان حرفه‌ای و صبور هستی.

وظایف:
1. به سوالات کاربران با دقت پاسخ بده
2. اگر نمی‌توانی کمک کنی، صادقانه بگو و به ادمین ارجاع بده
3. همیشه مودب و صبور باش
4. سعی کن مشکل را درک کنی قبل از پاسخ دادن

در پایان پاسخ، اگر فکر می‌کنی کاربر نیاز به کمک بیشتر دارد، بگو که می‌تواند تیکت بزند.""",

    "summarizer": """تو یک متخصص خلاصه‌سازی هستی.

قوانین خلاصه‌سازی:
1. نکات کلیدی را استخراج کن
2. خلاصه باید حداکثر ۳۰٪ متن اصلی باشد
3. ترتیب منطقی را حفظ کن
4. جزئیات غیرضروری را حذف کن
5. به زبان فارسی خلاصه کن""",

    "vision_analyzer": """تو یک تحلیلگر تصویر هستی.

وظایف:
1. تصویر ارسال شده را دقیق توصیف کن
2. اگر متنی در تصویر هست، آن را بخوان
3. اگر سوالی درباره تصویر پرسیده شده، پاسخ بده
4. به زبان فارسی پاسخ بده
5. اگر تصویر مدرک یا فرم اداری است، محتوای مهم را استخراج کن""",

    "audio_transcriber": """تو یک متخصص تبدیل گفتار به متن هستی.

وظایف:
1. صدای ارسال شده را به متن تبدیل کن
2. علائم نگارشی مناسب بگذار
3. اگر صدا واضح نبود، بگو
4. زبان صحبت را تشخیص بده""",
}


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۷: مسیرها و فایل‌ها
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
STATS_FILE = DATA_DIR / "ai_stats.json"
CACHE_FILE = DATA_DIR / "ai_cache.json"


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۸: توصیه‌های آب‌وهوا
# ═══════════════════════════════════════════════════════════════════════════════

WEATHER_ADVICE: Dict[str, str] = {
    "hot": "☀️ <b>هوا گرمه!</b> آب زیاد بخور، کرم ضدآفتاب بزن و کلاه یادت نره.",
    "warm": "🌤 <b>هوا گرم و دلپذیره!</b> روز خوبی برای گشت‌وگذار در پروجاست.",
    "mild": "🌡 <b>هوا معتدله!</b> یه ژاکت سبک همراه داشته باش.",
    "cool": "🍂 <b>هوا خنکه!</b> کاپشن سبک یا سویشرت ببر.",
    "cold": "❄️ <b>هوا سرده!</b> لباس گرم، کلاه و شال‌گردن یادت نره.",
    "freezing": "🥶 <b>یخبندانه!</b> لباس‌های خیلی گرم بپوش. دستکش هم ببر.",
    "rainy": "🌧 <b>بارونیه!</b> چتر ببر و کفش ضدآب بپوش.",
    "stormy": "⛈ <b>طوفانیه!</b> تا می‌تونی بیرون نرو.",
    "snowy": "🌨 <b>برفیه!</b> لباس گرم و کفش مناسب برف بپوش.",
    "windy": "💨 <b>باد شدیده!</b> کاپشن بادگیر ببر.",
    "foggy": "🌫 <b>مه‌آلوده!</b> موقع رانندگی احتیاط کن.",
    "cloudy": "☁️ <b>ابریه!</b> احتمال باران هست، چتر همراه داشته باش.",
    "nice": "🌈 <b>هوا عالیه!</b> برو بیرون و از پروجای زیبا لذت ببر!",
}


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۹: پاسخ‌های آماده (Fallback)
# ═══════════════════════════════════════════════════════════════════════════════

FALLBACK_RESPONSES: Dict[str, List[str]] = {

    "سلام": [
        "سلام! 👋 من دستیار هوشمند پروجا هستم. چطور می‌تونم کمکت کنم؟",
        "درود بر شما! 🎓 خوشحالم که پیام دادید. سوالتون رو بپرسید!",
        "سلام دوست عزیز! 🌟 آماده‌ام کمکت کنم. چه سوالی داری؟",
    ],

    "خوبی": [
        "ممنون از لطفت! 😊 من یه ربات هستم ولی خوشحالم که حالمو پرسیدی. تو چطوری؟",
        "عالیم! 🎉 ممنون که پرسیدی. کاری هست که بتونم برات انجام بدم؟",
    ],

    "ممنون": [
        "خواهش می‌کنم! 🙏 خوشحالم که تونستم کمک کنم.",
        "قابلی نداشت! 😊 اگر سوال دیگه‌ای داشتی، بپرس.",
    ],

    "خداحافظ": [
        "خداحافظ! 👋 موفق باشی. هر وقت سوالی داشتی برگرد!",
        "به امید دیدار! 🌟 موفقیت در تحصیلت آرزوی منه.",
    ],

    "ویزا": [
        "📋 <b>ویزای تحصیلی ایتالیا - راهنمای کامل</b>\n\n"
        "🔹 <b>مدارک اصلی مورد نیاز:</b>\n"
        "• پذیرش دانشگاه (Lettera di ammissione)\n"
        "• مدرک زبان (انگلیسی B2 یا ایتالیایی B1)\n"
        "• تمکن مالی (~۶۵۰۰ یورو در حساب)\n"
        "• بیمه درمانی معتبر\n"
        "• گذرنامه با حداقل ۱۸ ماه اعتبار\n\n"
        "💡 برای جزئیات کامل از بخش «راهنما» استفاده کن.",
    ],

    "پرمسو": [
        "🛂 <b>پرمسو دی سوجورنو (Permesso di Soggiorno)</b>\n\n"
        "اجازه اقامت در ایتالیا که بدون آن نمی‌توانید قانونی بمانید!\n\n"
        "⚠️ <b>مهم:</b> ظرف ۸ روز پس از ورود باید اقدام کنی!\n\n"
        "📖 جزئیات کامل در بخش «راهنما» موجوده.",
    ],

    "هزینه": [
        "💰 <b>هزینه‌های ماهانه زندگی در پروجا (۲۰۲۵)</b>\n\n"
        "🏠 <b>اجاره:</b> ۲۸۰-۴۵۰€\n"
        "🍽 <b>غذا:</b> ۱۵۰-۲۰۰€\n"
        "🚌 <b>حمل‌ونقل:</b> ۲۵-۳۵€\n"
        "📱 <b>موبایل:</b> ۱۰-۱۵€\n\n"
        "📊 <b>جمع کل:</b> ۶۵۰-۹۰۰€ ماهانه",
    ],

    "بورسیه": [
        "🏆 <b>بورسیه DSU (ADISU Umbria)</b>\n\n"
        "✅ <b>شرایط:</b> ISEE زیر ۲۷,۰۰۰€ + کسب ۴۰ واحد\n\n"
        "🎁 <b>مزایا:</b>\n"
        "• کمک هزینه: ~۵۰۰۰-۷۰۰۰€/سال\n"
        "• خوابگاه رایگان\n"
        "• کارت غذا رایگان\n\n"
        "🌐 سایت: adisumbria.it",
    ],

    "default": [
        "🤔 سوال جالبیه!\n\n"
        "متأسفانه الان پاسخ دقیقی ندارم.\n\n"
        "💡 <b>پیشنهاد:</b>\n"
        "• از منوی اصلی گزینه مورد نظر رو انتخاب کن\n"
        "• یا از بخش «پشتیبانی» تیکت بزن",
        
        "🔍 برای پاسخ دقیق‌تر، پیشنهاد می‌کنم:\n"
        "• 📖 بخش راهنما رو ببین\n"
        "• 💬 یه تیکت پشتیبانی بزن",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۰: دیکشنری ایتالیایی-فارسی (خلاصه شده - اصلی در فایل جداگانه)
# ═══════════════════════════════════════════════════════════════════════════════

ITALIAN_PERSIAN_DICTIONARY: Dict[str, str] = {
    # اصطلاحات اداری
    "permesso di soggiorno": "اجازه اقامت (پرمسو)",
    "codice fiscale": "کد مالیاتی (مثل کد ملی)",
    "questura": "اداره پلیس/مهاجرت",
    "comune": "شهرداری",
    "università": "دانشگاه",
    "borsa di studio": "بورسیه تحصیلی",
    "affitto": "اجاره",
    "contratto": "قرارداد",
    
    # عبارات روزمره
    "buongiorno": "صبح بخیر / روز بخیر",
    "buonasera": "عصر بخیر",
    "grazie": "ممنون",
    "prego": "خواهش می‌کنم",
    "scusi": "ببخشید",
    "per favore": "لطفاً",
    "quanto costa?": "قیمتش چنده؟",
    "dov'è?": "کجاست؟",
}


# ═══════════════════════════════════════════════════════════════════════════════
# پایان بخش ۱ از ۲
# ادامه در بخش ۲...
# ═══════════════════════════════════════════════════════════════════════════════

logger.info("📦 AI Service v2.0 - Part 1/2 loaded (Config, Models, Constants)")
# ═══════════════════════════════════════════════════════════════════════════════
# services/ai_service.py - بخش ۲ از ۲
# کلاس اصلی AIService و متدها
# ═══════════════════════════════════════════════════════════════════════════════


class AIService:
    """
    سرویس هوش مصنوعی چندمدله با پشتیبانی از OpenRouter.ai
    
    نسخه ۲.۰ با قابلیت‌های جدید:
        ✅ انتخاب مدل توسط کاربر
        ✅ پشتیبانی از تاریخچه مکالمه
        ✅ تبدیل صدا به متن (بدون OpenAI API)
        ✅ تحلیل تصویر با Vision
        ✅ Fallback هوشمند با اطلاع‌رسانی
    
    نحوه استفاده:
        from services.ai_service import ai_service
        
        # چت ساده
        response = await ai_service.chat("سلام")
        
        # چت با مدل خاص
        response = await ai_service.chat("سلام", model="claude-3.5-sonnet")
        
        # چت با تاریخچه
        history = [
            {"role": "user", "content": "سلام"},
            {"role": "assistant", "content": "سلام! چطور می‌تونم کمکت کنم؟"}
        ]
        response = await ai_service.chat("هزینه زندگی چقدره؟", history=history)
        
        # تبدیل صدا به متن
        text = await ai_service.transcribe_audio(audio_bytes)
        
        # تحلیل تصویر
        response = await ai_service.analyze_image(image_bytes, "این تصویر چیه؟")
    """
    
    def __init__(self):
        """مقداردهی اولیه سرویس"""
        
        # ═══════════════════════════════════════════════════════════════════════
        # خواندن API Key
        # ═══════════════════════════════════════════════════════════════════════
        
        self.api_key: Optional[str] = getattr(settings, 'OPENROUTER_API_KEY', None)
        
        # Fallback به HuggingFace (سازگاری با نسخه قبل)
        if not self.api_key:
            self.api_key = getattr(settings, 'HUGGINGFACE_API_KEY', None)
        
        # ═══════════════════════════════════════════════════════════════════════
        # تنظیم وضعیت
        # ═══════════════════════════════════════════════════════════════════════
        
        if self.api_key and len(self.api_key) > 10:
            self.status = AIStatus.ONLINE
            logger.success("🤖 AI Service initialized with API Key")
        else:
            self.status = AIStatus.OFFLINE
            logger.warning("⚠️ AI Service initialized WITHOUT API Key - Fallback mode only")
        
        # ═══════════════════════════════════════════════════════════════════════
        # ساخت هدرها
        # ═══════════════════════════════════════════════════════════════════════
        
        self.headers: Dict[str, str] = get_openrouter_headers(self.api_key) if self.api_key else {}
        
        # ═══════════════════════════════════════════════════════════════════════
        # آمار مصرف
        # ═══════════════════════════════════════════════════════════════════════
        
        self.usage_stats = APIUsageStats()
        self._load_stats()
        
        # ═══════════════════════════════════════════════════════════════════════
        # کش
        # ═══════════════════════════════════════════════════════════════════════
        
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_ttl = timedelta(hours=CACHE_TTL_HOURS)
        
        # ═══════════════════════════════════════════════════════════════════════
        # وضعیت مدل‌ها
        # ═══════════════════════════════════════════════════════════════════════
        
        # مدل‌هایی که موقتاً غیرفعال شده‌اند
        self._disabled_models: Dict[str, datetime] = {}
        self._model_cooldown_minutes: int = 5
        
        # ═══════════════════════════════════════════════════════════════════════
        # Reference به bot
        # ═══════════════════════════════════════════════════════════════════════
        
        self._bot = None
        
        # ═══════════════════════════════════════════════════════════════════════
        # مدل پیش‌فرض از تنظیمات
        # ═══════════════════════════════════════════════════════════════════════
        
        self.default_model: str = settings.AI_DEFAULT_MODEL
        
        logger.info(f"📊 AI Service Status: {self.status.value}")
        logger.info(f"📊 Default Model: {self.default_model}")
        logger.info(f"📊 Available Models: {len(AVAILABLE_MODELS)}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # متدهای مدیریت وضعیت
    # ═══════════════════════════════════════════════════════════════════════════
    
    def set_bot(self, bot) -> None:
        """تنظیم reference به bot برای ارسال پیام به ادمین"""
        self._bot = bot
        logger.debug("🤖 Bot reference set for AI Service")
    
    def is_available(self) -> bool:
        """آیا سرویس AI در دسترس است؟ (حتی در حالت Fallback)"""
        return True
    
    def is_ai_available(self) -> bool:
        """آیا AI واقعی (نه Fallback) در دسترس است؟"""
        return (
            self.status in [AIStatus.ONLINE, AIStatus.DEGRADED] 
            and bool(self.api_key)
        )
    
    def get_status(self) -> Dict[str, Any]:
        """دریافت وضعیت کامل سرویس"""
        total = self.usage_stats.total_requests
        success_rate = (self.usage_stats.successful_requests / total * 100) if total > 0 else 0.0
        
        active_models = len([
            m for m in AVAILABLE_MODELS 
            if m not in self._disabled_models
        ])
        
        return {
            "status": self.status.value,
            "api_key_configured": bool(self.api_key),
            "default_model": self.default_model,
            "total_requests": total,
            "successful_requests": self.usage_stats.successful_requests,
            "failed_requests": self.usage_stats.failed_requests,
            "fallback_used": self.usage_stats.fallback_used,
            "voice_requests": self.usage_stats.voice_requests,
            "image_requests": self.usage_stats.image_requests,
            "history_used_count": self.usage_stats.history_used_count,
            "success_rate": f"{success_rate:.1f}%",
            "total_models": len(AVAILABLE_MODELS),
            "active_models": active_models,
            "disabled_models": list(self._disabled_models.keys()),
            "cache_size": len(self._cache),
            "last_error": self.usage_stats.last_error,
            "last_error_model": self.usage_stats.last_error_model,
            "last_successful": self.usage_stats.last_successful_request.isoformat() 
                if self.usage_stats.last_successful_request else None,
        }
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """لیست مدل‌های موجود با وضعیت آن‌ها"""
        result = []
        now = datetime.now()
        
        for key, model in AVAILABLE_MODELS.items():
            is_disabled = key in self._disabled_models
            disabled_until = None
            
            if is_disabled:
                disabled_until = self._disabled_models[key]
                if now > disabled_until:
                    del self._disabled_models[key]
                    is_disabled = False
            
            result.append({
                "key": key,
                "model_id": model.model_id,
                "name": model.display_name,
                "provider": model.provider,
                "priority": model.priority,
                "supports_vision": model.supports_vision,
                "supports_audio": model.supports_audio,
                "is_active": model.is_active and not is_disabled,
                "disabled_until": disabled_until.isoformat() if disabled_until else None,
                "requests": self.usage_stats.requests_per_model.get(key, 0),
            })
        
        result.sort(key=lambda x: x["priority"])
        return result
    
    def get_model_info(self, model_key: str) -> Optional[AIModel]:
        """دریافت اطلاعات یک مدل خاص"""
        return AVAILABLE_MODELS.get(model_key)
    
    def is_model_available(self, model_key: str) -> bool:
        """آیا مدل خاص در دسترس است؟"""
        if model_key not in AVAILABLE_MODELS:
            return False
        
        if model_key in self._disabled_models:
            if datetime.now() < self._disabled_models[model_key]:
                return False
            del self._disabled_models[model_key]
        
        return AVAILABLE_MODELS[model_key].is_active
    
    # ═══════════════════════════════════════════════════════════════════════════
    # متدهای کش
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _make_cache_key(self, text: str, task_type: str = "chat", model: str = "") -> str:
        """ساخت کلید یکتا برای کش"""
        normalized = text.lower().strip()
        combined = f"{task_type}:{model}:{normalized}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def _get_from_cache(self, key: str) -> Optional[CacheEntry]:
        """دریافت از کش"""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        if datetime.now() - entry.timestamp > self._cache_ttl:
            del self._cache[key]
            return None
        
        entry.hit_count += 1
        logger.debug(f"📦 Cache HIT for key {key[:8]}...")
        return entry
    
    def _save_to_cache(
        self, 
        key: str, 
        response: str, 
        source: str,
        model_used: Optional[str] = None
    ) -> None:
        """ذخیره در کش"""
        if len(self._cache) >= MAX_CACHE_SIZE:
            self._cleanup_cache()
        
        self._cache[key] = CacheEntry(
            response=response,
            timestamp=datetime.now(),
            source=source,
            model_used=model_used,
            hit_count=0,
        )
        logger.debug(f"📦 Cache SAVE for key {key[:8]}...")
    
    def _cleanup_cache(self) -> None:
        """پاکسازی کش"""
        if not self._cache:
            return
        
        now = datetime.now()
        
        expired_keys = [
            key for key, entry in self._cache.items()
            if now - entry.timestamp > self._cache_ttl
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if len(self._cache) >= MAX_CACHE_SIZE:
            sorted_items = sorted(
                self._cache.items(),
                key=lambda x: (x[1].hit_count, x[1].timestamp)
            )
            to_remove = len(sorted_items) // 5
            for key, _ in sorted_items[:to_remove]:
                del self._cache[key]
        
        logger.info(f"🧹 Cache cleanup: {len(expired_keys)} expired, size now: {len(self._cache)}")
    
    def clear_cache(self) -> int:
        """پاکسازی کامل کش"""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"🗑️ Cache cleared: {count} entries removed")
        return count
    
    # ═══════════════════════════════════════════════════════════════════════════
    # متد اصلی فراخوانی OpenRouter API
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def _call_openrouter(
        self,
        model_key: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        فراخوانی OpenRouter API با یک مدل مشخص
        
        Args:
            model_key: کلید مدل (مثلاً "gpt-4o-mini")
            messages: لیست پیام‌ها
            max_tokens: حداکثر توکن خروجی
            temperature: میزان خلاقیت
        
        Returns:
            Tuple[متن پاسخ یا None, پیام خطا یا None]
        """
        if not self.api_key:
            return None, "API key not configured"
        
        if model_key not in AVAILABLE_MODELS:
            return None, f"Unknown model: {model_key}"
        
        model = AVAILABLE_MODELS[model_key]
        
        # چک غیرفعال بودن موقت
        if model_key in self._disabled_models:
            if datetime.now() < self._disabled_models[model_key]:
                return None, f"Model {model_key} temporarily disabled"
            del self._disabled_models[model_key]
        
        payload = {
            "model": model.model_id,
            "messages": messages,
            "max_tokens": min(max_tokens, model.max_tokens),
            "temperature": temperature,
        }
        
        for attempt in range(MAX_RETRIES_PER_MODEL):
            try:
                logger.debug(f"🔄 Calling {model.display_name} (attempt {attempt + 1})")
                
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        REQUEST_TIMEOUT_SECONDS,
                        connect=CONNECTION_TIMEOUT_SECONDS
                    )
                ) as client:
                    
                    response = await client.post(
                        OPENROUTER_BASE_URL,
                        headers=self.headers,
                        json=payload,
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if "choices" in data and len(data["choices"]) > 0:
                            content = data["choices"][0].get("message", {}).get("content", "")
                            
                            if content:
                                # ثبت آمار موفقیت
                                self.usage_stats.successful_requests += 1
                                self.usage_stats.last_successful_request = datetime.now()
                                
                                if model_key not in self.usage_stats.requests_per_model:
                                    self.usage_stats.requests_per_model[model_key] = 0
                                self.usage_stats.requests_per_model[model_key] += 1
                                
                                # تخمین توکن
                                self.usage_stats.total_tokens_used += len(content.split()) * 2
                                
                                logger.success(f"✅ {model.display_name} responded successfully")
                                return content.strip(), None
                        
                        return None, "Empty response from API"
                    
                    # مدیریت خطاها
                    elif response.status_code == 429:
                        logger.warning(f"⚠️ Rate limited by {model.display_name}")
                        self._disable_model_temporarily(model_key, minutes=10)
                        return None, "Rate limited"
                    
                    elif response.status_code == 401:
                        logger.error("❌ Invalid API Key")
                        self.status = AIStatus.OFFLINE
                        await self._notify_admin_error("API Key نامعتبر است!")
                        return None, "Invalid API key"
                    
                    elif response.status_code == 402:
                        logger.error("❌ Insufficient credits")
                        await self._notify_admin_error("اعتبار API تمام شده!")
                        return None, "Insufficient credits"
                    
                    elif response.status_code == 503:
                        logger.warning(f"⚠️ {model.display_name} temporarily unavailable")
                        if attempt < MAX_RETRIES_PER_MODEL - 1:
                            await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                            continue
                        return None, "Service unavailable"
                    
                    else:
                        error_text = response.text[:200] if response.text else "Unknown error"
                        logger.error(f"❌ API Error {response.status_code}: {error_text}")
                        return None, f"HTTP {response.status_code}: {error_text}"
            
            except httpx.TimeoutException:
                logger.warning(f"⏱️ Timeout calling {model.display_name}")
                if attempt < MAX_RETRIES_PER_MODEL - 1:
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue
                return None, "Timeout"
                
            except httpx.ConnectError as e:
                logger.error(f"🔌 Connection error: {e}")
                self._disable_model_temporarily(model_key, minutes=2)
                return None, "Connection error"
                
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                return None, str(e)
        
        self.usage_stats.failed_requests += 1
        return None, "All retries failed"
    
    def _disable_model_temporarily(self, model_key: str, minutes: int = 5) -> None:
        """غیرفعال کردن موقت یک مدل"""
        until = datetime.now() + timedelta(minutes=minutes)
        self._disabled_models[model_key] = until
        logger.info(f"⏸️ Model {model_key} disabled until {until.strftime('%H:%M:%S')}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # متد فراخوانی با Fallback چندلایه
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def _call_with_fallback(
        self,
        messages: List[Dict[str, Any]],
        model_priority: List[str],
        preferred_model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> Tuple[Optional[str], Optional[str], bool, Optional[str]]:
        """
        فراخوانی API با سیستم Fallback چندلایه
        
        Args:
            messages: لیست پیام‌ها
            model_priority: لیست مدل‌ها به ترتیب اولویت
            preferred_model: مدل ترجیحی (اگر کاربر انتخاب کرده)
            max_tokens: حداکثر توکن
            temperature: خلاقیت
        
        Returns:
            Tuple[پاسخ, مدل استفاده شده, آیا Fallback شد, مدل اصلی درخواست شده]
        """
        if not self.is_ai_available():
            return None, None, False, preferred_model
        
        # ساخت لیست مدل‌ها برای امتحان
        models_to_try = []
        original_model = preferred_model
        
        # اگر مدل ترجیحی مشخص شده، اول آن را امتحان کن
        if preferred_model and preferred_model in AVAILABLE_MODELS:
            models_to_try.append(preferred_model)
        
        # سپس بقیه مدل‌ها
        for model_key in model_priority:
            if model_key not in models_to_try and model_key in AVAILABLE_MODELS:
                models_to_try.append(model_key)
        
        # امتحان کردن مدل‌ها
        was_fallback = False
        
        for i, model_key in enumerate(models_to_try):
            if not AVAILABLE_MODELS[model_key].is_active:
                continue
            
            response_text, error = await self._call_openrouter(
                model_key=model_key,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            if response_text:
                # اگر از مدل اول نبود، Fallback شده
                if i > 0 and original_model:
                    was_fallback = True
                    logger.info(f"🔄 Fallback from {original_model} to {model_key}")
                
                return response_text, model_key, was_fallback, original_model
            
            # این مدل fail شد
            logger.debug(f"🔄 {model_key} failed: {error}, trying next...")
            
            # ذخیره خطا
            self.usage_stats.last_error = error
            self.usage_stats.last_error_time = datetime.now()
            self.usage_stats.last_error_model = model_key
        
        # همه مدل‌ها fail شدند
        logger.warning("⚠️ All models failed")
        return None, None, True, original_model
    
    # ═══════════════════════════════════════════════════════════════════════════
    # اطلاع‌رسانی به ادمین
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def _notify_admin_error(self, error_message: str) -> None:
        """ارسال پیام خطا به ادمین‌ها"""
        if not self._bot:
            logger.warning("Cannot notify admin: Bot not set")
            return
        
        text = (
            "🚨 <b>هشدار سرویس AI</b>\n\n"
            f"⚠️ {error_message}\n\n"
            f"⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📊 وضعیت: {self.status.value}"
        )
        
        for admin_id in settings.ADMIN_CHAT_IDS:
            try:
                await self._bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ذخیره و بارگذاری آمار
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _load_stats(self) -> None:
        """بارگذاری آمار از فایل"""
        if not STATS_FILE.exists():
            return
        
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.usage_stats.total_requests = data.get("total_requests", 0)
            self.usage_stats.successful_requests = data.get("successful_requests", 0)
            self.usage_stats.failed_requests = data.get("failed_requests", 0)
            self.usage_stats.fallback_used = data.get("fallback_used", 0)
            self.usage_stats.total_tokens_used = data.get("total_tokens_used", 0)
            self.usage_stats.requests_per_model = data.get("requests_per_model", {})
            self.usage_stats.voice_requests = data.get("voice_requests", 0)
            self.usage_stats.image_requests = data.get("image_requests", 0)
            
            logger.info("📊 Stats loaded from file")
            
        except Exception as e:
            logger.warning(f"Could not load stats: {e}")
    
    def save_stats(self) -> None:
        """ذخیره آمار در فایل"""
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            data = {
                "total_requests": self.usage_stats.total_requests,
                "successful_requests": self.usage_stats.successful_requests,
                "failed_requests": self.usage_stats.failed_requests,
                "fallback_used": self.usage_stats.fallback_used,
                "total_tokens_used": self.usage_stats.total_tokens_used,
                "requests_per_model": self.usage_stats.requests_per_model,
                "voice_requests": self.usage_stats.voice_requests,
                "image_requests": self.usage_stats.image_requests,
                "last_saved": datetime.now().isoformat(),
            }
            
            with open(STATS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug("📊 Stats saved")
            
        except Exception as e:
            logger.error(f"Could not save stats: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # متد کمکی برای پاسخ Fallback
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _get_fallback_response(self, message: str) -> str:
        """پیدا کردن پاسخ مناسب از دیتابیس Fallback"""
        message_lower = message.lower()
        
        for keyword, responses in FALLBACK_RESPONSES.items():
            if keyword != "default" and keyword in message_lower:
                return random.choice(responses)
        
        return random.choice(FALLBACK_RESPONSES["default"])
    
    # ═══════════════════════════════════════════════════════════════════════════
    # متد اصلی ساخت پیام‌ها با تاریخچه
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _build_messages_with_history(
        self,
        user_message: str,
        system_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        """
        ساخت لیست پیام‌ها با تاریخچه مکالمه
        
        Args:
            user_message: پیام فعلی کاربر
            system_prompt: پرامپت سیستم
            history: تاریخچه مکالمه (اختیاری)
        
        Returns:
            لیست پیام‌ها آماده برای API
        """
        messages = []
        
        # اگر تاریخچه داریم، از پرامپت با تاریخچه استفاده کن
        if history and len(history) > 0:
            # پرامپت سیستم با اشاره به تاریخچه
            system_with_history = SYSTEM_PROMPTS.get(
                "student_assistant_with_history",
                system_prompt
            )
            messages.append({"role": "system", "content": system_with_history})
            
            # اضافه کردن تاریخچه
            history_text = "\n\n--- تاریخچه مکالمه ---\n"
            for msg in history[-MAX_HISTORY_MESSAGES:]:
                role_name = "کاربر" if msg.get("role") == "user" else "دستیار"
                content = msg.get("content", "")[:500]  # محدود کردن طول
                history_text += f"{role_name}: {content}\n"
            history_text += "--- پایان تاریخچه ---\n\n"
            
            # اضافه کردن تاریخچه به پیام سیستم
            messages[0]["content"] += history_text
            
            # ثبت آمار
            self.usage_stats.history_used_count += 1
        else:
            messages.append({"role": "system", "content": system_prompt})
        
        # اضافه کردن پیام کاربر
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ۲۰. متد اصلی چت (اصلاح شده با model و history)
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def chat(
        self,
        message: str,
        user_id: int = 0,
        context: str = "student_assistant",
        model: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        use_cache: bool = True,
    ) -> AIResponse:
        """
        چت با هوش مصنوعی - نسخه ۲.۰
        
        Args:
            message: پیام کاربر
            user_id: شناسه کاربر
            context: نوع مکالمه (student_assistant, translator, ...)
            model: مدل انتخابی کاربر (اختیاری)
            history: تاریخچه مکالمه (اختیاری)
            use_cache: استفاده از کش
        
        Returns:
            AIResponse با تمام جزئیات
        
        مثال‌ها:
            # چت ساده
            response = await ai_service.chat("سلام")
            
            # با مدل خاص
            response = await ai_service.chat("سلام", model="claude-3.5-sonnet")
            
            # با تاریخچه
            history = [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            response = await ai_service.chat("ادامه بده", history=history)
        """
        start_time = time.time()
        self.usage_stats.total_requests += 1
        
        # ═══════════════════════════════════════════════════════════════════════
        # ۱. نرمال‌سازی و اعتبارسنجی
        # ═══════════════════════════════════════════════════════════════════════
        
        message_clean = message.strip()
        
        if not message_clean:
            return AIResponse(
                text="لطفاً سوالت رو بنویس! 😊",
                is_ai_generated=False,
                is_fallback=True,
                processing_time_ms=0,
            )
        
        # تعیین مدل
        preferred_model = model or self.default_model
        
        # ═══════════════════════════════════════════════════════════════════════
        # ۲. چک کش (فقط برای پیام‌های بدون تاریخچه)
        # ═══════════════════════════════════════════════════════════════════════
        
        cache_key = None
        if use_cache and not history:
            cache_key = self._make_cache_key(message_clean.lower(), "chat", preferred_model)
            cached = self._get_from_cache(cache_key)
            
            if cached:
                processing_time = int((time.time() - start_time) * 1000)
                return AIResponse(
                    text=cached.response,
                    is_ai_generated=(cached.source == "ai"),
                    model_used=cached.model_used,
                    model_key=preferred_model,
                    from_cache=True,
                    is_fallback=(cached.source == "fallback"),
                    processing_time_ms=processing_time,
                )
        
        # ═══════════════════════════════════════════════════════════════════════
        # ۳. تلاش برای API
        # ═══════════════════════════════════════════════════════════════════════
        
        if self.is_ai_available():
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS["student_assistant"])
            
            # ساخت پیام‌ها با تاریخچه
            messages = self._build_messages_with_history(
                user_message=message_clean,
                system_prompt=system_prompt,
                history=history,
            )
            
            # فراخوانی با Fallback
            response_text, model_used, was_fallback, original_model = await self._call_with_fallback(
                messages=messages,
                model_priority=CHAT_MODEL_PRIORITY,
                preferred_model=preferred_model,
                max_tokens=1024,
                temperature=0.7,
            )
            
            if response_text:
                processing_time = int((time.time() - start_time) * 1000)
                
                # ذخیره در کش (فقط بدون تاریخچه)
                if use_cache and cache_key and not history:
                    self._save_to_cache(cache_key, response_text, "ai", model_used)
                
                # اطلاعات مدل
                provider = None
                display_name = None
                if model_used and model_used in AVAILABLE_MODELS:
                    provider = AVAILABLE_MODELS[model_used].provider
                    display_name = AVAILABLE_MODELS[model_used].display_name
                
                return AIResponse(
                    text=response_text,
                    is_ai_generated=True,
                    model_used=display_name or model_used,
                    model_key=model_used,
                    provider=provider,
                    from_cache=False,
                    is_fallback=False,
                    was_model_fallback=was_fallback,
                    original_model=original_model,
                    processing_time_ms=processing_time,
                )
        
        # ═══════════════════════════════════════════════════════════════════════
        # ۴. Fallback به پاسخ‌های آماده
        # ═══════════════════════════════════════════════════════════════════════
        
        self.usage_stats.fallback_used += 1
        
        fallback_response = self._get_fallback_response(message_clean.lower())
        processing_time = int((time.time() - start_time) * 1000)
        
        # ذخیره در کش
        if use_cache and cache_key:
            self._save_to_cache(cache_key, fallback_response, "fallback", None)
        
        return AIResponse(
            text=fallback_response,
            is_ai_generated=False,
            model_used=None,
            model_key=None,
            provider=None,
            from_cache=False,
            is_fallback=True,
            was_model_fallback=True,
            original_model=preferred_model,
            processing_time_ms=processing_time,
            error="API not available, using fallback",
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ۲۱. متد تبدیل صدا به متن (جدید - با OpenRouter)
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        language: str = "fa",
        audio_format: str = "ogg",
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        تبدیل صدا به متن با استفاده از OpenRouter
        
        ⚠️ نکته: از مدل‌های Vision/Audio مانند Gemini استفاده می‌کند
        
        Args:
            audio_data: داده‌های صوتی به صورت bytes
            language: زبان صحبت (fa, en, it)
            audio_format: فرمت فایل (ogg, mp3, wav)
        
        Returns:
            Tuple[متن استخراج شده یا None, پیام خطا یا None]
        
        مثال:
            text, error = await ai_service.transcribe_audio(audio_bytes)
            if text:
                print(f"متن: {text}")
            else:
                print(f"خطا: {error}")
        """
        if not self.is_ai_available():
            return None, "سرویس AI در دسترس نیست"
        
        if not audio_data or len(audio_data) < 100:
            return None, "فایل صوتی خالی یا خیلی کوچک است"
        
        self.usage_stats.voice_requests += 1
        self.usage_stats.total_requests += 1
        
        try:
            # تبدیل به base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # تعیین MIME type
            mime_types = {
                "ogg": "audio/ogg",
                "oga": "audio/ogg",
                "mp3": "audio/mpeg",
                "wav": "audio/wav",
                "m4a": "audio/mp4",
                "webm": "audio/webm",
            }
            mime_type = mime_types.get(audio_format.lower(), "audio/ogg")
            
            # پرامپت برای تبدیل صدا
            lang_names = {"fa": "فارسی", "en": "انگلیسی", "it": "ایتالیایی"}
            lang_name = lang_names.get(language, "فارسی")
            
            prompt = f"""این یک فایل صوتی است. لطفاً:
1. محتوای صوتی را به متن تبدیل کن
2. زبان صحبت احتمالاً {lang_name} است
3. فقط متن استخراج شده را بنویس، بدون توضیح اضافه
4. علائم نگارشی مناسب بگذار
5. اگر صدا واضح نبود یا قابل تشخیص نبود، بگو "صدا قابل تشخیص نیست"
"""
            
            # امتحان مدل‌های Audio
            for model_key in AUDIO_MODEL_PRIORITY:
                if model_key not in AVAILABLE_MODELS:
                    continue
                
                model = AVAILABLE_MODELS[model_key]
                
                if not model.supports_audio:
                    continue
                
                # ساخت پیام با audio
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPTS["audio_transcriber"]},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "audio_url",
                                "audio_url": {
                                    "url": f"data:{mime_type};base64,{audio_base64}"
                                }
                            }
                        ]
                    }
                ]
                
                # برخی مدل‌ها از image_url با audio استفاده می‌کنند
                # تلاش دوم با فرمت دیگر
                messages_alt = [
                    {"role": "system", "content": SYSTEM_PROMPTS["audio_transcriber"]},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{audio_base64}"
                                }
                            }
                        ]
                    }
                ]
                
                # تلاش با فرمت اصلی
                for msg_format in [messages, messages_alt]:
                    try:
                        response_text, error = await self._call_openrouter(
                            model_key=model_key,
                            messages=msg_format,
                            max_tokens=500,
                            temperature=0.1,
                        )
                        
                        if response_text:
                            # پاکسازی پاسخ
                            text = response_text.strip()
                            
                            # چک پاسخ‌های خطا
                            error_phrases = [
                                "قابل تشخیص نیست",
                                "cannot transcribe",
                                "unable to process",
                                "no audio",
                                "صدایی نیست",
                            ]
                            
                            if any(phrase in text.lower() for phrase in error_phrases):
                                return None, "صدا قابل تشخیص نیست. لطفاً واضح‌تر صحبت کنید."
                            
                            logger.success(f"✅ Audio transcribed with {model.display_name}")
                            return text, None
                            
                    except Exception as e:
                        logger.debug(f"Format failed for {model_key}: {e}")
                        continue
                
                logger.debug(f"🔄 {model_key} failed for audio, trying next...")
            
            # اگر همه مدل‌ها fail شدند، از chat ساده استفاده کن
            logger.warning("⚠️ All audio models failed, trying text-only approach")
            
            fallback_prompt = f"""متأسفانه نتوانستم صدا را مستقیماً پردازش کنم.
کاربر یک پیام صوتی به زبان {lang_name} ارسال کرده.
لطفاً به او بگو که پیام صوتی دریافت شد ولی قابل پردازش نبود و از او بخواه متنی بنویسد."""
            
            return None, "مدل‌های تبدیل صدا در دسترس نیستند. لطفاً سوالتان را تایپ کنید."
            
        except Exception as e:
            logger.error(f"❌ Audio transcription error: {e}")
            return None, f"خطا در پردازش صدا: {str(e)}"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ۲۲. متد تحلیل تصویر (جدید)
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str = "این تصویر را توضیح بده",
        user_id: int = 0,
    ) -> AIResponse:
        """
        تحلیل تصویر با Vision API
        
        Args:
            image_data: داده‌های تصویر به صورت bytes
            prompt: سوال یا دستور کاربر درباره تصویر
            user_id: شناسه کاربر
        
        Returns:
            AIResponse با تحلیل تصویر
        
        مثال:
            response = await ai_service.analyze_image(image_bytes, "متن این تصویر را بخوان")
        """
        start_time = time.time()
        self.usage_stats.image_requests += 1
        self.usage_stats.total_requests += 1
        
        if not self.is_ai_available():
            return AIResponse(
                text="⚠️ سرویس تحلیل تصویر در دسترس نیست.",
                is_ai_generated=False,
                is_fallback=True,
                processing_time_ms=0,
            )
        
        if not image_data or len(image_data) < 100:
            return AIResponse(
                text="❌ تصویر خالی یا نامعتبر است.",
                is_ai_generated=False,
                is_fallback=True,
                processing_time_ms=0,
            )
        
        try:
            # تبدیل به base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # تشخیص فرمت تصویر (ساده)
            if image_data[:8] == b'\x89PNG\r\n\x1a\n':
                mime_type = "image/png"
            elif image_data[:2] == b'\xff\xd8':
                mime_type = "image/jpeg"
            elif image_data[:6] in (b'GIF87a', b'GIF89a'):
                mime_type = "image/gif"
            elif image_data[:4] == b'RIFF' and image_data[8:12] == b'WEBP':
                mime_type = "image/webp"
            else:
                mime_type = "image/jpeg"  # پیش‌فرض
            
            # ساخت پیام با تصویر
            messages = [
                {"role": "system", "content": SYSTEM_PROMPTS["vision_analyzer"]},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
            
            # امتحان مدل‌های Vision
            for model_key in VISION_MODEL_PRIORITY:
                if model_key not in AVAILABLE_MODELS:
                    continue
                
                model = AVAILABLE_MODELS[model_key]
                
                if not model.supports_vision:
                    continue
                
                try:
                    response_text, error = await self._call_openrouter(
                        model_key=model_key,
                        messages=messages,
                        max_tokens=1024,
                        temperature=0.3,
                    )
                    
                    if response_text:
                        processing_time = int((time.time() - start_time) * 1000)
                        
                        logger.success(f"✅ Image analyzed with {model.display_name}")
                        
                        return AIResponse(
                            text=response_text,
                            is_ai_generated=True,
                            model_used=model.display_name,
                            model_key=model_key,
                            provider=model.provider,
                            from_cache=False,
                            is_fallback=False,
                            processing_time_ms=processing_time,
                        )
                        
                except Exception as e:
                    logger.debug(f"🔄 {model_key} failed for vision: {e}")
                    continue
            
            # همه مدل‌ها fail شدند
            processing_time = int((time.time() - start_time) * 1000)
            
            return AIResponse(
                text="⚠️ متأسفانه نتوانستم تصویر را تحلیل کنم. لطفاً بعداً دوباره تلاش کنید.",
                is_ai_generated=False,
                is_fallback=True,
                processing_time_ms=processing_time,
                error="All vision models failed",
            )
            
        except Exception as e:
            logger.error(f"❌ Image analysis error: {e}")
            processing_time = int((time.time() - start_time) * 1000)
            
            return AIResponse(
                text=f"❌ خطا در تحلیل تصویر: {str(e)}",
                is_ai_generated=False,
                is_fallback=True,
                processing_time_ms=processing_time,
                error=str(e),
            )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ۲۳. متد ترجمه (اصلاح شده با model)
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def translate(
        self,
        text: str,
        source_lang: str = "it",
        target_lang: str = "fa",
        model: Optional[str] = None,
        use_cache: bool = True,
    ) -> AIResponse:
        """
        ترجمه متن
        
        Args:
            text: متن برای ترجمه
            source_lang: زبان مبدأ (it, en, fa)
            target_lang: زبان مقصد (it, en, fa)
            model: مدل انتخابی (اختیاری)
            use_cache: استفاده از کش
        
        Returns:
            AIResponse
        """
        start_time = time.time()
        self.usage_stats.total_requests += 1
        
        text_clean = text.strip()
        
        if not text_clean:
            return AIResponse(
                text="متنی برای ترجمه وارد نشده!",
                is_ai_generated=False,
                is_fallback=True,
                processing_time_ms=0,
            )
        
        # چک دیکشنری محلی
        text_lower = text_clean.lower()
        if source_lang == "it" and target_lang == "fa":
            if text_lower in ITALIAN_PERSIAN_DICTIONARY:
                translation = ITALIAN_PERSIAN_DICTIONARY[text_lower]
                processing_time = int((time.time() - start_time) * 1000)
                
                return AIResponse(
                    text=f"🇮🇹 <b>{text_clean}</b>\n\n🇮🇷 {translation}",
                    is_ai_generated=False,
                    is_fallback=True,
                    processing_time_ms=processing_time,
                )
        
        # چک کش
        cache_key = None
        preferred_model = model or self.default_model
        
        if use_cache:
            cache_key = self._make_cache_key(
                f"{source_lang}>{target_lang}:{text_lower}", 
                "translate",
                preferred_model
            )
            cached = self._get_from_cache(cache_key)
            
            if cached:
                processing_time = int((time.time() - start_time) * 1000)
                return AIResponse(
                    text=cached.response,
                    is_ai_generated=(cached.source == "ai"),
                    model_used=cached.model_used,
                    from_cache=True,
                    is_fallback=(cached.source == "fallback"),
                    processing_time_ms=processing_time,
                )
        
        # ترجمه با API
        if self.is_ai_available():
            lang_names = {"it": "ایتالیایی", "en": "انگلیسی", "fa": "فارسی"}
            source_name = lang_names.get(source_lang, source_lang)
            target_name = lang_names.get(target_lang, target_lang)
            
            messages = [
                {"role": "system", "content": SYSTEM_PROMPTS["translator"]},
                {"role": "user", "content": f"این متن را از {source_name} به {target_name} ترجمه کن:\n\n{text_clean}"},
            ]
            
            response_text, model_used, was_fallback, _ = await self._call_with_fallback(
                messages=messages,
                model_priority=TRANSLATION_MODEL_PRIORITY,
                preferred_model=preferred_model,
                max_tokens=1024,
                temperature=0.3,
            )
            
            if response_text:
                processing_time = int((time.time() - start_time) * 1000)
                
                formatted = f"🌐 <b>ترجمه:</b>\n\n"
                formatted += f"📝 <b>متن اصلی ({source_name}):</b>\n{text_clean}\n\n"
                formatted += f"📖 <b>ترجمه ({target_name}):</b>\n{response_text}"
                
                if use_cache and cache_key:
                    self._save_to_cache(cache_key, formatted, "ai", model_used)
                
                provider = None
                display_name = None
                if model_used and model_used in AVAILABLE_MODELS:
                    provider = AVAILABLE_MODELS[model_used].provider
                    display_name = AVAILABLE_MODELS[model_used].display_name
                
                return AIResponse(
                    text=formatted,
                    is_ai_generated=True,
                    model_used=display_name,
                    model_key=model_used,
                    provider=provider,
                    from_cache=False,
                    is_fallback=False,
                    was_model_fallback=was_fallback,
                    processing_time_ms=processing_time,
                )
        
        # Fallback
        self.usage_stats.fallback_used += 1
        processing_time = int((time.time() - start_time) * 1000)
        
        return AIResponse(
            text=f"🔤 <b>متن:</b>\n{text_clean}\n\n❌ ترجمه خودکار در دسترس نیست.",
            is_ai_generated=False,
            is_fallback=True,
            processing_time_ms=processing_time,
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ۲۴. متد کمک ایتالیایی (اصلاح شده)
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def italian_helper(
        self,
        word: str,
        help_type: str = "meaning",
        model: Optional[str] = None,
    ) -> AIResponse:
        """
        کمک در یادگیری زبان ایتالیایی
        
        Args:
            word: کلمه یا عبارت ایتالیایی
            help_type: نوع کمک (meaning, example, conjugate, pronunciation)
            model: مدل انتخابی (اختیاری)
        
        Returns:
            AIResponse
        """
        start_time = time.time()
        self.usage_stats.total_requests += 1
        
        word_clean = word.strip()
        word_lower = word_clean.lower()
        
        if not word_clean:
            return AIResponse(
                text="کلمه‌ای وارد نشده!",
                is_ai_generated=False,
                is_fallback=True,
                processing_time_ms=0,
            )
        
        # چک دیکشنری محلی برای معنی
        if help_type == "meaning" and word_lower in ITALIAN_PERSIAN_DICTIONARY:
            meaning = ITALIAN_PERSIAN_DICTIONARY[word_lower]
            processing_time = int((time.time() - start_time) * 1000)
            
            return AIResponse(
                text=f"🇮🇹 <b>{word_clean}</b>\n\n🇮🇷 <b>معنی:</b> {meaning}",
                is_ai_generated=False,
                is_fallback=True,
                processing_time_ms=processing_time,
            )
        
        # درخواست از API
        if self.is_ai_available():
            prompts = {
                "meaning": f"معنی و توضیح کلمه ایتالیایی «{word_clean}» را به فارسی بگو. تلفظ را هم با فینگلیش بنویس.",
                "example": f"برای کلمه ایتالیایی «{word_clean}» سه جمله مثال کاربردی بزن با ترجمه فارسی.",
                "conjugate": f"فعل ایتالیایی «{word_clean}» را در زمان حال صرف کن: io, tu, lui/lei, noi, voi, loro",
                "pronunciation": f"تلفظ صحیح «{word_clean}» را با فینگلیش بنویس و نکات تلفظی را توضیح بده.",
            }
            
            prompt = prompts.get(help_type, prompts["meaning"])
            
            messages = [
                {"role": "system", "content": SYSTEM_PROMPTS["italian_teacher"]},
                {"role": "user", "content": prompt},
            ]
            
            preferred_model = model or self.default_model
            
            response_text, model_used, was_fallback, _ = await self._call_with_fallback(
                messages=messages,
                model_priority=CHAT_MODEL_PRIORITY,
                preferred_model=preferred_model,
                max_tokens=512,
                temperature=0.5,
            )
            
            if response_text:
                processing_time = int((time.time() - start_time) * 1000)
                
                provider = None
                display_name = None
                if model_used and model_used in AVAILABLE_MODELS:
                    provider = AVAILABLE_MODELS[model_used].provider
                    display_name = AVAILABLE_MODELS[model_used].display_name
                
                return AIResponse(
                    text=response_text,
                    is_ai_generated=True,
                    model_used=display_name,
                    model_key=model_used,
                    provider=provider,
                    is_fallback=False,
                    was_model_fallback=was_fallback,
                    processing_time_ms=processing_time,
                )
        
        # Fallback
        self.usage_stats.fallback_used += 1
        processing_time = int((time.time() - start_time) * 1000)
        
        return AIResponse(
            text=f"🇮🇹 <b>{word_clean}</b>\n\n❌ اطلاعات این کلمه در دسترس نیست.",
            is_ai_generated=False,
            is_fallback=True,
            processing_time_ms=processing_time,
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ۲۵. متد خلاصه‌سازی
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def summarize(
        self,
        text: str,
        max_length: int = 200,
        model: Optional[str] = None,
    ) -> AIResponse:
        """خلاصه‌سازی متن"""
        start_time = time.time()
        self.usage_stats.total_requests += 1
        
        text_clean = text.strip()
        
        if not text_clean:
            return AIResponse(
                text="متنی برای خلاصه‌سازی وارد نشده!",
                is_ai_generated=False,
                is_fallback=True,
                processing_time_ms=0,
            )
        
        if self.is_ai_available():
            messages = [
                {"role": "system", "content": SYSTEM_PROMPTS["summarizer"]},
                {"role": "user", "content": f"این متن را در حداکثر {max_length} کلمه خلاصه کن:\n\n{text_clean}"},
            ]
            
            preferred_model = model or self.default_model
            
            response_text, model_used, was_fallback, _ = await self._call_with_fallback(
                messages=messages,
                model_priority=SUMMARIZATION_MODEL_PRIORITY,
                preferred_model=preferred_model,
                max_tokens=512,
                temperature=0.3,
            )
            
            if response_text:
                processing_time = int((time.time() - start_time) * 1000)
                
                provider = None
                display_name = None
                if model_used and model_used in AVAILABLE_MODELS:
                    provider = AVAILABLE_MODELS[model_used].provider
                    display_name = AVAILABLE_MODELS[model_used].display_name
                
                return AIResponse(
                    text=response_text,
                    is_ai_generated=True,
                    model_used=display_name,
                    provider=provider,
                    is_fallback=False,
                    processing_time_ms=processing_time,
                )
        
        # Fallback ساده
        self.usage_stats.fallback_used += 1
        
        sentences = text_clean.replace('\n', ' ').split('.')
        summary = '. '.join(s.strip() for s in sentences[:3] if s.strip())
        if summary and not summary.endswith('.'):
            summary += '.'
        
        if not summary:
            summary = text_clean[:200] + "..."
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return AIResponse(
            text=summary,
            is_ai_generated=False,
            is_fallback=True,
            processing_time_ms=processing_time,
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ۲۶. متد پاسخ پشتیبانی
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def smart_support(
        self,
        ticket_message: str,
        user_name: str = "کاربر",
    ) -> Tuple[str, float]:
        """پاسخ هوشمند به تیکت پشتیبانی"""
        message_lower = ticket_message.lower()
        
        for keyword, responses in FALLBACK_RESPONSES.items():
            if keyword != "default" and keyword in message_lower:
                return random.choice(responses), 0.8
        
        if self.is_ai_available():
            response = await self.chat(
                message=ticket_message,
                context="support_agent",
                use_cache=False,
            )
            
            if response.is_ai_generated:
                return response.text, 0.7
        
        return random.choice(FALLBACK_RESPONSES["default"]), 0.3
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ۲۷. متد توصیه آب‌وهوا
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_weather_advice(self, temperature: float, condition: str) -> str:
        """توصیه هوشمند بر اساس آب‌وهوا"""
        condition_lower = condition.lower()
        
        if "rain" in condition_lower or "drizzle" in condition_lower:
            return WEATHER_ADVICE["rainy"]
        if "thunder" in condition_lower or "storm" in condition_lower:
            return WEATHER_ADVICE["stormy"]
        if "snow" in condition_lower:
            return WEATHER_ADVICE["snowy"]
        if "fog" in condition_lower or "mist" in condition_lower:
            return WEATHER_ADVICE["foggy"]
        if "wind" in condition_lower and temperature < 15:
            return WEATHER_ADVICE["windy"]
        if "cloud" in condition_lower:
            return WEATHER_ADVICE["cloudy"]
        
        if temperature >= 35:
            return WEATHER_ADVICE["hot"]
        elif temperature >= 28:
            return WEATHER_ADVICE["warm"]
        elif temperature >= 20:
            return WEATHER_ADVICE["nice"]
        elif temperature >= 15:
            return WEATHER_ADVICE["mild"]
        elif temperature >= 8:
            return WEATHER_ADVICE["cool"]
        elif temperature >= 0:
            return WEATHER_ADVICE["cold"]
        else:
            return WEATHER_ADVICE["freezing"]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ۲۸. متد سازگاری با کد قدیمی
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """تولید پاسخ ساده (سازگاری با کد قدیمی)"""
        if not system_prompt:
            system_prompt = SYSTEM_PROMPTS["student_assistant"]
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        
        response_text, model_used, _, _ = await self._call_with_fallback(
            messages=messages,
            model_priority=CHAT_MODEL_PRIORITY,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return response_text
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ۲۹. بررسی سلامت سرویس
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def health_check(self) -> Dict[str, Any]:
        """بررسی سلامت سرویس"""
        result = {
            "status": "unknown",
            "api_available": False,
            "fallback_available": True,
            "cache_working": True,
            "models_checked": 0,
            "working_models": [],
            "failed_models": [],
        }
        
        if self.is_ai_available():
            test_messages = [
                {"role": "user", "content": "Say OK"}
            ]
            
            for model_key in ["gpt-4o-mini", "gemini-flash", "llama-3.1-8b"]:
                if model_key in AVAILABLE_MODELS:
                    result["models_checked"] += 1
                    
                    response, error = await self._call_openrouter(
                        model_key=model_key,
                        messages=test_messages,
                        max_tokens=10,
                        temperature=0,
                    )
                    
                    if response:
                        result["working_models"].append(model_key)
                        result["api_available"] = True
                    else:
                        result["failed_models"].append(model_key)
        
        if result["api_available"]:
            result["status"] = "healthy" if not result["failed_models"] else "degraded"
        else:
            result["status"] = "fallback_only"
        
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# ۳۰. ایجاد نمونه Singleton
# ═══════════════════════════════════════════════════════════════════════════════

ai_service = AIService()


# ═══════════════════════════════════════════════════════════════════════════════
# ۳۱. توابع کمکی
# ═══════════════════════════════════════════════════════════════════════════════

async def quick_chat(message: str, model: Optional[str] = None) -> str:
    """چت سریع - فقط متن پاسخ"""
    response = await ai_service.chat(message, model=model)
    return response.text


async def quick_translate(text: str, source: str = "it", target: str = "fa") -> str:
    """ترجمه سریع"""
    response = await ai_service.translate(text, source, target)
    return response.text


def get_ai_status() -> Dict[str, Any]:
    """دریافت وضعیت سرویس"""
    return ai_service.get_status()


# ═══════════════════════════════════════════════════════════════════════════════
# ۳۲. لاگ نهایی
# ═══════════════════════════════════════════════════════════════════════════════

logger.success("═" * 60)
logger.success("🤖 AI Service v2.0 - Fully Loaded!")
logger.success("═" * 60)
logger.info(f"   📊 Status: {ai_service.status.value}")
logger.info(f"   🤖 Default Model: {ai_service.default_model}")
logger.info(f"   📦 Available Models: {len(AVAILABLE_MODELS)}")
logger.info(f"   🖼️ Vision Models: {len([m for m in AVAILABLE_MODELS.values() if m.supports_vision])}")
logger.info(f"   🎤 Audio Models: {len([m for m in AVAILABLE_MODELS.values() if m.supports_audio])}")
logger.info(f"   📝 Fallback Entries: {len(FALLBACK_RESPONSES)}")
logger.info(f"   📖 Dictionary Entries: {len(ITALIAN_PERSIAN_DICTIONARY)}")
logger.success("═" * 60)


# ═══════════════════════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # کلاس‌ها
    "AIService",
    "AIModel",
    "AIResponse",
    "AIStatus",
    "ChatMessage",
    
    # نمونه سراسری
    "ai_service",
    
    # دیکشنری‌ها
    "AVAILABLE_MODELS",
    "SYSTEM_PROMPTS",
    "FALLBACK_RESPONSES",
    "ITALIAN_PERSIAN_DICTIONARY",
    
    # لیست‌های اولویت
    "CHAT_MODEL_PRIORITY",
    "VISION_MODEL_PRIORITY",
    "AUDIO_MODEL_PRIORITY",
    "TRANSLATION_MODEL_PRIORITY",
    
    # توابع کمکی
    "quick_chat",
    "quick_translate",
    "get_ai_status",
]