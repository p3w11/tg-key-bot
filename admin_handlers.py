"""Админ-панель: склад ключей, заявки на оплату, подтверждение/отклонение."""

from __future__ import annotations

import logging
import re

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
import keyboards as kb
import notify
import texts
from config import ADMIN_IDS
from states import AddKeys

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int | None) -> bool:
    return bool(user_id) and user_id in ADMIN_IDS


def _parse_order_id(data: str | None) -> int | None:
    try:
        return int((data or "").split(":", 1)[1])
    except (ValueError, IndexError):
        return None


# --------------------------------------------------------------------------- #
#  Команды
# --------------------------------------------------------------------------- #
@router.message(Command("myid"))
async def cmd_myid(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    note = " (вы администратор)" if is_admin(user.id) else ""
    await message.answer(
        f"Ваш Telegram ID: <code>{user.id}</code>{note}\n\n"
        "Этот ID нужно указать в файле .env в строке ADMIN_IDS."
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user and message.from_user.id):
        await message.answer(
            "⛔ Нет доступа.\n\n"
            f"Ваш ID: <code>{message.from_user.id}</code> — "
            "добавьте его в ADMIN_IDS в файле .env."
        )
        return
    await message.answer(texts.admin_panel(db.stats()), reply_markup=kb.admin_panel_menu())


@router.message(Command("stock"))
async def cmd_stock(message: Message) -> None:
    if not is_admin(message.from_user and message.from_user.id):
        return
    await message.answer(texts.admin_panel(db.stats()), reply_markup=kb.admin_panel_menu())


@router.message(Command("addkeys"))
async def cmd_addkeys(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user and message.from_user.id):
        return
    await state.set_state(AddKeys.waiting)
    await message.answer(
        texts.admin_addkeys_prompt(), reply_markup=kb.cancel_menu()
    )


# --------------------------------------------------------------------------- #
#  Админ-панель
# --------------------------------------------------------------------------- #
@router.callback_query(F.data == "adm_refresh")
async def cb_refresh(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    if callback.message:
        try:
            await callback.message.edit_text(
                texts.admin_panel(db.stats()), reply_markup=kb.admin_panel_menu()
            )
        except Exception:
            pass
    await callback.answer()


@router.callback_query(F.data == "adm_addkeys")
async def cb_addkeys(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AddKeys.waiting)
    if callback.message:
        try:
            await callback.message.edit_text(
                texts.admin_addkeys_prompt(), reply_markup=kb.cancel_menu()
            )
        except Exception:
            await callback.message.answer(
                texts.admin_addkeys_prompt(), reply_markup=kb.cancel_menu()
            )
    await callback.answer()


@router.message(AddKeys.waiting, F.text & ~F.text.startswith("/"))
async def on_add_keys(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user and message.from_user.id):
        await state.clear()
        return

    tokens = [
        token.strip()
        for token in re.split(r"[\s,;]+", message.text or "")
        if token.strip()
    ]
    values = [token for token in tokens if len(token) >= 4]

    if not values:
        await message.answer(
            "Не нашёл ни одного ключа. Пришлите ключи построчно (минимум 4 символа)."
        )
        return

    added, skipped = db.add_keys(values)
    await state.clear()
    await message.answer(
        "✅ <b>Готово</b>\n\n"
        f"Добавлено: <b>{added}</b>\n"
        f"Пропущено (дубликаты/короткие): <b>{skipped}</b>\n"
        f"Всего в наличии: <b>{db.stock_count()}</b>",
        reply_markup=kb.admin_panel_menu(),
    )


@router.callback_query(F.data == "adm_review")
async def cb_review(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    orders = db.review_orders()
    if not orders:
        await callback.answer("Заявок на проверке нет 🎉", show_alert=True)
        return

    for order in orders:
        if order.get("proof_chat_id") and order.get("proof_message_id"):
            try:
                await bot.copy_message(
                    chat_id=callback.from_user.id,
                    from_chat_id=order["proof_chat_id"],
                    message_id=order["proof_message_id"],
                )
            except Exception:
                logger.exception("Не удалось переслать чек заказа #%s", order["id"])
        await bot.send_message(
            callback.from_user.id,
            texts.admin_new_order(order),
            reply_markup=kb.order_review_menu(order["id"]),
        )
    await callback.answer()


# --------------------------------------------------------------------------- #
#  Подтверждение / отклонение оплаты
# --------------------------------------------------------------------------- #
@router.callback_query(F.data.startswith("acc:"))
async def cb_accept(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    order_id = _parse_order_id(callback.data)
    if order_id is None:
        await callback.answer("Некорректный заказ", show_alert=True)
        return
    order = db.get_order(order_id)
    if order is None:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    key, error = db.confirm_order(order_id)

    if error == "already":
        await callback.answer("Этот заказ уже обработан", show_alert=True)
        return
    if error == "no_keys":
        await callback.answer(
            "Нет свободных ключей! Добавьте их командой /addkeys", show_alert=True
        )
        return

    fresh = db.get_order(order_id) or order
    await notify.deliver_key(bot, fresh, key)  # type: ignore[arg-type]

    if callback.message:
        try:
            base = callback.message.html_text or ""
            await callback.message.edit_text(
                base + "\n\n✅ <b>Подтверждено</b>", reply_markup=None
            )
        except Exception:
            logger.exception("Не удалось обновить сообщение заказа #%s", order_id)

    await callback.answer("Ключ выдан ✅")


@router.callback_query(F.data.startswith("dec:"))
async def cb_decline(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    order_id = _parse_order_id(callback.data)
    if order_id is None:
        await callback.answer("Некорректный заказ", show_alert=True)
        return
    order = db.decline_order(order_id)

    if order is None:
        await callback.answer("Этот заказ уже обработан", show_alert=True)
        return

    try:
        await bot.send_message(order["user_id"], texts.order_declined())
    except Exception:
        logger.exception("Не удалось сообщить об отказе пользователю %s", order["user_id"])

    if callback.message:
        try:
            base = callback.message.html_text or ""
            await callback.message.edit_text(
                base + "\n\n❌ <b>Отклонено</b>", reply_markup=None
            )
        except Exception:
            logger.exception("Не удалось обновить сообщение заказа #%s", order_id)

    await callback.answer("Заказ отклонён")
