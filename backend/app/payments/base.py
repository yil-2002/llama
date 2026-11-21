"""Almashtiriladigan to'lov moduli.

Har bir provayder PaymentProvider protokolini amalga oshiradi. Yoqilgan provayderlar
.env dagi PAYMENT_PROVIDERS orqali tanlanadi ("stars", "stars,click,payme").

Muhim: Telegram qoidasiga ko'ra bot/Mini App ichida raqamli obuna faqat Stars bilan
sotiladi. Click/Payme faqat Telegramdan tashqaridagi veb-sahifada ko'rsatiladi
(in_telegram=False).
"""
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Payment, User
from ..services.users import grant_premium, log_event


@dataclass
class Plan:
    code: str
    title: str
    days: int
    price: int
    currency: str  # XTR | UZS


@dataclass
class Checkout:
    provider: str
    url: str  # Stars uchun invoice link, Click/Payme uchun to'lov sahifasi


class PaymentProvider(Protocol):
    name: str
    in_telegram: bool  # True: Mini App ichida ko'rsatish mumkin

    def plans(self) -> list[Plan]: ...

    async def create_checkout(self, user: User, plan: Plan) -> Checkout: ...


class PaymentNotConfigured(RuntimeError):
    pass


async def record_payment(
    session: AsyncSession,
    user: User,
    provider: str,
    external_id: str,
    amount: int,
    currency: str,
    days: int,
) -> bool:
    """To'lovni bir marta (idempotent) qayd etadi va premiumni uzaytiradi. Takroriy bo'lsa False."""
    dup = await session.scalar(
        select(Payment).where(Payment.provider == provider, Payment.external_id == external_id)
    )
    if dup:
        return False
    session.add(
        Payment(
            user_id=user.id, provider=provider, external_id=external_id, amount=amount, currency=currency, days=days
        )
    )
    grant_premium(user, days)
    log_event(session, user, "payment")
    await session.commit()
    return True
