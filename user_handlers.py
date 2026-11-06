"""Обработчики для покупателей: меню, оплата звёздами, оплата на Сбер."""

from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

import database as db
import keyboards as kb
import notify
import texts
from config import (
    ADMIN_IDS,
    PRICE_RUB,
    PRICE_STARS,
    PRODUCT_DESCRIPTION,
    PRODUCT_NAME,
)
from states import OrderFlow

logger = logging.getLogger(__name__)
router = Router()


async def _show(callback: CallbackQuery, text: str, markup=None) -> None:
    """Правит сообщение, а если не получается — отправляет новое."""
    if callback.message is None:
        return
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "not modified" in str(exc):
            return
        try:
            await callback.message.answer(text, reply_markup=markup)
        except Exception:
            logger.exception("Не удалось показать сообщение")
    except Exception:
        logger.exception("Не удалось показать сообщение")


# --------------------------------------------------------------------------- #
#  Меню
# --------------------------------------------------------------------------- #
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.start_text(), reply_markup=kb.main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.how_text(), reply_markup=kb.back_menu())


@router.message(Command("paysupport"))
async def cmd_paysupport(message: Message) -> None:
    await message.answer(texts.paysupport_text())


@router.callback_query(F.data == "home")
async def cb_home(callback: CallbackQuery) -> None:
    await _show(callback, texts.start_text(), kb.main_menu())
    await callback.answer()


@router.callback_query(F.data == "how")
async def cb_how(callback: CallbackQuery) -> None:
    await _show(callback, texts.how_text(), kb.back_menu())
    await callback.answer()


@router.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery) -> None:
    await _show(callback, texts.support_text(), kb.back_menu())
    await callback.answer()


@router.callback_query(F.data == "buy")
async def cb_buy(callback: CallbackQuery) -> None:
    if db.stock_count() == 0:
        await callback.answer(texts.no_keys(), show_alert=True)
        return
    await _show(callback, texts.buy_text(), kb.buy_menu())
    await callback.answer()


# --------------------------------------------------------------------------- #
#  Оплата Telegram Stars (автоматически)
# --------------------------------------------------------------------------- #
@router.callback_query(F.data == "pay_stars")
async def cb_pay_stars(callback: CallbackQuery, bot: Bot) -> None:
    if db.stock_count() == 0:
        await callback.answer(texts.no_keys(), show_alert=True)
        return

    user = callback.from_user
    order_id = db.create_pending_order(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        method="stars",
        price=PRICE_STARS,
    )

    try:
        await bot.send_invoice(
            chat_id=user.id,
            title=PRODUCT_NAME,
            description=PRODUCT_DESCRIPTION,
            payload=f"order:{order_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=PRODUCT_NAME, amount=PRICE_STARS)],
        )
    except Exception:
        logger.exception("Не удалось отправить счёт со звёздами")
        db.set_order_status(order_id, "expired")
        await callback.answer(
            "Не удалось создать счёт. Попробуйте позже.", show_alert=True
        )
        return

    await callback.answer("Счёт отправлен 👇")


@router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery) -> None:
    if db.stock_count() == 0:
        await query.answer(
            ok=False,
            error_message="Ключи временно закончились. Напишите в поддержку.",
        )
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_stars_paid(message: Message, bot: Bot) -> None:
    payment = message.successful_payment
    if payment is None:
        return

    try:
        order_id = int(payment.invoice_payload.split(":")[-1])
    except (ValueError, AttributeError):
        logger.error("Некорректный payload: %s", payment.invoice_payload)
        return

    order = db.get_order(order_id)
    if order is None:
        await notify.notify_admins(
            bot, f"⚠️ Оплата по неизвестному заказу: {payment.invoice_payload}"
        )
        return

    key, error = db.confirm_order(
        order_id, charge_id=payment.telegram_payment_charge_id
    )

    if error == "already":
        logger.info("Повторное уведомление об оплате заказа #%s", order_id)
        return

    order = db.get_order(order_id) or order

    if error == "no_keys":
        await notify.notify_admins(bot, texts.admin_no_keys(order))
        await message.answer(
            "✅ Оплата получена, но ключи временно закончились.\n\n"
            "Администратор свяжется с вами. " + texts.SUPPORT_LINE
        )
        return

    if key:
        await notify.deliver_key(bot, order, key)


# --------------------------------------------------------------------------- #
#  Оплата переводом на Сбер (ручное подтверждение)
# --------------------------------------------------------------------------- #
@router.callback_query(F.data == "pay_sber")
async def cb_pay_sber(callback: CallbackQuery) -> None:
    user = callback.from_user
    order = db.get_active_sber_order(user.id)

    if order is not None:
        if order["status"] == "review":
            await callback.answer(
                "Ваша оплата уже на проверке ✅", show_alert=True
            )
            return
    else:
        order = db.create_sber_order(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            price=PRICE_RUB,
        )
        if order is None:
            await callback.answer(texts.no_keys(), show_alert=True)
            return

    await _show(callback, texts.sber_requisites(order["id"]), kb.sber_menu(order["id"]))
    await callback.answer()


@router.callback_query(F.data.startswith("sber_paid:"))
async def cb_sber_paid(
    callback: CallbackQuery, state: FSMContext
) -> None:
    try:
        order_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка заказа", show_alert=True)
        return

    order = db.get_order(order_id)
    if order is None or order["user_id"] != callback.from_user.id:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    if order["status"] == "review":
        await callback.answer("Заявка уже на проверке ✅", show_alert=True)
        return
    if order["status"] != "pending":
        await callback.answer("Этот заказ уже обработан", show_alert=True)
        return

    db.set_order_status(order_id, "review")
    await state.set_state(OrderFlow.waiting_proof)
    await state.update_data(order_id=order_id)

    if callback.message:
        await callback.message.answer(texts.ask_proof(), reply_markup=kb.cancel_menu())
    await callback.answer()


@router.message(OrderFlow.waiting_proof, F.photo | F.document | F.text)
async def on_proof(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    order_id = data.get("order_id")
    order = db.get_order(order_id) if order_id else None

    if order is None or order["status"] != "review":
        await state.clear()
        await message.answer("Заявка не найдена. Оформите покупку заново: /start")
        return

    db.save_proof(order_id, message.chat.id, message.message_id)
    await state.clear()

    if not ADMIN_IDS:
        await message.answer(
            "⚠️ Администратор ещё не настроил бота, поэтому заявку некому проверить. "
            + texts.SUPPORT_LINE
        )
        return

    await notify.send_proof_to_admins(bot, message, order)
    await message.answer(texts.proof_received())


@router.message(OrderFlow.waiting_proof)
async def on_proof_wrong(message: Message) -> None:
    await message.answer(
        "Пришлите, пожалуйста, скриншот или фото чека (или текст с деталями перевода)."
    )


# --------------------------------------------------------------------------- #
#  Прочее
# --------------------------------------------------------------------------- #
@router.message(Command("mykeys"))
async def cmd_mykeys(message: Message) -> None:
    rows = db.user_keys(message.from_user.id)
    if not rows:
        await message.answer(texts.my_keys_empty())
        return

    lines = [texts.my_keys_intro()]
    for row in rows:
        lines.append(
            f"#{row['id']:04d} — <code>{escape(row['key_value'] or '')}</code>"
        )
    await message.answer("\n".join(lines))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    order_id = data.get("order_id")
    if order_id:
        db.set_order_status(order_id, "pending")
    await state.clear()
    await message.answer("Отменено. Открыть меню: /start")


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    order_id = data.get("order_id")
    if order_id:
        db.set_order_status(order_id, "pending")
    await state.clear()
    await callback.answer("Отменено")
    await _show(callback, texts.start_text(), kb.main_menu())


@router.message()
async def fallback(message: Message) -> None:
    if message.from_user and message.from_user.id in ADMIN_IDS:
        await message.answer(
            "Не понял команду. Меню: /start, админка: /admin"
        )
    else:
        await message.answer("Нажмите /start, чтобы открыть меню 🙂")


@router.callback_query()
async def cb_fallback(callback: CallbackQuery) -> None:
    await callback.answer()
