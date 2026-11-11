"""Общие детали уроков: класс Lesson и заготовки слайдов.

Слайды из библиотеки (A1, A2, A3 — презентации по главам пособия) берутся через take().
Уроки модуля NN описаны в units/mNN.py, собирает и проверяет их lessons.py.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from build_alp01_from_book import MODULE as A1
from build_alp02_from_book import MODULE as A2
from build_alp03_from_book import MODULE as A3
from deck import GOLD, GREEN, RED, ROOT, Module, Slide, build  # noqa: F401

OUT = ROOT / "lessons"


@dataclass
class Lesson:
    code: str
    slug: str
    sections: dict
    slides: list[Slide]

    @property
    def out(self) -> Path:
        major, minor = self.code.split(".")
        return OUT / f"M{int(major):02d}-{minor}_{self.slug}.pptx"

    def deck(self) -> Module:
        return Module(
            number=self.code,
            out=self.out,
            pdf_env="",
            pdf_candidates=[],
            page_offset=0,
            crops={},
            photos=set(),
            sections=self.sections,
            slides=self.slides,
            kicker=f"ШКОЛА АЛЬПИНИЗМА  ·  МОДУЛЬ {self.code.split('.')[0]}  ·  УРОК {self.code}",
        )


def take(src: Module, index: int, section: int, **changes) -> Slide:
    return replace(src.slides[index], section=section, origin=src, **changes)


def cover(src: Module | None, image: str, title: str, subtitle: str, caption: str, narration: str, size: int = 58) -> Slide:
    return Slide(
        "cover",
        title=title,
        image=image,
        caption=caption,
        narration=narration,
        origin=src,
        extra={
            "style": "card",
            "size": size,
            "subtitle": subtitle,
            "footer": "Схемы и фото — из пособия «Школа альпинизма».\n"
                      "Дополнения — из открытых источников. Не допуск и не аттестация.",
        },
    )


def divider(section: int, topics: list[str], narration: str) -> Slide:
    return Slide("divider", section=section, narration=narration, extra={"topics": topics})


def terms(section: int, title: str, pairs: list[tuple[str, str]], narration: str, src: str = "", **extra) -> Slide:
    return Slide("terms", section=section, title=title, narration=narration,
                 extra={"terms": pairs, "src": src or "Пособие «Школа альпинизма» и открытые источники", **extra})


def final(remember: list[str], nxt: list[str], live: list[str], narration: str) -> Slide:
    return Slide(
        "final",
        title="Главное из урока",
        narration=narration,
        extra={"columns": [("Запомнить", GOLD, remember), ("Дальше", GOLD, nxt), ("Только очно", RED, live)]},
    )


def one(name: str, accent=GOLD) -> dict:
    return {1: ("01", name, accent)}


SRC = "Пособие «Школа альпинизма» и открытые источники"


def numbers(section: int, title: str, cards: list[tuple[str, str]], narration: str, src: str = SRC, **extra) -> Slide:
    """Две–четыре карточки: крупно число или слово, под ним пояснение."""
    return Slide("numbers", section=section, title=title, narration=narration,
                 extra={"cards": cards, "src": src, **extra})


def columns(section: int, title: str, cols: list[tuple[str, object, list[str]]], narration: str,
            src: str = SRC) -> Slide:
    """Две–три колонки: (заголовок, цвет GOLD/GREEN/RED, 2–4 коротких пункта)."""
    return Slide("columns", section=section, title=title, narration=narration, extra={"columns": cols, "src": src})


def flags(section: int, title: str, items: list[str], callout: str, narration: str, src: str = SRC,
          accent=RED) -> Slide:
    """До десяти коротких признаков в две колонки и вывод на жёлтой плашке."""
    return Slide("flags", section=section, title=title, narration=narration,
                 extra={"flags": items, "callout": callout, "src": src, "accent": accent})


def timeline(section: int, title: str, events: list[tuple[str, str]], narration: str, src: str = SRC) -> Slide:
    """До шести шагов или дат: крупная метка и короткий текст."""
    return Slide("timeline", section=section, title=title, narration=narration, extra={"events": events, "src": src})
