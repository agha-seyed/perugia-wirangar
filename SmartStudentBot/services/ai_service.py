import os
import json
import base64
import time
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
import asyncio
import httpx

from config import settings, logger

# Optional fallback to Gemini if installed and configured
try:
    import google.generativeai as genai
    gemini_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY")
    if gemini_key:
        genai.configure(api_key=gemini_key)
    HAS_GEMINI_LIB = True
except Exception:
    HAS_GEMINI_LIB = False


# Data structures expected by ai_handler.py
@dataclass
class AIModel:
    model_id: str
    display_name: str
    provider: str = "Atria ASI"
    priority: int = 1
    supports_vision: bool = True
    supports_audio: bool = False
    is_active: bool = True
    system_prompt_supported: bool = True


@dataclass
class AIResponse:
    text: str
    is_ai_generated: bool = True
    model_used: Optional[str] = None
    model_key: Optional[str] = None
    provider: Optional[str] = "Atria ASI"
    processing_time_ms: int = 0
    from_cache: bool = False
    is_fallback: bool = False
    was_model_fallback: bool = False
    original_model: Optional[str] = None
    error: Optional[str] = None


# Constants expected by ai_handler
AVAILABLE_MODELS = {
    "Atria-Dawn-Preview": AIModel(
        model_id="Atria-Dawn-Preview",
        display_name="Atria ASI Dawn (پیش‌فرض)",
        provider="Atria ASI",
        priority=1,
        supports_vision=True,
        supports_audio=False,
        is_active=True,
        system_prompt_supported=True
    ),
    "gemini-1.5-flash": AIModel(
        model_id="gemini-1.5-flash",
        display_name="Gemini 1.5 Flash (پشتیبان)",
        provider="Google",
        priority=2,
        supports_vision=True,
        supports_audio=True,
        is_active=False,
        system_prompt_supported=True
    ),
}

CHAT_MODEL_PRIORITY = ["Atria-Dawn-Preview", "gemini-1.5-flash"]
VISION_MODEL_PRIORITY = ["Atria-Dawn-Preview", "gemini-1.5-flash"]
AUDIO_MODEL_PRIORITY = ["Atria-Dawn-Preview", "gemini-1.5-flash"]


def get_system_prompt(context: str, lang_code: str = "fa") -> str:
    lang_instruction = {
        "fa": "همواره به زبان فارسی روان، دقیق و محترمانه پاسخ دهید.",
        "en": "Always reply in fluent, polite English.",
        "it": "Rispondi sempre in italiano corretto e cortese."
    }.get(lang_code, "همواره به زبان فارسی روان، دقیق و محترمانه پاسخ دهید.")

    base_prompts = {
        "student_assistant": (
            "شما دستیار هوشمند و رسمی دانشجویان دانشگاه دولتی پروجا (Università degli Studi di Perugia - UniPG) "
            "و دانشگاه خارجی‌ها (UniStraPg) در ایتالیا هستید.\n"
            "شما در تمام زمینه‌های زندگی دانشجویی در پروجا راهنمای دانشجویان هستید:\n"
            "۱. بورسیه استانی ADiSU Umbria (محاسبه ISEE Parificato، ددلاین‌ها، خوابگاه رایگان، کارت سلف Mensa، کمک‌هزینه نقدی)\n"
            "۲. امور اداری و مهاجرتی (کد مالیاتی Codice Fiscale، پرمسو دی سوجورنو Permesso di Soggiorno، باجه پست Poste Italiane، اداره مهاجرت Questura)\n"
            "۳. زندگی در پروجا (حمل و نقل عمومی Minimetro و Busitalia، کارت بانکی، قرارداد اجاره خانه، خرید روزمره)\n"
            "۴. امور دانشگاهی (ثبت نام در پرتال Sol، امتحانات Appello، نمرات Libretto).\n"
            f"{lang_instruction}"
        ),
        "translator": f"شما یک مترجم حرفه‌ای، رسمی و دقیق بین زبان‌های فارسی، ایتالیایی و انگلیسی هستید. متون را با رعایت اصطلاحات حقوقی، دانشگاهی و محاوره‌ای ترجمه نمایید. {lang_instruction}",
        "italian_teacher": f"شما یک استاد صبور و ماهر زبان ایتالیایی برای دانشجویان هستید. گرامر، اصطلاحات روزمره و مثال‌های کاربردی در پروجا را به خوبی تشریح کنید. {lang_instruction}",
        "support_agent": f"شما پشتیبان دلسوز و حرفه‌ای ربات تلگرام و وب‌اپلیکیشن SmartStudentBot هستید. {lang_instruction}",
        "summarizer": f"متن ورودی را به صورت منسجم، مرتب و در قالب نکات کلیدی خلاصه نمایید. {lang_instruction}",
        "vision_analyzer": f"تصویر ارائه‌شده را با دقت بررسی نمایید و تمام نکات، اسناد، فرم‌های اداری یا متن‌های موجود در آن را استخراج و تحلیل کنید. {lang_instruction}",
        "audio_transcriber": f"پیام صوتی را پیاده‌سازی و پاسخ مرتبط ارائه دهید. {lang_instruction}",
    }
    return base_prompts.get(context, base_prompts["student_assistant"])


class AIService:
    """
    سرویس جامع هوش مصنوعی SmartStudentBot
    با پشتیبانی از Atria ASI (OpenAI-compatible) و فال‌بک به Gemini
    """
    def __init__(self):
        self.bot = None
        self._cache: Dict[str, Tuple[str, float]] = {}
        self.stats = {"requests": 0, "errors": 0, "atria_requests": 0, "gemini_requests": 0}
        self.client_timeout = 45.0

    def set_bot(self, bot):
        """تنظیم رفرنس ربات تلگرام"""
        self.bot = bot

    def save_stats(self):
        """ذخیره آمار مصرف هوش مصنوعی در فایل"""
        try:
            stats_path = Path("data") / "ai_stats.json"
            stats_path.parent.mkdir(parents=True, exist_ok=True)
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"Could not save AI stats: {e}")

    def clear_cache(self) -> int:
        """پاکسازی حافظه کش پاسخ‌ها"""
        count = len(self._cache)
        self._cache.clear()
        return count

    def get_available_models(self) -> List[Dict[str, Any]]:
        """دریافت مدل‌های فعال برای پنل مدیریت"""
        return [
            {
                "id": m.model_id,
                "name": m.display_name,
                "provider": m.provider,
                "is_active": m.is_active,
                "supports_vision": m.supports_vision,
                "supports_audio": m.supports_audio,
                "requests": self.stats.get("requests", 0),
            }
            for m in AVAILABLE_MODELS.values()
        ]

    def _get_atria_key(self) -> str:
        return (getattr(settings, "ATRIA_API_KEY", "") or os.getenv("ATRIA_API_KEY", "")).strip()

    def _get_atria_base_url(self) -> str:
        return (getattr(settings, "ATRIA_BASE_URL", "") or os.getenv("ATRIA_BASE_URL", "https://api.atria-asi.ai/v1")).strip().rstrip("/")

    def _get_atria_model(self) -> str:
        return (getattr(settings, "ATRIA_MODEL", "") or os.getenv("ATRIA_MODEL", "Atria-Dawn-Preview")).strip()

    async def _call_atria(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        max_tokens: int = 1500,
        temperature: float = 0.7
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        ارسال درخواست به Atria ASI REST API
        خروجی: (text_content, model_used, error_message)
        """
        api_key = self._get_atria_key()
        if not api_key:
            return None, None, "No Atria API key configured"

        base_url = self._get_atria_base_url()
        target_model = model or self._get_atria_model()
        # Ensure exact model name casing expected by Atria ASI
        if target_model.lower() == "atria-dawn-preview":
            target_model = "Atria-Dawn-Preview"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": target_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            async with httpx.AsyncClient(timeout=self.client_timeout) as client:
                resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        msg = choices[0].get("message", {})
                        content = msg.get("content") or ""
                        # Reasoning models may include thoughts in reasoning_content
                        if not content.strip() and msg.get("reasoning_content"):
                            content = msg.get("reasoning_content", "")
                        return content.strip(), target_model, None
                    return None, target_model, "Empty choices returned from Atria API"
                else:
                    err_text = resp.text
                    logger.error(f"Atria API Error {resp.status_code}: {err_text}")
                    return None, target_model, f"Atria API {resp.status_code}: {err_text[:120]}"
        except Exception as e:
            logger.error(f"Atria Connection Exception: {e}")
            return None, target_model, str(e)

    async def _call_gemini_fallback(
        self,
        message: str,
        system_instruction: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """پشتیبان گوگل جمینای در صورت در دسترس نبودن آتریا"""
        if not HAS_GEMINI_LIB:
            return None, None, "Gemini library not available"
        gemini_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            return None, None, "No Gemini API key configured"

        try:
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_instruction
            )
            contents = []
            if history:
                for h in history[-8:]:
                    role = "model" if h.get("role") == "assistant" else "user"
                    contents.append({"role": role, "parts": [h.get("content", "")]})
            contents.append({"role": "user", "parts": [message]})

            res = await model.generate_content_async(contents)
            return res.text.strip(), "gemini-1.5-flash", None
        except Exception as e:
            logger.error(f"Gemini fallback error: {e}")
            return None, "gemini-1.5-flash", str(e)

    async def chat(
        self,
        message: str,
        user_id: int = 0,
        context: str = "student_assistant",
        model: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        use_cache: bool = True,
        lang_code: str = "fa",
    ) -> AIResponse:
        """
        ارسال پیام به هوش مصنوعی و دریافت پاسخ هوشمند
        """
        start_time = time.time()
        self.stats["requests"] = self.stats.get("requests", 0) + 1

        clean_msg = message.strip()
        cache_key = f"{context}:{lang_code}:{clean_msg.lower()}"
        
        # بررسی کش
        if use_cache and not history and cache_key in self._cache:
            cached_text, cache_time = self._cache[cache_key]
            # اعتبار ۲ ساعته
            if time.time() - cache_time < 7200:
                elapsed_ms = int((time.time() - start_time) * 1000)
                return AIResponse(
                    text=cached_text,
                    is_ai_generated=True,
                    model_used=self._get_atria_model(),
                    model_key=self._get_atria_model(),
                    provider="Atria ASI",
                    processing_time_ms=elapsed_ms,
                    from_cache=True
                )

        system_prompt = get_system_prompt(context, lang_code=lang_code)

        # ساختار پیام‌ها برای فرمت OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for item in history[-8:]:
                r = item.get("role", "user")
                if r not in ("user", "assistant", "system"):
                    r = "user"
                c = item.get("content", "")
                if c:
                    messages.append({"role": r, "content": c})
        messages.append({"role": "user", "content": clean_msg})

        # اولویت ۱: تماس با Atria ASI
        atria_key = self._get_atria_key()
        if atria_key:
            content, model_used, err = await self._call_atria(
                messages=messages,
                model=model,
                max_tokens=1500
            )
            if content:
                self.stats["atria_requests"] = self.stats.get("atria_requests", 0) + 1
                if use_cache and not history:
                    self._cache[cache_key] = (content, time.time())
                elapsed_ms = int((time.time() - start_time) * 1000)
                return AIResponse(
                    text=content,
                    is_ai_generated=True,
                    model_used=model_used or self._get_atria_model(),
                    model_key=model_used or self._get_atria_model(),
                    provider="Atria ASI",
                    processing_time_ms=elapsed_ms,
                    from_cache=False
                )
            else:
                logger.warning(f"Atria failed: {err}, checking fallback...")

        # اولویت ۲: فال‌بک به Gemini در صورت فعال بودن
        gemini_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY")
        if gemini_key:
            g_content, g_model, g_err = await self._call_gemini_fallback(
                message=clean_msg,
                system_instruction=system_prompt,
                history=history
            )
            if g_content:
                self.stats["gemini_requests"] = self.stats.get("gemini_requests", 0) + 1
                elapsed_ms = int((time.time() - start_time) * 1000)
                return AIResponse(
                    text=g_content,
                    is_ai_generated=True,
                    model_used=g_model,
                    model_key=g_model,
                    provider="Google Gemini",
                    processing_time_ms=elapsed_ms,
                    is_fallback=True,
                    was_model_fallback=True
                )

        # هیچ کلیدی تنظیم نشده یا هر دو با خطا مواجه شدند
        self.stats["errors"] = self.stats.get("errors", 0) + 1
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if not atria_key and not gemini_key:
            fail_text = (
                "⚠️ سرویس هوش مصنوعی هنوز در سرور پیکربندی نشده است.\n\n"
                "برای فعال‌سازی لطفاً متغیر محیطی ATRIA_API_KEY را در تنظیمات Render قرار دهید."
            )
        else:
            fail_text = "متاسفانه سرویس هوش مصنوعی موقتاً با کندی یا اختلال مواجه شد. لطفاً چند لحظه دیگر دوباره تلاش نمایید."

        return AIResponse(
            text=fail_text,
            is_ai_generated=False,
            is_fallback=True,
            processing_time_ms=elapsed_ms,
            error="No working AI provider"
        )

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str = "این تصویر را تحلیل کن",
        user_id: int = 0
    ) -> AIResponse:
        """
        تحلیل اسناد یا تصاویر توسط Atria ASI / Gemini
        """
        start_time = time.time()
        self.stats["requests"] = self.stats.get("requests", 0) + 1

        atria_key = self._get_atria_key()
        if atria_key:
            try:
                b64_img = base64.b64encode(image_data).decode("utf-8")
                messages = [
                    {"role": "system", "content": get_system_prompt("vision_analyzer")},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt or "این تصویر یا فرم دانشگاهی را تحلیل کن و اطلاعات آن را بنویس."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64_img}"
                                }
                            }
                        ]
                    }
                ]
                content, model_used, err = await self._call_atria(messages, max_tokens=1500)
                if content:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    return AIResponse(
                        text=content,
                        is_ai_generated=True,
                        model_used=model_used,
                        model_key=model_used,
                        provider="Atria ASI",
                        processing_time_ms=elapsed_ms
                    )
            except Exception as e:
                logger.error(f"Atria vision processing error: {e}")

        # Gemini fallback
        if HAS_GEMINI_LIB and (getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY")):
            try:
                gen_model = genai.GenerativeModel("gemini-1.5-flash")
                image_part = {"mime_type": "image/jpeg", "data": image_data}
                res = await gen_model.generate_content_async([image_part, prompt or "این سند یا تصویر را تحلیل کن."])
                elapsed_ms = int((time.time() - start_time) * 1000)
                return AIResponse(
                    text=res.text.strip(),
                    is_ai_generated=True,
                    model_used="gemini-1.5-flash",
                    model_key="gemini-1.5-flash",
                    provider="Google Gemini",
                    processing_time_ms=elapsed_ms
                )
            except Exception as e:
                logger.error(f"Gemini vision error: {e}")

        elapsed_ms = int((time.time() - start_time) * 1000)
        return AIResponse(
            text="خطا در پردازش تصویر. لطفاً تصویر باکیفیت‌تر ارسال کنید یا سوال خود را متنی بپرسید.",
            is_fallback=True,
            processing_time_ms=elapsed_ms
        )

    async def vision_chat(
        self,
        image_bytes: bytes,
        prompt: str,
        user_id: int = 0
    ) -> AIResponse:
        """رابط سازگار برای تحلیل تصویر"""
        return await self.analyze_image(image_data=image_bytes, prompt=prompt, user_id=user_id)

    async def transcribe_audio(
        self,
        audio_data: bytes,
        language: str = "fa",
        audio_format: str = "ogg"
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        تبدیل صدا به متن - در صورت نبود سرویس صوتی، درخواست ارسال متن داده می‌شود
        """
        return None, "در حال حاضر پردازش هوش مصنوعی برای پیام‌های متنی فعال است. لطفاً سوال خود را به صورت متن ارسال نمایید."

    async def voice_chat(
        self,
        audio_bytes: bytes,
        user_id: int = 0
    ) -> AIResponse:
        """پاسخ به ویس در صورت ارسال پیام صوتی"""
        return AIResponse(
            text="در حال حاضر سرویس هوش مصنوعی پیام‌های متنی را با سرعت و دقت فوق‌العاده پاسخ می‌دهد. لطفاً سوالتان را به صورت متن بنویسید. 🙏",
            is_fallback=True
        )

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        model: Optional[str] = None,
        use_cache: bool = True
    ) -> AIResponse:
        """ترجمه تخصصی بین زبان‌های ایتالیایی، انگلیسی و فارسی"""
        lang_names = {
            "fa": "فارسی",
            "it": "ایتالیایی",
            "en": "انگلیسی"
        }
        src_name = lang_names.get(source_lang, source_lang)
        tgt_name = lang_names.get(target_lang, target_lang)

        prompt = (
            f"متن زیر را از زبان {src_name} به زبان {tgt_name} ترجمه روان، شایسته و بدون کاستی کن. "
            f"تنها ترجمه نهایی را بدون مقدمه و موخره ارائه بده:\n\n{text}"
        )
        return await self.chat(
            message=prompt,
            context="translator",
            model=model,
            use_cache=use_cache
        )

    async def italian_helper(
        self,
        word: str,
        help_type: str = "grammar",
        model: Optional[str] = None
    ) -> AIResponse:
        """آموزش و تشریح کلمات و اصطلاحات زبان ایتالیایی"""
        type_labels = {
            "grammar": "دستور زبان و نقش گرامری",
            "conjugation": "صرف فعل در زمان‌های مختلف",
            "synonyms": "مترادف‌ها و کاربردهای رایج در ایتالیا",
            "examples": "جملات نمونه و موقعیت‌های کاربردی در پروجا",
        }
        label = type_labels.get(help_type, "توضیح مفهومی و مثال")
        prompt = (
            f"لطفاً واژه یا عبارت ایتالیایی «{word}» را در زمینه «{label}» "
            f"همراه با ترجمه فارسی، تلفظ و مثال‌های شفاف تشریح بفرما."
        )
        return await self.chat(
            message=prompt,
            context="italian_teacher",
            model=model
        )

    def get_status(self) -> Dict[str, Any]:
        """وضعیت لحظه‌ای سرویس هوش مصنوعی"""
        atria_key = self._get_atria_key()
        has_key = bool(atria_key)
        return {
            "status": "online" if has_key else "offline",
            "provider": "Atria ASI",
            "model": self._get_atria_model(),
            "models_available": len(AVAILABLE_MODELS),
            "healthy": has_key,
            "total_requests": self.stats.get("requests", 0),
            "atria_requests": self.stats.get("atria_requests", 0),
            "gemini_requests": self.stats.get("gemini_requests", 0),
            "total_errors": self.stats.get("errors", 0),
        }


# نمونه سراسری سرویس
ai_service = AIService()