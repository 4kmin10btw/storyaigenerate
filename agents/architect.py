from gigachat_client import ask
from prompts import ARCHITECT_SYSTEM
from utils import extract_json


"""Агент-архитектор: проектирует структуру рассказа, персонажей и план сцен."""


def run_architect(memory, premise: str) -> dict:
    memory.set_premise(premise)
    user_prompt = f"Тема/жанр рассказа: {premise}\n\nСпроектируй структуру рассказа."
    raw = ask(ARCHITECT_SYSTEM, user_prompt, temperature=0.8)
    plan = extract_json(raw)
    if plan is None:
        raise RuntimeError(f"Архитектор вернул невалидный JSON:\n{raw}")
    memory.set_plan(plan)
    for c in plan.get("characters", []):
        memory.add_entity(
            type_="character",
            name=c.get("name", "безымянный"),
            attributes={
                "role": c.get("role", ""),
                "want": c.get("want", ""),
                "need": c.get("need", ""),
                "arc": c.get("arc", ""),
            },
            scene_idx=0,
        )
    for loc in plan.get("locations", []):
        memory.add_entity(
            type_="location",
            name=loc.get("name", "безымянное место"),
            attributes={"description": loc.get("description", "")},
            scene_idx=0,
        )
    for fact in plan.get("world_facts", []):
        memory.add_world_fact(fact, scene_idx=0)
    for thread in plan.get("planned_threads", []):
        memory.add_thread(thread, planted_scene=0)
    return plan
