"""Дополнительные схемы взамен мелких вырезок из книги: трещины, фронт, компас, пирамида."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Wedge, Circle, FancyArrowPatch

from common import BLUE, GOLD, GREEN, ICE, INK, MUTED, RED, ROCK, SNOW, figure, save


def crevasses():
    fig = figure(12, 7.2)
    ax = fig.add_axes((0.04, 0.06, 0.68, 0.82))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.set_title("Формы ледниковых трещин", loc="left", pad=8)

    def ice(x, y, w, h):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                    fc=ICE, ec=BLUE, lw=1.2))

    # 1 — изгиб
    ax.plot([0.4, 1.2, 2.2, 3.4], [5.2, 6.4, 6.7, 6.2], color=BLUE, lw=8, solid_capstyle="round")
    for i, xx in enumerate((0.7, 1.15, 1.6, 2.1, 2.6)):
        ax.plot([xx, xx + 0.05], [6.3 - i * 0.05, 5.3], color=INK, lw=1.4)
    ax.text(1.8, 4.7, "1  образование", ha="center", color=RED, fontsize=16, fontweight="bold")

    # 2 — открытые
    ice(4.3, 5.1, 1.1, 1.8)
    ice(5.7, 5.1, 1.1, 1.8)
    ax.add_patch(Polygon([(5.4, 5.1), (5.7, 6.9), (5.55, 6.9), (5.25, 5.1)], fc="white", ec="none"))
    ax.text(5.55, 4.7, "2  открытая", ha="center", color=RED, fontsize=16, fontweight="bold")

    # 3 — закрытая
    ice(7.6, 5.0, 3.2, 2.0)
    ax.add_patch(Polygon([(8.7, 5.0), (9.15, 6.2), (9.7, 5.0)], fc="#d9e7f2", ec=BLUE, lw=1))
    ax.plot([8.7, 9.15, 9.7], [7.0, 6.35, 7.0], color=SNOW, lw=10, solid_capstyle="round")
    ax.plot([8.7, 9.15, 9.7], [7.0, 6.35, 7.0], color=BLUE, lw=1.2)
    ax.text(9.2, 4.7, "3  закрытая мостом", ha="center", color=RED, fontsize=16, fontweight="bold")

    ax.text(0.3, 3.6, "Где ждать трещину", fontsize=18, fontweight="bold", color=INK, ha="left")
    for i, line in enumerate([
        "Внешняя сторона поворота ледника",
        "Перегиб и выпуклость ложа",
        "Край ледника и место слияния",
        "Ниже ледопада",
        "Полосы и провалы на снегу — закрытый мост",
    ]):
        ax.text(0.5, 3.0 - i * 0.55, "•  " + line, fontsize=16, color=INK, ha="left")
    return fig


def front():
    fig = figure(12, 6.6)
    ax = fig.add_axes((0.05, 0.08, 0.9, 0.78))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title("Холодный фронт: ветер до и после", loc="left")
    ax.add_patch(Polygon([(0.3, 0.4), (7.2, 0.4), (4.2, 4.6)], fc="#d7e6f5", ec=BLUE, lw=1.5))
    ax.add_patch(Polygon([(4.2, 4.6), (7.2, 0.4), (11.5, 0.4), (11.5, 5.2), (6.2, 5.2)], fc="#f8e2c4", ec=GOLD, lw=1.2))
    ax.annotate("", xy=(3.2, 1.2), xytext=(1.0, 1.2),
                arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=2.5))
    ax.text(1.6, 1.5, "после: запад\nи северо-запад", fontsize=14, color=BLUE, ha="center")
    ax.annotate("", xy=(10.6, 1.2), xytext=(8.4, 1.2),
                arrowprops=dict(arrowstyle="-|>", color="#c47b12", lw=2.5))
    ax.text(9.5, 1.55, "перед фронтом:\nюг и юго-запад", fontsize=14, color="#c47b12", ha="center")
    ax.text(2.2, 3.3, "холодный\nвоздух", fontsize=16, color=BLUE, ha="center", fontweight="bold")
    ax.text(9.4, 4.2, "тёплый воздух", fontsize=16, color="#c47b12", ha="center", fontweight="bold")
    ax.text(6.2, 0.05, "Кучевые башни и шквал — на линии фронта, не «за сутки».", fontsize=14, color=MUTED, ha="center")
    return fig


def compass():
    fig = figure(8, 8)
    ax = fig.add_axes((0.08, 0.08, 0.84, 0.8))
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.35, 1.25)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Планшетный компас", pad=6)
    ax.add_patch(FancyBboxPatch((-1.15, -0.7), 2.3, 1.15, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=SNOW, ec=MUTED, lw=1.5))
    ax.plot([-1.05, 1.05], [0.15, 0.15], color=RED, lw=2)
    ax.annotate("", xy=(1.05, 0.15), xytext=(0.7, 0.15),
                arrowprops=dict(arrowstyle="-|>", color=RED, lw=2))
    ax.text(0, -0.45, "линейка и стрелка направления", fontsize=13, ha="center", color=INK)
    ax.add_patch(Circle((0, 0.15), 0.42, fc="white", ec=INK, lw=2))
    ax.annotate("", xy=(0, 0.5), xytext=(0, 0.15),
                arrowprops=dict(arrowstyle="-|>", color=RED, lw=3))
    ax.plot([0, 0], [0.15, -0.2], color=MUTED, lw=3)
    ax.text(0, 0.62, "N", fontsize=16, fontweight="bold", color=RED, ha="center")
    for ang, lab in ((0, "С"), (90, "В"), (180, "Ю"), (270, "З")):
        import math
        # decorative only: cardinals around capsule
    ax.text(0, -1.05, "Север колбы совмещают со стрелкой.\nАзимут читают у стрелки направления.", fontsize=14,
            ha="center", color=INK)
    return fig


def pyramid():
    fig = figure(8, 7.2)
    ax = fig.add_axes((0.12, 0.08, 0.76, 0.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("Пирамида: много опасных ситуаций\nна одну тяжёлую травму", pad=8)
    levels = [
        (4.2, 8.6, 1.6, "1", "смерть"),
        (3.3, 6.9, 3.4, "20", "тяжёлых травм"),
        (2.4, 5.2, 5.2, "200", "лёгких травм"),
        (1.5, 3.5, 7.0, "2 000", "близко к травме"),
        (0.4, 1.6, 9.2, "200 000", "опасных ситуаций"),
    ]
    colors = ["#f6d0d4", "#f8e2c4", "#fff3c4", "#e7f2d8", "#d7e6f5"]
    for (x, y, w, num, label), c in zip(levels, colors):
        ax.add_patch(Polygon([(5 - w / 2, y), (5 + w / 2, y), (5 + w / 2 + 0.45, y + 1.45),
                              (5 - w / 2 - 0.45, y + 1.45)], fc=c, ec=INK, lw=1.3))
        ax.text(5, y + 0.85, f"{num}   {label}", ha="center", va="center", fontsize=15, color=INK, fontweight="bold")
    return fig


def main():
    for name, fn in (
        ("01_crevs", crevasses),
        ("02_front", front),
        ("02_compass", compass),
        ("02_pyramid", pyramid),
    ):
        path = save(fn(), name)
        print(path)


if __name__ == "__main__":
    main()
