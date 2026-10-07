# handlers/ai_handler.py
# هندلر کامل هوش مصنوعی - نسخه ۷.۰
# ژانویه ۲۰۲۵

"""
═══════════════════════════════════════════════════════════════════════════════
                    🤖 هندلر هوشمند SmartStudentBot - نسخه ۷.۰
═══════════════════════════════════════════════════════════════════════════════

نسخه ۷.۰ شامل:
    ✅ پشتیبانی کامل از تاریخچه مکالمه (مشکل اصلی حل شد)
    ✅ انتخاب و استفاده واقعی از مدل توسط کاربر
    ✅ پیام صوتی با OpenRouter (بدون نیاز به OpenAI API)
    ✅ تحلیل تصویر با Vision API
    ✅ نمایش واضح Fallback به کاربر
    ✅ خواندن تنظیمات از config.py
    ✅ سیستم Warm-up و Keep-Alive
    ✅ مدیریت کامل خطاها با پیام‌های واضح

═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱: ایمپورت‌ها
# ═══════════════════════════════════════════════════════════════════════════════

# کتابخانه‌های استاندارد
import asyncio
import random
import traceback
import base64
import io
import os
from gtts import gTTS
from pypdf import PdfReader
from datetime import datetime, timedelta
from collections import defaultdict, Counter, deque
from contextlib import suppress, asynccontextmanager
from dataclasses import dataclass, field
from typing import (
    Dict, List, Optional, Any, Tuple, Callable, 
    AsyncGenerator, TypeVar, Union
)
from enum import Enum

# کتابخانه‌های شخص ثالث
import aiohttp
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode, ChatAction
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError

# تنظیمات پروژه
from config import settings, logger


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲: ایمپورت سرویس‌ها با Fallback ایمن
# ═══════════════════════════════════════════════════════════════════════════════

# ایمپورت AI Service
try:
    from services.ai_service import (
        ai_service, 
        AVAILABLE_MODELS, 
        AIResponse,
        AIModel,
        CHAT_MODEL_PRIORITY,
        VISION_MODEL_PRIORITY,
        AUDIO_MODEL_PRIORITY,
    )
    AI_SERVICE_AVAILABLE = True
    logger.info("✅ AI Service imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ AI Service not available: {e}")
    AI_SERVICE_AVAILABLE = False
    ai_service = None
    AVAILABLE_MODELS = {}
    CHAT_MODEL_PRIORITY = []
    VISION_MODEL_PRIORITY = []
    AUDIO_MODEL_PRIORITY = []
    
    @dataclass
    class AIResponse:
        """کلاس Fallback برای پاسخ AI"""
        text: str = "سرویس AI در دسترس نیست."
        is_ai_generated: bool = False
        model_used: Optional[str] = None
        model_key: Optional[str] = None
        provider: Optional[str] = None
        processing_time_ms: int = 0
        from_cache: bool = False
        is_fallback: bool = True
        was_model_fallback: bool = False
        original_model: Optional[str] = None
        error: Optional[str] = None


# ایمپورت توابع زبان
try:
    from handlers.cmd_start import get_user_lang, get_text, load_lang
    LANG_SERVICE_AVAILABLE = True
except ImportError:
    LANG_SERVICE_AVAILABLE = False
    def get_user_lang(user_id: int) -> dict: 
        return {"code": "fa"}
    def get_text(lang: dict, key: str, default: str = "") -> str: 
        return lang.get(key, default or key)
    def load_lang(code: str) -> dict: 
        return {"code": code}


# ایمپورت دیتابیس
try:
    from database import db
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    db = None


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۳: راه‌اندازی Router
# ═══════════════════════════════════════════════════════════════════════════════

router = Router()
router.name = "ai_handler"


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۴: خواندن تنظیمات از config.py
# ═══════════════════════════════════════════════════════════════════════════════

# تنظیمات Voice
VOICE_ENABLED: bool = settings.AI_VOICE_ENABLED
VOICE_MAX_DURATION_SECONDS: int = settings.AI_VOICE_MAX_DURATION
VOICE_SUPPORTED_FORMATS: List[str] = ["ogg", "mp3", "wav", "m4a", "oga", "webm"]

# تنظیمات Image
IMAGE_ENABLED: bool = settings.AI_IMAGE_ENABLED
IMAGE_MAX_SIZE_MB: int = settings.AI_IMAGE_MAX_SIZE_MB
IMAGE_SUPPORTED_FORMATS: List[str] = ["jpg", "jpeg", "png", "gif", "webp"]

# تنظیمات Rate Limiting
RATE_LIMIT_MESSAGES: int = settings.AI_RATE_LIMIT_MESSAGES
RATE_LIMIT_WINDOW: int = settings.AI_RATE_LIMIT_WINDOW
RATE_LIMIT_PREMIUM_MULTIPLIER: int = settings.AI_RATE_LIMIT_PREMIUM_MULTIPLIER

# تنظیمات تاریخچه چت
MAX_CHAT_HISTORY: int = settings.AI_HISTORY_MAX_MESSAGES
HISTORY_ENABLED: bool = settings.AI_HISTORY_ENABLED
HISTORY_CLEANUP_INTERVAL: int = 3600  # هر ساعت
HISTORY_MAX_AGE_HOURS: int = 24

# تنظیمات Timeout و Retry
AI_TIMEOUT_SECONDS: int = settings.AI_TIMEOUT_SECONDS
AI_RETRY_ATTEMPTS: int = settings.AI_MAX_RETRIES
AI_RETRY_DELAY_BASE: float = 1.0
AI_RETRY_DELAY_MAX: float = 10.0
TYPING_INTERVAL: int = 4

# تنظیمات Warm-up و Keep-Alive
WARMUP_ENABLED: bool = settings.AI_WARMUP_ENABLED
WARMUP_TIMEOUT_SECONDS: int = settings.AI_WARMUP_TIMEOUT
WARMUP_MESSAGE: str = "ping"
WARMUP_CACHE_DURATION: int = 300

KEEP_ALIVE_ENABLED: bool = settings.AI_KEEP_ALIVE_ENABLED
KEEP_ALIVE_INTERVAL: int = settings.AI_KEEP_ALIVE_INTERVAL
KEEP_ALIVE_MESSAGE: str = "keep-alive"

COLD_START_DETECTION_ENABLED: bool = True
COLD_START_THRESHOLD_MS: int = 5000
COLD_START_EXTRA_RETRIES: int = 2

# تنظیمات کش
CACHE_ENABLED: bool = settings.AI_CACHE_ENABLED

# مدل پیش‌فرض
DEFAULT_MODEL: str = settings.AI_DEFAULT_MODEL

# تنظیمات متریک
METRICS_MAX_POPULAR_QUESTIONS: int = 100
METRICS_RESPONSE_TIME_SAMPLES: int = 100


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۵: مدل‌های قابل انتخاب توسط کاربر
# ═══════════════════════════════════════════════════════════════════════════════

# ذخیره مدل انتخابی هر کاربر
_user_model_preferences: Dict[int, str] = {}
_user_model_last_activity: Dict[int, datetime] = {}

# اطلاعات نمایشی مدل‌ها
USER_SELECTABLE_MODELS: Dict[str, Dict[str, Any]] = {
    "gpt-4o-mini": {
        "icon": "⚡",
        "name": "GPT-4o Mini",
        "description": "سریع و ارزان - پیشنهادی",
        "provider": "OpenAI",
        "supports_vision": True,
        "supports_audio": False,
    },
    "gpt-4o": {
        "icon": "🧠",
        "name": "GPT-4o",
        "description": "قوی‌ترین - برای سوالات پیچیده",
        "provider": "OpenAI",
        "supports_vision": True,
        "supports_audio": True,
    },
    "claude-3.5-sonnet": {
        "icon": "🎭",
        "name": "Claude 3.5 Sonnet",
        "description": "بسیار هوشمند - کدنویسی عالی",
        "provider": "Anthropic",
        "supports_vision": True,
        "supports_audio": False,
    },
    "claude-3-haiku": {
        "icon": "🐇",
        "name": "Claude 3 Haiku",
        "description": "سریع و ارزان",
        "provider": "Anthropic",
        "supports_vision": True,
        "supports_audio": False,
    },
    "gemini-flash": {
        "icon": "💎",
        "name": "Gemini Flash 1.5",
        "description": "گوگل - سریع و رایگان",
        "provider": "Google",
        "supports_vision": True,
        "supports_audio": True,
    },
    "gemini-pro": {
        "icon": "💎",
        "name": "Gemini Pro 1.5",
        "description": "گوگل - context بلند",
        "provider": "Google",
        "supports_vision": True,
        "supports_audio": True,
    },
    "llama-3.1-70b": {
        "icon": "🦙",
        "name": "Llama 3.1 70B",
        "description": "متا - رایگان و قوی",
        "provider": "Meta",
        "supports_vision": False,
        "supports_audio": False,
    },
    "llama-3.1-8b": {
        "icon": "🦙",
        "name": "Llama 3.1 8B",
        "description": "متا - سبک و سریع",
        "provider": "Meta",
        "supports_vision": False,
        "supports_audio": False,
    },
    "grok": {
        "icon": "🤖",
        "name": "Grok",
        "description": "ایلان ماسک - xAI",
        "provider": "xAI",
        "supports_vision": False,
        "supports_audio": False,
    },
    "mistral-large": {
        "icon": "🌪️",
        "name": "Mistral Large",
        "description": "فرانسوی - قوی",
        "provider": "Mistral",
        "supports_vision": False,
        "supports_audio": False,
    },
}


def get_user_model(user_id: int) -> str:
    """دریافت مدل انتخابی کاربر"""
    return _user_model_preferences.get(user_id, DEFAULT_MODEL)


def set_user_model(user_id: int, model_key: str) -> bool:
    """تنظیم مدل برای کاربر"""
    if model_key in USER_SELECTABLE_MODELS or model_key in AVAILABLE_MODELS:
        _user_model_preferences[user_id] = model_key
        _user_model_last_activity[user_id] = datetime.now()
        logger.info(f"🤖 User {user_id} selected model: {model_key}")
        return True
    return False


def cleanup_user_model_preferences() -> int:
    """پاکسازی تنظیمات مدل کاربران غیرفعال"""
    if not _user_model_last_activity:
        return 0
    
    cutoff = datetime.now() - timedelta(hours=HISTORY_MAX_AGE_HOURS)
    users_to_remove = [
        user_id for user_id, last_time in _user_model_last_activity.items()
        if last_time < cutoff
    ]
    
    for user_id in users_to_remove:
        _user_model_preferences.pop(user_id, None)
        _user_model_last_activity.pop(user_id, None)
    
    if users_to_remove:
        logger.info(f"🧹 Cleaned {len(users_to_remove)} user model preferences")
    
    return len(users_to_remove)


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۶: کلاس‌های پایه
# ═══════════════════════════════════════════════════════════════════════════════

class Language(Enum):
    """زبان‌های پشتیبانی شده"""
    FA = "fa"
    EN = "en"
    IT = "it"


@dataclass
class ServiceHealth:
    """وضعیت سلامت سرویس"""
    is_ready: bool = False
    last_check: Optional[datetime] = None
    last_response_time_ms: int = 0
    consecutive_failures: int = 0
    is_cold: bool = True
    last_successful_call: Optional[datetime] = None


class AIStates(StatesGroup):
    """وضعیت‌های FSM"""
    chatting = State()
    waiting_for_translation = State()
    waiting_for_italian_word = State()
    selecting_help_type = State()
    waiting_for_feedback = State()
    warming_up = State()


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۷: کلاس AIServiceManager
# ═══════════════════════════════════════════════════════════════════════════════

class AIServiceManager:
    """
    مدیریت سرویس AI با قابلیت Warm-up و Keep-Alive
    """
    
    def __init__(self):
        self.health = ServiceHealth()
        self._lock = asyncio.Lock()
        self._warmup_in_progress = False
        self._warmup_event = asyncio.Event()
        self._keep_alive_task: Optional[asyncio.Task] = None
        
    @property
    def is_ready(self) -> bool:
        """آیا سرویس آماده است؟"""
        if not self.health.last_check:
            return False
        elapsed = (datetime.now() - self.health.last_check).total_seconds()
        return self.health.is_ready and elapsed < WARMUP_CACHE_DURATION
    
    @property
    def needs_warmup(self) -> bool:
        """آیا نیاز به Warm-up داریم؟"""
        if not WARMUP_ENABLED:
            return False
        if not self.health.last_check:
            return True
        elapsed = (datetime.now() - self.health.last_check).total_seconds()
        return elapsed >= WARMUP_CACHE_DURATION
    
    @property
    def is_cold(self) -> bool:
        """آیا سرویس در حالت Cold است؟"""
        if not self.health.last_successful_call:
            return True
        elapsed = (datetime.now() - self.health.last_successful_call).total_seconds()
        return elapsed > KEEP_ALIVE_INTERVAL
    
    async def warmup(self, force: bool = False) -> bool:
        """Warm-up سرویس AI"""
        if not force and not self.needs_warmup:
            return True
        
        if self._warmup_in_progress:
            try:
                await asyncio.wait_for(
                    self._warmup_event.wait(),
                    timeout=WARMUP_TIMEOUT_SECONDS
                )
                return self.health.is_ready
            except asyncio.TimeoutError:
                return False
        
        async with self._lock:
            self._warmup_in_progress = True
            self._warmup_event.clear()
            
            try:
                logger.info("🔥 Starting AI service warmup...")
                start_time = datetime.now()
                
                if not AI_SERVICE_AVAILABLE or not ai_service:
                    self.health.is_ready = False
                    return False
                
                try:
                    response = await asyncio.wait_for(
                        ai_service.chat(
                            message=WARMUP_MESSAGE,
                            user_id=0,
                            use_cache=False
                        ),
                        timeout=WARMUP_TIMEOUT_SECONDS
                    )
                    
                    elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                    
                    if response and response.text:
                        self.health.is_ready = True
                        self.health.last_check = datetime.now()
                        self.health.last_response_time_ms = elapsed_ms
                        self.health.consecutive_failures = 0
                        self.health.is_cold = False
                        self.health.last_successful_call = datetime.now()
                        
                        logger.success(f"✅ AI warmup successful in {elapsed_ms}ms")
                        return True
                    else:
                        raise Exception("Empty response")
                        
                except asyncio.TimeoutError:
                    logger.warning(f"⏰ AI warmup timeout")
                    self.health.consecutive_failures += 1
                    self.health.is_cold = True
                    return False
                    
                except Exception as e:
                    logger.error(f"❌ AI warmup error: {e}")
                    self.health.consecutive_failures += 1
                    return False
                    
            finally:
                self._warmup_in_progress = False
                self._warmup_event.set()
    
    async def ensure_ready(self, user_lang: str = "fa") -> Tuple[bool, str]:
        """اطمینان از آماده بودن سرویس"""
        if self.is_ready and not self.is_cold:
            return True, "✅"
        
        success = await self.warmup()
        
        if success:
            return True, "✅"
        else:
            return False, "⚠️ سرویس در حال بیدار شدن..."
    
    async def health_check(self) -> Dict[str, Any]:
        """بررسی سلامت"""
        return {
            "is_ready": self.health.is_ready,
            "is_cold": self.is_cold,
            "last_check": self.health.last_check.isoformat() if self.health.last_check else None,
            "last_response_time_ms": self.health.last_response_time_ms,
            "consecutive_failures": self.health.consecutive_failures,
            "warmup_in_progress": self._warmup_in_progress,
            "needs_warmup": self.needs_warmup,
        }
    
    def record_success(self, response_time_ms: int) -> None:
        """ثبت فراخوانی موفق"""
        self.health.is_ready = True
        self.health.last_check = datetime.now()
        self.health.last_response_time_ms = response_time_ms
        self.health.consecutive_failures = 0
        self.health.is_cold = False
        self.health.last_successful_call = datetime.now()
    
    def record_failure(self) -> None:
        """ثبت فراخوانی ناموفق"""
        self.health.consecutive_failures += 1
        if self.health.consecutive_failures >= 3:
            self.health.is_ready = False
    
    async def start_keep_alive(self) -> None:
        """شروع Keep-Alive"""
        if not KEEP_ALIVE_ENABLED:
            return
        
        if self._keep_alive_task and not self._keep_alive_task.done():
            return
        
        self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())
        logger.info("💓 Keep-alive started")
    
    async def stop_keep_alive(self) -> None:
        """توقف Keep-Alive"""
        if self._keep_alive_task:
            self._keep_alive_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._keep_alive_task
            logger.info("💓 Keep-alive stopped")
    
    async def _keep_alive_loop(self) -> None:
        """حلقه Keep-Alive"""
        while True:
            try:
                await asyncio.sleep(KEEP_ALIVE_INTERVAL)
                
                if self.health.last_successful_call and AI_SERVICE_AVAILABLE and ai_service:
                    try:
                        response = await asyncio.wait_for(
                            ai_service.chat(
                                message=KEEP_ALIVE_MESSAGE,
                                user_id=0,
                                use_cache=False
                            ),
                            timeout=10
                        )
                        
                        if response:
                            self.health.last_successful_call = datetime.now()
                            self.health.is_cold = False
                            
                    except Exception as e:
                        logger.debug(f"💓 Keep-alive ping failed: {e}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Keep-alive error: {e}")
                await asyncio.sleep(60)


# نمونه سراسری
service_manager = AIServiceManager()


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۸: کلاس Metrics
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AIMetrics:
    """مدیریت آمار و متریک‌ها"""
    
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0
    cache_hits: int = 0
    cold_start_requests: int = 0
    warmup_count: int = 0
    total_response_time_ms: int = 0
    
    # آمار جدید
    voice_requests: int = 0
    image_requests: int = 0
    model_fallback_count: int = 0
    history_used_count: int = 0
    
    response_times: deque = field(
        default_factory=lambda: deque(maxlen=METRICS_RESPONSE_TIME_SAMPLES)
    )
    
    requests_per_user: Counter = field(default_factory=Counter)
    requests_per_model: Counter = field(default_factory=Counter)
    popular_questions: Counter = field(default_factory=Counter)
    errors_by_type: Counter = field(default_factory=Counter)
    started_at: datetime = field(default_factory=datetime.now)
    
    def record_request(
        self, 
        user_id: int, 
        question: str, 
        success: bool, 
        time_ms: int,
        from_cache: bool = False,
        error_type: Optional[str] = None,
        was_cold_start: bool = False,
        model_used: Optional[str] = None,
        was_model_fallback: bool = False,
        used_history: bool = False,
    ) -> None:
        """ثبت یک درخواست"""
        self.total_requests += 1
        self.total_response_time_ms += time_ms
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error_type:
                self.errors_by_type[error_type] += 1
        
        if from_cache:
            self.cache_hits += 1
        
        if was_cold_start:
            self.cold_start_requests += 1
        
        if was_model_fallback:
            self.model_fallback_count += 1
        
        if used_history:
            self.history_used_count += 1
        
        if model_used:
            self.requests_per_model[model_used] += 1
        
        self.response_times.append(time_ms)
        self.requests_per_user[user_id] += 1
        
        short_question = question[:50].strip()
        if short_question:
            self.popular_questions[short_question] += 1
            if len(self.popular_questions) > METRICS_MAX_POPULAR_QUESTIONS:
                self.popular_questions = Counter(
                    dict(self.popular_questions.most_common(METRICS_MAX_POPULAR_QUESTIONS // 2))
                )
    
    def record_timeout(self, user_id: int) -> None:
        """ثبت timeout"""
        self.timeout_requests += 1
        self.failed_requests += 1
        self.total_requests += 1
        self.errors_by_type["timeout"] += 1
        self.requests_per_user[user_id] += 1
    
    def record_warmup(self) -> None:
        """ثبت Warm-up"""
        self.warmup_count += 1
    
    def record_voice(self) -> None:
        """ثبت درخواست صوتی"""
        self.voice_requests += 1
    
    def record_image(self) -> None:
        """ثبت درخواست تصویر"""
        self.image_requests += 1
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def avg_response_time_ms(self) -> float:
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    @property
    def cache_hit_rate(self) -> float:
        if self.successful_requests == 0:
            return 0.0
        return (self.cache_hits / self.successful_requests) * 100
    
    @property
    def model_fallback_rate(self) -> float:
        if self.successful_requests == 0:
            return 0.0
        return (self.model_fallback_count / self.successful_requests) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "timeout_requests": self.timeout_requests,
            "cache_hits": self.cache_hits,
            "cold_start_requests": self.cold_start_requests,
            "warmup_count": self.warmup_count,
            "voice_requests": self.voice_requests,
            "image_requests": self.image_requests,
            "model_fallback_count": self.model_fallback_count,
            "history_used_count": self.history_used_count,
            "success_rate": f"{self.success_rate:.1f}%",
            "avg_response_time_ms": f"{self.avg_response_time_ms:.0f}",
            "cache_hit_rate": f"{self.cache_hit_rate:.1f}%",
            "model_fallback_rate": f"{self.model_fallback_rate:.1f}%",
            "unique_users": len(self.requests_per_user),
            "top_models": dict(self.requests_per_model.most_common(5)),
        }
    
    def reset(self) -> Dict[str, Any]:
        """ریست آمار"""
        old_stats = self.to_dict()
        
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.timeout_requests = 0
        self.cache_hits = 0
        self.cold_start_requests = 0
        self.warmup_count = 0
        self.total_response_time_ms = 0
        self.voice_requests = 0
        self.image_requests = 0
        self.model_fallback_count = 0
        self.history_used_count = 0
        self.response_times = deque(maxlen=METRICS_RESPONSE_TIME_SAMPLES)
        self.requests_per_user = Counter()
        self.requests_per_model = Counter()
        self.popular_questions = Counter()
        self.errors_by_type = Counter()
        self.started_at = datetime.now()
        
        return old_stats


# نمونه سراسری
metrics = AIMetrics()


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۹: مدیریت تاریخچه چت
# ═══════════════════════════════════════════════════════════════════════════════

class ChatHistoryManager:
    """
    مدیریت تاریخچه چت کاربران
    
    این کلاس تاریخچه مکالمات را ذخیره و مدیریت می‌کند
    تا AI بتواند context مکالمه قبلی را داشته باشد.
    """
    
    def __init__(self, use_database: bool = False):
        self.use_database = use_database and DATABASE_AVAILABLE
        self._memory_history: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        self._last_activity: Dict[int, datetime] = {}
    
    async def add(
        self, 
        user_id: int, 
        role: str, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """اضافه کردن پیام به تاریخچه"""
        if not HISTORY_ENABLED:
            return
        
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self._memory_history[user_id].append(entry)
        
        # محدود کردن سایز
        if len(self._memory_history[user_id]) > MAX_CHAT_HISTORY * 2:
            self._memory_history[user_id] = self._memory_history[user_id][-MAX_CHAT_HISTORY * 2:]
        
        self._last_activity[user_id] = datetime.now()
    
    async def get(
        self, 
        user_id: int, 
        limit: int = MAX_CHAT_HISTORY
    ) -> List[Dict[str, str]]:
        """دریافت تاریخچه چت برای ارسال به AI"""
        if not HISTORY_ENABLED:
            return []
        
        history = self._memory_history.get(user_id, [])
        
        # فقط role و content را برگردان (فرمت مورد نیاز AI)
        return [
            {"role": h["role"], "content": h["content"]} 
            for h in history[-limit:]
        ]
    
    async def get_full(
        self, 
        user_id: int, 
        limit: int = MAX_CHAT_HISTORY
    ) -> List[Dict[str, Any]]:
        """دریافت تاریخچه کامل با متادیتا"""
        return self._memory_history.get(user_id, [])[-limit:]
    
    async def clear(self, user_id: int) -> int:
        """پاک کردن تاریخچه کاربر"""
        count = len(self._memory_history.get(user_id, []))
        self._memory_history[user_id] = []
        self._last_activity.pop(user_id, None)
        return count
    
    async def cleanup_old_data(self) -> int:
        """پاکسازی داده‌های قدیمی"""
        cleaned = 0
        cutoff = datetime.now() - timedelta(hours=HISTORY_MAX_AGE_HOURS)
        
        users_to_clean = [
            user_id for user_id, last_time in self._last_activity.items()
            if last_time < cutoff
        ]
        
        for user_id in users_to_clean:
            self._memory_history.pop(user_id, None)
            self._last_activity.pop(user_id, None)
            cleaned += 1
        
        if cleaned > 0:
            logger.info(f"🧹 Cleaned history for {cleaned} users")
        
        return cleaned
    
    def get_stats(self) -> Dict[str, int]:
        """دریافت آمار"""
        total_messages = sum(len(h) for h in self._memory_history.values())
        return {
            "total_users": len(self._memory_history),
            "total_messages": total_messages,
            "active_users": len(self._last_activity),
        }


# نمونه سراسری
chat_history_manager = ChatHistoryManager(use_database=DATABASE_AVAILABLE)


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۰: مدیریت Rate Limiting
# ═══════════════════════════════════════════════════════════════════════════════

class RateLimiter:
    """مدیریت محدودیت نرخ درخواست"""
    
    def __init__(self):
        self._user_requests: Dict[int, List[datetime]] = defaultdict(list)
        self._premium_users: set = set()
    
    def add_premium_user(self, user_id: int) -> None:
        self._premium_users.add(user_id)
    
    def remove_premium_user(self, user_id: int) -> None:
        self._premium_users.discard(user_id)
    
    def is_premium(self, user_id: int) -> bool:
        return user_id in self._premium_users
    
    def check(self, user_id: int) -> Tuple[bool, int]:
        """بررسی محدودیت - برگرداندن (مجاز است, ثانیه تا مجاز شدن)"""
        now = datetime.now()
        window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW)
        
        self._user_requests[user_id] = [
            t for t in self._user_requests[user_id] if t > window_start
        ]
        
        limit = RATE_LIMIT_MESSAGES
        if self.is_premium(user_id):
            limit *= RATE_LIMIT_PREMIUM_MULTIPLIER
        
        if len(self._user_requests[user_id]) >= limit:
            oldest = min(self._user_requests[user_id])
            wait = int((oldest + timedelta(seconds=RATE_LIMIT_WINDOW) - now).total_seconds())
            return False, max(0, wait)
        
        self._user_requests[user_id].append(now)
        return True, 0
    
    def get_remaining(self, user_id: int) -> int:
        """تعداد درخواست‌های باقی‌مانده"""
        now = datetime.now()
        window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW)
        
        recent = [t for t in self._user_requests.get(user_id, []) if t > window_start]
        
        limit = RATE_LIMIT_MESSAGES
        if self.is_premium(user_id):
            limit *= RATE_LIMIT_PREMIUM_MULTIPLIER
        
        return max(0, limit - len(recent))
    
    async def cleanup(self) -> int:
        """پاکسازی"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=RATE_LIMIT_WINDOW * 2)
        cleaned = 0
        
        users_to_clean = [
            user_id for user_id, requests in self._user_requests.items()
            if all(t < cutoff for t in requests)
        ]
        
        for user_id in users_to_clean:
            del self._user_requests[user_id]
            cleaned += 1
        
        return cleaned


# نمونه سراسری
rate_limiter = RateLimiter()


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۱: سوالات پرتکرار
# ═══════════════════════════════════════════════════════════════════════════════

QUICK_QUESTIONS: Dict[str, Dict[str, str]] = {
    "scholarship": {
        "fa": "شرایط و مراحل دریافت بورسیه DSU چیست؟ چه مدارکی لازم است؟",
        "en": "What are the requirements for DSU scholarship?",
        "it": "Quali sono i requisiti per la borsa di studio DSU?",
    },
    "permesso": {
        "fa": "مراحل گرفتن پرمسو (اجازه اقامت) در ایتالیا چیست؟",
        "en": "What are the steps to get a permesso in Italy?",
        "it": "Quali sono i passaggi per ottenere il permesso di soggiorno?",
    },
    "cost": {
        "fa": "هزینه ماهانه زندگی دانشجویی در پروجا چقدر است؟",
        "en": "What is the monthly cost of living in Perugia?",
        "it": "Qual è il costo mensile della vita a Perugia?",
    },
    "housing": {
        "fa": "چطور در پروجا خانه یا اتاق پیدا کنم؟",
        "en": "How to find housing in Perugia?",
        "it": "Come trovare alloggio a Perugia?",
    },
    "isee": {
        "fa": "ISEE چیست و چطور محاسبه می‌شود؟",
        "en": "What is ISEE and how is it calculated?",
        "it": "Cos'è l'ISEE e come si calcola?",
    },
    "codice_fiscale": {
        "fa": "کد فیسکاله چیست و چطور دریافت کنم؟",
        "en": "What is Codice Fiscale and how to get it?",
        "it": "Cos'è il Codice Fiscale e come ottenerlo?",
    },
    "university": {
        "fa": "ثبت‌نام در دانشگاه پروجا چگونه است؟",
        "en": "How to enroll at the University of Perugia?",
        "it": "Come iscriversi all'Università di Perugia?",
    },
}


def get_quick_question(key: str, lang: str = "fa") -> str:
    """دریافت متن سوال سریع"""
    return QUICK_QUESTIONS.get(key, {}).get(lang, "")


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۲: ایموجی‌ها
# ═══════════════════════════════════════════════════════════════════════════════

SUCCESS_EMOJIS = ["✨", "🎯", "💡", "🌟", "⭐", "🎉", "✅", "👍", "🚀", "💪"]


def get_random_emoji() -> str:
    return random.choice(SUCCESS_EMOJIS)


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۳: سیستم پیام‌های چندزبانه
# ═══════════════════════════════════════════════════════════════════════════════

MESSAGES: Dict[str, Dict[str, Any]] = {
    "fa": {
        # پردازش
        "thinking": [
            "🧠 <i>دارم فکر می‌کنم...</i>",
            "🤔 <i>یه لحظه صبر کن...</i>",
            "💭 <i>در حال پردازش...</i>",
            "⚡ <i>دارم جواب رو آماده می‌کنم...</i>",
        ],
        
        # Warm-up
        "warming_up": "🔄 <i>در حال آماده‌سازی سرویس...</i>",
        "warming_up_done": "✅ سرویس آماده است!",
        "warming_up_failed": "⚠️ سرویس در حال بیدار شدن است...",
        "service_waking_up": "☕ <i>سرویس در حال بیدار شدن...</i>",
        "retry_after_warmup": "🔄 در حال تلاش مجدد...",
        
        # Voice
        "voice_processing": "🎤 <i>در حال تبدیل صدا به متن...</i>",
        "voice_too_long": "⚠️ حداکثر طول ویس {seconds} ثانیه است.",
        "voice_error": "❌ خطا در پردازش صدا. لطفاً دوباره تلاش کنید.",
        "voice_empty": "❌ متنی از صدا استخراج نشد.\n\n💡 <b>راه‌حل:</b>\n• واضح‌تر صحبت کنید\n• نویز محیط را کم کنید\n• یا سوالتان را تایپ کنید",
        "voice_your_text": "🎤 <b>متن استخراج شده:</b>",
        "voice_not_supported": "⚠️ پشتیبانی از پیام صوتی فعال نیست.",
        
        # Image
        "image_processing": "🖼️ <i>در حال تحلیل تصویر...</i>",
        "image_too_large": "⚠️ حداکثر حجم تصویر {size}MB است.",
        "image_error": "❌ خطا در پردازش تصویر.",
        "image_analysis": "🖼️ <b>تحلیل تصویر:</b>",
        "image_not_supported": "⚠️ پشتیبانی از تصویر فعال نیست.",
        "image_no_caption": "این تصویر را توضیح بده و اگر متنی دارد بخوان.",
        
        # مدل
        "select_model_title": "🤖 <b>انتخاب مدل هوش مصنوعی</b>",
        "current_model": "مدل فعلی",
        "model_selected": "✅ مدل {name} انتخاب شد!",
        "model_not_found": "❌ مدل یافت نشد",
        "model_fallback_notice": "\n\n⚠️ <i>توجه: مدل {original} در دسترس نبود، از {used} استفاده شد.</i>",
        
        # خوشامدگویی
        "greeting": [
            "سلام! 👋 چطور می‌تونم کمکت کنم؟",
            "سلام دوست عزیز! 🌟 سوالت رو بپرس!",
            "هی! 😊 آماده‌ام کمکت کنم.",
        ],
        
        # خطا
        "error": [
            "😅 یه مشکلی پیش اومد، دوباره امتحان کن!",
            "🔄 خطا در پردازش، لطفاً دوباره بفرست.",
        ],
        
        # عمومی
        "rate_limit": "⏳ لطفاً {seconds} ثانیه صبر کنید.",
        "timeout": "⚠️ پاسخ‌دهی خیلی طول کشید. لطفاً دوباره تلاش کنید.",
        "service_unavailable": "⚠️ سرویس AI در حال حاضر در دسترس نیست.",
        "empty_message": "⚠️ لطفاً یک متن بنویسید!",
        "cancelled": "❌ لغو شد.",
        "chat_ended": "✅ چت پایان یافت.",
        "history_cleared": "🗑 {count} پیام پاک شد!",
        "send_word": "✍️ یک کلمه ایتالیایی بفرست:",
        "send_text": "✍️ متن خود را ارسال کنید:",
        "no_access": "⛔ دسترسی ندارید!",
        
        # منو
        "menu_title": "🤖 <b>دستیار هوشمند پروجا</b>",
        "chat_title": "💬 <b>چت با دستیار هوشمند</b>",
        "translate_title": "🌐 <b>ترجمه هوشمند</b>",
        "italian_title": "🇮🇹 <b>کمک یادگیری ایتالیایی</b>",
        "stats_title": "📊 <b>وضعیت سرویس AI</b>",
        "quick_title": "⚡ <b>سوالات پرتکرار</b>",
        
        # دکمه‌ها
        "btn_start_chat": "💬 شروع چت",
        "btn_translate": "🌐 ترجمه",
        "btn_italian": "🇮🇹 ایتالیایی",
        "btn_quick": "⚡ سوالات سریع",
        "btn_stats": "📊 وضعیت",
        "btn_main_menu": "🏠 منوی اصلی",
        "btn_ai_menu": "🔙 منوی AI",
        "btn_end_chat": "❌ پایان",
        "btn_clear_history": "🗑 پاک کردن تاریخچه",
        "btn_refresh": "🔄 به‌روزرسانی",
        "btn_cancel": "❌ لغو",
        "btn_select_model": "🤖 انتخاب مدل",
        "btn_new_word": "🆕 کلمه جدید",
        "btn_another_translate": "🔄 ترجمه دیگر",
        "btn_q_scholarship": "🎓 بورسیه",
        "btn_q_permesso": "🛂 پرمسو",
        "btn_q_cost": "💰 هزینه",
        "btn_q_housing": "🏠 مسکن",
    },
    
    "en": {
        "thinking": [
            "🧠 <i>Thinking...</i>",
            "🤔 <i>Just a moment...</i>",
            "💭 <i>Processing...</i>",
            "⚡ <i>Preparing the answer...</i>",
        ],
        "warming_up": "🔄 <i>Preparing service...</i>",
        "warming_up_done": "✅ Service is ready!",
        "warming_up_failed": "⚠️ Service is waking up...",
        "service_waking_up": "☕ <i>Service is waking up...</i>",
        "retry_after_warmup": "🔄 Retrying...",
        "voice_processing": "🎤 <i>Converting speech to text...</i>",
        "voice_too_long": "⚠️ Maximum voice length is {seconds} seconds.",
        "voice_error": "❌ Error processing audio. Please try again.",
        "voice_empty": "❌ No text extracted. Please speak clearly or type your question.",
        "voice_your_text": "🎤 <b>Extracted text:</b>",
        "voice_not_supported": "⚠️ Voice messages not supported.",
        "image_processing": "🖼️ <i>Analyzing image...</i>",
        "image_too_large": "⚠️ Maximum image size is {size}MB.",
        "image_error": "❌ Error processing image.",
        "image_analysis": "🖼️ <b>Image analysis:</b>",
        "image_not_supported": "⚠️ Image analysis not supported.",
        "image_no_caption": "Explain this image and transcribe any visible text.",
        "select_model_title": "🤖 <b>Select AI Model</b>",
        "current_model": "Current model",
        "model_selected": "✅ Model {name} selected!",
        "model_not_found": "❌ Model not found",
        "model_fallback_notice": "\n\n⚠️ <i>Note: {original} was unavailable, used {used} instead.</i>",
        "greeting": [
            "Hello! 👋 How can I help you?",
            "Hi friend! 🌟 Feel free to ask your question!",
            "Hey! 😊 Ready to help you.",
        ],
        "error": [
            "😅 Something went wrong, please try again!",
            "🔄 Processing error, please resend.",
        ],
        "rate_limit": "⏳ Please wait {seconds} seconds.",
        "timeout": "⚠️ Request timed out. Please try again.",
        "service_unavailable": "⚠️ AI service is currently unavailable.",
        "empty_message": "⚠️ Please write a message!",
        "cancelled": "❌ Cancelled.",
        "chat_ended": "✅ Chat ended.",
        "history_cleared": "🗑 {count} messages cleared!",
        "send_word": "✍️ Send an Italian word:",
        "send_text": "✍️ Send your text:",
        "no_access": "⛔ Access denied!",
        "menu_title": "🤖 <b>Perugia Smart Assistant</b>",
        "chat_title": "💬 <b>Chat with Smart Assistant</b>",
        "translate_title": "🌐 <b>Smart Translation</b>",
        "italian_title": "🇮🇹 <b>Italian Learning Help</b>",
        "stats_title": "📊 <b>AI Service Status</b>",
        "quick_title": "⚡ <b>Frequently Asked Questions</b>",
        "btn_start_chat": "💬 Start Chat",
        "btn_translate": "🌐 Translate",
        "btn_italian": "🇮🇹 Italian",
        "btn_quick": "⚡ Quick Questions",
        "btn_stats": "📊 Status",
        "btn_main_menu": "🏠 Main Menu",
        "btn_ai_menu": "🔙 AI Menu",
        "btn_end_chat": "❌ End Chat",
        "btn_clear_history": "🗑 Clear History",
        "btn_refresh": "🔄 Refresh",
        "btn_cancel": "❌ Cancel",
        "btn_select_model": "🤖 Select Model",
        "btn_new_word": "🆕 New Word",
        "btn_another_translate": "🔄 Another Translation",
        "btn_q_scholarship": "🎓 Scholarship",
        "btn_q_permesso": "🛂 Permesso",
        "btn_q_cost": "💰 Costs",
        "btn_q_housing": "🏠 Housing",
    },

    "it": {
        "thinking": [
            "🧠 <i>Sto pensando...</i>",
            "🤔 <i>Un momento...</i>",
            "💭 <i>Elaborazione in corso...</i>",
            "⚡ <i>Preparo la risposta...</i>",
        ],
        "warming_up": "🔄 <i>Preparazione del servizio...</i>",
        "warming_up_done": "✅ Servizio pronto!",
        "warming_up_failed": "⚠️ Il servizio si sta riattivando...",
        "service_waking_up": "☕ <i>Servizio in risveglio...</i>",
        "retry_after_warmup": "🔄 Riprovo...",
        "voice_processing": "🎤 <i>Trascrizione audio in testo...</i>",
        "voice_too_long": "⚠️ Lunghezza massima del vocale: {seconds} secondi.",
        "voice_error": "❌ Errore durante l'elaborazione dell'audio.",
        "voice_empty": "❌ Nessun testo rilevato. Parla chiaramente o scrivi il messaggio.",
        "voice_your_text": "🎤 <b>Testo estratto:</b>",
        "voice_not_supported": "⚠️ Messaggi vocali non supportati.",
        "image_processing": "🖼️ <i>Analisi dell'immagine...</i>",
        "image_too_large": "⚠️ Dimensione massima immagine: {size}MB.",
        "image_error": "❌ Errore durante l'elaborazione dell'immagine.",
        "image_analysis": "🖼️ <b>Analisi immagine:</b>",
        "image_not_supported": "⚠️ Analisi immagini non supportata.",
        "image_no_caption": "Descrivi questa immagine e leggi eventuale testo presente.",
        "select_model_title": "🤖 <b>Seleziona Modello AI</b>",
        "current_model": "Modello attuale",
        "model_selected": "✅ Modello {name} selezionato!",
        "model_not_found": "❌ Modello non trovato",
        "model_fallback_notice": "\n\n⚠️ <i>Nota: {original} non era disponibile, è stato usato {used}.</i>",
        "greeting": [
            "Ciao! 👋 Come posso aiutarti?",
            "Benvenuto! 🌟 Fai la tua domanda!",
            "Ehi! 😊 Pronto ad aiutarti.",
        ],
        "error": [
            "😅 Si è verificato un errore, riprova!",
            "🔄 Errore di elaborazione, invia di nuovo.",
        ],
        "rate_limit": "⏳ Attendi {seconds} secondi.",
        "timeout": "⚠️ Richiesta scaduta. Riprova per favore.",
        "service_unavailable": "⚠️ Servizio AI momentaneamente non disponibile.",
        "empty_message": "⚠️ Inserisci un messaggio!",
        "cancelled": "❌ Annullato.",
        "chat_ended": "✅ Chat terminata.",
        "history_cleared": "🗑 {count} messaggi cancellati!",
        "send_word": "✍️ Invia una parola in italiano:",
        "send_text": "✍️ Invia il tuo testo:",
        "no_access": "⛔ Accesso negato!",
        "menu_title": "🤖 <b>Assistente Intelligente Perugia</b>",
        "chat_title": "💬 <b>Chat con Assistente AI</b>",
        "translate_title": "🌐 <b>Traduzione Smart</b>",
        "italian_title": "🇮🇹 <b>Aiuto Lingua Italiana</b>",
        "stats_title": "📊 <b>Stato del Servizio AI</b>",
        "quick_title": "⚡ <b>Domande Frequenti</b>",
        "btn_start_chat": "💬 Inizia Chat",
        "btn_translate": "🌐 Traduci",
        "btn_italian": "🇮🇹 Italiano",
        "btn_quick": "⚡ Domande Rapide",
        "btn_stats": "📊 Stato",
        "btn_main_menu": "🏠 Menu Principale",
        "btn_ai_menu": "🔙 Menu AI",
        "btn_end_chat": "❌ Termina",
        "btn_clear_history": "🗑 Cancella Cronologia",
        "btn_refresh": "🔄 Aggiorna",
        "btn_cancel": "❌ Annulla",
        "btn_select_model": "🤖 Scegli Modello",
        "btn_new_word": "🆕 Nuova Parola",
        "btn_another_translate": "🔄 Altra Traduzione",
        "btn_q_scholarship": "🎓 Borsa Studio",
        "btn_q_permesso": "🛂 Permesso",
        "btn_q_cost": "💰 Costi",
        "btn_q_housing": "🏠 Alloggio",
    },
}


def get_msg(user_lang: str, key: str, **kwargs) -> str:
    """دریافت پیام براساس زبان"""
    lang_messages = MESSAGES.get(user_lang, MESSAGES["fa"])
    msg = lang_messages.get(key)
    
    if msg is None:
        msg = MESSAGES["fa"].get(key, key)
    
    if isinstance(msg, list):
        msg = random.choice(msg)
    
    if kwargs:
        try:
            msg = msg.format(**kwargs)
        except (KeyError, ValueError):
            pass
    
    return msg


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۴: توابع کمکی پایه
# ═══════════════════════════════════════════════════════════════════════════════

async def safe_answer(
    message: Message, 
    text: str, 
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: ParseMode = ParseMode.HTML,
    **kwargs
) -> Optional[Message]:
    """ارسال ایمن پیام"""
    try:
        return await message.answer(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            **kwargs
        )
    except TelegramBadRequest as e:
        logger.warning(f"⚠️ safe_answer error: {e}")
        try:
            clean_text = text.replace("<b>", "").replace("</b>", "")
            clean_text = clean_text.replace("<i>", "").replace("</i>", "")
            return await message.answer(text=clean_text, reply_markup=reply_markup, **kwargs)
        except Exception:
            return None
    except Exception as e:
        logger.error(f"❌ safe_answer error: {e}")
        return None


async def safe_edit_text(
    message: Message, 
    text: str, 
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: ParseMode = ParseMode.HTML,
    disable_web_page_preview: bool = True
) -> bool:
    """ویرایش ایمن پیام"""
    try:
        await message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview
        )
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            return True
        logger.warning(f"⚠️ safe_edit_text error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ safe_edit_text error: {e}")
        return False


async def safe_delete_message(message: Message) -> bool:
    """حذف ایمن پیام"""
    try:
        await message.delete()
        return True
    except Exception:
        return False


async def safe_answer_callback(
    callback: CallbackQuery, 
    text: str = "", 
    show_alert: bool = False
) -> bool:
    """پاسخ ایمن به callback"""
    try:
        await callback.answer(text=text, show_alert=show_alert)
        return True
    except Exception:
        return False


async def keep_typing(bot: Bot, chat_id: int) -> None:
    """ارسال مداوم وضعیت Typing"""
    try:
        while True:
            try:
                await bot.send_chat_action(chat_id, ChatAction.TYPING)
            except Exception:
                pass
            await asyncio.sleep(TYPING_INTERVAL)
    except asyncio.CancelledError:
        pass


async def get_user_language(user_id: int, state: Optional[FSMContext] = None) -> str:
    """دریافت زبان کاربر"""
    if state:
        try:
            data = await state.get_data()
            if "language" in data:
                return data["language"]
        except Exception:
            pass
    
    if LANG_SERVICE_AVAILABLE:
        try:
            lang_data = get_user_lang(user_id)
            return lang_data.get("code", "fa")
        except Exception:
            pass
    
    return "fa"


def is_admin(user_id: int) -> bool:
    """بررسی ادمین بودن"""
    return settings.is_admin(user_id)


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۵: تابع اصلی چت با تاریخچه (مشکل اصلی حل شد!)
# ═══════════════════════════════════════════════════════════════════════════════

async def chat_with_history(
    user_id: int,
    message: str,
    user_lang: str = "fa",
    model: Optional[str] = None,
    save_to_history: bool = True,
) -> Tuple[Optional[AIResponse], bool]:
    """
    🆕 چت با AI همراه با تاریخچه مکالمه
    
    این تابع مشکل اصلی "تاریخچه ذخیره میشه ولی استفاده نمیشه" را حل می‌کند.
    
    مراحل:
    1. دریافت تاریخچه قبلی از chat_history_manager
    2. ذخیره پیام کاربر در تاریخچه
    3. ارسال پیام + تاریخچه به ai_service.chat()
    4. ذخیره پاسخ AI در تاریخچه
    5. برگرداندن پاسخ
    
    Args:
        user_id: شناسه کاربر
        message: پیام کاربر
        user_lang: زبان کاربر
        model: مدل انتخابی (اختیاری، اگر None از تنظیمات کاربر)
        save_to_history: آیا در تاریخچه ذخیره شود
        
    Returns:
        Tuple[AIResponse یا None, آیا Cold Start بود]
    """
    if not AI_SERVICE_AVAILABLE or not ai_service:
        return None, False
    
    was_cold_start = service_manager.is_cold
    
    # ۱. دریافت مدل
    selected_model = model or get_user_model(user_id)
    
    # ۲. دریافت تاریخچه قبلی
    history = []
    if HISTORY_ENABLED:
        history = await chat_history_manager.get(user_id, limit=MAX_CHAT_HISTORY)
        if history:
            logger.debug(f"📜 Using {len(history)} history messages for user {user_id}")
    
    # ۳. ذخیره پیام کاربر
    if save_to_history and HISTORY_ENABLED:
        await chat_history_manager.add(
            user_id=user_id,
            role="user",
            content=message
        )
    
    # ۴. فراخوانی AI با تاریخچه و مدل
    try:
        response = await ai_service.chat(
            message=message,
            user_id=user_id,
            context="student_assistant",
            model=selected_model,  # ✅ مدل انتخابی کاربر
            history=history,       # ✅ تاریخچه مکالمه
            use_cache=CACHE_ENABLED and not history,  # کش فقط بدون تاریخچه
        )
        
        # ۵. ذخیره پاسخ AI
        if response and response.text and save_to_history and HISTORY_ENABLED:
            await chat_history_manager.add(
                user_id=user_id,
                role="assistant",
                content=response.text,
                metadata={
                    "model": response.model_key,
                    "was_fallback": response.was_model_fallback,
                }
            )
        
        # ۶. به‌روزرسانی service_manager
        if response and response.is_ai_generated:
            service_manager.record_success(response.processing_time_ms)
        
        return response, was_cold_start
        
    except Exception as e:
        logger.error(f"❌ chat_with_history error: {e}")
        service_manager.record_failure()
        return None, was_cold_start


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۶: Context Managers
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def ai_processing_context(
    bot: Bot,
    chat_id: int,
    message: Message,
    user_lang: str = "fa",
    thinking_text: Optional[str] = None,
    show_keyboard: bool = False,
    keyboard: Optional[InlineKeyboardMarkup] = None,
    do_warmup: bool = True
) -> AsyncGenerator[Tuple[Message, datetime, bool], None]:
    """
    Context Manager برای پردازش‌های AI
    
    Usage:
        async with ai_processing_context(bot, chat_id, message) as (thinking_msg, start_time, was_cold):
            response = await chat_with_history(user_id, text)
            await safe_edit_text(thinking_msg, response.text)
    """
    was_cold = service_manager.is_cold
    
    # Warm-up
    if do_warmup and WARMUP_ENABLED and service_manager.needs_warmup:
        warmup_msg = await safe_answer(message, get_msg(user_lang, "warming_up"))
        
        warmup_success = await service_manager.warmup()
        
        if warmup_success:
            if warmup_msg:
                await safe_edit_text(warmup_msg, get_msg(user_lang, "warming_up_done"))
                await asyncio.sleep(0.5)
            metrics.record_warmup()
        else:
            if warmup_msg:
                await safe_edit_text(warmup_msg, get_msg(user_lang, "service_waking_up"))
            was_cold = True
    
    # متن پیش‌فرض
    if thinking_text is None:
        thinking_text = get_msg(user_lang, "thinking")
        if was_cold:
            thinking_text = get_msg(user_lang, "service_waking_up") + "\n\n" + thinking_text
    
    start_time = datetime.now()
    typing_task = None
    thinking_msg = None
    
    try:
        thinking_msg = await safe_answer(
            message,
            thinking_text,
            reply_markup=keyboard if show_keyboard else None
        )
        
        if thinking_msg is None:
            thinking_msg = message
        
        typing_task = asyncio.create_task(keep_typing(bot, chat_id))
        
        yield thinking_msg, start_time, was_cold
        
    finally:
        if typing_task is not None:
            typing_task.cancel()
            with suppress(asyncio.CancelledError):
                await typing_task


@asynccontextmanager
async def callback_processing_context(
    callback: CallbackQuery,
    user_lang: str = "fa",
    thinking_text: Optional[str] = None,
    answer_text: str = "⏳",
    do_warmup: bool = True
) -> AsyncGenerator[Tuple[Message, datetime, bool], None]:
    """Context Manager برای callback های AI"""
    was_cold = service_manager.is_cold
    
    if do_warmup and WARMUP_ENABLED and service_manager.needs_warmup:
        await safe_answer_callback(callback, "🔄")
        await safe_edit_text(callback.message, get_msg(user_lang, "warming_up"))
        
        warmup_success = await service_manager.warmup()
        if warmup_success:
            metrics.record_warmup()
        else:
            was_cold = True
    else:
        await safe_answer_callback(callback, answer_text)
    
    if thinking_text is None:
        thinking_text = get_msg(user_lang, "thinking")
        if was_cold:
            thinking_text = get_msg(user_lang, "service_waking_up") + "\n\n" + thinking_text
    
    start_time = datetime.now()
    typing_task = None
    
    try:
        await safe_edit_text(callback.message, thinking_text)
        
        typing_task = asyncio.create_task(
            keep_typing(callback.bot, callback.message.chat.id)
        )
        
        yield callback.message, start_time, was_cold
        
    finally:
        if typing_task is not None:
            typing_task.cancel()
            with suppress(asyncio.CancelledError):
                await typing_task


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۷: توابع فرمت‌دهی پاسخ
# ═══════════════════════════════════════════════════════════════════════════════

def format_ai_response(
    response: AIResponse,
    user_lang: str = "fa",
    include_metadata: bool = True,
    question: Optional[str] = None,
    was_cold_start: bool = False
) -> str:
    """
    فرمت‌دهی پاسخ AI برای نمایش به کاربر
    
    شامل:
    - پاسخ اصلی
    - اطلاعات مدل استفاده شده
    - نمایش Fallback در صورت استفاده
    """
    emoji = get_random_emoji()
    text_parts = []
    
    # نمایش سوال
    if question:
        text_parts.append(f"❓ <b>سوال:</b>\n{question}\n")
        text_parts.append("━━━━━━━━━━━━━━━━━━━━━\n")
    
    # پاسخ اصلی
    text_parts.append(f"{emoji} <b>پاسخ:</b>\n\n{response.text}")
    
    # متادیتا
    if include_metadata:
        text_parts.append("\n\n━━━━━━━━━━━━━━━━━━━━━")
        
        # منبع پاسخ
        if response.is_ai_generated:
            source = f"🤖 AI"
            if response.model_used:
                source += f" ({response.model_used})"
        else:
            source = "📚 دانش محلی"
        
        if response.from_cache:
            source += " 📦"
        
        if was_cold_start:
            source += " ❄️"
        
        time_info = f"⏱ {response.processing_time_ms}ms"
        
        text_parts.append(f"\n<i>{source} | {time_info}</i>")
        
        # نمایش Fallback
        if response.was_model_fallback and response.original_model:
            original_info = USER_SELECTABLE_MODELS.get(response.original_model, {})
            used_info = USER_SELECTABLE_MODELS.get(response.model_key, {})
            
            original_name = original_info.get("name", response.original_model)
            used_name = used_info.get("name", response.model_key or "Unknown")
            
            text_parts.append(
                get_msg(user_lang, "model_fallback_notice", 
                       original=original_name, used=used_name)
            )
    
    return "".join(text_parts)


def format_translation_response(
    response: AIResponse,
    source_lang: str,
    target_lang: str,
    original_text: Optional[str] = None,
    user_lang: str = "fa"
) -> str:
    """فرمت‌دهی پاسخ ترجمه"""
    lang_flags = {"fa": "🇮🇷", "en": "🇬🇧", "it": "🇮🇹", "auto": "🔮"}
    
    emoji = get_random_emoji()
    src_flag = lang_flags.get(source_lang, "🌐")
    tgt_flag = lang_flags.get(target_lang, "🌐")
    
    text_parts = [f"🌐 <b>ترجمه {src_flag} → {tgt_flag}</b>\n\n"]
    
    if original_text:
        text_parts.append(f"📝 <b>متن اصلی:</b>\n{original_text}\n\n")
        text_parts.append("━━━━━━━━━━━━━━━━━━━━━\n\n")
    
    text_parts.append(f"{emoji} <b>ترجمه:</b>\n\n{response.text}")
    
    text_parts.append("\n\n━━━━━━━━━━━━━━━━━━━━━")
    source = "🤖 AI" if response.is_ai_generated else "📖"
    if response.model_used:
        source += f" ({response.model_used})"
    text_parts.append(f"\n<i>{source} | ⏱ {response.processing_time_ms}ms</i>")
    
    return "".join(text_parts)


def format_italian_help_response(
    response: AIResponse,
    word: str,
    help_type: str,
    user_lang: str = "fa"
) -> str:
    """فرمت‌دهی پاسخ کمک ایتالیایی"""
    help_type_names = {
        "meaning": "معنی",
        "example": "مثال",
        "conjugate": "صرف فعل",
        "pronunciation": "تلفظ"
    }
    
    emoji = get_random_emoji()
    type_name = help_type_names.get(help_type, help_type)
    
    return (
        f"🇮🇹 <b>{word}</b>\n"
        f"<i>{type_name.upper()}</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{emoji} {response.text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>{'🤖 AI' if response.is_ai_generated else '📖'} | ⏱ {response.processing_time_ms}ms</i>"
    )


def create_error_response(message: Optional[str] = None, user_lang: str = "fa") -> AIResponse:
    """ایجاد پاسخ خطا"""
    return AIResponse(
        text=message or get_msg(user_lang, "error"),
        is_ai_generated=False,
        is_fallback=True,
        error=message
    )


# ═══════════════════════════════════════════════════════════════════════════════
# پایان بخش ۱ از ۳
# ═══════════════════════════════════════════════════════════════════════════════

logger.info("📦 AI Handler v7.0 - Part 1/3 loaded")
logger.info(f"   • Voice Enabled: {VOICE_ENABLED}")
logger.info(f"   • Image Enabled: {IMAGE_ENABLED}")
logger.info(f"   • History Enabled: {HISTORY_ENABLED}")
logger.info(f"   • Default Model: {DEFAULT_MODEL}")
# ═══════════════════════════════════════════════════════════════════════════════
# handlers/ai_handler.py - بخش ۲ از ۳
# کیبوردها و هندلرهای اصلی
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۸: کیبوردها
# ═══════════════════════════════════════════════════════════════════════════════

def get_ai_menu_keyboard(user_lang: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد منوی اصلی AI"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_start_chat"),
                callback_data="ai:start_chat"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_translate"),
                callback_data="ai:translate_menu"
            ),
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_italian"),
                callback_data="ai:italian_menu"
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_select_model"),
                callback_data="ai:select_model"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_quick"),
                callback_data="ai:quick"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_stats"),
                callback_data="ai:stats"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_main_menu"),
                callback_data="main_menu"
            )
        ],
    ])


def get_chat_keyboard(user_lang: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد حین چت"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_msg(user_lang, "btn_q_scholarship"), callback_data="ai:q_scholarship"),
            InlineKeyboardButton(text=get_msg(user_lang, "btn_q_permesso"), callback_data="ai:q_permesso"),
        ],
        [
            InlineKeyboardButton(text=get_msg(user_lang, "btn_q_cost"), callback_data="ai:q_cost"),
            InlineKeyboardButton(text=get_msg(user_lang, "btn_q_housing"), callback_data="ai:q_housing"),
        ],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_clear_history"),
                callback_data="ai:clear_history"
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_ai_menu"),
                callback_data="ai:menu"
            ),
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_end_chat"),
                callback_data="ai:end_chat"
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_main_menu"),
                callback_data="main_menu"
            ),
        ],
    ])


def get_chat_with_model_keyboard(
    user_id: int,
    user_lang: str = "fa"
) -> InlineKeyboardMarkup:
    """کیبورد چت با نمایش مدل فعلی"""
    current_model = get_user_model(user_id)
    model_info = USER_SELECTABLE_MODELS.get(current_model, {})
    model_icon = model_info.get("icon", "🤖")
    model_name = model_info.get("name", current_model)
    
    # تعداد پیام‌های تاریخچه
    history_count = len(chat_history_manager._memory_history.get(user_id, []))
    if user_lang == "it":
        clear_text = f"🗑 Cancella ({history_count})" if history_count > 0 else "🗑 Vuoto"
    elif user_lang == "en":
        clear_text = f"🗑 Clear ({history_count})" if history_count > 0 else "🗑 Empty"
    else:
        clear_text = f"🗑 پاک ({history_count})" if history_count > 0 else "🗑 خالی"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_msg(user_lang, "btn_q_scholarship"), callback_data="ai:q_scholarship"),
            InlineKeyboardButton(text=get_msg(user_lang, "btn_q_permesso"), callback_data="ai:q_permesso"),
        ],
        [
            InlineKeyboardButton(text=get_msg(user_lang, "btn_q_cost"), callback_data="ai:q_cost"),
            InlineKeyboardButton(text=get_msg(user_lang, "btn_q_housing"), callback_data="ai:q_housing"),
        ],
        [
            InlineKeyboardButton(
                text=f"{model_icon} {model_name}",
                callback_data="ai:select_model"
            ),
        ],
        [
            InlineKeyboardButton(
                text=clear_text,
                callback_data="ai:clear_history"
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_ai_menu"),
                callback_data="ai:menu"
            ),
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_end_chat"),
                callback_data="ai:end_chat"
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_main_menu"),
                callback_data="main_menu"
            ),
        ],
    ])


def get_translate_menu_keyboard(user_lang: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد منوی ترجمه"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🇮🇹 → 🇮🇷  ایتالیایی به فارسی",
                callback_data="ai:tr_it_fa"
            )
        ],
        [
            InlineKeyboardButton(
                text="🇮🇷 → 🇮🇹  فارسی به ایتالیایی",
                callback_data="ai:tr_fa_it"
            )
        ],
        [
            InlineKeyboardButton(
                text="🇬🇧 → 🇮🇷  انگلیسی به فارسی",
                callback_data="ai:tr_en_fa"
            )
        ],
        [
            InlineKeyboardButton(
                text="🇮🇷 → 🇬🇧  فارسی به انگلیسی",
                callback_data="ai:tr_fa_en"
            )
        ],
        [
            InlineKeyboardButton(
                text="🇮🇹 → 🇬🇧  ایتالیایی به انگلیسی",
                callback_data="ai:tr_it_en"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔮 تشخیص خودکار → فارسی",
                callback_data="ai:tr_auto_fa"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_ai_menu"),
                callback_data="ai:menu"
            )
        ],
    ])


def get_translation_result_keyboard(
    source_lang: str, 
    target_lang: str,
    user_lang: str = "fa"
) -> InlineKeyboardMarkup:
    """کیبورد نتیجه ترجمه"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_another_translate"),
                callback_data=f"ai:tr_{source_lang}_{target_lang}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 منوی ترجمه",
                callback_data="ai:translate_menu"
            ),
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_ai_menu"),
                callback_data="ai:menu"
            )
        ]
    ])


def get_italian_help_keyboard(word: str, user_lang: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد کمک ایتالیایی"""
    safe_word = word[:20] if word else "parola"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📖 معنی",
                callback_data=f"ai:it_meaning:{safe_word}"
            ),
            InlineKeyboardButton(
                text="📝 مثال",
                callback_data=f"ai:it_example:{safe_word}"
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔄 صرف فعل",
                callback_data=f"ai:it_conjugate:{safe_word}"
            ),
            InlineKeyboardButton(
                text="🗣 تلفظ",
                callback_data=f"ai:it_pronounce:{safe_word}"
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_new_word"),
                callback_data="ai:italian_menu"
            ),
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_ai_menu"),
                callback_data="ai:menu"
            ),
        ],
    ])


def get_back_keyboard(user_lang: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد بازگشت"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_ai_menu"),
                callback_data="ai:menu"
            ),
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_main_menu"),
                callback_data="main_menu"
            ),
        ]
    ])


def get_cancel_keyboard(user_lang: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد لغو"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔄 تغییر زبان",
                callback_data="ai:translate_menu"
            ),
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_cancel"),
                callback_data="ai:menu"
            )
        ]
    ])


def get_quick_questions_keyboard(user_lang: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد سوالات سریع"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 شرایط بورسیه DSU", callback_data="ai:q_scholarship")],
        [InlineKeyboardButton(text="🛂 مراحل گرفتن پرمسو", callback_data="ai:q_permesso")],
        [InlineKeyboardButton(text="💰 هزینه زندگی در پروجا", callback_data="ai:q_cost")],
        [InlineKeyboardButton(text="🏠 پیدا کردن مسکن", callback_data="ai:q_housing")],
        [InlineKeyboardButton(text="🧮 محاسبه ISEE", callback_data="ai:q_isee")],
        [InlineKeyboardButton(text="🆔 کد فیسکاله", callback_data="ai:q_codice_fiscale")],
        [InlineKeyboardButton(text="🏫 ثبت‌نام دانشگاه", callback_data="ai:q_university")],
        [InlineKeyboardButton(text="💬 سوال دیگه دارم", callback_data="ai:start_chat")],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_ai_menu"),
                callback_data="ai:menu"
            )
        ],
    ])


def get_stats_keyboard(user_id: int, user_lang: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد صفحه آمار"""
    buttons = [
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_refresh"),
                callback_data="ai:stats"
            )
        ]
    ]
    
    if is_admin(user_id):
        buttons.append([
            InlineKeyboardButton(text="🗑 پاک کش", callback_data="ai:admin_clear"),
            InlineKeyboardButton(text="📋 مدل‌ها", callback_data="ai:admin_models"),
        ])
        buttons.append([
            InlineKeyboardButton(text="🔧 تست سرویس", callback_data="ai:admin_test"),
            InlineKeyboardButton(text="📊 متریک‌ها", callback_data="ai:admin_metrics"),
        ])
        buttons.append([
            InlineKeyboardButton(text="🔥 Warm-up", callback_data="ai:admin_warmup"),
            InlineKeyboardButton(text="🔄 ریست آمار", callback_data="ai:admin_reset_metrics"),
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text=get_msg(user_lang, "btn_ai_menu"),
            callback_data="ai:menu"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_model_selection_keyboard(
    current_model: str,
    user_lang: str = "fa"
) -> InlineKeyboardMarkup:
    """کیبورد انتخاب مدل AI"""
    buttons = []
    
    # گروه‌بندی بر اساس provider
    providers: Dict[str, List[Tuple[str, Dict]]] = {}
    for model_key, info in USER_SELECTABLE_MODELS.items():
        provider = info["provider"]
        if provider not in providers:
            providers[provider] = []
        providers[provider].append((model_key, info))
    
    provider_order = ["OpenAI", "Anthropic", "Google", "Meta", "xAI", "Mistral"]
    
    for provider in provider_order:
        if provider not in providers:
            continue
        
        models = providers[provider]
        
        # هدر provider
        buttons.append([
            InlineKeyboardButton(
                text=f"━━ {provider} ━━",
                callback_data="ai:noop"
            )
        ])
        
        for model_key, info in models:
            check = "✅ " if model_key == current_model else ""
            vision = " 🖼️" if info.get("supports_vision") else ""
            audio = " 🎤" if info.get("supports_audio") else ""
            
            btn_text = f"{check}{info['icon']} {info['name']}{vision}{audio}"
            
            buttons.append([
                InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"ai:set_model:{model_key}"
                )
            ])
    
    buttons.append([
        InlineKeyboardButton(
            text=get_msg(user_lang, "btn_ai_menu"),
            callback_data="ai:menu"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_voice_result_keyboard(user_lang: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد نتیجه پیام صوتی"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎤 ویس دیگه", callback_data="ai:start_chat"),
            InlineKeyboardButton(text="💬 تایپ کنم", callback_data="ai:start_chat"),
        ],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_ai_menu"),
                callback_data="ai:menu"
            ),
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_end_chat"),
                callback_data="ai:end_chat"
            ),
        ],
    ])


def get_image_result_keyboard(user_lang: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد نتیجه تحلیل تصویر"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🖼️ تصویر دیگه", callback_data="ai:start_chat"),
            InlineKeyboardButton(text="💬 سوال بپرسم", callback_data="ai:start_chat"),
        ],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_ai_menu"),
                callback_data="ai:menu"
            ),
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_end_chat"),
                callback_data="ai:end_chat"
            ),
        ],
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۹: هندلر منوی اصلی AI
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ai_chat")
@router.callback_query(F.data == "ai:menu")
async def show_ai_menu(callback: CallbackQuery, state: FSMContext):
    """نمایش منوی اصلی AI"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    logger.info(f"📱 User {user_id} opened AI menu")
    
    await state.clear()
    
    # وضعیت سرویس
    status_text = "N/A"
    status_emoji = "⚪"
    
    if AI_SERVICE_AVAILABLE and ai_service:
        try:
            status = ai_service.get_status()
            status_map = {
                "online": ("🟢", "آنلاین"),
                "degraded": ("🟡", "محدود"),
                "limited": ("🟠", "کند"),
                "offline": ("🔴", "آفلاین")
            }
            status_code = status.get("status", "unknown")
            status_emoji, status_text = status_map.get(status_code, ("⚪", status_code))
            
            if service_manager.is_cold:
                status_text += " (❄️)"
            else:
                status_text += " (🔥)"
                
        except Exception as e:
            logger.warning(f"⚠️ Error getting AI status: {e}")
            status_emoji = "🟡"
            status_text = "در حال بررسی"
    else:
        status_emoji = "🔴"
        status_text = "غیرفعال"
    
    # مدل فعلی کاربر
    current_model = get_user_model(user_id)
    model_info = USER_SELECTABLE_MODELS.get(current_model, {})
    model_display = f"{model_info.get('icon', '🤖')} {model_info.get('name', current_model)}"
    
    # تعداد پیام‌های تاریخچه
    history_count = len(chat_history_manager._memory_history.get(user_id, []))
    
    # ساخت متن
    text = f"{get_msg(user_lang, 'menu_title')}\n\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"🔌 <b>وضعیت:</b> {status_emoji} {status_text}\n"
    text += f"🤖 <b>مدل:</b> {model_display}\n"
    
    if history_count > 0:
        text += f"💬 <b>تاریخچه:</b> {history_count} پیام\n"
    
    text += f"\n<b>✨ امکانات:</b>\n"
    text += f"💬 چت هوشمند با حافظه مکالمه\n"
    text += f"🌐 ترجمه ایتالیایی ↔ فارسی ↔ انگلیسی\n"
    text += f"🇮🇹 کمک یادگیری ایتالیایی\n"
    
    if VOICE_ENABLED:
        text += f"🎤 ارسال پیام صوتی\n"
    if IMAGE_ENABLED:
        text += f"🖼️ تحلیل تصویر\n"
    
    text += f"⚡ سوالات پرتکرار\n\n"
    text += f"👇 <b>انتخاب کن:</b>"
    
    await safe_edit_text(
        callback.message,
        text,
        get_ai_menu_keyboard(user_lang)
    )
    await safe_answer_callback(callback)


@router.message(Command("ai", "ask", "chat"))
async def cmd_ai(message: Message, state: FSMContext):
    """دستور ورود به AI"""
    user_id = message.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    text = message.text or ""
    for cmd in ["/ai", "/ask", "/chat"]:
        text = text.replace(cmd, "").strip()
    
    if text:
        logger.info(f"📝 User {user_id} asked directly: {text[:50]}...")
        await state.set_state(AIStates.chatting)
        message.text = text
        await process_chat(message, state)
    else:
        await message.answer(
            f"{get_msg(user_lang, 'menu_title')}\n\nانتخاب کن:",
            reply_markup=get_ai_menu_keyboard(user_lang),
            parse_mode=ParseMode.HTML
        )


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۰: شروع چت
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ai:start_chat")
async def start_chat(callback: CallbackQuery, state: FSMContext):
    """شروع چت تعاملی با AI"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    logger.info(f"💬 User {user_id} starting chat...")
    
    await safe_answer_callback(callback, "⏳")
    
    # Warm-up
    warmup_needed = service_manager.needs_warmup or service_manager.is_cold
    
    if warmup_needed and WARMUP_ENABLED:
        warmup_text = f"{get_msg(user_lang, 'chat_title')}\n\n"
        warmup_text += f"{get_msg(user_lang, 'warming_up')}"
        
        await safe_edit_text(callback.message, warmup_text)
        
        typing_task = asyncio.create_task(
            keep_typing(callback.bot, callback.message.chat.id)
        )
        
        try:
            warmup_success = await service_manager.warmup(force=False)
            if warmup_success:
                metrics.record_warmup()
        finally:
            typing_task.cancel()
            with suppress(asyncio.CancelledError):
                await typing_task
    
    await state.set_state(AIStates.chatting)
    await state.update_data(language=user_lang)
    
    greeting = get_msg(user_lang, "greeting")
    
    # مدل فعلی
    current_model = get_user_model(user_id)
    model_info = USER_SELECTABLE_MODELS.get(current_model, {})
    model_display = f"{model_info.get('icon', '🤖')} {model_info.get('name', current_model)}"
    
    # تاریخچه
    history_count = len(chat_history_manager._memory_history.get(user_id, []))
    
    # وضعیت سرویس
    if service_manager.is_cold:
        service_status = "\n\n⚠️ <i>سرویس ممکن است کمی کند پاسخ دهد</i>"
    else:
        service_status = "\n\n✅ <i>سرویس آماده است</i>"
    
    text = f"{get_msg(user_lang, 'chat_title')}\n\n"
    text += f"{greeting}\n\n"
    text += f"🤖 <b>مدل:</b> {model_display}\n"
    
    if history_count > 0:
        text += f"💬 <b>تاریخچه:</b> {history_count} پیام (ادامه مکالمه قبلی)\n"
    
    # ورودی‌های پشتیبانی شده
    input_types = ["✍️ متن"]
    if VOICE_ENABLED:
        input_types.append("🎤 ویس")
    if IMAGE_ENABLED:
        input_types.append("🖼️ تصویر")
    
    text += f"\n<b>ورودی‌ها:</b> {' | '.join(input_types)}\n\n"
    text += f"✍️ <b>سوالت رو بنویس یا ویس/عکس بفرست...</b>"
    text += service_status
    
    await safe_edit_text(
        callback.message,
        text,
        get_chat_with_model_keyboard(user_id, user_lang)
    )


@router.callback_query(F.data == "ai:end_chat")
async def end_chat(callback: CallbackQuery, state: FSMContext):
    """پایان چت"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    logger.info(f"👋 User {user_id} ended chat")
    
    await state.clear()
    
    history = await chat_history_manager.get(user_id)
    message_count = len(history) // 2
    
    text = f"✅ <b>{get_msg(user_lang, 'chat_ended')}</b>\n\n"
    text += f"📊 <b>آمار این جلسه:</b>\n"
    text += f"• پیام‌ها: {len(history)}\n"
    text += f"• سوال و جواب: {message_count}\n\n"
    text += f"هر وقت خواستی برگرد! 👋"
    
    await safe_edit_text(
        callback.message,
        text,
        get_back_keyboard(user_lang)
    )
    await safe_answer_callback(callback, "👋")


@router.callback_query(F.data == "ai:clear_history")
async def clear_chat_history_handler(callback: CallbackQuery, state: FSMContext):
    """پاک کردن تاریخچه چت"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    count = await chat_history_manager.clear(user_id)
    
    logger.info(f"🗑 User {user_id} cleared {count} messages")
    
    await safe_answer_callback(
        callback,
        get_msg(user_lang, "history_cleared", count=count),
        show_alert=True
    )
    
    # به‌روزرسانی کیبورد
    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_chat_with_model_keyboard(user_id, user_lang)
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۱: پردازش اصلی چت (با تاریخچه - مشکل اصلی حل شد!)
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(AIStates.chatting, F.text)
async def process_chat(message: Message, state: FSMContext):
    """
    پردازش پیام‌های متنی چت - نسخه ۷.۰
    
    ✅ تغییرات کلیدی:
    - استفاده از chat_with_history() که تاریخچه را هم ارسال می‌کند
    - مدل انتخابی کاربر واقعاً استفاده می‌شود
    - نمایش Fallback در صورت تغییر مدل
    """
    user_id = message.from_user.id
    user_lang = await get_user_language(user_id, state)
    user_text = (message.text or "").strip()
    
    # بررسی دستورات خروج
    cancel_commands = ["/cancel", "/stop", "لغو", "خروج", "پایان", "cancel", "stop"]
    if user_text.lower() in cancel_commands:
        await state.clear()
        await message.answer(
            get_msg(user_lang, "cancelled"),
            reply_markup=get_back_keyboard(user_lang),
            parse_mode=ParseMode.HTML
        )
        return

    # بررسی خالی نبودن
    if not user_text:
        await message.answer(
            get_msg(user_lang, "empty_message"),
            reply_markup=get_chat_with_model_keyboard(user_id, user_lang),
            parse_mode=ParseMode.HTML
        )
        return

    # بررسی Rate Limit
    allowed, wait_seconds = rate_limiter.check(user_id)
    if not allowed:
        await message.answer(
            get_msg(user_lang, "rate_limit", seconds=wait_seconds),
            parse_mode=ParseMode.HTML
        )
        return

    logger.info(f"💬 Chat from {user_id}: {user_text[:50]}...")
    
    # شروع پردازش
    async with ai_processing_context(
        bot=message.bot,
        chat_id=message.chat.id,
        message=message,
        user_lang=user_lang,
        do_warmup=True
    ) as (thinking_msg, start_time, was_initially_cold):
        
        try:
            # ✅ استفاده از chat_with_history - مشکل اصلی حل شد!
            response, was_cold_start = await chat_with_history(
                user_id=user_id,
                message=user_text,
                user_lang=user_lang,
                model=None,  # از تنظیمات کاربر استفاده می‌کند
                save_to_history=True,
            )
            
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if response:
                # تعیین اینکه آیا تاریخچه استفاده شد
                history_count = len(chat_history_manager._memory_history.get(user_id, []))
                used_history = history_count > 2  # حداقل یک رفت و برگشت قبلی
                
                # ثبت متریک
                metrics.record_request(
                    user_id=user_id,
                    question=user_text,
                    success=True,
                    time_ms=elapsed_ms,
                    from_cache=response.from_cache,
                    was_cold_start=was_cold_start or was_initially_cold,
                    model_used=response.model_key,
                    was_model_fallback=response.was_model_fallback,
                    used_history=used_history,
                )
                
                # فرمت پاسخ
                response.processing_time_ms = elapsed_ms
                result_text = format_ai_response(
                    response=response,
                    user_lang=user_lang,
                    include_metadata=True,
                    was_cold_start=was_cold_start
                )
                
                await safe_edit_text(
                    thinking_msg,
                    result_text,
                    get_chat_with_model_keyboard(user_id, user_lang)
                )
                
            else:
                # Timeout یا خطا
                metrics.record_timeout(user_id)
                
                if was_cold_start or was_initially_cold:
                    error_text = get_msg(user_lang, "warming_up_failed")
                    error_text += "\n\n" + get_msg(user_lang, "retry_after_warmup")
                else:
                    error_text = get_msg(user_lang, "timeout")
                
                await safe_edit_text(
                    thinking_msg,
                    error_text,
                    get_chat_with_model_keyboard(user_id, user_lang)
                )
                
        except Exception as e:
            logger.error(f"❌ Error in process_chat: {e}")
            logger.debug(traceback.format_exc())
            
            metrics.record_request(
                user_id=user_id,
                question=user_text,
                success=False,
                time_ms=0,
                error_type=type(e).__name__
            )
            
            await safe_edit_text(
                thinking_msg,
                get_msg(user_lang, "error"),
                get_chat_with_model_keyboard(user_id, user_lang)
            )


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۲: سوالات سریع
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ai:quick")
async def show_quick_questions_menu(callback: CallbackQuery, state: FSMContext):
    """نمایش منوی سوالات سریع"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    await state.clear()
    
    text = f"{get_msg(user_lang, 'quick_title')}\n\n"
    text += "یکی رو انتخاب کن تا سریع جواب بگیری:\n\n"
    text += "💡 <i>این سوالات از پیش آماده شده‌اند</i>"
    
    await safe_edit_text(
        callback.message,
        text,
        get_quick_questions_keyboard(user_lang)
    )
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("ai:q_"))
async def handle_quick_question(callback: CallbackQuery, state: FSMContext):
    """پردازش سوالات سریع"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    q_key = callback.data.replace("ai:q_", "")
    question = get_quick_question(q_key, user_lang)
    
    if not question:
        question = "سوال نامشخص"
    
    logger.info(f"⚡ Quick question from {user_id}: {q_key}")
    
    await state.set_state(AIStates.chatting)
    
    async with callback_processing_context(
        callback=callback,
        user_lang=user_lang,
        thinking_text=f"❓ <b>سوال:</b>\n{question}\n\n{get_msg(user_lang, 'thinking')}",
        do_warmup=True
    ) as (msg, start_time, was_initially_cold):
        
        try:
            # ✅ استفاده از chat_with_history
            response, was_cold_start = await chat_with_history(
                user_id=user_id,
                message=question,
                user_lang=user_lang,
                save_to_history=True,
            )
            
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if response:
                metrics.record_request(
                    user_id=user_id,
                    question=f"[QUICK:{q_key}] {question[:30]}",
                    success=True,
                    time_ms=elapsed_ms,
                    from_cache=response.from_cache,
                    was_cold_start=was_cold_start or was_initially_cold,
                    model_used=response.model_key,
                    was_model_fallback=response.was_model_fallback,
                )
                
                response.processing_time_ms = elapsed_ms
                result_text = format_ai_response(
                    response=response,
                    user_lang=user_lang,
                    include_metadata=True,
                    question=question,
                    was_cold_start=was_cold_start
                )
                
                await safe_edit_text(
                    msg, 
                    result_text, 
                    get_chat_with_model_keyboard(user_id, user_lang)
                )
            else:
                metrics.record_timeout(user_id)
                await safe_edit_text(
                    msg,
                    f"❓ <b>سوال:</b>\n{question}\n\n{get_msg(user_lang, 'timeout')}",
                    get_chat_with_model_keyboard(user_id, user_lang)
                )
                
        except Exception as e:
            logger.error(f"❌ Error in quick question: {e}")
            await safe_edit_text(
                msg,
                get_msg(user_lang, "error"),
                get_chat_with_model_keyboard(user_id, user_lang)
            )


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۳: هندلر Voice (پیام صوتی) - با OpenRouter
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(AIStates.chatting, F.voice)
async def handle_voice_message(message: Message, state: FSMContext):
    """
    پردازش پیام صوتی - نسخه ۷.۰
    
    ✅ استفاده از ai_service.transcribe_audio() با OpenRouter
    ✅ نیازی به OPENAI_API_KEY نیست!
    """
    user_id = message.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    # بررسی فعال بودن
    if not VOICE_ENABLED:
        await message.answer(
            get_msg(user_lang, "voice_not_supported"),
            parse_mode=ParseMode.HTML
        )
        return
    
    # بررسی طول ویس
    voice_duration = message.voice.duration
    if voice_duration > VOICE_MAX_DURATION_SECONDS:
        await message.answer(
            get_msg(user_lang, "voice_too_long", seconds=VOICE_MAX_DURATION_SECONDS),
            parse_mode=ParseMode.HTML
        )
        return
    
    # Rate Limit
    allowed, wait_seconds = rate_limiter.check(user_id)
    if not allowed:
        await message.answer(
            get_msg(user_lang, "rate_limit", seconds=wait_seconds),
            parse_mode=ParseMode.HTML
        )
        return
    
    logger.info(f"🎤 Voice message from {user_id}, duration: {voice_duration}s")
    metrics.record_voice()
    
    async with ai_processing_context(
        bot=message.bot,
        chat_id=message.chat.id,
        message=message,
        user_lang=user_lang,
        thinking_text=get_msg(user_lang, "voice_processing"),
        do_warmup=True
    ) as (thinking_msg, start_time, was_initially_cold):
        
        try:
            # ۱. دانلود فایل صوتی
            file = await message.bot.get_file(message.voice.file_id)
            file_bytes = await message.bot.download_file(file.file_path)
            
            # تبدیل به bytes
            if hasattr(file_bytes, 'read'):
                audio_data = file_bytes.read()
            elif isinstance(file_bytes, io.BytesIO):
                audio_data = file_bytes.getvalue()
            else:
                audio_data = file_bytes
            
            # ۲. تبدیل صدا به متن با OpenRouter
            if AI_SERVICE_AVAILABLE and ai_service:
                transcribed_text, error = await ai_service.transcribe_audio(
                    audio_data=audio_data,
                    language=user_lang,
                    audio_format="ogg"
                )
            else:
                transcribed_text = None
                error = "سرویس AI در دسترس نیست"
            
            if error or not transcribed_text:
                await safe_edit_text(
                    thinking_msg,
                    get_msg(user_lang, "voice_empty"),
                    get_chat_with_model_keyboard(user_id, user_lang)
                )
                return
            
            # ۳. نمایش متن استخراج شده
            await safe_edit_text(
                thinking_msg,
                f"{get_msg(user_lang, 'voice_your_text')}\n{transcribed_text}\n\n{get_msg(user_lang, 'thinking')}"
            )
            
            # ۴. ارسال به AI با تاریخچه
            response, was_cold_start = await chat_with_history(
                user_id=user_id,
                message=transcribed_text,
                user_lang=user_lang,
                save_to_history=True,
            )
            
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if response:
                metrics.record_request(
                    user_id=user_id,
                    question=f"[VOICE] {transcribed_text[:30]}",
                    success=True,
                    time_ms=elapsed_ms,
                    from_cache=response.from_cache,
                    was_cold_start=was_cold_start or was_initially_cold,
                    model_used=response.model_key,
                )
                
                response.processing_time_ms = elapsed_ms
                
                result_text = f"🎤 <b>سوال شما:</b>\n{transcribed_text}\n\n"
                result_text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
                result_text += format_ai_response(
                    response=response,
                    user_lang=user_lang,
                    include_metadata=True,
                    was_cold_start=was_cold_start
                )
                
                await safe_edit_text(
                    thinking_msg,
                    result_text,
                    get_voice_result_keyboard(user_lang)
                )
            else:
                metrics.record_timeout(user_id)
                await safe_edit_text(
                    thinking_msg,
                    f"🎤 <b>متن:</b>\n{transcribed_text}\n\n{get_msg(user_lang, 'timeout')}",
                    get_chat_with_model_keyboard(user_id, user_lang)
                )
                
        except Exception as e:
            logger.error(f"❌ Voice processing error: {e}")
            logger.debug(traceback.format_exc())
            await safe_edit_text(
                thinking_msg,
                get_msg(user_lang, "voice_error"),
                get_chat_with_model_keyboard(user_id, user_lang)
            )


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۴: هندلر Image (تصویر)
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(AIStates.chatting, F.photo)
async def handle_image_message(message: Message, state: FSMContext):
    """پردازش تصویر"""
    user_id = message.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    if not IMAGE_ENABLED:
        await message.answer(
            get_msg(user_lang, "image_not_supported"),
            parse_mode=ParseMode.HTML
        )
        return
    
    # Rate Limit
    allowed, wait_seconds = rate_limiter.check(user_id)
    if not allowed:
        await message.answer(
            get_msg(user_lang, "rate_limit", seconds=wait_seconds),
            parse_mode=ParseMode.HTML
        )
        return
    
    # بزرگترین سایز
    photo = message.photo[-1]
    
    # Caption یا پیش‌فرض
    user_prompt = message.caption or get_msg(user_lang, "image_no_caption")
    
    logger.info(f"🖼️ Image from {user_id}, prompt: {user_prompt[:30]}...")
    metrics.record_image()
    
    async with ai_processing_context(
        bot=message.bot,
        chat_id=message.chat.id,
        message=message,
        user_lang=user_lang,
        thinking_text=get_msg(user_lang, "image_processing"),
        do_warmup=True
    ) as (thinking_msg, start_time, was_initially_cold):
        
        try:
            # دانلود تصویر
            file = await message.bot.get_file(photo.file_id)
            file_bytes = await message.bot.download_file(file.file_path)
            
            if hasattr(file_bytes, 'read'):
                image_data = file_bytes.read()
            elif isinstance(file_bytes, io.BytesIO):
                image_data = file_bytes.getvalue()
            else:
                image_data = file_bytes
            
            # تحلیل با Vision API
            if AI_SERVICE_AVAILABLE and ai_service:
                response = await ai_service.analyze_image(
                    image_data=image_data,
                    prompt=user_prompt,
                    user_id=user_id
                )
            else:
                response = create_error_response("سرویس AI در دسترس نیست", user_lang)
            
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if response and response.is_ai_generated:
                # ذخیره در تاریخچه
                await chat_history_manager.add(
                    user_id, "user",
                    f"[🖼️ Image] {user_prompt}"
                )
                await chat_history_manager.add(
                    user_id, "assistant",
                    response.text
                )
                
                metrics.record_request(
                    user_id=user_id,
                    question=f"[IMAGE] {user_prompt[:30]}",
                    success=True,
                    time_ms=elapsed_ms,
                    model_used=response.model_key,
                )
                
                result_text = f"{get_msg(user_lang, 'image_analysis')}\n\n"
                result_text += response.text
                result_text += "\n\n━━━━━━━━━━━━━━━━━━━━━"
                result_text += f"\n<i>🤖 {response.model_used} | ⏱ {elapsed_ms}ms</i>"
                
                await safe_edit_text(
                    thinking_msg,
                    result_text,
                    get_image_result_keyboard(user_lang)
                )
            else:
                error_msg = response.error if response else "خطای ناشناخته"
                await safe_edit_text(
                    thinking_msg,
                    f"{get_msg(user_lang, 'image_error')}\n\n<i>{error_msg}</i>",
                    get_chat_with_model_keyboard(user_id, user_lang)
                )
                
        except Exception as e:
            logger.error(f"❌ Image handling error: {e}")
            await safe_edit_text(
                thinking_msg,
                get_msg(user_lang, "image_error"),
                get_chat_with_model_keyboard(user_id, user_lang)
            )


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۵: هندلرهای انتخاب مدل
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ai:select_model")
async def show_model_selection(callback: CallbackQuery, state: FSMContext):
    """نمایش منوی انتخاب مدل"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    current_model = get_user_model(user_id)
    current_info = USER_SELECTABLE_MODELS.get(current_model, {})
    
    text = f"{get_msg(user_lang, 'select_model_title')}\n\n"
    
    if current_info:
        text += f"<b>{get_msg(user_lang, 'current_model')}:</b> "
        text += f"{current_info.get('icon', '')} {current_info.get('name', current_model)}\n"
        text += f"<i>{current_info.get('description', '')}</i>\n\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "🖼️ = پشتیبانی از تصویر\n"
    text += "🎤 = پشتیبانی از صدا\n"
    text += "✅ = مدل فعلی شما\n\n"
    text += "مدل مورد نظرت رو انتخاب کن:"
    
    await safe_edit_text(
        callback.message,
        text,
        get_model_selection_keyboard(current_model, user_lang)
    )
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("ai:set_model:"))
async def handle_model_selection(callback: CallbackQuery, state: FSMContext):
    """ذخیره مدل انتخابی"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    model_key = callback.data.replace("ai:set_model:", "")
    
    if set_user_model(user_id, model_key):
        model_info = USER_SELECTABLE_MODELS.get(model_key, {})
        model_name = model_info.get("name", model_key)
        
        await safe_answer_callback(
            callback,
            get_msg(user_lang, "model_selected", name=model_name),
            show_alert=True
        )
        
        # آپدیت صفحه
        await show_model_selection(callback, state)
    else:
        await safe_answer_callback(
            callback,
            get_msg(user_lang, "model_not_found"),
            show_alert=True
        )


@router.callback_query(F.data == "ai:noop")
async def noop_callback(callback: CallbackQuery):
    """عدم انجام کار (برای هدرها)"""
    await safe_answer_callback(callback)


# ═══════════════════════════════════════════════════════════════════════════════
# پایان بخش ۲ از ۳
# ═══════════════════════════════════════════════════════════════════════════════

logger.info("📦 AI Handler v7.0 - Part 2/3 loaded (Keyboards, Menu, Chat, Voice, Image, Model)")
# ═══════════════════════════════════════════════════════════════════════════════
# handlers/ai_handler.py - بخش ۳ از ۳
# ترجمه، ایتالیایی، آمار، ادمین، و توابع نهایی
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۶: مترجم هوشمند
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "translate")
@router.callback_query(F.data == "ai_translate")
@router.callback_query(F.data == "ai:translate_menu")
async def show_translate_menu(callback: CallbackQuery, state: FSMContext):
    """نمایش منوی ترجمه"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    await state.clear()
    
    text = f"{get_msg(user_lang, 'translate_title')}\n\n"
    text += "زبان مبدأ و مقصد رو انتخاب کن:\n\n"
    text += "💡 <i>یا «تشخیص خودکار» رو بزن!</i>"
    
    await safe_edit_text(
        callback.message,
        text,
        get_translate_menu_keyboard(user_lang)
    )
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("ai:tr_"))
async def select_translation(callback: CallbackQuery, state: FSMContext):
    """انتخاب زبان ترجمه"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    data = callback.data.replace("ai:tr_", "")
    
    if "_" in data:
        parts = data.split("_")
        source_lang = parts[0]
        target_lang = parts[1] if len(parts) > 1 else "fa"
    else:
        source_lang = "auto"
        target_lang = "fa"
    
    await state.update_data(
        tr_source=source_lang,
        tr_target=target_lang,
        language=user_lang
    )
    await state.set_state(AIStates.waiting_for_translation)
    
    lang_names = {
        "it": "ایتالیایی 🇮🇹",
        "en": "انگلیسی 🇬🇧",
        "fa": "فارسی 🇮🇷",
        "auto": "تشخیص خودکار 🔮"
    }
    
    source_name = lang_names.get(source_lang, source_lang)
    target_name = lang_names.get(target_lang, target_lang)
    
    text = f"🌐 <b>ترجمه {source_name} → {target_name}</b>\n\n"
    text += f"{get_msg(user_lang, 'send_text')}\n\n"
    text += "❌ لغو: /cancel"
    
    await safe_edit_text(
        callback.message,
        text,
        get_cancel_keyboard(user_lang)
    )
    await safe_answer_callback(callback)


@router.message(AIStates.waiting_for_translation)
async def process_translation(message: Message, state: FSMContext):
    """پردازش ترجمه"""
    user_id = message.from_user.id
    data = await state.get_data()
    user_lang = data.get("language", "fa")
    source_lang = data.get("tr_source", "auto")
    target_lang = data.get("tr_target", "fa")
    
    text_to_translate = (message.text or "").strip()
    
    # لغو
    if text_to_translate.lower() in ["/cancel", "لغو", "cancel"]:
        await state.clear()
        await message.answer(
            get_msg(user_lang, "cancelled"),
            reply_markup=get_back_keyboard(user_lang),
            parse_mode=ParseMode.HTML
        )
        return
    
    if not text_to_translate:
        await message.answer(
            get_msg(user_lang, "empty_message"),
            parse_mode=ParseMode.HTML
        )
        return
    
    # Rate Limit
    allowed, wait_seconds = rate_limiter.check(user_id)
    if not allowed:
        await message.answer(
            get_msg(user_lang, "rate_limit", seconds=wait_seconds),
            parse_mode=ParseMode.HTML
        )
        return
    
    logger.info(f"🌐 Translation from {user_id}: {source_lang} → {target_lang}")
    
    async with ai_processing_context(
        bot=message.bot,
        chat_id=message.chat.id,
        message=message,
        user_lang=user_lang,
        do_warmup=True
    ) as (thinking_msg, start_time, was_initially_cold):
        
        try:
            if AI_SERVICE_AVAILABLE and ai_service:
                actual_source = source_lang if source_lang != "auto" else "it"
                
                # دریافت مدل کاربر
                user_model = get_user_model(user_id)
                
                response = await ai_service.translate(
                    text=text_to_translate,
                    source_lang=actual_source,
                    target_lang=target_lang,
                    model=user_model,
                    use_cache=CACHE_ENABLED,
                )
                
                elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                if response and response.text:
                    metrics.record_request(
                        user_id=user_id,
                        question=f"[TR:{source_lang}→{target_lang}]",
                        success=True,
                        time_ms=elapsed_ms,
                        from_cache=response.from_cache,
                        was_cold_start=was_initially_cold,
                        model_used=response.model_key,
                        was_model_fallback=response.was_model_fallback,
                    )
                    
                    await safe_edit_text(
                        thinking_msg,
                        response.text,
                        get_translation_result_keyboard(source_lang, target_lang, user_lang)
                    )
                else:
                    await safe_edit_text(
                        thinking_msg,
                        get_msg(user_lang, "timeout"),
                        get_translate_menu_keyboard(user_lang)
                    )
            else:
                await safe_edit_text(
                    thinking_msg,
                    get_msg(user_lang, "service_unavailable"),
                    get_back_keyboard(user_lang)
                )
                
        except Exception as e:
            logger.error(f"❌ Translation error: {e}")
            await safe_edit_text(
                thinking_msg,
                get_msg(user_lang, "error"),
                get_translate_menu_keyboard(user_lang)
            )


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۷: دستیار زبان ایتالیایی
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "italian")
@router.callback_query(F.data == "ai_italian_help")
@router.callback_query(F.data == "ai:italian_menu")
async def show_italian_menu(callback: CallbackQuery, state: FSMContext):
    """منوی کمک ایتالیایی"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    await state.clear()
    await state.set_state(AIStates.waiting_for_italian_word)
    await state.update_data(language=user_lang)
    
    text = f"{get_msg(user_lang, 'italian_title')}\n\n"
    text += f"{get_msg(user_lang, 'send_word')}\n\n"
    text += "📖 معنی و توضیح\n"
    text += "📝 مثال کاربردی\n"
    text += "🔄 صرف فعل\n"
    text += "🗣 تلفظ صحیح\n\n"
    text += "❌ لغو: /cancel"
    
    await safe_edit_text(
        callback.message,
        text,
        get_back_keyboard(user_lang)
    )
    await safe_answer_callback(callback)


@router.message(AIStates.waiting_for_italian_word)
async def receive_italian_word(message: Message, state: FSMContext):
    """دریافت کلمه ایتالیایی"""
    user_id = message.from_user.id
    data = await state.get_data()
    user_lang = data.get("language", "fa")
    
    word = (message.text or "").strip()
    
    if word.lower() in ["/cancel", "لغو", "cancel"]:
        await state.clear()
        await message.answer(
            get_msg(user_lang, "cancelled"),
            reply_markup=get_back_keyboard(user_lang),
            parse_mode=ParseMode.HTML
        )
        return
    
    if not word:
        await message.answer(
            get_msg(user_lang, "empty_message"),
            parse_mode=ParseMode.HTML
        )
        return
    
    await state.update_data(italian_word=word)
    
    text = f"🇮🇹 <b>{word}</b>\n\n"
    text += "چه کمکی می‌خوای؟ 👇"
    
    await message.answer(
        text,
        reply_markup=get_italian_help_keyboard(word, user_lang),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data.startswith("ai:it_"))
async def process_italian_help(callback: CallbackQuery, state: FSMContext):
    """پردازش درخواست‌های کمک ایتالیایی"""
    user_id = callback.from_user.id
    data = await state.get_data()
    user_lang = data.get("language", "fa")
    
    callback_data = callback.data.replace("ai:it_", "")
    parts = callback_data.split(":", 1)
    
    help_type = parts[0]
    word = parts[1] if len(parts) > 1 else ""
    
    if not word or word == "parola":
        word = data.get("italian_word", "")
    
    if not word:
        await safe_answer_callback(
            callback,
            "❌ کلمه مشخص نیست",
            show_alert=True
        )
        return
    
    help_type_map = {
        "meaning": "meaning",
        "example": "example",
        "conjugate": "conjugate",
        "pronounce": "pronunciation"
    }
    
    actual_help_type = help_type_map.get(help_type, "meaning")
    
    logger.info(f"🇮🇹 Italian help from {user_id}: {help_type} for '{word}'")
    
    async with callback_processing_context(
        callback=callback,
        user_lang=user_lang,
        thinking_text=f"🇮🇹 <b>{word}</b>\n\n{get_msg(user_lang, 'thinking')}",
        do_warmup=True
    ) as (msg, start_time, was_initially_cold):
        
        try:
            if AI_SERVICE_AVAILABLE and ai_service:
                user_model = get_user_model(user_id)
                
                response = await ai_service.italian_helper(
                    word=word,
                    help_type=actual_help_type,
                    model=user_model,
                )
                
                elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                if response and response.text:
                    metrics.record_request(
                        user_id=user_id,
                        question=f"[IT:{help_type}] {word}",
                        success=True,
                        time_ms=elapsed_ms,
                        from_cache=response.from_cache,
                        was_cold_start=was_initially_cold,
                        model_used=response.model_key,
                    )
                    
                    response.processing_time_ms = elapsed_ms
                    result_text = format_italian_help_response(
                        response=response,
                        word=word,
                        help_type=actual_help_type,
                        user_lang=user_lang
                    )
                    
                    await safe_edit_text(
                        msg,
                        result_text,
                        get_italian_help_keyboard(word, user_lang)
                    )
                else:
                    await safe_edit_text(
                        msg,
                        get_msg(user_lang, "timeout"),
                        get_italian_help_keyboard(word, user_lang)
                    )
            else:
                await safe_edit_text(
                    msg,
                    get_msg(user_lang, "service_unavailable"),
                    get_back_keyboard(user_lang)
                )
                
        except Exception as e:
            logger.error(f"❌ Italian help error: {e}")
            await safe_edit_text(
                msg,
                get_msg(user_lang, "error"),
                get_italian_help_keyboard(word, user_lang)
            )


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۸: آمار و وضعیت سرویس
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ai_status")
@router.callback_query(F.data == "ai:stats")
async def show_stats(callback: CallbackQuery, state: FSMContext):
    """نمایش آمار سرویس AI"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    await safe_answer_callback(callback)
    
    text_parts = [f"{get_msg(user_lang, 'stats_title')}\n\n"]
    text_parts.append("━━━━━━━━━━━━━━━━━━━━━\n\n")
    
    # وضعیت سرویس
    if AI_SERVICE_AVAILABLE and ai_service:
        try:
            status = ai_service.get_status()
            status_code = status.get("status", "unknown")
            
            status_map = {
                "online": ("🟢", "آنلاین"),
                "degraded": ("🟡", "محدود"),
                "limited": ("🟠", "کند"),
                "offline": ("🔴", "آفلاین")
            }
            status_emoji, status_text = status_map.get(status_code, ("⚪", status_code))
            
            text_parts.append(f"<b>🔌 وضعیت سرویس:</b> {status_emoji} {status_text}\n")
            text_parts.append(f"<b>🔑 API Key:</b> {'✅' if status.get('api_key_configured') else '❌'}\n")
            text_parts.append(f"<b>🤖 مدل پیش‌فرض:</b> {status.get('default_model', 'N/A')}\n\n")
            
            # Cold/Warm
            health = await service_manager.health_check()
            cold_status = "❄️ Cold" if health["is_cold"] else "🔥 Warm"
            text_parts.append(f"<b>🌡 وضعیت:</b> {cold_status}\n")
            text_parts.append(f"<b>⏱ آخرین پاسخ:</b> {health['last_response_time_ms']}ms\n\n")
            
            # آمار سرویس
            text_parts.append(f"<b>📈 آمار سرویس:</b>\n")
            text_parts.append(f"• کل: <code>{status.get('total_requests', 0)}</code>\n")
            text_parts.append(f"• موفق: <code>{status.get('successful_requests', 0)}</code>\n")
            text_parts.append(f"• Voice: <code>{status.get('voice_requests', 0)}</code>\n")
            text_parts.append(f"• Image: <code>{status.get('image_requests', 0)}</code>\n")
            text_parts.append(f"• نرخ موفقیت: <code>{status.get('success_rate', '0%')}</code>\n\n")
            
            text_parts.append(f"<b>🤖 مدل‌ها:</b> {status.get('active_models', 0)}/{status.get('total_models', 0)}\n")
            text_parts.append(f"<b>💾 کش:</b> {status.get('cache_size', 0)} آیتم\n\n")
            
        except Exception as e:
            logger.error(f"❌ Error getting status: {e}")
            text_parts.append("⚠️ خطا در دریافت وضعیت\n\n")
    else:
        text_parts.append("🔴 <b>سرویس AI:</b> غیرفعال\n\n")
    
    # متریک‌های هندلر
    text_parts.append("━━━━━━━━━━━━━━━━━━━━━\n\n")
    text_parts.append(f"<b>📊 متریک‌های بات:</b>\n")
    text_parts.append(f"• کل: <code>{metrics.total_requests}</code>\n")
    text_parts.append(f"• موفق: <code>{metrics.successful_requests}</code>\n")
    text_parts.append(f"• ناموفق: <code>{metrics.failed_requests}</code>\n")
    text_parts.append(f"• Voice: <code>{metrics.voice_requests}</code>\n")
    text_parts.append(f"• Image: <code>{metrics.image_requests}</code>\n")
    text_parts.append(f"• تاریخچه استفاده: <code>{metrics.history_used_count}</code>\n")
    text_parts.append(f"• Model Fallback: <code>{metrics.model_fallback_count}</code>\n")
    text_parts.append(f"• نرخ موفقیت: <code>{metrics.success_rate:.1f}%</code>\n")
    text_parts.append(f"• میانگین زمان: <code>{metrics.avg_response_time_ms:.0f}ms</code>\n")
    text_parts.append(f"• کاربران یکتا: <code>{len(metrics.requests_per_user)}</code>\n\n")
    
    # تاریخچه چت
    history_stats = chat_history_manager.get_stats()
    text_parts.append(f"<b>💬 تاریخچه:</b>\n")
    text_parts.append(f"• کاربران: <code>{history_stats['active_users']}</code>\n")
    text_parts.append(f"• پیام‌ها: <code>{history_stats['total_messages']}</code>\n\n")
    
    # مدل‌های پرمصرف
    if metrics.requests_per_model:
        text_parts.append(f"<b>🏆 مدل‌های پرمصرف:</b>\n")
        for model, count in metrics.requests_per_model.most_common(3):
            model_info = USER_SELECTABLE_MODELS.get(model, {})
            icon = model_info.get("icon", "🤖")
            text_parts.append(f"• {icon} {model}: {count}\n")
        text_parts.append("\n")
    
    text_parts.append("━━━━━━━━━━━━━━━━━━━━━\n")
    text_parts.append(f"<i>⏰ {datetime.now().strftime('%H:%M:%S')}</i>")
    
    await safe_edit_text(
        callback.message,
        "".join(text_parts),
        get_stats_keyboard(user_id, user_lang)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۹: ابزارهای ادمین
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ai:admin_clear")
async def admin_clear_cache(callback: CallbackQuery, state: FSMContext):
    """پاک کردن کش AI"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await safe_answer_callback(callback, get_msg("fa", "no_access"), show_alert=True)
        return
    
    if AI_SERVICE_AVAILABLE and ai_service:
        try:
            count = ai_service.clear_cache()
            logger.info(f"🗑 Admin {user_id} cleared {count} cache items")
            await safe_answer_callback(callback, f"🗑 {count} آیتم پاک شد!", show_alert=True)
        except Exception as e:
            await safe_answer_callback(callback, f"❌ خطا: {e}", show_alert=True)
    
    await show_stats(callback, state)


@router.callback_query(F.data == "ai:admin_models")
async def admin_list_models(callback: CallbackQuery, state: FSMContext):
    """لیست مدل‌ها"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    if not is_admin(user_id):
        await safe_answer_callback(callback, get_msg("fa", "no_access"), show_alert=True)
        return
    
    await safe_answer_callback(callback)
    
    text_parts = ["📋 <b>لیست مدل‌های AI</b>\n\n"]
    
    if AI_SERVICE_AVAILABLE and ai_service:
        try:
            models = ai_service.get_available_models()
            
            for model in models[:15]:
                status_icon = "🟢" if model.get("is_active") else "🔴"
                name = model.get("name", "Unknown")
                provider = model.get("provider", "")
                requests = model.get("requests", 0)
                vision = "🖼️" if model.get("supports_vision") else ""
                audio = "🎤" if model.get("supports_audio") else ""
                
                text_parts.append(f"{status_icon} <b>{name}</b> {vision}{audio}\n")
                text_parts.append(f"   📡 {provider} | 📊 {requests}\n\n")
            
        except Exception as e:
            text_parts.append(f"❌ خطا: {e}\n")
    else:
        text_parts.append("🔴 سرویس غیرفعال\n")
    
    await safe_edit_text(
        callback.message,
        "".join(text_parts),
        get_stats_keyboard(user_id, user_lang)
    )


@router.callback_query(F.data == "ai:admin_test")
async def admin_test_service(callback: CallbackQuery, state: FSMContext):
    """تست سرویس AI"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    if not is_admin(user_id):
        await safe_answer_callback(callback, get_msg("fa", "no_access"), show_alert=True)
        return
    
    await safe_answer_callback(callback, "⏳ تست...")
    await safe_edit_text(callback.message, "🔧 <b>تست سرویس AI</b>\n\n⏳ در حال ارسال...")
    
    typing_task = asyncio.create_task(keep_typing(callback.bot, callback.message.chat.id))
    
    try:
        if AI_SERVICE_AVAILABLE and ai_service:
            start_time = datetime.now()
            
            response = await ai_service.chat(
                message="Test: Say 'OK' and the current time.",
                user_id=user_id,
                use_cache=False
            )
            
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if response and response.is_ai_generated:
                service_manager.record_success(elapsed_ms)
                
                text = f"✅ <b>تست موفق!</b>\n\n"
                text += f"<b>⏱ زمان:</b> {elapsed_ms}ms\n"
                text += f"<b>🤖 مدل:</b> {response.model_used}\n"
                text += f"<b>📦 کش:</b> {'بله' if response.from_cache else 'خیر'}\n"
                text += f"<b>🔄 Fallback:</b> {'بله' if response.was_model_fallback else 'خیر'}\n\n"
                text += f"<b>📝 پاسخ:</b>\n{response.text[:300]}"
            else:
                text = f"❌ <b>تست ناموفق</b>\n\n⏱ {elapsed_ms}ms"
        else:
            text = "🔴 <b>سرویس غیرفعال</b>"
        
    except Exception as e:
        text = f"❌ <b>خطا:</b>\n<code>{str(e)[:200]}</code>"
    
    finally:
        typing_task.cancel()
        with suppress(asyncio.CancelledError):
            await typing_task
    
    await safe_edit_text(callback.message, text, get_stats_keyboard(user_id, user_lang))


@router.callback_query(F.data == "ai:admin_warmup")
async def admin_warmup_service(callback: CallbackQuery, state: FSMContext):
    """Warm-up دستی"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    if not is_admin(user_id):
        await safe_answer_callback(callback, get_msg("fa", "no_access"), show_alert=True)
        return
    
    await safe_answer_callback(callback, "🔥 Warm-up...")
    await safe_edit_text(callback.message, "🔥 <b>Warm-up</b>\n\n⏳ در حال اجرا...")
    
    typing_task = asyncio.create_task(keep_typing(callback.bot, callback.message.chat.id))
    
    try:
        start_time = datetime.now()
        success = await service_manager.warmup(force=True)
        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        if success:
            metrics.record_warmup()
            health = await service_manager.health_check()
            
            text = f"✅ <b>Warm-up موفق!</b>\n\n"
            text += f"<b>⏱ زمان:</b> {elapsed_ms}ms\n"
            text += f"<b>🌡 وضعیت:</b> {'🔥 Warm' if not health['is_cold'] else '❄️ Cold'}\n"
        else:
            text = f"❌ <b>Warm-up ناموفق</b>\n\n⏱ {elapsed_ms}ms"
        
    except Exception as e:
        text = f"❌ <b>خطا:</b>\n<code>{str(e)[:200]}</code>"
    
    finally:
        typing_task.cancel()
        with suppress(asyncio.CancelledError):
            await typing_task
    
    await safe_edit_text(callback.message, text, get_stats_keyboard(user_id, user_lang))


@router.callback_query(F.data == "ai:admin_metrics")
async def admin_show_metrics(callback: CallbackQuery, state: FSMContext):
    """متریک‌های پیشرفته"""
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    if not is_admin(user_id):
        await safe_answer_callback(callback, get_msg("fa", "no_access"), show_alert=True)
        return
    
    await safe_answer_callback(callback)
    
    stats = metrics.to_dict()
    
    text_parts = ["📊 <b>متریک‌های پیشرفته</b>\n\n"]
    
    for key, value in stats.items():
        text_parts.append(f"• <b>{key}:</b> <code>{value}</code>\n")
    
    text_parts.append(f"\n<b>🏆 کاربران پرمصرف:</b>\n")
    for uid, count in metrics.requests_per_user.most_common(5):
        text_parts.append(f"• {uid}: {count}\n")
    
    text_parts.append(f"\n<b>❌ خطاها:</b>\n")
    for error, count in metrics.errors_by_type.most_common(5):
        text_parts.append(f"• {error}: {count}\n")
    
    await safe_edit_text(
        callback.message,
        "".join(text_parts),
        get_stats_keyboard(user_id, user_lang)
    )


@router.callback_query(F.data == "ai:admin_reset_metrics")
async def admin_reset_metrics(callback: CallbackQuery, state: FSMContext):
    """ریست آمار"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await safe_answer_callback(callback, get_msg("fa", "no_access"), show_alert=True)
        return
    
    old_stats = metrics.reset()
    
    logger.info(f"📊 Admin {user_id} reset metrics")
    
    await safe_answer_callback(
        callback,
        f"🔄 ریست شد! (قبلی: {old_stats.get('total_requests', 0)} درخواست)",
        show_alert=True
    )
    
    await show_stats(callback, state)


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۳۰: دستورات دیباگ
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("ai_debug"))
async def debug_ai(message: Message, state: FSMContext):
    """اطلاعات دیباگ"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    current_state = await state.get_state()
    state_data = await state.get_data()
    
    text_parts = ["🔍 <b>Debug Info</b>\n\n"]
    
    text_parts.append(f"<b>🔄 State:</b> <code>{current_state}</code>\n")
    text_parts.append(f"<b>📦 Data:</b> <code>{list(state_data.keys())}</code>\n\n")
    
    text_parts.append(f"<b>🤖 Services:</b>\n")
    text_parts.append(f"• AI: <code>{AI_SERVICE_AVAILABLE}</code>\n")
    text_parts.append(f"• Lang: <code>{LANG_SERVICE_AVAILABLE}</code>\n")
    text_parts.append(f"• DB: <code>{DATABASE_AVAILABLE}</code>\n\n")
    
    health = await service_manager.health_check()
    text_parts.append(f"<b>🌡 Service Manager:</b>\n")
    for key, value in health.items():
        text_parts.append(f"• {key}: <code>{value}</code>\n")
    
    text_parts.append(f"\n<b>⚙️ Config:</b>\n")
    text_parts.append(f"• Voice: <code>{VOICE_ENABLED}</code>\n")
    text_parts.append(f"• Image: <code>{IMAGE_ENABLED}</code>\n")
    text_parts.append(f"• History: <code>{HISTORY_ENABLED}</code>\n")
    text_parts.append(f"• Default Model: <code>{DEFAULT_MODEL}</code>\n")
    
    user_model = get_user_model(user_id)
    text_parts.append(f"\n<b>👤 Your Model:</b> <code>{user_model}</code>\n")
    
    history = await chat_history_manager.get(user_id)
    text_parts.append(f"<b>💬 Your History:</b> <code>{len(history)} messages</code>\n")
    
    await message.answer("".join(text_parts), parse_mode=ParseMode.HTML)


@router.message(Command("ai_cleanup"))
async def manual_cleanup(message: Message):
    """پاکسازی دستی"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    await message.answer("🧹 در حال پاکسازی...")
    
    history_cleaned = await chat_history_manager.cleanup_old_data()
    rate_cleaned = await rate_limiter.cleanup()
    model_cleaned = cleanup_user_model_preferences()
    
    await message.answer(
        f"✅ <b>پاکسازی انجام شد</b>\n\n"
        f"• تاریخچه: {history_cleaned} کاربر\n"
        f"• Rate Limit: {rate_cleaned} ورودی\n"
        f"• Model Prefs: {model_cleaned} کاربر",
        parse_mode=ParseMode.HTML
    )


@router.message(Command("ai_model"))
async def set_model_command(message: Message):
    """تنظیم مدل با دستور"""
    user_id = message.from_user.id
    
    text = message.text or ""
    parts = text.split()
    
    if len(parts) < 2:
        models_text = "\n".join([
            f"• <code>{key}</code> - {info['name']}"
            for key, info in USER_SELECTABLE_MODELS.items()
        ])
        await message.answer(
            f"📝 <b>استفاده:</b>\n/ai_model MODEL_KEY\n\n<b>مدل‌ها:</b>\n{models_text}",
            parse_mode=ParseMode.HTML
        )
        return
    
    model_key = parts[1].lower()
    
    if set_user_model(user_id, model_key):
        model_info = USER_SELECTABLE_MODELS.get(model_key, {})
        await message.answer(
            f"✅ مدل <b>{model_info.get('name', model_key)}</b> انتخاب شد.",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer("❌ مدل یافت نشد.")


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۳۱: بازخورد و لغو
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("ai:feedback_"))
async def handle_feedback(callback: CallbackQuery, state: FSMContext):
    """دریافت بازخورد"""
    user_id = callback.from_user.id
    feedback_type = callback.data.replace("ai:feedback_", "")
    
    logger.info(f"📝 Feedback from {user_id}: {feedback_type}")
    
    if feedback_type == "good":
        await safe_answer_callback(callback, "🙏 ممنون!", show_alert=True)
    else:
        await safe_answer_callback(callback, "🙏 ممنون! سعی می‌کنیم بهتر بشیم.", show_alert=True)


@router.message(Command("cancel"), StateFilter(AIStates))
async def cancel_command(message: Message, state: FSMContext):
    """لغو عملیات"""
    user_id = message.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    await state.clear()
    
    await message.answer(
        get_msg(user_lang, "cancelled"),
        reply_markup=get_back_keyboard(user_lang),
        parse_mode=ParseMode.HTML
    )


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۳۲: تسک‌های پس‌زمینه
# ═══════════════════════════════════════════════════════════════════════════════

_cleanup_task: Optional[asyncio.Task] = None


async def cleanup_loop():
    """حلقه پاکسازی خودکار"""
    logger.info("🧹 Cleanup loop started")
    
    while True:
        try:
            await asyncio.sleep(HISTORY_CLEANUP_INTERVAL)
            
            logger.info("🧹 Running scheduled cleanup...")
            
            history_cleaned = await chat_history_manager.cleanup_old_data()
            rate_cleaned = await rate_limiter.cleanup()
            model_cleaned = cleanup_user_model_preferences()
            
            if AI_SERVICE_AVAILABLE and ai_service:
                try:
                    ai_service.save_stats()
                except Exception:
                    pass
            
            logger.info(f"🧹 Cleanup: history={history_cleaned}, rate={rate_cleaned}, models={model_cleaned}")
            
        except asyncio.CancelledError:
            logger.info("🧹 Cleanup loop cancelled")
            break
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
            await asyncio.sleep(60)


def start_cleanup_task() -> asyncio.Task:
    """شروع تسک پاکسازی"""
    global _cleanup_task
    
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(cleanup_loop())
    
    return _cleanup_task


def stop_cleanup_task() -> None:
    """توقف تسک پاکسازی"""
    global _cleanup_task
    
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۳۳: هوک‌های راه‌اندازی و توقف
# ═══════════════════════════════════════════════════════════════════════════════

async def on_startup() -> None:
    """
    اجرا در زمان راه‌اندازی بات
    
    این تابع باید از main.py فراخوانی شود:
        from handlers.ai_handler import on_startup
        await on_startup()
    """
    logger.info("🚀 AI Handler starting up...")
    
    # شروع تسک پاکسازی
    start_cleanup_task()
    
    # شروع Keep-Alive
    if KEEP_ALIVE_ENABLED:
        await service_manager.start_keep_alive()
    
    # Warm-up اولیه
    if WARMUP_ENABLED and AI_SERVICE_AVAILABLE:
        logger.info("🔥 Performing initial warmup...")
        try:
            success = await service_manager.warmup(force=True)
            if success:
                metrics.record_warmup()
                logger.success("✅ Initial warmup successful")
            else:
                logger.warning("⚠️ Initial warmup failed")
        except Exception as e:
            logger.error(f"❌ Warmup error: {e}")
    
    # بررسی سرویس
    if AI_SERVICE_AVAILABLE and ai_service:
        try:
            status = ai_service.get_status()
            logger.info(f"🤖 AI Service: {status.get('status', 'unknown')}")
            logger.info(f"🤖 Models: {status.get('active_models', 0)}")
        except Exception as e:
            logger.warning(f"⚠️ Could not check AI: {e}")
    
    logger.success("✅ AI Handler started")


async def on_shutdown() -> None:
    """
    اجرا در زمان توقف بات
    
    این تابع باید از main.py فراخوانی شود:
        from handlers.ai_handler import on_shutdown
        await on_shutdown()
    """
    logger.info("🛑 AI Handler shutting down...")
    
    stop_cleanup_task()
    
    await service_manager.stop_keep_alive()
    
    if AI_SERVICE_AVAILABLE and ai_service:
        try:
            ai_service.save_stats()
        except Exception:
            pass
    
    logger.info(f"📊 Final metrics: {metrics.to_dict()}")
    
    logger.success("✅ AI Handler stopped")


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۳۴: تابع کمکی ثبت روتر
# ═══════════════════════════════════════════════════════════════════════════════

def setup_router(parent_router) -> Router:
    """ثبت روتر AI در روتر اصلی"""
    parent_router.include_router(router)
    logger.info("📎 AI Router registered")
    return router


def get_router() -> Router:
    """دریافت روتر AI"""
    return router


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۳۵: لاگ نهایی و Export
# ═══════════════════════════════════════════════════════════════════════════════

logger.success("═" * 60)
logger.success("🤖 AI Handler v7.0 - Fully Loaded!")
logger.success("═" * 60)
logger.info(f"   📦 Router: {router.name}")
logger.info(f"   🤖 AI Service: {'✅' if AI_SERVICE_AVAILABLE else '❌'}")
logger.info(f"   🌐 Lang Service: {'✅' if LANG_SERVICE_AVAILABLE else '❌'}")
logger.info(f"   💾 Database: {'✅' if DATABASE_AVAILABLE else '❌'}")
logger.info(f"   🎤 Voice: {'✅' if VOICE_ENABLED else '❌'}")
logger.info(f"   🖼️ Image: {'✅' if IMAGE_ENABLED else '❌'}")
logger.info(f"   💬 History: {'✅' if HISTORY_ENABLED else '❌'}")
logger.info(f"   🔥 Warmup: {'✅' if WARMUP_ENABLED else '❌'}")
logger.info(f"   💓 Keep-Alive: {'✅' if KEEP_ALIVE_ENABLED else '❌'}")
logger.info(f"   🤖 Default Model: {DEFAULT_MODEL}")
logger.info(f"   📊 Models Available: {len(USER_SELECTABLE_MODELS)}")
logger.success("═" * 60)


# ═══════════════════════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Router
    "router",
    "get_router",
    "setup_router",
    
    # States
    "AIStates",
    
    # کلاس‌ها
    "AIMetrics",
    "ChatHistoryManager",
    "RateLimiter",
    "AIServiceManager",
    "ServiceHealth",
    
    # نمونه‌های سراسری
    "metrics",
    "chat_history_manager",
    "rate_limiter",
    "service_manager",
    
    # توابع اصلی
    "chat_with_history",
    
    # توابع کمکی
    "safe_answer",
    "safe_edit_text",
    "safe_delete_message",
    "safe_answer_callback",
    "keep_typing",
    "get_user_language",
    "is_admin",
    "get_user_model",
    "set_user_model",
    
    # Context Managers
    "ai_processing_context",
    "callback_processing_context",
    
    # فرمت‌دهی
    "format_ai_response",
    "format_translation_response",
    "format_italian_help_response",
    "create_error_response",
    
    # پیام‌ها
    "get_msg",
    "get_random_emoji",
    "MESSAGES",
    
    # کیبوردها
    "get_ai_menu_keyboard",
    "get_chat_keyboard",
    "get_chat_with_model_keyboard",
    "get_translate_menu_keyboard",
    "get_translation_result_keyboard",
    "get_italian_help_keyboard",
    "get_quick_questions_keyboard",
    "get_back_keyboard",
    "get_cancel_keyboard",
    "get_stats_keyboard",
    "get_model_selection_keyboard",
    "get_voice_result_keyboard",
    "get_image_result_keyboard",
    
    # هوک‌ها
    "on_startup",
    "on_shutdown",
    
    # تسک‌ها
    "start_cleanup_task",
    "stop_cleanup_task",
    
    # ثابت‌ها
    "AI_SERVICE_AVAILABLE",
    "LANG_SERVICE_AVAILABLE",
    "DATABASE_AVAILABLE",
    "VOICE_ENABLED",
    "IMAGE_ENABLED",
    "HISTORY_ENABLED",
    "WARMUP_ENABLED",
    "KEEP_ALIVE_ENABLED",
    "DEFAULT_MODEL",
    "USER_SELECTABLE_MODELS",
    "QUICK_QUESTIONS",
]

@router.message(AIStates.chatting, F.document)
async def handle_document(message: types.Message, state: FSMContext, bot: Bot):
    """دریافت فایل و پردازش با هوش مصنوعی (فقط اگر کاربر در حال گفتگو با هوش مصنوعی باشد)"""
        
    user_id = message.from_user.id
    doc = message.document
    
    if not doc.file_name.lower().endswith('.pdf'):
        await message.answer("⚠️ لطفاً فقط فایل‌های PDF ارسال کنید.")
        return
        
    loading = await message.answer("📄 در حال خواندن محتوای فایل PDF...")
    try:
        file = await bot.get_file(doc.file_id)
        file_bytes = await bot.download_file(file.file_path)
        
        reader = PdfReader(file_bytes)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
                
        if not text.strip():
            await loading.edit_text("⚠️ متنی در این PDF یافت نشد (شاید عکس باشد).")
            return
            
        await loading.edit_text("🧠 در حال تحلیل محتوا توسط هوش مصنوعی...")
        
        # limit text to avoid huge context length issues
        text = text[:15000]
        
        prompt = f"متن زیر را بخوان و خلاصه‌ای از نکات مهم آن را به زبان فارسی ساده بگو. اگر فایل قانونی، بورس یا قرارداد است نکات کلیدی و هشدارهای مهم آن را حتما ذکر کن:\n\n{text}"
        
        from services.ai_service import ai_service
        response = await ai_service.chat(prompt, user_id=user_id, context="student_assistant")
        
        await loading.edit_text(response.text)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        await loading.edit_text(f"⚠️ خطا در پردازش فایل: {e}")
