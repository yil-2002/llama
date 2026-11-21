"""Click va Payme — MChJ/YaTT tayyor bo'lgach ulanadi.

Bu provayderlar Telegramdan TASHQARIDAGI veb-sahifada ishlatiladi (in_telegram=False),
shuning uchun Mini App ularni ko'rsatmaydi. Ulash uchun:
  1. .env: PAYMENT_PROVIDERS=stars,click,payme va CLICK_*/PAYME_* kalitlari
  2. Click (Prepare/Complete) va Payme (JSON-RPC) webhook endpoint'larini qo'shing (hali yozilmagan)
  3. Webhook muvaffaqiyatli bo'lganda payments.base.record_payment(...) chaqiriladi

Hujjatlar: Click Merchant API https://docs.click.uz , Payme Merchant/Subscribe API https://developer.help.paycom.uz
"""
import base64
from urllib.parse import urlencode

from ..config import get_settings
from ..models import User
from .base import Checkout, PaymentNotConfigured, Plan


def _uzs_plans() -> list[Plan]:
    s = get_settings()
    return [Plan("premium_month", "Premium — 30 kun", s.premium_period_days, s.premium_uzs_price, "UZS")]


class ClickProvider:
    name = "click"
    in_telegram = False

    def plans(self) -> list[Plan]:
        return _uzs_plans()

    async def create_checkout(self, user: User, plan: Plan) -> Checkout:
        s = get_settings()
        if not (s.click_service_id and s.click_merchant_id and s.click_secret_key):
            raise PaymentNotConfigured("Click kalitlari kiritilmagan")
        # merchant_trans_id = bizning buyurtma identifikatorimiz (webhook'da qaytib keladi)
        query = urlencode(
            {
                "service_id": s.click_service_id,
                "merchant_id": s.click_merchant_id,
                "amount": plan.price,
                "transaction_param": f"{user.id}:{plan.code}",
                "return_url": s.external_pay_url or s.webapp_url,
            }
        )
        return Checkout(provider=self.name, url=f"https://my.click.uz/services/pay?{query}")


class PaymeProvider:
    name = "payme"
    in_telegram = False

    def plans(self) -> list[Plan]:
        return _uzs_plans()

    async def create_checkout(self, user: User, plan: Plan) -> Checkout:
        s = get_settings()
        if not (s.payme_merchant_id and s.payme_secret_key):
            raise PaymentNotConfigured("Payme kalitlari kiritilmagan")
        # Payme summani tiyinda kutadi
        params = f"m={s.payme_merchant_id};ac.user_id={user.id};ac.plan={plan.code};a={plan.price * 100}"
        token = base64.b64encode(params.encode()).decode()
        return Checkout(provider=self.name, url=f"https://checkout.paycom.uz/{token}")
