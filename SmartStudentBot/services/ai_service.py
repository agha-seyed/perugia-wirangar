import os
import json
import base64
import time
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
import asyncio

import google.generativeai as genai
from config import settings, logger

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

# Data structures expected by ai_handler.py
@dataclass
class AIModel:
    model_id: str
    display_name: str
    provider: str = "Google"
    priority: int = 1
    supports_vision: bool = True
    supports_audio: bool = True
    is_active: bool = True
    system_prompt_supported: bool = True

@dataclass
class AIResponse:
    text: str
    is_ai_generated: bool = True
    model_used: Optional[str] = None
    model_key: Optional[str] = None
    provider: Optional[str] = "Google"
    processing_time_ms: int = 0
    from_cache: bool = False
    is_fallback: bool = False
    was_model_fallback: bool = False
    original_model: Optional[str] = None
    error: Optional[str] = None

# Constants expected by ai_handler
AVAILABLE_MODELS = {
    "gemini-1.5-flash": AIModel("gemini-1.5-flash", "Gemini 1.5 Flash", priority=1),
    "gemini-1.5-pro": AIModel("gemini-1.5-pro", "Gemini 1.5 Pro", priority=2),
}
CHAT_MODEL_PRIORITY = ["gemini-1.5-flash", "gemini-1.5-pro"]
VISION_MODEL_PRIORITY = ["gemini-1.5-flash", "gemini-1.5-pro"]
AUDIO_MODEL_PRIORITY = ["gemini-1.5-flash", "gemini-1.5-pro"]

def get_system_prompt(context: str, lang_code: str = "fa") -> str:
    lang_instruction = {
        "fa": "Reply in Persian (Farsi).",
        "en": "Reply in English.",
        "it": "Reply in Italian."
    }.get(lang_code, "Reply in Persian (Farsi).")
    
    base_prompts = {
        "student_assistant": f"You are a helpful and expert student assistant for Perugia university students in Italy. Guide them through academics, ADiSU scholarships, housing, and student life in Perugia. {lang_instruction}",
        "translator": "You are a professional translator between Italian, English and Persian.",
        "italian_teacher": f"You are a patient Italian language tutor explaining concepts clearly. {lang_instruction}",
        "support_agent": f"You are a polite customer support agent for SmartStudentBot. {lang_instruction}",
        "summarizer": f"Summarize the provided text concisely. {lang_instruction}",
        "vision_analyzer": f"Analyze this image in detail and describe its contents. {lang_instruction}",
        "audio_transcriber": f"Transcribe this audio message and answer appropriately. {lang_instruction}",
    }
    return base_prompts.get(context, base_prompts["student_assistant"])

class AIService:
    def __init__(self):
        self._models = {}
        self.bot = None
        self.stats = {"requests": 0, "errors": 0}
        
    def set_bot(self, bot):
        """تنظیم رفرنس ربات برای ارسال اکشن‌ها و پیام‌ها"""
        self.bot = bot

    def save_stats(self):
        """ذخیره آمار مصرف هوش مصنوعی"""
        try:
            stats_path = Path("data") / "ai_stats.json"
            stats_path.parent.mkdir(parents=True, exist_ok=True)
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"Could not save AI stats: {e}")
        
    def _get_gemini_model(self, model_name="gemini-1.5-flash", system_instruction=None):
        try:
            return genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction
            )
        except Exception as e:
            logger.error(f"Error creating Gemini model: {e}")
            return None

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
        start_time = time.time()
        
        system_prompt = get_system_prompt(context, lang_code=lang_code)
        target_model = model if model in ["gemini-1.5-flash", "gemini-1.5-pro"] else "gemini-1.5-flash"
        
        gen_model = self._get_gemini_model(target_model, system_instruction=system_prompt)
        
        if not gen_model:
            return AIResponse(text="سرویس هوش مصنوعی در حال حاضر در دسترس نیست.", is_fallback=True)

        try:
            # Convert history to Gemini format if provided
            contents = []
            if history:
                for h in history:
                    role = "model" if h.get("role") == "assistant" else "user"
                    contents.append({"role": role, "parts": [h.get("content", "")]})
            
            contents.append({"role": "user", "parts": [message]})
            
            # Use asyncio to run the blocking API call in an executor
            # google-generativeai has async support `generate_content_async`
            response = await gen_model.generate_content_async(contents)
            
            time_ms = int((time.time() - start_time) * 1000)
            
            return AIResponse(
                text=response.text,
                model_used=target_model,
                model_key=target_model,
                processing_time_ms=time_ms
            )
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return AIResponse(
                text=f"متاسفانه خطایی رخ داد: {str(e)[:50]}",
                is_fallback=True,
                error=str(e)
            )

    async def vision_chat(
        self,
        image_bytes: bytes,
        prompt: str,
        user_id: int = 0
    ) -> AIResponse:
        start_time = time.time()
        system_prompt = SYSTEM_PROMPTS["vision_analyzer"]
        gen_model = self._get_gemini_model("gemini-1.5-flash", system_instruction=system_prompt)
        
        try:
            image_part = {
                "mime_type": "image/jpeg",
                "data": image_bytes
            }
            response = await gen_model.generate_content_async([image_part, prompt])
            time_ms = int((time.time() - start_time) * 1000)
            return AIResponse(
                text=response.text,
                model_used="gemini-1.5-flash",
                model_key="gemini-1.5-flash",
                processing_time_ms=time_ms
            )
        except Exception as e:
            logger.error(f"Gemini Vision Error: {e}")
            return AIResponse(text="خطا در پردازش تصویر", is_fallback=True, error=str(e))

    async def voice_chat(
        self,
        audio_bytes: bytes,
        user_id: int = 0
    ) -> AIResponse:
        start_time = time.time()
        system_prompt = SYSTEM_PROMPTS["audio_transcriber"]
        gen_model = self._get_gemini_model("gemini-1.5-flash", system_instruction=system_prompt)
        
        try:
            audio_part = {
                "mime_type": "audio/ogg",
                "data": audio_bytes
            }
            response = await gen_model.generate_content_async([audio_part, "Transcribe and answer appropriately in Persian."])
            time_ms = int((time.time() - start_time) * 1000)
            return AIResponse(
                text=response.text,
                model_used="gemini-1.5-flash",
                model_key="gemini-1.5-flash",
                processing_time_ms=time_ms
            )
        except Exception as e:
            logger.error(f"Gemini Voice Error: {e}")
            return AIResponse(text="خطا در پردازش صدا", is_fallback=True, error=str(e))

    def get_status(self) -> Dict[str, Any]:
        """وضعیت سرویس هوش مصنوعی"""
        return {
            "status": "online",
            "provider": "Google Gemini",
            "model": "gemini-1.5-flash",
            "models_available": len(AVAILABLE_MODELS),
            "healthy": True
        }

ai_service = AIService()