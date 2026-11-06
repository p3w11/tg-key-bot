"""Inline-клавиатуры."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import PRICE_RUB, PRICE_STARS


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Купить ключ", callback_data="buy")],
            [
                InlineKeyboardButton(text="ℹ️ Как это работает", callback_data="how"),
                InlineKeyboardButton(text="🆘 Поддержка", callback_data="support"),
            ],
        ]
    )


def buy_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⭐ Оплатить {PRICE_STARS} звёздами",
                    callback_data="pay_stars",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"💳 Перевод {PRICE_RUB} ₽ на Сбер",
                    callback_data="pay_sber",
                )
            ],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="home")],
        ]
    )


def sber_menu(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Я оплатил", callback_data=f"sber_paid:{order_id}"
                )
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy")],
        ]
    )


def order_review_menu(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить", callback_data=f"acc:{order_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить", callback_data=f"dec:{order_id}"
                ),
            ]
        ]
    )


def admin_panel_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить ключи", callback_data="adm_addkeys")],
            [InlineKeyboardButton(text="⏳ Заявки на проверке", callback_data="adm_review")],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="adm_refresh")],
        ]
    )


def cancel_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
        ]
    )


def back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="home")]
        ]
    )
