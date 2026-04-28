import random
import string
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, Header
from aiogram import Bot

from app.api.models import AuthRequest, AuthVerify, TokenResponse, UserInfo
from app.api.utils import create_access_token
from app.api.deps import get_current_user
from app.db.database import (
    get_user_by_identifier, save_web_auth_code, 
    get_web_auth_code, delete_web_auth_code
)
from app.handlers.common import normalize_phone
from app.config import config

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Global bot instance, will be set in main.py or during startup
bot_instance: Bot = None

def set_bot_instance(bot: Bot):
    global bot_instance
    bot_instance = bot

@router.get("/me", response_model=UserInfo)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Returns the current user's profile information."""
    return {
        "id": current_user["user_id"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "username": None
    }

@router.post("/request-code")
async def request_code(payload: AuthRequest):
    identifier = payload.identifier.strip()
    
    # Normalize if it's not an ID
    if not identifier.startswith("!"):
        identifier = normalize_phone(identifier)
    
    user = await get_user_by_identifier(identifier)
    if not user:
        raise HTTPException(status_code=404, detail="Користувача не знайдено в базі.")
    
    if not user.get('user_id'):
        raise HTTPException(status_code=400, detail="Користувач ще не зареєстрований у Telegram-боті.")

    # Generate 6-digit code
    code = "".join(random.choices(string.digits, k=6))
    expires_at = datetime.now() + timedelta(minutes=10)
    
    await save_web_auth_code(user['user_id'], code, expires_at)
    
    # Send code via Bot
    if bot_instance:
        try:
            msg = (
                f"🔐 <b>Код авторизації для сайту:</b>\n\n"
                f"<code>{code}</code>\n\n"
                f"Дійсний 10 хвилин. Не передавайте цей код нікому."
            )
            await bot_instance.send_message(chat_id=user['user_id'], text=msg, parse_mode="HTML")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Помилка відправки повідомлення в Telegram: {e}")
    else:
        # For testing purposes if bot is not running
        print(f"DEBUG: Auth code for {user['full_name']}: {code}")

    return {"message": "Код відправлено в Telegram."}

@router.post("/verify-code", response_model=TokenResponse)
async def verify_code(payload: AuthVerify):
    identifier = payload.identifier.strip()
    if not identifier.startswith("!"):
        identifier = normalize_phone(identifier)
        
    user = await get_user_by_identifier(identifier)
    if not user:
        raise HTTPException(status_code=404, detail="Користувача не знайдено.")

    is_valid = await get_web_auth_code(user['user_id'], payload.code)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Невірний або прострочений код.")

    # Clean up code after use
    await delete_web_auth_code(user['user_id'])

    # Create JWT
    token_data = {
        "sub": str(user['user_id']),
        "role": user['role'],
        "full_name": user['full_name']
    }
    
    # Check if user is admin via config.admin_ids
    if user['user_id'] in config.admin_ids:
        token_data['role'] = 'admin'

    token = create_access_token(token_data)
    
    return {
        "access_token": token,
        "role": token_data['role'],
        "full_name": user['full_name']
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """
    Refreshes the current access token.
    Only works if the current token is still valid.
    """
    token_data = {
        "sub": str(current_user['user_id']),
        "role": current_user['role'],
        "full_name": current_user['full_name']
    }
    
    # Ensure role is current (e.g. if someone was promoted to admin)
    if current_user['user_id'] in config.admin_ids:
        token_data['role'] = 'admin'

    token = create_access_token(token_data)
    
    return {
        "access_token": token,
        "role": token_data['role'],
        "full_name": current_user['full_name']
    }
