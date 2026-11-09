#!/usr/bin/env python3
"""Презентация модуля 3 из рисунков пособия «Школа альпинизма».

Берёт иллюстрации со страниц 104–139 модуля (главы 6 и 7) и раскладывает
их по слайдам. Схемы не перерисовываются.

PDF ищется в таком порядке: аргумент командной строки, переменная ALP03_PDF,
затем типичные пути загрузки. В репозиторий сам файл пособия не кладётся:
картинки уже вшиты в pptx.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Emu

W, H = 1920, 1080
DPI = 210

NAVY = (11, 47, 74)
BLUE = (20, 102, 168)
GOLD = (255, 207, 63)
ICE = (233, 241, 248)
INK = (18, 22, 27)
MUTED = (74, 85, 96)
WHITE = (255, 255, 255)
SHADOW = (214, 224, 232)

REG = "/usr/share/fonts/truetype/macos/Inter-Regular.ttf"
BOLD = "/usr/share/fonts/truetype/macos/Inter-Bold.ttf"

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "ALP-03_laviny-naglyadno.pptx"
PREVIEW = Path("/tmp/alp03-slides")

# book page, clip in PDF points (origin top-left)
CROPS: dict[str, tuple[int, tuple[float, float, float, float]]] = {
    "hero": (104, (0, 0, 468, 308)),
    "forces": (105, (236, 148, 428, 292)),
    "slab": (105, (240, 302, 428, 520)),
    "zones": (106, (68, 172, 405, 422)),
    "sizes": (107, (52, 28, 418, 270)),
    "wind": (108, (38, 92, 434, 252)),
    "slabphoto": (108, (46, 250, 430, 502)),
    "cornice": (109, (36, 30, 422, 276)),
    "temp": (109, (46, 346, 420, 618)),
    "aspect": (110, (288, 468, 430, 628)),
    "angles": (111, (24, 240, 428, 434)),
    "convex": (112, (16, 252, 258, 400)),
    "bezengi": (112, (46, 398, 430, 626)),
    "anchors": (113, (46, 146, 414, 364)),
    "route": (114, (96, 398, 400, 628)),
    "time": (119, (36, 120, 432, 472)),
    "kit": (121, (40, 172, 424, 492)),
    "ch7": (122, (0, 0, 468, 294)),
    "sun": (131, (72, 230, 422, 436)),
    "lenin": (132, (46, 68, 430, 308)),
    "acclim": (134, (44, 318, 428, 622)),
    "elbrus": (135, (44, 348, 416, 624)),
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(BOLD if bold else REG, size)


def find_pdf() -> Path:
    candidates = []
    if len(sys.argv) > 1:
        candidates.append(Path(sys.argv[1]))
    if os.environ.get("ALP03_PDF"):
        candidates.append(Path(os.environ["ALP03_PDF"]))
    candidates.extend(
        [
            Path("/home/ubuntu/.cursor/projects/agent-repos-far-education/uploads/ALP_Module_03__1__35db.pdf"),
            ROOT / "ALP_Module_03.pdf",
        ]
    )
    for path in candidates:
        if path.is_file():
            return path
    raise SystemExit("Не найден PDF модуля 3. Передайте путь аргументом или ALP03_PDF.")


def crop_page(doc: pymupdf.Document, name: str) -> Image.Image:
    book, (x0, y0, x1, y1) = CROPS[name]
    page = doc[book - 94]
    pix = page.get_pixmap(dpi=DPI, clip=pymupdf.Rect(x0, y0, x1, y1), alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def trim_margin(im: Image.Image, thresh: int = 247, pad: int = 10) -> Image.Image:
    """Срезает внешние почти белые поля. Внутренние просветы не трогает."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()

    def row_blank(y: int) -> bool:
        for x in range(0, w, 4):
            r, g, b = px[x, y]
            if r < thresh or g < thresh or b < thresh:
                return False
        return True

    def col_blank(x: int) -> bool:
        for y in range(0, h, 4):
            r, g, b = px[x, y]
            if r < thresh or g < thresh or b < thresh:
                return False
        return True

    top = 0
    while top < h * 0.22 and row_blank(top):
        top += 1
    bot = h - 1
    while bot > h * 0.78 and row_blank(bot):
        bot -= 1
    left = 0
    while left < w * 0.18 and col_blank(left):
        left += 1
    right = w - 1
    while right > w * 0.82 and col_blank(right):
        right -= 1
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(w - 1, right + pad)
    bot = min(h - 1, bot + pad)
    if right - left < 40 or bot - top < 40:
        return im
    return im.crop((left, top, right + 1, bot + 1))


def fit(im: Image.Image, box_w: int, box_h: int) -> Image.Image:
    scale = min(box_w / im.width, box_h / im.height)
    size = (max(1, int(im.width * scale)), max(1, int(im.height * scale)))
    return im.resize(size, Image.Resampling.LANCZOS)


def cover(im: Image.Image, box_w: int, box_h: int, ax: float = 0.5, ay: float = 0.45) -> Image.Image:
    scale = max(box_w / im.width, box_h / im.height)
    nw, nh = int(im.width * scale), int(im.height * scale)
    resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, min(nw - box_w, int((nw - box_w) * ax)))
    top = max(0, min(nh - box_h, int((nh - box_h) * ay)))
    return resized.crop((left, top, left + box_w, top + box_h))


def draw_text(d: ImageDraw.ImageDraw, xy, text: str, size: int, bold=False, fill=INK, anchor="lt"):
    d.text(xy, text, font=font(size, bold), fill=fill, anchor=anchor)


def footer(d: ImageDraw.ImageDraw, page: int, index: int, total: int) -> None:
    d.rectangle([0, H - 58, W, H], fill=NAVY)
    d.rectangle([0, H - 62, W, H - 58], fill=GOLD)
    left = "Школа альпинизма  ·  Модуль 3"
    if page:
        left += f"  ·  пособие, с. {page}"
    left += "  ·  не аттестация"
    draw_text(d, (48, H - 30), left, 20, fill=WHITE, anchor="lm")
    draw_text(d, (W - 48, H - 30), f"{index}  /  {total}", 20, fill=GOLD, anchor="rm")


def figure_slide(title: str, im: Image.Image, caption: str, note: str, page: int, index: int, total: int) -> Image.Image:
    canvas = Image.new("RGB", (W, H), ICE)
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, 0, W, 8], fill=GOLD)
    draw_text(d, (64, 36), "МОДУЛЬ 3", 18, bold=True, fill=BLUE, anchor="lt")
    draw_text(d, (64, 78), title, 44, bold=True, fill=NAVY, anchor="lt")

    top = 148
    if note:
        draw_text(d, (64, 136), note, 22, fill=MUTED, anchor="lt")
        top = 176
    bottom = 980 if caption else 1000
    pad = 22
    max_w, max_h = W - 160 - pad * 2, bottom - top - pad * 2
    fitted = fit(im, max_w, max_h)
    card_w, card_h = fitted.width + pad * 2, fitted.height + pad * 2
    cx = (W - card_w) // 2
    cy = top + (bottom - top - card_h) // 2
    d.rounded_rectangle([cx + 5, cy + 8, cx + card_w + 5, cy + card_h + 8], radius=16, fill=SHADOW)
    d.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=16, fill=WHITE)
    canvas.paste(fitted, (cx + pad, cy + pad))
    if caption:
        draw_text(d, (W // 2, 1002), caption, 20, fill=MUTED, anchor="mm")
    footer(d, page, index, total)
    return canvas


def title_slide(hero: Image.Image) -> Image.Image:
    panel = 620
    canvas = Image.new("RGB", (W, H), NAVY)
    photo = cover(hero, W - panel, H, ax=0.0, ay=0.62)
    canvas.paste(photo, (panel, 0))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, 0, panel, H], fill=NAVY)
    d.rectangle([0, 0, 10, H], fill=GOLD)
    draw_text(d, (56, 88), "ШКОЛА АЛЬПИНИЗМА", 20, bold=True, fill=GOLD)
    draw_text(d, (56, 168), "Модуль 3", 28, fill=(186, 214, 232))
    draw_text(d, (56, 230), "Лавины", 78, bold=True, fill=WHITE)
    draw_text(d, (56, 330), "и влияние высокогорной", 36, fill=WHITE)
    draw_text(d, (56, 378), "среды", 36, fill=WHITE)
    d.rectangle([56, 460, 180, 466], fill=GOLD)
    draw_text(d, (56, 500), "Главы 6 и 7 пособия", 24, fill=(214, 226, 234))
    draw_text(d, (56, 538), "Страницы 104–139", 24, fill=(214, 226, 234))
    draw_text(d, (56, 640), "Восхождение на вершину Когутай,", 22, fill=(186, 206, 218))
    draw_text(d, (56, 672), "Кавказ, апрель", 22, fill=(186, 206, 218))
    draw_text(d, (56, H - 92), "Рисунки взяты со страниц книги.", 20, fill=(170, 196, 214))
    draw_text(d, (56, H - 58), "Это не аттестация и не допуск.", 20, fill=GOLD)
    return canvas


def section_slide(photo: Image.Image, kicker: str, caption: str, index: int, total: int) -> Image.Image:
    bar = 78
    frame = Image.new("RGB", (W, H), NAVY)
    fitted = fit(photo, W, H - bar)
    frame.paste(fitted, ((W - fitted.width) // 2, (H - bar - fitted.height) // 2))
    d = ImageDraw.Draw(frame)
    d.rectangle([0, H - bar, W, H], fill=NAVY)
    d.rectangle([0, H - bar - 4, W, H - bar], fill=GOLD)
    draw_text(d, (48, H - bar // 2), kicker, 22, bold=True, fill=GOLD, anchor="lm")
    draw_text(d, (W // 2, H - bar // 2), caption, 22, fill=WHITE, anchor="mm")
    draw_text(d, (W - 48, H - bar // 2), f"{index}  /  {total}", 20, fill=GOLD, anchor="rm")
    return frame


def close_slide(index: int, total: int) -> Image.Image:
    canvas = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, 0, W, 8], fill=GOLD)
    draw_text(d, (72, 56), "МОДУЛЬ 3", 18, bold=True, fill=GOLD)
    draw_text(d, (72, 100), "Что эти слайды не заменяют", 46, bold=True, fill=WHITE)

    cards = [
        ("Откуда рисунки", "Со страниц 104–139\nпособия «Школа\nальпинизма». Схемы\nне перерисованы."),
        ("Проверка", "Шесть вопросов модуля\nи ответы к ним остаются\nв файле пособия."),
        ("Только очно", "Поиск в лавине, зонд,\nоткапывание, первая\nпомощь, приёмы на снегу\nи на льду."),
    ]
    gap = 28
    card_w = (W - 144 - gap * 2) // 3
    y = 230
    h = 430
    for i, (head, body) in enumerate(cards):
        x = 72 + i * (card_w + gap)
        d.rounded_rectangle([x, y, x + card_w, y + h], radius=18, fill=(16, 62, 96))
        d.rectangle([x, y, x + 8, y + h], fill=GOLD)
        draw_text(d, (x + 36, y + 36), head, 28, bold=True, fill=WHITE)
        line_y = y + 110
        for line in body.split("\n"):
            draw_text(d, (x + 36, line_y), line, 26, fill=(214, 226, 234))
            line_y += 40
    draw_text(
        d,
        (72, H - 150),
        "Слайды не допуск, не квалификация и не официальный экзамен ФАР.",
        26,
        fill=GOLD,
    )
    draw_text(d, (W - 72, H - 48), f"{index}  /  {total}", 20, fill=WHITE, anchor="rm")
    return canvas


def build_images(doc: pymupdf.Document) -> list[Image.Image]:
    raw = {name: crop_page(doc, name) for name in CROPS}
    trim_names = {
        "forces",
        "slab",
        "zones",
        "sizes",
        "wind",
        "temp",
        "aspect",
        "angles",
        "convex",
        "anchors",
        "route",
        "time",
        "kit",
        "acclim",
        "elbrus",
    }
    pics = {name: trim_margin(im) if name in trim_names else im for name, im in raw.items()}

    specs: list[tuple] = [
        ("title",),
        ("figure", "Силы, которые держат снег на склоне", "forces", 105, "", ""),
        ("figure", "«Доска» срывается по слабому слою", "slab", 105, "", ""),
        ("figure", "Два типа отрыва", "zones", 106, "", ""),
        ("figure", "Пять размеров лавины", "sizes", 107, "", ""),
        ("figure", "Ветер перекладывает снег", "wind", 108, "", ""),
        ("figure", "Сошедшая «доска»", "slabphoto", 108, "", ""),
        ("figure", "Карниз", "cornice", 109, "", ""),
        ("figure", "Пять температурных сценариев", "temp", 109, "", ""),
        ("figure", "С каких склонов сходит больше лавин", "aspect", 110, "", ""),
        ("figure", "На каком угле сходит лавина", "angles", 111, "", ""),
        ("figure", "Выпуклый перелом держит напряжение", "convex", 112, "", ""),
        ("figure", "Лавина в Безенги", "bezengi", 112, "", ""),
        ("figure", "Что на склоне работает как якорь", "anchors", 113, "", ""),
        ("figure", "Опасную зону проходят по одному", "route", 114, "", ""),
        (
            "figure",
            "Первые минуты решают",
            "time",
            119,
            "",
            "Рисунок про время. Искать, зондировать и откапывать здесь не учат — это очно.",
        ),
        (
            "figure",
            "Три предмета на каждого",
            "kit",
            121,
            "",
            "Комплект из пособия. Пользоваться им учатся на практике.",
        ),
        ("section",),
        ("figure", "Солнце на снегу", "sun", 131, "", ""),
        ("figure", "Пик Ленина, 7134 м", "lenin", 132, "", ""),
        ("figure", "Акклиматизация идёт пилой", "acclim", 134, "", ""),
        ("figure", "Набор высоты на Эльбрус", "elbrus", 135, "", ""),
        ("close",),
    ]
    total = len(specs)
    slides: list[Image.Image] = []
    for i, spec in enumerate(specs, start=1):
        kind = spec[0]
        if kind == "title":
            slides.append(title_slide(pics["hero"]))
        elif kind == "section":
            slides.append(
                section_slide(
                    pics["ch7"],
                    "Глава 7",
                    "«Райские ночевки», ущелье Адыр-су, Кавказ  ·  с. 122",
                    i,
                    total,
                )
            )
        elif kind == "close":
            slides.append(close_slide(i, total))
        else:
            _, title, key, page, caption, note = spec
            slides.append(figure_slide(title, pics[key], caption, note, page, i, total))
    return slides


def write_pptx(slides: list[Image.Image], dest: Path) -> None:
    prs = Presentation()
    prs.slide_width = Emu(12192000)  # 13.333 in
    prs.slide_height = Emu(6858000)  # 7.5 in
    blank = prs.slide_layouts[6]
    tmp = PREVIEW
    tmp.mkdir(parents=True, exist_ok=True)
    for i, slide in enumerate(slides, start=1):
        path = tmp / f"{i:02d}.png"
        slide.save(path, optimize=True)
        s = prs.slides.add_slide(blank)
        s.shapes.add_picture(str(path), 0, 0, width=prs.slide_width, height=prs.slide_height)
    dest.parent.mkdir(parents=True, exist_ok=True)
    prs.save(dest)


def main() -> None:
    pdf = find_pdf()
    doc = pymupdf.open(pdf)
    slides = build_images(doc)
    write_pptx(slides, OUT)
    print(f"{len(slides)} slides -> {OUT}")


if __name__ == "__main__":
    main()
