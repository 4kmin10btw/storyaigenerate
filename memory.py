import json
from typing import Any, Dict, List, Optional

"""
Память рассказа, построенная по принципу онтологии.

Идея: хранить не только "текущее состояние мира", но и историю изменений
каждого объекта (по аналогии со схемой системного оператора - состояние
системы отслеживается во времени, а не перезаписывается молча). Это дает
возможность контроллеру проверять таймлайн и логику: если персонаж
"вдруг" оказался там, где не мог быть, это видно из истории.
Структура:
- entities:      персонажи, локации, предметы - текущие атрибуты + history[]
- timeline:      хронология событий рассказа (не порядок сцен в тексте,
                  а порядок событий "внутри мира")
- world_facts:   неизменяемые установленные факты о мире/сюжете
- open_threads:  посеянные, но еще не оплаченные сюжетные обещания
- plan:          план архитектора (структура, сцены)
- critique_log:  история оценок критика по сценам и попыткам
"""


class StoryMemory:
    def __init__(self):
        self.data: Dict[str, Any] = {
            "meta": {"premise": None, "title": None},
            "entities": {},
            "timeline": [],
            "world_facts": [],
            "open_threads": [],
            "plan": {},
            "critique_log": {},
        }
        self._next_id = 1

    def _gen_id(self, prefix: str) -> str:
        new_id = f"{prefix}_{self._next_id}"
        self._next_id += 1
        return new_id

    def set_premise(self, premise: str):
        self.data["meta"]["premise"] = premise

    def set_plan(self, plan: dict):
        self.data["meta"]["title"] = plan.get("title")
        self.data["plan"] = plan

    def add_entity(self, type_: str, name: str, attributes: Optional[dict] = None,
                   scene_idx: int = 0, entity_id: Optional[str] = None) -> str:
        eid = entity_id or self._gen_id(type_[:3])
        if eid in self.data["entities"]:
            return eid
        self.data["entities"][eid] = {
            "type": type_,
            "name": name,
            "attributes": attributes or {},
            "history": [{"scene": scene_idx, "event": "created", "attributes": attributes or {}}],
        }
        return eid

    def update_entity(self, entity_id: str, field: str, new_value: Any,
                       reason: str, scene_idx: int):
        entity = self.data["entities"].get(entity_id)
        if entity is None:
            return
        old_value = entity["attributes"].get(field)
        entity["attributes"][field] = new_value
        entity["history"].append({
            "scene": scene_idx,
            "field": field,
            "old": old_value,
            "new": new_value,
            "reason": reason,
        })

    def find_entity_id_by_name(self, name: str) -> Optional[str]:
        for eid, e in self.data["entities"].items():
            if e["name"].strip().lower() == name.strip().lower():
                return eid
        return None

    # временная линия

    def add_event(self, scene_idx: int, summary: str, time_label: str = "",
                  causes: Optional[List[str]] = None, entities: Optional[List[str]] = None) -> str:
        eid = self._gen_id("ev")
        self.data["timeline"].append({
            "id": eid,
            "scene": scene_idx,
            "time_label": time_label,
            "summary": summary,
            "causes": causes or [],
            "entities": entities or [],
        })
        return eid

    # факты мира

    def add_world_fact(self, fact: str, scene_idx: int = 0):
        if any(f["fact"] == fact for f in self.data["world_facts"]):
            return
        self.data["world_facts"].append({
            "id": self._gen_id("fact"),
            "fact": fact,
            "scene": scene_idx,
        })

    # сюжетные нити

    def add_thread(self, description: str, planted_scene: int) -> str:
        tid = self._gen_id("thr")
        self.data["open_threads"].append({
            "id": tid,
            "description": description,
            "planted_scene": planted_scene,
            "status": "open",
            "resolved_scene": None,
        })
        return tid

    def resolve_thread_by_description(self, description_hint: str, scene_idx: int):
        for t in self.data["open_threads"]:
            if t["status"] == "open" and description_hint.strip().lower() in t["description"].strip().lower():
                t["status"] = "resolved"
                t["resolved_scene"] = scene_idx
                return

    def open_threads_list(self) -> List[dict]:
        return [t for t in self.data["open_threads"] if t["status"] == "open"]

    # применение вывода писателя

    def apply_writer_output(self, scene_idx: int, draft: dict):
        """
        draft - распарсенный JSON от писателя:
        {
          "text": "...",
          "new_entities": [{"type":..,"name":..,"attributes":{...}}],
          "entity_updates": [{"name":..,"field":..,"new_value":..,"reason":..}],
          "new_events": [{"summary":..,"time_label":..,"entities":[..]}],
          "threads_planted": ["..."],
          "threads_resolved": ["..."]
        }
        """
        for e in draft.get("new_entities", []) or []:
            self.add_entity(
                type_=e.get("type", "object"),
                name=e.get("name", "безымянный"),
                attributes=e.get("attributes", {}),
                scene_idx=scene_idx,
            )

        for u in draft.get("entity_updates", []) or []:
            eid = self.find_entity_id_by_name(u.get("name", ""))
            if eid:
                self.update_entity(
                    eid, u.get("field", "note"), u.get("new_value"),
                    u.get("reason", ""), scene_idx,
                )
        for ev in draft.get("new_events", []) or []:
            self.add_event(
                scene_idx=scene_idx,
                summary=ev.get("summary", ""),
                time_label=ev.get("time_label", ""),
                entities=ev.get("entities", []),
            )
        for thr in draft.get("threads_planted", []) or []:
            self.add_thread(thr, planted_scene=scene_idx)
        for thr in draft.get("threads_resolved", []) or []:
            self.resolve_thread_by_description(thr, scene_idx)

    # критик

    def log_critique(self, scene_idx: int, attempt: int, critique: dict):
        key = str(scene_idx)
        self.data["critique_log"].setdefault(key, [])
        self.data["critique_log"][key].append({"attempt": attempt, **critique})

    # снимок для промпта

    def snapshot_for_prompt(self, max_events: int = 15) -> dict:
        """
        Урезанный снимок памяти для передачи в промпт агентам - чтобы не раздувать
        контекст полной историей изменений
        """
        entities_brief = {
            eid: {"type": e["type"], "name": e["name"], "attributes": e["attributes"]}
            for eid, e in self.data["entities"].items()
        }
        return {
            "world_facts": [f["fact"] for f in self.data["world_facts"]],
            "entities": entities_brief,
            "timeline_recent": self.data["timeline"][-max_events:],
            "open_threads": [t["description"] for t in self.open_threads_list()],
        }

    def full_snapshot_for_critic(self) -> dict:
        """Критику отдаем полную картину, включая историю изменений сущностей"""
        return self.data

    # сохранение

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def load(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
