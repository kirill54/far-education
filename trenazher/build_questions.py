# -*- coding: utf-8 -*-
"""Выгружает банки вопросов ФАР в questions.js для тренажёра."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ATT = Path(r"C:\Users\Пользователь\ФАР\_context\ФАР_лендинг_передача\programs\attestation")
sys.path.insert(0, str(ATT))

from alpine_exam_content import ALPINE_THEORY_COUNT, ALPINE_THEORY_SECTIONS  # noqa: E402
from parse_far_ski_exam import parse_theory  # noqa: E402


def _append(out: list, items_by_section, track: str, source: str, start: int) -> int:
    n = start
    for title, items in items_by_section:
        for item in items:
            n += 1
            out.append(
                {
                    "id": n,
                    "section": title,
                    "track": track,
                    "source": source,
                    "q": item["q"],
                    "a": item["a"],
                    "b": item["b"],
                    "c": item["c"],
                    "correct": item["correct"],
                }
            )
    return n


def main() -> None:
    out: list[dict] = []
    n = _append(
        out,
        ALPINE_THEORY_SECTIONS,
        "alpine",
        "alpine-2026-02-08",
        0,
    )
    n = _append(
        out,
        parse_theory(),
        "ski",
        "ski-2025-04-02",
        n,
    )
    dest = HERE / "questions.js"
    payload = json.dumps(out, ensure_ascii=False, indent=2)
    dest.write_text(
        "// Банки: Билеты_для_тестирования_альпинизм_горный_туризм_08_02_2026.docx; "
        "Вопросы20250402_теоретический_экзамен_правильные.docx\n"
        f"window.FAR_QUESTIONS = {payload};\n",
        encoding="utf-8",
    )
    counts = {"alpine": 0, "ski": 0}
    for q in out:
        counts[q["track"]] += 1
    print(
        f"wrote {dest.name}: {len(out)} q  "
        f"alpine={counts['alpine']} ski={counts['ski']} "
        f"(alpine source {ALPINE_THEORY_COUNT})"
    )


if __name__ == "__main__":
    main()
