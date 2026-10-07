# handlers/pagopa_handler.py
# راهنمای تعاملی پرداخت شهریه، عوارض و قبوض با سیستم PagoPA ایتالیا
# نسخه ۱.۰ - ژانویه ۲۰۲۶

from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import logger
from handlers.cmd_start import get_text, get_user_lang

router = Router()
router.name = "pagopa_handler"

# ─────────────────────────────────────────────────────────
# کیبوردهای منوی PagoPA
# ─────────────────────────────────────────────────────────

def get_pagopa_main_keyboard(lang: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد اصلی راهنمای PagoPA"""
    buttons = [
        [
            InlineKeyboardButton(text="📱 پرداخت آنلاین (اپ بانک / IO / کارت)", callback_data="pagopa_online"),
            InlineKeyboardButton(text="🏪 پرداخت حضوری در تابانچی (Tabacchi)", callback_data="pagopa_tabacchi")
        ],
        [
            InlineKeyboardButton(text="🏤 پرداخت در اداره پست (Poste)", callback_data="pagopa_poste"),
            InlineKeyboardButton(text="🔍 آناتومی فیش (کد IUV چیست؟)", callback_data="pagopa_anatomy")
        ],
        [
            InlineKeyboardButton(text="⚠️ ثبت نشدن پرداخت در SOL و سوالات متداول", callback_data="pagopa_faq")
        ],
        [
            InlineKeyboardButton(text=get_text(lang, "back_to_guides", "🔙 بازگشت به راهنماها"), callback_data="guides"),
            InlineKeyboardButton(text=get_text(lang, "back_to_menu", "🏠 منوی اصلی"), callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pagopa_back_keyboard(lang: str = "fa") -> InlineKeyboardMarkup:
    """کیبورد بازگشت به منوی PagoPA"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 سایر روش‌های PagoPA", callback_data="pagopa_menu"),
            InlineKeyboardButton(text=get_text(lang, "back_to_menu", "🏠 منوی اصلی"), callback_data="main_menu")
        ]
    ])


# ─────────────────────────────────────────────────────────
# هندلرهای پیام و کال‌بک
# ─────────────────────────────────────────────────────────

@router.callback_query(F.data.in_(["pagopa_menu", "pagopa_guide"]))
async def pagopa_menu(callback: types.CallbackQuery):
    """منوی اصلی راهنمای جامع PagoPA"""
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    
    text = (
        "💳 <b>راهنمای جامع پرداخت‌های دولتی و دانشگاهی با سامانه PagoPA</b>\n\n"
        "سامانه <b>PagoPA</b> شبکه سراسری و رسمی پرداخت به سازمان‌های دولتی، دانشگاه پروجا (UniPG) و سازمان رفاهی ADiSU است.\n\n"
        "📌 <b>پرداخت‌های متداول دانشجویان در پروجا:</b>\n"
        "• قسط اول، دوم و سوم شهریه در پورتال SOL\n"
        "• عوارض استانی اومبریا (Tassa Regionale)\n"
        "• اجاره خوابگاه ادیسو یا جریمه‌های دانشجویی\n"
        "• هزینه تمبر مالیاتی مجازی (Marca da Bollo)\n\n"
        "👇 <i>روش مورد نظر خود را برای مشاهده دستورالعمل گام‌به‌گام انتخاب کنید:</i>"
    )
    
    keyboard = get_pagopa_main_keyboard(lang)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "pagopa_online")
async def pagopa_online_guide(callback: types.CallbackQuery):
    """راهنمای پرداخت آنلاین"""
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    
    text = (
        "📱 <b>روش اول: پرداخت آنلاین و سریع (کمترین کارمزد)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>۱. از طریق پورتال دانشجویی SOL:</b>\n"
        "• وارد بخش <code>Segreteria -> Pagamenti</code> شوید.\n"
        "• روی فیش صادر شده کلیک کنید و گزینه <b>Paga Online</b> را بزنید.\n"
        "• از طریق کارت بانکی (Visa/Mastercard/PostePay) یا حساب بانکی پرداخت کنید.\n\n"
        "<b>۲. از طریق اپلیکیشن بانک یا Revolut (کد CBILL):</b>\n"
        "• در اپلیکیشن بانکی خود بخش <b>CBILL / PagoPA</b> را باز کنید.\n"
        "• شناسه سازمان (Codice Ente دانشگاه پروجا: <code>00448820548</code>) را وارد کنید.\n"
        "• کد ۱۸ رقمی <b>Codice Avviso (IUV)</b> را وارد یا بارکد را با دوربین اسکن کنید.\n\n"
        "<b>۳. از طریق اپلیکیشن ملی IO:</b>\n"
        "• با SPID وارد اپلیکیشن IO شوید.\n"
        "• بارکد فیش را اسکن کرده و با کارمزد بسیار ناچیز پرداخت نمایید.\n\n"
        "💡 <b>مزیت:</b> بدون نیاز به خروج از خانه، کارمزد حدود ۰.۵ الی ۱.۵ یورو و صدور آنی رسید دیجیتال (RT)."
    )
    
    await callback.message.edit_text(text, reply_markup=get_pagopa_back_keyboard(lang), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "pagopa_tabacchi")
async def pagopa_tabacchi_guide(callback: types.CallbackQuery):
    """راهنمای پرداخت در تابانچی"""
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    
    text = (
        "🏪 <b>روش دوم: پرداخت حضوری در توتون‌فروشی‌ها (Tabacchi / PuntoLIS)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "اگر هنوز کارت بانکی یا اینترنت فعال ندارید، این ساده‌ترین راه پرداخت نقدی در پروجا است!\n\n"
        "<b>مراحل گام‌به‌گام:</b>\n"
        "۱. فایل PDF فیش (Avviso di Pagamento) را دانلود کنید (پرینت کاغذی الزامی نیست؛ نمایش واضح بارکد روی موبایل کافی است).\n"
        "۲. به نزدیک‌ترین تابانچی دارای نماد <b>T</b> یا تابلوهای <b>PuntoLIS / Mooney</b> مراجعه کنید.\n"
        "۳. به متصدی بگویید:\n"
        "   🗣 <i>\"Salve, vorrei pagare questo avviso PagoPA per favore.\"</i>\n"
        "   (سلام، می‌خواهم این فیش پاگوپی‌آ را پرداخت کنم).\n"
        "۴. متصدی بارکد را اسکن می‌کند. مبلغ را به همراه کارمزد (حدود ۲ تا ۲.۵ یورو) نقدی یا با کارت بپردازید.\n"
        "۵. <b>بسیار مهم:</b> فیش کاغذی (Scontrino di Pagamento) که متصدی به شما می‌دهد را دور نیندازید! تا پایان فارغ‌التحصیلی از آن عکس بگیرید و نگه دارید."
    )
    
    await callback.message.edit_text(text, reply_markup=get_pagopa_back_keyboard(lang), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "pagopa_poste")
async def pagopa_poste_guide(callback: types.CallbackQuery):
    """راهنمای پرداخت در اداره پست"""
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    
    text = (
        "🏤 <b>روش سوم: پرداخت در باجه یا خودپرداز اداره پست (Poste Italiane)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "در تمام شعب پست پروجا (به‌ویژه شعبه مرکزی Piazza Matteotti یا شعبه ایستگاه قطار Fontivegge):\n\n"
        "<b>روش‌ها:</b>\n"
        "• <b>باجه حضوری:</b> برگه پرینت شده فیش را به کارمند باجه پست تحویل دهید و هزینه را پرداخت کنید.\n"
        "• <b>دستگاه‌های خودپرداز Postamat:</b> کارت بانکی خود را وارد کرده، گزینه Pagamenti و سپس PagoPA را انتخاب و بارکدخوان فیش را اسکن کنید.\n\n"
        "💶 <b>کارمزد:</b> برای دارندگان حساب پست‌پِی حدود ۱ یورو و برای پرداخت نقدی حدود ۲ یورو است."
    )
    
    await callback.message.edit_text(text, reply_markup=get_pagopa_back_keyboard(lang), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "pagopa_anatomy")
async def pagopa_anatomy_guide(callback: types.CallbackQuery):
    """آناتومی و مشخصات فیش PagoPA"""
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    
    text = (
        "🔍 <b>کدهای روی برگه PagoPA به چه معنا هستند؟</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "روی هر فیش پرداختی که از SOL یا ADiSU دانلود می‌کنید، بخش‌های زیر وجود دارد:\n\n"
        "۱. <b>Codice Avviso (کد IUV):</b>\n"
        "یک کد ۱۸ رقمی بدون فاصله (مثل <code>301000000123456789</code>) که شناسه اختصاصی بدهی شماست.\n\n"
        "۲. <b>Codice Fiscale dell'Ente:</b>\n"
        "کد مالیاتی سازمانی که پول را دریافت می‌کند (برای دانشگاه پروجا: <code>00448820548</code>).\n\n"
        "۳. <b>Data di Scadenza:</b>\n"
        "تاریخ انقضای فیش. پس از این تاریخ، ممکن است فیش منقضی شود و باید در SOL روی آن کلیک کنید تا فیش جدید با مهلت جدید تولید شود.\n\n"
        "۴. <b>QR Code / Barcode:</b>\n"
        "مربع شطرنجی که برای اسکن سریع با گوشی یا در باجه‌های تابانچی استفاده می‌شود."
    )
    
    await callback.message.edit_text(text, reply_markup=get_pagopa_back_keyboard(lang), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "pagopa_faq")
async def pagopa_faq_guide(callback: types.CallbackQuery):
    """سوالات متداول و خطای سبز نشدن وضعیت"""
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    
    text = (
        "⚠️ <b>نکات بحرانی و سوالات رایج PagoPA در پروجا:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "❓ <b>من پرداخت کردم ولی در SOL هنوز چراغ قرمز است و سبز نشده! چرا؟</b>\n"
        "✅ سیستم بانکی ایتالیا و سرورهای دانشگاه پروجا بلادرنگ متصل نیستند. ثبت و تسویه نهایی معمولاً <b>۲۴ الی ۷۲ ساعت کاری</b> طول می‌کشد. هرگز نگران نباشید و <b>به هیچ وجه دوباره پرداخت نکنید</b>!\n\n"
        "❓ <b>رسید پرداخت (Ricevuta Telematica - RT) چیست؟</b>\n"
        "✅ پس از پرداخت، سامانه یک کد پیگیری و فیش دیجیتال صادر می‌کند که اثبات رسمی پرداخت شماست. اگر بعد از ۳ روز کاری ثبت نشد، با ارسال تیکت و ضمیمه کردن این رسید به دایره شهریه (Ufficio Tasse UniPG)، فوراً تأیید می‌شود.\n\n"
        "❓ <b>فیش اشتباه پرداخت کردم، آیا پولم می‌سوزد؟</b>\n"
        "✅ در صورت پرداخت اشتباه یا اضافه، می‌توانید درخواست رسمی استرداد (Domanda di Rimborso) در پورتال ثبت کنید."
    )
    
    await callback.message.edit_text(text, reply_markup=get_pagopa_back_keyboard(lang), parse_mode="HTML")
    await callback.answer()


@router.message(F.text.in_(["/pagopa", "پرداخت شهریه", "راهنمای pagopa", "pagopa"]))
async def pagopa_command(message: types.Message):
    """دستور مستقیم برای باز کردن راهنمای PagoPA"""
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    
    text = (
        "💳 <b>راهنمای پرداخت‌های دولتی و شهریه دانشگاه با PagoPA</b>\n\n"
        "برای مشاهده آموزش گام‌به‌گام روش‌های پرداخت آنلاین و حضوری در شهر پروجا، گزینه‌های زیر را ببینید:"
    )
    keyboard = get_pagopa_main_keyboard(lang)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
