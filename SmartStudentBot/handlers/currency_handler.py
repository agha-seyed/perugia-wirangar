# handlers/currency_handler.py
# بخش استعلام زنده و لحظه‌ای نرخ ارز، طلا و رمزارز با BrsApi
# طراحی سلطنتی، پشتیبانی از چندزبانه و اتصال به محاسبه‌گر ISEE

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from contextlib import suppress

from config import settings, logger
from services.currency_service import currency_service
from handlers.cmd_start import get_text, get_user_lang, get_user_lang_code_async

router = Router()

def get_currency_keyboard(is_group: bool = False) -> InlineKeyboardMarkup:
    """
    کیبورد تعاملی تابلو نرخ ارز و طلا
    """
    webapp_url = settings.WEBAPP_URL or "https://smartstudentbot-webapp.onrender.com"
    
    if is_group:
        webapp_btn = InlineKeyboardButton(
            text="🌟 مینی‌اپ پروجا 🚀",
            url=webapp_url
        )
    else:
        webapp_btn = InlineKeyboardButton(
            text="🌟 مینی‌اپ پروجا 🚀",
            web_app=WebAppInfo(url=webapp_url)
        )

    buttons = [
        [
            InlineKeyboardButton(text="🧮 محاسبه هوشمند ISEE با نرخ روز", callback_data="isee"),
        ],
        [
            InlineKeyboardButton(text="🔄 بروزرسانی قیمت‌ها", callback_data="refresh_currency"),
            webapp_btn
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("currency", "rates", "arz", "toman"))
async def cmd_currency_rates(message: types.Message):
    """
    نمایش تابلو زنده نرخ ارز و طلا با دستورات متنی
    """
    lang_code = await get_user_lang_code_async(message.from_user.id)
    is_group = message.chat.type in ["group", "supergroup"]

    # ارسال پیام موقت در صورت تاخیر شبکه
    loading_msg = await message.answer("⏳ در حال استعلام آخرین مظنه بازار آزاد...")
    
    try:
        data = await currency_service.get_all_rates(force_refresh=False)
        text = currency_service.format_currency_message(data, lang_code=lang_code)
        
        await loading_msg.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=get_currency_keyboard(is_group=is_group),
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error in cmd_currency_rates: {e}")
        await loading_msg.edit_text(
            "⚠️ متأسفانه در حال حاضر ارتباط با وب‌سرویس نرخ ارز برقرار نشد. لطفاً چند لحظه دیگر امتحان فرمایید.",
            reply_markup=get_currency_keyboard(is_group=is_group)
        )


@router.callback_query(F.data.in_(["currency_rates", "currency_menu", "refresh_currency"]))
async def cb_currency_rates(callback: types.CallbackQuery):
    """
    کالبک دکمه منوی اصلی یا دکمه بروزرسانی
    """
    force = (callback.data == "refresh_currency")
    is_group = callback.message.chat.type in ["group", "supergroup"]
    lang_code = await get_user_lang_code_async(callback.from_user.id)

    if force:
        with suppress(Exception):
            await callback.answer("🔄 در حال بروزرسانی نرخ‌های لحظه‌ای...", show_alert=False)

    try:
        data = await currency_service.get_all_rates(force_refresh=force)
        text = currency_service.format_currency_message(data, lang_code=lang_code)

        await callback.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=get_currency_keyboard(is_group=is_group),
            disable_web_page_preview=True
        )
        if force:
            with suppress(Exception):
                await callback.answer("✅ نرخ‌ها با موفقیت بروزرسانی شدند!", show_alert=False)
    except Exception as e:
        logger.debug(f"cb_currency_rates notice: {e}")
        with suppress(Exception):
            await callback.answer("نرخ‌ها در وضعیت بروز قرار دارند.", show_alert=False)
