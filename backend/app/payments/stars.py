"""Telegram Stars (XTR) obunasi.

createInvoiceLink + subscription_period=30 kun => Telegram har oy avtomatik yechadi.
To'lov tasdig'i bot'dagi successful_payment handler orqali keladi (bot/handlers.py).
https://core.telegram.org/bots/payments-stars
"""
import json

import httpx

from ..config import get_settings
from ..models import User
from .base import Checkout, Plan

SUBSCRIPTION_PERIOD = 2592000  # Telegram faqat 30 kunni qo'llab-quvvatlaydi


def make_payload(user: User, plan: Plan) -> str:
    return json.dumps({"u": user.id, "p": plan.code})


def parse_payload(payload: str) -> dict:
    return json.loads(payload)


class StarsProvider:
    name = "stars"
    in_telegram = True

    def __init__(self, http: httpx.AsyncClient | None = None):
        s = get_settings()
        self._http = http or httpx.AsyncClient(base_url=f"https://api.telegram.org/bot{s.bot_token}", timeout=20)

    def plans(self) -> list[Plan]:
        s = get_settings()
        return [Plan("premium_month", "Premium — 30 kun", s.premium_period_days, s.premium_stars_price, "XTR")]

    async def create_checkout(self, user: User, plan: Plan) -> Checkout:
        resp = await self._http.post(
            "/createInvoiceLink",
            json={
                "title": "Owly Premium",
                "description": "Cheksiz AI suhbat, IELTS mock va o'zbekcha batafsil feedback",
                "payload": make_payload(user, plan),
                "currency": "XTR",
                "prices": [{"label": plan.title, "amount": plan.price}],
                "subscription_period": SUBSCRIPTION_PERIOD,
            },
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("ok"):
            raise RuntimeError(body.get("description", "createInvoiceLink xatosi"))
        return Checkout(provider=self.name, url=body["result"])
