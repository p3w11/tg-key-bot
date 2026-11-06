"""Точка входа: запуск бота."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

import admin_handlers
import database as db
import texts
import user_handlers
from config import ADMIN_IDS, BASE_DIR, BOT_TOKEN, ORDER_TTL_HOURS
from import_keys import load_keys

# Чтобы кириллица и эмодзи не роняли вывод консоли на Windows.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logger = logging.getLogger(__name__)


async def expiry_worker(bot: Bot) -> None:
    """Отменяет неоплаченные заказы и возвращает ключи на склад."""
    while True:
        try:
            for order in db.expire_old_orders(ORDER_TTL_HOURS):
                if order["method"] == "sber":
                    try:
                        await bot.send_message(
                            order["user_id"], texts.order_expired()
                        )
                    except Exception:
                        logger.info(
                            "Не удалось уведомить об отмене заказа #%s", order["id"]
                        )
        except Exception:
            logger.exception("Ошибка в планировщике заказов")
        await asyncio.sleep(1800)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )

    if not BOT_TOKEN:
        print(
            "\n[ОШИБКА] Не задан BOT_TOKEN.\n\n"
            "1. Создайте файл .env рядом с bot.py (скопируйте .env.example).\n"
            "2. Вставьте токен от @BotFather в строку BOT_TOKEN=...\n"
        )
        sys.exit(1)

    db.init()

    # При первом запуске на новом хостинге автоматически загружаем склад из keys.txt.
    if db.total_keys() == 0:
        values = load_keys(BASE_DIR / "keys.txt")
        if values:
            added, skipped = db.add_keys(values)
            logger.info(
                "Первичная загрузка ключей из keys.txt: добавлено %s, пропущено %s",
                added,
                skipped,
            )

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)

    asyncio.create_task(expiry_worker(bot))

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Главное меню"),
            BotCommand(command="mykeys", description="Мои ключи"),
            BotCommand(command="paysupport", description="Помощь по оплате"),
            BotCommand(command="myid", description="Мой Telegram ID"),
            BotCommand(command="admin", description="Админ-панель"),
            BotCommand(command="addkeys", description="Добавить ключи (админ)"),
        ]
    )

    me = await bot.get_me()
    print(f"\n✅ Бот @{me.username} запущен. Остановить: Ctrl+C\n")

    if not ADMIN_IDS:
        print(
            "⚠️  ADMIN_IDS пустой: заявки на оплату некому отправлять.\n"
            "   Напишите боту /myid, получите свой ID и добавьте его в .env:\n"
            "   ADMIN_IDS=123456789\n"
        )
    else:
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    "🤖 <b>Бот запущен</b>\n\n"
                    "Админка: /admin\n"
                    f"Ключей в наличии: <b>{db.stock_count()}</b>",
                )
            except Exception:
                logger.warning(
                    "Не удалось написать админу %s (нажмите /start в боте от своего аккаунта)",
                    admin_id,
                )

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")
