# handlers/ai_handler.py
# هندلر کامل هوش مصنوعی - نسخه ۴.۰ (Final Production)
# ژانویه ۲۰۲۵

"""
🤖 هندلر هوشمند SmartStudentBot - نسخه نهایی
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
نسخه ۴.۰ شامل:
    ✅ رفع باگ safe_answer
    ✅ Context Manager برای کاهش کد تکراری
    ✅ سیستم Metrics برای مانیتورینگ
    ✅ Cleanup Task برای جلوگیری از نشت حافظه
    ✅ ChatHistoryManager با قابلیت دیتابیس
    ✅ سیستم چندزبانه (i18n)
    ✅ Retry Mechanism هوشمند
    ✅ Continuous Typing
    ✅ مدیریت کامل خطاها و Timeout
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱: ایمپورت‌ها
# ═══════════════════════════════════════════════════════════════════════════════

# کتابخانه‌های استاندارد
import asyncio
import random
import traceback
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from contextlib import suppress, asynccontextmanager
from dataclasses import dataclass, field
from typing import (
    Dict, 
    List, 
    Optional, 
    Any, 
    Tuple, 
    Callable, 
    AsyncGenerator,
    TypeVar,
    Union
)
from enum import Enum

# کتابخانه‌های شخص ثالث
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

try:
    from services.ai_service import ai_service, AVAILABLE_MODELS, AIResponse
    AI_SERVICE_AVAILABLE = True
    logger.info("✅ AI Service imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ AI Service not available: {e}")
    AI_SERVICE_AVAILABLE = False
    ai_service = None
    AVAILABLE_MODELS = []
    
    # کلاس جایگزین برای جلوگیری از کرش
    @dataclass
    class AIResponse:
        """کلاس Fallback برای پاسخ AI"""
        text: str = "سرویس AI در دسترس نیست."
        is_ai_generated: bool = False
        model_used: Optional[str] = None
        processing_time_ms: int = 0
        from_cache: bool = False
        error: Optional[str] = None
        
        @classmethod
        def error_response(cls, message: str) -> 'AIResponse':
            """ایجاد پاسخ خطا"""
            return cls(text=message, error=message)


# ایمپورت توابع زبان (اختیاری)
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


# ایمپورت دیتابیس (اختیاری - برای تاریخچه)
try:
    from database import db
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    db = None


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۳: تنظیمات و ثابت‌های پیکربندی
# ═══════════════════════════════════════════════════════════════════════════════

# راه‌اندازی Router
router = Router()
router.name = "ai_handler"

# ═══════════════════════════════════════════════════════════════════════════════
# تنظیمات Rate Limiting
# ═══════════════════════════════════════════════════════════════════════════════
RATE_LIMIT_MESSAGES = 10          # حداکثر پیام در بازه زمانی
RATE_LIMIT_WINDOW = 60            # بازه زمانی (ثانیه)
RATE_LIMIT_PREMIUM_MULTIPLIER = 2 # ضریب برای کاربران ویژه

# ═══════════════════════════════════════════════════════════════════════════════
# تنظیمات تاریخچه چت
# ═══════════════════════════════════════════════════════════════════════════════
MAX_CHAT_HISTORY = 10             # حداکثر پیام در تاریخچه
HISTORY_CLEANUP_INTERVAL = 3600   # فاصله پاکسازی (ثانیه)
HISTORY_MAX_AGE_HOURS = 24        # حداکثر عمر تاریخچه (ساعت)

# ═══════════════════════════════════════════════════════════════════════════════
# تنظیمات Timeout و Retry
# ═══════════════════════════════════════════════════════════════════════════════
AI_TIMEOUT_SECONDS = 30           # حداکثر زمان انتظار
AI_RETRY_ATTEMPTS = 3             # تعداد تلاش مجدد
AI_RETRY_DELAY_BASE = 1           # تأخیر پایه بین تلاش‌ها (ثانیه)
AI_RETRY_DELAY_MAX = 10           # حداکثر تأخیر (ثانیه)
TYPING_INTERVAL = 4               # فاصله ارسال typing (ثانیه)

# ═══════════════════════════════════════════════════════════════════════════════
# تنظیمات Metrics
# ═══════════════════════════════════════════════════════════════════════════════
METRICS_MAX_POPULAR_QUESTIONS = 100  # حداکثر سوالات پرتکرار ذخیره شده
METRICS_RESPONSE_TIME_SAMPLES = 100  # نمونه‌های زمان پاسخ


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۴: سیستم چندزبانه (i18n)
# ═══════════════════════════════════════════════════════════════════════════════

class Language(Enum):
    """زبان‌های پشتیبانی شده"""
    FA = "fa"
    EN = "en"
    IT = "it"


MESSAGES: Dict[str, Dict[str, Any]] = {
    "fa": {
        # پیام‌های در حال پردازش
        "thinking": [
            "🧠 <i>دارم فکر می‌کنم...</i>",
            "🤔 <i>یه لحظه صبر کن...</i>",
            "💭 <i>در حال پردازش...</i>",
            "⚡ <i>دارم جواب رو آماده می‌کنم...</i>",
            "🔍 <i>دارم بررسی می‌کنم...</i>",
            "📚 <i>در حال جستجو...</i>",
        ],
        
        # پیام‌های خوشامدگویی
        "greeting": [
            "سلام! 👋 چطور می‌تونم کمکت کنم؟",
            "سلام دوست عزیز! 🌟 سوالت رو بپرس!",
            "هی! 😊 آماده‌ام کمکت کنم.",
            "درود! 🎓 هر سوالی داری بپرس.",
        ],
        
        # پیام‌های خطا
        "error": [
            "😅 یه مشکلی پیش اومد، دوباره امتحان کن!",
            "🔄 خطا در پردازش، لطفاً دوباره بفرست.",
            "⚠️ موقتاً مشکل داریم، یه کم صبر کن.",
        ],
        
        # پیام‌های خاص
        "rate_limit": "⏳ لطفاً {seconds} ثانیه صبر کنید.",
        "timeout": "⚠️ پاسخ‌دهی خیلی طول کشید. لطفاً دوباره تلاش کنید.",
        "service_unavailable": "⚠️ سرویس AI در حال حاضر در دسترس نیست.",
        "empty_message": "⚠️ لطفاً یک متن بنویسید!",
        "cancelled": "❌ لغو شد.",
        "chat_ended": "✅ چت پایان یافت.",
        "history_cleared": "🗑 {count} پیام پاک شد!",
        "send_word": "✍️ یک کلمه یا عبارت ایتالیایی بفرست:",
        "send_text": "✍️ متن خود را ارسال کنید:",
        "word_not_found": "❌ کلمه مشخص نیست. دوباره وارد کنید.",
        "no_access": "⛔ دسترسی ندارید!",
        
        # عناوین منو
        "menu_title": "🤖 <b>دستیار هوشمند پروجا</b>",
        "chat_title": "💬 <b>چت با دستیار هوشمند</b>",
        "translate_title": "🌐 <b>ترجمه هوشمند</b>",
        "italian_title": "🇮🇹 <b>کمک یادگیری ایتالیایی</b>",
        "stats_title": "📊 <b>وضعیت سرویس AI</b>",
        "quick_title": "⚡ <b>سوالات پرتکرار</b>",
        
        # دکمه‌ها
        "btn_start_chat": "💬 شروع چت با AI",
        "btn_translate": "🌐 ترجمه متن",
        "btn_italian": "🇮🇹 کمک ایتالیایی",
        "btn_quick": "⚡ سوالات پرتکرار",
        "btn_stats": "📊 وضعیت سرویس",
        "btn_main_menu": "🏠 منوی اصلی",
        "btn_ai_menu": "🔙 منوی AI",
        "btn_end_chat": "❌ پایان چت",
        "btn_clear_history": "🗑 پاک کردن تاریخچه",
        "btn_refresh": "🔄 به‌روزرسانی",
        "btn_cancel": "❌ لغو",
        "btn_change_lang": "🔄 تغییر زبان",
        "btn_new_word": "🆕 کلمه جدید",
        "btn_another_translate": "🔄 ترجمه دیگر",
    },
    
    "en": {
        "thinking": [
            "🧠 <i>Thinking...</i>",
            "🤔 <i>Just a moment...</i>",
            "💭 <i>Processing...</i>",
            "⚡ <i>Preparing response...</i>",
            "🔍 <i>Checking...</i>",
        ],
        "greeting": [
            "Hello! 👋 How can I help you?",
            "Hi there! 🌟 Ask me anything!",
            "Hey! 😊 Ready to help.",
        ],
        "error": [
            "😅 Something went wrong, try again!",
            "🔄 Processing error, please resend.",
            "⚠️ Temporary issue, please wait.",
        ],
        "rate_limit": "⏳ Please wait {seconds} seconds.",
        "timeout": "⚠️ Response took too long. Please try again.",
        "service_unavailable": "⚠️ AI service is currently unavailable.",
        "empty_message": "⚠️ Please write something!",
        "cancelled": "❌ Cancelled.",
        "chat_ended": "✅ Chat ended.",
        "history_cleared": "🗑 {count} messages cleared!",
        "send_word": "✍️ Send an Italian word or phrase:",
        "send_text": "✍️ Send your text:",
        "word_not_found": "❌ Word not specified. Please enter again.",
        "no_access": "⛔ Access denied!",
        
        "menu_title": "🤖 <b>Perugia Smart Assistant</b>",
        "chat_title": "💬 <b>Chat with Smart Assistant</b>",
        "translate_title": "🌐 <b>Smart Translation</b>",
        "italian_title": "🇮🇹 <b>Italian Learning Helper</b>",
        "stats_title": "📊 <b>AI Service Status</b>",
        "quick_title": "⚡ <b>Quick Questions</b>",
        
        "btn_start_chat": "💬 Start Chat with AI",
        "btn_translate": "🌐 Translate Text",
        "btn_italian": "🇮🇹 Italian Help",
        "btn_quick": "⚡ Quick Questions",
        "btn_stats": "📊 Service Status",
        "btn_main_menu": "🏠 Main Menu",
        "btn_ai_menu": "🔙 AI Menu",
        "btn_end_chat": "❌ End Chat",
        "btn_clear_history": "🗑 Clear History",
        "btn_refresh": "🔄 Refresh",
        "btn_cancel": "❌ Cancel",
        "btn_change_lang": "🔄 Change Language",
        "btn_new_word": "🆕 New Word",
        "btn_another_translate": "🔄 Translate Another",
    },
    
    "it": {
        "thinking": [
            "🧠 <i>Sto pensando...</i>",
            "🤔 <i>Un momento...</i>",
            "💭 <i>Elaborazione...</i>",
        ],
        "greeting": [
            "Ciao! 👋 Come posso aiutarti?",
            "Ciao! 🌟 Chiedimi qualsiasi cosa!",
        ],
        "error": [
            "😅 Qualcosa è andato storto, riprova!",
        ],
        "rate_limit": "⏳ Per favore attendi {seconds} secondi.",
        "timeout": "⚠️ Risposta troppo lenta. Riprova.",
        "service_unavailable": "⚠️ Servizio AI non disponibile.",
        "empty_message": "⚠️ Per favore scrivi qualcosa!",
        "cancelled": "❌ Annullato.",
        "chat_ended": "✅ Chat terminata.",
        "history_cleared": "🗑 {count} messaggi cancellati!",
    }
}

# ایموجی‌های موفقیت
SUCCESS_EMOJIS = ["✨", "🎯", "💡", "🌟", "⭐", "🎉", "✅", "👍", "🚀", "💪"]


def get_msg(user_lang: str, key: str, **kwargs) -> str:
    """
    دریافت پیام براساس زبان کاربر
    
    Args:
        user_lang: کد زبان (fa, en, it)
        key: کلید پیام
        **kwargs: پارامترهای قالب‌بندی
        
    Returns:
        پیام ترجمه شده
    """
    # دریافت پیام از زبان کاربر، یا fallback به فارسی
    lang_messages = MESSAGES.get(user_lang, MESSAGES["fa"])
    msg = lang_messages.get(key)
    
    # اگر پیام در زبان کاربر نبود، از فارسی بگیر
    if msg is None:
        msg = MESSAGES["fa"].get(key, key)
    
    # اگر لیست بود، یکی را تصادفی انتخاب کن
    if isinstance(msg, list):
        msg = random.choice(msg)
    
    # قالب‌بندی با پارامترها
    if kwargs:
        try:
            msg = msg.format(**kwargs)
        except (KeyError, ValueError):
            pass
    
    return msg


def get_random_emoji() -> str:
    """انتخاب تصادفی ایموجی موفقیت"""
    return random.choice(SUCCESS_EMOJIS)


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۵: کلاس Metrics برای مانیتورینگ
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AIMetrics:
    """
    کلاس مدیریت آمار و متریک‌های سرویس AI
    
    Attributes:
        total_requests: تعداد کل درخواست‌ها
        successful_requests: درخواست‌های موفق
        failed_requests: درخواست‌های ناموفق
        timeout_requests: درخواست‌های تایم‌اوت شده
        cache_hits: تعداد برخورد با کش
        total_response_time_ms: مجموع زمان پاسخ‌دهی
        response_times: لیست زمان‌های پاسخ اخیر
        requests_per_user: تعداد درخواست هر کاربر
        popular_questions: سوالات پرتکرار
        errors_by_type: خطاها به تفکیک نوع
        started_at: زمان شروع
    """
    
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0
    cache_hits: int = 0
    total_response_time_ms: int = 0
    response_times: List[int] = field(default_factory=list)
    requests_per_user: Counter = field(default_factory=Counter)
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
        error_type: Optional[str] = None
    ) -> None:
        """
        ثبت یک درخواست جدید
        
        Args:
            user_id: شناسه کاربر
            question: متن سوال
            success: موفقیت‌آمیز بودن
            time_ms: زمان پردازش (میلی‌ثانیه)
            from_cache: آیا از کش بود
            error_type: نوع خطا (در صورت وجود)
        """
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
        
        # ذخیره زمان پاسخ (با محدودیت)
        self.response_times.append(time_ms)
        if len(self.response_times) > METRICS_RESPONSE_TIME_SAMPLES:
            self.response_times = self.response_times[-METRICS_RESPONSE_TIME_SAMPLES:]
        
        # ثبت تعداد درخواست کاربر
        self.requests_per_user[user_id] += 1
        
        # ثبت سوال پرتکرار (فقط ۵۰ کاراکتر اول)
        short_question = question[:50].strip()
        if short_question:
            self.popular_questions[short_question] += 1
            # محدود کردن تعداد سوالات ذخیره شده
            if len(self.popular_questions) > METRICS_MAX_POPULAR_QUESTIONS:
                # حذف کم‌تکرارترین‌ها
                self.popular_questions = Counter(
                    dict(self.popular_questions.most_common(METRICS_MAX_POPULAR_QUESTIONS // 2))
                )
    
    def record_timeout(self, user_id: int) -> None:
        """ثبت تایم‌اوت"""
        self.timeout_requests += 1
        self.failed_requests += 1
        self.total_requests += 1
        self.errors_by_type["timeout"] += 1
        self.requests_per_user[user_id] += 1
    
    @property
    def success_rate(self) -> float:
        """نرخ موفقیت (درصد)"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def avg_response_time_ms(self) -> float:
        """میانگین زمان پاسخ (میلی‌ثانیه)"""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    @property
    def cache_hit_rate(self) -> float:
        """نرخ برخورد با کش (درصد)"""
        if self.successful_requests == 0:
            return 0.0
        return (self.cache_hits / self.successful_requests) * 100
    
    @property
    def uptime(self) -> timedelta:
        """مدت زمان فعالیت"""
        return datetime.now() - self.started_at
    
    def get_top_users(self, limit: int = 10) -> List[Tuple[int, int]]:
        """کاربران پرمصرف"""
        return self.requests_per_user.most_common(limit)
    
    def get_top_questions(self, limit: int = 10) -> List[Tuple[str, int]]:
        """سوالات پرتکرار"""
        return self.popular_questions.most_common(limit)
    
    def get_error_summary(self) -> Dict[str, int]:
        """خلاصه خطاها"""
        return dict(self.errors_by_type)
    
    def to_dict(self) -> Dict[str, Any]:
        """تبدیل به دیکشنری"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "timeout_requests": self.timeout_requests,
            "cache_hits": self.cache_hits,
            "success_rate": f"{self.success_rate:.1f}%",
            "avg_response_time_ms": f"{self.avg_response_time_ms:.0f}",
            "cache_hit_rate": f"{self.cache_hit_rate:.1f}%",
            "uptime_hours": f"{self.uptime.total_seconds() / 3600:.1f}",
            "unique_users": len(self.requests_per_user),
        }
    
    def reset(self) -> Dict[str, Any]:
        """ریست آمار و برگرداندن آمار قبلی"""
        old_stats = self.to_dict()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.timeout_requests = 0
        self.cache_hits = 0
        self.total_response_time_ms = 0
        self.response_times = []
        self.requests_per_user = Counter()
        self.popular_questions = Counter()
        self.errors_by_type = Counter()
        self.started_at = datetime.now()
        return old_stats


# نمونه سراسری Metrics
metrics = AIMetrics()


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۶: مدیریت تاریخچه چت
# ═══════════════════════════════════════════════════════════════════════════════

class ChatHistoryManager:
    """
    مدیریت تاریخچه چت کاربران
    
    پشتیبانی از:
    - ذخیره در حافظه (پیش‌فرض)
    - ذخیره در دیتابیس (اختیاری)
    - پاکسازی خودکار داده‌های قدیمی
    """
    
    def __init__(self, use_database: bool = False):
        """
        مقداردهی اولیه
        
        Args:
            use_database: استفاده از دیتابیس به جای حافظه
        """
        self.use_database = use_database and DATABASE_AVAILABLE
        
        # ذخیره در حافظه
        self._memory_history: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        self._last_activity: Dict[int, datetime] = {}
    
    async def add(
        self, 
        user_id: int, 
        role: str, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        افزودن پیام به تاریخچه
        
        Args:
            user_id: شناسه کاربر
            role: نقش (user, assistant, system)
            content: محتوای پیام
            metadata: اطلاعات اضافی
        """
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        if self.use_database:
            await self._add_to_database(user_id, entry)
        else:
            self._add_to_memory(user_id, entry)
        
        self._last_activity[user_id] = datetime.now()
    
    def _add_to_memory(self, user_id: int, entry: Dict[str, Any]) -> None:
        """افزودن به حافظه"""
        self._memory_history[user_id].append(entry)
        
        # محدود کردن تعداد
        if len(self._memory_history[user_id]) > MAX_CHAT_HISTORY * 2:
            self._memory_history[user_id] = self._memory_history[user_id][-MAX_CHAT_HISTORY * 2:]
    
    async def _add_to_database(self, user_id: int, entry: Dict[str, Any]) -> None:
        """افزودن به دیتابیس"""
        if not db:
            self._add_to_memory(user_id, entry)
            return
        
        try:
            await db.execute(
                """
                INSERT INTO chat_history (user_id, role, content, metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id, 
                    entry["role"], 
                    entry["content"], 
                    str(entry.get("metadata", {})),
                    entry["timestamp"]
                )
            )
        except Exception as e:
            logger.error(f"❌ Database insert error: {e}")
            # Fallback به حافظه
            self._add_to_memory(user_id, entry)
    
    async def get(
        self, 
        user_id: int, 
        limit: int = MAX_CHAT_HISTORY
    ) -> List[Dict[str, str]]:
        """
        دریافت تاریخچه کاربر
        
        Args:
            user_id: شناسه کاربر
            limit: حداکثر تعداد پیام
            
        Returns:
            لیست پیام‌ها
        """
        if self.use_database:
            return await self._get_from_database(user_id, limit)
        else:
            return self._get_from_memory(user_id, limit)
    
    def _get_from_memory(self, user_id: int, limit: int) -> List[Dict[str, str]]:
        """دریافت از حافظه"""
        history = self._memory_history.get(user_id, [])
        # فقط role و content برگردان (برای API)
        return [{"role": h["role"], "content": h["content"]} for h in history[-limit:]]
    
    async def _get_from_database(self, user_id: int, limit: int) -> List[Dict[str, str]]:
        """دریافت از دیتابیس"""
        if not db:
            return self._get_from_memory(user_id, limit)
        
        try:
            rows = await db.fetch_all(
                """
                SELECT role, content FROM chat_history 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
                """,
                (user_id, limit)
            )
            return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        except Exception as e:
            logger.error(f"❌ Database fetch error: {e}")
            return self._get_from_memory(user_id, limit)
    
    async def clear(self, user_id: int) -> int:
        """
        پاک کردن تاریخچه کاربر
        
        Returns:
            تعداد پیام‌های پاک شده
        """
        if self.use_database:
            return await self._clear_from_database(user_id)
        else:
            return self._clear_from_memory(user_id)
    
    def _clear_from_memory(self, user_id: int) -> int:
        """پاک کردن از حافظه"""
        count = len(self._memory_history.get(user_id, []))
        self._memory_history[user_id] = []
        if user_id in self._last_activity:
            del self._last_activity[user_id]
        return count
    
    async def _clear_from_database(self, user_id: int) -> int:
        """پاک کردن از دیتابیس"""
        if not db:
            return self._clear_from_memory(user_id)
        
        try:
            result = await db.execute(
                "DELETE FROM chat_history WHERE user_id = ?",
                (user_id,)
            )
            self._clear_from_memory(user_id)  # پاک کردن کش محلی هم
            return result.rowcount if hasattr(result, 'rowcount') else 0
        except Exception as e:
            logger.error(f"❌ Database delete error: {e}")
            return self._clear_from_memory(user_id)
    
    async def cleanup_old_data(self) -> int:
        """
        پاکسازی داده‌های قدیمی
        
        Returns:
            تعداد کاربران پاک‌شده
        """
        cleaned = 0
        cutoff = datetime.now() - timedelta(hours=HISTORY_MAX_AGE_HOURS)
        
        # پاکسازی حافظه
        users_to_clean = [
            user_id for user_id, last_time in self._last_activity.items()
            if last_time < cutoff
        ]
        
        for user_id in users_to_clean:
            self._memory_history.pop(user_id, None)
            self._last_activity.pop(user_id, None)
            cleaned += 1
        
        # پاکسازی دیتابیس
        if self.use_database and db:
            try:
                await db.execute(
                    "DELETE FROM chat_history WHERE created_at < ?",
                    (cutoff.isoformat(),)
                )
            except Exception as e:
                logger.error(f"❌ Database cleanup error: {e}")
        
        if cleaned > 0:
            logger.info(f"🧹 Cleaned up history for {cleaned} users")
        
        return cleaned
    
    def get_stats(self) -> Dict[str, int]:
        """آمار تاریخچه"""
        total_messages = sum(len(h) for h in self._memory_history.values())
        return {
            "total_users": len(self._memory_history),
            "total_messages": total_messages,
            "active_users": len(self._last_activity),
        }


# نمونه سراسری ChatHistoryManager
chat_history_manager = ChatHistoryManager(use_database=DATABASE_AVAILABLE)


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۷: مدیریت Rate Limiting
# ═══════════════════════════════════════════════════════════════════════════════

class RateLimiter:
    """
    مدیریت محدودیت نرخ درخواست کاربران
    """
    
    def __init__(self):
        self._user_requests: Dict[int, List[datetime]] = defaultdict(list)
        self._premium_users: set = set()
    
    def add_premium_user(self, user_id: int) -> None:
        """افزودن کاربر ویژه"""
        self._premium_users.add(user_id)
    
    def remove_premium_user(self, user_id: int) -> None:
        """حذف کاربر ویژه"""
        self._premium_users.discard(user_id)
    
    def is_premium(self, user_id: int) -> bool:
        """آیا کاربر ویژه است"""
        return user_id in self._premium_users
    
    def check(self, user_id: int) -> Tuple[bool, int]:
        """
        بررسی محدودیت کاربر
        
        Args:
            user_id: شناسه کاربر
            
        Returns:
            (مجاز است, ثانیه‌های انتظار)
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW)
        
        # پاکسازی درخواست‌های قدیمی
        self._user_requests[user_id] = [
            t for t in self._user_requests[user_id] if t > window_start
        ]
        
        # محاسبه حد مجاز
        limit = RATE_LIMIT_MESSAGES
        if self.is_premium(user_id):
            limit *= RATE_LIMIT_PREMIUM_MULTIPLIER
        
        # بررسی محدودیت
        if len(self._user_requests[user_id]) >= limit:
            oldest = min(self._user_requests[user_id])
            wait = int((oldest + timedelta(seconds=RATE_LIMIT_WINDOW) - now).total_seconds())
            return False, max(0, wait)
        
        # ثبت درخواست جدید
        self._user_requests[user_id].append(now)
        return True, 0
    
    def get_remaining(self, user_id: int) -> int:
        """تعداد درخواست‌های باقیمانده"""
        now = datetime.now()
        window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW)
        
        recent = [t for t in self._user_requests.get(user_id, []) if t > window_start]
        
        limit = RATE_LIMIT_MESSAGES
        if self.is_premium(user_id):
            limit *= RATE_LIMIT_PREMIUM_MULTIPLIER
        
        return max(0, limit - len(recent))
    
    async def cleanup(self) -> int:
        """پاکسازی داده‌های قدیمی"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=RATE_LIMIT_WINDOW * 2)
        cleaned = 0
        
        users_to_clean = []
        for user_id, requests in self._user_requests.items():
            if all(t < cutoff for t in requests):
                users_to_clean.append(user_id)
        
        for user_id in users_to_clean:
            del self._user_requests[user_id]
            cleaned += 1
        
        return cleaned


# نمونه سراسری RateLimiter
rate_limiter = RateLimiter()


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۸: سوالات پرتکرار
# ═══════════════════════════════════════════════════════════════════════════════

QUICK_QUESTIONS: Dict[str, Dict[str, str]] = {
    "scholarship": {
        "fa": "شرایط و مراحل دریافت بورسیه DSU چیست؟ چه مدارکی لازم است؟",
        "en": "What are the requirements and steps for DSU scholarship? What documents are needed?",
        "it": "Quali sono i requisiti e i passaggi per la borsa di studio DSU?",
    },
    "permesso": {
        "fa": "مراحل گرفتن پرمسو (اجازه اقامت) در ایتالیا چیست؟",
        "en": "What are the steps to get a permesso (residence permit) in Italy?",
        "it": "Quali sono i passaggi per ottenere il permesso di soggiorno in Italia?",
    },
    "cost": {
        "fa": "هزینه ماهانه زندگی دانشجویی در پروجا چقدر است؟ (اجاره، غذا، ...)",
        "en": "What is the monthly cost of student life in Perugia? (rent, food, ...)",
        "it": "Qual è il costo mensile della vita studentesca a Perugia?",
    },
    "housing": {
        "fa": "چطور در پروجا خانه یا اتاق پیدا کنم؟ سایت‌های معتبر کدامند؟",
        "en": "How to find a house or room in Perugia? What are reliable websites?",
        "it": "Come trovare una casa o una stanza a Perugia? Quali sono i siti affidabili?",
    },
    "isee": {
        "fa": "ISEE چیست و چطور محاسبه می‌شود؟ چرا برای بورسیه مهم است؟",
        "en": "What is ISEE and how is it calculated? Why is it important for scholarships?",
        "it": "Cos'è l'ISEE e come si calcola? Perché è importante per le borse di studio?",
    },
    "codice_fiscale": {
        "fa": "کد فیسکاله (Codice Fiscale) چیست و چطور دریافت کنم؟",
        "en": "What is Codice Fiscale and how to get it?",
        "it": "Cos'è il Codice Fiscale e come ottenerlo?",
    },
    "university": {
        "fa": "ثبت‌نام در دانشگاه پروجا چگونه است؟ مدارک لازم کدامند؟",
        "en": "How to enroll at the University of Perugia? What documents are needed?",
        "it": "Come iscriversi all'Università di Perugia? Quali documenti servono?",
    },
}


def get_quick_question(key: str, lang: str = "fa") -> str:
    """دریافت متن سوال سریع"""
    question_data = QUICK_QUESTIONS.get(key, {})
    return question_data.get(lang, question_data.get("fa", ""))


# ═══════════════════════════════════════════════════════════════════════════════
# پایان بخش ۱
# ═══════════════════════════════════════════════════════════════════════════════

logger.info("📦 AI Handler v4.0 - Part 1 loaded (Imports, Config, Classes)")
# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۹: States (وضعیت‌های FSM)
# ═══════════════════════════════════════════════════════════════════════════════

class AIStates(StatesGroup):
    """
    وضعیت‌های مختلف تعامل کاربر با AI
    
    States:
        chatting: در حال چت آزاد
        waiting_for_translation: منتظر متن برای ترجمه
        waiting_for_italian_word: منتظر کلمه ایتالیایی
        selecting_help_type: انتخاب نوع کمک
        waiting_for_feedback: منتظر بازخورد کاربر
    """
    chatting = State()
    waiting_for_translation = State()
    waiting_for_italian_word = State()
    selecting_help_type = State()
    waiting_for_feedback = State()


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۰: توابع کمکی پایه (Base Helpers)
# ═══════════════════════════════════════════════════════════════════════════════

async def safe_answer(
    message: Message, 
    text: str, 
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: ParseMode = ParseMode.HTML,
    **kwargs
) -> Optional[Message]:
    """
    ارسال ایمن پیام جدید
    
    Args:
        message: پیام اصلی برای پاسخ دادن
        text: متن پیام
        reply_markup: کیبورد (اختیاری)
        parse_mode: نوع پارس (پیش‌فرض HTML)
        **kwargs: پارامترهای اضافی
        
    Returns:
        پیام ارسال شده یا None در صورت خطا
    """
    try:
        return await message.answer(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            **kwargs
        )
    except TelegramBadRequest as e:
        logger.warning(f"⚠️ safe_answer TelegramBadRequest: {e}")
        # تلاش بدون parse_mode
        try:
            return await message.answer(
                text=text.replace("<b>", "").replace("</b>", "")
                        .replace("<i>", "").replace("</i>", "")
                        .replace("<code>", "").replace("</code>", ""),
                reply_markup=reply_markup,
                **kwargs
            )
        except Exception:
            return None
    except TelegramNetworkError as e:
        logger.error(f"❌ safe_answer NetworkError: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ safe_answer unexpected error: {e}")
        return None


async def safe_edit_text(
    message: Message, 
    text: str, 
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: ParseMode = ParseMode.HTML,
    disable_web_page_preview: bool = True
) -> bool:
    """
    ویرایش ایمن پیام
    
    Args:
        message: پیام برای ویرایش
        text: متن جدید
        reply_markup: کیبورد جدید (اختیاری)
        parse_mode: نوع پارس
        disable_web_page_preview: غیرفعال کردن پیش‌نمایش لینک
        
    Returns:
        True در صورت موفقیت
    """
    try:
        await message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview
        )
        return True
    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        # این خطاها قابل چشم‌پوشی هستند
        if "message is not modified" in error_msg:
            return True
        if "message to edit not found" in error_msg:
            logger.warning("⚠️ Message to edit not found")
            return False
        if "message can't be edited" in error_msg:
            logger.warning("⚠️ Message can't be edited")
            return False
        logger.error(f"❌ safe_edit_text error: {e}")
        return False
    except TelegramNetworkError as e:
        logger.error(f"❌ safe_edit_text NetworkError: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ safe_edit_text unexpected error: {e}")
        return False


async def safe_delete_message(message: Message) -> bool:
    """
    حذف ایمن پیام
    
    Returns:
        True در صورت موفقیت
    """
    try:
        await message.delete()
        return True
    except TelegramBadRequest:
        return False
    except Exception as e:
        logger.error(f"❌ safe_delete_message error: {e}")
        return False


async def safe_answer_callback(
    callback: CallbackQuery, 
    text: str = "", 
    show_alert: bool = False
) -> bool:
    """
    پاسخ ایمن به callback query
    
    Returns:
        True در صورت موفقیت
    """
    try:
        await callback.answer(text=text, show_alert=show_alert)
        return True
    except TelegramBadRequest:
        return True  # احتمالاً قبلاً پاسخ داده شده
    except Exception as e:
        logger.error(f"❌ safe_answer_callback error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۱: توابع کمکی Typing و Timeout
# ═══════════════════════════════════════════════════════════════════════════════

async def keep_typing(bot: Bot, chat_id: int) -> None:
    """
    ارسال مداوم وضعیت Typing
    
    تلگرام وضعیت تایپینگ را فقط ۵ ثانیه نگه می‌دارد.
    این تابع هر ۴ ثانیه آن را تمدید می‌کند.
    
    Note:
        این تابع باید به عنوان asyncio.Task اجرا شود و
        در پایان کار cancel شود.
    
    Args:
        bot: نمونه بات تلگرام
        chat_id: شناسه چت
    """
    try:
        while True:
            try:
                await bot.send_chat_action(chat_id, ChatAction.TYPING)
            except TelegramNetworkError:
                pass  # ادامه بده حتی اگر شبکه مشکل داشت
            except TelegramBadRequest:
                break  # چت دیگر وجود ندارد
            await asyncio.sleep(TYPING_INTERVAL)
    except asyncio.CancelledError:
        pass  # تسک کنسل شد (طبیعی)
    except Exception as e:
        logger.error(f"❌ Error in keep_typing: {e}")


async def call_ai_with_timeout(
    func: Callable,
    *args,
    timeout: int = AI_TIMEOUT_SECONDS,
    **kwargs
) -> Optional[Any]:
    """
    فراخوانی تابع AI با مدیریت Timeout
    
    Args:
        func: تابع async برای فراخوانی
        *args: آرگومان‌های تابع
        timeout: حداکثر زمان انتظار (ثانیه)
        **kwargs: آرگومان‌های کلیدی تابع
        
    Returns:
        نتیجه تابع یا None در صورت timeout/خطا
    """
    try:
        logger.debug(f"🤖 Calling AI function with timeout={timeout}s")
        start_time = datetime.now()
        
        result = await asyncio.wait_for(
            func(*args, **kwargs), 
            timeout=timeout
        )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ AI responded in {elapsed:.2f}s")
        
        return result
        
    except asyncio.TimeoutError:
        logger.error(f"⏰ AI timeout after {timeout}s!")
        return None
    except Exception as e:
        logger.error(f"❌ AI call error: {e}")
        logger.debug(traceback.format_exc())
        return None


async def call_ai_with_retry(
    func: Callable,
    *args,
    max_attempts: int = AI_RETRY_ATTEMPTS,
    timeout: int = AI_TIMEOUT_SECONDS,
    **kwargs
) -> Optional[Any]:
    """
    فراخوانی تابع AI با Retry خودکار
    
    Args:
        func: تابع async برای فراخوانی
        *args: آرگومان‌های تابع
        max_attempts: حداکثر تعداد تلاش
        timeout: حداکثر زمان هر تلاش
        **kwargs: آرگومان‌های کلیدی تابع
        
    Returns:
        نتیجه تابع یا None در صورت شکست همه تلاش‌ها
    """
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.debug(f"🔄 AI call attempt {attempt}/{max_attempts}")
            
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout
            )
            
            if result is not None:
                if attempt > 1:
                    logger.info(f"✅ AI succeeded on attempt {attempt}")
                return result
                
        except asyncio.TimeoutError:
            last_error = "timeout"
            logger.warning(f"⏰ Attempt {attempt} timed out")
            
        except Exception as e:
            last_error = str(e)
            logger.warning(f"❌ Attempt {attempt} failed: {e}")
        
        # تأخیر قبل از تلاش بعدی (exponential backoff)
        if attempt < max_attempts:
            delay = min(
                AI_RETRY_DELAY_BASE * (2 ** (attempt - 1)),
                AI_RETRY_DELAY_MAX
            )
            logger.debug(f"⏳ Waiting {delay}s before retry...")
            await asyncio.sleep(delay)
    
    logger.error(f"❌ All {max_attempts} attempts failed. Last error: {last_error}")
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۲: Context Manager برای پردازش AI
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def ai_processing_context(
    bot: Bot,
    chat_id: int,
    message: Message,
    user_lang: str = "fa",
    thinking_text: Optional[str] = None,
    show_keyboard: bool = False,
    keyboard: Optional[InlineKeyboardMarkup] = None
) -> AsyncGenerator[Tuple[Message, datetime], None]:
    """
    Context Manager برای پردازش‌های AI
    
    این context manager:
    - پیام "در حال فکر کردن" نمایش می‌دهد
    - Typing loop را مدیریت می‌کند
    - در پایان typing را متوقف می‌کند
    - زمان شروع را برمی‌گرداند
    
    Usage:
        async with ai_processing_context(bot, chat_id, message) as (thinking_msg, start_time):
            response = await call_ai_with_timeout(...)
            elapsed = (datetime.now() - start_time).total_seconds()
            await safe_edit_text(thinking_msg, response.text)
    
    Args:
        bot: نمونه بات
        chat_id: شناسه چت
        message: پیام کاربر
        user_lang: زبان کاربر
        thinking_text: متن سفارشی (اختیاری)
        show_keyboard: نمایش کیبورد در پیام اولیه
        keyboard: کیبورد سفارشی
        
    Yields:
        (پیام thinking, زمان شروع)
    """
    # متن پیش‌فرض
    if thinking_text is None:
        thinking_text = get_msg(user_lang, "thinking")
    
    start_time = datetime.now()
    typing_task = None
    thinking_msg = None
    
    try:
        # ارسال پیام اولیه
        thinking_msg = await safe_answer(
            message,
            thinking_text,
            reply_markup=keyboard if show_keyboard else None
        )
        
        # اگر ارسال ناموفق بود، از پیام اصلی استفاده کن
        if thinking_msg is None:
            thinking_msg = message
        
        # شروع typing loop
        typing_task = asyncio.create_task(keep_typing(bot, chat_id))
        
        yield thinking_msg, start_time
        
    finally:
        # حتماً typing task را متوقف کن
        if typing_task is not None:
            typing_task.cancel()
            with suppress(asyncio.CancelledError):
                await typing_task


@asynccontextmanager
async def callback_processing_context(
    callback: CallbackQuery,
    user_lang: str = "fa",
    thinking_text: Optional[str] = None,
    answer_text: str = "⏳"
) -> AsyncGenerator[Tuple[Message, datetime], None]:
    """
    Context Manager برای پردازش callback های AI
    
    مشابه ai_processing_context اما برای callback ها
    
    Args:
        callback: callback query
        user_lang: زبان کاربر
        thinking_text: متن سفارشی
        answer_text: متن پاسخ سریع callback
        
    Yields:
        (پیام برای ویرایش, زمان شروع)
    """
    if thinking_text is None:
        thinking_text = get_msg(user_lang, "thinking")
    
    start_time = datetime.now()
    typing_task = None
    
    try:
        # پاسخ سریع به callback
        await safe_answer_callback(callback, answer_text)
        
        # ویرایش پیام موجود
        await safe_edit_text(callback.message, thinking_text)
        
        # شروع typing loop
        typing_task = asyncio.create_task(
            keep_typing(callback.bot, callback.message.chat.id)
        )
        
        yield callback.message, start_time
        
    finally:
        if typing_task is not None:
            typing_task.cancel()
            with suppress(asyncio.CancelledError):
                await typing_task


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۳: توابع کمکی Response
# ═══════════════════════════════════════════════════════════════════════════════

def create_error_response(
    message: Optional[str] = None,
    user_lang: str = "fa"
) -> AIResponse:
    """
    ایجاد پاسخ خطای استاندارد
    
    Args:
        message: پیام سفارشی (اختیاری)
        user_lang: زبان کاربر
        
    Returns:
        AIResponse با پیام خطا
    """
    error_text = message or get_msg(user_lang, "error")
    
    if AI_SERVICE_AVAILABLE:
        return AIResponse(
            text=error_text,
            is_ai_generated=False,
            model_used=None,
            processing_time_ms=0,
            from_cache=False,
            error=error_text
        )
    else:
        response = AIResponse()
        response.text = error_text
        response.error = error_text
        return response


def format_ai_response(
    response: AIResponse,
    user_lang: str = "fa",
    include_metadata: bool = True,
    question: Optional[str] = None
) -> str:
    """
    فرمت‌دهی پاسخ AI برای نمایش
    
    Args:
        response: پاسخ AI
        user_lang: زبان کاربر
        include_metadata: شامل اطلاعات متا
        question: سوال اصلی (اختیاری)
        
    Returns:
        متن فرمت‌شده
    """
    emoji = get_random_emoji()
    text_parts = []
    
    # نمایش سوال (اگر موجود بود)
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
        
        # زمان پردازش
        time_info = f"⏱ {response.processing_time_ms}ms"
        
        text_parts.append(f"\n<i>{source} | {time_info}</i>")
    
    return "".join(text_parts)


def format_translation_response(
    response: AIResponse,
    source_lang: str,
    target_lang: str,
    original_text: Optional[str] = None,
    user_lang: str = "fa"
) -> str:
    """
    فرمت‌دهی پاسخ ترجمه
    
    Args:
        response: پاسخ AI
        source_lang: زبان مبدأ
        target_lang: زبان مقصد
        original_text: متن اصلی (اختیاری)
        user_lang: زبان کاربر
        
    Returns:
        متن فرمت‌شده
    """
    lang_flags = {
        "fa": "🇮🇷",
        "en": "🇬🇧", 
        "it": "🇮🇹",
        "auto": "🔮"
    }
    
    emoji = get_random_emoji()
    text_parts = []
    
    # عنوان
    src_flag = lang_flags.get(source_lang, "🌐")
    tgt_flag = lang_flags.get(target_lang, "🌐")
    text_parts.append(f"🌐 <b>ترجمه {src_flag} → {tgt_flag}</b>\n\n")
    
    # متن اصلی
    if original_text:
        text_parts.append(f"📝 <b>متن اصلی:</b>\n{original_text}\n\n")
        text_parts.append("━━━━━━━━━━━━━━━━━━━━━\n\n")
    
    # ترجمه
    text_parts.append(f"{emoji} <b>ترجمه:</b>\n\n{response.text}")
    
    # متادیتا
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
    """
    فرمت‌دهی پاسخ کمک ایتالیایی
    
    Args:
        response: پاسخ AI
        word: کلمه ایتالیایی
        help_type: نوع کمک
        user_lang: زبان کاربر
        
    Returns:
        متن فرمت‌شده
    """
    help_type_names = {
        "meaning": "معنی",
        "example": "مثال",
        "conjugate": "صرف فعل",
        "pronunciation": "تلفظ"
    }
    
    emoji = get_random_emoji()
    type_name = help_type_names.get(help_type, help_type)
    
    text_parts = [
        f"🇮🇹 <b>{word}</b>\n",
        f"<i>{type_name.upper()}</i>\n\n",
        "━━━━━━━━━━━━━━━━━━━━━\n\n",
        f"{emoji} {response.text}\n\n",
        "━━━━━━━━━━━━━━━━━━━━━\n",
    ]
    
    source = "🤖 AI" if response.is_ai_generated else "📖"
    text_parts.append(f"<i>{source} | ⏱ {response.processing_time_ms}ms</i>")
    
    return "".join(text_parts)


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۴: توابع دریافت زبان کاربر
# ═══════════════════════════════════════════════════════════════════════════════

async def get_user_language(
    user_id: int, 
    state: Optional[FSMContext] = None
) -> str:
    """
    دریافت زبان کاربر
    
    Args:
        user_id: شناسه کاربر
        state: FSM context (اختیاری)
        
    Returns:
        کد زبان (fa, en, it)
    """
    # اول از state بخوان
    if state:
        try:
            data = await state.get_data()
            if "language" in data:
                return data["language"]
        except Exception:
            pass
    
    # سپس از سرویس زبان
    if LANG_SERVICE_AVAILABLE:
        try:
            lang_data = get_user_lang(user_id)
            return lang_data.get("code", "fa")
        except Exception:
            pass
    
    return "fa"


def is_admin(user_id: int) -> bool:
    """
    بررسی ادمین بودن کاربر
    
    Args:
        user_id: شناسه کاربر
        
    Returns:
        True اگر ادمین باشد
    """
    return user_id in settings.ADMIN_CHAT_IDS


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۵: کیبوردها (Keyboards)
# ═══════════════════════════════════════════════════════════════════════════════

def get_ai_menu_keyboard(user_lang: str = "fa") -> InlineKeyboardMarkup:
    """
    کیبورد منوی اصلی AI
    
    Args:
        user_lang: زبان کاربر
        
    Returns:
        InlineKeyboardMarkup
    """
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
    """
    کیبورد حین چت
    
    Args:
        user_lang: زبان کاربر
        
    Returns:
        InlineKeyboardMarkup
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎓 بورسیه", callback_data="ai:q_scholarship"),
            InlineKeyboardButton(text="🛂 پرمسو", callback_data="ai:q_permesso"),
        ],
        [
            InlineKeyboardButton(text="💰 هزینه", callback_data="ai:q_cost"),
            InlineKeyboardButton(text="🏠 مسکن", callback_data="ai:q_housing"),
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
    ])


def get_translate_menu_keyboard(user_lang: str = "fa") -> InlineKeyboardMarkup:
    """
    کیبورد منوی ترجمه
    
    Args:
        user_lang: زبان کاربر
        
    Returns:
        InlineKeyboardMarkup
    """
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
    """
    کیبورد نتیجه ترجمه
    
    Args:
        source_lang: زبان مبدأ
        target_lang: زبان مقصد
        user_lang: زبان کاربر
        
    Returns:
        InlineKeyboardMarkup
    """
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


def get_italian_help_keyboard(
    word: str,
    user_lang: str = "fa"
) -> InlineKeyboardMarkup:
    """
    کیبورد کمک ایتالیایی
    
    Args:
        word: کلمه ایتالیایی
        user_lang: زبان کاربر
        
    Returns:
        InlineKeyboardMarkup
    """
    # محدود کردن طول کلمه برای callback_data
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
    """
    کیبورد بازگشت ساده
    
    Args:
        user_lang: زبان کاربر
        
    Returns:
        InlineKeyboardMarkup
    """
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
    """
    کیبورد لغو
    
    Args:
        user_lang: زبان کاربر
        
    Returns:
        InlineKeyboardMarkup
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_change_lang"),
                callback_data="ai:translate_menu"
            ),
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_cancel"),
                callback_data="ai:menu"
            )
        ]
    ])


def get_quick_questions_keyboard(user_lang: str = "fa") -> InlineKeyboardMarkup:
    """
    کیبورد سوالات سریع
    
    Args:
        user_lang: زبان کاربر
        
    Returns:
        InlineKeyboardMarkup
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 شرایط بورسیه DSU", callback_data="ai:q_scholarship")],
        [InlineKeyboardButton(text="🛂 مراحل گرفتن پرمسو", callback_data="ai:q_permesso")],
        [InlineKeyboardButton(text="💰 هزینه زندگی در پروجا", callback_data="ai:q_cost")],
        [InlineKeyboardButton(text="🏠 پیدا کردن مسکن", callback_data="ai:q_housing")],
        [InlineKeyboardButton(text="🧮 محاسبه ISEE", callback_data="ai:q_isee")],
        [InlineKeyboardButton(text="🆔 کد فیسکاله", callback_data="ai:q_codice_fiscale")],
        [InlineKeyboardButton(text="🏫 ثبت‌نام دانشگاه", callback_data="ai:q_university")],
        [
            InlineKeyboardButton(text="💬 سوال دیگه دارم", callback_data="ai:start_chat")
        ],
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_ai_menu"),
                callback_data="ai:menu"
            )
        ],
    ])


def get_stats_keyboard(
    user_id: int,
    user_lang: str = "fa"
) -> InlineKeyboardMarkup:
    """
    کیبورد صفحه آمار
    
    Args:
        user_id: شناسه کاربر
        user_lang: زبان کاربر
        
    Returns:
        InlineKeyboardMarkup
    """
    buttons = [
        [
            InlineKeyboardButton(
                text=get_msg(user_lang, "btn_refresh"),
                callback_data="ai:stats"
            )
        ]
    ]
    
    # دکمه‌های ادمین
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
            InlineKeyboardButton(text="🔄 ریست آمار", callback_data="ai:admin_reset_metrics"),
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text=get_msg(user_lang, "btn_ai_menu"),
            callback_data="ai:menu"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_feedback_keyboard(user_lang: str = "fa") -> InlineKeyboardMarkup:
    """
    کیبورد بازخورد
    
    Args:
        user_lang: زبان کاربر
        
    Returns:
        InlineKeyboardMarkup
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 مفید بود", callback_data="ai:feedback_good"),
            InlineKeyboardButton(text="👎 مفید نبود", callback_data="ai:feedback_bad"),
        ],
        [
            InlineKeyboardButton(text="💬 ادامه چت", callback_data="ai:start_chat"),
        ]
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# پایان بخش ۲
# ═══════════════════════════════════════════════════════════════════════════════

logger.info("📦 AI Handler v4.0 - Part 2 loaded (States, Helpers, Keyboards)")
# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۶: هندلر منوی اصلی AI
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ai_chat")
@router.callback_query(F.data == "ai:menu")
async def show_ai_menu(callback: CallbackQuery, state: FSMContext):
    """
    نمایش منوی اصلی AI
    
    این هندلر:
    - State را پاک می‌کند
    - وضعیت سرویس را نمایش می‌دهد
    - منوی انتخاب را نشان می‌دهد
    """
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    logger.info(f"📱 User {user_id} opened AI menu")
    
    # پاک کردن state قبلی
    await state.clear()
    
    # دریافت وضعیت سرویس
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
        except Exception as e:
            logger.warning(f"⚠️ Error getting AI status: {e}")
            status_emoji = "🟡"
            status_text = "در حال بررسی"
    else:
        status_emoji = "🔴"
        status_text = "غیرفعال"
    
    # ساخت متن منو
    text = f"{get_msg(user_lang, 'menu_title')}\n\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"🔌 <b>وضعیت:</b> {status_emoji} {status_text}\n\n"
    text += f"<b>✨ امکانات:</b>\n"
    text += f"💬 <b>چت:</b> هر سوالی بپرس!\n"
    text += f"🌐 <b>ترجمه:</b> ایتالیایی ↔ فارسی ↔ انگلیسی\n"
    text += f"🇮🇹 <b>ایتالیایی:</b> معنی، تلفظ، صرف فعل\n"
    text += f"⚡ <b>سریع:</b> سوالات پرتکرار\n\n"
    text += f"👇 <b>انتخاب کن:</b>"
    
    await safe_edit_text(
        callback.message,
        text,
        get_ai_menu_keyboard(user_lang)
    )
    await safe_answer_callback(callback)


@router.message(Command("ai", "ask", "chat"))
async def cmd_ai(message: Message, state: FSMContext):
    """
    دستور ورود به AI
    
    پشتیبانی از:
    - /ai - نمایش منو
    - /ai سوال - پاسخ مستقیم
    - /ask سوال - پاسخ مستقیم
    - /chat - شروع چت
    """
    user_id = message.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    # استخراج متن بعد از دستور
    text = message.text or ""
    for cmd in ["/ai", "/ask", "/chat"]:
        text = text.replace(cmd, "").strip()
    
    if text:
        # اگر کاربر سوال را جلوی دستور نوشته
        logger.info(f"📝 User {user_id} asked directly: {text[:50]}...")
        await state.set_state(AIStates.chatting)
        
        # ساخت پیام جعلی با متن سوال
        message.text = text
        await process_chat(message, state)
    else:
        # نمایش منو
        await message.answer(
            f"{get_msg(user_lang, 'menu_title')}\n\nانتخاب کن:",
            reply_markup=get_ai_menu_keyboard(user_lang),
            parse_mode=ParseMode.HTML
        )


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۷: شروع و پایان چت
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ai:start_chat")
async def start_chat(callback: CallbackQuery, state: FSMContext):
    """
    شروع چت تعاملی با AI
    """
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    logger.info(f"💬 User {user_id} started chat")
    
    # تنظیم state
    await state.set_state(AIStates.chatting)
    await state.update_data(language=user_lang)
    
    # انتخاب پیام خوشامدگویی
    greeting = get_msg(user_lang, "greeting")
    
    # ساخت متن
    text = f"{get_msg(user_lang, 'chat_title')}\n\n"
    text += f"{greeting}\n\n"
    text += f"🎓 تحصیل | 🛂 پرمسو | 💰 هزینه | 🏠 مسکن\n\n"
    text += f"✍️ <b>سوالت رو بنویس...</b>\n\n"
    text += f"💡 <i>یا از دکمه‌های زیر استفاده کن</i>"
    
    await safe_edit_text(
        callback.message,
        text,
        get_chat_keyboard(user_lang)
    )
    await safe_answer_callback(callback, "💬 بنویس!")


@router.callback_query(F.data == "ai:end_chat")
async def end_chat(callback: CallbackQuery, state: FSMContext):
    """
    پایان چت و نمایش آمار
    """
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    logger.info(f"👋 User {user_id} ended chat")
    
    # پاک کردن state
    await state.clear()
    
    # دریافت آمار تاریخچه
    history = await chat_history_manager.get(user_id)
    message_count = len(history) // 2  # تعداد جفت پیام (سوال + جواب)
    
    # ساخت متن
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
    """
    پاک کردن تاریخچه چت کاربر
    """
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    # پاک کردن
    count = await chat_history_manager.clear(user_id)
    
    logger.info(f"🗑 User {user_id} cleared {count} messages")
    
    await safe_answer_callback(
        callback,
        get_msg(user_lang, "history_cleared", count=count),
        show_alert=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۸: پردازش اصلی چت
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(AIStates.chatting)
async def process_chat(message: Message, state: FSMContext):
    """
    پردازش پیام‌های چت کاربر
    
    این تابع اصلی‌ترین هندلر چت است و مسئولیت:
    - بررسی Rate Limit
    - ارسال درخواست به AI
    - مدیریت خطا و Timeout
    - ذخیره تاریخچه
    - ثبت متریک‌ها
    """
    user_id = message.from_user.id
    user_lang = await get_user_language(user_id, state)
    user_text = (message.text or "").strip()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ۱. بررسی دستورات خروج
    # ═══════════════════════════════════════════════════════════════════════════
    cancel_commands = ["/cancel", "/stop", "لغو", "خروج", "پایان", "cancel", "stop"]
    if user_text.lower() in cancel_commands:
        await state.clear()
        await message.answer(
            get_msg(user_lang, "cancelled"),
            reply_markup=get_back_keyboard(user_lang),
            parse_mode=ParseMode.HTML
        )
        return

    # ═══════════════════════════════════════════════════════════════════════════
    # ۲. بررسی خالی نبودن پیام
    # ═══════════════════════════════════════════════════════════════════════════
    if not user_text:
        await message.answer(
            get_msg(user_lang, "empty_message"),
            reply_markup=get_chat_keyboard(user_lang),
            parse_mode=ParseMode.HTML
        )
        return

    # ═══════════════════════════════════════════════════════════════════════════
    # ۳. بررسی Rate Limit
    # ═══════════════════════════════════════════════════════════════════════════
    allowed, wait_seconds = rate_limiter.check(user_id)
    if not allowed:
        await message.answer(
            get_msg(user_lang, "rate_limit", seconds=wait_seconds),
            parse_mode=ParseMode.HTML
        )
        logger.warning(f"⚠️ Rate limit for user {user_id}, wait: {wait_seconds}s")
        return

    # ═══════════════════════════════════════════════════════════════════════════
    # ۴. شروع پردازش با Context Manager
    # ═══════════════════════════════════════════════════════════════════════════
    logger.info(f"💬 Chat from {user_id}: {user_text[:50]}...")
    
    async with ai_processing_context(
        bot=message.bot,
        chat_id=message.chat.id,
        message=message,
        user_lang=user_lang
    ) as (thinking_msg, start_time):
        
        try:
            # ═══════════════════════════════════════════════════════════════════
            # ۵. فراخوانی AI
            # ═══════════════════════════════════════════════════════════════════
            if AI_SERVICE_AVAILABLE and ai_service:
                # دریافت تاریخچه برای context
                history = await chat_history_manager.get(user_id, limit=MAX_CHAT_HISTORY)
                
                # فراخوانی با retry
                response = await call_ai_with_retry(
                    ai_service.chat,
                    message=user_text,
                    user_id=user_id,
                    history=history,
                    max_attempts=AI_RETRY_ATTEMPTS,
                    timeout=AI_TIMEOUT_SECONDS
                )
                
                # محاسبه زمان پردازش
                elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                if response:
                    # ═══════════════════════════════════════════════════════════
                    # ۶. موفقیت - ذخیره و نمایش
                    # ═══════════════════════════════════════════════════════════
                    
                    # ذخیره در تاریخچه
                    await chat_history_manager.add(user_id, "user", user_text)
                    await chat_history_manager.add(
                        user_id, 
                        "assistant", 
                        response.text,
                        metadata={"model": response.model_used}
                    )
                    
                    # ثبت متریک
                    metrics.record_request(
                        user_id=user_id,
                        question=user_text,
                        success=True,
                        time_ms=elapsed_ms,
                        from_cache=response.from_cache
                    )
                    
                    # فرمت و نمایش پاسخ
                    response.processing_time_ms = elapsed_ms
                    result_text = format_ai_response(
                        response=response,
                        user_lang=user_lang,
                        include_metadata=True
                    )
                    
                    await safe_edit_text(
                        thinking_msg,
                        result_text,
                        get_chat_keyboard(user_lang)
                    )
                    
                else:
                    # ═══════════════════════════════════════════════════════════
                    # ۷. Timeout یا خطا
                    # ═══════════════════════════════════════════════════════════
                    metrics.record_timeout(user_id)
                    
                    await safe_edit_text(
                        thinking_msg,
                        get_msg(user_lang, "timeout"),
                        get_chat_keyboard(user_lang)
                    )
                    
            else:
                # ═══════════════════════════════════════════════════════════════
                # سرویس در دسترس نیست
                # ═══════════════════════════════════════════════════════════════
                await safe_edit_text(
                    thinking_msg,
                    get_msg(user_lang, "service_unavailable"),
                    get_back_keyboard(user_lang)
                )
                
        except Exception as e:
            # ═══════════════════════════════════════════════════════════════════
            # ۸. خطای غیرمنتظره
            # ═══════════════════════════════════════════════════════════════════
            logger.error(f"❌ Critical error in process_chat: {e}")
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
                get_chat_keyboard(user_lang)
            )


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۱۹: سوالات سریع
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ai:quick")
async def show_quick_questions_menu(callback: CallbackQuery, state: FSMContext):
    """
    نمایش منوی سوالات سریع
    """
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
    """
    پردازش سوالات سریع
    
    الگوی callback: ai:q_{question_key}
    مثال: ai:q_scholarship, ai:q_permesso
    """
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    # استخراج کلید سوال
    q_key = callback.data.replace("ai:q_", "")
    
    # دریافت متن سوال
    question = get_quick_question(q_key, user_lang)
    if not question:
        question = "سوال نامشخص. لطفاً دوباره تلاش کنید."
    
    logger.info(f"⚡ Quick question from {user_id}: {q_key}")
    
    # تنظیم state
    await state.set_state(AIStates.chatting)
    
    # شروع پردازش
    async with callback_processing_context(
        callback=callback,
        user_lang=user_lang,
        thinking_text=f"❓ <b>سوال:</b>\n{question}\n\n{get_msg(user_lang, 'thinking')}",
        answer_text="⏳ در حال پردازش..."
    ) as (msg, start_time):
        
        try:
            if AI_SERVICE_AVAILABLE and ai_service:
                response = await call_ai_with_retry(
                    ai_service.chat,
                    message=question,
                    user_id=user_id,
                    max_attempts=AI_RETRY_ATTEMPTS,
                    timeout=AI_TIMEOUT_SECONDS
                )
                
                elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                if response:
                    # ذخیره در تاریخچه
                    await chat_history_manager.add(user_id, "user", question)
                    await chat_history_manager.add(user_id, "assistant", response.text)
                    
                    # ثبت متریک
                    metrics.record_request(
                        user_id=user_id,
                        question=f"[QUICK:{q_key}] {question[:30]}",
                        success=True,
                        time_ms=elapsed_ms,
                        from_cache=response.from_cache
                    )
                    
                    # فرمت پاسخ
                    response.processing_time_ms = elapsed_ms
                    result_text = format_ai_response(
                        response=response,
                        user_lang=user_lang,
                        include_metadata=True,
                        question=question
                    )
                    
                    await safe_edit_text(msg, result_text, get_chat_keyboard(user_lang))
                else:
                    metrics.record_timeout(user_id)
                    await safe_edit_text(
                        msg,
                        f"❓ <b>سوال:</b>\n{question}\n\n{get_msg(user_lang, 'timeout')}",
                        get_chat_keyboard(user_lang)
                    )
            else:
                await safe_edit_text(
                    msg,
                    get_msg(user_lang, "service_unavailable"),
                    get_back_keyboard(user_lang)
                )
                
        except Exception as e:
            logger.error(f"❌ Error in quick question: {e}")
            await safe_edit_text(
                msg,
                get_msg(user_lang, "error"),
                get_chat_keyboard(user_lang)
            )


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۰: مترجم هوشمند
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "translate")
@router.callback_query(F.data == "ai_translate")
@router.callback_query(F.data == "ai:translate_menu")
async def show_translate_menu(callback: CallbackQuery, state: FSMContext):
    """
    نمایش منوی ترجمه
    """
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
    """
    انتخاب زبان ترجمه و درخواست متن
    
    الگوی callback: ai:tr_{source}_{target}
    مثال: ai:tr_it_fa, ai:tr_en_fa, ai:tr_auto_fa
    """
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    # استخراج زبان‌ها
    data = callback.data.replace("ai:tr_", "")
    
    if "_" in data:
        parts = data.split("_")
        source_lang = parts[0]
        target_lang = parts[1] if len(parts) > 1 else "fa"
    else:
        source_lang = "auto"
        target_lang = "fa"
    
    # ذخیره در state
    await state.update_data(
        tr_source=source_lang,
        tr_target=target_lang,
        language=user_lang
    )
    await state.set_state(AIStates.waiting_for_translation)
    
    # نام زبان‌ها
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
    """
    پردازش متن برای ترجمه
    """
    user_id = message.from_user.id
    data = await state.get_data()
    user_lang = data.get("language", "fa")
    source_lang = data.get("tr_source", "auto")
    target_lang = data.get("tr_target", "fa")
    
    text_to_translate = (message.text or "").strip()
    
    # بررسی لغو
    if text_to_translate.lower() in ["/cancel", "لغو", "cancel"]:
        await state.clear()
        await message.answer(
            get_msg(user_lang, "cancelled"),
            reply_markup=get_back_keyboard(user_lang),
            parse_mode=ParseMode.HTML
        )
        return
    
    # بررسی خالی نبودن
    if not text_to_translate:
        await message.answer(
            get_msg(user_lang, "empty_message"),
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
    
    logger.info(f"🌐 Translation request from {user_id}: {source_lang} → {target_lang}")
    
    # شروع پردازش
    async with ai_processing_context(
        bot=message.bot,
        chat_id=message.chat.id,
        message=message,
        user_lang=user_lang
    ) as (thinking_msg, start_time):
        
        try:
            if AI_SERVICE_AVAILABLE and ai_service:
                # تبدیل auto به زبان پیش‌فرض
                actual_source = source_lang if source_lang != "auto" else "it"
                
                response = await call_ai_with_retry(
                    ai_service.translate,
                    text=text_to_translate,
                    source_lang=actual_source,
                    target_lang=target_lang,
                    max_attempts=AI_RETRY_ATTEMPTS,
                    timeout=AI_TIMEOUT_SECONDS
                )
                
                elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                if response:
                    # ثبت متریک
                    metrics.record_request(
                        user_id=user_id,
                        question=f"[TRANSLATE:{source_lang}→{target_lang}]",
                        success=True,
                        time_ms=elapsed_ms,
                        from_cache=response.from_cache
                    )
                    
                    # فرمت پاسخ
                    response.processing_time_ms = elapsed_ms
                    result_text = format_translation_response(
                        response=response,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        original_text=text_to_translate,
                        user_lang=user_lang
                    )
                    
                    await safe_edit_text(
                        thinking_msg,
                        result_text,
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
# بخش ۲۱: دستیار زبان ایتالیایی
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "italian")
@router.callback_query(F.data == "ai_italian_help")
@router.callback_query(F.data == "ai:italian_menu")
async def show_italian_menu(callback: CallbackQuery, state: FSMContext):
    """
    منوی کمک یادگیری ایتالیایی
    """
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
    """
    دریافت کلمه ایتالیایی از کاربر
    """
    user_id = message.from_user.id
    data = await state.get_data()
    user_lang = data.get("language", "fa")
    
    word = (message.text or "").strip()
    
    # بررسی لغو
    if word.lower() in ["/cancel", "لغو", "cancel"]:
        await state.clear()
        await message.answer(
            get_msg(user_lang, "cancelled"),
            reply_markup=get_back_keyboard(user_lang),
            parse_mode=ParseMode.HTML
        )
        return
    
    # بررسی خالی نبودن
    if not word:
        await message.answer(
            get_msg(user_lang, "empty_message"),
            parse_mode=ParseMode.HTML
        )
        return
    
    # ذخیره کلمه در state
    await state.update_data(italian_word=word)
    
    # نمایش منوی انتخاب نوع کمک
    text = f"🇮🇹 <b>{word}</b>\n\n"
    text += "چه کمکی می‌خوای؟ 👇"
    
    await message.answer(
        text,
        reply_markup=get_italian_help_keyboard(word, user_lang),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data.startswith("ai:it_"))
async def process_italian_help(callback: CallbackQuery, state: FSMContext):
    """
    پردازش درخواست‌های کمک ایتالیایی
    
    الگوی callback: ai:it_{help_type}:{word}
    مثال: ai:it_meaning:ciao, ai:it_conjugate:essere
    """
    user_id = callback.from_user.id
    data = await state.get_data()
    user_lang = data.get("language", "fa")
    
    # استخراج نوع کمک و کلمه
    callback_data = callback.data.replace("ai:it_", "")
    parts = callback_data.split(":", 1)
    
    help_type = parts[0]
    word = parts[1] if len(parts) > 1 else ""
    
    # اگر کلمه در callback نبود، از state بگیر
    if not word or word == "parola":
        word = data.get("italian_word", "")
    
    if not word:
        await safe_answer_callback(
            callback,
            get_msg(user_lang, "word_not_found"),
            show_alert=True
        )
        return
    
    # نگاشت نوع درخواست
    help_type_map = {
        "meaning": "meaning",
        "example": "example",
        "conjugate": "conjugate",
        "pronounce": "pronunciation"
    }
    
    actual_help_type = help_type_map.get(help_type, "meaning")
    
    logger.info(f"🇮🇹 Italian help from {user_id}: {help_type} for '{word}'")
    
    # شروع پردازش
    async with callback_processing_context(
        callback=callback,
        user_lang=user_lang,
        thinking_text=f"🇮🇹 <b>{word}</b>\n\n{get_msg(user_lang, 'thinking')}",
        answer_text="⏳"
    ) as (msg, start_time):
        
        try:
            if AI_SERVICE_AVAILABLE and ai_service:
                response = await call_ai_with_retry(
                    ai_service.italian_helper,
                    word=word,
                    help_type=actual_help_type,
                    max_attempts=AI_RETRY_ATTEMPTS,
                    timeout=AI_TIMEOUT_SECONDS
                )
                
                elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                if response:
                    # ثبت متریک
                    metrics.record_request(
                        user_id=user_id,
                        question=f"[ITALIAN:{help_type}] {word}",
                        success=True,
                        time_ms=elapsed_ms,
                        from_cache=response.from_cache
                    )
                    
                    # فرمت پاسخ
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
# بخش ۲۲: بازخورد کاربران
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("ai:feedback_"))
async def handle_feedback(callback: CallbackQuery, state: FSMContext):
    """
    دریافت بازخورد کاربر
    """
    user_id = callback.from_user.id
    feedback_type = callback.data.replace("ai:feedback_", "")
    
    logger.info(f"📝 Feedback from {user_id}: {feedback_type}")
    
    if feedback_type == "good":
        await safe_answer_callback(callback, "🙏 ممنون از بازخوردت!", show_alert=True)
    elif feedback_type == "bad":
        await safe_answer_callback(
            callback,
            "🙏 ممنون! سعی می‌کنیم بهتر بشیم.",
            show_alert=True
        )


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۳: دستور لغو عمومی
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("cancel"), StateFilter(AIStates))
async def cancel_command(message: Message, state: FSMContext):
    """
    لغو عملیات جاری با دستور /cancel
    """
    user_id = message.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    current_state = await state.get_state()
    logger.info(f"❌ User {user_id} cancelled state: {current_state}")
    
    await state.clear()
    
    await message.answer(
        get_msg(user_lang, "cancelled"),
        reply_markup=get_back_keyboard(user_lang),
        parse_mode=ParseMode.HTML
    )


# ═══════════════════════════════════════════════════════════════════════════════
# پایان بخش ۳
# ═══════════════════════════════════════════════════════════════════════════════

logger.info("📦 AI Handler v4.0 - Part 3 loaded (Menu, Chat, Quick, Translate, Italian)")
# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۴: آمار و وضعیت سرویس
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ai_status")
@router.callback_query(F.data == "ai:stats")
async def show_stats(callback: CallbackQuery, state: FSMContext):
    """
    نمایش آمار و وضعیت سرویس AI
    
    شامل:
    - وضعیت سرویس (آنلاین/آفلاین)
    - آمار درخواست‌ها
    - نرخ موفقیت
    - زمان پاسخ‌دهی
    - اطلاعات کش
    """
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    await safe_answer_callback(callback)
    
    text_parts = [f"{get_msg(user_lang, 'stats_title')}\n\n"]
    text_parts.append("━━━━━━━━━━━━━━━━━━━━━\n\n")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # وضعیت سرویس AI
    # ═══════════════════════════════════════════════════════════════════════════
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
            text_parts.append(f"<b>🔑 API Key:</b> {'✅ تنظیم شده' if status.get('api_key_configured') else '❌ تنظیم نشده'}\n\n")
            
            # آمار از سرویس
            text_parts.append(f"<b>📈 آمار سرویس:</b>\n")
            text_parts.append(f"• کل درخواست‌ها: <code>{status.get('total_requests', 0)}</code>\n")
            text_parts.append(f"• موفق: <code>{status.get('successful_requests', 0)}</code>\n")
            text_parts.append(f"• نرخ موفقیت: <code>{status.get('success_rate', '0%')}</code>\n\n")
            
            text_parts.append(f"<b>🤖 مدل‌ها:</b> {status.get('active_models', 0)}/{status.get('total_models', 0)} فعال\n")
            text_parts.append(f"<b>💾 کش:</b> {status.get('cache_size', 0)} آیتم\n\n")
            
        except Exception as e:
            logger.error(f"❌ Error getting AI service status: {e}")
            text_parts.append("⚠️ خطا در دریافت وضعیت سرویس\n\n")
    else:
        text_parts.append("🔴 <b>سرویس AI:</b> غیرفعال (Fallback Mode)\n\n")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # آمار متریک‌های داخلی
    # ═══════════════════════════════════════════════════════════════════════════
    text_parts.append("━━━━━━━━━━━━━━━━━━━━━\n\n")
    text_parts.append(f"<b>📊 متریک‌های بات:</b>\n")
    text_parts.append(f"• کل درخواست‌ها: <code>{metrics.total_requests}</code>\n")
    text_parts.append(f"• موفق: <code>{metrics.successful_requests}</code>\n")
    text_parts.append(f"• ناموفق: <code>{metrics.failed_requests}</code>\n")
    text_parts.append(f"• تایم‌اوت: <code>{metrics.timeout_requests}</code>\n")
    text_parts.append(f"• نرخ موفقیت: <code>{metrics.success_rate:.1f}%</code>\n")
    text_parts.append(f"• میانگین زمان: <code>{metrics.avg_response_time_ms:.0f}ms</code>\n")
    text_parts.append(f"• کاربران یکتا: <code>{len(metrics.requests_per_user)}</code>\n\n")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # آمار تاریخچه چت
    # ═══════════════════════════════════════════════════════════════════════════
    history_stats = chat_history_manager.get_stats()
    text_parts.append(f"<b>💬 تاریخچه چت:</b>\n")
    text_parts.append(f"• کاربران فعال: <code>{history_stats['active_users']}</code>\n")
    text_parts.append(f"• کل پیام‌ها: <code>{history_stats['total_messages']}</code>\n\n")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # زمان آپدیت
    # ═══════════════════════════════════════════════════════════════════════════
    text_parts.append("━━━━━━━━━━━━━━━━━━━━━\n")
    text_parts.append(f"<i>⏰ آخرین به‌روزرسانی: {datetime.now().strftime('%H:%M:%S')}</i>")
    
    await safe_edit_text(
        callback.message,
        "".join(text_parts),
        get_stats_keyboard(user_id, user_lang)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۵: ابزارهای ادمین
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ai:admin_clear")
async def admin_clear_cache(callback: CallbackQuery, state: FSMContext):
    """
    پاک کردن کش AI (فقط ادمین)
    """
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await safe_answer_callback(
            callback,
            get_msg("fa", "no_access"),
            show_alert=True
        )
        return
    
    if AI_SERVICE_AVAILABLE and ai_service:
        try:
            count = ai_service.clear_cache()
            logger.info(f"🗑 Admin {user_id} cleared {count} cache items")
            await safe_answer_callback(
                callback,
                f"🗑 {count} آیتم از کش پاک شد!",
                show_alert=True
            )
        except Exception as e:
            logger.error(f"❌ Error clearing cache: {e}")
            await safe_answer_callback(callback, "❌ خطا در پاک کردن کش", show_alert=True)
    else:
        await safe_answer_callback(callback, "⚠️ سرویس در دسترس نیست", show_alert=True)
    
    # رفرش صفحه آمار
    await show_stats(callback, state)


@router.callback_query(F.data == "ai:admin_models")
async def admin_list_models(callback: CallbackQuery, state: FSMContext):
    """
    لیست مدل‌های AI (فقط ادمین)
    """
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    if not is_admin(user_id):
        await safe_answer_callback(callback, get_msg("fa", "no_access"), show_alert=True)
        return
    
    await safe_answer_callback(callback)
    
    text_parts = ["📋 <b>لیست مدل‌های AI</b>\n\n"]
    text_parts.append("━━━━━━━━━━━━━━━━━━━━━\n\n")
    
    if AI_SERVICE_AVAILABLE and ai_service:
        try:
            models = ai_service.get_available_models()
            
            if models:
                for i, model in enumerate(models[:15], 1):  # حداکثر ۱۵ مدل
                    status_icon = "🟢" if model.get("is_active") else "🔴"
                    name = model.get("name", "Unknown")
                    provider = model.get("provider", "")
                    requests = model.get("requests", 0)
                    
                    text_parts.append(f"{status_icon} <b>{name}</b>\n")
                    text_parts.append(f"   📡 {provider} | 📊 {requests} درخواست\n\n")
                
                if len(models) > 15:
                    text_parts.append(f"<i>... و {len(models) - 15} مدل دیگر</i>\n\n")
            else:
                text_parts.append("⚠️ هیچ مدلی یافت نشد.\n\n")
                
        except Exception as e:
            logger.error(f"❌ Error getting models: {e}")
            text_parts.append("❌ خطا در دریافت لیست مدل‌ها\n\n")
    else:
        text_parts.append("🔴 سرویس AI غیرفعال است.\n\n")
    
    text_parts.append("━━━━━━━━━━━━━━━━━━━━━\n")
    text_parts.append(f"<i>⏰ {datetime.now().strftime('%H:%M:%S')}</i>")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 به‌روزرسانی", callback_data="ai:admin_models")],
        [InlineKeyboardButton(text="🔙 آمار", callback_data="ai:stats")]
    ])
    
    await safe_edit_text(callback.message, "".join(text_parts), keyboard)


@router.callback_query(F.data == "ai:admin_test")
async def admin_test_service(callback: CallbackQuery, state: FSMContext):
    """
    تست واقعی سرویس AI (فقط ادمین)
    """
    user_id = callback.from_user.id
    user_lang = await get_user_language(user_id, state)
    
    if not is_admin(user_id):
        await safe_answer_callback(callback, get_msg("fa", "no_access"), show_alert=True)
        return
    
    await safe_answer_callback(callback, "⏳ در حال تست...")
    
    # نمایش پیام در حال تست
    await safe_edit_text(
        callback.message,
        "🔧 <b>تست سرویس AI</b>\n\n⏳ در حال ارسال درخواست تست..."
    )
    
    # شروع typing
    typing_task = asyncio.create_task(keep_typing(callback.bot, callback.message.chat.id))
    
    try:
        if AI_SERVICE_AVAILABLE and ai_service:
            start_time = datetime.now()
            
            response = await call_ai_with_timeout(
                ai_service.chat,
                message="This is a test message. Please respond with 'OK' and the current time.",
                user_id=user_id,
                timeout=15
            )
            
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if response:
                text = f"✅ <b>تست موفق!</b>\n\n"
                text += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                text += f"<b>⏱ زمان پاسخ:</b> <code>{elapsed_ms}ms</code>\n"
                text += f"<b>🤖 مدل:</b> <code>{response.model_used or 'N/A'}</code>\n"
                text += f"<b>📦 از کش:</b> {'بله' if response.from_cache else 'خیر'}\n\n"
                text += f"<b>📝 پاسخ:</b>\n{response.text[:500]}"
                
                if len(response.text) > 500:
                    text += "..."
            else:
                text = f"❌ <b>تست ناموفق</b>\n\n"
                text += f"<b>⏱ زمان:</b> <code>{elapsed_ms}ms</code>\n"
                text += f"<b>علت:</b> Timeout یا خطای سرویس"
        else:
            text = "🔴 <b>سرویس AI غیرفعال است</b>\n\nتست امکان‌پذیر نیست."
        
    except Exception as e:
        logger.error(f"❌ Admin test error: {e}")
        text = f"❌ <b>خطا در تست</b>\n\n<code>{str(e)[:200]}</code>"
    
    finally:
        typing_task.cancel()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 تست مجدد", callback_data="ai:admin_test")],
        [InlineKeyboardButton(text="🔙 آمار", callback_data="ai:stats")]
    ])
    
    await safe_edit_text(callback.message, text, keyboard)


@router.callback_query(F.data == "ai:admin_metrics")
async def admin_show_metrics(callback: CallbackQuery, state: FSMContext):
    """
    نمایش متریک‌های پیشرفته (فقط ادمین)
    """
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await safe_answer_callback(callback, get_msg("fa", "no_access"), show_alert=True)
        return
    
    await safe_answer_callback(callback)
    
    text_parts = ["📊 <b>متریک‌های پیشرفته</b>\n\n"]
    text_parts.append("━━━━━━━━━━━━━━━━━━━━━\n\n")
    
    # آمار کلی
    text_parts.append(f"<b>📈 آمار کلی:</b>\n")
    text_parts.append(f"• کل: <code>{metrics.total_requests}</code>\n")
    text_parts.append(f"• موفق: <code>{metrics.successful_requests}</code>\n")
    text_parts.append(f"• ناموفق: <code>{metrics.failed_requests}</code>\n")
    text_parts.append(f"• تایم‌اوت: <code>{metrics.timeout_requests}</code>\n")
    text_parts.append(f"• کش: <code>{metrics.cache_hits}</code>\n")
    text_parts.append(f"• نرخ موفقیت: <code>{metrics.success_rate:.1f}%</code>\n")
    text_parts.append(f"• نرخ کش: <code>{metrics.cache_hit_rate:.1f}%</code>\n\n")
    
    # زمان پاسخ
    text_parts.append(f"<b>⏱ زمان پاسخ:</b>\n")
    text_parts.append(f"• میانگین: <code>{metrics.avg_response_time_ms:.0f}ms</code>\n")
    if metrics.response_times:
        text_parts.append(f"• کمینه: <code>{min(metrics.response_times)}ms</code>\n")
        text_parts.append(f"• بیشینه: <code>{max(metrics.response_times)}ms</code>\n")
    text_parts.append("\n")
    
    # کاربران پرمصرف
    top_users = metrics.get_top_users(5)
    if top_users:
        text_parts.append(f"<b>👥 کاربران پرمصرف:</b>\n")
        for uid, count in top_users:
            text_parts.append(f"• <code>{uid}</code>: {count} درخواست\n")
        text_parts.append("\n")
    
    # سوالات پرتکرار
    top_questions = metrics.get_top_questions(5)
    if top_questions:
        text_parts.append(f"<b>❓ سوالات پرتکرار:</b>\n")
        for q, count in top_questions:
            text_parts.append(f"• {count}x: <i>{q[:30]}...</i>\n")
        text_parts.append("\n")
    
    # خطاها
    errors = metrics.get_error_summary()
    if errors:
        text_parts.append(f"<b>❌ خطاها:</b>\n")
        for error_type, count in errors.items():
            text_parts.append(f"• {error_type}: {count}\n")
        text_parts.append("\n")
    
    # زمان فعالیت
    uptime = metrics.uptime
    hours = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)
    text_parts.append(f"<b>⏰ زمان فعالیت:</b> {hours}h {minutes}m\n\n")
    
    text_parts.append("━━━━━━━━━━━━━━━━━━━━━\n")
    text_parts.append(f"<i>آخرین به‌روزرسانی: {datetime.now().strftime('%H:%M:%S')}</i>")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 به‌روزرسانی", callback_data="ai:admin_metrics")],
        [
            InlineKeyboardButton(text="🔄 ریست", callback_data="ai:admin_reset_metrics"),
            InlineKeyboardButton(text="🔙 آمار", callback_data="ai:stats")
        ]
    ])
    
    await safe_edit_text(callback.message, "".join(text_parts), keyboard)


@router.callback_query(F.data == "ai:admin_reset_metrics")
async def admin_reset_metrics(callback: CallbackQuery, state: FSMContext):
    """
    ریست آمار متریک‌ها (فقط ادمین)
    """
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await safe_answer_callback(callback, get_msg("fa", "no_access"), show_alert=True)
        return
    
    # ذخیره آمار قبلی
    old_stats = metrics.reset()
    
    logger.info(f"📊 Admin {user_id} reset metrics. Old stats: {old_stats}")
    
    await safe_answer_callback(
        callback,
        f"🔄 آمار ریست شد!\nدرخواست‌های قبلی: {old_stats.get('total_requests', 0)}",
        show_alert=True
    )
    
    # نمایش آمار جدید
    await admin_show_metrics(callback, state)


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۶: تسک پاکسازی خودکار (Background Cleanup)
# ═══════════════════════════════════════════════════════════════════════════════

_cleanup_task: Optional[asyncio.Task] = None


async def cleanup_loop():
    """
    حلقه پاکسازی خودکار
    
    این تسک:
    - هر ساعت یکبار اجرا می‌شود
    - تاریخچه‌های قدیمی را پاک می‌کند
    - داده‌های Rate Limiter را پاک می‌کند
    - از نشت حافظه جلوگیری می‌کند
    """
    logger.info("🧹 Cleanup loop started")
    
    while True:
        try:
            await asyncio.sleep(HISTORY_CLEANUP_INTERVAL)
            
            logger.info("🧹 Running scheduled cleanup...")
            
            # پاکسازی تاریخچه
            history_cleaned = await chat_history_manager.cleanup_old_data()
            
            # پاکسازی rate limiter
            rate_cleaned = await rate_limiter.cleanup()
            
            logger.info(f"🧹 Cleanup done: {history_cleaned} history users, {rate_cleaned} rate limit entries")
            
        except asyncio.CancelledError:
            logger.info("🧹 Cleanup loop cancelled")
            break
        except Exception as e:
            logger.error(f"❌ Error in cleanup loop: {e}")
            await asyncio.sleep(60)  # در صورت خطا، کمی صبر کن


def start_cleanup_task() -> asyncio.Task:
    """
    شروع تسک پاکسازی
    
    Returns:
        تسک ایجاد شده
    """
    global _cleanup_task
    
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("🧹 Cleanup task created")
    
    return _cleanup_task


def stop_cleanup_task() -> None:
    """
    توقف تسک پاکسازی
    """
    global _cleanup_task
    
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        logger.info("🧹 Cleanup task cancelled")


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۷: دستورات دیباگ
# ═══════════════════════════════════════════════════════════════════════════════

@router.message(Command("ai_debug"))
async def debug_ai(message: Message, state: FSMContext):
    """
    نمایش اطلاعات دیباگ (فقط ادمین)
    """
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    current_state = await state.get_state()
    state_data = await state.get_data()
    
    text_parts = ["🔍 <b>Debug Info</b>\n\n"]
    
    # اطلاعات State
    text_parts.append(f"<b>🔄 State:</b>\n")
    text_parts.append(f"• Current: <code>{current_state}</code>\n")
    text_parts.append(f"• Data keys: <code>{list(state_data.keys())}</code>\n\n")
    
    # اطلاعات سرویس
    text_parts.append(f"<b>🤖 Service:</b>\n")
    text_parts.append(f"• AI Available: <code>{AI_SERVICE_AVAILABLE}</code>\n")
    text_parts.append(f"• Lang Available: <code>{LANG_SERVICE_AVAILABLE}</code>\n")
    text_parts.append(f"• DB Available: <code>{DATABASE_AVAILABLE}</code>\n\n")
    
    # تاریخچه کاربر
    history = await chat_history_manager.get(user_id)
    text_parts.append(f"<b>💬 User History:</b>\n")
    text_parts.append(f"• Messages: <code>{len(history)}</code>\n\n")
    
    # Rate Limit
    remaining = rate_limiter.get_remaining(user_id)
    text_parts.append(f"<b>⏱ Rate Limit:</b>\n")
    text_parts.append(f"• Remaining: <code>{remaining}/{RATE_LIMIT_MESSAGES}</code>\n")
    text_parts.append(f"• Premium: <code>{rate_limiter.is_premium(user_id)}</code>\n\n")
    
    # Cleanup Task
    cleanup_status = "Running" if _cleanup_task and not _cleanup_task.done() else "Stopped"
    text_parts.append(f"<b>🧹 Cleanup Task:</b> <code>{cleanup_status}</code>\n\n")
    
    # متریک‌ها
    text_parts.append(f"<b>📊 Metrics Summary:</b>\n")
    text_parts.append(f"• Total: <code>{metrics.total_requests}</code>\n")
    text_parts.append(f"• Success Rate: <code>{metrics.success_rate:.1f}%</code>\n")
    
    await message.answer("".join(text_parts), parse_mode=ParseMode.HTML)


@router.message(Command("ai_cleanup"))
async def manual_cleanup(message: Message):
    """
    پاکسازی دستی (فقط ادمین)
    """
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    await message.answer("🧹 در حال پاکسازی...")
    
    history_cleaned = await chat_history_manager.cleanup_old_data()
    rate_cleaned = await rate_limiter.cleanup()
    
    await message.answer(
        f"✅ <b>پاکسازی انجام شد</b>\n\n"
        f"• تاریخچه: {history_cleaned} کاربر\n"
        f"• Rate Limit: {rate_cleaned} ورودی",
        parse_mode=ParseMode.HTML
    )


@router.message(Command("ai_premium"))
async def manage_premium(message: Message):
    """
    مدیریت کاربران ویژه (فقط ادمین)
    
    استفاده:
    /ai_premium add 123456789
    /ai_premium remove 123456789
    /ai_premium list
    """
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    text = message.text or ""
    parts = text.split()
    
    if len(parts) < 2:
        await message.answer(
            "📝 <b>استفاده:</b>\n"
            "/ai_premium add USER_ID\n"
            "/ai_premium remove USER_ID\n"
            "/ai_premium list",
            parse_mode=ParseMode.HTML
        )
        return
    
    action = parts[1].lower()
    
    if action == "list":
        premium_users = list(rate_limiter._premium_users)
        if premium_users:
            users_text = "\n".join([f"• <code>{uid}</code>" for uid in premium_users])
            await message.answer(f"👑 <b>کاربران ویژه:</b>\n{users_text}", parse_mode=ParseMode.HTML)
        else:
            await message.answer("👑 هیچ کاربر ویژه‌ای وجود ندارد.", parse_mode=ParseMode.HTML)
        return
    
    if len(parts) < 3:
        await message.answer("⚠️ شناسه کاربر را وارد کنید.")
        return
    
    try:
        target_user_id = int(parts[2])
    except ValueError:
        await message.answer("⚠️ شناسه کاربر باید عدد باشد.")
        return
    
    if action == "add":
        rate_limiter.add_premium_user(target_user_id)
        await message.answer(f"✅ کاربر <code>{target_user_id}</code> به لیست ویژه اضافه شد.", parse_mode=ParseMode.HTML)
        logger.info(f"👑 Admin {user_id} added premium user {target_user_id}")
    elif action == "remove":
        rate_limiter.remove_premium_user(target_user_id)
        await message.answer(f"✅ کاربر <code>{target_user_id}</code> از لیست ویژه حذف شد.", parse_mode=ParseMode.HTML)
        logger.info(f"👑 Admin {user_id} removed premium user {target_user_id}")
    else:
        await message.answer("⚠️ دستور نامعتبر. از add یا remove استفاده کنید.")


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۸: هوک‌های راه‌اندازی و توقف
# ═══════════════════════════════════════════════════════════════════════════════

async def on_startup() -> None:
    """
    اجرا در زمان راه‌اندازی بات
    
    این تابع باید از main.py فراخوانی شود.
    """
    logger.info("🚀 AI Handler starting up...")
    
    # شروع تسک پاکسازی
    start_cleanup_task()
    
    # بررسی وضعیت سرویس
    if AI_SERVICE_AVAILABLE and ai_service:
        try:
            status = ai_service.get_status()
            logger.info(f"🤖 AI Service status: {status.get('status', 'unknown')}")
        except Exception as e:
            logger.warning(f"⚠️ Could not check AI service: {e}")
    
    logger.success("✅ AI Handler started successfully")


async def on_shutdown() -> None:
    """
    اجرا در زمان توقف بات
    
    این تابع باید از main.py فراخوانی شود.
    """
    logger.info("🛑 AI Handler shutting down...")
    
    # توقف تسک پاکسازی
    stop_cleanup_task()
    
    # ذخیره آمار (اختیاری)
    final_stats = metrics.to_dict()
    logger.info(f"📊 Final metrics: {final_stats}")
    
    logger.success("✅ AI Handler stopped")


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۲۹: تابع کمکی برای ثبت روتر
# ═══════════════════════════════════════════════════════════════════════════════

def setup_router(parent_router) -> Router:
    """
    ثبت روتر AI در روتر اصلی
    
    Args:
        parent_router: روتر والد (معمولاً dp یا روتر اصلی)
        
    Returns:
        روتر AI
        
    Usage:
        from handlers.ai_handler import setup_router
        ai_router = setup_router(dp)
    """
    parent_router.include_router(router)
    logger.info(f"📎 AI Router registered to parent")
    return router


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۳۰: لاگ نهایی و خروجی
# ═══════════════════════════════════════════════════════════════════════════════

# لاگ بارگذاری موفق
logger.success("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
logger.success("🤖 AI Handler v4.0 (Production) - Fully Loaded!")
logger.success("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
logger.info(f"   📦 Router Name: {router.name}")
logger.info(f"   🤖 AI Service: {'✅ Available' if AI_SERVICE_AVAILABLE else '❌ Unavailable'}")
logger.info(f"   🌐 Lang Service: {'✅ Available' if LANG_SERVICE_AVAILABLE else '❌ Unavailable'}")
logger.info(f"   💾 Database: {'✅ Available' if DATABASE_AVAILABLE else '❌ Unavailable'}")
logger.info(f"   ⏱ Timeout: {AI_TIMEOUT_SECONDS}s")
logger.info(f"   🔄 Retry Attempts: {AI_RETRY_ATTEMPTS}")
logger.info(f"   📊 Rate Limit: {RATE_LIMIT_MESSAGES}/{RATE_LIMIT_WINDOW}s")
logger.info(f"   🧹 Cleanup Interval: {HISTORY_CLEANUP_INTERVAL}s")
logger.success("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# ═══════════════════════════════════════════════════════════════════════════════
# بخش ۳۱: Export های عمومی
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Router اصلی
    "router",
    
    # States
    "AIStates",
    
    # کلاس‌ها
    "AIMetrics",
    "ChatHistoryManager",
    "RateLimiter",
    
    # نمونه‌های سراسری
    "metrics",
    "chat_history_manager",
    "rate_limiter",
    
    # توابع کمکی
    "safe_answer",
    "safe_edit_text",
    "safe_delete_message",
    "safe_answer_callback",
    "keep_typing",
    "call_ai_with_timeout",
    "call_ai_with_retry",
    "get_msg",
    "get_user_language",
    "is_admin",
    
    # Context Managers
    "ai_processing_context",
    "callback_processing_context",
    
    # توابع فرمت
    "format_ai_response",
    "format_translation_response",
    "format_italian_help_response",
    "create_error_response",
    
    # کیبوردها
    "get_ai_menu_keyboard",
    "get_chat_keyboard",
    "get_translate_menu_keyboard",
    "get_italian_help_keyboard",
    "get_quick_questions_keyboard",
    "get_back_keyboard",
    "get_stats_keyboard",
    
    # هوک‌ها
    "on_startup",
    "on_shutdown",
    "setup_router",
    
    # تسک‌ها
    "start_cleanup_task",
    "stop_cleanup_task",
    
    # ثابت‌ها
    "AI_SERVICE_AVAILABLE",
    "LANG_SERVICE_AVAILABLE",
    "DATABASE_AVAILABLE",
    "MESSAGES",
    "QUICK_QUESTIONS",
]