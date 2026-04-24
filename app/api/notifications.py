from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Any
import json
import logging
from pywebpush import webpush, WebPushException

from app.api.deps import get_current_user
from app.db.database import add_push_subscription, get_all_push_subscriptions, remove_push_subscription
from app.config import config

router = APIRouter(prefix="/notifications", tags=["Notifications"])

class PushSubscription(BaseModel):
    endpoint: str
    keys: dict

@router.get("/vapid-public-key")
async def get_vapid_public_key():
    return {"public_key": config.vapid_public_key}

@router.post("/subscribe")
async def subscribe(subscription: PushSubscription, current_user: dict = Depends(get_current_user)):
    try:
        await add_push_subscription(
            user_id=current_user["user_id"],
            subscription_json=subscription.model_dump_json()
        )
        return {"status": "success", "message": "Subscribed successfully"}
    except Exception as e:
        logging.error(f"Subscription error: {e}")
        raise HTTPException(status_code=500, detail="Failed to subscribe")

async def send_web_push(subscription_info: dict, message: str, title: str = "GPU Alert"):
    """Sends a single web push notification."""
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps({
                "title": title,
                "body": message
            }),
            vapid_private_key=config.vapid_private_key,
            vapid_claims={"sub": f"mailto:{config.vapid_claim_email}"}
        )
        return True
    except WebPushException as ex:
        logging.error(f"WebPush error: {ex}")
        # If subscription is no longer valid, we should remove it
        if ex.response and ex.response.status_code in [404, 410]:
            await remove_push_subscription(json.dumps(subscription_info))
        return False
    except Exception as e:
        logging.error(f"General push error: {e}")
        return False

async def broadcast_alert(message: str, title: str = "GPU Alert"):
    """Sends notification to all active subscribers."""
    subscriptions = await get_all_push_subscriptions()
    count = 0
    for sub in subscriptions:
        sub_info = json.loads(sub["subscription_json"])
        success = await send_web_push(sub_info, message, title)
        if success:
            count += 1
    logging.info(f"Broadcasted alert to {count} devices.")
