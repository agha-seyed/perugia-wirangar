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
    """کیبورد اصلی راهنمای PagoPA به زبان کاربر"""
    if lang == "it":
        buttons = [
            [
                InlineKeyboardButton(text="📱 Pagamento Online (App / IO / Carta)", callback_data="pagopa_online"),
                InlineKeyboardButton(text="🏪 Pagamento dal Tabaccaio (PuntoLIS)", callback_data="pagopa_tabacchi")
            ],
            [
                InlineKeyboardButton(text="🏤 Pagamento alle Poste (Poste)", callback_data="pagopa_poste"),
                InlineKeyboardButton(text="🔍 Cos'è il codice IUV?", callback_data="pagopa_anatomy")
            ],
            [
                InlineKeyboardButton(text="⚠️ FAQ e Pagamento non registrato su SOL", callback_data="pagopa_faq")
            ],
            [
                InlineKeyboardButton(text=get_text(lang, "back_to_guides", "🔙 Guide"), callback_data="guides"),
                InlineKeyboardButton(text=get_text(lang, "back_to_menu", "🏠 Menu Principale"), callback_data="main_menu")
            ]
        ]
    elif lang == "en":
        buttons = [
            [
                InlineKeyboardButton(text="📱 Online Payment (App / IO / Card)", callback_data="pagopa_online"),
                InlineKeyboardButton(text="🏪 Pay at Tabacchi (PuntoLIS)", callback_data="pagopa_tabacchi")
            ],
            [
                InlineKeyboardButton(text="🏤 Pay at Post Office (Poste)", callback_data="pagopa_poste"),
                InlineKeyboardButton(text="🔍 What is IUV code?", callback_data="pagopa_anatomy")
            ],
            [
                InlineKeyboardButton(text="⚠️ FAQ & Payment not updated on SOL", callback_data="pagopa_faq")
            ],
            [
                InlineKeyboardButton(text=get_text(lang, "back_to_guides", "🔙 Guides"), callback_data="guides"),
                InlineKeyboardButton(text=get_text(lang, "back_to_menu", "🏠 Main Menu"), callback_data="main_menu")
            ]
        ]
    else:
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
    """کیبورد بازگشت به منوی PagoPA به زبان کاربر"""
    if lang == "it":
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Altre modalità PagoPA", callback_data="pagopa_menu"),
                InlineKeyboardButton(text=get_text(lang, "back_to_menu", "🏠 Menu Principale"), callback_data="main_menu")
            ]
        ])
    elif lang == "en":
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Other PagoPA methods", callback_data="pagopa_menu"),
                InlineKeyboardButton(text=get_text(lang, "back_to_menu", "🏠 Main Menu"), callback_data="main_menu")
            ]
        ])
    else:
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
    
    if lang == "it":
        text = (
            "💳 <b>Guida Completa ai Pagamenti Universitari e Pubblici con PagoPA</b>\n\n"
            "Il sistema <b>PagoPA</b> è la piattaforma nazionale ufficiale per i pagamenti verso la Pubblica Amministrazione, l'Università degli Studi di Perugia (UniPG) e l'ADiSU Umbria.\n\n"
            "📌 <b>Pagamenti più frequenti per gli studenti a Perugia:</b>\n"
            "• Rate delle tasse universitarie sul portale SOL\n"
            "• Tassa Regionale per il Diritto allo Studio\n"
            "• Canoni alloggi ADiSU e relativi depositi cauzionali\n"
            "• Imposta di bollo virtuale (Marca da Bollo)\n\n"
            "👇 <i>Seleziona la modalità desiderata per visualizzare la guida passo-passo:</i>"
        )
    elif lang == "en":
        text = (
            "💳 <b>Comprehensive Guide to University & Public Payments with PagoPA</b>\n\n"
            "The <b>PagoPA</b> system is Italy's official national payment network for public entities, University of Perugia (UniPG), and ADiSU Umbria.\n\n"
            "📌 <b>Common student payments in Perugia:</b>\n"
            "• Tuition fee installments on the SOL portal\n"
            "• Regional student tax (Tassa Regionale)\n"
            "• ADiSU dormitory rents and deposits\n"
            "• Virtual revenue stamps (Marca da Bollo)\n\n"
            "👇 <i>Select a method below for step-by-step instructions:</i>"
        )
    else:
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
    
    if lang == "it":
        text = (
            "📱 <b>Metodo 1: Pagamento Online Veloce (Commissioni Minime)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>1. Tramite il portale studenti SOL:</b>\n"
            "• Accedi a <code>Segreteria -> Pagamenti</code>.\n"
            "• Clicca sul bollettino emesso e seleziona <b>Paga Online</b>.\n"
            "• Paga con carta di credito/debito (Visa, Mastercard, PostePay) o conto bancario.\n\n"
            "<b>2. Tramite la tua App Bancaria o Revolut (Codice CBILL):</b>\n"
            "• Apri la sezione <b>CBILL / PagoPA</b> nella tua app bancaria.\n"
            "• Inserisci il Codice Ente UniPG: <code>00448820548</code>.\n"
            "• Digita il <b>Codice Avviso (IUV)</b> di 18 cifre o scansiona il codice a barre.\n\n"
            "<b>3. Tramite l'App IO:</b>\n"
            "• Accedi all'App IO con SPID o CIE.\n"
            "• Scansiona il codice a barre dell'avviso e completa il pagamento.\n\n"
            "💡 <b>Vantaggi:</b> Nessun bisogno di uscire di casa, commissioni ridotte (~0,50€ - 1,50€) e ricevuta telematica immediata (RT)."
        )
    elif lang == "en":
        text = (
            "📱 <b>Method 1: Fast Online Payment (Lowest Fees)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>1. Via the SOL Student Portal:</b>\n"
            "• Go to <code>Segreteria -> Pagamenti</code>.\n"
            "• Click on the invoice and choose <b>Paga Online</b>.\n"
            "• Pay securely using your debit/credit card (Visa, Mastercard, PostePay) or bank transfer.\n\n"
            "<b>2. Via your Banking App or Revolut (CBILL Code):</b>\n"
            "• Open the <b>CBILL / PagoPA</b> section in your bank app.\n"
            "• Enter the UniPG Institution Code: <code>00448820548</code>.\n"
            "• Type the 18-digit <b>Codice Avviso (IUV)</b> or scan the barcode.\n\n"
            "<b>3. Via the IO App:</b>\n"
            "• Log in to IO with your SPID or CIE.\n"
            "• Scan the QR code on the payment notice and pay instantly.\n\n"
            "💡 <b>Benefits:</b> Quick, low transaction fee (€0.50 - €1.50), and instant electronic receipt (RT)."
        )
    else:
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
    
    if lang == "it":
        text = (
            "🏪 <b>Metodo 2: Pagamento di Persona dal Tabaccaio (PuntoLIS / Mooney)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Se non hai ancora una carta o un conto attivo in Italia, questo è il modo più pratico per pagare in contanti a Perugia!\n\n"
            "<b>Procedura passo-passo:</b>\n"
            "1. Scarica l'Avviso di Pagamento PDF (basta mostrarlo sullo smartphone).\n"
            "2. Recati presso un tabaccaio con insegna <b>T</b> o cartello <b>PuntoLIS / Mooney</b>.\n"
            "3. Dì al negoziante:\n"
            "   🗣 <i>\"Salve, vorrei pagare questo avviso PagoPA per favore.\"</i>\n"
            "4. L'esercente scansionerà il codice a barre. Paga l'importo più la commissione (~2,00€ - 2,50€) in contanti o con carta.\n"
            "5. <b>Importante:</b> Conserva sempre lo scontrino cartaceo come prova di pagamento!\n"
        )
    elif lang == "en":
        text = (
            "🏪 <b>Method 2: In-Person Cash Payment at Tabacchi (PuntoLIS / Mooney)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "If you don't have an active Italian bank card yet, this is the easiest cash payment option in Perugia!\n\n"
            "<b>Step-by-step:</b>\n"
            "1. Download the PDF payment notice (showing the barcode clearly on your phone is sufficient).\n"
            "2. Visit any tobacco shop (Tabacchi) displaying the blue <b>T</b> sign, <b>PuntoLIS</b>, or <b>Mooney</b> logos.\n"
            "3. Say to the clerk:\n"
            "   🗣 <i>\"Salve, vorrei pagare questo avviso PagoPA per favore.\"</i>\n"
            "4. The clerk will scan the barcode. Pay the amount plus the processing fee (~€2.00 - €2.50) in cash or by card.\n"
            "5. <b>Critical:</b> Keep the paper receipt (Scontrino) safely as official proof of payment!\n"
        )
    else:
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
    
    if lang == "it":
        text = (
            "🏤 <b>Metodo 3: Pagamento agli Uffici Postali (Poste Italiane)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Disponibile presso tutti gli uffici postali di Perugia (es. sede centrale in Piazza Matteotti o alla stazione Fontivegge):\n\n"
            "<b>Modalità:</b>\n"
            "• <b>Allo sportello:</b> Consegna il bollettino PagoPA stampato all'operatore e paga in contanti o carta.\n"
            "• <b>Agli sportelli Postamat ATM:</b> Inserisci la carta Postepay/BancoPosta, seleziona Pagamenti -> PagoPA e scansiona il codice a barre.\n\n"
            "💶 <b>Commissione:</b> Circa 1,00€ - 2,00€."
        )
    elif lang == "en":
        text = (
            "🏤 <b>Method 3: Payment at Post Offices (Poste Italiane)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Available at all Post Offices in Perugia (e.g., Central Post Office in Piazza Matteotti or near Fontivegge Station):\n\n"
            "<b>Options:</b>\n"
            "• <b>At the Counter:</b> Hand the printed PagoPA notice to the counter clerk and pay with cash or card.\n"
            "• <b>At Postamat ATMs:</b> Insert your card, choose Payments -> PagoPA, and scan the barcode.\n\n"
            "💶 <b>Fee:</b> Approximately €1.00 - €2.00."
        )
    else:
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
    
    if lang == "it":
        text = (
            "🔍 <b>Cosa significano i codici sull'Avviso PagoPA?</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Sull'avviso scaricato da SOL o ADiSU trovi le seguenti informazioni essenziali:\n\n"
            "۱. <b>Codice Avviso (Codice IUV):</b>\n"
            "Codice numerico di 18 cifre (es. <code>301000000123456789</code>) che identifica univocamente la tua tassa.\n\n"
            "۲. <b>Codice Fiscale dell'Ente:</b>\n"
            "Codice fiscale dell'ente creditore (Università degli Studi di Perugia: <code>00448820548</code>).\n\n"
            "۳. <b>Data di Scadenza:</b>\n"
            "Termine entro il quale completare il pagamento.\n\n"
            "۴. <b>QR Code / Codice a Barre:</b>\n"
            "Utilizzato per la scansione rapida con app mobile o dal tabaccaio."
        )
    elif lang == "en":
        text = (
            "🔍 <b>Understanding Your PagoPA Notice</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Every PagoPA invoice generated on SOL or ADiSU contains:\n\n"
            "1. <b>Codice Avviso (IUV Code):</b>\n"
            "An 18-digit unique payment code (e.g., <code>301000000123456789</code>) linked specifically to your university fee.\n\n"
            "2. <b>Codice Fiscale dell'Ente:</b>\n"
            "Tax identification number of the institution (UniPG: <code>00448820548</code>).\n\n"
            "3. <b>Data di Scadenza (Due Date):</b>\n"
            "Deadline for payment before late fees.\n\n"
            "4. <b>QR Code / Barcode:</b>\n"
            "Used for quick scanning with banking apps or tobacco shop terminals."
        )
    else:
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
    
    if lang == "it":
        text = (
            "⚠️ <b>Domande Frequenti e Risoluzione Problemi PagoPA</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "❓ <b>Ho pagato ma sul portale SOL lo stato è ancora rosso. Perché?</b>\n"
            "✅ I circuiti bancari e i server dell'Università non si sincronizzano istantaneamente. La registrazione definitiva richiede solitamente da <b>24 a 72 ore lavorative</b>. Non preoccuparti e <b>non pagare due volte</b>!\n\n"
            "❓ <b>Cos'è la Ricevuta Telematica (RT)?</b>\n"
            "✅ È la prova ufficiale e digitale del pagamento avvenuto. Conservala sempre: se dopo 3 giorni lavorativi il pagamento non viene visualizzato, apri un ticket alla Segreteria Studenti allegando questo documento.\n\n"
            "❓ <b>Ho pagato un avviso errato, posso recuperare l'importo?</b>\n"
            "✅ Sì, è possibile presentare una domanda di rimborso ufficiale (Domanda di Rimborso) tramite la segreteria dell'ateneo."
        )
    elif lang == "en":
        text = (
            "⚠️ <b>Frequently Asked Questions & Troubleshooting</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "❓ <b>I paid, but SOL still shows a red unpaid mark. Why?</b>\n"
            "✅ Banking networks and university databases do not sync in real-time. Final clearance takes <b>24 to 72 business hours</b>. Do not panic and <b>never pay twice</b>!\n\n"
            "❓ <b>What is the Electronic Receipt (Ricevuta Telematica - RT)?</b>\n"
            "✅ It is your official digital proof of payment. Save it; if SOL does not update after 3 business days, send a ticket to the UniPG Tuition Office (Ufficio Tasse) with this receipt attached.\n\n"
            "❓ <b>I paid an incorrect invoice, what should I do?</b>\n"
            "✅ You can submit an official reimbursement request (Domanda di Rimborso) via the university portal."
        )
    else:
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
    
    if lang == "it":
        text = (
            "💳 <b>Guida ai Pagamenti Universitari e Tasse con PagoPA</b>\n\n"
            "Consulta le opzioni sottostanti per la guida dettagliata sui metodi di pagamento a Perugia:"
        )
    elif lang == "en":
        text = (
            "💳 <b>University Fees & Public Payments Guide with PagoPA</b>\n\n"
            "Explore the options below for step-by-step guides on payment methods in Perugia:"
        )
    else:
        text = (
            "💳 <b>راهنمای پرداخت‌های دولتی و شهریه دانشگاه با PagoPA</b>\n\n"
            "برای مشاهده آموزش گام‌به‌گام روش‌های پرداخت آنلاین و حضوری در شهر پروجا، گزینه‌های زیر را ببینید:"
        )
    keyboard = get_pagopa_main_keyboard(lang)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
