#!/usr/bin/env python3
"""Собирает черновик курса в одну HTML-страницу.

Рисунок берётся из текста урока, из строки ![подпись](путь), и встаёт в том же разделе.
Запуск из корня репозитория: python3 review/build.py
"""

from __future__ import annotations

import base64
import hashlib
import html
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "presentations"))

from deck import image_file  # noqa: E402
from lessons import LESSONS  # noqa: E402

OUT = Path(__file__).resolve().parent

MODULES = {
    1: "Профессия и система подготовки",
    2: "Горная среда и её опасности",
    3: "Погода в горах",
    4: "Ориентирование и навигация",
    5: "Человек в горах",
    6: "Снаряжение, бивак и экология",
    7: "Верёвка, узлы, основы страховки",
    8: "Скальный рельеф",
    9: "Снег, лёд и закрытый ледник",
    10: "Лавины",
    11: "Простой и комбинированный рельеф, переправы, короткая верёвка",
    12: "Группа и лидерство",
    13: "Планирование маршрута и управление риском",
    14: "Первая помощь в горах",
    15: "Аварийная ситуация",
    16: "Итоговый экзамен",
}

# Схемы, которые лежат в course/mNN/figures и не названы на слайде.
EXTRA = {
    "8.2": [
        ("petlya", "Петля на выступе", ROOT / "course/m08/figures/petlya.png"),
        ("ottyazhka", "Оттяжка между точкой и верёвкой", ROOT / "course/m08/figures/ottyazhka.png"),
        ("oppoziciya", "Оппозиция закладок", ROOT / "course/m08/figures/oppoziciya.png"),
        ("frend", "Френд в щели", ROOT / "course/m08/figures/frend.png"),
    ],
    "9.1": [
        ("sneg-i-led", "Снег, где ещё рубят ступени, и лёд", ROOT / "course/m09/figures/sneg-i-led.png"),
    ],
}

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "j", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}


def slug(text: str) -> str:
    out = []
    for ch in text.lower().replace("ё", "е"):
        if ch in TRANSLIT:
            out.append(TRANSLIT[ch])
        elif ch.isascii() and ch.isalnum():
            out.append(ch)
        else:
            out.append("-")
    value = re.sub(r"-{2,}", "-", "".join(out)).strip("-")
    return value[:60] or "razdel"


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def inline(text: str) -> str:
    safe = esc(text)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    return safe


def reading_path(code: str, lesson_slug: str) -> Path:
    major = int(code.split(".")[0])
    return ROOT / "course" / f"m{major:02d}" / "reading" / f"{code}-{lesson_slug}.md"


def lesson_title(markdown: str, lesson) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    cover = next((s for s in lesson.slides if s.kind == "cover"), None)
    if cover and cover.title:
        return cover.title.replace("\n", " ")
    return lesson.slug


IMG_LINE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)$")


def parse_sections(markdown: str, base: Path) -> list[tuple[str, list[tuple]]]:
    """Возвращает (заголовок, блоки). Блок — абзац или рисунок из текста урока."""
    sections: list[tuple[str, list[tuple]]] = [("", [])]
    buf: list[str] = []

    def flush_para():
        text = " ".join(part.strip() for part in buf).strip()
        buf.clear()
        if text:
            sections[-1][1].append(("p", text))

    for line in markdown.splitlines():
        image = IMG_LINE.match(line.strip())
        if line.startswith("# "):
            flush_para()
            continue
        if line.startswith("## "):
            flush_para()
            sections.append((line[3:].strip(), []))
            continue
        if image:
            flush_para()
            alt, rel = image.group(1), image.group(2)
            path = (base / rel).resolve()
            if not path.is_file():
                raise SystemExit(f"Нет рисунка {path} из {base}")
            sections[-1][1].append(("img", alt, path))
            continue
        if not line.strip():
            flush_para()
            continue
        buf.append(line)
    flush_para()
    return [(title, blocks) for title, blocks in sections if blocks or title]


def section_figures(sections: list[tuple[str, list[tuple]]]) -> list[tuple[str, str, Path]]:
    found = []
    for heading, blocks in sections:
        for block in blocks:
            if block[0] == "img":
                found.append((heading, block[1], block[2]))
    return found


def figures_for(lesson) -> list[tuple[str, str, Path]]:
    found: list[tuple[str, str, Path]] = []
    seen: set[Path] = set()
    for slide in lesson.slides:
        if not slide.image or slide.kind == "cover":
            continue
        src = slide.origin or lesson.deck()
        path = image_file(src, slide.image)
        if path is None or path in seen:
            continue
        seen.add(path)
        title = slide.title.replace("\n", " ") or slide.image
        found.append((slug(slide.image), title, path))
    for key, title, path in EXTRA.get(lesson.code, []):
        if path.is_file() and path not in seen:
            seen.add(path)
            found.append((key, title, path))
    return found


_IMAGE_SRC: dict[Path, str] = {}


def image_src(path: Path) -> str:
    """Картинка внутри страницы: отдельный файл img/ в просмотре не подгружается."""
    path = path.resolve()
    cached = _IMAGE_SRC.get(path)
    if cached is not None:
        return cached
    mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    cached = f"data:{mime};base64,{encoded}"
    _IMAGE_SRC[path] = cached
    return cached


def css() -> str:
    return """
:root {
  --ink: #1c1915;
  --muted: #5c564c;
  --line: #e4dfd6;
  --paper: #f7f5f1;
  --card: #fffcf8;
  --navy: #0b2f4a;
  --blue: #0e5c8a;
  --gold: #8a6a12;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  color: var(--ink);
  background: var(--paper);
  font-family: "Iowan Old Style", Palatino, "Palatino Linotype", Georgia, serif;
  font-size: 20px;
  line-height: 1.65;
}
a { color: var(--blue); }
.layout { display: grid; grid-template-columns: 280px 1fr; min-height: 100vh; }
nav {
  position: sticky;
  top: 0;
  align-self: start;
  height: 100vh;
  overflow: auto;
  background: var(--navy);
  color: #e7eef4;
  padding: 22px 16px 40px;
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size: 14px;
  line-height: 1.35;
}
nav a { color: inherit; text-decoration: none; }
nav .brand { display: block; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; font-size: 12px; margin-bottom: 6px; }
nav .brand-sub { display: block; color: #b7c9d8; margin-bottom: 18px; }
nav .mod { margin: 16px 0 6px; color: #ffcf3f; font-size: 12px; font-weight: 700; }
nav ol { list-style: none; margin: 0; padding: 0; }
nav li a { display: block; padding: 5px 8px; border-radius: 6px; }
nav li a:hover { background: rgba(255,255,255,.08); }
nav li a.current { background: #fffcf8; color: var(--navy); }
nav .toc-fig { color: #b7c9d8; font-size: 12px; }
main { padding: 36px 48px 80px; max-width: 920px; }
.kicker {
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--blue);
  margin: 0 0 10px;
}
h1 { font-size: 40px; line-height: 1.15; font-weight: 700; letter-spacing: -.02em; margin: 0 0 12px; }
.lead {
  font-family: "Helvetica Neue", Arial, sans-serif;
  color: var(--muted);
  font-size: 16px;
  margin: 0 0 28px;
}
h2 { font-size: 28px; line-height: 1.25; margin: 2.2em 0 .6em; }
p { margin: 0 0 1em; }
article, .home-mod, #risunki { scroll-margin-top: 24px; }
article { padding-top: 12px; border-top: 1px solid var(--line); margin-top: 48px; }
article section { scroll-margin-top: 24px; }
figure {
  margin: 28px 0;
  padding: 12px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
}
figure img { display: block; width: 100%; height: auto; border-radius: 6px; }
figcaption {
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size: 15px;
  line-height: 1.4;
  margin-top: 10px;
  color: var(--ink);
}
figcaption .tag {
  display: block;
  color: var(--gold);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .05em;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.pager {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 48px;
  padding-top: 20px;
  border-top: 1px solid var(--line);
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size: 15px;
}
.pager a { text-decoration: none; }
.cards { display: grid; gap: 10px; }
.card {
  display: block;
  padding: 14px 16px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 10px;
  text-decoration: none;
  color: inherit;
}
.card strong { font-family: "Helvetica Neue", Arial, sans-serif; }
.card span { display: block; color: var(--muted); font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px; margin-top: 4px; }
.home-mod { margin-top: 36px; }
.home-mod h2 { margin-top: 0; font-size: 24px; }
@media (max-width: 860px) {
  .layout { grid-template-columns: 1fr; }
  nav { position: relative; height: auto; max-height: 40vh; }
  main { padding: 24px 18px 64px; }
  h1 { font-size: 32px; }
}
"""


def lesson_anchor(code: str) -> str:
    return "urok-" + code.replace(".", "-")


def nav(current: str | None, lessons_meta: list[dict]) -> str:
    parts = [
        '<a class="brand" href="#nachalo">Школа альпинизма</a>',
        '<span class="brand-sub">Черновик для замечаний</span>',
        '<a class="toc-fig" href="#risunki">Рисунки по урокам</a>',
    ]
    last_mod = None
    items = []
    for item in lessons_meta:
        if item["module"] != last_mod:
            if items:
                parts.append("<ol>" + "".join(items) + "</ol>")
                items = []
            last_mod = item["module"]
            parts.append(f'<div class="mod">Модуль {item["module"]}</div>')
        cls = ' class="current"' if item["code"] == current else ""
        items.append(
            f'<li><a{cls} href="#{lesson_anchor(item["code"])}">{esc(item["code"])} {esc(item["title"])}</a></li>'
        )
    if items:
        parts.append("<ol>" + "".join(items) + "</ol>")
    return "<nav>" + "".join(parts) + "</nav>"


def page(title: str, body: str, current: str | None, lessons_meta: list[dict]) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>{css()}</style>
</head>
<body>
<div class="layout">
{nav(current, lessons_meta)}
<main>
{body}
</main>
</div>
</body>
</html>
"""


def figure_html(item: dict, anchor: str, heading: str, caption: str, path: Path) -> str:
    src = image_src(path)
    fig_id = f"fig-{anchor}-{slug(path.stem)}"
    where = f"Урок {item['code']} · {heading}" if heading else f"Урок {item['code']}"
    return (
        f'<figure id="{fig_id}" data-review="figure" data-lesson="{esc(item["code"])}">'
        f'<img src="{esc(src)}" alt="{esc(caption)}">'
        f'<figcaption><span class="tag">{esc(where)}</span>{esc(caption)}</figcaption>'
        f"</figure>"
    )


def render_lesson(item: dict, prev_item: dict | None, next_item: dict | None) -> str:
    anchor = lesson_anchor(item["code"])
    sections_html = []
    used = set()
    for heading, blocks in item["sections"]:
        if not heading and not blocks:
            continue
        sid = slug(heading) if heading else "nachalo"
        base = sid
        n = 2
        while sid in used:
            sid = f"{base}-{n}"
            n += 1
        used.add(sid)
        section_id = f"{anchor}-{sid}"
        parts = []
        if heading:
            parts.append(f'<h2>{inline(heading)}</h2>')
        for block in blocks:
            if block[0] == "p":
                parts.append(f"<p>{inline(block[1])}</p>")
            else:
                parts.append(figure_html(item, anchor, heading, block[1], block[2]))
        sections_html.append(
            f'<section id="{section_id}" data-review="section" data-lesson="{esc(item["code"])}">'
            + "".join(parts)
            + "</section>"
        )
    pager = ['<div class="pager">']
    if prev_item:
        pager.append(
            f'<a href="#{lesson_anchor(prev_item["code"])}">← {esc(prev_item["code"])} {esc(prev_item["title"])}</a>'
        )
    else:
        pager.append("<span></span>")
    if next_item:
        pager.append(
            f'<a href="#{lesson_anchor(next_item["code"])}">{esc(next_item["code"])} {esc(next_item["title"])} →</a>'
        )
    else:
        pager.append("<span></span>")
    pager.append("</div>")
    fig_note = (
        f' Рисунков в уроке: {len(item["figures"])}. Каждый стоит в своём разделе.'
        if item["figures"] else ""
    )
    return (
        f'<article id="{anchor}" data-review="chapter" data-lesson="{esc(item["code"])}">'
        f'<p class="kicker">Модуль {item["module"]} · {esc(item["module_title"])}</p>'
        f"<h1>{esc(item['code'])}. {esc(item['title'])}</h1>"
        f'<p class="lead">Черновик для замечаний к тексту и к рисункам. Курс не опубликован и не даёт допуска.{esc(fig_note)}</p>'
        + "".join(sections_html)
        + "".join(pager)
        + "</article>"
    )


def render_index(lessons_meta: list[dict]) -> str:
    chunks = [
        '<div id="nachalo">',
        '<p class="kicker">ФАР · теория для инструкторов-проводников</p>',
        "<h1>Школа альпинизма</h1>",
        '<p class="lead">53 главы на одной странице. Рисунок стоит внутри своего урока, в том разделе, который он поясняет. Курс не опубликован.</p>',
        '<p><a href="#risunki">Рисунки по урокам</a></p>',
    ]
    last = None
    for item in lessons_meta:
        if item["module"] != last:
            if last is not None:
                chunks.append("</div></div>")
            last = item["module"]
            chunks.append(
                f'<div class="home-mod" id="modul-{item["module"]}" data-review="module">'
                f'<h2>Модуль {item["module"]}. {esc(item["module_title"])}</h2><div class="cards">'
            )
        fig = f'<span>Рисунков: {len(item["figures"])}</span>' if item["figures"] else ""
        chunks.append(
            f'<a class="card" href="#{lesson_anchor(item["code"])}"><strong>{esc(item["code"])}. {esc(item["title"])}</strong>'
            f"{fig}</a>"
        )
    chunks.append("</div></div></div>")
    for i, item in enumerate(lessons_meta):
        prev_item = lessons_meta[i - 1] if i else None
        next_item = lessons_meta[i + 1] if i + 1 < len(lessons_meta) else None
        chunks.append(render_lesson(item, prev_item, next_item))
    chunks.append('<section id="risunki"><h1>Рисунки по урокам</h1>')
    chunks.append('<p class="lead">Список только переходит к схеме. Сама схема стоит в разделе своего урока.</p>')
    any_fig = False
    for item in lessons_meta:
        if not item["figures"]:
            continue
        any_fig = True
        anchor = lesson_anchor(item["code"])
        chunks.append(
            f'<h2><a href="#{anchor}">{esc(item["code"])}. {esc(item["title"])}</a></h2><ul>'
        )
        for heading, caption, path in item["figures"]:
            fig_id = f"fig-{anchor}-{slug(path.stem)}"
            chunks.append(
                f'<li><a href="#{fig_id}">{esc(caption)}</a> — раздел «{esc(heading)}»</li>'
            )
        chunks.append("</ul>")
    if not any_fig:
        chunks.append("<p>Файлов рисунков не найдено.</p>")
    chunks.append("</section>")
    chunks.append(
        "<script>const links=[...document.querySelectorAll('nav a[href^=\"#urok-\"]')];"
        "function mark(){const hash=location.hash||'';let best='';"
        "for(const a of links){const href=a.getAttribute('href');"
        "if(hash===href||hash.startsWith(href+'-')){if(href.length>best.length)best=href;}}"
        "for(const a of links)a.classList.toggle('current',a.getAttribute('href')===best);}"
        "addEventListener('hashchange',mark);mark();</script>"
    )
    return page("Школа альпинизма — черновик", "".join(chunks), None, lessons_meta)


def main() -> None:
    lessons_meta = []
    for lesson in LESSONS:
        path = reading_path(lesson.code, lesson.slug)
        if not path.is_file():
            raise SystemExit(f"Нет главы: {path}")
        markdown = path.read_text(encoding="utf-8")
        module = int(lesson.code.split(".")[0])
        sections = parse_sections(markdown, path.parent)
        lessons_meta.append({
            "code": lesson.code,
            "slug": lesson.slug,
            "file": f"{lesson.code}.html",
            "module": module,
            "module_title": MODULES[module],
            "title": lesson_title(markdown, lesson),
            "sections": sections,
            "figures": section_figures(sections),
        })
        placed = {hashlib.sha256(figure[2].read_bytes()).digest() for figure in section_figures(sections)}
        for _key, title, figure_path in figures_for(lesson):
            digest = hashlib.sha256(figure_path.read_bytes()).digest()
            if digest not in placed:
                raise SystemExit(f"Рисунок «{title}» не встроен в урок {lesson.code}")
    img_dir = OUT / "img"
    if img_dir.exists():
        shutil.rmtree(img_dir)
    for old in OUT.glob("*.html"):
        old.unlink()
    (OUT / "index.html").write_text(render_index(lessons_meta), encoding="utf-8")
    fig_count = sum(len(item["figures"]) for item in lessons_meta)
    print(f"уроков {len(lessons_meta)}, рисунков {fig_count}, файл review/index.html")
    for item in lessons_meta:
        if item["figures"]:
            names = ", ".join(title for _, title, _ in item["figures"])
            print(f'  {item["code"]}: {names}')


if __name__ == "__main__":
    main()
