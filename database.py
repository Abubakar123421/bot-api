import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = os.environ.get("MONGODB_URI")

client = AsyncIOMotorClient(MONGODB_URI)
db     = client["botdb"]
guilds = db["guilds"]

DEFAULT_SETTINGS = {
    "welcome_enabled":    False,
    "welcome_channel_id": None,
    "welcome_message":    "Welcome {user} to {server}! 🎉",
    "welcome_color":      "#5865F2",
    "verify_channel_id":  None,
    "videos_channel_id":  None,
    "role_name":          "subscribers",
    "required_texts": [
        "agtop",
        "subscribed",
        "agtop302",
        "i create discord related tutorials"
    ]
}

async def get_guild_settings(guild_id: str) -> dict:
    settings = await guilds.find_one({"guild_id": guild_id})
    if not settings:
        new_settings = {"guild_id": guild_id, **DEFAULT_SETTINGS}
        await guilds.insert_one(new_settings)
        return new_settings
    return settings

async def update_guild_settings(guild_id: str, updates: dict) -> None:
    await guilds.update_one(
        {"guild_id": guild_id},
        {"$set": updates},
        upsert=True
    )
