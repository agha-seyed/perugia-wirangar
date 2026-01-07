# config.py
# فایل تنظیمات اصلی - نسخه اصلاح‌شده و نهایی
# ژانویه ۲۰۲۵

import os
import sys
from typing import List
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# بارگذاری .env
load_dotenv(override=True)

# مسیر پایه
BASE_DIR = Path(__file__).parent


class Settings:
    """تنظیمات اصلی پروژه"""
    
    # ─────────────────────────────────────────────────────
    # تلگرام
    # ─────────────────────────────────────────────────────
    
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    BOT_ID: str = os.getenv("BOT_ID", "perugia").strip()
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "").strip()
    CHANNEL_ID: str = os.getenv("CHANNEL_ID", "").strip()
    
    # لیست ادمین‌ها
    @property
    def ADMIN_CHAT_IDS(self) -> List[int]:
        ids_str = os.getenv("ADMIN_CHAT_IDS", "").strip()
        if not ids_str:
            return []
        try:
            return [int(x.strip()) for x in ids_str.split(",") if x.strip().isdigit()]
        except ValueError:
            return []
    
    # ─────────────────────────────────────────────────────
    # سرور
    # ─────────────────────────────────────────────────────
    
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000").strip().rstrip("/")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # ─────────────────────────────────────────────────────
    # دیتابیس
    # ─────────────────────────────────────────────────────
    
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://smartstudentbot:supersecretpassword123@postgres:5432/smartstudentbot"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379")
    
    # ─────────────────────────────────────────────────────
    # کلیدهای API
    # ─────────────────────────────────────────────────────
    
    # OpenRouter (اصلی برای AI)
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "").strip()
    
    # HuggingFace (پشتیبان)
    HUGGINGFACE_API_KEY: str = os.getenv("HUGGINGFACE_API_KEY", "").strip()
    
    # آب و هوا
    OPENWEATHERMAP_API_KEY: str = os.getenv("OPENWEATHERMAP_API_KEY", "").strip()
    
    # نرخ ارز
    EXCHANGE_RATE_API_KEY: str = os.getenv("EXCHANGE_RATE_API_KEY", "").strip()
    
    # ─────────────────────────────────────────────────────
    # ویژگی‌ها
    # ─────────────────────────────────────────────────────
    
    @property
    def FEATURE_AI_ENABLED(self) -> bool:
        return os.getenv("FEATURE_AI_ENABLED", "True").lower() in ("true", "1", "yes")
    
    @property
    def FEATURE_NEWS_ENABLED(self) -> bool:
        return os.getenv("FEATURE_NEWS_ENABLED", "True").lower() in ("true", "1", "yes")
    
    @property
    def FEATURE_GAMIFICATION(self) -> bool:
        return os.getenv("FEATURE_GAMIFICATION", "False").lower() in ("true", "1", "yes")
    
    # ─────────────────────────────────────────────────────
    # محیط
    # ─────────────────────────────────────────────────────
    
    @property
    def ENVIRONMENT(self) -> str:
        if "localhost" in self.BASE_URL or "127.0.0.1" in self.BASE_URL:
            return "development"
        return os.getenv("ENVIRONMENT", "production")
    
    @property
    def IS_LOCAL(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    # ─────────────────────────────────────────────────────
    # Sentry
    # ─────────────────────────────────────────────────────
    
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "").strip()
    
    # ─────────────────────────────────────────────────────
    # مسیرها
    # ─────────────────────────────────────────────────────
    
    @property
    def DATA_DIR(self) -> Path:
        path = BASE_DIR / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def UPLOADS_DIR(self) -> Path:
        path = BASE_DIR / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path


# ایجاد نمونه
settings = Settings()


# ─────────────────────────────────────────────────────────────────────────────
# اعتبارسنجی
# ─────────────────────────────────────────────────────────────────────────────

critical_missing = []

if not settings.TELEGRAM_BOT_TOKEN:
    critical_missing.append("TELEGRAM_BOT_TOKEN")

if not settings.WEBHOOK_SECRET and not settings.IS_LOCAL:
    critical_missing.append("WEBHOOK_SECRET")

if critical_missing:
    logger.critical(f"❌ متغیرهای ضروری تنظیم نشده: {', '.join(critical_missing)}")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# لاگینگ
# ─────────────────────────────────────────────────────────────────────────────

logger.remove()

log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

logger.add(
    sink=sys.stdout,
    level="DEBUG" if settings.IS_LOCAL else "INFO",
    format=log_format,
    colorize=True,
)

# لاگ به فایل در پروداکشن
if not settings.IS_LOCAL:
    log_file = settings.DATA_DIR / "logs" / "bot_{time:YYYY-MM-DD}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        sink=str(log_file),
        level="INFO",
        format=log_format,
        rotation="00:00",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sentry
# ─────────────────────────────────────────────────────────────────────────────

if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=1.0 if settings.IS_LOCAL else 0.2,
            profiles_sample_rate=1.0 if settings.IS_LOCAL else 0.1,
            environment=settings.ENVIRONMENT,
            release="smartstudentbot@1.0.0",
            integrations=[FastApiIntegration()],
        )
        logger.success("🛡️ Sentry initialized")
    except ImportError:
        logger.warning("⚠️ sentry-sdk not installed")
    except Exception as e:
        logger.error(f"❌ Sentry init failed: {e}")
else:
    logger.debug("Sentry DSN not set - skipping")


# ─────────────────────────────────────────────────────────────────────────────
# لاگ تنظیمات
# ─────────────────────────────────────────────────────────────────────────────

logger.info("=" * 50)
logger.info("🚀 SmartStudentBot Configuration")
logger.info("=" * 50)
logger.info(f"   Environment: {settings.ENVIRONMENT}")
logger.info(f"   Base URL: {settings.BASE_URL}")
logger.info(f"   Admins: {settings.ADMIN_CHAT_IDS}")
logger.info(f"   AI Enabled: {settings.FEATURE_AI_ENABLED}")
logger.info(f"   OpenRouter: {'✅' if settings.OPENROUTER_API_KEY else '❌'}")
logger.info(f"   HuggingFace: {'✅' if settings.HUGGINGFACE_API_KEY else '❌'}")
logger.info(f"   Weather API: {'✅' if settings.OPENWEATHERMAP_API_KEY else '❌'}")
logger.info("=" * 50)


# ─────────────────────────────────────────────────────────────────────────────
# Export
# ─────────────────────────────────────────────────────────────────────────────

__all__ = ["settings", "logger", "BASE_DIR"]