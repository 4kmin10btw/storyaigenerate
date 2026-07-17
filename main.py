import os
from memory import StoryMemory
from agents.architect import run_architect
from agents.writer import run_writer
from agents.edigit statustor import run_editor
from agents.critic import run_critic


"""
Точка входа. Объединяет четырех агентов:
  архитектор -> писатель -> редактор -> контролер-душнила (цикл правок)
Рассказ и отчет о памяти сохраняются в директорию этого скрипта
"""

MAX_REVISIONS_PER_SCENE = 2   # сколько раз максимум переписываем сцену
CONSISTENCY_THRESHOLD = 7      # ниже - обязательная правка (нарушена логика/факты)
QUALITY_THRESHOLD = 6          # средний балл по остальным критериям, ниже - правка


def scene_passes(critique: dict) -> bool:
    scores = critique.get("scores", {})
    consistency = scores.get("consistency", 0)
    other = [v for k, v in scores.items() if k != "consistency"]
    avg_other = sum(other) / len(other) if other else 0
    return consistency >= CONSISTENCY_THRESHOLD and avg_other >= QUALITY_THRESHOLD


def run_scene(memory: StoryMemory, scene: dict) -> str:
    revision_note = None
    final_text = None
    for attempt in range(MAX_REVISIONS_PER_SCENE + 1):
        print(f"    [писатель] попытка {attempt + 1}...")
        draft = run_writer(memory, scene, revision_note)
        print(f"    [редактор] правка стиля...")
        edited_text = run_editor(memory, draft.get("text", ""), scene)
        print(f"    [критик] проверка согласованности и качества...")
        critique = run_critic(memory, edited_text, scene)
        memory.log_critique(scene["index"], attempt, critique)
        final_text = edited_text
        last_draft = draft
        if scene_passes(critique) or attempt == MAX_REVISIONS_PER_SCENE:
            # применяем изменения в память только когда сцена принята
            # или исчерпаны попытки - берем последний вариант как есть
            memory.apply_writer_output(scene["index"], last_draft)
            print(f"    -> сцена принята со счетом {critique.get('scores')}")
            break
        else:
            revision_note = critique.get("issues", [])
            print(f"    -> сцена отправлена на доработку: {revision_note}")
    return final_text


def main():
    premise = input(
        "Тема/жанр рассказа (Enter - по умолчанию): "
    ).strip()
    if not premise:
        premise = "психологическая драма о человеке, который возвращается в дом детства"
    memory = StoryMemory()
    print("\n=== АРХИТЕКТОР строит план рассказа ===")
    plan = run_architect(memory, premise)
    print(f"Название: {plan.get('title')}")
    print(f"Кратко: {plan.get('logline')}")
    print(f"Сцен в плане: {len(plan.get('scenes', []))}\n")
    scene_texts = []
    for scene in plan.get("scenes", []):
        print(f"=== Сцена {scene['index']}: {scene.get('title', '')} ===")
        text = run_scene(memory, scene)
        scene_texts.append(text)
        print()
    story = "\n\n".join(scene_texts)
    out_dir = os.path.dirname(os.path.abspath(__file__))
    story_path = os.path.join(out_dir, "story.md")
    with open(story_path, "w", encoding="utf-8") as f:
        title = plan.get("title", "Рассказ")
        f.write(f"# {title}\n\n{story}\n")
    memory_path = os.path.join(out_dir, "memory_report.json")
    memory.save(memory_path)
    print(f"Рассказ: {story_path}")
    print(f"Отчет о памяти (онтология/таймлайн/критика): {memory_path}")


if __name__ == "__main__":
    main()
