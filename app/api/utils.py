import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from app.config import config

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=config.jwt_expires_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        config.jwt_secret.get_secret_value(), 
        algorithm=config.jwt_algorithm
    )
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        decoded_token = jwt.decode(
            token, 
            config.jwt_secret.get_secret_value(), 
            algorithms=[config.jwt_algorithm]
        )
        return decoded_token if decoded_token["exp"] >= datetime.now(timezone.utc).timestamp() else None
    except:
        return None
