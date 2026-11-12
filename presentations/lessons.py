#!/usr/bin/env python3
"""Уроки курса в логическом порядке, а не по главам пособия.

Уроки модуля NN описаны в units/mNN.py, каждый урок — отдельная презентация в lessons/.
Проверка (--check) сверяет текст слайдов и озвучки урока с тремя списками в course/mNN/:

- terms.json — термины модуля: каждый должен звучать в своём уроке;
- bank.json — вопросы банка аттестации ФАР: ключевые факты правильного ответа должны
  быть в уроке, за которым закреплён вопрос; все 255 вопросов закреплены ровно один раз;
- test.json — вопросы теста модуля: то же по полям "l" (урок) и "keys".

Ключ — начало слова или фраза; варианты через «|», совпадение ищется с начала слова.

    python3 presentations/lessons.py               # собрать все уроки и проверить
    python3 presentations/lessons.py 2.1 10.2      # собрать выбранные
    python3 presentations/lessons.py --check       # только проверить
    python3 presentations/lessons.py --check -v    # с перечнем того, что ещё не собрано
    LESSON_UNITS=m05,m14 python3 presentations/lessons.py --check   # только эти модули
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys

from deck import ROOT, build
from lesson_kit import OUT, Lesson

COURSE = ROOT.parent / "course"
BANK = ROOT.parent / "trenazher" / "questions.js"
UNITS = [u.strip() for u in os.environ.get("LESSON_UNITS", "").split(",") if u.strip()]


def selected(paths):
    return [p for p in sorted(paths) if not UNITS or (p.stem if p.suffix == ".py" else p.parent.name) in UNITS]


def load_lessons() -> list[Lesson]:
    lessons = []
    for path in selected((ROOT / "units").glob("m[0-9][0-9].py")):
        lessons += importlib.import_module(f"units.{path.stem}").LESSONS
    key = lambda lesson: tuple(int(p) for p in lesson.code.split("."))  # noqa: E731
    codes = [lesson.code for lesson in lessons]
    dupes = {c for c in codes if codes.count(c) > 1}
    if dupes:
        raise SystemExit(f"Повтор номера урока: {sorted(dupes)}")
    return sorted(lessons, key=key)


LESSONS = load_lessons()


def norm(s: str) -> str:
    return s.lower().replace("ё", "е")


def term_stems(term: dict) -> list[str]:
    if term.get("k"):
        return [norm(k) for k in term["k"]]
    words = re.findall(r"[а-яёa-z]{4,}", norm(term["t"]))
    return [words[0][: max(4, len(words[0]) - 2)]] if words else [norm(term["t"])]


def lesson_text(lesson: Lesson) -> str:
    parts = []
    for s in lesson.slides:
        parts += [s.title, s.caption, s.warning, s.narration, *s.items]
        for key in ("subtitle", "callout"):
            parts.append(str(s.extra.get(key, "")))
        for key in ("topics", "flags"):
            parts += s.extra.get(key, [])
        for pair in s.extra.get("terms", []) + s.extra.get("cards", []) + s.extra.get("events", []):
            parts += pair
        for _, _, items in s.extra.get("columns", []):
            parts += items
    return norm(" ".join(parts))


def found(key: str, body: str) -> bool:
    return any(re.search(r"(?<![а-яa-z0-9])" + re.escape(norm(alt.strip())), body) for alt in key.split("|"))


def ref_slides(ref: str) -> tuple[str, list[int]] | None:
    """«урок 10.3, слайд 7», «урок 2.1, слайды 5, 7», «урок 3.2, слайды 6–8» → ('10.3', [7])."""
    m = re.match(r"урок (\d+\.\d+), слайды? ([\d,–\- ]+)", ref)
    if not m:
        return None
    nums: list[int] = []
    for part in re.split(r",\s*", m[2].strip(" ,")):
        a, _, b = part.replace("–", "-").partition("-")
        nums += list(range(int(a), int(b or a) + 1))
    return m[1], nums


def ref_problem(q: dict, by_code: dict) -> str:
    """Ссылка «Где смотреть» должна вести на слайд, где есть хотя бы один ключ вопроса."""
    parsed = ref_slides(q.get("ref", ""))
    if not parsed:
        return f"ссылка не по образцу «урок X.Y, слайд N»: {q.get('ref', '')!r}"
    code, nums = parsed
    lesson = by_code.get(code)
    if lesson is None:
        return ""
    if any(n < 1 or n > len(lesson.slides) for n in nums):
        return f"ссылка {q['ref']!r}: в уроке {code} всего {len(lesson.slides)} слайдов"
    body = " ".join(lesson_text(Lesson(code, "", {}, [lesson.slides[n - 1]])) for n in nums)
    if not any(found(k, body) for k in q.get("keys", [])):
        return f"ссылка {q['ref']!r}: на этих слайдах нет ни одного ключа вопроса"
    return ""


def bank_ids() -> set[int]:
    raw = BANK.read_text(encoding="utf-8")
    raw = raw[raw.index("["): raw.rindex("]") + 1]
    return {q["id"] for q in json.loads(raw) if q.get("track") == "alpine"}


def check(verbose: bool = False) -> int:
    texts = {lesson.code: lesson_text(lesson) for lesson in LESSONS}
    problems: list[str] = []
    pending: list[str] = []
    stats = {}

    def verify(kind: str, label: str, code: str, keys: list[str], any_key: bool = False) -> None:
        stats.setdefault(kind, [0, 0, 0])[1] += 1
        if not code or not keys:
            problems.append(f"{kind}: {label} — нет урока или ключей")
            return
        body = texts.get(code)
        if body is None:
            stats[kind][2] += 1
            pending.append(f"{kind}: {label} → урок {code} ещё не собран")
            return
        miss = [k for k in keys if not found(k, body)]
        if any_key and len(miss) < len(keys):
            miss = []
        if miss:
            problems.append(f"{kind}: {label} → урок {code}, не найдено: {', '.join(miss)}")
        else:
            stats[kind][0] += 1

    for path in selected(COURSE.glob("m[0-9][0-9]/terms.json")):
        for t in json.loads(path.read_text(encoding="utf-8"))["terms"]:
            verify("термины", t["t"], t.get("l", ""), term_stems(t), any_key=True)

    mapped: dict[int, str] = {}
    for path in selected(COURSE.glob("m[0-9][0-9]/bank.json")):
        for qid, item in json.loads(path.read_text(encoding="utf-8"))["questions"].items():
            if int(qid) in mapped:
                problems.append(f"банк: вопрос № {qid} закреплён дважды ({mapped[int(qid)]} и {path.parent.name})")
            mapped[int(qid)] = path.parent.name
            verify("банк ФАР", f"№ {qid}", item.get("l", ""), item.get("k", []))
    missing = [] if UNITS else sorted(bank_ids() - set(mapped))
    if missing:
        problems.append(f"банк: не закреплены {len(missing)} вопросов: {missing[:40]}{' …' if len(missing) > 40 else ''}")

    by_code = {lesson.code: lesson for lesson in LESSONS}
    for path in selected(COURSE.glob("m[0-9][0-9]/test.json")):
        for q in json.loads(path.read_text(encoding="utf-8"))["questions"]:
            verify("тесты", q["id"], q.get("l", ""), q.get("keys", []))
            problem = ref_problem(q, by_code)
            if problem:
                problems.append(f"тесты: {q['id']} — {problem}")

    for kind, (ok, total, wait) in stats.items():
        print(f"{kind}: {total}, найдено в уроках {ok}, ждут уроков {wait}, ошибок {total - ok - wait}")
    if missing:
        print(f"банк ФАР: не закреплено за уроками {len(missing)} из {len(bank_ids())}")
    for line in problems:
        print("  ✗", line)
    if verbose:
        for line in pending:
            print("  …", line)
    return 1 if problems else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("codes", nargs="*", help="номера уроков, например 2.1 10.3")
    parser.add_argument("--check", action="store_true", help="только проверить")
    parser.add_argument("-v", "--verbose", action="store_true", help="показать, что ждёт несобранных уроков")
    args = parser.parse_args()
    if not args.check:
        OUT.mkdir(exist_ok=True)
        for lesson in LESSONS:
            if not args.codes or lesson.code in args.codes:
                build(lesson.deck())
    sys.exit(check(args.verbose))


if __name__ == "__main__":
    main()
