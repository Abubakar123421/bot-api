
import os
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from database import get_guild_settings, update_guild_settings, guilds

router = APIRouter()

API_SECRET = os.environ.get("API_SECRET", "agtop302dashboard")


def verify_token(x_api_key: str = Header(...)):
    if x_api_key != API_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ── Models ────────────────────────────────────────────────────
class WelcomeSettings(BaseModel):
    welcome_enabled:    Optional[bool] = None
    welcome_channel_id: Optional[str]  = None
    welcome_message:    Optional[str]  = None
    welcome_color:      Optional[str]  = None

class VerifySettings(BaseModel):
    verify_channel_id: Optional[str]       = None
    role_name:         Optional[str]       = None
    required_texts:    Optional[List[str]] = None

class YoutubeSettings(BaseModel):
    videos_channel_id: Optional[str] = None


# ── GET guild settings ────────────────────────────────────────
@router.get("/{guild_id}/settings")
async def get_settings(guild_id: str, x_api_key: str = Header(...)):
    verify_token(x_api_key)
    settings = await get_guild_settings(guild_id)
    settings.pop("_id", None)
    return settings


# ── SAVE welcome settings ─────────────────────────────────────
@router.post("/{guild_id}/welcome")
async def save_welcome(guild_id: str, body: WelcomeSettings, x_api_key: str = Header(...)):
    verify_token(x_api_key)
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided")
    await update_guild_settings(guild_id, updates)
    return {"success": True, "updated": updates}


# ── SAVE verification settings ────────────────────────────────
@router.post("/{guild_id}/verify")
async def save_verify(guild_id: str, body: VerifySettings, x_api_key: str = Header(...)):
    verify_token(x_api_key)
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided")
    await update_guild_settings(guild_id, updates)
    return {"success": True, "updated": updates}


# ── SAVE youtube settings ─────────────────────────────────────
@router.post("/{guild_id}/youtube")
async def save_youtube(guild_id: str, body: YoutubeSettings, x_api_key: str = Header(...)):
    verify_token(x_api_key)
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided")
    await update_guild_settings(guild_id, updates)
    return {"success": True, "updated": updates}


# ── GET all guilds ────────────────────────────────────────────
@router.get("/all")
async def get_all_guilds(x_api_key: str = Header(...)):
    verify_token(x_api_key)
    all_guilds = await guilds.find({}).to_list(length=None)
    for g in all_guilds:
        g.pop("_id", None)
    return all_guilds
