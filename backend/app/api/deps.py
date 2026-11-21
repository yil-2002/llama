from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_session
from ..models import User
from ..services.users import get_or_create_user
from ..telegram_auth import InitDataError, validate_init_data


async def current_user(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        data = validate_init_data(x_telegram_init_data, get_settings().bot_token)
    except InitDataError as e:
        raise HTTPException(401, str(e)) from e
    tg = data.get("user") or {}
    if "id" not in tg:
        raise HTTPException(401, "user yo'q")
    user = await get_or_create_user(session, int(tg["id"]), tg.get("first_name", ""), tg.get("username"))
    await session.commit()
    return user


async def admin_user(user: User = Depends(current_user)) -> User:
    if user.telegram_id not in get_settings().admin_ids:
        raise HTTPException(403, "faqat adminlar uchun")
    return user
