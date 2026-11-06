"""Уведомления администраторам и выдача ключей."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, Message

import database as db
import keyboards
import texts
from config import ADMIN_IDS, LOW_STOCK_THRESHOLD

logger = logging.getLogger(__name__)


async def notify_admins(
    bot: Bot, text: str, markup: InlineKeyboardMarkup | None = None
) -> None:
    if not ADMIN_IDS:
        logger.warning("ADMIN_IDS не задан — уведомление не отправлено: %s", text)
        return
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=markup)
        except Exception:
            logger.exception("Не удалось отправить сообщение админу %s", admin_id)


async def send_proof_to_admins(bot: Bot, message: Message, order: dict) -> None:
    """Отправляет админам подтверждение оплаты вместе с кнопками."""
    if not ADMIN_IDS:
        logger.warning("ADMIN_IDS не задан — заявка #%s не отправлена", order["id"])
        return

    markup = keyboards.order_review_menu(order["id"])
    for admin_id in ADMIN_IDS:
        try:
            await bot.copy_message(
                chat_id=admin_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
        except Exception:
            logger.exception("Не удалось переслать чек админу %s", admin_id)
        try:
            await bot.send_message(
                admin_id, texts.admin_new_order(order), reply_markup=markup
            )
        except Exception:
            logger.exception("Не удалось отправить заявку админу %s", admin_id)


async def deliver_key(bot: Bot, order: dict, key: str) -> bool:
    """Отправляет ключ покупателю и уведомляет админов о продаже."""
    sent = True
    try:
        await bot.send_message(order["user_id"], texts.key_delivered(key))
    except Exception:
        sent = False
        logger.exception("Не удалось отправить ключ пользователю %s", order["user_id"])
        await notify_admins(
            bot,
            f"⚠️ Ключ выдан, но сообщение пользователю "
            f"<code>{order['user_id']}</code> не доставлено. "
            f"Заказ #{order['id']:04d}, ключ: <code>{key}</code>",
        )

    await notify_admins(bot, texts.admin_sale(order, key))

    remaining = db.stock_count()
    if remaining <= LOW_STOCK_THRESHOLD:
        await notify_admins(bot, texts.admin_stock_low(remaining))
    return sent
