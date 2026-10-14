from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from src.config import get_settings

def get_async_db() -> AsyncIOMotorDatabase:
    global _async_client
    settings = get_settings()
    if _async_client is None:
        _async_client = AsyncIOMotorClient(settings.mongodb_uri)
    return _async_client[settings.mongodb_db_name]


async def ping_database() -> bool:
    db = get_async_db()
    res = await db.command("ping")
    return bool(res.get("ok"))
