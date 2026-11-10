#!/usr/bin/env python3
"""Проверяет тесты и сценарии симулятора модуля и собирает из них markdown.

    python3 course/render_course.py            # все папки course/mNN
    python3 course/render_course.py m01 m02    # только указанные

Источник правды — JSON: test.json и scenarios.json. Markdown рядом с ними
пересобирается этим скриптом, руками его не правят.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

COURSE = Path(__file__).resolve().parent
LETTERS = ("a", "b", "c")
RU = {"a": "а", "b": "б", "c": "в"}
GRADES = {"best": "Лучшее", "ok": "Допустимое", "error": "Ошибка", "critical": "Критическая ошибка"}
SCALES = {"безопасность", "решения", "работа с группой"}


def check_test(data: dict) -> list[str]:
    errors = []
    questions = data["questions"]
    if not 30 <= len(questions) <= 45:
        errors.append(f"вопросов {len(questions)}, нужно 30–45")
    if len(questions) < data["draw"] or data["pass"] > data["draw"]:
        errors.append("выборка больше банка или порог больше выборки")
    ids = Counter(q["id"] for q in questions)
    errors += [f"повтор id {i}" for i, n in ids.items() if n > 1]
    for q in questions:
        for key in ("q", *LETTERS, "correct", "explanation", "ref", "section"):
            if not q.get(key):
                errors.append(f"{q['id']}: пусто поле {key}")
        if q.get("correct") not in LETTERS:
            errors.append(f"{q['id']}: correct должен быть a, b или c")
        if len({q[k] for k in LETTERS}) < 3:
            errors.append(f"{q['id']}: одинаковые варианты")
    for section, n in Counter(q["section"] for q in questions).items():
        if n < 3:
            errors.append(f"в разделе «{section}» меньше трёх вопросов")
    return errors


def render_test(data: dict) -> str:
    questions = data["questions"]
    share = Counter(q["correct"] for q in questions)
    out = [
        f"# Тест модуля {data['module']}. {data['title']}",
        "",
        f"Банк — {len(questions)} вопросов. В попытке — {data['draw']} случайных, "
        f"зачёт — от {data['pass']} правильных. Один верный ответ из трёх.",
        "",
        "Правильные ответы по буквам: " + ", ".join(f"{RU[k]} — {share[k]}" for k in LETTERS) + ".",
        "Вопросы с номером из банка аттестации ФАР помечены «банк №».",
        "",
    ]
    section = None
    for q in questions:
        if q["section"] != section:
            section = q["section"]
            out += [f"## {section}", ""]
        bank = f" *(банк № {q['bank']})*" if q.get("bank") else ""
        out.append(f"**{q['id']}.** {q['q']}{bank}")
        out.append("")
        for k in LETTERS:
            mark = " ✓" if k == q["correct"] else ""
            out.append(f"- {RU[k]}) {q[k]}{mark}")
        out += ["", f"> {q['explanation']} *Где смотреть: {q['ref']}.*", ""]
    return "\n".join(out)


def paths(steps: dict, start: str) -> list[list[str]]:
    """All step sequences from start to an ending (an option without next)."""
    result = []

    def walk(step: str, trail: list[str]) -> None:
        trail = trail + [step]
        for option in steps[step]["options"]:
            nxt = option.get("next")
            if nxt is None:
                result.append(trail)
            elif nxt not in trail:
                walk(nxt, trail)

    walk(start, [])
    return result


def check_scenario(s: dict) -> list[str]:
    errors = []
    steps = s["steps"]
    if s["start"] not in steps:
        errors.append(f"{s['id']}: нет стартового шага {s['start']}")
        return errors
    for name, step in steps.items():
        if step.get("scale") not in SCALES:
            errors.append(f"{s['id']}/{name}: шкала должна быть одной из {sorted(SCALES)}")
        if not 2 <= len(step["options"]) <= 4:
            errors.append(f"{s['id']}/{name}: вариантов должно быть 2–4")
        if not any(o["grade"] == "best" for o in step["options"]):
            errors.append(f"{s['id']}/{name}: нет лучшего варианта")
        for o in step["options"]:
            if o["grade"] not in GRADES:
                errors.append(f"{s['id']}/{name}: неизвестная оценка {o['grade']}")
            if o["grade"] == "critical" and o.get("next"):
                errors.append(f"{s['id']}/{name}: критическая ошибка должна завершать сценарий")
            if o.get("next") and o["next"] not in steps:
                errors.append(f"{s['id']}/{name}: переход на несуществующий шаг {o['next']}")
    reachable = {step for trail in paths(steps, s["start"]) for step in trail}
    errors += [f"{s['id']}: шаг {n} недостижим" for n in steps if n not in reachable]

    best = [s["start"]]
    while True:
        nxt = next(o.get("next") for o in steps[best[-1]]["options"] if o["grade"] == "best")
        if nxt is None:
            break
        best.append(nxt)
    if not 4 <= len(best) <= 6:
        errors.append(f"{s['id']}: на лучшем пути {len(best)} решений, нужно 4–6")
    return errors


def render_scenarios(data: dict) -> str:
    pts = data["points"]
    out = [
        f"# Симулятор модуля {data['module']}",
        "",
        f"Баллы: лучшее +{pts['best']}, допустимое +{pts['ok']}, ошибка {pts['error']}. "
        "Критическая ошибка завершает сценарий разбором. "
        "Баллы шага идут в его шкалу: безопасность, решения или работа с группой.",
        "",
    ]
    for s in data["scenarios"]:
        steps = s["steps"]
        order = list(dict.fromkeys(step for trail in paths(steps, s["start"]) for step in trail))
        number = {name: i for i, name in enumerate(order, 1)}
        out += [f"## «{s['title']}»", "", f"**Вводные.** {s['intro']}", ""]
        for name in order:
            step = steps[name]
            out += [f"### Шаг {number[name]} · {step['scale']}", "", step["text"], ""]
            for letter, o in zip("АБВГ", step["options"]):
                if o.get("next"):
                    where = f"→ шаг {number[o['next']]}"
                elif o["grade"] == "critical":
                    where = "→ разбор, сценарий окончен"
                else:
                    where = "→ итог"
                out.append(f"- **{letter}.** {o['text']}")
                out.append(f"  — *{GRADES[o['grade']]}.* {o['feedback']} {where}")
            out.append("")
        out += ["**Повторить:** " + "; ".join(s["lessons"]) + ".", ""]
    return "\n".join(out)


def main(names: list[str]) -> int:
    dirs = [COURSE / n for n in names] if names else sorted(COURSE.glob("m[0-9][0-9]"))
    failed = False
    for d in dirs:
        test = json.loads((d / "test.json").read_text(encoding="utf-8"))
        scen = json.loads((d / "scenarios.json").read_text(encoding="utf-8"))
        errors = check_test(test) + [e for s in scen["scenarios"] for e in check_scenario(s)]
        if errors:
            failed = True
            print(f"{d.name}: ошибки")
            for e in errors:
                print("  -", e)
            continue
        (d / "test.md").write_text(render_test(test) + "\n", encoding="utf-8")
        (d / "scenarios.md").write_text(render_scenarios(scen) + "\n", encoding="utf-8")
        letters = Counter(q["correct"] for q in test["questions"])
        print(f"{d.name}: {len(test['questions'])} вопросов {dict(letters)}, "
              f"{len(scen['scenarios'])} сценария — ок")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
