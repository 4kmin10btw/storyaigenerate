import json
import re
from typing import Any, Optional


"""Мелкие утилиты, общие для всех агентов."""


def extract_json(raw_text: str) -> Optional[Any]:
    """
    Модель иногда оборачивает JSON в ```json ... ``` или добавляет пояснения
    до/после. Эта функция пытается вытащить и распарсить JSON-объект максимально
    терпимо к таким отклонениям.
    """
    if raw_text is None:
        return None
    text = raw_text.strip()
    # снимаем markdown-ограждения ```json ... ``` или ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    # прямой парсинг
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # запасной вариант: вырезаем от первой { до последней }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None
    return None


def safe_get(d: dict, path: list, default=None):
    """Достает значение по цепочке ключей, не падая на отсутствующих уровнях"""
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur
