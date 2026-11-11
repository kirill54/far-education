#!/usr/bin/env python3
"""Перерисованные схемы из пособия: одна функция на схему.

Запуск `python3 presentations/figures/book.py` перерисовывает всё,
`python3 presentations/figures/book.py 03_time 01_trash` — только указанные.
Файлы ложатся в presentations/img/<модуль>_<имя>.png и подменяют вырезки из книги.

Большинство схем рисуется на холсте в дюймах (ось = размер фигуры), так проще
держать одинаковый кегль: на боковой карточке слайда схема 9" ужимается до ~7",
на широкой — 12" почти не масштабируется.
"""

from __future__ import annotations

import json
import math
import sys
import urllib.request
from pathlib import Path

import numpy as np
from matplotlib import patheffects
from matplotlib.patches import (Arc, Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle,
                                Wedge)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BLUE, GOLD, GREEN, GRID, ICE, IMG, INK, MUTED, NAVY, RED, ROCK, SNOW, figure,  # noqa: E402
                    plt, save)

ORANGE = "#e8833a"
SKY = "#dcebf6"
SKY2 = "#a9cde8"
DARKSNOW = "#c9dcea"
FOREST = "#2e6b3a"
GRASS = "#9cc97a"
WARM = "#f7c9a9"
LIGHTRED = "#f6d3d6"
LIGHTGREEN = "#dcefd0"
LIGHTGOLD = "#fdf0c4"
CACHE = Path("/tmp/far_fig_cache")

FIGS: dict = {}


def fig_(name):
    def wrap(fn):
        FIGS[name] = fn
        return fn
    return wrap


# ---------------------------------------------------------------- helpers

def canvas(w: float, h: float):
    """Холст, где координаты совпадают с дюймами фигуры."""
    fig = figure(w, h)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.set_axis_off()
    return fig, ax


def T(ax, x, y, s, size=18, color=INK, weight="normal", ha="center", va="center", **kw):
    return ax.text(x, y, s, fontsize=size, color=color, fontweight=weight, ha=ha, va=va, **kw)


def tag(ax, x, y, s, size=17, color=INK, fc="white", ec=None, ha="center", va="center", weight="normal",
        pad=0.3, alpha=0.93, **kw):
    """Подпись на светлой плашке — читается поверх любого фона."""
    return ax.text(x, y, s, fontsize=size, color=color, ha=ha, va=va, fontweight=weight,
                   bbox=dict(boxstyle=f"round,pad={pad}", fc=fc, ec=ec or "none", lw=1.5, alpha=alpha), **kw)


def arrow(ax, p0, p1, color=RED, lw=4, ms=28, style="-|>", rad=0.0, z=5, ls="-", shrink=0):
    a = FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=ms, color=color, lw=lw, zorder=z, linestyle=ls,
                        connectionstyle=f"arc3,rad={rad}", shrinkA=shrink, shrinkB=shrink, capstyle="round",
                        joinstyle="round")
    ax.add_patch(a)
    return a


def box(ax, x, y, w, h, fc, ec="none", lw=0, r=0.12, z=1, alpha=1.0):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw, zorder=z,
                       alpha=alpha)
    ax.add_patch(p)
    return p


def poly(ax, pts, fc, ec="none", lw=0, z=1, alpha=1.0, closed=True, **kw):
    p = Polygon(np.asarray(pts, float), closed=closed, fc=fc, ec=ec, lw=lw, zorder=z, alpha=alpha, **kw)
    ax.add_patch(p)
    return p


def tree(ax, x, y, h=0.6, color=FOREST, z=3):
    w = h * 0.55
    ax.add_patch(Rectangle((x - h * 0.04, y), h * 0.08, h * 0.2, fc="#5b4636", zorder=z))
    for i, k in enumerate((1.0, 0.8, 0.6)):
        b = y + h * (0.15 + i * 0.25)
        poly(ax, [(x - w * k / 2, b), (x + w * k / 2, b), (x, b + h * 0.45)], color, z=z)


def person(ax, x, y, h=0.5, color=INK, z=6):
    """Человечек по росту h; (x, y) — точка между ступнями."""
    lw = h * 9
    head = Circle((x, y + h * 0.88), h * 0.11, fc=color, ec="none", zorder=z)
    ax.add_patch(head)
    ax.plot([x, x], [y + h * 0.42, y + h * 0.76], color=color, lw=lw, solid_capstyle="round", zorder=z)
    ax.plot([x - h * 0.14, x, x + h * 0.14], [y, y + h * 0.42, y], color=color, lw=lw, solid_capstyle="round",
            zorder=z)
    ax.plot([x - h * 0.17, x, x + h * 0.17], [y + h * 0.48, y + h * 0.70, y + h * 0.48], color=color, lw=lw * 0.8,
            solid_capstyle="round", zorder=z)


def sitter(ax, x, y, h=0.5, color=INK, z=6):
    """Человек сидит на корточках, обхватив колени (поза при грозе)."""
    lw = h * 10
    ax.add_patch(Circle((x + h * 0.12, y + h * 0.78), h * 0.13, fc=color, zorder=z))
    ax.plot([x - h * 0.1, x + h * 0.05], [y + h * 0.15, y + h * 0.62], color=color, lw=lw, solid_capstyle="round",
            zorder=z)
    ax.plot([x + h * 0.05, x + h * 0.35, x + h * 0.25], [y + h * 0.15, y + h * 0.42, y + h * 0.02], color=color,
            lw=lw, solid_capstyle="round", zorder=z)
    ax.plot([x + h * 0.05, x + h * 0.32], [y + h * 0.55, y + h * 0.38], color=color, lw=lw * 0.8,
            solid_capstyle="round", zorder=z)


def pchip(xs, ys, xq):
    """Монотонная кубическая интерполяция (Fritsch–Carlson) без scipy."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    h = np.diff(xs)
    d = np.diff(ys) / h
    m = np.zeros_like(ys)
    for i in range(1, len(xs) - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    m[0], m[-1] = d[0], d[-1]
    xq = np.asarray(xq, float)
    i = np.clip(np.searchsorted(xs, xq) - 1, 0, len(xs) - 2)
    t = (xq - xs[i]) / h[i]
    h00, h10, h01, h11 = 2 * t**3 - 3 * t**2 + 1, t**3 - 2 * t**2 + t, -2 * t**3 + 3 * t**2, t**3 - t**2
    return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]


def chart_axes(fig, rect=(0.11, 0.14, 0.86, 0.8)):
    ax = fig.add_axes(rect)
    ax.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=16, length=0, pad=8)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
        ax.spines[s].set_linewidth(1.5)
    return ax


def wrap(s: str, n: int) -> str:
    words, lines, cur = s.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > n:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return "\n".join(lines)


def fetch(url: str, name: str) -> Path:
    CACHE.mkdir(exist_ok=True)
    path = CACHE / name
    if not path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "far-education-figures/1.0"})
        path.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    return path


# ================================================================ модуль 3

@fig_("03_time")
def time_curve():
    fig = figure(9, 6.3)
    ax = chart_axes(fig, (0.1, 0.13, 0.87, 0.83))
    t = np.linspace(0, 140, 600)
    ch = [(0, 100), (5, 97.5), (10, 95), (15, 92.4), (18, 91), (21, 80), (25, 63), (30, 46), (35, 34), (45, 30.5),
          (60, 26.5), (75, 23), (90, 20.5), (100, 17), (110, 13), (120, 9.5), (130, 7), (140, 5.5)]
    ca = [(0, 100), (5, 88), (10, 77), (14, 62), (18, 50), (25, 37), (35, 27), (45, 22), (60, 17.5), (90, 12),
          (120, 7.5), (140, 5)]
    for x0, x1, c in ((0, 18, LIGHTGREEN), (18, 35, LIGHTRED)):
        ax.axvspan(x0, x1, color=c, zorder=0, lw=0)
    sw = pchip(*zip(*ch), t)
    cn = pchip(*zip(*ca), t)
    ax.plot(t, cn, color=MUTED, lw=3.2, ls=(0, (5, 3)), zorder=3)
    ax.plot(t, sw, color=RED, lw=5, zorder=4, solid_capstyle="round")
    for x, y, s, dx, dy in ((18, 91, "91 %", 3, 4), (35, 34, "34 %", 3, 6), (90, 20.5, "≈ 20 %", 0, 7),
                            (130, 7, "≈ 7 %", 0, 7)):
        ax.plot(x, y, "o", ms=11, color=RED, mec="white", mew=2.5, zorder=5)
        ax.text(x + dx, y + dy, s, fontsize=19, fontweight="bold", color=RED, ha="left" if dx else "center")
    ax.text(9, 50, "первые\n15–18 мин:\nживы\n9 из 10", fontsize=17, ha="center", va="center", color=FOREST,
            fontweight="bold")
    ax.text(26.5, 2, "удушье:\nвыжи-\nвает\nкаждый\nтретий", fontsize=14, ha="center", va="bottom", color=RED)
    ax.text(68, 37, "воздушный карман:\nснижение медленнее", fontsize=16, ha="center", color=INK)
    ax.text(116, 30, "переохлаждение", fontsize=16, ha="center", color=INK)
    ax.text(40, 2.5, "пунктир — морской климат:\nпадение уже с 10-й минуты", fontsize=15, color=MUTED, ha="left",
            va="bottom")
    ax.set_xlim(0, 140)
    ax.set_ylim(0, 105)
    ax.set_xticks([0, 18, 35, 60, 90, 120])
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_yticklabels(["0", "20", "40", "60", "80", "100 %"])
    ax.set_xlabel("сколько минут человек под снегом", fontsize=17, labelpad=6)
    ax.set_ylabel("доля живых", fontsize=17, labelpad=4)
    return fig


@fig_("03_forces")
def forces():
    fig, ax = canvas(9, 6.4)
    psi = math.radians(33)
    t = np.array([math.cos(psi), math.sin(psi)])
    n = np.array([-math.sin(psi), math.cos(psi)])
    o = np.array([0.4, 0.5])
    L = 11
    poly(ax, [o, o + t * L, (9, 0), (0, 0), (0, 0.5)], "#cfc6bc", z=1)
    cols = ["#e9f2fa", "#d7e7f4", "#eef5fb", "#c9dff0"]
    th = [0.42, 0.28, 0.5, 0.45]
    base = 0.0
    for c, w in zip(cols, th):
        poly(ax, [o + n * base, o + t * L + n * base, o + t * L + n * (base + w), o + n * (base + w)], c,
             ec="#9fbbd3", lw=1.2, z=2)
        base += w
    ax.plot(*zip(o, o + t * L), color="#8a7f74", lw=3, zorder=3)
    # угол склона
    ax.plot([o[0], o[0] + 2.6], [o[1], o[1]], color=INK, lw=2, zorder=4)
    ax.add_patch(Arc(o, 3.6, 3.6, theta1=0, theta2=33, color=INK, lw=2, zorder=4))
    T(ax, o[0] + 2.15, o[1] + 0.42, "ψ", 22, weight="bold")
    T(ax, 3.1, 0.55, "крутизна склона ψ", 17, ha="left")
    # силы
    p = o + t * 6.1 + n * 0.95
    g = 2.9
    G = p + np.array([0, -g])
    S = p - t * g * math.sin(psi)
    C = p + np.array([math.sin(psi), -math.cos(psi)]) * g * math.cos(psi)
    for a, b in ((S, G), (C, G)):
        ax.plot(*zip(a, b), color=ORANGE, lw=2, ls=(0, (4, 3)), zorder=5)
    for end, c in ((G, RED), (S, ORANGE), (C, ORANGE)):
        arrow(ax, p, end, color=c, lw=5, ms=30, z=6)
    ax.add_patch(Circle(p, 0.09, color=INK, zorder=7))
    ax.add_patch(Arc(p, 2.0, 2.0, theta1=-90, theta2=-90 + 33, color=INK, lw=2, zorder=6))
    T(ax, p[0] + 0.35, p[1] - 1.3, "ψ", 20, weight="bold")
    tag(ax, G[0] + 0.12, G[1] - 0.35, "сила тяжести", 18, color=RED, weight="bold", ha="left")
    tag(ax, S[0] - 0.15, S[1] + 0.3, "сдвиг\nвдоль склона", 18, color=ORANGE, weight="bold", ha="right")
    tag(ax, C[0] + 0.25, C[1] + 0.1, "сжатие:\nприжимает\nк склону", 18, color=ORANGE, weight="bold", ha="left")
    tag(ax, 0.3, 5.7, "Снег лежит слоями.\nПока сцепление слоёв\nсильнее сдвига — держится.\nЧем круче склон, тем\nбольше сдвиг",
        17, ha="left", va="top", fc=SNOW)
    return fig


@fig_("03_slab")
def slab():
    fig, ax = canvas(9, 7.3)
    a = math.radians(25)
    t = np.array([math.cos(a), math.sin(a)])
    n = np.array([-math.sin(a), math.cos(a)])
    o = np.array([0.3, 2.45])
    L = 8.6
    end = o + t * L
    poly(ax, [o, end, (end[0], 2.25), (o[0], 2.25)], "#6d7f99", z=1)
    w = 0.17
    s = 0.95
    c0 = 4.9  # линия отрыва (расстояние вдоль склона)
    poly(ax, [o + t * 0.9, end, end + n * w, o + t * 0.9 + n * w], ORANGE, z=2)
    poly(ax, [o + t * c0 + n * w, end + n * w, end + n * (w + s), o + t * c0 + n * (w + s)], "#d6e8f6",
         ec="#7ea6c8", lw=1.5, z=3)
    shift = -t * 0.6
    poly(ax, [o + t * 1.0 + n * w + shift, o + t * (c0 - 0.35) + n * w + shift,
              o + t * (c0 - 0.15) + n * (w + s) + shift, o + t * 1.3 + n * (w + s * 0.9) + shift], "#e8f1f9",
         ec="#7ea6c8", lw=1.5, z=3)
    for k in (2.0, 3.0, 4.0):
        q = o + t * k + n * (w + s * 0.5) + shift
        arrow(ax, q + t * 0.35, q - t * 0.35, color="#4a7eaa", lw=2.5, ms=18, z=4)
    cr = o + t * c0
    ax.plot([cr[0] + n[0] * w, cr[0] + n[0] * (w + s)], [cr[1] + n[1] * w, cr[1] + n[1] * (w + s)], color=RED,
            lw=4, zorder=5)
    top = cr + n * (w + s)
    tag(ax, top[0] - 0.6, top[1] + 0.95, "линия отрыва", 18, color=RED, weight="bold")
    arrow(ax, (top[0] - 0.4, top[1] + 0.7), top + n * 0.05, color=RED, lw=2.5, ms=20)
    q = o + t * 7.0 + n * (w + s * 0.5)
    T(ax, q[0], q[1], "плита («доска»)", 18, weight="bold", rotation=25, rotation_mode="anchor")
    q = o + t * 6.6 + n * 0.08
    tag(ax, q[0] + 0.6, q[1] - 0.95, "слабый слой", 18, color=ORANGE, weight="bold")
    arrow(ax, (q[0] + 0.4, q[1] - 0.7), q, color=ORANGE, lw=2.5, ms=20)
    T(ax, end[0] - 0.2, 2.6, "старый снег, грунт", 16, color="white", ha="right")
    # домино
    y0 = 0.35
    ax.plot([0.2, 8.8], [y0, y0], color=INK, lw=2)
    xs = np.linspace(1.6, 8.3, 12)
    for i, x in enumerate(xs):
        k = min(1.0, max(0.0, (8 - i) / 8))
        ang = math.radians(90 - 72 * k)
        hgt, wd = 1.15, 0.16
        c, s_ = math.cos(ang), math.sin(ang)
        pts = [(x, y0), (x + wd * s_, y0 - wd * c * 0), (x + wd * s_ + hgt * c, y0 + hgt * s_), (x + hgt * c,
                                                                                                    y0 + hgt * s_)]
        pts = [(x, y0), (x + wd, y0), (x + wd + hgt * math.cos(ang), y0 + hgt * math.sin(ang)),
               (x + hgt * math.cos(ang), y0 + hgt * math.sin(ang))]
        poly(ax, pts, "#3f88b8" if k > 0 else "#8ab6d6", ec="white", lw=1, z=3)
    arrow(ax, (0.2, 0.95), (1.45, 0.95), color=RED, lw=7, ms=34)
    T(ax, 0.2, 1.65, "нагрузка", 17, color=RED, weight="bold", ha="left")
    T(ax, 4.6, 1.95, "разрушение бежит по слабому слою, как домино", 18, weight="bold")
    return fig


def mountain_bg(ax, w, h, peaks, base=0.0, fc="#f4f8fb", ec="#9db7cc"):
    pts = [(0, base)] + peaks + [(w, base)]
    poly(ax, pts, fc, ec=ec, lw=2, z=1)


@fig_("03_zones")
def zones():
    fig, ax = canvas(9.2, 6.4)
    poly(ax, [(0, 0), (9.2, 0), (9.2, 6.4), (0, 6.4)], SKY, z=0)
    mountain_bg(ax, 9.2, 6.4, [(0, 4.2), (2.1, 5.6), (3.4, 4.9), (4.6, 5.1), (6.2, 6.0), (7.6, 5.0), (9.2, 4.5)],
                base=0.9)
    poly(ax, [(0, 0), (9.2, 0), (9.2, 1.3), (0, 1.3)], "#f4f8fb", z=1)
    # А — доска: линия отрыва, путь, конус
    crown = [(1.0, 4.55), (3.6, 4.55)]
    path = [(1.0, 4.55), (3.6, 4.55), (3.45, 3.6), (3.0, 2.6), (2.6, 1.9), (1.5, 1.9), (1.2, 2.8), (1.05, 3.7)]
    poly(ax, path, "#c7dbea", ec="#7ea6c8", lw=2, z=2)
    ax.plot(*zip(*crown), color=RED, lw=5, zorder=4)
    for i in range(70):
        rng = np.random.default_rng(i)
        x, y = 2.05 + rng.normal(0, 0.55), 1.55 + abs(rng.normal(0, 0.25))
        ax.add_patch(Circle((x, y), 0.09 + 0.08 * rng.random(), fc="white", ec="#8fb1cc", lw=1, zorder=3))
    # Б — из точки
    start = (6.4, 5.2)
    tail = [start, (6.75, 4.2), (7.1, 3.1), (7.35, 2.2), (6.55, 2.2), (6.4, 3.1), (6.3, 4.2)]
    poly(ax, tail, "#c7dbea", ec="#7ea6c8", lw=2, z=2)
    ax.add_patch(Circle(start, 0.11, color=RED, zorder=4))
    for i in range(30):
        rng = np.random.default_rng(100 + i)
        ax.add_patch(Circle((6.95 + rng.normal(0, 0.3), 1.95 + abs(rng.normal(0, 0.15))),
                            0.07 + 0.06 * rng.random(), fc="white", ec="#8fb1cc", lw=1, zorder=3))
    for x, y in ((0.4, 2.2), (0.7, 3.0), (4.3, 2.4), (4.8, 3.1), (4.5, 1.7), (5.4, 2.0), (8.2, 2.6), (8.6, 3.4),
                 (8.0, 1.8), (5.6, 3.3)):
        tree(ax, x, y, 0.55)
    for s, x, y in (("1", 2.3, 4.95), ("2", 2.3, 3.2), ("3", 3.35, 1.55), ("1", 6.0, 5.35), ("2", 6.45, 3.35),
                    ("3", 7.85, 1.85)):
        ax.add_patch(Circle((x, y), 0.25, fc="white", ec=INK, lw=1.5, zorder=6))
        T(ax, x, y, s, 17, weight="bold", zorder=7)
    T(ax, 0.35, 5.25, "А", 34, color=RED, weight="bold")
    T(ax, 8.7, 5.25, "Б", 34, color=RED, weight="bold")
    T(ax, 2.3, 0.55, "А — от линии («доска»)", 18, weight="bold")
    T(ax, 6.95, 0.55, "Б — из точки", 18, weight="bold")
    tag(ax, 4.6, 6.0, "1 — зона зарождения   2 — транзит   3 — конус выноса", 16, fc="white")
    return fig


@fig_("03_sizes")
def sizes():
    rows = [
        ("1", "Относительно безвредна для людей", "10", "10"),
        ("2", "Может засыпать, травмировать или убить человека", "100", "100"),
        ("3", "Может засыпать или разрушить легковую машину, грузовик, деревянный дом, сломать несколько деревьев",
         "1 000", "1 000"),
        ("4", "Может разрушить вагон, большой грузовик, несколько зданий или участок леса до 4 га", "10 000",
         "2 000"),
        ("5", "Может снести деревню или лес площадью до 40 га", "100 000", "3 000"),
    ]
    fig, ax = canvas(10.5, 6.6)
    cols = [0.0, 1.2, 7.1, 8.8, 10.5]
    heads = ["Размер", "Что может натворить", "Масса, т", "Путь, м"]
    hy = 5.95
    box(ax, 0, hy, 10.5, 0.65, NAVY, r=0.08)
    for i, hname in enumerate(heads):
        T(ax, (cols[i] + cols[i + 1]) / 2, hy + 0.33, hname, 18, color="white", weight="bold")
    heights = [0.8, 0.95, 1.45, 1.45, 0.95]
    y = hy - 0.08
    for (k, desc, m, p), hgt in zip(rows, heights):
        y -= hgt
        hot = k == "2"
        fc = LIGHTRED if hot else (SNOW if int(k) % 2 else "white")
        box(ax, 0, y + 0.04, 10.5, hgt - 0.08, fc, ec=RED if hot else "none", lw=2.5 if hot else 0, r=0.06)
        T(ax, (cols[0] + cols[1]) / 2, y + hgt / 2, k, 26, weight="bold", color=RED if hot else NAVY)
        T(ax, cols[1] + 0.15, y + hgt / 2, wrap(desc, 46), 17, ha="left", weight="bold" if hot else "normal",
          linespacing=1.15)
        T(ax, (cols[2] + cols[3]) / 2, y + hgt / 2, m, 19)
        T(ax, (cols[3] + cols[4]) / 2, y + hgt / 2, p, 19)
    return fig


@fig_("03_wind")
def wind():
    fig, ax = canvas(12, 3.9)
    poly(ax, [(0, 0), (12, 0), (12, 3.9), (0, 3.9)], SKY, z=0)
    ridge = [(0, 0), (0, 0.35), (2.5, 0.9), (5.2, 2.35), (6.0, 2.85), (6.7, 2.45), (9.3, 0.9), (12, 0.45), (12, 0)]
    poly(ax, ridge, "#a49a8f", z=1)
    # наветренный: тонкий снег; подветренный: толстый
    wind_side = [(0, 0.35), (2.5, 0.9), (5.2, 2.35), (6.0, 2.85), (6.0, 2.97), (5.2, 2.45), (2.5, 1.0), (0, 0.45)]
    poly(ax, wind_side, "white", ec="#9fbbd3", lw=1.2, z=2)
    lee = [(6.0, 2.85), (6.7, 2.45), (9.3, 0.9), (12, 0.45), (12, 0.75), (9.4, 1.42), (7.4, 2.4), (6.9, 2.8),
           (6.05, 2.97)]
    poly(ax, lee, "#e3eff8", ec="#7ea6c8", lw=1.5, z=2)
    poly(ax, [(6.0, 2.97), (6.85, 3.08), (7.25, 2.95), (7.15, 2.72), (6.9, 2.8)], "#e3eff8", ec="#7ea6c8", lw=1.5,
         z=3)
    for k, y in enumerate((2.75, 3.35)):
        xs = np.linspace(0.2, 11.8, 200)
        ys = y + 0.95 * np.exp(-((xs - 6.1) / 2.3) ** 2) * (1.1 - k * 0.25) - 0.25 * (xs / 12)
        ax.plot(xs, ys, color=BLUE, lw=3, zorder=4)
        arrow(ax, (xs[-3], ys[-3]), (xs[-1] + 0.05, ys[-1] - 0.01), color=BLUE, lw=3, ms=22)
    for x0, y0 in ((3.3, 1.5), (4.55, 2.15)):
        arrow(ax, (x0, y0), (x0 + 0.85, y0 + 0.45), color=RED, lw=3, ms=20)
    for x0, y0 in ((6.95, 2.95), (7.85, 2.45)):
        arrow(ax, (x0, y0), (x0 + 0.4, y0 - 0.55), color=RED, lw=3, ms=20)
    arrow(ax, (0.3, 3.35), (2.1, 3.35), color=RED, lw=7, ms=36)
    T(ax, 0.3, 3.68, "ветер", 18, weight="bold", color=RED, ha="left")
    tag(ax, 1.45, 1.75, "наветренный склон:\nснег выдувает,\nзаструги", 16, ha="center")
    tag(ax, 10.3, 2.05, "подветренный склон:\nснег оседает —\nперегруз, «доски»", 16, weight="bold", color=RED)
    tag(ax, 7.95, 3.45, "карниз", 16)
    tag(ax, 4.55, 0.45, "перенос снега — уже с 5–7 м/с в высокогорье, с 3–4 м/с в предгорьях", 15)
    return fig


@fig_("03_temp")
def temp():
    cards = [
        ("Сильное\nбыстрое\nпотепление\nвыше нуля", "#d63b47", "опасность\nрастёт", RED),
        ("Медленное\nумеренное\nпотепление", "#e8833a", "снег\nкрепнет", GREEN),
        ("Тепло днём,\nхолод\nночью", "#5a9e32", "снег\nкрепнет", GREEN),
        ("Холодная\nпогода", "#3fa7b5", "всё остаётся\nкак было", MUTED),
        ("Долгий\nсильный\nмороз", "#284a7e", "растут\nслабые слои", RED),
    ]
    fig, ax = canvas(12, 3.75)
    w, gap = 2.18, 0.27
    for i, (s, c, verdict, vc) in enumerate(cards):
        x = i * (w + gap)
        box(ax, x, 1.45, w, 2.25, c, r=0.18)
        T(ax, x + w / 2, 2.58, s, 18, color="white", weight="bold", linespacing=1.1)
        mark = {RED: "▲", GREEN: "▼", MUTED: "■"}[vc]
        box(ax, x + 0.08, 0.05, w - 0.16, 1.2, "white", ec=vc, lw=3, r=0.14)
        T(ax, x + 0.33, 0.65, mark, 22, color=vc)
        T(ax, x + w / 2 + 0.18, 0.65, verdict, 16, color=vc if vc != MUTED else INK, weight="bold",
          linespacing=1.05)
    return fig


@fig_("03_aspect")
def aspect():
    fig, ax = canvas(7.6, 7.0)
    c = (3.9, 3.75)
    R = 2.45
    # углы matplotlib: 0° = восток, против часовой
    for t1, t2, col in ((45, 135, "#e06c75"), (0, 45, "#f6c36b"), (135, 180, "#f6c36b"), (180, 360, "#7cc49a")):
        ax.add_patch(Wedge(c, R, t1, t2, fc=col, ec="white", lw=3, zorder=2))
    rng = np.linspace(0, 2 * np.pi, 300)
    for r in (0.6, 1.2, 1.8):
        ax.plot(c[0] + r * np.cos(rng), c[1] + r * np.sin(rng), color="white", lw=1, alpha=0.6, zorder=3)
    T(ax, c[0], c[1] + 1.45, "56 %", 34, color="white", weight="bold", zorder=5)
    T(ax, c[0], c[1] - 1.25, "30 %", 34, color="white", weight="bold", zorder=5)
    for s, ang in (("С", 90), ("В", 0), ("Ю", 270), ("З", 180)):
        x, y = c[0] + (R + 0.42) * math.cos(math.radians(ang)), c[1] + (R + 0.42) * math.sin(math.radians(ang))
        T(ax, x, y, s, 24, weight="bold")
    for s, ang in (("СВ", 45), ("СЗ", 135)):
        x, y = c[0] + (R + 0.4) * math.cos(math.radians(ang)), c[1] + (R + 0.4) * math.sin(math.radians(ang))
        T(ax, x, y, s, 17, color=MUTED, weight="bold")
    T(ax, c[0], 0.25, "доля лавин по направлению склона", 18)
    arrow(ax, (0.05, 6.75), (1.55, 6.75), color=BLUE, lw=6, ms=30)
    T(ax, 0.05, 6.4, "западный ветер", 16, color=BLUE, ha="left", weight="bold")
    return fig


@fig_("03_angles")
def angles():
    fig, ax = canvas(9.0, 6.6)
    o = (0.45, 0.6)
    R = 5.4
    zones = [
        (0, 15, "#eef2f6", "мокрые лавины,\nсели — редко", 0.62, 14),
        (15, 25, "#dfe8f0", "редкие лавины", 0.6, 15),
        (25, 45, "#f2a65a", "основной диапазон лавин", 0.55, 17),
        (45, 60, "#f8d2a8", "часто ссыпается\nсвежий снег", 0.58, 15),
        (60, 90, "#f4f6f8", "лавины\nмаловероятны:\nснег не держится", 0.8, 15),
    ]
    for a1, a2, col, s, rr, fs in zones:
        ax.add_patch(Wedge(o, R, a1, a2, fc=col, ec="white", lw=2, zorder=2))
        mid = math.radians((a1 + a2) / 2)
        rot = (a1 + a2) / 2 if a2 - a1 < 30 else 0
        T(ax, o[0] + R * rr * math.cos(mid), o[1] + R * rr * math.sin(mid), s, fs, rotation=rot,
          rotation_mode="anchor", weight="bold" if a1 == 25 else "normal", zorder=6)
    freq = {20: 0.12, 25: 0.32, 30: 0.58, 35: 1.0, 40: 0.7, 45: 0.38, 50: 0.14}
    for a, f in freq.items():
        ax.add_patch(Wedge(o, R + 0.12 + f * 1.25, a + 0.3, a + 4.7, width=f * 1.25, fc=RED if a == 35 else ORANGE,
                           ec="white", lw=1, zorder=3))
    for a in (0, 15, 25, 30, 35, 40, 45, 50, 55, 60, 90):
        r = R + (1.6 if 20 <= a <= 55 else 0.45)
        T(ax, o[0] + r * math.cos(math.radians(a)), o[1] + r * math.sin(math.radians(a)), f"{a}°",
          16 if a % 15 == 0 or a in (25, 45) else 13, color=INK if a % 15 == 0 or a in (25, 45) else MUTED)
    a38 = math.radians(38)
    ax.plot([o[0] + R * 0.86 * math.cos(a38), o[0] + (R + 1.4) * math.cos(a38)],
            [o[1] + R * 0.86 * math.sin(a38), o[1] + (R + 1.4) * math.sin(a38)], color=RED, lw=2.5,
            ls=(0, (5, 3)), zorder=5)
    tag(ax, 5.9, 6.55, "больше всего\nнесчастных случаев —\nоколо 38°", 16, color=RED, weight="bold", ha="left")
    T(ax, o[0] + 0.15, 0.25, "крутизна склона, градусы", 16, ha="left", color=MUTED)
    T(ax, 3.2, 6.1, "столбики — частота\nнесчастных случаев", 15, color=ORANGE, weight="bold", ha="center")
    return fig


@fig_("03_convex")
def convex():
    fig, ax = canvas(9, 5.4)
    x = np.linspace(0.3, 8.8, 400)
    y = 1.0 + 3.0 / (1 + np.exp((x - 4.2) * 1.25))
    poly(ax, list(zip(x, y - 0.0)) + [(8.8, 0.4), (0.3, 0.4)], "#e1edf7", z=1)
    ax.plot(x, y, color=BLUE, lw=12, solid_capstyle="round", zorder=3)
    i = np.argmin(abs(x - 2.6))
    dx, dy = x[i + 5] - x[i - 5], y[i + 5] - y[i - 5]
    nrm = np.array([-dy, dx]) / math.hypot(dx, dy)
    p = np.array([x[i], y[i]])
    ax.plot(*zip(p - nrm * 1.3, p + nrm * 0.8), color=RED, lw=3, ls=(0, (5, 3)), zorder=4)
    tg = np.array([dx, dy]) / math.hypot(dx, dy)
    arrow(ax, p + nrm * 0.55 - tg * 0.25, p + nrm * 0.55 - tg * 1.1, color=RED, lw=3.5, ms=22)
    arrow(ax, p + nrm * 0.55 + tg * 0.25, p + nrm * 0.55 + tg * 1.1, color=RED, lw=3.5, ms=22)
    tag(ax, 3.65, 5.05, "выпуклость: снег растянут — рвётся первым", 17, color=RED, weight="bold")
    tag(ax, 1.25, 2.35, "вероятная\nлиния отрыва", 16, color=RED)
    j = np.argmin(abs(x - 6.6))
    q = np.array([x[j], y[j]])
    arrow(ax, q + np.array([-0.9, 0.62]), q + np.array([-0.2, 0.42]), color=GREEN, lw=3.5, ms=22)
    arrow(ax, q + np.array([0.9, 0.38]), q + np.array([0.2, 0.40]), color=GREEN, lw=3.5, ms=22)
    tag(ax, 6.6, 2.35, "вогнутость: снег сжат —\nустойчивее", 17, color=FOREST, weight="bold")
    return fig


@fig_("03_anchors")
def anchors():
    fig, ax = canvas(10.5, 6.8)
    w, h, gx, gy = 3.35, 3.15, 0.2, 0.3
    panels = [
        ("редкие деревья", "эффект слабый", "trees", 2, ORANGE),
        ("густой лес", "держит хорошо", "trees", 5, GREEN),
        ("очень густой лес", "держит лучше всего", "trees", 9, GREEN),
        ("гладкий склон:\nтрава, плиты", "сход до земли", "flat", 0, RED),
        ("камни, кусты", "держат", "rocks", 3, GREEN),
        ("крупные глыбы", "держат лучше", "rocks", 2, GREEN),
    ]
    for k, (title, verdict, kind, cnt, vc) in enumerate(panels):
        col, row = k % 3, k // 3
        x0, y0 = col * (w + gx), (1 - row) * (h + gy) + 0.05
        box(ax, x0, y0, w, h, SKY, r=0.1)

        def sl(u, off=0.0):
            return x0 + 0.15 + u * (w - 0.3), y0 + h - 0.95 - u * (h - 1.35) + off

        g = [sl(u) for u in np.linspace(0, 1, 30)]
        poly(ax, g + [(x0 + w - 0.15, y0 + 0.08), (x0 + 0.15, y0 + 0.08)], "#b9ab9b", z=2)
        snow = [sl(u, 0.28) for u in np.linspace(0, 1, 30)]
        poly(ax, g + snow[::-1], "white", ec="#9fbbd3", lw=1, z=3)
        rng = np.random.default_rng(k)
        if kind == "trees":
            for u in np.sort(rng.uniform(0.08, 0.92, cnt)):
                px, py = sl(u, 0.1)
                tree(ax, px, py, 0.62 + 0.2 * rng.random(), z=4)
        elif kind == "rocks":
            for u in np.linspace(0.2, 0.8, cnt):
                px, py = sl(u, 0.12)
                r = 0.16 if cnt > 2 else 0.3
                ax.add_patch(Ellipse((px, py), r * 2.2, r * 1.6, fc="#8a7f74", ec="#5e554c", lw=1, zorder=4))
        else:
            for u in np.linspace(0.05, 0.95, 14):
                px, py = sl(u, 0.14)
                ax.plot(px, py, ".", color="#9fbbd3", ms=5, zorder=4)
            arrow(ax, sl(0.35, 0.65), sl(0.75, 0.65), color=RED, lw=3, ms=20)
        T(ax, x0 + w - 0.15, y0 + h - 0.2, title, 16, ha="right", va="top", weight="bold")
        tag(ax, x0 + 0.2, y0 + 0.35, verdict, 16, color=vc, weight="bold", ha="left", fc="white")
    return fig


@fig_("03_route")
def route():
    fig, ax = canvas(9.2, 6.6)
    poly(ax, [(0, 0), (9.2, 0), (9.2, 6.6), (0, 6.6)], SKY, z=0)
    poly(ax, [(0, 0), (0, 3.6), (2.6, 6.2), (3.6, 5.6), (5.0, 4.3), (7.2, 4.8), (9.2, 4.0), (9.2, 0)], "#f4f8fb",
         ec="#9db7cc", lw=2, z=1)
    gully = [(2.45, 6.0), (3.35, 5.55), (4.2, 3.6), (5.4, 1.6), (4.35, 1.2), (3.1, 2.8), (2.35, 4.5)]
    poly(ax, gully, "#f6d3d6", ec=RED, lw=2, z=2, alpha=0.9)
    arrow(ax, (3.1, 4.6), (4.3, 2.4), color=RED, lw=10, ms=46)
    tag(ax, 3.75, 5.05, "опасная зона", 18, color=RED, weight="bold")
    for x, y in ((0.5, 3.0), (1.0, 2.4), (0.6, 1.7), (1.5, 3.1), (1.3, 1.2), (6.4, 3.4), (7.0, 2.9), (7.7, 3.5),
                 (8.4, 3.0), (8.8, 2.3), (6.1, 4.0), (7.4, 4.1), (8.0, 4.15)):
        if (x, y) in ((7.0, 2.9), (6.4, 3.4), (1.3, 1.2)):
            continue
        tree(ax, x, y, 0.6)
    for cx, cy in ((2.1, 1.3), (6.9, 1.95)):
        ax.add_patch(Ellipse((cx, cy), 2.3, 1.25, fc=LIGHTGREEN, ec=GREEN, lw=4, zorder=3, alpha=0.95))
    person(ax, 1.75, 1.0, 0.6, color=INK)
    person(ax, 2.25, 1.0, 0.6, color=INK)
    person(ax, 7.1, 1.7, 0.6, color=INK)
    T(ax, 2.1, 0.22, "безопасное место:\nостальные ждут и смотрят", 15, color=FOREST, weight="bold", va="center")
    T(ax, 6.9, 2.95, "безопасное место", 15, color=FOREST, weight="bold")
    xs = np.linspace(3.2, 6.0, 50)
    ys = 1.25 + 0.65 * ((xs - 3.2) / 2.8) ** 1.6
    ax.plot(xs, ys, color=RED, lw=3, ls=(0, (6, 4)), zorder=4)
    person(ax, 4.6, 1.42, 0.6, color=RED)
    tag(ax, 5.9, 0.75, "переходим по одному, быстро", 16, color=RED, weight="bold")
    return fig


@fig_("03_kit")
def kit():
    fig, ax = canvas(9.2, 6.2)
    # датчик
    box(ax, 0.6, 1.3, 1.9, 3.0, "#3c4a5a", r=0.3, z=2)
    box(ax, 0.85, 2.9, 1.4, 1.1, "#a8e07a", r=0.1, z=3)
    T(ax, 1.55, 3.45, "3,5 м", 18, weight="bold", zorder=4)
    arrow(ax, (1.2, 3.12), (1.9, 3.12), color=INK, lw=2.5, ms=14, z=4)
    box(ax, 0.85, 1.6, 1.4, 1.0, "#7ac943", r=0.12, z=3)
    ax.plot([1.2, 0.9, 0.55, 0.4], [1.3, 0.9, 0.85, 0.5], color="#7ac943", lw=4, zorder=1)
    # щуп
    segs = 6
    for i in range(segs):
        x0 = 3.4 + i * 0.05
        ax.plot([3.15 + i * 0.36, 3.15 + (i + 1) * 0.36], [1.05 + i * 0.55, 1.05 + (i + 1) * 0.55], color="#9aa4ad",
                lw=8, solid_capstyle="butt", zorder=2)
        ax.plot([3.15 + (i + 1) * 0.36] * 2, [1.0 + (i + 1) * 0.55, 1.1 + (i + 1) * 0.55], color=INK, lw=3,
                zorder=3)
    for k in range(1, 8):
        y = 1.05 + k * 0.4
        T(ax, 3.0 + (y - 1.05) / 0.55 * 0.36, y, "", 1)
    # лопата
    poly(ax, [(5.9, 1.0), (7.3, 0.7), (7.6, 2.0), (6.3, 2.4)], "#2f7fc1", ec="#1d5b8f", lw=2, z=2)
    ax.plot([6.95, 8.2], [2.2, 4.6], color="#b9c2ca", lw=10, solid_capstyle="round", zorder=1)
    ax.plot([7.85, 8.55], [4.75, 4.45], color=INK, lw=10, solid_capstyle="round", zorder=2)
    for x, y, n, s in ((1.55, 4.75, "1", "лавинный\nдатчик"), (4.25, 4.75, "2", "щуп\n(зонд)"),
                       (7.0, 4.75, "3", "лопата")):
        ax.add_patch(Circle((x - 0.95, y + 0.55), 0.28, fc=NAVY, zorder=5))
        T(ax, x - 0.95, y + 0.55, n, 18, color="white", weight="bold", zorder=6)
        T(ax, x - 0.55, y + 0.55, s, 19, weight="bold", ha="left", va="center")
    tag(ax, 4.6, 0.3, "полный комплект — у каждого участника", 18, color=RED, weight="bold", fc=LIGHTRED)
    return fig


ACCLIM = {
    "сильная группа": (BLUE, [(0, 3500), (3, 6100), (4, 3500), (6, 3500), (9, 6100), (9.5, 7134), (10, 6100),
                              (11, 3500)]),
    "обычная группа": (GREEN, [(0, 3500), (2, 5300), (3, 3500), (5, 3500), (6, 4400), (8, 6100), (9, 3500),
                               (11, 3500), (12, 4400), (13, 5300), (14, 6100), (14.5, 7134), (16, 3500)]),
    "слабая группа": (GOLD, [(0, 3500), (2, 4900), (2.05, 4400), (3, 5300), (4, 3500), (6, 3500), (8.65, 5700),
                             (9, 5300), (10, 6100), (11.4, 3500), (14, 3500), (15, 4400), (16, 5300),
                             (16.65, 6100), (17.55, 7134), (18, 6100), (20, 3500)]),
}


@fig_("03_acclim")
def acclim():
    fig = figure(9.4, 6.4)
    ax = chart_axes(fig, (0.11, 0.12, 0.86, 0.8))
    ax.axhline(6100, color=RED, lw=1.5, ls=(0, (5, 4)), zorder=1)
    ax.text(3.4, 6170, "ночёвка на 6100 м\n(пик Раздельная)", fontsize=14, color=RED, ha="left", va="bottom")
    for name, (c, pts) in ACCLIM.items():
        x, y = zip(*pts)
        ax.plot(x, y, color=c, lw=3.5, marker="o", ms=6, zorder=3, label=name, solid_joinstyle="round")
    ax.plot([9.5, 14.5, 17.55], [7134] * 3, "*", ms=22, color=RED, mec="white", zorder=5)
    ax.set_xlim(0, 20.3)
    ax.set_ylim(3300, 7500)
    ax.set_xticks(range(0, 21, 2))
    ax.set_yticks([3500, 4400, 5300, 6100, 7134])
    ax.set_xlabel("день", fontsize=17)
    ax.set_ylabel("высота, м", fontsize=17)
    ax.legend(loc="upper left", fontsize=15, frameon=True, framealpha=0.95, edgecolor="white", ncol=3,
              bbox_to_anchor=(0, 1.13), handlelength=1.6, columnspacing=1.2)
    ax.text(0.15, 7300, "вершина 7134 м", fontsize=14, color=RED, va="center")
    return fig


@fig_("03_elbrus")
def elbrus():
    fig = figure(9.4, 6.2)
    ax = chart_axes(fig, (0.11, 0.13, 0.87, 0.82))
    pts = [(0.25, 2300), (1, 2300), (1.5, 3800), (2, 2300), (2.5, 3800), (3, 2300), (3.85, 4100), (4, 4100),
           (4.55, 5000), (5, 2300), (6, 2300), (6.85, 4100), (7, 4100), (7.55, 5642), (8, 2300)]
    x, y = zip(*pts)
    ax.plot(x, y, color=GREEN, lw=4, zorder=3, solid_joinstyle="round")
    nights = [(1, 2300), (2, 2300), (3, 2300), (4, 4100), (5, 2300), (6, 2300), (7, 4100)]
    ax.plot(*zip(*nights), "o", ms=13, color=NAVY, mec="white", mew=2, zorder=4, label="ночёвка")
    ax.plot([7.55], [5642], "*", ms=26, color=RED, mec="white", zorder=5)
    for d in range(1, 8):
        ax.axvline(d, color=GRID, lw=1.2, zorder=0)
    ax.set_xticks([d - 0.5 for d in range(1, 9)])
    ax.set_xticklabels([str(d) for d in range(1, 9)], fontsize=17, fontweight="bold")
    ax.xaxis.grid(False)
    ax.set_xlim(0, 8.25)
    ax.set_ylim(2000, 6150)
    ax.set_yticks([2300, 3800, 4100, 5000, 5642])
    ax.set_xlabel("день", fontsize=17)
    ax.set_ylabel("высота, м", fontsize=17)
    for xx, yy, s in ((1.5, 3800, "3800"), (2.5, 3800, "3800"), (4.55, 5000, "5000"), (7.55, 5642, "вершина 5642"),
                      (3.6, 4100, "4100"), (6.6, 4100, "4100")):
        ax.text(xx, yy + 110, s, fontsize=14, ha="center", va="bottom", color=INK)
    ax.text(0.5, 2420, "Азау", fontsize=14, ha="center", va="bottom", color=MUTED)
    ax.text(5.5, 2420, "отдых", fontsize=14, ha="center", va="bottom", color=MUTED)
    ax.legend(loc="upper left", fontsize=15, frameon=False)
    return fig


# ================================================================ запуск

def main(names: list[str]):
    todo = names or list(FIGS)
    for name in todo:
        fig = FIGS[name]()
        if isinstance(fig, Path):
            print("ok", fig.name)
            continue
        path = save(fig, name)
        print("ok", path.name)


if __name__ == "__main__":
    main(sys.argv[1:])
