from gigachat_client import ask
from prompts import EDITOR_SYSTEM

"""Агент-редактор: правит стиль, диалоги, темп и подтекст, не трогая факты сюжета."""


def run_editor(memory, text: str, scene: dict) -> str:
    user_prompt = (
        f"Сцена «{scene.get('title', '')}» (цель сцены: {scene.get('goal', '')}).\n\n"
        f"Черновик:\n{text}\n\nОтредактируй."
    )
    edited = ask(EDITOR_SYSTEM, user_prompt, temperature=0.6)
    return edited.strip()
