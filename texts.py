"""Все тексты бота."""

from __future__ import annotations

from html import escape

from config import (
    PRICE_RUB,
    PRICE_STARS,
    PRODUCT_DESCRIPTION,
    PRODUCT_NAME,
    SBER_NAME,
    SBER_PHONE,
    SUPPORT_CONTACT,
)

SUPPORT_LINE = (
    f"Напишите в поддержку: {escape(SUPPORT_CONTACT)}"
    if SUPPORT_CONTACT
    else "Напишите администратору бота."
)


def start_text() -> str:
    return (
        "👋 <b>Добро пожаловать!</b>\n\n"
        f"Здесь можно купить <b>{escape(PRODUCT_NAME.lower())}</b> "
        "и получить его сразу после оплаты.\n\n"
        f"💰 Цена: <b>{PRICE_RUB} ₽</b> или <b>{PRICE_STARS} ⭐</b>"
    )


def how_text() -> str:
    return (
        "ℹ️ <b>Как это работает</b>\n\n"
        "1. Нажмите «🛒 Купить ключ» и выберите способ оплаты.\n\n"
        f"⭐ <b>Telegram Stars</b> — оплата внутри Telegram. "
        "Ключ приходит автоматически через пару секунд.\n\n"
        "💳 <b>Перевод на Сбер</b> — переводите сумму на указанный номер, "
        "нажимаете «✅ Я оплатил» и присылаете чек. "
        "После подтверждения оплаты бот сразу пришлёт ключ.\n\n"
        "🔑 Ключ приходит отдельным сообщением — нажмите на него, чтобы скопировать."
    )


def support_text() -> str:
    return (
        "🆘 <b>Поддержка</b>\n\n"
        + (f"Связь: {escape(SUPPORT_CONTACT)}\n\n" if SUPPORT_CONTACT else "")
        + "По вопросам оплаты и возврата средств: /paysupport"
    )


def paysupport_text() -> str:
    return (
        "🆘 <b>Помощь по оплате</b>\n\n"
        + (
            f"Напишите нам: {escape(SUPPORT_CONTACT)}\n\n"
            if SUPPORT_CONTACT
            else "Напишите администратору бота.\n\n"
        )
        + "Укажите номер заказа и приложите чек — так мы быстрее всё проверим."
    )


def buy_text() -> str:
    return (
        "🛒 <b>Покупка ключа</b>\n\n"
        f"{escape(PRODUCT_DESCRIPTION)}\n\n"
        f"💰 Стоимость: <b>{PRICE_RUB} ₽</b> или <b>{PRICE_STARS} ⭐</b>\n\n"
        "Выберите способ оплаты:"
    )


def sber_requisites(order_id: int) -> str:
    recipient = (
        f"\n👤 Получатель: <b>{escape(SBER_NAME)}</b>" if SBER_NAME else ""
    )
    return (
        "💳 <b>Оплата переводом на Сбер</b>\n\n"
        f"Сумма: <b>{PRICE_RUB} ₽</b>\n"
        f"Номер: <code>{escape(SBER_PHONE)}</code>{recipient}\n"
        f"Заказ: <b>#{order_id:04d}</b>\n\n"
        "1. Переведите сумму на номер выше (СБП или по номеру телефона).\n"
        "2. Нажмите «✅ Я оплатил» и пришлите чек или скриншот перевода.\n"
        "3. После проверки бот сразу пришлёт ключ.\n\n"
        "⚠️ Ключ выдаётся только после подтверждения оплаты."
    )


def ask_proof() -> str:
    return (
        "📸 <b>Пришлите подтверждение оплаты</b>\n\n"
        "Отправьте скриншот или фото чека одним сообщением. "
        "Можно добавить комментарий текстом.\n\n"
        "После проверки ключ придёт сюда автоматически."
    )


def proof_received() -> str:
    return (
        "✅ <b>Чек получен!</b>\n\n"
        "Заявка отправлена на проверку. Обычно это занимает несколько минут. "
        "Ключ придёт сюда автоматически — ничего дополнительно делать не нужно."
    )


def key_delivered(key: str) -> str:
    return (
        "🎉 <b>Оплата подтверждена!</b>\n\n"
        "🔑 Ваш ключ:\n"
        f"<code>{escape(key)}</code>\n\n"
        "Нажмите на ключ, чтобы скопировать. Сохраните его в надёжном месте."
    )


def order_declined() -> str:
    return (
        "❌ <b>Оплата не подтверждена</b>\n\n"
        "Администратор не нашёл ваш перевод. Если вы точно отправили деньги — "
        f"{SUPPORT_LINE}"
    )


def order_expired() -> str:
    return (
        "⌛ <b>Заказ отменён</b>\n\n"
        "Оплата не поступила за отведённое время. "
        "Вы можете оформить новый заказ в любой момент — нажмите /start."
    )


def no_keys() -> str:
    return "😔 Ключи временно закончились. Попробуйте позже или напишите в поддержку."


def my_keys_intro() -> str:
    return "🔑 <b>Ваши последние ключи</b>\n"


def my_keys_empty() -> str:
    return "У вас пока нет купленных ключей."


def admin_new_order(order: dict) -> str:
    username = f"@{order['username']}" if order.get("username") else "без username"
    return (
        "💳 <b>Заявка на оплату (Сбер)</b>\n\n"
        f"Заказ: <b>#{order['id']:04d}</b>\n"
        f"Сумма: <b>{order['price']} ₽</b>\n"
        f"Покупатель: <a href=\"tg://user?id={order['user_id']}\">"
        f"{escape(order.get('full_name') or str(order['user_id']))}</a>\n"
        f"Username: {escape(username)}\n"
        f"ID: <code>{order['user_id']}</code>\n\n"
        "Проверьте перевод и нажмите кнопку ниже👇"
    )


def admin_sale(order: dict, key: str) -> str:
    return (
        "✅ <b>Продажа</b>\n\n"
        f"Заказ: <b>#{order['id']:04d}</b>\n"
        f"Покупатель: <code>{order['user_id']}</code>\n"
        f"Сумма: <b>{order['price']} {'⭐' if order['method'] == 'stars' else '₽'}</b>\n"
        f"Ключ: <code>{escape(key)}</code>"
    )


def admin_no_keys(order: dict) -> str:
    return (
        "⚠️ <b>Оплата прошла, но ключей нет!</b>\n\n"
        f"Заказ: <b>#{order['id']:04d}</b>\n"
        f"Покупатель: <code>{order['user_id']}</code>\n\n"
        "Срочно добавьте ключи командой /addkeys и свяжитесь с покупателем. "
        "Либо верните платёж."
    )


def admin_panel(stats: dict) -> str:
    return (
        "🛠 <b>Админ-панель</b>\n\n"
        f"📦 Ключей в наличии: <b>{stats['available']}</b>\n"
        f"🔒 Зарезервировано: <b>{stats['reserved']}</b>\n"
        f"✅ Продано: <b>{stats['sold']}</b>\n"
        f"⏳ Заявок на проверке: <b>{stats['review']}</b>\n\n"
        f"💰 Выручка (Сбер): <b>{stats['rub_revenue']} ₽</b>\n"
        f"⭐ Продаж за звёзды: <b>{stats['stars_sales']}</b>"
    )


def admin_addkeys_prompt() -> str:
    return (
        "➕ <b>Добавление ключей</b>\n\n"
        "Отправьте ключи одним сообщением — каждый с новой строки "
        "(можно через запятую или пробел).\n\n"
        "Дубликаты будут автоматически пропущены."
    )


def admin_stock_low(available: int) -> str:
    return (
        f"⚠️ Осталось мало ключей: <b>{available}</b>\n"
        "Пополните склад командой /addkeys."
    )
