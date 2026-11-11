#!/usr/bin/env python3
"""Приводит test.json и scenarios.json модулей к общему компактному виду.

    python3 course/format_json.py            # все модули
    python3 course/format_json.py m05 m14    # только указанные
"""

import json
import sys
from pathlib import Path

COURSE = Path(__file__).resolve().parent


def J(v):
    return json.dumps(v, ensure_ascii=False)


def kv(d, keys):
    return ", ".join(f"{J(k)}: {J(d[k])}" for k in keys if k in d)


QUESTION = [["id", "section", "bank", "l"], ["q"], ["a", "b", "c"], ["correct", "explanation", "ref"], ["keys"]]


def test(d):
    out = ["{"] + [f"  {J(k)}: {J(v)}," for k, v in d.items() if k != "questions"] + ['  "questions": [']
    for i, q in enumerate(d["questions"]):
        known = {k for row in QUESTION for k in row}
        rows = [kv(q, row) for row in QUESTION] + [kv(q, [k for k in q if k not in known])]
        rows = [r for r in rows if r]
        body = ",\n     ".join(rows)
        out.append(f"    {{{body}}}" + ("," if i < len(d["questions"]) - 1 else ""))
    return out + ["  ]", "}"]


def scenarios(d):
    out = ["{", f'  "module": {J(d["module"])},', f'  "points": {J(d["points"])},', '  "scenarios": [']
    for si, s in enumerate(d["scenarios"]):
        out += ["    {"] + [f"      {J(k)}: {J(s[k])}," for k in ("id", "title", "intro", "start", "lessons")]
        out.append('      "steps": {')
        names = list(s["steps"])
        for ni, n in enumerate(names):
            st = s["steps"][n]
            out += [f"        {J(n)}: {{", f'          "scale": {J(st["scale"])},', f'          "text": {J(st["text"])},',
                    '          "options": [']
            for oi, o in enumerate(st["options"]):
                out += [f"            {{{kv(o, ['text', 'grade', 'next'])},",
                        f"             {kv(o, ['feedback'])}}}" + ("," if oi < len(st["options"]) - 1 else "")]
            out += ["          ]", "        }" + ("," if ni < len(names) - 1 else "")]
        out += ["      }", "    }" + ("," if si < len(d["scenarios"]) - 1 else "")]
    return out + ["  ]", "}"]


def main(names):
    dirs = [COURSE / n for n in names] if names else sorted(COURSE.glob("m[0-9][0-9]"))
    for folder in dirs:
        for name, fmt in (("test.json", test), ("scenarios.json", scenarios)):
            path = folder / name
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                path.write_text("\n".join(fmt(data)) + "\n", encoding="utf-8")
                assert json.loads(path.read_text(encoding="utf-8")) == data


if __name__ == "__main__":
    main(sys.argv[1:])
