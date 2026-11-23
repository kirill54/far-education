#!/usr/bin/env python3
"""Схемы решений, которые уже есть в тексте уроков.

Рисует геометрию по формулировкам курса, а не по фото из книг:
станция спуска (урок 7.4), страховка на снегу (9.2), кулуар (10.3),
малая группа (15.1). Брод (11.4) оставлен отдельным файлом: там подписи
уже совпали с правилом урока.

    python3 course/figures/draw_schemes.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONTB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

BG = (245, 248, 251)
INK = (28, 33, 38)
MUTED = (70, 78, 86)
GREEN = (15, 122, 74)
GREEN_BG = (232, 245, 236)
RED = (176, 42, 36)
RED_BG = (253, 236, 236)
BLUE = (20, 102, 168)
BLUE_BG = (232, 241, 248)
WHITE = (255, 255, 255)
ROCK = (186, 156, 126)
ROCK_DK = (140, 112, 86)
SNOW = (248, 250, 252)
ROPE = (32, 92, 168)
METAL = (150, 158, 166)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONTB if bold else FONT, size)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if draw.textlength(trial, font=fnt) <= width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def text(draw, xy, s, fnt, fill=INK, anchor="lt"):
    draw.text(xy, s, font=fnt, fill=fill, anchor=anchor)


def card(draw, box, tone: str):
    bg, edge = {"ok": (GREEN_BG, GREEN), "bad": (RED_BG, RED), "info": (BLUE_BG, BLUE)}[tone]
    draw.rounded_rectangle(box, 28, fill=bg, outline=edge, width=4)


def pill(draw, xy, label, tone: str):
    fnt = font(26, True)
    pad_x, h = 18, 46
    w = int(draw.textlength(label, font=fnt)) + pad_x * 2
    x, y = xy
    fill = {"ok": GREEN, "bad": RED, "info": BLUE}[tone]
    draw.rounded_rectangle((x, y, x + w, y + h), 12, fill=fill)
    text(draw, (x + w / 2, y + h / 2), label, fnt, WHITE, "mm")


def caption(draw, box, s):
    x0, y0, x1, y1 = box
    fnt = font(24)
    lines = wrap(draw, s, fnt, x1 - x0 - 36)
    total = len(lines) * 32
    y = y1 - 28 - total
    for line in lines:
        text(draw, ((x0 + x1) / 2, y), line, fnt, INK, "mt")
        y += 32


def title(draw, s):
    text(draw, (960, 58), s, font(48, True), INK, "mm")


def save(im: Image.Image, name: str, folders: list[str]) -> None:
    for folder in folders:
        path = ROOT / folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        im.save(path, "PNG")
        print(path.relative_to(ROOT))


def knot(draw, x, y):
    draw.ellipse((x - 16, y - 14, x + 16, y + 14), outline=ROPE, width=8)


def rappel():
    im = Image.new("RGB", (1920, 1080), BG)
    d = ImageDraw.Draw(im)
    title(d, "Станция спуска")
    boxes = [(48, 130, 640, 1020), (664, 130, 1256, 1020), (1280, 130, 1872, 1020)]
    tones = ("ok", "bad", "bad")
    labels = ("Через металл", "Через ленту", "Чужая петля")
    notes = (
        "Середина свободно проходит через кольцо. Метка — изолентой, узлы — на концах.",
        "Верёвка, которую тянут по ленте, оплавляет её трением.",
        "Найденную петлю для спуска не берут: снаружи она целая, внутри оплавлена.",
    )
    for box, tone, label, note in zip(boxes, tones, labels, notes):
        card(d, box, tone)
        pill(d, (box[0] + 28, box[1] + 24), label, tone)
        caption(d, box, note)

    # 1. Свободная середина в металлическом кольце, узлы далеко внизу.
    rock = [(120, 250), (560, 250), (500, 620), (160, 620)]
    d.polygon(rock, fill=ROCK)
    d.line(rock + [rock[0]], fill=ROCK_DK, width=3)
    cx, cy = 340, 360
    d.ellipse((cx - 54, cy - 54, cx + 54, cy + 54), outline=METAL, width=16)
    d.ellipse((cx - 28, cy - 28, cx + 28, cy + 28), outline=METAL, width=8)
    d.ellipse((cx - 78, cy - 8, cx - 58, cy + 12), fill=METAL)
    d.ellipse((cx + 58, cy - 8, cx + 78, cy + 12), fill=METAL)
    d.arc((cx - 36, cy - 10, cx + 36, cy + 70), 200, 340, fill=ROPE, width=14)
    d.line((cx - 34, cy + 52, cx - 70, 860), fill=ROPE, width=14)
    d.line((cx + 34, cy + 52, cx + 70, 860), fill=ROPE, width=14)
    d.rounded_rectangle((cx - 22, cy + 28, cx + 22, cy + 48), 4, fill=(92, 184, 92))
    knot(d, cx - 70, 860)
    knot(d, cx + 70, 860)

    # 2. Та же верёвка идёт через текстильную петлю.
    sx = 960
    d.polygon([(760, 250), (1160, 250), (1100, 620), (800, 620)], fill=ROCK)
    d.line((sx - 28, 300, sx - 28, 470), fill=GREEN, width=18)
    d.line((sx + 28, 300, sx + 28, 470), fill=GREEN, width=18)
    d.arc((sx - 28, 270, sx + 28, 330), 180, 360, fill=GREEN, width=18)
    d.arc((sx - 36, 430, sx + 36, 500), 0, 180, fill=GREEN, width=18)
    d.arc((sx - 30, 400, sx + 30, 470), 200, 340, fill=ROPE, width=12)
    d.line((sx - 28, 430, sx - 50, 860), fill=ROPE, width=12)
    d.line((sx + 28, 430, sx + 50, 860), fill=ROPE, width=12)
    d.ellipse((sx - 18, 448, sx + 18, 484), outline=(214, 120, 40), width=6)
    knot(d, sx - 50, 860)
    knot(d, sx + 50, 860)

    # 3. Разрез: снаружи целое, внутри спёкшиеся волокна.
    d.polygon([(1360, 280), (1800, 280), (1740, 520), (1400, 520)], fill=ROCK)
    d.line((1580, 300, 1500, 470), fill=GREEN, width=26)
    d.line((1580, 300, 1660, 470), fill=GREEN, width=26)
    d.arc((1500, 250, 1660, 360), 180, 360, fill=GREEN, width=26)
    d.rounded_rectangle((1490, 500, 1670, 860), 40, fill=GREEN)
    d.rounded_rectangle((1524, 540, 1636, 820), 24, fill=(40, 40, 42))
    for y in range(560, 800, 28):
        d.line((1540, y, 1620, y + 10), fill=(90, 90, 92), width=3)
    return im


def snow():
    im = Image.new("RGB", (1920, 1080), BG)
    d = ImageDraw.Draw(im)
    title(d, "Страховка на снегу")
    boxes = [(48, 130, 640, 1020), (664, 130, 1256, 1020), (1280, 130, 1872, 1020)]
    for box, tone, label, note in zip(
        boxes,
        ("ok", "bad", "ok"),
        ("Через ледоруб", "Стоять на ледорубе", "Т-якорь"),
        (
            "Ледоруб до головки. Верёвка под клювом. Страхующий ниже, ледоруб на уровне колена.",
            "Стоя на ледорубе или выше него, страхующий выворачивает ледоруб.",
            "Петля за середину древка. Паз по линии нагрузки. Снег перед траншеей не трогают.",
        ),
    ):
        card(d, box, tone)
        pill(d, (box[0] + 28, box[1] + 24), label, tone)
        caption(d, box, note)

    def slope(x0, x1, y_hi, y_lo):
        d.polygon([(x0, y_lo), (x1, y_hi), (x1, 900), (x0, 900)], fill=SNOW, outline=(210, 216, 222))

    def axe(x, head_y, buried=True):
        shaft_end = head_y + (150 if buried else 210)
        d.line((x, head_y, x, shaft_end), fill=(50, 54, 58), width=12)
        d.polygon([(x - 8, head_y), (x + 46, head_y - 8), (x + 8, head_y + 16)], fill=(50, 54, 58))
        d.polygon([(x, head_y + 4), (x - 42, head_y + 18), (x - 8, head_y + 28)], fill=(70, 74, 78))
        return shaft_end

    slope(90, 600, 430, 760)
    axe(250, 655, True)
    d.line((230, 648, 390, 720), fill=ROPE, width=8)
    d.ellipse((360, 700, 400, 760), outline=GREEN, width=6)
    d.line((380, 760, 380, 820), fill=GREEN, width=6)
    d.line((360, 790, 330, 850), fill=GREEN, width=6)
    d.line((400, 790, 430, 850), fill=GREEN, width=6)

    slope(700, 1220, 430, 760)
    axe(980, 430, False)
    d.ellipse((960, 360, 1000, 400), outline=RED, width=6)
    d.line((980, 400, 980, 455), fill=RED, width=6)
    d.line((955, 430, 1005, 430), fill=RED, width=6)

    d.polygon([(1340, 280), (1820, 280), (1820, 860), (1340, 860)], fill=SNOW, outline=(210, 216, 222))
    d.polygon([(1380, 470), (1760, 470), (1760, 620), (1460, 700), (1380, 620)], fill=(226, 232, 238))
    d.line((1480, 560, 1720, 560), fill=(50, 54, 58), width=12)
    d.polygon([(1480, 548), (1450, 530), (1458, 572)], fill=(50, 54, 58))
    d.ellipse((1588, 540, 1620, 580), outline=GREEN, width=8)
    d.line((1604, 580, 1680, 820), fill=GREEN, width=8)
    d.line((1620, 620, 1760, 760), fill=(186, 196, 206), width=3)
    return im


def couloir():
    im = Image.new("RGB", (1920, 1080), BG)
    d = ImageDraw.Draw(im)
    title(d, "Кулуар зимой")
    boxes = [(48, 140, 940, 1000), (980, 140, 1872, 1000)]
    for box, tone, label, note in zip(
        boxes,
        ("bad", "ok"),
        ("По дну", "По бортам"),
        (
            "Дно — ловушка: сюда собирается лавина.",
            "Идут и пересекают по борту, не по дну.",
        ),
    ):
        card(d, box, tone)
        pill(d, (box[0] + 28, box[1] + 24), label, tone)
        caption(d, box, note)

    def gully(left, top):
        d.polygon(
            [(left, top), (left + 250, top), (left + 390, top + 620), (left + 40, top + 620)],
            fill=ROCK,
        )
        d.polygon(
            [(left + 560, top), (left + 810, top), (left + 700, top + 620), (left + 430, top + 620)],
            fill=ROCK,
        )
        d.polygon(
            [(left + 230, top + 40), (left + 560, top + 40), (left + 450, top + 600), (left + 360, top + 600)],
            fill=WHITE,
        )

    gully(110, 250)
    d.line((500, 320, 500, 820), fill=RED, width=8)
    for i, y in enumerate(range(340, 820, 28)):
        if i % 2:
            continue
        d.line((500, y, 500, y + 14), fill=BG, width=8)
    for xy in ((470, 400), (520, 460), (480, 540), (530, 610)):
        d.rounded_rectangle((xy[0], xy[1], xy[0] + 28, xy[1] + 18), 4, fill=(230, 234, 238))

    gully(1040, 250)
    d.line((1160, 300, 1220, 820), fill=GREEN, width=8)
    for i, y in enumerate(range(310, 820, 28)):
        if i % 2:
            continue
        d.line((1160 + (y - 300) * 0.09, y, 1160 + (y - 300) * 0.09, y + 14), fill=BG, width=8)
    d.ellipse((1128, 360, 1172, 404), outline=GREEN, width=6)
    d.line((1150, 404, 1150, 470), fill=GREEN, width=6)
    return im


def party():
    im = Image.new("RGB", (1920, 1080), BG)
    d = ImageDraw.Draw(im)
    title(d, "Малая группа и профессиональная команда")
    boxes = [(48, 140, 940, 1000), (980, 140, 1872, 1000)]
    for box, tone, label, note in zip(
        boxes,
        ("ok", "info"),
        ("Двойка", "Команда спасателей"),
        (
            "Одна безусловная станция. Если рука отпустит тормоз, верёвка зафиксируется сама.",
            "Две независимые станции и две верёвки: грузовая и страховочная. Чужой приём сюда не переносят.",
        ),
    ):
        card(d, box, tone)
        pill(d, (box[0] + 28, box[1] + 24), label, tone)
        caption(d, box, note)

    d.polygon([(160, 430), (820, 430), (760, 860), (220, 860)], fill=ROCK)
    d.ellipse((430, 250, 470, 290), outline=METAL, width=8)
    d.ellipse((500, 250, 540, 290), outline=METAL, width=8)
    d.line((450, 290, 490, 360), fill=GREEN, width=6)
    d.line((520, 290, 490, 360), fill=GREEN, width=6)
    d.ellipse((474, 348, 506, 380), outline=METAL, width=6)
    d.line((490, 380, 490, 800), fill=ROPE, width=10)
    d.rounded_rectangle((470, 470, 530, 510), 6, fill=(60, 64, 68))
    d.arc((500, 500, 560, 560), 200, 40, fill=GREEN, width=7)
    d.line((530, 530, 560, 490), fill=GREEN, width=5)
    d.ellipse((560, 455, 600, 495), outline=BLUE, width=5)
    d.line((580, 495, 580, 560), fill=BLUE, width=5)
    d.ellipse((460, 760, 510, 810), outline=BLUE, width=5)

    d.polygon([(1100, 520), (1760, 520), (1760, 860), (1100, 860)], fill=ROCK)
    for x, label, color in ((1240, "грузовая", RED), (1580, "страховочная", BLUE)):
        d.ellipse((x - 16, 560, x + 16, 592), outline=METAL, width=8)
        d.line((x, 592, x, 780), fill=color, width=10)
        text(d, (x, 800), label, font(22, True), INK, "mt")
    d.ellipse((1224, 640, 1256, 672), outline=METAL, width=5)
    return im


def main() -> None:
    save(rappel(), "spusk-kolco.png", ["course/m07/figures", "presentations/img"])
    save(snow(), "sneg-yakorya.png", ["course/m09/figures", "presentations/img"])
    save(couloir(), "kuluar-bort.png", ["course/m10/figures", "presentations/img"])
    save(party(), "malaya-stanciya.png", ["course/m15/figures", "presentations/img"])
    src = Path("/opt/cursor/artifacts/assets/brod-izluchina-2.jpg")
    if src.is_file():
        brod = Image.open(src).convert("RGB")
        save(brod, "brod-izluchina.png", ["course/m11/figures", "presentations/img"])


if __name__ == "__main__":
    main()
