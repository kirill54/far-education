#!/usr/bin/env python3
"""Наглядные схемы модуля 3 по темам пособия, с. 104–139.

Рисунки не сканы страниц: исходный PDF с фотографиями книги в рабочей
копии отсутствует. Схемы повторяют учебные различения модуля.
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
SCALE = 2
OUT_DIR = "/workspace/presentations/assets"

NAVY = (11, 47, 74)
BLUE = (20, 102, 168)
BLUE_DEEP = (14, 78, 128)
INK = (18, 22, 27)
MUTED = (74, 85, 96)
SKY = (214, 230, 242)
SNOW = (247, 250, 252)
SNOW_2 = (226, 234, 240)
SNOW_3 = (196, 214, 226)
ROCK = (122, 132, 140)
ROCK_DARK = (74, 84, 92)
AMBER = (176, 112, 42)
RED = (163, 45, 45)
WHITE = (255, 255, 255)
BG = (244, 247, 250)
CARD = (255, 255, 255)
LINE = (210, 220, 228)

REG = "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"
BOLD = "/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(BOLD if bold else REG, size * SCALE)


class Board:
    def __init__(self) -> None:
        self.im = Image.new("RGB", (W * SCALE, H * SCALE), BG)
        self.d = ImageDraw.Draw(self.im)

    def s(self, n: float) -> int:
        return int(n * SCALE)

    def box(self, x, y, w, h, fill, radius=0, outline=None, width=1):
        xy = [self.s(x), self.s(y), self.s(x + w), self.s(y + h)]
        if radius:
            self.d.rounded_rectangle(xy, radius=self.s(radius), fill=fill, outline=outline, width=self.s(width) if outline else 1)
        else:
            self.d.rectangle(xy, fill=fill, outline=outline, width=self.s(width) if outline else 1)

    def poly(self, pts, fill, outline=None, width=2):
        self.d.polygon([(self.s(x), self.s(y)) for x, y in pts], fill=fill, outline=outline)
        if outline:
            self.d.line([(self.s(x), self.s(y)) for x, y in pts] + [(self.s(pts[0][0]), self.s(pts[0][1]))], fill=outline, width=self.s(width))

    def line(self, pts, fill, width=3):
        self.d.line([(self.s(x), self.s(y)) for x, y in pts], fill=fill, width=self.s(width), joint="curve")

    def ellipse(self, x, y, w, h, fill, outline=None, width=2):
        self.d.ellipse([self.s(x), self.s(y), self.s(x + w), self.s(y + h)], fill=fill, outline=outline, width=self.s(width) if outline else 1)

    def wrap(self, s: str, size: int, bold: bool, width: float) -> list[str]:
        face = _font(size, bold)
        lines: list[str] = []
        for paragraph in str(s).split("\n"):
            cur = ""
            for word in paragraph.split():
                trial = word if not cur else f"{cur} {word}"
                if face.getlength(trial) <= width * SCALE:
                    cur = trial
                else:
                    if cur:
                        lines.append(cur)
                    cur = word
            lines.append(cur)
        return lines or [""]

    def text(self, x, y, s, size, fill=INK, bold=False, anchor="lt", width=None):
        raw = str(s)
        if width:
            raw = "\n".join(self.wrap(raw, size, bold, width))
        lines = raw.split("\n")
        line_h = size * 1.28
        if anchor in ("mm", "mt") and len(lines) > 1:
            y = y - line_h * (len(lines) - 1) / 2
        for i, line in enumerate(lines):
            use = "lt" if i and anchor in ("mm", "mt", "lm") else anchor
            self.d.text((self.s(x), self.s(y + i * line_h)), line, font=_font(size, bold), fill=fill, anchor=use)

    def header(self, kicker: str, title: str):
        self.box(0, 0, W, 8, NAVY)
        self.text(72, 36, kicker.upper(), 16, BLUE, bold=True)
        self.text(72, 64, title, 40, NAVY, bold=True)

    def footer(self, n: int, total: int):
        self.text(72, 1032, "Школа альпинизма   ·   Модуль 3   ·   схемы к пособию, с. 104–139   ·   не аттестация", 16, MUTED)
        self.text(1848, 1032, f"{n}  /  {total}", 16, MUTED, anchor="rt")

    def person(self, x, y, scale=1.0, color=NAVY, pack=False):
        """x, y — точка опоры ног."""
        s = scale
        self.ellipse(x - 8 * s, y - 52 * s, 16 * s, 16 * s, color)
        self.box(x - 9 * s, y - 36 * s, 18 * s, 20 * s, color, radius=4 * s)
        self.line([(x - 4 * s, y - 16 * s), (x - 10 * s, y)], color, width=max(3, int(4 * s)))
        self.line([(x + 4 * s, y - 16 * s), (x + 10 * s, y)], color, width=max(3, int(4 * s)))
        if pack:
            self.box(x - 4 * s, y - 34 * s, 14 * s, 12 * s, BLUE, radius=2)

    def save(self, path: str) -> None:
        out = self.im.resize((W, H), Image.Resampling.LANCZOS)
        out.save(path, "PNG")


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def slope_band(ridge_l, ridge_r, base_l, base_r, t0, t1):
    return [
        lerp(ridge_l, base_l, t0),
        lerp(ridge_r, base_r, t0),
        lerp(ridge_r, base_r, t1),
        lerp(ridge_l, base_l, t1),
    ]


def draw_slope(b: Board, ox, oy, ow, oh, zones=True, people=True, tracks=False, debris=False, cornice=False, loaded=False):
    """Профиль склона: верх — зарождение, середина — транзит, низ — отложение."""
    b.box(ox, oy, ow, oh, SKY)
    top = (ox + ow * 0.10, oy + oh * 0.16)
    z1 = (ox + ow * 0.36, oy + oh * 0.36)
    z2 = (ox + ow * 0.64, oy + oh * 0.60)
    toe = (ox + ow * 0.90, oy + oh * 0.76)
    floor_r = (ox + ow * 0.96, oy + oh * 0.92)
    floor_l = (ox + ow * 0.04, oy + oh * 0.92)
    b.poly([top, z1, z2, toe, floor_r, floor_l], (168, 180, 190))
    seams = [top, z1, z2, toe]
    colors = [(248, 251, 253), (186, 214, 230), (140, 178, 204)]
    depth = oh * (0.11 if loaded else 0.055)
    if zones:
        for i in range(3):
            a, c = seams[i], seams[i + 1]
            b.poly([a, c, (c[0], c[1] + depth), (a[0], a[1] + depth)], colors[i], outline=BLUE, width=2)
    else:
        b.poly([top, toe, (toe[0], toe[1] + depth), (top[0], top[1] + depth)], SNOW, outline=BLUE, width=2)
    b.line([lerp(top, z1, 0.2), z2], NAVY, width=5)
    b.poly([z2, (z2[0] - ow * 0.03, z2[1] - oh * 0.012), (z2[0] - ow * 0.012, z2[1] - oh * 0.03)], NAVY)
    if cornice:
        b.poly([
            (top[0] - ow * 0.02, top[1] + oh * 0.01),
            (top[0] + ow * 0.07, top[1] - oh * 0.03),
            (top[0] + ow * 0.11, top[1] + oh * 0.05),
            (top[0] + ow * 0.04, top[1] + oh * 0.07),
            (top[0] - ow * 0.01, top[1] + oh * 0.04),
        ], WHITE, outline=NAVY, width=3)
    if people:
        mid = lerp(z1, z2, 0.42)
        for dx, pack in ((-34, False), (0, True), (34, False)):
            b.person(mid[0] + dx, mid[1] - 2, 1.2, pack=pack)
    if tracks:
        for i in range(9):
            p = lerp(top, toe, 0.12 + i * 0.08)
            b.ellipse(p[0] - 6, p[1] - 16, 14, 8, NAVY)
    if debris:
        for i in range(7):
            p = lerp(z2, toe, 0.25 + i * 0.1)
            b.ellipse(p[0], p[1] + 6, 34, 14, WHITE, outline=BLUE, width=2)
    if zones:
        b.text(lerp(top, z1, 0.4)[0], top[1] - 8, "1  зарождение", 18, NAVY, bold=True, anchor="lb")
        transit = lerp(z1, z2, 0.15)
        b.text(transit[0] + (90 if people else 0), transit[1] - (70 if people else 28), "2  транзит", 18, NAVY, bold=True, anchor="lb")
        dep = lerp(z2, toe, 0.72)
        b.text(dep[0], dep[1] - 28, "3  отложение", 18, NAVY, bold=True, anchor="lb")
    return top, z1, z2, toe


def pill(b: Board, x, y, w, h, label, fill=WHITE, fg=NAVY):
    b.box(x, y, w, h, fill, radius=12)
    b.text(x + w / 2, y + h / 2, label, 20, fg, bold=True, anchor="mm")


# --- slides ---

def s01(b: Board):
    b.box(0, 0, W, H, NAVY)
    b.box(0, 0, 16, H, BLUE)
    draw_slope(b, 980, 80, 860, 920, people=True, debris=True)
    b.text(80, 180, "ШКОЛА АЛЬПИНИЗМА", 18, (158, 201, 236), bold=True)
    b.text(80, 230, "Модуль 3", 28, WHITE, bold=True)
    b.text(80, 290, "Лавины и влияние\nвысокогорной среды", 58, WHITE, bold=True)
    b.text(80, 520, "Наглядные схемы к пособию.\nСтраницы 104–139.", 28, (213, 228, 240))
    b.text(80, 680, "Это не допуск к поиску, первой помощи\nи не аттестация инструктора-проводника.", 22, (158, 201, 236))


def s02(b: Board):
    b.header("Как читать", "Четыре темы. На каждой — одна схема.")
    items = [
        ("1", "Где пройдёт лавина", "Три зоны и слои снега"),
        ("2", "Что меняет склон", "Ветер, карниз, признаки"),
        ("3", "Чего слайд не даёт", "Поиск только очно"),
        ("4", "Что делает с человеком", "Холод, солнце, высота"),
    ]
    for i, (n, title, sub) in enumerate(items):
        x = 72 + i * 460
        b.box(x, 230, 430, 640, WHITE, radius=18)
        b.box(x, 230, 430, 12, BLUE, radius=0)
        b.ellipse(x + 36, 270, 64, 64, NAVY)
        b.text(x + 68, 302, n, 28, WHITE, bold=True, anchor="mm")
        b.text(x + 36, 370, title, 28, NAVY, bold=True)
        b.text(x + 36, 470, sub, 22, MUTED)
    b.footer(2, TOTAL)


def s03(b: Board):
    b.header("Урок 1  ·  с. 104–109", "Сначала зоны. Потом решение, идти ли.")
    draw_slope(b, 72, 200, 1180, 780, people=True, debris=True)
    labels = [
        ("1", "Зарождение", "Где снег может прийти в движение"),
        ("2", "Транзит", "Где лавина набирает путь"),
        ("3", "Отложение", "Где масса останавливается"),
    ]
    for i, (n, name, desc) in enumerate(labels):
        y = 230 + i * 200
        b.box(1300, y, 540, 170, WHITE, radius=16)
        b.ellipse(1324, y + 48, 64, 64, NAVY if i == 0 else BLUE)
        b.text(1356, y + 80, n, 26, WHITE, bold=True, anchor="mm")
        b.text(1410, y + 40, name, 26, NAVY, bold=True)
        b.text(1410, y + 88, desc, 20, MUTED)
    b.footer(3, TOTAL)


def s04(b: Board):
    b.header("Урок 1", "Снег лежит слоями. «Доска» сходит целиком.")
    # разрез покрова
    b.box(72, 210, 1100, 760, SKY, radius=16)
    b.text(120, 240, "Разрез покрова", 22, MUTED, bold=True)
    layers = [
        ((236, 242, 246), "Свежий снег", 90),
        ((196, 214, 224), "Ветровая доска", 110),
        (AMBER, "Слабый слой", 36),
        ((168, 186, 198), "Старый снег", 150),
        (ROCK, "Грунт", 70),
    ]
    y = 300
    for color, name, h in layers:
        b.box(160, y, 820, h, color)
        fg = (90, 50, 10) if name == "Слабый слой" else NAVY
        if name == "Грунт":
            fg = WHITE
        b.text(180, y + h / 2, name, 24, fg, bold=True, anchor="lm")
        y += h
    b.line([(1000, 400), (1000, 510), (1080, 470)], RED, width=6)
    b.text(160, 820, "Доска сходит по слабому слою одним куском.", 24, NAVY, bold=True, width=860)
    # правая карточка — что из этого следует
    b.box(1220, 210, 628, 760, WHITE, radius=16)
    b.text(1260, 260, "Не название типа", 32, NAVY, bold=True)
    points = [
        "Слои копились в разные дни.",
        "Доска опасна тем, что в движение приходит сразу большой объём.",
        "Вопрос урока: где путь и где встанет группа.",
    ]
    for i, p in enumerate(points):
        yy = 400 + i * 150
        b.ellipse(1260, yy, 18, 18, BLUE)
        b.text(1300, yy - 8, p, 24, INK, width=480)
    b.footer(4, TOTAL)


def s05(b: Board):
    b.header("Урок 1", "Это видно. Это ещё не разрешение идти.")
    panels = [
        ("Сводка по району", "Оценка района не отвечает\nза этот склон и этот час."),
        ("Нет старых следов", "Пустой склон не доказывает,\nчто схода не будет."),
        ("Чужой след", "Кто-то прошёл — это факт\nпрохода, не проверка снега."),
        ("«Я здесь ходил»", "Прошлый раз не заменяет\nсегодняшний снег и ветер."),
    ]
    for i, (title, body) in enumerate(panels):
        c, r = i % 2, i // 2
        x, y = 72 + c * 920, 200 + r * 390
        b.box(x, y, 880, 360, WHITE, radius=16)
        b.box(x, y, 12, 360, RED if i else BLUE)
        # мини-знак
        b.box(x + 40, y + 36, 200, 140, SKY, radius=12)
        if i == 0:
            b.box(x + 70, y + 70, 140, 80, WHITE, radius=6)
            b.ellipse(x + 150, y + 86, 28, 28, RED)
        elif i == 1:
            b.poly([(x + 60, y + 160), (x + 140, y + 60), (x + 220, y + 160)], SNOW, outline=BLUE, width=2)
        elif i == 2:
            for k in range(5):
                b.ellipse(x + 70 + k * 30, y + 100, 16, 10, BLUE)
        else:
            b.person(x + 140, y + 160, 1.3)
        b.text(x + 270, y + 50, title, 30, NAVY, bold=True)
        b.text(x + 270, y + 140, body, 24, INK)
        b.text(x + 270, y + 270, "Не гарантия склона", 20, RED, bold=True)
    b.footer(5, TOTAL)


def s06(b: Board):
    b.header("Урок 2  ·  с. 107–118", "Ветер переносит снег на подветренную сторону.")
    b.box(72, 200, 1776, 780, SKY, radius=16)
    # наветренный пологий
    b.poly([(120, 860), (980, 420), (980, 900), (120, 900)], (214, 226, 234))
    # подветренный круче
    b.poly([(980, 420), (1700, 860), (1700, 900), (980, 900)], (168, 198, 216))
    # гребень
    b.poly([(900, 400), (1080, 390), (1040, 450), (920, 460)], ROCK_DARK)
    # карниз
    b.poly([(1000, 400), (1160, 390), (1200, 470), (1100, 500), (1020, 450)], WHITE, outline=BLUE, width=3)
    # стрелки ветра
    for yy in (300, 360, 430):
        b.line([(180, yy), (760, yy - 20)], NAVY, width=6)
        b.poly([(760, yy - 20), (720, yy - 40), (720, yy)], NAVY)
    # снежная пыль
    for k in range(6):
        b.ellipse(640 + k * 28, 300 + (k % 3) * 18, 18, 8, WHITE)
    b.text(200, 240, "Наветренный", 26, NAVY, bold=True)
    b.text(1280, 240, "Подветренный", 26, NAVY, bold=True)
    b.text(1080, 520, "Карниз", 24, BLUE, bold=True)
    b.text(1320, 640, "Здесь копится\nперенесённый снег", 24, NAVY, bold=True)
    b.footer(6, TOTAL)


def s07(b: Board):
    b.header("Урок 2", "Смотреть на склон, а не на «район вообще».")
    b.box(72, 200, 1100, 780, WHITE, radius=16)
    draw_slope(b, 100, 240, 1040, 700, people=True, loaded=True)
    notes = [
        (1220, 220, "Свежий снег", "Новый слой ещё не часть старого покрова."),
        (1220, 420, "Ход температуры", "Важна смена, не одна цифра утром."),
        (1220, 620, "Форма и сторона", "Крутизна, экспозиция, местные карманы снега."),
        (1220, 820, "Последствия", "Редкий сход важен, если под ним люди."),
    ]
    # last one may collide with footer — use 3 and a caption
    notes = notes[:3]
    for x, y, title, body in notes:
        b.box(x, y, 628, 170, WHITE, radius=14)
        b.box(x, y, 10, 170, BLUE)
        b.text(x + 36, y + 28, title, 26, NAVY, bold=True)
        b.text(x + 36, y + 80, body, 22, INK)
    b.text(1220, 900, "Схему углов смотрите в пособии, с. 111, не на этом слайде.", 20, MUTED, width=620)
    b.footer(7, TOTAL)


def s08(b: Board):
    b.header("Урок 2", "Красный флаг — повод пересмотреть план.")
    # левая панель
    b.box(72, 210, 860, 760, WHITE, radius=16)
    b.box(72, 210, 860, 14, RED)
    draw_slope(b, 100, 280, 800, 420, people=False, debris=True)
    b.text(110, 240, "Признаки есть", 28, NAVY, bold=True)
    b.text(110, 740, "План пересматривают.\nЭто не ответ «ещё можно успеть».", 24, INK)
    # правая
    b.box(980, 210, 868, 760, WHITE, radius=16)
    b.box(980, 210, 868, 14, NAVY)
    draw_slope(b, 1010, 280, 800, 420, people=False, debris=False, tracks=False)
    b.text(1020, 240, "Признаков не видно", 28, NAVY, bold=True)
    b.text(1020, 740, "Пустой список флагов\nне делает склон безопасным.", 24, INK)
    b.footer(8, TOTAL)


def s09(b: Board):
    b.header("Урок 2", "Та же линия после ветра — уже другой склон.")
    b.box(72, 210, 860, 760, WHITE, radius=16)
    b.text(100, 240, "Вчера", 28, MUTED, bold=True)
    draw_slope(b, 110, 320, 780, 500, people=True, tracks=True, cornice=False)
    b.text(100, 860, "Знакомый след и память о маршруте.", 22, MUTED)
    b.box(980, 210, 868, 760, WHITE, radius=16)
    b.box(980, 210, 868, 14, RED)
    b.text(1010, 240, "После снегопада и ветра", 28, NAVY, bold=True)
    draw_slope(b, 1020, 320, 780, 500, people=True, loaded=True, debris=False)
    b.text(1010, 860, "Нужна новая оценка и точка отказа.", 22, INK)
    b.footer(9, TOTAL)


def s10(b: Board):
    b.header("Урок 3  ·  с. 119–121", "Экран показывает рамку. Навык поиска он не даёт.")
    b.box(72, 210, 1776, 760, WHITE, radius=16)
    cols = [
        ("Понять здесь", BLUE, ["Время до спасателей важно.", "Без навыка на этот рельеф не выходят.", "Тест проверяет понимание, не допуск."]),
        ("Только очно", RED, ["Поиск датчиком.", "Зондирование и откапывание.", "Организация помощи на месте."]),
    ]
    for i, (title, color, lines) in enumerate(cols):
        x = 120 + i * 860
        b.box(x, 270, 760, 70, color, radius=10)
        b.text(x + 380, 305, title, 28, WHITE, bold=True, anchor="mm")
        for k, line in enumerate(lines):
            y = 400 + k * 120
            b.ellipse(x + 10, y, 22, 22, color)
            b.text(x + 52, y - 8, line, 28, INK)
    b.footer(10, TOTAL)


def s11(b: Board):
    b.header("Урок 3", "Вопрос задают до выхода, не на конусе выноса.")
    checks = [
        ("Комплект есть?", "Датчик, щуп и лопата на группу,\nа не «должны быть в рюкзаке»."),
        ("Эти люди умеют?", "Не «когда-то слышали».\nУмение проверяется действием."),
        ("Если ответа нет", "Это довод не выходить\nна лавинный рельеф."),
    ]
    for i, (title, body) in enumerate(checks):
        x = 72 + i * 610
        b.box(x, 230, 580, 700, WHITE, radius=18)
        b.ellipse(x + 230, 290, 120, 120, NAVY if i < 2 else RED)
        b.text(x + 290, 350, str(i + 1), 42, WHITE, bold=True, anchor="mm")
        b.text(x + 40, 460, title, 32, NAVY, bold=True)
        b.text(x + 40, 560, body, 24, INK)
    b.footer(11, TOTAL)


def s12(b: Board):
    b.header("Урок 4  ·  с. 122–139", "Горы уменьшают запас человека.")
    b.box(72, 210, 1776, 760, WHITE, radius=16)
    # человек в центре
    b.text(960, 280, "Запас человека", 22, MUTED, anchor="mt")
    b.box(360, 330, 1200, 36, SNOW_2, radius=8)
    b.box(360, 330, 520, 36, BLUE, radius=8)
    b.text(960, 390, "часть запаса уже съедена средой", 20, MUTED, anchor="mt")
    factors = [
        (160, "Холод", "Ветер и мороз забирают силы"),
        (590, "Солнце", "Ожог и перегрев на снегу"),
        (1020, "Вода и еда", "Без них решение хуже"),
        (1450, "Высота", "Форма это не отменяет"),
    ]
    for x, name, note in factors:
        b.box(x, 470, 360, 400, BG, radius=16)
        cx, cy = x + 180, 560
        b.ellipse(cx - 50, cy - 50, 100, 100, NAVY)
        if name == "Холод":
            for ang in range(0, 360, 45):
                import math
                rad = math.radians(ang)
                b.line([(cx + 16 * math.cos(rad), cy + 16 * math.sin(rad)),
                        (cx + 30 * math.cos(rad), cy + 30 * math.sin(rad))], WHITE, width=3)
        elif name == "Солнце":
            b.ellipse(cx - 14, cy - 14, 28, 28, (255, 196, 64))
        elif name == "Вода и еда":
            b.ellipse(cx - 12, cy - 4, 24, 28, (120, 190, 230))
        else:
            b.poly([(cx, cy - 22), (cx + 26, cy + 16), (cx - 26, cy + 16)], WHITE)
        b.text(x + 180, 650, name, 26, NAVY, bold=True, anchor="mt")
        b.text(x + 30, 710, note, 22, INK, width=300)
    b.footer(12, TOTAL)


def s13(b: Board):
    b.header("Урок 4", "Форма и акклиматизация — не одно и то же.")
    b.box(72, 220, 860, 740, WHITE, radius=16)
    b.text(110, 260, "Одинаковая высота", 28, NAVY, bold=True)
    b.line([(160, 620), (760, 620)], LINE, width=4)
    b.person(300, 620, 2.2, pack=True)
    b.person(620, 620, 2.2)
    # второй сидит — упрощённо ниже и другой позой: согнутый
    b.text(160, 700, "Оба тренированы. Реакция может разойтись.", 24, INK)
    b.box(980, 220, 868, 740, WHITE, radius=16)
    b.box(980, 220, 868, 14, RED)
    b.text(1020, 270, "Чем не заменяют план", 28, NAVY, bold=True)
    for i, line in enumerate([
        "Уверенностью «я сильный».",
        "Тем, что сосед идёт нормально.",
        "Решением терпеть до вершины.",
    ]):
        y = 400 + i * 120
        b.ellipse(1040, y, 22, 22, RED)
        b.text(1080, y - 8, line, 28, INK)
    b.footer(13, TOTAL)


def s14(b: Board):
    b.header("Урок 4", "Жалоба меняет план всей группы.")
    steps = [
        ("1", "Сказали", "Плохой сон и жалоба —\nуже информация."),
        ("2", "Остановились", "Состояние смотрят сейчас,\nне «после вершины»."),
        ("3", "Пересмотрели", "Маршрут меняют. При нужде\nвызывают помощь."),
    ]
    for i, (n, title, body) in enumerate(steps):
        x = 72 + i * 610
        b.box(x, 230, 580, 700, WHITE, radius=18)
        b.box(x, 230, 580, 120, NAVY if i < 2 else RED)
        b.text(x + 40, 268, n, 36, WHITE, bold=True)
        b.text(x + 110, 275, title, 32, WHITE, bold=True)
        b.text(x + 40, 420, body, 28, INK)
    b.footer(14, TOTAL)


def s15(b: Board):
    b.header("Ситуация из модуля", "Знакомый склон на следующее утро.")
    draw_slope(b, 72, 200, 1100, 780, people=True, loaded=True)
    b.box(1220, 220, 628, 720, WHITE, radius=16)
    b.text(1260, 270, "Условие", 18, BLUE, bold=True)
    b.text(1260, 320, "Ночью были снег и ветер.\nГруппа хочет пересечь склон\nпо известной линии.", 26, INK)
    b.text(1260, 520, "И ещё", 18, RED, bold=True)
    b.text(1260, 570, "Один участник плохо спал\nи жалуется на самочувствие.", 26, INK)
    b.text(1260, 760, "Дальше — шесть вопросов.\nБукву выбирают до ключа.", 22, MUTED)
    b.footer(15, TOTAL)


def question(b: Board, n, prompt, options, sketch):
    b.header(f"Проверка  ·  вопрос {n} из 6", prompt)
    b.box(72, 210, 760, 760, SKY, radius=16)
    sketch(b)
    for i, (letter, text) in enumerate(options):
        y = 220 + i * 200
        b.box(880, y, 968, 170, WHITE, radius=16)
        b.ellipse(910, y + 50, 70, 70, NAVY)
        b.text(945, y + 85, letter, 28, WHITE, bold=True, anchor="mm")
        b.text(1010, y + 85, text, 26, INK, anchor="lm")
    b.footer(15 + n, TOTAL)


def sk1(b):
    draw_slope(b, 100, 250, 700, 680, people=True)


def sk2(b):
    draw_slope(b, 100, 250, 700, 680, people=False, tracks=True)


def sk3(b):
    b.box(230, 360, 440, 280, WHITE, radius=20)
    b.box(400, 300, 16, 220, RED)
    b.poly([(360, 300), (456, 300), (408, 250)], RED)


def sk4(b):
    b.text(180, 460, "Поиск\nсо слайда\nне засчитывается", 36, NAVY, bold=True)


def sk5(b):
    b.person(420, 700, 3.2)
    b.ellipse(560, 430, 28, 28, RED)


def sk6(b):
    b.person(280, 720, 2.6, pack=True)
    b.person(560, 720, 2.6)


QUESTIONS = [
    (1, "Что определяет лавинный риск?",
     [("А", "Только крутизна и снег"),
      ("Б", "Снег, погода, рельеф и люди"),
      ("В", "Только бюллетень по району")], sk1),
    (2, "След предыдущей группы означает…",
     [("А", "Склон уже проверен"),
      ("Б", "Мало данных для гарантии"),
      ("В", "Линию можно не менять")], sk2),
    (3, "Как понимать красные флаги?",
     [("А", "Повод пересмотреть план"),
      ("Б", "Нет флага — склон устойчив"),
      ("В", "Повод идти быстрее")], sk3),
    (4, "Онлайн-тест подтверждает навык поиска?",
     [("А", "Да, если названы этапы"),
      ("Б", "Нет, нужна очная проверка"),
      ("В", "Да, если балл выше порога")], sk4),
    (5, "Ухудшение самочувствия на высоте",
     [("А", "Терпеть до вершины"),
      ("Б", "Оценить состояние и сменить план"),
      ("В", "Скрыть это от группы")], sk5),
    (6, "Почему форма не заменяет акклиматизацию?",
     [("А", "Реакция на высоту личная"),
      ("Б", "Тренировка её заменяет"),
      ("В", "План нужен только новичкам")], sk6),
]


def s_key(b: Board):
    b.box(0, 0, W, H, NAVY)
    b.text(72, 40, "КЛЮЧ ПРЕПОДАВАТЕЛЯ  ·  НЕ ПОКАЗЫВАТЬ ДО ОТВЕТОВ", 18, (231, 200, 196), bold=True)
    b.text(72, 90, "Верные формулировки из ключа модуля", 36, WHITE, bold=True)
    rows = [
        "1 Б    Снег, погода, рельеф и воздействие на людей.",
        "2 Б    След группы — не гарантия устойчивости.",
        "3 А    Красный флаг — повод пересмотреть план.",
        "4 Б    Навык поиска подтверждается только очно.",
        "5 Б    Оценить состояние и пересмотреть план, при нужде запросить помощь.",
        "6 А    Личная реакция на высоту может отличаться.",
    ]
    for i, row in enumerate(rows):
        b.text(72, 200 + i * 110, row, 28, WHITE)
    b.text(72, 980, "Ошибка в вопросах 2–5 не закрывается общим счётом. Это правило курса, не балл экзамена ФАР.", 20, (213, 228, 240))


def s_end(b: Board):
    b.header("После схем", "Дальше открывают само пособие.")
    cards = [
        ("Страницы 104–139", "Определения, таблицы и фотографии остаются в книге. Слайд их не заменяет."),
        ("Тест", "Шесть вопросов. Пять верных — ориентир. Критическая ошибка модуль не закрывает."),
        ("Очно", "Поиск, откапывание, первая помощь и ход по снегу этим файлом не засчитываются."),
    ]
    for i, (title, body) in enumerate(cards):
        x = 72 + i * 610
        b.box(x, 240, 580, 620, WHITE, radius=18)
        b.box(x, 240, 580, 12, BLUE)
        b.text(x + 40, 300, title, 32, NAVY, bold=True)
        b.text(x + 40, 420, body, 26, INK)
    b.footer(TOTAL, TOTAL)


TOTAL = 23  # title..end: 1 + 14 content through situation is 15, +6 questions = 21, key 22, end 23


def build_images():
    os.makedirs(OUT_DIR, exist_ok=True)
    makers = [s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12, s13, s14, s15]
    paths = []
    for i, fn in enumerate(makers, start=1):
        b = Board()
        fn(b)
        path = os.path.join(OUT_DIR, f"{i:02d}.png")
        b.save(path)
        paths.append(path)
    for n, prompt, options, sketch in QUESTIONS:
        b = Board()
        question(b, n, prompt, options, sketch)
        path = os.path.join(OUT_DIR, f"{15+n:02d}.png")
        b.save(path)
        paths.append(path)
    b = Board()
    s_key(b)
    path = os.path.join(OUT_DIR, "22.png")
    b.save(path)
    paths.append(path)
    b = Board()
    s_end(b)
    path = os.path.join(OUT_DIR, "23.png")
    b.save(path)
    paths.append(path)
    return paths


def build_pptx(paths: list[str]) -> str:
    from pptx import Presentation
    from pptx.util import Inches, Emu

    out = "/workspace/presentations/ALP-03_laviny-naglyadno.pptx"
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    prs.core_properties.title = "Школа альпинизма. Модуль 3. Лавины и влияние высокогорной среды"
    prs.core_properties.subject = "Наглядные схемы к пособию, с. 104–139"
    prs.core_properties.author = "Учебный комплект курса по пособию ФАР"
    blank = prs.slide_layouts[6]
    for path in paths:
        slide = prs.slides.add_slide(blank)
        slide.shapes.add_picture(path, Emu(0), Emu(0), width=prs.slide_width, height=prs.slide_height)
    prs.save(out)
    return out


if __name__ == "__main__":
    images = build_images()
    print(build_pptx(images))
