# main.py
# فایل اصلی اجرای ربات - اصلاح شده برای رفع خطای Router و IP
# ژانویه ۲۰۲۵

import os
import sys
import io
import asyncio
from contextlib import asynccontextmanager

# تنظیم انکودینگ خروجی کنسول برای ویندوز
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from fastapi import FastAPI, Request, HTTPException
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi.middleware.cors import CORSMiddleware

from config import settings, logger
from database import db_manager

# بازپیکربندی لاگورو با UTF-8 برای جلوگیری از خطاهای cp1252
try:
    logger.remove()
    logger.add(sys.stdout, colorize=True, enqueue=True, backtrace=True, diagnose=True)
except Exception:
    pass

# ─────────────────────────────────────────────────────────────────────────────
# ساخت Bot و Dispatcher
# ─────────────────────────────────────────────────────────────────────────────

bot = Bot(
    token=settings.TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
        protect_content=False,
        link_preview_is_disabled=False,
    )
)

# ایجاد منبع ذخیره‌سازی FSM با پشتیبانی از Redis و فال‌بک حافظه
fsm_storage = MemoryStorage()
if getattr(settings, "REDIS_URL", None):
    try:
        from aiogram.fsm.storage.redis import RedisStorage
        fsm_storage = RedisStorage.from_url(settings.REDIS_URL)
        logger.info(f"🔄 Initialized RedisStorage for FSM: {settings.REDIS_URL}")
    except Exception as e:
        logger.warning(f"⚠️ Redis is not accessible ({e}). Running FSM with MemoryStorage fallback.")
        fsm_storage = MemoryStorage()

dp = Dispatcher(storage=fsm_storage)


# ─────────────────────────────────────────────────────────────────────────────
# ثبت روترها
# ─────────────────────────────────────────────────────────────────────────────

def register_routers():
    """ثبت تمام روترها با مدیریت خطا"""
    
    # لیست ماژول‌ها و نام روتر
    routers_config = [
        ("handlers.cmd_start", "start_router"),
        ("handlers.ai_handler", "ai_router"),
        ("handlers.consult_handler", "consult_router"),
        ("handlers.roommate_handler", "roommate_router"),
        ("handlers.feedback_handler", "feedback_router"),
        ("handlers.weather_handler", "weather_router"),
        ("handlers.news_handler", "news_router"),
        ("handlers.guide_handler", "guide_router"),
        ("handlers.isee_handler", "isee_router"),
        ("handlers.places_handler", "places_router"),
        ("handlers.italian_handler", "italian_router"),
        ("handlers.market_handler", "market_router"),
        ("handlers.events_handler", "events_router"),
        ("handlers.dashboard_handler", "dashboard_router"),
        ("handlers.cost_handler", "cost_router"),
        ("handlers.pagopa_handler", "pagopa_router"),
    ]
    
    registered = 0
    
    for module_name, router_var in routers_config:
        try:
            # ایمپورت داینامیک ماژول
            module = __import__(module_name, fromlist=["router"])
            # دریافت متغیر router از داخل ماژول
            router = getattr(module, "router")
            dp.include_router(router)
            logger.debug(f"   ✓ {module_name}")
            registered += 1
        except ImportError as e:
            logger.warning(f"   ⚠ {module_name}: {e}")
        except Exception as e:
            logger.error(f"   ✗ {module_name}: {e}")
    
    logger.info(f"📦 Routers registered: {registered}/{len(routers_config)}")
    
    # تنظیم AI Service
    try:
        from services.ai_service import ai_service
        ai_service.set_bot(bot)
        logger.debug("   ✓ AI Service bot reference set")
    except Exception as e:
        logger.debug(f"   ⚠ AI Service: {e}")


# ❌ نکته مهم: خط اجرای مستقیم register_routers() از اینجا حذف شد


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan (چرخه حیات برنامه)
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """مدیریت چرخه حیات (شروع و پایان)"""
    
    logger.info("=" * 50)
    logger.info("🚀 SmartStudentBot Starting...")
    logger.info("=" * 50)
    
    # اتصال به دیتابیس MongoDB
    await db_manager.connect()
    
    # ✅ انتقال ثبت روترها به اینجا (فقط یک بار اجرا می‌شود)
    register_routers()

    # ─────────────────────────────────────────────────────
    # Startup (شروع)
    # ─────────────────────────────────────────────────────
    
    try:
        # 1. اطلاعات ربات
        bot_info = await bot.get_me()
        logger.success(f"🤖 Bot: @{bot_info.username}")
        
        # 2. هوک راه‌اندازی هندلر هوش مصنوعی
        try:
            from handlers.ai_handler import on_startup as ai_startup
            await ai_startup()
            logger.info("✅ AI Handler startup hooks executed")
        except ImportError:
            logger.warning("⚠️ Could not import ai_handler hooks (module missing?)")
        except Exception as e:
            logger.error(f"❌ Error in AI startup hooks: {e}")

        # 3. تنظیم Webhook یا Polling
        if settings.IS_LOCAL:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("🔄 Mode: Polling (Local)")
        else:
            webhook_url = f"{settings.BASE_URL}/webhook/{settings.BOT_ID}/{settings.WEBHOOK_SECRET}"
            
            current = await bot.get_webhook_info()
            if current.url != webhook_url:
                await bot.set_webhook(
                    url=webhook_url,
                    allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"],
                    drop_pending_updates=True,
                )
                logger.success(f"🌐 Webhook set: {webhook_url}")
            else:
                logger.info("🌐 Webhook already configured")
        
        # 4. تنظیم دکمه منوی اختصاصی مینی‌اپ برای گوشی‌ها و تلگرام موبایل
        try:
            from aiogram.types import MenuButtonWebApp, WebAppInfo
            webapp_url = settings.WEBAPP_URL or "https://smartstudentbot-webapp.onrender.com"
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="🚀 مینی‌اپ پروجا",
                    web_app=WebAppInfo(url=webapp_url)
                )
            )
            logger.success(f"📱 Telegram Chat Menu Button configured: {webapp_url}")
        except Exception as e:
            logger.warning(f"⚠️ Could not set chat menu button: {e}")

        logger.success("✅ Bot is ready!")
        
    except Exception as e:
        logger.critical(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # ─────────────────────────────────────────────────────
    # Shutdown (پایان)
    # ─────────────────────────────────────────────────────
    
    logger.info("🛑 Shutting down...")
    
    # بستن اتصال دیتابیس
    await db_manager.close()
    
    try:
        try:
            from handlers.ai_handler import on_shutdown as ai_shutdown
            await ai_shutdown()
        except Exception as e:
            logger.error(f"Error stopping AI handler: {e}")

        try:
            from services.ai_service import ai_service
            ai_service.save_stats()
        except:
            pass
        
        await bot.session.close()
        logger.info("👋 Goodbye!")
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SmartStudentBot API",
    description="ربات هوشمند دانشجویان ایرانی در پروجا",
    version="1.0.0",
    docs_url="/docs" if settings.IS_LOCAL else None,
    redoc_url=None,
    lifespan=lifespan,
)

# تنظیمات CORS برای مینی‌اپ
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # در پروداکشن به دامین Vercel محدود شود
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

try:
    from api.webapp_api import router as webapp_router
    app.include_router(webapp_router)
except ImportError as e:
    logger.error(f"Failed to import webapp_router: {e}")

@app.get("/")
async def root():
    return {"name": "SmartStudentBot", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


@app.get("/ready")
async def readiness_check():
    try:
        await bot.get_me()
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(503, "Bot not ready")


@app.post(f"/webhook/{settings.BOT_ID}/{settings.WEBHOOK_SECRET}")
async def webhook_handler(request: Request):
    """Webhook endpoint"""
    
    # ✅ اصلاح شده: دریافت IP واقعی از پشت پروکسی Render
    if not settings.IS_LOCAL:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # اولین IP در لیست، IP واقعی کاربر/تلگرام است
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # لیست IPهای رنج تلگرام (اختیاری برای لاگ)
        # telegram_ips = ("149.154.", "91.108.", "185.76.")
        
        # لاگ را تمیزتر کردیم که فقط در صورت نیاز نمایش دهد
        # logger.info(f"📩 Incoming update from IP: {client_ip}")

    try:
        update = types.Update(**(await request.json()))
        await dp.feed_update(bot=bot, update=update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": False}


async def run_polling():
    """اجرای ربات در حالت Polling برای محیط توسعه محلی"""
    logger.info("=" * 50)
    logger.info("🚀 SmartStudentBot Starting in POLLING mode...")
    logger.info("=" * 50)
    
    # اتصال به دیتابیس
    await db_manager.connect()
    
    # ثبت روترها
    register_routers()
    
    # هوک استارتاپ هوش مصنوعی
    try:
        from handlers.ai_handler import on_startup as ai_startup
        await ai_startup()
    except Exception as e:
        logger.debug(f"AI startup hook: {e}")
        
    try:
        bot_info = await bot.get_me()
        logger.success(f"🤖 Bot Polling started: @{bot_info.username}")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"])
    finally:
        logger.info("🛑 Polling stopped, cleaning up...")
        try:
            from handlers.ai_handler import on_shutdown as ai_shutdown
            await ai_shutdown()
        except Exception:
            pass
        await db_manager.close()
        await bot.session.close()


# ─────────────────────────────────────────────────────────────────────────────
# نقطه ورود
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if settings.IS_LOCAL:
        try:
            asyncio.run(run_polling())
        except KeyboardInterrupt:
            logger.info("👋 Stopped by user")
    else:
        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=settings.PORT,
            workers=1,
        )
