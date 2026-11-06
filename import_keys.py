"""Массовая загрузка ключей из файла keys.txt в базу бота.

Использование:
    .venv\\Scripts\\python.exe import_keys.py
    .venv\\Scripts\\python.exe import_keys.py другой_файл.txt

Ключи можно писать по одному в строке или через запятую. Строки, начинающиеся
с "#", игнорируются.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import database as db

BASE_DIR = Path(__file__).resolve().parent


def load_keys(path: Path) -> list[str]:
    """Читает ключи из текстового файла."""
    if not path.exists():
        return []

    values: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        values.extend(
            token
            for token in re.split(r"[\s,;]+", line)
            if token and len(token) >= 4
        )
    return values


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DIR / "keys.txt"
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()

    if not path.exists():
        print(f"Файл не найден: {path}")
        return

    values = load_keys(path)
    if not values:
        print("В файле не найдено ни одного ключа (минимум 4 символа).")
        return

    db.init()
    added, skipped = db.add_keys(values)
    print(
        f"Добавлено: {added}\n"
        f"Пропущено (дубликаты): {skipped}\n"
        f"Всего доступно: {db.stock_count()}"
    )


if __name__ == "__main__":
    main()
