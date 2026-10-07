import hmac
import hashlib
import json
from urllib.parse import parse_qsl
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from typing import Dict, Any

from config import settings

# تعریف هدر برای دریافت initData در API
api_key_header = APIKeyHeader(name="X-Telegram-Init-Data", auto_error=False)

def verify_telegram_webapp_data(telegram_init_data: str) -> Dict[str, Any]:
    """
    Verifies the data received from Telegram Mini App.
    Returns the parsed data as a dict if valid.
    Raises HTTPException if invalid.
    """
    if not telegram_init_data:
        raise HTTPException(status_code=401, detail="Missing Telegram initData")

    parsed_data = dict(parse_qsl(telegram_init_data))
    if "hash" not in parsed_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram initData (missing hash)")
        
    received_hash = parsed_data.pop("hash")
    
    # Sort the dictionary keys and create a data check string
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed_data.items())
    )
    
    # Create the secret key from the bot token
    secret_key = hmac.new(
        b"WebAppData",
        settings.TELEGRAM_BOT_TOKEN.encode("utf-8"),
        hashlib.sha256
    ).digest()
    
    # Calculate the hash
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    if calculated_hash != received_hash:
        raise HTTPException(status_code=401, detail="Invalid Telegram initData signature")
        
    # Return user data if it exists
    if "user" in parsed_data:
        try:
            parsed_data["user"] = json.loads(parsed_data["user"])
        except json.JSONDecodeError:
            pass
            
    return parsed_data

async def get_current_webapp_user(init_data: str = Security(api_key_header)) -> Dict[str, Any]:
    """
    FastAPI Dependency for verifying Telegram Mini App users.
    Usage:
        @app.get("/api/v1/market")
        async def get_market(user: dict = Depends(get_current_webapp_user)):
            return {"user_id": user.get("id")}
    """
    # در محیط لوکال/تست برای سهولت توسعه می‌توان اعتبارسنجی را دور زد (اختیاری)
    if settings.IS_LOCAL and not init_data:
        return {"id": 123456, "first_name": "Test User", "username": "test_student"}
        
    data = verify_telegram_webapp_data(init_data)
    user_data = data.get("user")
    if not user_data:
        raise HTTPException(status_code=401, detail="No user data found in initData")
        
    return user_data
