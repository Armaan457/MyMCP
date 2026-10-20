from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from src.config import get_settings

_async_client: AsyncIOMotorClient | None = None


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


async def init_indexes():
    db = get_async_db()
    await db["resume_chunks"].create_index(
        [("content", "text"), ("title", "text"), ("tags", "text")],
        name="resume_search_index"
    )
    await db["github_cache"].create_index("username", unique=True)
    await db["leetcode_cache"].create_index("username", unique=True)

