# engine/form_engine.py - موتور فرم JSON-driven (قابل استفاده برای هر فرم)

import json
from typing import Tuple
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class FormEngine:
    def __init__(self, form_json_path: str):
        with open(form_json_path, "r", encoding="utf-8") as f:
            self.form = json.load(f)
        self.total_steps = len(self.form)

    def get_step_data(self, step: int):
        return next((s for s in self.form if s["step"] == step), None)

    def get_progress(self, step: int) -> str:
        percent = int((step / self.total_steps) * 100)
        bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
        return f"🔹 مرحله <b>{step}</b> از <b>{self.total_steps}</b> ({percent}%)\n[{bar}]\n"

    def get_question_keyboard(self, step: int):
        step_data = self.get_step_data(step)
        if step_data["type"] == "choice":
            buttons = []
            for opt in step_data["options"]:
                buttons.append([InlineKeyboardButton(text=opt["text"], callback_data=f"form_answer_{step}_{opt['value']}")])
            buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="form_back")])
            return InlineKeyboardMarkup(inline_keyboard=buttons)
        else:
            return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 بازگشت", callback_data="form_back")]
            ])

    def validate_input(self, step: int, value: str) -> Tuple[bool, str]:
        step_data = self.get_step_data(step)
        validation = step_data.get("validation", {})
        
        if step_data["type"] == "number":
            try:
                num = int(value)
                if validation.get("min") and num < validation["min"]:
                    return False, f"حداقل {validation['min']} باشد."
                if validation.get("max") and num > validation["max"]:
                    return False, f"حداکثر {validation['max']} باشد."
            except:
                return False, "لطفاً عدد وارد کنید."
        
        if validation.get("min_length") and len(value) < validation["min_length"]:
            return False, f"حداقل {validation['min_length']} حرف باشد."
        
        return True, ""