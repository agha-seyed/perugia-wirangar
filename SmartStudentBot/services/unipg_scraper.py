# services/unipg_scraper.py
# سامانه خزشگر و رصد هوشمند اطلاعیه‌های دانشگاه پروجا (UniPG) و سازمان ADiSU Umbria
# نسخه ۱.۰ - سازگار با کش هوشمند و فال‌بک آفلاین

import asyncio
import time
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from config import logger

# کش اخبار و ددلاین‌ها به مدت ۲۰ دقیقه (1200 ثانیه)
_CACHE = {
    "unipg": {"data": [], "timestamp": 0},
    "adisu": {"data": [], "timestamp": 0},
    "deadlines": {"data": [], "timestamp": 0}
}
CACHE_TTL = 1200

def translate_title_to_persian(title_it: str) -> str:
    """ترجمه روان تیترهای خبری دانشگاه پروجا و ادیسو به فارسی"""
    t_lower = title_it.lower()
    
    rules = [
        ("bando di concorso per l'assegnazione di borse", "فراخوان رسمی ثبت‌نام بورسیه تحصیلی و کمک‌هزینه دانشجویی"),
        ("bando di concorso", "فراخوان و دفترچه رسمی آزمون"),
        ("borse di studio", "بورسیه‌های تحصیلی و کمک‌هزینه مالی"),
        ("posto letto", "اسکان و ظرفیت اتاق در خوابگاه‌های دانشجویی"),
        ("alloggi", "خوابگاه‌ها و خدمات اسکان دانشجویی"),
        ("graduatoria provvisoria", "نتایج و رتبه‌بندی اولیه متقاضیان"),
        ("graduatoria definitiva", "اسامی و رتبه‌بندی نهایی پذیرفته‌شدگان"),
        ("graduatorie", "لیست رتبه‌بندی و اسامی پذیرفته‌شدگان"),
        ("immatricolazioni", "آغاز فرآیند ثبت‌نام سال جدید تحصیلی"),
        ("iscrizioni", "مهلت ثبت‌نام و پرداخت شهریه"),
        ("inaugurazione anno accademico", "مراسم رسمی افتتاح سال تحصیلی جدید دانشگاه"),
        ("sessione esami", "زمان‌بندی و ثبت‌نام دوره امتحانات"),
        ("servizio ristorazione", "خدمات تغذیه و شارژ کارت سلف سرویس (Mensa)"),
        ("mensa", "سلف سرویس و کارت غذای دانشجویی"),
        ("tasse e contributi", "جدول و شرایط پرداخت شهریه و اقساط"),
        ("studenti internazionali", "اطلاعیه ویژه دانشجویان بین‌المللی و خارجی"),
        ("chiusura uffici", "تعطیلی بخش‌های اداری دانشگاه و ادیسو"),
        ("minimetro", "تخفیف کارت اشتراک مینی‌مترو و اتوبوس‌های شهری"),
        ("orientamento", "جلسه راهنمایی و معارفه دانشجویان جدید"),
        ("elezioni", "انتخابات نمایندگان شورای دانشجویی"),
    ]
    for key, fa_text in rules:
        if key in t_lower:
            return fa_text
            
    return title_it

# ددلاین‌های ثابت و روتین تقویم تحصیلی پروجا (به عنوان فال‌بک و راهنمای دانشجویی)
DEFAULT_ACADEMIC_DEADLINES = [
    {
        "title": "ثبت‌نام و ارسال درخواست آنلاین بورس ADiSU",
        "deadline": "اوایل سپتامبر (معمولاً ۱ الی ۱۰ سپتامبر)",
        "category": "💰 بورسیه",
        "importance": "🔴 بحرانی",
        "desc": "تکمیل فرم آنلاین در پورتال ادیسو و انتخاب درخواست خوابگاه + کمک‌هزینه تحصیلی.",
        "link": "https://www.adisu.umbria.it"
    },
    {
        "title": "تحویل مدرک ISEE Parificato به دانشگاه و ادیسو",
        "deadline": "اواخر اکتبر تا اواسط نوامبر",
        "category": "📄 مدارک مالی",
        "importance": "🔴 بحرانی",
        "desc": "بارگذاری برگه ISEE معادل صادر شده توسط CAF یا بارگذاری در پورتال Sol UniPG.",
        "link": "https://www.unipg.it/didattica/procedure-amministrative/tasse-e-agevolazioni"
    },
    {
        "title": "پرداخت قسط اول شهریه (Tassa d'iscrizione)",
        "deadline": "اواسط نوامبر (معمولاً ۱۵ نوامبر)",
        "category": "💳 شهریه",
        "importance": "🟠 مهم",
        "desc": "پرداخت با شناسه PagoPA از طریق پورتال دانشجویی SOL.",
        "link": "https://www.unipg.it/servizi-online/sol"
    },
    {
        "title": "درخواست خوابگاه دانشجویی (تایید جایگاه)",
        "deadline": "اواخر سپتامبر",
        "category": "🏠 اسکان",
        "importance": "🔴 بحرانی",
        "desc": "پس از انتشار لیست اولیه (Graduatoria provvisoria) متقاضیان باید وضعیت خود را ثبت نهایی کنند.",
        "link": "https://www.adisu.umbria.it/avvisi"
    },
    {
        "title": "ثبت‌نام سشن امتحانات زمستانه (Sessione Invernale)",
        "deadline": "دسامبر تا ژانویه",
        "category": "🎓 امتحانات",
        "importance": "🟡 عادی",
        "desc": "ثبت‌نام در پورتال SOL حداقل ۵ روز قبل از تاریخ هر امتحان الزامی است.",
        "link": "https://www.unipg.it/servizi-online/sol"
    },
    {
        "title": "تمدید پروسه پرمسو دی سوجورنو (Permesso di Soggiorno)",
        "deadline": "۶۰ روز قبل از انقضا",
        "category": "🛂 اقامت",
        "importance": "🔴 بحرانی",
        "desc": "تهیه کیت پستی از اداره پست مرکزی Piazza Matteotti پروجا و ارسال مدارک.",
        "link": "https://www.portaleimmigrazione.it"
    }
]

# اطلاعیه‌های پایه دانشگاه در صورت قطعی اینترنت سرور
FALLBACK_UNIPG_NEWS = [
    {
        "title": "راهنمای ثبت‌نام سال تحصیلی جدید و تقویم آموزشی UniPG",
        "date": "به‌روزرسانی جاری",
        "link": "https://www.unipg.it/didattica",
        "category": "🎓 دانشگاه",
        "summary": "شروع کلاس‌های ترم پاییز، فرآیند ثبت‌نام آنلاین در SOL و دریافت شماره ماتریکولا."
    },
    {
        "title": "جدول زمان‌بندی و شهریه‌های دانشجویان بین‌المللی",
        "date": "سال تحصیلی",
        "link": "https://www.unipg.it/didattica/procedure-amministrative/tasse-e-agevolazioni",
        "category": "💰 مالی",
        "summary": "معافیت‌های شهریه بر پایه ISEE Parificato و جدول اقساط پرداختی از طریق سامانه PagoPA."
    },
    {
        "title": "سرویس‌های حمل و نقل عمومی پروجا (Minimetrò و اتوبوس‌های Busitalia)",
        "date": "تخفیف دانشجویی",
        "link": "https://www.unipg.it/servizi",
        "category": "🚌 خدمات",
        "summary": "اطلاعیه تخفیف اشتراک سالانه مینی‌مترو و کارت عبور دانشجویی اومبریا."
    }
]

# اطلاعیه‌های پایه ادیسو در صورت عدم دسترسی به سایت
FALLBACK_ADISU_NEWS = [
    {
        "title": "دفترچه آزمون بورس و خدمات رفاهی سال تحصیلی (Bando di Concorso)",
        "date": "اطلاعیه رسمی",
        "link": "https://www.adisu.umbria.it/avvisi",
        "category": "💰 بورس",
        "summary": "شرایط بهره‌مندی از کمک هزینه نقدی، اسکان رایگان در خوابگاه‌های پروجا و ترنی و کارت سلف سرویس."
    },
    {
        "title": "دستورالعمل شارژ کارت غذاخوری و سلف‌های دانشجویی (Mensa)",
        "date": "خدمات رفاهی",
        "link": "https://www.adisu.umbria.it/ristorazione",
        "category": "🍽 منسا",
        "summary": "نحوه ثبت اپلیکیشن ادیسو، نرخ ژتون‌ها بر اساس فاز ISEE و آدرس سلف‌های Via Pascoli و Via Innamorati."
    },
    {
        "title": "قوانین تحویل و تخلیه اتاق‌های خوابگاه دانشجویی (Residenze ADiSU)",
        "date": "اسکان",
        "link": "https://www.adisu.umbria.it/residenze",
        "category": "🏠 خوابگاه",
        "summary": "مدارک لازم برای تحویل کلید، تعهدنامه انضباطی و تسویه عوارض سالانه."
    }
]


class UniPGScraper:
    """کلاس خزشگر و مدیریت اطلاعیه‌های دانشگاه پروجا و ادیسو"""

    @classmethod
    async def get_unipg_news(cls, limit: int = 5) -> List[Dict[str, Any]]:
        """دریافت آخرین اخبار و اطلاعیه‌های رسمی UniPG"""
        now = time.time()
        if _CACHE["unipg"]["data"] and (now - _CACHE["unipg"]["timestamp"] < CACHE_TTL):
            return _CACHE["unipg"]["data"][:limit]

        news_items: List[Dict[str, Any]] = []

        # ۱. تلاش برای خواندن از فید RSS رسمی
        rss_urls = [
            "https://www.unipg.it/ateneo/comunicazione/news-e-avvisi?format=feed&type=rss",
            "https://www.unipg.it/news?format=feed&type=rss"
        ]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=headers) as client:
            for url in rss_urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200 and resp.content:
                        root = ET.fromstring(resp.content)
                        items = root.findall(".//item")
                        for it in items:
                            title = it.find("title").text.strip() if it.find("title") is not None else ""
                            link = it.find("link").text.strip() if it.find("link") is not None else "https://www.unipg.it"
                            pub_date = it.find("pubDate").text.strip() if it.find("pubDate") is not None else ""
                            desc = it.find("description").text.strip() if it.find("description") is not None else ""
                            
                            # پاکسازی تگ‌های HTML از description
                            if desc:
                                soup = BeautifulSoup(desc, "html.parser")
                                desc = soup.get_text()[:140] + "..." if len(soup.get_text()) > 140 else soup.get_text()

                            if title:
                                title_fa = translate_title_to_persian(title)
                                news_items.append({
                                    "title": title_fa,
                                    "original_title": title,
                                    "date": " ".join(pub_date.split()[:4]) if pub_date else "اخیراً",
                                    "link": link,
                                    "category": "🏛 دانشگاه",
                                    "summary": desc or "اطلاعیه رسمی پورتال دانشگاه پروجا"
                                })
                        if news_items:
                            break
                except Exception as e:
                    logger.debug(f"RSS fetch failed for {url}: {e}")

            # ۲. اگر RSS موفق نبود، اسکرپ صفحه اول اخبار UniPG
            if not news_items:
                try:
                    page_url = "https://www.unipg.it/ateneo/comunicazione/news-e-avvisi"
                    resp = await client.get(page_url)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        cards = soup.select(".item-page, .article-title, .news-item, h2 a, h3 a")
                        for card in cards[:8]:
                            title = card.get_text(strip=True)
                            href = card.get("href", "")
                            if href and not href.startswith("http"):
                                href = f"https://www.unipg.it{href}"
                            if title and len(title) > 10 and not any(n["title"] == title for n in news_items):
                                title_fa = translate_title_to_persian(title)
                                news_items.append({
                                    "title": title_fa,
                                    "original_title": title,
                                    "date": "تازه",
                                    "link": href or "https://www.unipg.it",
                                    "category": "🏛 دانشگاه",
                                    "summary": "مشاهده متن کامل اطلاعیه در وب‌سایت UniPG."
                                })
                except Exception as e:
                    logger.warning(f"HTML scraping failed for UniPG: {e}")

        # ۳. در صورت بروز هرگونه خطا یا مسدودی، از فال‌بک معتبر استفاده می‌کنیم
        if not news_items:
            news_items = FALLBACK_UNIPG_NEWS

        _CACHE["unipg"] = {"data": news_items, "timestamp": now}
        return news_items[:limit]

    @classmethod
    async def get_adisu_news(cls, limit: int = 5) -> List[Dict[str, Any]]:
        """دریافت آخرین اطلاعیه‌های بورس، اسکان و رفاهی ADiSU Umbria"""
        now = time.time()
        if _CACHE["adisu"]["data"] and (now - _CACHE["adisu"]["timestamp"] < CACHE_TTL):
            return _CACHE["adisu"]["data"][:limit]

        adisu_items: List[Dict[str, Any]] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=headers) as client:
                url = "https://www.adisu.umbria.it/avvisi"
                resp = await client.get(url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # جستجوی مقالات و لینک‌های اطلاعیه
                    links = soup.select("article h2 a, .view-content .views-row a, .field-content a")
                    for a in links[:10]:
                        title = a.get_text(strip=True)
                        href = a.get("href", "")
                        if href and not href.startswith("http"):
                            href = f"https://www.adisu.umbria.it{href}"
                        
                        if title and len(title) > 12 and not any(x.get("original_title") == title for x in adisu_items):
                            cat = "🏠 مسکن / بورس"
                            if "bando" in title.lower() or "borsa" in title.lower():
                                cat = "💰 بورس تحصیلی"
                            elif "posto letto" in title.lower() or "alloggio" in title.lower():
                                cat = "🏠 خوابگاه"
                            elif "mensa" in title.lower() or "ristorazione" in title.lower():
                                cat = "🍽 غذاخوری"

                            title_fa = translate_title_to_persian(title)
                            adisu_items.append({
                                "title": title_fa,
                                "original_title": title,
                                "date": "جدید",
                                "link": href or "https://www.adisu.umbria.it/avvisi",
                                "category": cat,
                                "summary": "اطلاعیه رسمی سازمان خدمات رفاهی و بورسیه دانشجویی اومبریا (ADiSU)."
                            })
        except Exception as e:
            logger.warning(f"ADiSU fetch error: {e}")

        if not adisu_items:
            adisu_items = FALLBACK_ADISU_NEWS

        _CACHE["adisu"] = {"data": adisu_items, "timestamp": now}
        return adisu_items[:limit]

    @classmethod
    def get_deadlines(cls) -> List[Dict[str, Any]]:
        """دریافت تقویم ددلاین‌های بحرانی و مهم دانشجویان پروجا"""
        return DEFAULT_ACADEMIC_DEADLINES
