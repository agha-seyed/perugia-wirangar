# services/currency_service.py
# سرویس جامع و زنده استعلام نرخ ارز، طلا و کریپتو
# ادغام وب‌سرویس BrsApi + فال‌بک هوشمند کلاستر TGJU + کشینگ پرسرعت

import asyncio
import time
import re
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import pytz
import httpx

from config import settings, logger

class CurrencyService:
    """
    مدیریت متمرکز استعلام و تبدیل نرخ ارزهای خارجی و طلا
    پشتیبانی از BrsApi با کلید اختصاصی و کلاستر TGJU
    """
    def __init__(self):
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: float = 0
        self._cache_ttl: int = 180  # کش ۳ دقیقه‌ای برای تازه بودن و عدم اتمام سهمیه
        self._lock = asyncio.Lock()

    async def get_all_rates(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        دریافت لیست کامل نرخ‌های ارز، طلا و کریپتو
        """
        now = time.time()
        if not force_refresh and self._cache and (now - self._cache_timestamp < self._cache_ttl):
            return self._cache

        async with self._lock:
            # بررسی مجدد بعد از قفل
            if not force_refresh and self._cache and (now - self._cache_timestamp < self._cache_ttl):
                return self._cache

            data = await self._fetch_from_brsapi()
            if not data:
                data = await self._fetch_from_tgju()
            if not data:
                data = self._get_fallback_data()

            self._cache = data
            self._cache_timestamp = now
            return data

    async def get_eur_rate(self) -> int:
        """
        دریافت نرخ لحظه‌ای یورو به تومان (جهت محاسبه ISEE و هزینه‌ها)
        """
        rates = await self.get_all_rates()
        eur = rates.get("eur_toman") or 304000
        return int(eur)

    async def get_usd_rate(self) -> int:
        """
        دریافت نرخ لحظه‌ای دلار به تومان
        """
        rates = await self.get_all_rates()
        usd = rates.get("usd_toman") or 268000
        return int(usd)

    async def _fetch_from_brsapi(self) -> Optional[Dict[str, Any]]:
        """
        دریافت داده از وب‌سرویس BrsApi با کلید اختصاصی
        """
        api_key = settings.BRSAPI_KEY
        if not api_key:
            logger.debug("BrsApi key not configured, falling back to TGJU")
            return None

        url = f"{settings.BRSAPI_URL}?key={api_key}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Accept": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=4.5, headers=headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    json_data = resp.json()
                    currencies_raw = json_data.get("currency", [])
                    golds_raw = json_data.get("gold", [])
                    cryptos_raw = json_data.get("cryptocurrency", [])

                    eur_price = 0
                    usd_price = 0
                    currencies_list = []

                    def safe_int(val, default=0):
                        try:
                            if val is None: return default
                            return int(round(float(str(val).replace(",", ""))))
                        except:
                            return default

                    def safe_float(val, default=0.0):
                        try:
                            if val is None: return default
                            return float(str(val).replace(",", ""))
                        except:
                            return default

                    for c in currencies_raw:
                        sym = c.get("symbol", "").upper()
                        name = c.get("name", "")
                        price = safe_int(c.get("price"))
                        change = safe_float(c.get("change_percent"))

                        if sym == "EUR" or name in ["یورو", "یورو اروپا"]:
                            eur_price = price
                        elif sym == "USD" or name in ["دلار", "دلار آمریکا"]:
                            usd_price = price

                        if sym in ["EUR", "USD", "GBP", "AED", "CAD", "TRY", "CHF", "AUD"]:
                            currencies_list.append({
                                "symbol": sym,
                                "name": name,
                                "price": price,
                                "change": change
                            })

                    gold_list = []
                    for g in golds_raw[:6]:
                        gold_list.append({
                            "name": g.get("name", ""),
                            "price": safe_int(g.get("price")),
                            "change": safe_float(g.get("change_percent"))
                        })

                    crypto_list = []
                    for cr in cryptos_raw[:4]:
                        crypto_list.append({
                            "symbol": cr.get("symbol", "").upper(),
                            "name": cr.get("name", ""),
                            "price": safe_int(cr.get("price")),
                            "change": safe_float(cr.get("change_percent"))
                        })

                    if eur_price > 50000:
                        tehran_tz = pytz.timezone("Asia/Tehran")
                        now_str = datetime.now(tehran_tz).strftime("%H:%M:%S - %Y/%m/%d")

                        logger.info(f"✅ Live rates successfully fetched from BrsApi: EUR={eur_price:,} Toman")
                        return {
                            "eur_toman": eur_price,
                            "usd_toman": usd_price or 268000,
                            "currencies": currencies_list,
                            "gold": gold_list,
                            "crypto": crypto_list,
                            "source": "brsapi",
                            "source_name": "سامانه جامع بازار آزاد (BrsApi)",
                            "updated_at": now_str,
                            "timestamp": time.time()
                        }
        except Exception as e:
            logger.warning(f"⚠️ BrsApi fetch error: {e}")

        return None

    async def _fetch_from_tgju(self) -> Optional[Dict[str, Any]]:
        """
        فال‌بک به کلاستر TGJU در صورت عدم دسترسی به BrsApi
        """
        urls = [
            "https://call.tgju.org/ajax.json",
            "https://call4.tgju.org/ajax.json",
            "https://call3.tgju.org/ajax.json",
            "https://call2.tgju.org/ajax.json",
        ]
        headers = {"User-Agent": "Mozilla/5.0"}

        for url in urls:
            try:
                async with httpx.AsyncClient(timeout=3.0, headers=headers) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        json_data = resp.json()
                        curr = json_data.get("current", {})

                        # قیمت یورو به ریال
                        eur_obj = curr.get("price_eur") or curr.get("sarafiroyal_eur_sell") or curr.get("sarafiyaran_eur_sell")
                        usd_obj = curr.get("price_dollar_rl")

                        eur_toman = 0
                        usd_toman = 0

                        if eur_obj:
                            val_str = eur_obj.get("p", "") if isinstance(eur_obj, dict) else str(eur_obj)
                            clean = re.sub(r"[^\d]", "", val_str)
                            if clean:
                                eur_toman = int(clean) // 10

                        if usd_obj:
                            val_str = usd_obj.get("p", "") if isinstance(usd_obj, dict) else str(usd_obj)
                            clean = re.sub(r"[^\d]", "", val_str)
                            if clean:
                                usd_toman = int(clean) // 10

                        if eur_toman > 50000:
                            tehran_tz = pytz.timezone("Asia/Tehran")
                            now_str = datetime.now(tehran_tz).strftime("%H:%M:%S - %Y/%m/%d")

                            currencies_list = [
                                {"symbol": "EUR", "name": "یورو", "price": eur_toman, "change": 0.0},
                                {"symbol": "USD", "name": "دلار آمریکا", "price": usd_toman or 268000, "change": 0.0},
                            ]

                            logger.info(f"✅ Live rates fetched from TGJU: EUR={eur_toman:,} Toman")
                            return {
                                "eur_toman": eur_toman,
                                "usd_toman": usd_toman or 268000,
                                "currencies": currencies_list,
                                "gold": [],
                                "crypto": [],
                                "source": "tgju",
                                "source_name": "اتحادیه طلا و جواهر تهران (TGJU)",
                                "updated_at": now_str,
                                "timestamp": time.time()
                            }
            except Exception:
                continue

        return None

    def _get_fallback_data(self) -> Dict[str, Any]:
        """
        مقادیر پایدار آفلاین در صورت قطعی کامل اینترنت
        """
        tehran_tz = pytz.timezone("Asia/Tehran")
        now_str = datetime.now(tehran_tz).strftime("%H:%M:%S - %Y/%m/%d")

        return {
            "eur_toman": 304000,
            "usd_toman": 268000,
            "currencies": [
                {"symbol": "EUR", "name": "یورو", "price": 304000, "change": 0.0},
                {"symbol": "USD", "name": "دلار آمریکا", "price": 268000, "change": 0.0},
                {"symbol": "GBP", "name": "پوند انگلیس", "price": 355000, "change": 0.0},
                {"symbol": "AED", "name": "درهم امارات", "price": 73000, "change": 0.0},
                {"symbol": "CAD", "name": "دلار کانادا", "price": 189000, "change": 0.0},
                {"symbol": "TRY", "name": "لیر ترکیه", "price": 5450, "change": 0.0},
            ],
            "gold": [
                {"name": "طلای ۱۸ عیار", "price": 26400000, "change": 0.0},
                {"name": "سکه تمام بهار آزادی", "price": 114500000, "change": 0.0},
            ],
            "crypto": [
                {"symbol": "USDT", "name": "تتر", "price": 268000, "change": 0.0}
            ],
            "source": "static_fallback",
            "source_name": "پایگاه داده آفلاین پروجا",
            "updated_at": now_str,
            "timestamp": time.time()
        }

    def format_currency_message(self, data: Dict[str, Any], lang_code: str = "fa") -> str:
        """
        تولید متن شکیل و فرمت‌شده برای تلگرام
        """
        updated_at = data.get("updated_at", "")
        source_name = data.get("source_name", "بازار آزاد")
        currencies = data.get("currencies", [])
        gold = data.get("gold", [])
        crypto = data.get("crypto", [])

        # آیکون ارزها
        flag_icons = {
            "EUR": "💶",
            "USD": "💵",
            "GBP": "💷",
            "AED": "🇦🇪",
            "CAD": "🇨🇦",
            "TRY": "🇹🇷",
            "CHF": "🇨🇭",
            "AUD": "🇦🇺"
        }

        lines = [
            "🏛 <b>تابلو زنده نرخ ارز، طلا و رمزارز</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📡 <b>مرجع:</b> {source_name}",
            f"🕒 <b>آخرین بروزرسانی:</b> <code>{updated_at}</code>\n",
            "💱 <b>اسکناس و ارزهای خارجی (تومان):</b>"
        ]

        for c in currencies:
            sym = c.get("symbol", "")
            icon = flag_icons.get(sym, "🔹")
            name = c.get("name", sym)
            price = c.get("price", 0)
            change = c.get("change", 0.0)
            change_str = ""
            if change > 0:
                change_str = f" 📈 +{change}%"
            elif change < 0:
                change_str = f" 📉 {change}%"

            lines.append(f"{icon} <b>{name} ({sym}):</b> <code>{price:,}</code> تومان{change_str}")

        if gold:
            lines.append("\n🪙 <b>مسکوکات و طلا (ریال):</b>")
            for g in gold:
                name = g.get("name", "")
                price = g.get("price", 0)
                change = g.get("change", 0.0)
                change_str = f" ({'+' if change>0 else ''}{change}%)" if change != 0 else ""
                lines.append(f"▫️ <b>{name}:</b> <code>{price:,}</code> ریال{change_str}")

        if crypto:
            lines.append("\n💎 <b>ارزهای دیجیتال پایه (تومان):</b>")
            for cr in crypto:
                sym = cr.get("symbol", "")
                name = cr.get("name", sym)
                price = cr.get("price", 0)
                lines.append(f"▫️ <b>{name} ({sym}):</b> <code>{price:,}</code> تومان")

        lines.append("\n━━━━━━━━━━━━━━━━━━━━")
        lines.append("🎓 <i>نرخ یورو مبنای محاسبات ISEE Parificato و هزینه‌های زندگی در پروجا است.</i>")

        return "\n".join(lines)


# نمونه سینگلتون سراسری
currency_service = CurrencyService()
