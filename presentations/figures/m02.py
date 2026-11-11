"""Схемы модуля 2: где на леднике ждать трещины.

    python3 presentations/figures/m02.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Polygon  # noqa: E402

from common import GREEN, ICE, INK, MUTED, NAVY, RED, ROCK, SNOW, figure, save  # noqa: E402


def band(points, widths, n=200):
    """Полоса вдоль осевой линии: возвращает ось, нормали и края."""
    pts = np.array(points, float)
    t = np.linspace(0, 1, len(pts))
    s = np.linspace(0, 1, n)
    x = np.interp(s, t, pts[:, 0])
    y = np.interp(s, t, pts[:, 1])
    k = np.ones(15) / 15
    x = np.convolve(np.pad(x, 7, mode="edge"), k, "valid")
    y = np.convolve(np.pad(y, 7, mode="edge"), k, "valid")
    w = np.interp(s, np.linspace(0, 1, len(widths)), widths)
    dx, dy = np.gradient(x), np.gradient(y)
    ln = np.hypot(dx, dy)
    nx, ny = -dy / ln, dx / ln
    left = np.c_[x + nx * w, y + ny * w]
    right = np.c_[x - nx * w, y - ny * w]
    return np.c_[x, y], np.c_[nx, ny], w, left, right


def at(axis, norm, w, s, off):
    i = int(s * (len(axis) - 1))
    return axis[i] + norm[i] * w[i] * off, norm[i]


def crack(ax, p, d, length, color=NAVY, lw=3.2):
    d = np.array(d) / np.hypot(*d)
    a, b = p - d * length / 2, p + d * length / 2
    ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw, solid_capstyle="round")


def badge(ax, x, y, n):
    ax.add_patch(Circle((x, y), 0.32, fc=RED, ec="white", lw=2.5, zorder=5))
    ax.text(x, y - 0.01, str(n), ha="center", va="center", fontsize=19, fontweight="bold", color="white", zorder=6)


def crevasse_zones():
    fig = figure(10, 8)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.add_patch(Polygon([(0, 0), (10, 0), (10, 8), (0, 8)], fc="#e9e3dc", ec="none"))

    main = [(7.6, 7.3), (7.3, 6.2), (6.8, 5.0), (5.6, 4.0), (4.0, 3.4), (2.9, 2.4), (2.4, 1.0)]
    axis, norm, w, left, right = band(main, [1.35, 1.25, 1.05, 0.95, 0.9, 0.8, 0.55])
    trib = [(9.6, 5.9), (8.6, 5.0), (7.4, 4.3), (6.3, 3.9)]
    _, _, _, tl, tr = band(trib, [0.45, 0.45, 0.42, 0.4])
    for poly in (np.r_[tl, tr[::-1]], np.r_[left, right[::-1]]):
        ax.add_patch(Polygon(poly, fc=SNOW, ec=ROCK, lw=2.5, zorder=1))
    ax.add_patch(Polygon(np.r_[tl[-40:], tr[-40:][::-1]], fc=SNOW, ec="none", zorder=1.5))
    top = np.r_[left[:1], right[:1]]
    ax.plot(*np.c_[left[0], right[0]], color=ROCK, lw=7, solid_capstyle="round", zorder=2)
    ax.text(*(top.mean(0) + [0, 0.32]), "склон", ha="center", va="bottom", fontsize=14, color=MUTED)
    tongue = axis[-1]
    ax.add_patch(Polygon(np.r_[left[-25:], right[-25:][::-1]], fc=ICE, ec="none", alpha=0.6, zorder=1.6))
    ax.text(tongue[0], tongue[1] - 0.45, "язык", ha="center", va="top", fontsize=14, color=MUTED)

    # 5. Бергшрунд под склоном
    i = 6
    berg = np.r_[[left[i] * 0.85 + right[i] * 0.15], [axis[i] + [0, -0.08]], [right[i] * 0.85 + left[i] * 0.15]]
    ax.plot(berg[:, 0], berg[:, 1], color=NAVY, lw=4, zorder=3)
    badge(ax, axis[i][0] - 1.7, axis[i][1] - 0.1, 5)

    # 1. Перегиб ложа — серии поперечных трещин
    for s in np.linspace(0.2, 0.32, 5):
        j = int(s * (len(axis) - 1))
        for off in (-0.55, 0.0, 0.55):
            p, nrm = at(axis, norm, w, s, off)
            crack(ax, p, nrm, w[j] * 0.45)
    p, _ = at(axis, norm, w, 0.26, -1.0)
    badge(ax, p[0] + 0.55, p[1], 1)

    # 2. Внешний край поворота
    for s in np.linspace(0.47, 0.6, 5):
        j = int(s * (len(axis) - 1))
        p, nrm = at(axis, norm, w, s, 0.62)
        crack(ax, p, nrm, w[j] * 0.55)
    p, _ = at(axis, norm, w, 0.54, 1.0)
    badge(ax, p[0] - 0.25, p[1] + 0.5, 2)

    # 3. Краевые — косо у бортов
    for s in np.linspace(0.68, 0.84, 5):
        j = int(s * (len(axis) - 1))
        tang = np.array([norm[j][1], -norm[j][0]])
        for side in (1, -1):
            p, nrm = at(axis, norm, w, s, 0.72 * side)
            crack(ax, p, nrm * side + tang * 0.9, w[j] * 0.45, lw=2.8)
    p, _ = at(axis, norm, w, 0.76, -1.0)
    badge(ax, p[0] + 0.55, p[1] - 0.2, 3)

    # 4. Слияние ледников
    for k, off in enumerate((-0.35, 0.0, 0.35)):
        p, nrm = at(axis, norm, w, 0.44 + 0.02 * k, 0.15 + off)
        crack(ax, p + [0.35, -0.25], [1, 0.25], 0.5)
    badge(ax, 7.9, 3.75, 4)

    # Безопасная линия ближе к внутренней стороне поворота
    route = np.array([at(axis, norm, w, s, -0.45 + 0.1 * np.sin(s * 6))[0] for s in np.linspace(0.36, 0.96, 30)])
    ax.plot(route[:, 0], route[:, 1], color=GREEN, lw=3.5, ls=(0, (2, 1.5)), zorder=4)
    ax.text(route[-1][0] - 0.3, route[-1][1] + 0.1, "путь", ha="right", va="center", fontsize=15, color=GREEN,
            fontweight="bold")

    ax.add_patch(FancyArrowPatch((8.9, 7.3), (8.5, 6.0), arrowstyle="-|>", mutation_scale=28, lw=3, color=MUTED))
    ax.text(9.05, 6.65, "течение\nльда", ha="left", va="center", fontsize=14, color=MUTED)
    ax.text(0.3, 7.6, "Ледник в плане", ha="left", va="top", fontsize=20, fontweight="bold", color=INK)
    save(fig, "m02_crevasse_zones")


if __name__ == "__main__":
    crevasse_zones()
