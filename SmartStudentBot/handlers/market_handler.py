# handlers/market_handler.py
# سیستم کامل بازارچه دانشجویی پروجا (چندزبانه: FA, EN, IT)

from datetime import datetime
from typing import Optional
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import db_manager
from config import logger

try:
    from handlers.cmd_start import get_user_lang, get_text, get_user_lang_code
except ImportError:
    def get_user_lang(user_id: int) -> dict: return {}
    def get_text(lang: dict, key: str, default: str = "") -> str: return default
    def get_user_lang_code(user_id: int) -> str: return "fa"

router = Router()
router.name = "market_handler"

# ماشین وضعیت برای ثبت آگهی
class MarketState(StatesGroup):
    waiting_title = State()
    waiting_category = State()
    waiting_price = State()
    waiting_desc = State()
    waiting_photo = State()
    waiting_contact = State()

CATEGORIES = {
    "fa": {
        "books": "📚 کتاب و جزوه",
        "home": "🍳 لوازم منزل",
        "digital": "💻 لوازم دیجیتال",
        "transport": "🚲 دوچرخه و حمل‌ونقل",
        "other": "📦 سایر لوازم"
    },
    "en": {
        "books": "📚 Books & Notes",
        "home": "🍳 Home & Room",
        "digital": "💻 Digital & Tech",
        "transport": "🚲 Bikes & Transport",
        "other": "📦 Other Items"
    },
    "it": {
        "books": "📚 Libri e Appunti",
        "home": "🍳 Casa e Stanza",
        "digital": "💻 Elettronica & Tech",
        "transport": "🚲 Bici e Trasporti",
        "other": "📦 Altri Articoli"
    }
}

def get_categories(lang_code: str = "fa") -> dict:
    return CATEGORIES.get(lang_code, CATEGORIES["fa"])

def get_market_main_keyboard(items: list = None, current_cat: str = "all", lang_code: str = "fa") -> InlineKeyboardMarkup:
    buttons = []
    
    if lang_code == "it":
        cat_row1 = [
            InlineKeyboardButton(text="📚 Libri", callback_data="mflt_books"),
            InlineKeyboardButton(text="🍳 Casa", callback_data="mflt_home"),
            InlineKeyboardButton(text="💻 Tech", callback_data="mflt_digital")
        ]
        cat_row2 = [
            InlineKeyboardButton(text="🚲 Bici", callback_data="mflt_transport"),
            InlineKeyboardButton(text="📦 Altro", callback_data="mflt_other"),
            InlineKeyboardButton(text="🌐 Tutti", callback_data="mflt_all")
        ]
        btn_add = "➕ Vendi un Oggetto"
        btn_refresh = "🔄 Aggiorna Lista"
        btn_menu = "🏠 Menu Principale"
    elif lang_code == "en":
        cat_row1 = [
            InlineKeyboardButton(text="📚 Books", callback_data="mflt_books"),
            InlineKeyboardButton(text="🍳 Home", callback_data="mflt_home"),
            InlineKeyboardButton(text="💻 Tech", callback_data="mflt_digital")
        ]
        cat_row2 = [
            InlineKeyboardButton(text="🚲 Bikes", callback_data="mflt_transport"),
            InlineKeyboardButton(text="📦 Other", callback_data="mflt_other"),
            InlineKeyboardButton(text="🌐 All Items", callback_data="mflt_all")
        ]
        btn_add = "➕ Post Item for Sale"
        btn_refresh = "🔄 Refresh List"
        btn_menu = "🏠 Main Menu"
    else:
        cat_row1 = [
            InlineKeyboardButton(text="📚 کتب", callback_data="mflt_books"),
            InlineKeyboardButton(text="🍳 منزل", callback_data="mflt_home"),
            InlineKeyboardButton(text="💻 دیجیتال", callback_data="mflt_digital")
        ]
        cat_row2 = [
            InlineKeyboardButton(text="🚲 دوچرخه", callback_data="mflt_transport"),
            InlineKeyboardButton(text="📦 سایر", callback_data="mflt_other"),
            InlineKeyboardButton(text="🌐 همه کالاها", callback_data="mflt_all")
        ]
        btn_add = "➕ ثبت آگهی فروش کالا"
        btn_refresh = "🔄 بروزرسانی لیست"
        btn_menu = "🏠 بازگشت به منوی اصلی"

    buttons.append(cat_row1)
    buttons.append(cat_row2)
    
    # دکمه‌های مشاهده جزئیات کالاهای عکس‌دار
    if items:
        detail_buttons = []
        for i, item in enumerate(items[:6], 1):
            i_id = item.get("item_id") or item.get("_id") or str(i)
            has_pic = " 📸" if item.get("photo_id") else ""
            title_short = (item.get("title", "")[:12] + "..") if len(item.get("title", "")) > 12 else item.get("title", "")
            detail_buttons.append(InlineKeyboardButton(text=f"🔍 {i}. {title_short}{has_pic}", callback_data=f"mview_{i_id}"))
        
        for j in range(0, len(detail_buttons), 2):
            buttons.append(detail_buttons[j:j+2])
            
    buttons.append([
        InlineKeyboardButton(text=btn_add, callback_data="market_add"),
        InlineKeyboardButton(text=btn_refresh, callback_data="market_refresh")
    ])
    buttons.append([
        InlineKeyboardButton(text=btn_menu, callback_data="main_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("market"))
@router.callback_query(F.data.in_(["market", "market_refresh"]))
@router.callback_query(F.data.startswith("mflt_"))
async def show_market(event: types.Message | types.CallbackQuery, state: FSMContext):
    """نمایش لیست اقلام بازارچه با فیلتر دسته‌بندی"""
    await state.clear()
    user_id = event.from_user.id
    lang_code = get_user_lang_code(user_id)
    cats = get_categories(lang_code)
    
    selected_cat = "all"
    if isinstance(event, types.CallbackQuery) and event.data.startswith("mflt_"):
        selected_cat = event.data.replace("mflt_", "")
        
    all_items = await db_manager.get_market_items(limit=30)
    
    if selected_cat != "all":
        items = [it for it in all_items if it.get("category") == selected_cat]
        cat_title = cats.get(selected_cat, selected_cat)
    else:
        items = all_items
        cat_title = "Tutti" if lang_code == "it" else ("All Categories" if lang_code == "en" else "همه دسته‌بندی‌ها")
    
    if lang_code == "it":
        text = "🛒 <b>Mercatino Studenti di Perugia</b>\n"
        text += f"🏷 Categoria: <b>{cat_title}</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        if not items:
            text += "📭 Nessun articolo presente in questa categoria.\n"
            text += "Hai qualcosa da vendere o cedere? Pubblica il primo annuncio!\n\n"
        else:
            text += f"📦 <b>Articoli disponibili ({len(items)}):</b>\n\n"
            for i, item in enumerate(items[:10], 1):
                title = item.get("title", "Senza titolo")
                price = item.get("price", "Trattabile")
                cat_name = cats.get(item.get("category", ""), "📦 Articolo")
                contact = item.get("contact", "---")
                desc = item.get("description", "")
                has_photo = " 📸 (Con foto)" if item.get("photo_id") else ""
                text += f"<b>{i}. {title}</b>{has_photo}\n"
                text += f"   💰 Prezzo: <b>{price}€</b> | {cat_name}\n"
                if desc:
                    text += f"   📝 <i>{desc[:90]}...</i>\n" if len(desc) > 90 else f"   📝 <i>{desc}</i>\n"
                text += f"   👤 Contatto: {contact}\n"
                text += "─────────────────────\n"
            text += "\n💡 Clicca sui tasti numerati per vedere foto e dettagli completi."
    elif lang_code == "en":
        text = "🛒 <b>Perugia Student Marketplace</b>\n"
        text += f"🏷 Category: <b>{cat_title}</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        if not items:
            text += "📭 No items listed in this category.\n"
            text += "Have something to sell or give away? Post the first listing!\n\n"
        else:
            text += f"📦 <b>Available Items ({len(items)}):</b>\n\n"
            for i, item in enumerate(items[:10], 1):
                title = item.get("title", "Untitled")
                price = item.get("price", "Negotiable")
                cat_name = cats.get(item.get("category", ""), "📦 Item")
                contact = item.get("contact", "---")
                desc = item.get("description", "")
                has_photo = " 📸 (With photo)" if item.get("photo_id") else ""
                text += f"<b>{i}. {title}</b>{has_photo}\n"
                text += f"   💰 Price: <b>{price}€</b> | {cat_name}\n"
                if desc:
                    text += f"   📝 <i>{desc[:90]}...</i>\n" if len(desc) > 90 else f"   📝 <i>{desc}</i>\n"
                text += f"   👤 Seller: {contact}\n"
                text += "─────────────────────\n"
            text += "\n💡 Tap on the item buttons below to view full details and photos."
    else:
        text = "🛒 <b>بازارچه دست‌دوم دانشجویان پروجا</b>\n"
        text += f"🏷 دسته‌بندی انتخابی: <b>{cat_title}</b>\n"
        text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        if not items:
            text += "📭 هیچ کالایی در این دسته‌بندی ثبت نشده است.\n"
            text += "اگر وسیله‌ای برای فروش یا واگذاری دارید، اولین آگهی را ثبت کنید!\n\n"
        else:
            text += f"📦 <b>آگهی‌های موجود ({len(items)} مورد):</b>\n\n"
            for i, item in enumerate(items[:10], 1):
                title = item.get("title", "بدون عنوان")
                price = item.get("price", "توافقی")
                cat_name = cats.get(item.get("category", ""), "📦 کالا")
                contact = item.get("contact", "ثبت نشده")
                desc = item.get("description", "")
                has_photo = " 📸 (دارای عکس)" if item.get("photo_id") else ""
                text += f"<b>{i}. {title}</b>{has_photo}\n"
                text += f"   💰 قیمت: <b>{price}€</b> | {cat_name}\n"
                if desc:
                    text += f"   📝 <i>{desc[:90]}...</i>\n" if len(desc) > 90 else f"   📝 <i>{desc}</i>\n"
                text += f"   👤 فروشنده: {contact}\n"
                text += "─────────────────────\n"
            text += "\n💡 برای دیدن عکس و مشخصات کامل، دکمه‌های جستجوی شماره کالا را لمس کنید."

    keyboard = get_market_main_keyboard(items, selected_cat, lang_code)

    if isinstance(event, types.CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception:
            await event.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("mview_"))
async def view_market_item(callback: types.CallbackQuery):
    """مشاهده تکی کالا همراه با تصویر و اطلاعات تماس"""
    item_id = callback.data.replace("mview_", "")
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    cats = get_categories(lang_code)
    
    items = await db_manager.get_market_items(limit=50)
    found_item = None
    for it in items:
        cur_id = it.get("item_id") or it.get("_id") or ""
        if str(cur_id) == str(item_id):
            found_item = it
            break
            
    if not found_item:
        msg = "⚠️ Articolo non trovato." if lang_code == "it" else ("⚠️ Item not found." if lang_code == "en" else "⚠️ اطلاعات کالا یافت نشد.")
        await callback.answer(msg, show_alert=True)
        return
        
    title = found_item.get("title", "Item")
    price = found_item.get("price", "---")
    cat_name = cats.get(found_item.get("category", ""), "📦")
    desc = found_item.get("description", "---")
    contact = found_item.get("contact", "---")
    date_str = found_item.get("created_at", "")
    photo_id = found_item.get("photo_id")
    
    if lang_code == "it":
        card_text = (
            f"🏷 <b>{title}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 <b>Prezzo:</b> <code>{price} €</code>\n"
            f"📂 <b>Categoria:</b> {cat_name}\n"
            f"📝 <b>Descrizione:</b>\n{desc}\n\n"
            f"📞 <b>Contatto Venditore:</b>\n{contact}\n"
            f"📅 Data: {date_str}"
        )
        btn_back = "🔙 Torna al Mercatino"
    elif lang_code == "en":
        card_text = (
            f"🏷 <b>{title}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 <b>Price:</b> <code>{price} €</code>\n"
            f"📂 <b>Category:</b> {cat_name}\n"
            f"📝 <b>Description:</b>\n{desc}\n\n"
            f"📞 <b>Seller Contact:</b>\n{contact}\n"
            f"📅 Date: {date_str}"
        )
        btn_back = "🔙 Back to Market"
    else:
        card_text = (
            f"🏷 <b>{title}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 <b>قیمت:</b> <code>{price} €</code>\n"
            f"📂 <b>دسته‌بندی:</b> {cat_name}\n"
            f"📝 <b>توضیحات:</b>\n{desc}\n\n"
            f"📞 <b>اطلاعات تماس و آیدی فروشنده:</b>\n{contact}\n"
            f"📅 تاریخ ثبت: {date_str}"
        )
        btn_back = "🔙 بازگشت به بازارچه"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_back, callback_data="market")]
    ])
    
    if photo_id:
        try:
            await callback.message.answer_photo(photo_id, caption=card_text, reply_markup=kb, parse_mode="HTML")
            await callback.answer()
            return
        except Exception as e:
            logger.warning(f"Could not send item photo {photo_id}: {e}")
            
    await callback.message.answer(card_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "market_add")
async def start_add_market_item(callback: types.CallbackQuery, state: FSMContext):
    """شروع ثبت آگهی فروش کالا"""
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    await state.set_state(MarketState.waiting_title)
    
    if lang_code == "it":
        text = "➕ <b>Pubblica un nuovo articolo nel mercatino</b>\n\n"
        text += "Inserisci il <b>titolo dell'oggetto</b> (es: Libro di Italiano A1, Bicicletta, ecc.):"
        btn_cancel = "❌ Annulla"
    elif lang_code == "en":
        text = "➕ <b>Post a New Item in Perugia Marketplace</b>\n\n"
        text += "Please send the <b>item title</b> (e.g. Italian A1 book, Mountain bike, etc.):"
        btn_cancel = "❌ Cancel"
    else:
        text = "➕ <b>ثبت آگهی جدید در بازارچه پروجا</b>\n\n"
        text += "لطفاً <b>عنوان کالا</b> را ارسال کنید (مثال: کتاب ایتالیایی A1 یا دوچرخه کوهستان):"
        btn_cancel = "❌ انصراف"
        
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_cancel, callback_data="market")]
    ])
    await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.message(MarketState.waiting_title)
async def process_market_title(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang_code = get_user_lang_code(user_id)
    cats = get_categories(lang_code)
    
    title = message.text.strip() if message.text else ""
    if len(title) < 3:
        err = "⚠️ Inserisci un titolo più dettagliato (almeno 3 caratteri):" if lang_code == "it" else (
            "⚠️ Please enter a more descriptive title (at least 3 characters):" if lang_code == "en" else
            "⚠️ لطفاً عنوان دقیق‌تری (حداقل ۳ حرف) وارد کنید:"
        )
        await message.answer(err)
        return
        
    await state.update_data(title=title)
    await state.set_state(MarketState.waiting_category)
    
    buttons = []
    for cat_id, cat_title in cats.items():
        buttons.append([InlineKeyboardButton(text=cat_title, callback_data=f"mcat_{cat_id}")])
    btn_cancel = "❌ Annulla" if lang_code == "it" else ("❌ Cancel" if lang_code == "en" else "❌ انصراف")
    buttons.append([InlineKeyboardButton(text=btn_cancel, callback_data="market")])
    
    if lang_code == "it":
        prompt = f"✅ Titolo: <b>{title}</b>\n\nSeleziona la <b>categoria</b>:"
    elif lang_code == "en":
        prompt = f"✅ Title: <b>{title}</b>\n\nPlease select the <b>category</b>:"
    else:
        prompt = f"✅ عنوان: <b>{title}</b>\n\nلطفاً <b>دسته‌بندی</b> کالا را انتخاب کنید:"
        
    await message.answer(
        prompt,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("mcat_"), MarketState.waiting_category)
async def process_market_category(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    cats = get_categories(lang_code)
    
    cat_id = callback.data.split("_")[1]
    await state.update_data(category=cat_id)
    await state.set_state(MarketState.waiting_price)
    
    if lang_code == "it":
        text = f"✅ Categoria: <b>{cats.get(cat_id, '')}</b>\n\n"
        text += "Inserisci il <b>prezzo in Euro (€)</b> (solo numeri, es: 25):"
        btn_cancel = "❌ Annulla"
    elif lang_code == "en":
        text = f"✅ Category: <b>{cats.get(cat_id, '')}</b>\n\n"
        text += "Please send the <b>price in Euro (€)</b> (numbers only, e.g. 25):"
        btn_cancel = "❌ Cancel"
    else:
        text = f"✅ دسته‌بندی: <b>{cats.get(cat_id, '')}</b>\n\n"
        text += "لطفاً <b>قیمت کالا به یورو (€)</b> را وارد کنید (فقط عدد، مثلاً: 25):"
        btn_cancel = "❌ انصراف"
        
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_cancel, callback_data="market")]
    ])
    await callback.message.edit_text(text, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.message(MarketState.waiting_price)
async def process_market_price(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang_code = get_user_lang_code(user_id)
    price_text = message.text.strip() if message.text else ""
    try:
        price = float(price_text.replace("€", "").replace("euro", "").replace("یورو", "").strip())
    except ValueError:
        err = "⚠️ Inserisci un numero valido per il prezzo (es: 30):" if lang_code == "it" else (
            "⚠️ Please enter a valid number for price (e.g. 30):" if lang_code == "en" else
            "⚠️ لطفاً فقط یک عدد معتبر برای قیمت به یورو وارد کنید (مثال: 30):"
        )
        await message.answer(err)
        return
        
    await state.update_data(price=price)
    await state.set_state(MarketState.waiting_desc)
    
    btn_cancel = "❌ Annulla" if lang_code == "it" else ("❌ Cancel" if lang_code == "en" else "❌ انصراف")
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_cancel, callback_data="market")]
    ])
    
    if lang_code == "it":
        prompt = f"✅ Prezzo: <b>{price}€</b>\n\nOra scrivi una <b>breve descrizione</b> delle condizioni dell'oggetto:"
    elif lang_code == "en":
        prompt = f"✅ Price: <b>{price}€</b>\n\nNow write a <b>short description</b> of condition, features or details:"
    else:
        prompt = f"✅ قیمت: <b>{price}€</b>\n\nاکنون یک <b>توضیح کوتاه</b> درباره وضعیت، تمیزی یا مشخصات کالا بنویسید:"
        
    await message.answer(prompt, reply_markup=cancel_kb, parse_mode="HTML")


@router.message(MarketState.waiting_desc)
async def process_market_desc(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang_code = get_user_lang_code(user_id)
    desc = message.text.strip() if message.text else ""
    await state.update_data(description=desc)
    await state.set_state(MarketState.waiting_photo)
    
    if lang_code == "it":
        btn_skip = "⏭ Salta Foto"
        btn_cancel = "❌ Annulla"
        text = (
            "📸 <b>Foto dell'oggetto (molto consigliata)</b>\n\n"
            "Invia una foto chiara del tuo articolo.\n\n"
            "💡 <i>Se non hai una foto ora, tocca «Salta Foto».</i>"
        )
    elif lang_code == "en":
        btn_skip = "⏭ Skip Photo"
        btn_cancel = "❌ Cancel"
        text = (
            "📸 <b>Item Photo (Highly Recommended)</b>\n\n"
            "Please upload a clear photo of your item.\n\n"
            "💡 <i>If you don't have a photo right now, tap «Skip Photo».</i>"
        )
    else:
        btn_skip = "⏭ بدون عکس ادامه بده"
        btn_cancel = "❌ انصراف"
        text = (
            "📸 <b>ارسال عکس کالا (بسیار مؤثر در فروش)</b>\n\n"
            "لطفاً یک تصویر واضح از کالای خود ارسال کنید.\n\n"
            "💡 <i>اگر در حال حاضر عکسی ندارید، می‌توانید دکمه «بدون عکس ادامه بده» را لمس کنید.</i>"
        )
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_skip, callback_data="market_skip_photo")],
        [InlineKeyboardButton(text=btn_cancel, callback_data="market")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(MarketState.waiting_photo, F.photo)
async def process_market_photo(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang_code = get_user_lang_code(user_id)
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await state.set_state(MarketState.waiting_contact)
    
    default_contact = f"@{message.from_user.username}" if message.from_user.username else ""
    btn_cancel = "❌ Annulla" if lang_code == "it" else ("❌ Cancel" if lang_code == "en" else "❌ انصراف")
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_cancel, callback_data="market")]
    ])
    
    if lang_code == "it":
        prompt = "✅ Foto ricevuta con successo!\n\n📞 Invia il tuo <b>contatto Telegram o telefono</b> da mostrare nell'annuncio:\n"
        if default_contact: prompt += f"(Puoi inviare il tuo username <code>{default_contact}</code>)"
    elif lang_code == "en":
        prompt = "✅ Photo uploaded successfully!\n\n📞 Please send your <b>Telegram username or phone number</b> for buyers to contact you:\n"
        if default_contact: prompt += f"(You can send your username <code>{default_contact}</code>)"
    else:
        prompt = "✅ تصویر کالا با موفقیت ثبت شد!\n\n📞 لطفاً <b>آیدی تلگرام یا شماره تماس</b> خود را جهت درج در آگهی ارسال کنید:\n"
        if default_contact: prompt += f"(می‌توانید همان آیدی تلگرام خودتان یعنی <code>{default_contact}</code> را بفرستید)"
        
    await message.answer(prompt, reply_markup=cancel_kb, parse_mode="HTML")


@router.callback_query(F.data == "market_skip_photo", MarketState.waiting_photo)
async def skip_market_photo(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang_code = get_user_lang_code(user_id)
    await state.update_data(photo_id="")
    await state.set_state(MarketState.waiting_contact)
    
    default_contact = f"@{callback.from_user.username}" if callback.from_user.username else ""
    btn_cancel = "❌ Annulla" if lang_code == "it" else ("❌ Cancel" if lang_code == "en" else "❌ انصراف")
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_cancel, callback_data="market")]
    ])
    
    if lang_code == "it":
        prompt = "📞 Invia il tuo <b>username Telegram o numero</b> per il contatto:\n"
        if default_contact: prompt += f"(Puoi inviare <code>{default_contact}</code>)"
    elif lang_code == "en":
        prompt = "📞 Please send your <b>Telegram username or phone</b> for contact:\n"
        if default_contact: prompt += f"(You can send <code>{default_contact}</code>)"
    else:
        prompt = "📞 لطفاً <b>آیدی یا شماره تماس</b> خود را جهت درج در آگهی ارسال کنید:\n"
        if default_contact: prompt += f"(می‌توانید همان آیدی تلگرام خودتان یعنی <code>{default_contact}</code> را ارسال کنید)"
        
    await callback.message.edit_text(prompt, reply_markup=cancel_kb, parse_mode="HTML")
    await callback.answer()


@router.message(MarketState.waiting_photo)
async def process_market_photo_invalid(message: types.Message):
    user_id = message.from_user.id
    lang_code = get_user_lang_code(user_id)
    if lang_code == "it":
        msg = "📸 Invia una foto oppure tocca «Salta Foto»:"
        btn_skip = "⏭ Salta Foto"
        btn_cancel = "❌ Annulla"
    elif lang_code == "en":
        msg = "📸 Please send a photo or tap «Skip Photo»:"
        btn_skip = "⏭ Skip Photo"
        btn_cancel = "❌ Cancel"
    else:
        msg = "📸 لطفاً یک عکس ارسال کنید یا دکمه «بدون عکس ادامه بده» را لمس نمایید:"
        btn_skip = "⏭ بدون عکس ادامه بده"
        btn_cancel = "❌ انصراف"
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_skip, callback_data="market_skip_photo")],
        [InlineKeyboardButton(text=btn_cancel, callback_data="market")]
    ])
    await message.answer(msg, reply_markup=kb)


@router.message(MarketState.waiting_contact)
async def process_market_contact(message: types.Message, state: FSMContext):
    contact = message.text.strip() if message.text else ""
    data = await state.get_data()
    user_id = message.from_user.id
    lang_code = get_user_lang_code(user_id)
    cats = get_categories(lang_code)
    
    item_id = f"m_{int(datetime.now().timestamp())}_{user_id % 1000}"
    item_data = {
        "item_id": item_id,
        "user_id": user_id,
        "title": data.get("title"),
        "category": data.get("category"),
        "price": data.get("price"),
        "description": data.get("description"),
        "photo_id": data.get("photo_id", ""),
        "contact": contact,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    await db_manager.save_market_item(item_data)
    await state.clear()
    await db_manager.add_user_xp(user_id, 30)
    
    if lang_code == "it":
        success_text = "🎉 <b>Il tuo annuncio è stato pubblicato con successo!</b>\n\n"
        success_text += f"📌 <b>{item_data['title']}</b> - <b>{item_data['price']}€</b>\n"
        success_text += f"📂 Categoria: {cats.get(item_data['category'], '')}\n"
        success_text += f"📞 Contatto: {contact}\n\n"
        success_text += "🎁 <i>Hai guadagnato +30 XP!</i>"
        btn_view = "🛍 Visualizza nel Mercatino"
        btn_home = "🏠 Menu Principale"
    elif lang_code == "en":
        success_text = "🎉 <b>Your listing has been published successfully!</b>\n\n"
        success_text += f"📌 <b>{item_data['title']}</b> - <b>{item_data['price']}€</b>\n"
        success_text += f"📂 Category: {cats.get(item_data['category'], '')}\n"
        success_text += f"📞 Contact: {contact}\n\n"
        success_text += "🎁 <i>You earned +30 XP!</i>"
        btn_view = "🛍 View in Marketplace"
        btn_home = "🏠 Main Menu"
    else:
        success_text = "🎉 <b>آگهی شما با موفقیت در بازارچه پروجا ثبت شد!</b>\n\n"
        success_text += f"📌 <b>{item_data['title']}</b> - <b>{item_data['price']}€</b>\n"
        success_text += f"📂 دسته‌بندی: {cats.get(item_data['category'], '')}\n"
        success_text += f"📞 اطلاعات ارتباطی: {contact}\n\n"
        success_text += "🎁 <i>+30 امتیاز دانشجویی (XP) دریافت کردید!</i>"
        btn_view = "🛍 مشاهده در بازارچه"
        btn_home = "🏠 منوی اصلی"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_view, callback_data="market")],
        [InlineKeyboardButton(text=btn_home, callback_data="main_menu")]
    ])
    await message.answer(success_text, reply_markup=kb, parse_mode="HTML")
