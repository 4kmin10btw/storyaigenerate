import os
import time
from dotenv import load_dotenv
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole


"""
Обертка над GigaChat SDK.
"""

load_dotenv()
_client = None


def get_client() -> GigaChat:
    """Инициализация единственного экземпляра GigaChat на весь процесс."""
    global _client
    if _client is not None:
        return _client
    credentials = os.getenv("GIGACHAT_CLIENT_SECRET")
    if not credentials:
        raise RuntimeError("Не задан GIGACHAT_CLIENT_SECRET в .env")
    credentials = credentials.strip()
    _client = GigaChat(
        credentials=credentials,
        verify_ssl_certs=False,
    )
    return _client


def ask(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 3000,
    retries: int = 3,
) -> str:
    """
    Отправляет системный + пользовательский промпт в GigaChat и возвращает
    текст ответа. Простейший retry на случай сетевых сбоев/лимитов.
    """
    client = get_client()
    chat = Chat(
        messages=[
            Messages(role=MessagesRole.SYSTEM, content=system_prompt),
            Messages(role=MessagesRole.USER, content=user_prompt),
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = client.chat(chat)
            return response.choices[0].message.content
        except Exception as exc:  # лимиты
            last_error = exc
            wait = 2 * attempt
            print(f"[gigachat_client] попытка {attempt} не удалась: {exc}. Жду {wait}с...")
            time.sleep(wait)
    raise RuntimeError(f"GigaChat недоступен после {retries} попыток: {last_error}")