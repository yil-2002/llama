from ..config import get_settings
from .base import Checkout, PaymentNotConfigured, PaymentProvider, Plan, record_payment
from .external import ClickProvider, PaymeProvider
from .stars import StarsProvider

_REGISTRY: dict[str, type] = {
    "stars": StarsProvider,
    "click": ClickProvider,
    "payme": PaymeProvider,
}


def register_provider(name: str, cls: type) -> None:
    """Yangi provayder qo'shish uchun (masalan, Uzum Bank)."""
    _REGISTRY[name] = cls


def get_provider(name: str) -> PaymentProvider:
    if name not in get_settings().enabled_payment_providers or name not in _REGISTRY:
        raise PaymentNotConfigured(f"{name} yoqilmagan")
    return _REGISTRY[name]()


def enabled_providers(in_telegram: bool | None = None) -> list[PaymentProvider]:
    out = []
    for name in get_settings().enabled_payment_providers:
        if name in _REGISTRY:
            p = _REGISTRY[name]()
            if in_telegram is None or p.in_telegram == in_telegram:
                out.append(p)
    return out


__all__ = [
    "Checkout",
    "PaymentNotConfigured",
    "PaymentProvider",
    "Plan",
    "enabled_providers",
    "get_provider",
    "record_payment",
    "register_provider",
]
