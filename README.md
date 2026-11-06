# Kityou Keys — Telegram-бот для продажи ключей

Бот @kityouDOM_bot: клиент оплачивает (Telegram Stars или перевод на Сбер),
получает ровно один ключ со склада. Админ подтверждает ручные платежи,
склад и статистика — команды /stock и /admin.

## Запуск

```bash
pip install -r requirements.txt
python bot.py
```

Переменные окружения: `BOT_TOKEN`, `ADMIN_IDS`, `DATA_DIR` (по умолчанию /app/data,
постоянный диск хостинга). База SQLite создаётся автоматически.
