import json
from gigachat_client import ask
from prompts import WRITER_SYSTEM
from utils import extract_json

"""Агент-писатель: пишет черновик одной сцены, опираясь на память рассказа."""


def run_writer(memory, scene: dict, revision_note=None) -> dict:
    snapshot = memory.snapshot_for_prompt()
    context = {
        "scene": scene,
        "memory": snapshot,
    }
    if revision_note:
        context["revision_note"] = revision_note
    user_prompt = (
        "Контекст (память рассказа и задание на сцену) в формате JSON:\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
        + "\n\nНапиши черновик этой сцены."
    )
    raw = ask(WRITER_SYSTEM, user_prompt, temperature=0.85)
    draft = extract_json(raw)
    if draft is None or "text" not in draft:
        # запасной вариант: считаем весь ответ текстом сцены без структурных изменений
        draft = {"text": raw, "new_entities": [], "entity_updates": [],
                  "new_events": [], "threads_planted": [], "threads_resolved": []}

    return draft
