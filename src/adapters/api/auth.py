from fastapi import Header, HTTPException
from src.infrastructure.config.settings import settings


async def verify_api_key(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
