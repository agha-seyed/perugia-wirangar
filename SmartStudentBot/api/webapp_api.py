from fastapi import APIRouter, Depends, Query, Body, HTTPException
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
import re

from database import db_manager
from config import logger

router = APIRouter(prefix="/api/v1/webapp", tags=["webapp"])

from services.currency_service import currency_service

@router.get("/currency")
async def get_live_currency():
    """
    دریافت نرخ لحظه‌ای و زنده یورو و سایر ارزها به تومان برای مینی‌اپ
    بدون نیاز به احراز هویت برای بارگذاری سریع در فرانت‌اند
    """
    try:
        data = await currency_service.get_all_rates()
        eur = data.get("eur_toman", 304000)
        return {
            "eur_toman": eur,
            "usd_toman": data.get("usd_toman", 268000),
            "currencies": data.get("currencies", []),
            "gold": data.get("gold", []),
            "crypto": data.get("crypto", []),
            "source": data.get("source", "brsapi"),
            "source_name": data.get("source_name", "بازار آزاد"),
            "formatted": f"{eur:,} تومان",
            "updated_at": data.get("updated_at", "")
        }
    except Exception as e:
        logger.error(f"Error in webapp currency endpoint: {e}")
        return {
            "eur_toman": 304000,
            "usd_toman": 268000,
            "source": "fallback",
            "formatted": "304,000 تومان",
            "cached": True
        }


@router.get("/places")
async def get_places():
    """
    دریافت لیست جامع اماکن مهم پروجا با مختصات GPS و دسته‌بندی برای نقشه مینی‌اپ
    """
    places = [
        {
            "id": "questura",
            "name": "Questura di Perugia (اداره پلیس مهاجرت)",
            "name_it": "Questura - Ufficio Immigrazione",
            "category": "gov",
            "category_fa": "ادارات دولتی",
            "lat": 43.0800,
            "lng": 12.3420,
            "address": "Via del Tabacchificio, 21, Ellera",
            "hours": "دوشنبه تا جمعه ۸:۳۰-۱۲:۳۰",
            "desc": "محل انجام انگشت‌نگاری و تحویل کارت پرمسو دی سوجورنو (اقامت دانشجویی)."
        },
        {
            "id": "agenzia",
            "name": "Agenzia delle Entrate (اداره مالیات)",
            "name_it": "Agenzia delle Entrate",
            "category": "gov",
            "category_fa": "ادارات دولتی",
            "lat": 43.10895,
            "lng": 12.38885,
            "address": "Via Canali, 12, Perugia",
            "hours": "دوشنبه تا جمعه ۸:۳۰-۱۳:۰۰ (با نوبت آنلاین)",
            "desc": "صدور کد مالیاتی (کدیچه فیسکاله) و ثبت رسمی قرارداد اجاره خانه."
        },
        {
            "id": "poste",
            "name": "Poste Italiane - Centrale (پست مرکزی)",
            "name_it": "Poste Italiane Centro",
            "category": "gov",
            "category_fa": "ادارات دولتی",
            "lat": 43.11072,
            "lng": 12.38918,
            "address": "Piazza Giacomo Matteotti, 14",
            "hours": "دوشنبه تا جمعه ۸:۲۰-۱۹:۰۵، شنبه تا ۱۲:۳۵",
            "desc": "دریافت و ارسال کیت زرد پرمسو، پرداخت فیش‌ها و افتتاح کارت بانکی Postepay."
        },
        {
            "id": "adisu",
            "name": "ADiSU Umbria (سازمان بورس و اسکان)",
            "name_it": "ADiSU Umbria - Sede Centrale",
            "category": "gov",
            "category_fa": "ادارات دولتی",
            "lat": 43.1190,
            "lng": 12.3880,
            "address": "Via Benedetta, 14, Perugia",
            "hours": "دوشنبه تا پنجشنبه ۹:۰۰-۱۳:۰۰",
            "desc": "مرکز اداری بورس استانی، اختصاص خوابگاه دانشجویی و صدور کارت سلف غذا."
        },
        {
            "id": "uni_main",
            "name": "دانشگاه پروجا - ساختمان مرکزی",
            "name_it": "Università degli Studi di Perugia (Rettorato)",
            "category": "uni",
            "category_fa": "دانشگاه‌ها",
            "lat": 43.1160,
            "lng": 12.3860,
            "address": "Piazza dell'Università, 1",
            "hours": "دوشنبه تا جمعه ۸:۳۰-۱۸:۰۰",
            "desc": "ساختمان ریاست دانشگاه، دبیرخانه مرکزی و اداره دانشجویان بین‌المللی."
        },
        {
            "id": "engineering",
            "name": "دانشکده مهندسی UniPG",
            "name_it": "Polo d'Ingegneria",
            "category": "uni",
            "category_fa": "دانشگاه‌ها",
            "lat": 43.0990,
            "lng": 12.3750,
            "address": "Via Goffredo Duranti, 93 (Elce)",
            "hours": "دوشنبه تا جمعه ۸:۰۰-۱۹:۳۰",
            "desc": "دانشکده مهندسی، علوم کامپیوتر، رباتیک و آزمایشگاه‌های پیشرفته."
        },
        {
            "id": "medicine",
            "name": "دانشکده پزشکی و جراحی",
            "name_it": "Polo Didattico di Medicina",
            "category": "uni",
            "category_fa": "دانشگاه‌ها",
            "lat": 43.1040,
            "lng": 12.3900,
            "address": "Piazzale Lucio Severi, 1 (Ospedale Silvestrini)",
            "hours": "دوشنبه تا جمعه ۸:۰۰-۱۸:۰۰",
            "desc": "پردیس علوم پزشکی، داروسازی و بیمارستان آموزشی پروجا."
        },
        {
            "id": "mensa_pascoli",
            "name": "سلف مرکزی دانشگاه (Mensa Pascoli)",
            "name_it": "Mensa Universitaria Via Pascoli",
            "category": "canteen",
            "category_fa": "سلف و غذاخوری",
            "lat": 43.1180,
            "lng": 12.3840,
            "address": "Via Giovanni Pascoli, 23",
            "hours": "ناهار: ۱۲:۰۰-۱۴:۳۰ | شام: ۱۹:۰۰-۲۱:۱۵",
            "desc": "سلف اصلی دانشجویی با غذای کامل گرم، پیتزا و بوفه سالاد با کارت ادیسو."
        },
        {
            "id": "mensa_innamorati",
            "name": "سلف دانشکده مهندسی (Mensa Elce)",
            "name_it": "Mensa Innamorati",
            "category": "canteen",
            "category_fa": "سلف و غذاخوری",
            "lat": 43.1195,
            "lng": 12.3785,
            "address": "Via degli Innamorati, 3",
            "hours": "ناهار: ۱۲:۱۵-۱۴:۱۵",
            "desc": "سلف دانشجویی منطقه الچه، نزدیک دانشکده مهندسی و علوم پایه."
        },
        {
            "id": "fontivegge",
            "name": "ایستگاه قطار مرکزی (Stazione Fontivegge)",
            "name_it": "Stazione Ferroviaria Perugia Fontivegge",
            "category": "transit",
            "category_fa": "حمل‌ونقل",
            "lat": 43.1048,
            "lng": 12.3752,
            "address": "Piazza Vittorio Veneto",
            "hours": "۲۴ ساعته",
            "desc": "ایستگاه قطارهای Trenitalia به رم، فلورانس و میلان + ترمینال اتوبوس‌های بین‌شهری."
        },
        {
            "id": "minimetro_pincetto",
            "name": "ایستگاه مینی‌مترو Pincetto (مرکز تاریخی)",
            "name_it": "Minimetrò Pincetto",
            "category": "transit",
            "category_fa": "حمل‌ونقل",
            "lat": 43.1085,
            "lng": 12.3912,
            "address": "Via Pincetto, Centro Storico",
            "hours": "۷:۰۰ صبح تا ۲۱:۲۰ شب",
            "desc": "ایستگاه مینی‌مترو مرکز تاریخی، نزدیک میدان اصلی ۴ نوامبر و خیابان وانتوچی."
        },
        {
            "id": "minimetro_cupa",
            "name": "ایستگاه مینی‌مترو Cupa",
            "name_it": "Minimetrò Cupa",
            "category": "transit",
            "category_fa": "حمل‌ونقل",
            "lat": 43.1130,
            "lng": 12.3820,
            "address": "Via Pellini / Cupa",
            "hours": "۷:۰۰ صبح تا ۲۱:۲۰ شب",
            "desc": "ایستگاه مینی‌مترو دارای پله‌برقی به سمت دانشکده حقوق و سلف پاسکولی."
        }
    ]
    return {"places": places, "count": len(places)}


@router.get("/market")
async def get_market_items(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """دریافت آیتم‌های بازارچه"""
    items = await db_manager.get_market_items(limit=limit, skip=skip)
    return {"items": items}


@router.post("/market")
async def create_market_item(payload: Dict[str, Any] = Body(...)):
    """ثبت آگهی جدید در بازارچه از طریق مینی‌اپ"""
    title = payload.get("title", "").strip()
    price = payload.get("price", 0)
    contact = payload.get("contact", "").strip()
    
    if not title or not contact:
        raise HTTPException(status_code=400, detail="Title and contact are required")

    item_data = {
        "title": title,
        "price": float(price),
        "category": payload.get("category", "general"),
        "area": payload.get("area", "Perugia"),
        "contact": contact if contact.startswith("@") else f"@{contact}",
        "description": payload.get("description", ""),
        "created_at": datetime.now().isoformat(),
        "is_active": True
    }
    await db_manager.save_market_item(item_data)
    return {"ok": True, "message": "آگهی شما با موفقیت ثبت شد", "item": item_data}


@router.get("/roommates")
async def get_roommates(
    area: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100)
):
    """دریافت آگهی‌های هم‌اتاقی"""
    ads = await db_manager.get_active_roommate_ads(area=area, limit=limit)
    return {"ads": ads}


@router.post("/roommates")
async def create_roommate_ad(payload: Dict[str, Any] = Body(...)):
    """ثبت آگهی هم‌اتاقی و مسکن از طریق مینی‌اپ"""
    title = payload.get("title", "").strip()
    price = payload.get("price", 0)
    contact = payload.get("contact", "").strip()
    
    if not title or not contact:
        raise HTTPException(status_code=400, detail="Title and contact are required")

    ad_data = {
        "title": title,
        "price": float(price),
        "area": payload.get("area", "Elce"),
        "type": payload.get("type", "اتاق تک‌نفره"),
        "amenities": payload.get("amenities", ["wifi", "washing"]),
        "contact": contact if contact.startswith("@") else f"@{contact}",
        "description": payload.get("description", ""),
        "created_at": datetime.now().isoformat(),
        "is_active": True
    }
    await db_manager.save_roommate_ad(ad_data)
    return {"ok": True, "message": "آگهی مسکن با موفقیت ثبت شد", "ad": ad_data}


@router.post("/consult")
async def submit_consultation(payload: Dict[str, Any] = Body(...)):
    """ثبت درخواست مشاوره تحصیلی و اداری"""
    name = payload.get("name", "کاربر مینی‌اپ")
    topic = payload.get("topic", "مشاوره عمومی")
    contact = payload.get("contact", "")
    notes = payload.get("notes", "")

    consult_id = f"c_{int(datetime.now().timestamp())}"
    data = {
        "name": name,
        "topic": topic,
        "contact": contact,
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "status": "pending"
    }
    await db_manager.save_consult(consult_id, data)

    # اطلاع‌رسانی سریع به ادمین‌های بات در تلگرام
    try:
        from config import settings
        from main import bot
        admin_ids = settings.ADMIN_CHAT_IDS
        admin_msg = (
            f"🎓 <b>درخواست مشاوره تحصیلی و اداری جدید از مینی‌اپ!</b>\n\n"
            f"👤 <b>نام و مشخصات:</b> {name}\n"
            f"📌 <b>موضوع:</b> {topic}\n"
            f"📱 <b>ارتباط:</b> <code>{contact}</code>\n"
            f"📝 <b>توضیحات:</b> {notes or 'بدون توضیحات'}\n"
            f"🆔 <b>کد رهگیری:</b> <code>{consult_id}</code>\n"
            f"⏰ <b>زمان ثبت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        for aid in admin_ids:
            try:
                await bot.send_message(chat_id=aid, text=admin_msg, parse_mode="HTML")
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"Admin notification notice: {e}")

    return {"ok": True, "consult_id": consult_id, "message": "درخواست مشاوره شما با موفقیت ثبت شد و به مشاورین ارجاع گردید."}


@router.post("/feedback")
async def submit_feedback(payload: Dict[str, Any] = Body(...)):
    """ارسال تیکت یا بازخورد به پشتیبانی"""
    text = payload.get("text", "").strip()
    contact = payload.get("contact", "")
    
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    ticket_id = f"fb_{int(datetime.now().timestamp())}"
    data = {
        "text": text,
        "contact": contact,
        "created_at": datetime.now().isoformat(),
        "status": "open"
    }
    await db_manager.save_ticket(ticket_id, data)
    return {"ok": True, "ticket_id": ticket_id, "message": "بازخورد شما دریافت شد"}
