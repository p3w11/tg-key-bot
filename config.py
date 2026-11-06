"""Настройки бота. Все значения берутся из файла .env рядом с bot.py."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", encoding="utf-8")


def _str(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _int(name: str, default: int) -> int:
    value = _str(name)
    try:
        return int(value)
    except ValueError:
        return default


# --- Telegram ---
BOT_TOKEN = _str("BOT_TOKEN")

# ID владельца (можно несколько через запятую). Узнать свой ID: команда /myid в боте.
ADMIN_IDS: set[int] = {
    int(part)
    for part in _str("ADMIN_IDS", "5656146940").replace(";", ",").replace(" ", "").split(",")
    if part.isdigit()
}

# --- Товар ---
PRODUCT_NAME = _str("PRODUCT_NAME", "Ключ доступа")
PRODUCT_DESCRIPTION = _str(
    "PRODUCT_DESCRIPTION",
    "Лицензионный ключ. Выдаётся автоматически после подтверждения оплаты.",
)
PRICE_RUB = max(1, _int("PRICE_RUB", 199))
PRICE_STARS = max(1, _int("PRICE_STARS", 100))

# --- Реквизиты для перевода ---
SBER_PHONE = _str("SBER_PHONE", "+79059859766")
SBER_NAME = _str("SBER_NAME", "")
SUPPORT_CONTACT = _str("SUPPORT_CONTACT", "")

# --- Прочее ---
_data_env = _str("DATA_DIR")
if _data_env:
    DATA_DIR = Path(_data_env)
elif Path("/app/data").is_dir():
    # Постоянный том на хостинге (Bothost и большинство Docker-платформ).
    DATA_DIR = Path("/app/data")
else:
    DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "bot.db"
ORDER_TTL_HOURS = _int("ORDER_TTL_HOURS", 24)
LOW_STOCK_THRESHOLD = _int("LOW_STOCK_THRESHOLD", 5)
