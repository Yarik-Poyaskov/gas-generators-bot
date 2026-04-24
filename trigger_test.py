import asyncio
import json
import requests
from app.db.database import get_objects_with_latest_status
from app.api.ws import broadcast_new_report

async def main():
    # 1. Find K1 ID
    objects = await get_objects_with_latest_status()
    target = None
    for obj in objects:
        if 'K1' in obj['name'] or 'K1' in (obj.get('short_name') or ''):
            target = obj
            break
    
    if not target:
        print("Object K1 not found!")
        return

    obj_id = target['id']
    print(f"Found K1 with ID: {obj_id}. Triggering animation...")
    
    # We can't call broadcast_new_report directly because it depends on the running event loop of the server.
    # Instead, let's just use the API if it has a way, or simulate a call.
    # For now, let's just print instructions or try to find a port to send a request.
    
    print(f"To see the animation, I will now add a temporary test route to the API.")

if __name__ == "__main__":
    asyncio.run(main())
