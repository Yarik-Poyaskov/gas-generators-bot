import asyncio
import json
from app.db.database import get_all_push_subscriptions
from app.api.notifications import send_web_push

async def test_broadcast():
    print("--- Testing Web Push Broadcast ---")
    subs = await get_all_push_subscriptions()
    print(f"Found {len(subs)} subscriptions in DB.")
    
    for sub in subs:
        sub_info = json.loads(sub["subscription_json"])
        print(f"Sending to user_id: {sub['user_id']}...")
        success = await send_web_push(sub_info, "Це тестове сповіщення від системи!", "ТЕСТ PUSH")
        if success:
            print("✅ Sent successfully!")
        else:
            print("❌ Failed to send.")

if __name__ == "__main__":
    asyncio.run(test_broadcast())
