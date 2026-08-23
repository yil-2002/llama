"""Generate a bcrypt hash for BOT_PASSWORD_HASH in .env.

Usage (from the project root, with dependencies installed):
    python -m scripts.gen_password_hash

Or directly inside the running container:
    docker compose exec bot python -m scripts.gen_password_hash

The script prompts for a password twice (no echo) and prints a bcrypt
hash to paste into .env as BOT_PASSWORD_HASH=<hash>. The plaintext
password is never written to disk or logged anywhere.
"""
from __future__ import annotations

import getpass
import sys

import bcrypt


def main() -> None:
    password = getpass.getpass("Yangi parolni kiriting: ")
    if not password:
        print("Parol bo'sh bo'lishi mumkin emas.", file=sys.stderr)
        sys.exit(1)

    confirm = getpass.getpass("Parolni qayta kiriting: ")
    if password != confirm:
        print("Parollar mos kelmadi.", file=sys.stderr)
        sys.exit(1)

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    print("\nQuyidagini .env fayliga qo'ying:\n")
    print(f"BOT_PASSWORD_HASH={hashed}\n")
    print("Botni qayta ishga tushiring: docker compose restart bot")


if __name__ == "__main__":
    main()
