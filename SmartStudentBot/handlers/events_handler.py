# handlers/events_handler.py
# سیستم رویدادها، دورهمی‌ها و تقویم فرهنگی دانشجویی پروجا (چندزبانه)

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db_manager

try:
    from handlers.cmd_start import get_user_lang, get_text, get_user_lang_code
except ImportError:
    def get_user_lang(user_id: int) -> dict: return {}
    def get_text(lang: dict, key: str, default: str = "") -> str: return default
    def get_user_lang_code(user_id: int) -> str: return "fa"

router = Router()
router.name = "events_handler"

@router.message(Command("events"))
@router.callback_query(F.data.in_(["events", "events_refresh"]))
async def show_events(event: types.Message | types.CallbackQuery):
    """نمایش لیست رویدادها و دورهمی‌های دانشجویی به زبان کاربر"""
    user_id = event.from_user.id
    lang_code = get_user_lang_code(user_id)
    
    events_list = await db_manager.get_events()
    
    if lang_code == "it":
        text = "🎉 <b>Eventi, Incontri e Tour Studenteschi a Perugia</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        if not events_list:
            text += "Nessun nuovo evento registrato al momento.\n"
        else:
            for i, ev in enumerate(events_list, 1):
                title = ev.get("title", "Senza titolo")
                date = ev.get("date", "Data da definire")
                location = ev.get("location", "Perugia")
                desc = ev.get("description", "")
                text += f"<b>{i}. {title}</b>\n"
                text += f"   📅 Data: <b>{date}</b>\n"
                text += f"   📍 Luogo: <b>{location}</b>\n"
                if desc:
                    text += f"   ℹ️ Info: <i>{desc}</i>\n"
                text += "─────────────────────\n"
        text += "\n💡 <i>Condividi con i tuoi amici per partecipare insieme agli eventi!</i>"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Aggiorna Eventi", callback_data="events_refresh"),
                InlineKeyboardButton(text="📤 Condividi", switch_inline_query="🎉 Eventi per studenti Perugia")
            ],
            [
                InlineKeyboardButton(text="🔙 Torna alla Guida", callback_data="guide:main"),
                InlineKeyboardButton(text="🏠 Menu Principale", callback_data="main_menu")
            ]
        ])
    elif lang_code == "en":
        text = "🎉 <b>Student Events, Meetups & Tours in Perugia</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        if not events_list:
            text += "No upcoming events scheduled right now.\n"
        else:
            for i, ev in enumerate(events_list, 1):
                title = ev.get("title", "Untitled")
                date = ev.get("date", "TBD")
                location = ev.get("location", "Perugia")
                desc = ev.get("description", "")
                text += f"<b>{i}. {title}</b>\n"
                text += f"   📅 Date: <b>{date}</b>\n"
                text += f"   📍 Location: <b>{location}</b>\n"
                if desc:
                    text += f"   ℹ️ Details: <i>{desc}</i>\n"
                text += "─────────────────────\n"
        text += "\n💡 <i>Share with friends to join student gatherings and city tours together!</i>"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Refresh Events", callback_data="events_refresh"),
                InlineKeyboardButton(text="📤 Share with Friends", switch_inline_query="🎉 Perugia Student Events")
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Guide", callback_data="guide:main"),
                InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")
            ]
        ])
    else:
        text = "🎉 <b>رویدادها، دورهمی‌ها و تورهای دانشجویی پروجا</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        if not events_list:
            text += "در حال حاضر رویداد جدیدی ثبت نشده است.\n"
        else:
            for i, ev in enumerate(events_list, 1):
                title = ev.get("title", "بدون عنوان")
                date = ev.get("date", "نامشخص")
                location = ev.get("location", "پروجا")
                desc = ev.get("description", "")
                text += f"<b>{i}. {title}</b>\n"
                text += f"   📅 زمان: <b>{date}</b>\n"
                text += f"   📍 مکان: <b>{location}</b>\n"
                if desc:
                    text += f"   ℹ️ توضیحات: <i>{desc}</i>\n"
                text += "─────────────────────\n"
        text += "\n💡 <i>برای هماهنگی جهت دورهمی‌ها یا شرکت در برنامه‌ها، با دوستان خود به اشتراک بگذارید!</i>"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 بروزرسانی رویدادها", callback_data="events_refresh"),
                InlineKeyboardButton(text="📤 اشتراک با دوستان", switch_inline_query="🎉 رویدادهای دانشجویی پروجا")
            ],
            [
                InlineKeyboardButton(text="🔙 بازگشت به راهنما", callback_data="guide:main"),
                InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="main_menu")
            ]
        ])
    
    if isinstance(event, types.CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception:
            await event.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=keyboard, parse_mode="HTML")
