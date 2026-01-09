# engine/scoring.py - محاسبه خودکار شانس بورسیه DSU

def calculate_dsu_chance(data: dict) -> dict:
    score = 50  # پایه
    
    # بودجه پایین = امتیاز بالا
    budget = data.get("budget", 1000)
    if budget < 500:
        score += 30
    elif budget < 700:
        score += 20
    elif budget < 900:
        score += 10
    
    # ملیت non-EU = امتیاز بالاتر (چون رقابت کمتر در برخی موارد)
    nationality = data.get("nationality", "").lower()
    if "ایران" in nationality or "non-eu" in nationality:
        score += 15
    
    # نیاز به خوابگاه = امتیاز بالا
    if data.get("accommodation") == "dorm" or data.get("roommate_need") == "yes":
        score += 20
    
    # هدف زبان = امتیاز بالا (نیاز به حمایت بیشتر)
    if data.get("study_goal") == "language":
        score += 10
    
    # سن جوان = امتیاز
    age = data.get("age", 25)
    if age < 25:
        score += 10
    
    score = min(100, score)
    
    if score >= 80:
        label = "High"
        color = "🟢"
    elif score >= 60:
        label = "Medium"
        color = "🟡"
    else:
        label = "Low"
        color = "🔴"
    
    return {
        "score": score,
        "label": label,
        "color": color,
        "explanation": [
            "بودجه پایین" if budget < 700 else "بودجه متوسط",
            "نیاز به خوابگاه" if data.get("accommodation") == "dorm" else "آپارتمان شخصی",
            "non-EU" if "ایران" in nationality else "EU",
            "سن جوان" if age < 25 else "سن بالاتر"
        ]
    }