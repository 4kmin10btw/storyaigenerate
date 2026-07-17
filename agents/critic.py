import json
from gigachat_client import ask
from prompts import CRITIC_SYSTEM
from utils import extract_json


"""Агент-контролер: проверяет согласованность с памятью и оценивает качество."""


DEFAULT_CRITIQUE = {
    "scores": {"style": 5, "density": 5, "depth": 5, "architecture": 5,
               "originality": 5, "consistency": 5},
    "issues": ["Не удалось распарсить ответ критика - использована оценка по умолчанию."],
    "verdict": "revise",
}


def run_critic(memory, text: str, scene: dict) -> dict:
    full_memory = memory.full_snapshot_for_critic()

    context = {
        "scene": scene,
        "memory": full_memory,
        "text": text,
    }
    user_prompt = (
        "Полная память рассказа и текст сцены для проверки (JSON):\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )
    raw = ask(CRITIC_SYSTEM, user_prompt, temperature=0.3)
    critique = extract_json(raw)
    if critique is None or "scores" not in critique:
        return DEFAULT_CRITIQUE
    critique.setdefault("issues", [])
    critique.setdefault("verdict", "revise")
    return critique
