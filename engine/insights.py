# engine/insights.py - تولید تحلیل هوشمند

def generate_insights(data: dict, dsu_chance: dict) -> list:
    insights = []
    
    if dsu_chance["score"] >= 80:
        insights.append("🚨 اولویت بالا – شانس بورسیه بسیار بالا")
    elif dsu_chance["score"] >= 60:
        insights.append("✅ شانس خوب – با کمی بهینه‌سازی عالی می‌شود")
    
    if data.get("language_level") in ["beginner", "none"]:
        insights.append("📚 نیاز به دوره زبان پیش از ورود")
    
    if data.get("roommate_need") == "yes":
        insights.append("🏠 پیشنهاد اتصال به بخش یافتن هم‌اتاقی")
    
    if "پزشکی" in data.get("field_university", "") or "دندانپزشکی" in data.get("field_university", ""):
        insights.append("⚕️ رشته رقابتی – نیاز به بررسی نمرات و آزمون ورودی")
    
    insights.append("📞 تماس فوری توصیه می‌شود")
    
    return insights