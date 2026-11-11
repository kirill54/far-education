"""Схемы модуля 11: лестница средств страховки и перила по диагонали через реку.

    python3 presentations/figures/m11.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon  # noqa: E402

from common import BLUE, GOLD, GREEN, ICE, INK, MUTED, NAVY, RED, ROCK, figure, save  # noqa: E402


def ladder():
    fig = figure(14, 5.6)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 5.6)
    ax.axis("off")
    steps = [
        ("Свободно", "тропа, осыпь,\nпологий снег", GREEN),
        ("Рукой", "один–два\nтрудных шага", GREEN),
        ("Короткая\nверёвка", "срыв —\nв зародыше", GOLD),
        ("Через рельеф,\nучастки", "выступ, станция\nна 10–20 м", GOLD),
        ("Перила,\nстанции", "фирн, лёд, плиты,\nгруппа", RED),
        ("Разворот", "нет следующей\nступени", NAVY),
    ]
    w, h0, dh = 2.1, 0.9, 0.62
    for i, (name, note, color) in enumerate(steps):
        x = 0.35 + i * 2.25
        h = h0 + i * dh
        ax.add_patch(FancyBboxPatch((x, 0.3), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    fc=color, ec="none", alpha=0.95))
        ax.text(x + w / 2, 0.3 + h - 0.12, name, ha="center", va="top", fontsize=17, fontweight="bold",
                color="white" if color in (RED, NAVY, GREEN) else INK)
        ax.text(x + w / 2, 0.3 + h + 0.15, note, ha="center", va="bottom", fontsize=13.5, color=INK)
    ax.add_patch(FancyArrowPatch((0.6, 4.95), (12.4, 4.95), arrowstyle="-|>", mutation_scale=28, lw=3,
                                 color=MUTED))
    ax.text(6.5, 5.12, "признак опасности → ступень выше, заранее, на площадке", ha="center", va="bottom",
            fontsize=15, color=INK, fontweight="bold")
    save(fig, "m11_ladder")


def diagonal():
    fig = figure(8, 7.2)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 7.2)
    ax.axis("off")
    ax.add_patch(Polygon([(0, 1.6), (8, 1.6), (8, 5.6), (0, 5.6)], closed=True, fc=ICE, ec="none"))
    ax.add_patch(Polygon([(0, 0), (8, 0), (8, 1.6), (0, 1.6)], closed=True, fc="#e8e1d6", ec="none"))
    ax.add_patch(Polygon([(0, 5.6), (8, 5.6), (8, 7.2), (0, 7.2)], closed=True, fc="#e8e1d6", ec="none"))
    for y in (2.3, 3.5, 4.7):
        for x in (0.6, 3.2, 5.8):
            ax.add_patch(FancyArrowPatch((x, y), (x + 1.3, y), arrowstyle="-|>", mutation_scale=18, lw=2,
                                         color=BLUE, alpha=0.7))
    ax.text(7.85, 3.0, "течение", ha="right", va="center", fontsize=15, color=BLUE, fontweight="bold",
            rotation=0)
    a, b = (1.6, 1.25), (5.4, 5.95)
    ax.plot([a[0], b[0]], [a[1], b[1]], color=GOLD, lw=5, solid_capstyle="round")
    for (x, y) in (a, b):
        ax.add_patch(FancyBboxPatch((x - 0.3, y - 0.22), 0.6, 0.44, boxstyle="round,pad=0.02",
                                    fc=ROCK, ec="none"))
    ax.text(a[0] + 0.45, a[1] - 0.35, "вход", fontsize=15, color=INK, fontweight="bold")
    ax.text(b[0] + 0.45, b[1] + 0.1, "выход — ниже по течению", fontsize=15, color=INK, fontweight="bold")
    px, py = 3.85, 3.4
    ax.plot([px], [py], "o", ms=16, color=RED)
    ax.annotate("участник: ниже перил\nпо течению, лицом к течению", (px, py), (4.6, 4.05), fontsize=14,
                color=INK, arrowprops=dict(arrowstyle="-", color=INK, lw=1.2))
    ax.plot([3.6], [0.95], "o", ms=14, color=NAVY)
    ax.text(2.6, 0.3, "страхующий с концом и ножом —\nниже входа по течению", fontsize=13.5, color=INK)
    ax.text(0.25, 2.75, "≈ 45°\nк течению", fontsize=15, color=INK, fontweight="bold")
    save(fig, "m11_diagonal")


if __name__ == "__main__":
    ladder()
    diagonal()
