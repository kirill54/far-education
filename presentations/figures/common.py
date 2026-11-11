"""Общий стиль перерисованных схем: белый фон, палитра курса, шрифт с метрикой Arial.

Схема сохраняется в presentations/img/<имя>.png; deck.py берёт её вместо вырезки из книги,
если имя совпадает с именем вырезки (<модуль>_<имя>, например 03_time) или с полем image слайда.
Ширина 2400 px: на слайде схема занимает до 12 дюймов, этого хватает для чёткого текста.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

IMG = Path(__file__).resolve().parent.parent / "img"

INK = "#0c1b2a"
NAVY = "#13283e"
MUTED = "#6c8299"
GRID = "#d5dee7"
GOLD = "#f2b705"
GREEN = "#5a9e32"
RED = "#d63b47"
BLUE = "#2f7fc1"
ICE = "#b8d7ea"
SNOW = "#eef4f9"
ROCK = "#8a7f74"

WIDTH_PX = 2400

plt.rcParams.update({
    "font.family": ["Liberation Sans", "Arimo", "DejaVu Sans"],
    "font.size": 15,
    "text.color": INK,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "axes.titleweight": "bold",
    "axes.titlesize": 20,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})


def figure(w: float = 12, h: float = 6.75):
    """Холст в дюймах; соотношение по умолчанию 16:9."""
    return plt.figure(figsize=(w, h))


def save(fig, name: str) -> Path:
    IMG.mkdir(exist_ok=True)
    path = IMG / f"{name}.png"
    w_in = fig.get_size_inches()[0]
    fig.savefig(path, dpi=WIDTH_PX / w_in, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    return path
