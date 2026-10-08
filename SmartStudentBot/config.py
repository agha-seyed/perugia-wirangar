# config.py
# فایل تنظیمات اصلی - نسخه ۲.۰ (اصلاح شده و توسعه یافته)
# ژانویه ۲۰۲۵

"""
═══════════════════════════════════════════════════════════════════════════════
                        تنظیمات SmartStudentBot
═══════════════════════════════════════════════════════════════════════════════
این فایل شامل تمام تنظیمات پروژه است:
    ✅ تنظیمات تلگرام (توکن، ادمین‌ها، وب‌هوک)
    ✅ تنظیمات سرور (URL، پورت)
    ✅ تنظیمات دیتابیس (PostgreSQL، Redis)
    ✅ کلیدهای API (OpenRouter، آب‌وهوا، نرخ ارز)
    ✅ تنظیمات AI (Voice، Image، مدل‌ها)
    ✅ تنظیمات لاگینگ و Sentry
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# ═══════════════════════════════════════════════════════════════════════════════
# بارگذاری متغیرهای محیطی
# ═══════════════════════════════════════════════════════════════════════════════

# بارگذاری .env (متغیرهای سیستمی و Render اولویت دارند)
load_dotenv(override=False)

# مسیر پایه پروژه
BASE_DIR = Path(__file__).parent


# ═══════════════════════════════════════════════════════════════════════════════
# کلاس تنظیمات اصلی
# ═══════════════════════════════════════════════════════════════════════════════

class Settings:
    """
    کلاس مرکزی تنظیمات پروژه
    
    تمام تنظیمات از متغیرهای محیطی (.env) خوانده می‌شوند.
    مقادیر پیش‌فرض برای توسعه محلی تنظیم شده‌اند.
    """
    
    # ═══════════════════════════════════════════════════════════════════════════
    # تنظیمات تلگرام
    # ═══════════════════════════════════════════════════════════════════════════
    
    # توکن ربات (ضروری)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    
    # شناسه یکتای ربات (برای webhook)
    BOT_ID: str = os.getenv("BOT_ID", "perugia").strip()
    
    # رمز امنیتی webhook
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "").strip()
    
    # شناسه کانال (اختیاری)
    CHANNEL_ID: str = os.getenv("CHANNEL_ID", "").strip()
    
    @property
    def ADMIN_CHAT_IDS(self) -> List[int]:
        """
        لیست شناسه ادمین‌ها
        
        فرمت در .env: ADMIN_CHAT_IDS=123456789,987654321
        """
        ids_str = os.getenv("ADMIN_CHAT_IDS", "").strip()
        if not ids_str:
            return []
        try:
            return [int(x.strip()) for x in ids_str.split(",") if x.strip().isdigit()]
        except ValueError:
            return []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # تنظیمات سرور
    # ═══════════════════════════════════════════════════════════════════════════
    
    # آدرس پایه سرور (برای webhook - خودکار در Render پشتیبانی می‌شود)
    BASE_URL: str = (os.getenv("RENDER_EXTERNAL_URL") or os.getenv("BASE_URL", "http://localhost:8000")).strip().rstrip("/")
    
    # آدرس وب‌اپلیکیشن (Telegram Mini App URL)
    WEBAPP_URL: str = (os.getenv("WEBAPP_URL") or "https://smartstudentbot-webapp.onrender.com").strip().rstrip("/")
    
    # پورت سرور
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # تنظیمات دیتابیس
    # ═══════════════════════════════════════════════════════════════════════════
    
    # MongoDB Connection String (پشتیبانی از MONGODB_URL, MONGO_URI, MONGODB_URI, MONGO_URL, DATABASE_URL)
    @property
    def MONGO_URI(self) -> str:
        raw = (
            os.getenv("MONGODB_URL")
            or os.getenv("MONGO_URI")
            or os.getenv("MONGODB_URI")
            or os.getenv("MONGO_URL")
            or os.getenv("DATABASE_URL")
            or "mongodb://localhost:27017/"
        ).strip().strip('"').strip("'")
        return raw.strip()
    
    # نام دیتابیس (پشتیبانی از DB_NAME, DB, MONGO_DB, DATABASE_NAME)
    @property
    def DB_NAME(self) -> str:
        return (
            os.getenv("DB_NAME")
            or os.getenv("DB")
            or os.getenv("MONGO_DB")
            or os.getenv("DATABASE_NAME")
            or "smart_student_bot"
        ).strip().strip('"').strip("'")
    
    # Gemini API Key (هوش مصنوعی گوگل - پشتیبان)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    
    # Atria ASI (هوش مصنوعی با ۱۰۰ میلیون توکن)
    ATRIA_API_KEY: str = os.getenv("ATRIA_API_KEY", "").strip()
    ATRIA_BASE_URL: str = os.getenv("ATRIA_BASE_URL", "https://api.atria-asi.ai/v1").strip().rstrip("/")
    ATRIA_MODEL: str = os.getenv("ATRIA_MODEL", "Atria-Dawn-Preview").strip()
    
    # سامانه استعلام نرخ لحظه‌ای ارز و طلا (BrsApi)
    BRSAPI_KEY: str = os.getenv("BRSAPI_KEY", "").strip()
    BRSAPI_URL: str = os.getenv("BRSAPI_URL", "https://Api.BrsApi.ir/Market/Gold_Currency.php").strip()
    
    # Redis (پشتیبانی از REDIS_URL، فرمت Upstash REST و افزودن خودکار اسکیما)
    @property
    def REDIS_URL(self) -> str:
        url = (
            os.getenv("REDIS_URL")
            or os.getenv("REDIS_URI")
            or os.getenv("REDIS_INTERNAL_URL")
            or os.getenv("REDIS_EXTERNAL_URL")
            or ""
        ).strip().strip('"').strip("'")
        if not url:
            return ""
        
        # اگر کاربر فرمت REST مربوط به Upstash را کپی کرده باشد، خودکار تبدیل به ردیس استاندارد می‌شود
        if "upstash.io" in url and ("UPSTASH" in url or "https://" in url):
            import re
            host_match = re.search(r'(?:https?://)?([a-zA-Z0-9\.\-]+\.upstash\.io)', url)
            token_match = re.search(r'TOKEN\s*=\s*["\']?([a-zA-Z0-9_\-]+)["\']?', url)
            if host_match and token_match:
                host = host_match.group(1)
                token = token_match.group(1)
                return f"rediss://default:{token}@{host}:6379"

        if not any(url.startswith(scheme) for scheme in ("redis://", "rediss://", "unix://")):
            if "upstash.io" in url:
                url = f"rediss://{url}"
            else:
                url = f"redis://{url}"
        return url
    
    # ═══════════════════════════════════════════════════════════════════════════
    # کلیدهای API - هوش مصنوعی
    # ═══════════════════════════════════════════════════════════════════════════
    
    # OpenRouter (API اصلی برای AI)
    # این کلید برای همه مدل‌ها استفاده می‌شود: GPT-4, Claude, Gemini, Llama, ...
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "").strip()
    
    # HuggingFace (پشتیبان - اختیاری)
    HUGGINGFACE_API_KEY: str = os.getenv("HUGGINGFACE_API_KEY", "").strip()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # کلیدهای API - سرویس‌های دیگر
    # ═══════════════════════════════════════════════════════════════════════════
    
    # آب و هوا
    OPENWEATHERMAP_API_KEY: str = os.getenv("OPENWEATHERMAP_API_KEY", "").strip()
    
    # نرخ ارز
    EXCHANGE_RATE_API_KEY: str = os.getenv("EXCHANGE_RATE_API_KEY", "").strip()
    
    @property
    def NAVASAN_API_KEYS(self) -> List[str]:
        """کلیدهای چرخشی برای دریافت لحظه‌ای نرخ ارز از Navasan"""
        keys = os.getenv("NAVASAN_API_KEYS", "").strip()
        if keys:
            return [k.strip() for k in keys.split(",") if k.strip()]
        return [
            "freepnP0B5PJNRJD5XUTFauKTpubrxE2",
            "freeWVcwTB4Xq8yT48Y0YHgCy8JcvulU",
            "freezW677iqPcZxRFwQbpX0iZQfxaWwi",
            "freeb2n6GMnQA0IIxbKUX3y9BC51Cn2N",
            "freeZjQukbJZKuek0fWGgww8C8bf2wG4",
        ]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # تنظیمات AI - Voice (پیام صوتی)
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def AI_VOICE_ENABLED(self) -> bool:
        """آیا پشتیبانی از پیام صوتی فعال است؟"""
        return os.getenv("AI_VOICE_ENABLED", "True").lower() in ("true", "1", "yes")
    
    @property
    def AI_VOICE_MAX_DURATION(self) -> int:
        """حداکثر طول پیام صوتی (ثانیه)"""
        return int(os.getenv("AI_VOICE_MAX_DURATION", "60"))
    
    @property
    def AI_VOICE_PROVIDER(self) -> str:
        """
        سرویس تبدیل صدا به متن
        گزینه‌ها: openrouter, groq, local
        """
        return os.getenv("AI_VOICE_PROVIDER", "openrouter").lower()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # تنظیمات AI - Image (تصویر)
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def AI_IMAGE_ENABLED(self) -> bool:
        """آیا پشتیبانی از تحلیل تصویر فعال است؟"""
        return os.getenv("AI_IMAGE_ENABLED", "True").lower() in ("true", "1", "yes")
    
    @property
    def AI_IMAGE_MAX_SIZE_MB(self) -> int:
        """حداکثر حجم تصویر (مگابایت)"""
        return int(os.getenv("AI_IMAGE_MAX_SIZE_MB", "10"))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # تنظیمات AI - عمومی
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def AI_DEFAULT_MODEL(self) -> str:
        """مدل پیش‌فرض AI"""
        return os.getenv("AI_DEFAULT_MODEL", "Atria-Dawn-Preview")
    
    @property
    def AI_TIMEOUT_SECONDS(self) -> int:
        """حداکثر زمان انتظار برای پاسخ AI (ثانیه)"""
        return int(os.getenv("AI_TIMEOUT_SECONDS", "30"))
    
    @property
    def AI_MAX_RETRIES(self) -> int:
        """حداکثر تعداد تلاش مجدد"""
        return int(os.getenv("AI_MAX_RETRIES", "3"))
    
    @property
    def AI_CACHE_ENABLED(self) -> bool:
        """آیا کش AI فعال است؟"""
        return os.getenv("AI_CACHE_ENABLED", "True").lower() in ("true", "1", "yes")
    
    @property
    def AI_CACHE_TTL_HOURS(self) -> int:
        """مدت اعتبار کش (ساعت)"""
        return int(os.getenv("AI_CACHE_TTL_HOURS", "4"))
    
    @property
    def AI_HISTORY_ENABLED(self) -> bool:
        """آیا تاریخچه چت فعال است؟"""
        return os.getenv("AI_HISTORY_ENABLED", "True").lower() in ("true", "1", "yes")
    
    @property
    def AI_HISTORY_MAX_MESSAGES(self) -> int:
        """حداکثر تعداد پیام در تاریخچه"""
        return int(os.getenv("AI_HISTORY_MAX_MESSAGES", "10"))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # تنظیمات AI - Rate Limiting
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def AI_RATE_LIMIT_MESSAGES(self) -> int:
        """تعداد پیام مجاز در بازه زمانی"""
        return int(os.getenv("AI_RATE_LIMIT_MESSAGES", "10"))
    
    @property
    def AI_RATE_LIMIT_WINDOW(self) -> int:
        """بازه زمانی rate limit (ثانیه)"""
        return int(os.getenv("AI_RATE_LIMIT_WINDOW", "60"))
    
    @property
    def AI_RATE_LIMIT_PREMIUM_MULTIPLIER(self) -> int:
        """ضریب افزایش برای کاربران ویژه"""
        return int(os.getenv("AI_RATE_LIMIT_PREMIUM_MULTIPLIER", "2"))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # تنظیمات AI - Warm-up و Keep-Alive
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def AI_WARMUP_ENABLED(self) -> bool:
        """آیا Warm-up فعال است؟"""
        return os.getenv("AI_WARMUP_ENABLED", "True").lower() in ("true", "1", "yes")
    
    @property
    def AI_WARMUP_TIMEOUT(self) -> int:
        """حداکثر زمان Warm-up (ثانیه)"""
        return int(os.getenv("AI_WARMUP_TIMEOUT", "10"))
    
    @property
    def AI_KEEP_ALIVE_ENABLED(self) -> bool:
        """آیا Keep-Alive فعال است؟"""
        return os.getenv("AI_KEEP_ALIVE_ENABLED", "True").lower() in ("true", "1", "yes")
    
    @property
    def AI_KEEP_ALIVE_INTERVAL(self) -> int:
        """فاصله بین ping های Keep-Alive (ثانیه)"""
        return int(os.getenv("AI_KEEP_ALIVE_INTERVAL", "180"))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ویژگی‌های پروژه (Feature Flags)
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def FEATURE_AI_ENABLED(self) -> bool:
        """آیا ماژول AI فعال است؟"""
        return os.getenv("FEATURE_AI_ENABLED", "True").lower() in ("true", "1", "yes")
    
    @property
    def FEATURE_NEWS_ENABLED(self) -> bool:
        """آیا ماژول اخبار فعال است؟"""
        return os.getenv("FEATURE_NEWS_ENABLED", "True").lower() in ("true", "1", "yes")
    
    @property
    def FEATURE_GAMIFICATION(self) -> bool:
        """آیا سیستم امتیازدهی فعال است؟"""
        return os.getenv("FEATURE_GAMIFICATION", "False").lower() in ("true", "1", "yes")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # تشخیص محیط
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def ENVIRONMENT(self) -> str:
        """
        تشخیص محیط اجرا
        
        Returns:
            "development" یا "production"
        """
        # اگر در .env مشخص شده
        env = os.getenv("ENVIRONMENT", "").lower()
        if env in ("development", "production", "staging"):
            return env
        
        # تشخیص خودکار از روی BASE_URL
        if "localhost" in self.BASE_URL or "127.0.0.1" in self.BASE_URL:
            return "development"
        
        return "production"
    
    @property
    def IS_LOCAL(self) -> bool:
        """آیا در محیط توسعه محلی هستیم؟"""
        return self.ENVIRONMENT == "development"
    
    @property
    def IS_PRODUCTION(self) -> bool:
        """آیا در محیط پروداکشن هستیم؟"""
        return self.ENVIRONMENT == "production"
    
    @property
    def DEBUG(self) -> bool:
        """آیا حالت دیباگ فعال است؟"""
        return os.getenv("DEBUG", str(self.IS_LOCAL)).lower() in ("true", "1", "yes")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Sentry (خطایابی)
    # ═══════════════════════════════════════════════════════════════════════════
    
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "").strip()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # مسیرها
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def DATA_DIR(self) -> Path:
        """مسیر پوشه داده‌ها"""
        path = BASE_DIR / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def LOGS_DIR(self) -> Path:
        """مسیر پوشه لاگ‌ها"""
        path = self.DATA_DIR / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def UPLOADS_DIR(self) -> Path:
        """مسیر پوشه آپلودها"""
        path = BASE_DIR / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def CACHE_DIR(self) -> Path:
        """مسیر پوشه کش"""
        path = self.DATA_DIR / "cache"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def LANG_DIR(self) -> Path:
        """مسیر پوشه فایل‌های زبان"""
        return BASE_DIR / "lang"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # متدهای کمکی
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_webhook_url(self) -> str:
        """ساخت URL کامل Webhook"""
        return f"{self.BASE_URL}/webhook/{self.BOT_ID}/{self.WEBHOOK_SECRET}"
    
    def is_admin(self, user_id: int) -> bool:
        """بررسی ادمین بودن کاربر"""
        return user_id in self.ADMIN_CHAT_IDS
    
    def get_ai_config(self) -> dict:
        """دریافت تمام تنظیمات AI به صورت دیکشنری"""
        return {
            "voice_enabled": self.AI_VOICE_ENABLED,
            "voice_max_duration": self.AI_VOICE_MAX_DURATION,
            "voice_provider": self.AI_VOICE_PROVIDER,
            "image_enabled": self.AI_IMAGE_ENABLED,
            "image_max_size_mb": self.AI_IMAGE_MAX_SIZE_MB,
            "default_model": self.AI_DEFAULT_MODEL,
            "timeout_seconds": self.AI_TIMEOUT_SECONDS,
            "max_retries": self.AI_MAX_RETRIES,
            "cache_enabled": self.AI_CACHE_ENABLED,
            "cache_ttl_hours": self.AI_CACHE_TTL_HOURS,
            "history_enabled": self.AI_HISTORY_ENABLED,
            "history_max_messages": self.AI_HISTORY_MAX_MESSAGES,
            "warmup_enabled": self.AI_WARMUP_ENABLED,
            "keep_alive_enabled": self.AI_KEEP_ALIVE_ENABLED,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ایجاد نمونه تنظیمات
# ═══════════════════════════════════════════════════════════════════════════════

settings = Settings()


# ═══════════════════════════════════════════════════════════════════════════════
# اعتبارسنجی تنظیمات ضروری
# ═══════════════════════════════════════════════════════════════════════════════

def validate_settings() -> bool:
    """
    اعتبارسنجی تنظیمات ضروری
    
    Returns:
        True اگر همه چیز درست باشد
        
    Raises:
        SystemExit اگر تنظیمات ضروری موجود نباشند
    """
    critical_missing = []
    warnings = []
    
    # بررسی‌های ضروری
    if not settings.TELEGRAM_BOT_TOKEN:
        critical_missing.append("TELEGRAM_BOT_TOKEN")
    
    if not settings.WEBHOOK_SECRET and not settings.IS_LOCAL:
        critical_missing.append("WEBHOOK_SECRET (required for production)")
    
    # بررسی‌های هشداری
    if not settings.ATRIA_API_KEY and not settings.OPENROUTER_API_KEY:
        warnings.append("ATRIA_API_KEY - AI features will use fallback mode")
    
    if not settings.ADMIN_CHAT_IDS:
        warnings.append("ADMIN_CHAT_IDS - No admins configured")
    
    if not settings.OPENWEATHERMAP_API_KEY:
        warnings.append("OPENWEATHERMAP_API_KEY - Weather feature disabled")
    
    # نمایش هشدارها
    for warning in warnings:
        logger.warning(f"⚠️ {warning}")
    
    # خروج در صورت نبود تنظیمات ضروری
    if critical_missing:
        logger.critical(f"❌ Missing critical settings: {', '.join(critical_missing)}")
        sys.exit(1)
    
    return True


# اجرای اعتبارسنجی
validate_settings()


# ═══════════════════════════════════════════════════════════════════════════════
# تنظیمات لاگینگ
# ═══════════════════════════════════════════════════════════════════════════════

# حذف handler های پیش‌فرض
logger.remove()

# فرمت لاگ
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# لاگ به کنسول
logger.add(
    sink=sys.stdout,
    level="DEBUG" if settings.DEBUG else "INFO",
    format=LOG_FORMAT,
    colorize=True,
)

# لاگ به فایل در پروداکشن
if settings.IS_PRODUCTION:
    log_file = settings.LOGS_DIR / "bot_{time:YYYY-MM-DD}.log"
    
    logger.add(
        sink=str(log_file),
        level="INFO",
        format=LOG_FORMAT,
        rotation="00:00",      # روزانه
        retention="30 days",   # نگهداری ۳۰ روز
        compression="zip",     # فشرده‌سازی
        encoding="utf-8",
    )
    
    # لاگ خطاها به فایل جداگانه
    error_log_file = settings.LOGS_DIR / "errors_{time:YYYY-MM-DD}.log"
    
    logger.add(
        sink=str(error_log_file),
        level="ERROR",
        format=LOG_FORMAT,
        rotation="00:00",
        retention="60 days",
        compression="zip",
        encoding="utf-8",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# تنظیمات Sentry (خطایابی)
# ═══════════════════════════════════════════════════════════════════════════════

if settings.SENTRY_DSN and settings.IS_PRODUCTION:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=0.2,
            profiles_sample_rate=0.1,
            environment=settings.ENVIRONMENT,
            release="smartstudentbot@2.0.0",
            integrations=[
                FastApiIntegration(),
                AsyncioIntegration(),
            ],
        )
        logger.success("🛡️ Sentry initialized successfully")
        
    except ImportError:
        logger.warning("⚠️ sentry-sdk not installed, skipping Sentry setup")
    except Exception as e:
        logger.error(f"❌ Sentry initialization failed: {e}")
else:
    if not settings.SENTRY_DSN:
        logger.debug("Sentry DSN not configured - skipping")


# ═══════════════════════════════════════════════════════════════════════════════
# نمایش تنظیمات در لاگ
# ═══════════════════════════════════════════════════════════════════════════════

logger.info("═" * 60)
logger.info("🚀 SmartStudentBot Configuration v2.0")
logger.info("═" * 60)
logger.info(f"   📍 Environment: {settings.ENVIRONMENT}")
logger.info(f"   🌐 Base URL: {settings.BASE_URL}")
logger.info(f"   🔧 Debug Mode: {settings.DEBUG}")
logger.info(f"   👥 Admins: {len(settings.ADMIN_CHAT_IDS)} configured")
logger.info("─" * 60)
logger.info("   🤖 AI Settings:")
logger.info(f"      • OpenRouter API: {'✅ Configured' if settings.OPENROUTER_API_KEY else '❌ Not set'}")
logger.info(f"      • Default Model: {settings.AI_DEFAULT_MODEL}")
logger.info(f"      • Voice Enabled: {settings.AI_VOICE_ENABLED}")
logger.info(f"      • Image Enabled: {settings.AI_IMAGE_ENABLED}")
logger.info(f"      • History Enabled: {settings.AI_HISTORY_ENABLED}")
logger.info(f"      • Cache Enabled: {settings.AI_CACHE_ENABLED}")
logger.info(f"      • Warmup Enabled: {settings.AI_WARMUP_ENABLED}")
logger.info("─" * 60)
logger.info("   🔌 Services:")
logger.info(f"      • Weather API: {'✅' if settings.OPENWEATHERMAP_API_KEY else '❌'}")
logger.info(f"      • Exchange Rate API: {'✅' if settings.EXCHANGE_RATE_API_KEY else '❌'}")
logger.info(f"      • Sentry: {'✅' if settings.SENTRY_DSN else '❌'}")
logger.info("─" * 60)
logger.info("   💾 Database Settings:")
mongo_status = "✅ Remote/Cloud" if "localhost" not in settings.MONGO_URI and settings.MONGO_URI else "⚠️ Localhost/Fallback"
logger.info(f"      • MongoDB: {mongo_status}")
logger.info(f"      • Database Name: {settings.DB_NAME}")
redis_status = "✅ Configured" if settings.REDIS_URL and "localhost" not in settings.REDIS_URL else ("⚠️ Localhost" if settings.REDIS_URL else "❌ Not set")
logger.info(f"      • Redis: {redis_status}")
logger.info("═" * 60)


# ═══════════════════════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "settings",
    "logger",
    "BASE_DIR",
    "Settings",
]