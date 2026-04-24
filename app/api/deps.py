from fastapi import Header, HTTPException, Depends
from app.api.utils import decode_access_token
from app.db.database import get_user

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    
    user_id = int(payload.get("sub"))
    user = await get_user(user_id)
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    return {
        "user_id": user_id,
        "role": payload.get("role"),
        "full_name": payload.get("full_name")
    }

def require_role(roles: list):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Permission denied")
        return current_user
    return role_checker
