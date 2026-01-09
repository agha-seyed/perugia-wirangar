# main.py
# فایل اصلی اجرای ربات - اصلاح شده برای رفع خطای Router و IP
# ژانویه ۲۰۲۵

import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings, logger

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

dp = Dispatcher(storage=MemoryStorage())


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
        
        logger.success("✅ Bot is ready!")
        
    except Exception as e:
        logger.critical(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # ─────────────────────────────────────────────────────
    # Shutdown (پایان)
    # ─────────────────────────────────────────────────────
    
    logger.info("🛑 Shutting down...")
    
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


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

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
    except:
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
