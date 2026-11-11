"""Общее оформление презентаций курса «Школа альпинизма».

Модуль хранит палитру, раскладки слайдов и сборку PPTX. Данные конкретного модуля
(страницы пособия, вырезки рисунков, слайды и текст озвучки) лежат в build_alpNN_from_book.py.
Заметки к слайдам — готовый текст диктора, его же читает make_video.py.
"""

from __future__ import annotations

import io
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

FONT = "Arial"

DEEP = RGBColor(0x07, 0x1E, 0x30)
NAVY = RGBColor(0x0B, 0x2F, 0x4A)
PANEL = RGBColor(0x12, 0x3A, 0x5A)
GOLD = RGBColor(0xFF, 0xCF, 0x3F)
GREEN = RGBColor(0x7C, 0xC1, 0x4E)
RED = RGBColor(0xE5, 0x48, 0x4D)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ICE = RGBColor(0xC9, 0xDA, 0xE8)
MUTED = RGBColor(0x8F, 0xA8, 0xBC)

ROOT = Path(__file__).resolve().parent
UPLOADS = Path("/home/ubuntu/.cursor/projects/agent-repos-far-education/uploads")

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
PX_W, PX_H = 1920, 1080


@dataclass
class Slide:
    kind: str
    section: int = 0
    title: str = ""
    image: str = ""
    page: str = ""
    items: list[str] = field(default_factory=list)
    warning: str = ""
    caption: str = ""
    narration: str = ""
    extra: dict = field(default_factory=dict)
    origin: Module | None = None


@dataclass
class Module:
    """Всё, что отличает один модуль от другого.

    crops: имя → (страница книги, (x0, y0, x1, y1) в пунктах PDF от левого верхнего угла).
    page_offset: индекс страницы в PDF = страница книги + page_offset.
    """

    number: str
    out: Path
    pdf_env: str
    pdf_candidates: list[Path]
    page_offset: int
    crops: dict[str, tuple[int, tuple[float, float, float, float]]]
    photos: set[str]
    sections: dict[int, tuple[str, str, RGBColor]]
    slides: list[Slide]
    rotate: dict[str, int] = field(default_factory=dict)
    kicker: str = ""


def find_pdf(module: Module) -> Path:
    candidates = []
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".pdf"):
        candidates.append(Path(sys.argv[1]))
    if os.environ.get(module.pdf_env):
        candidates.append(Path(os.environ[module.pdf_env]))
    candidates.extend(module.pdf_candidates)
    for path in candidates:
        if path.is_file():
            return path
    raise SystemExit(
        f"Не найден PDF модуля {module.number}. Передайте путь аргументом или {module.pdf_env}."
    )


def crop_page(doc: pymupdf.Document, module: Module, name: str) -> Image.Image:
    book, (x0, y0, x1, y1) = module.crops[name]
    dpi = 300 if name in module.photos else 200
    page = doc[book + module.page_offset]
    pix = page.get_pixmap(dpi=dpi, clip=pymupdf.Rect(x0, y0, x1, y1), alpha=False)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    if name in module.rotate:
        im = im.rotate(module.rotate[name], expand=True)
    return im


def trim_margin(im: Image.Image, thresh: int = 247, pad: int = 10) -> Image.Image:
    """Срезает внешние почти белые поля. Внутренние просветы не трогает."""
    w, h = im.size
    px = im.load()

    def blank(xs, ys) -> bool:
        return all(min(px[x, y]) >= thresh for x in xs for y in ys)

    top = 0
    while top < h * 0.22 and blank(range(0, w, 4), [top]):
        top += 1
    bot = h - 1
    while bot > h * 0.78 and blank(range(0, w, 4), [bot]):
        bot -= 1
    left = 0
    while left < w * 0.18 and blank([left], range(0, h, 4)):
        left += 1
    right = w - 1
    while right > w * 0.82 and blank([right], range(0, h, 4)):
        right -= 1
    box = (max(0, left - pad), max(0, top - pad), min(w, right + pad + 1), min(h, bot + pad + 1))
    if box[2] - box[0] < 40 or box[3] - box[1] < 40:
        return im
    return im.crop(box)


def cover_px(im: Image.Image, w: int, h: int, ax=0.5, ay=0.5) -> Image.Image:
    scale = max(w / im.width, h / im.height)
    nw, nh = math.ceil(im.width * scale), math.ceil(im.height * scale)
    big = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = int((nw - w) * ax)
    top = int((nh - h) * ay)
    return big.crop((left, top, left + w, top + h))


def shade(im: Image.Image, side: str = "left", strength: float = 0.88, reach: float = 0.62) -> Image.Image:
    """Затемняет фото градиентом, чтобы поверх читался белый текст."""
    w, h = im.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    if side in ("left", "right"):
        stop = int(w * reach)
        for i in range(stop):
            t = 1 - i / stop
            x = i if side == "left" else w - 1 - i
            d.line([(x, 0), (x, h)], fill=int(255 * strength * (t ** 0.8)))
    else:
        start = int(h * (1 - reach))
        for y in range(start, h):
            t = (y - start) / (h - start)
            d.line([(0, y), (w, y)], fill=int(255 * strength * (t ** 0.9)))
    dark_rgb = Image.new("RGB", (w, h), (7, 30, 48))
    return Image.composite(dark_rgb, im, mask)


def to_stream(im: Image.Image, photo: bool) -> io.BytesIO:
    buf = io.BytesIO()
    if photo:
        im.save(buf, "JPEG", quality=86, optimize=True)
    else:
        im.save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf


def shape(slide, x, y, w, h, fill, kind=MSO_SHAPE.RECTANGLE, radius=None):
    shp = slide.shapes.add_shape(kind, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.line.fill.background()
    shp.shadow.inherit = False
    if radius is not None:
        shp.adjustments[0] = radius
    return shp


def text(slide, x, y, w, h, s, size, bold=False, color=WHITE, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, spacing=1.0):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    for i, line in enumerate(s.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        r = p.add_run()
        r.text = line
        r.font.name = FONT
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
    return box


def lines_needed(s: str, width_in: float, size: int) -> int:
    per_line = max(8, int(width_in * 72 / (size * 0.53)))
    words, lines, cur = s.split(), 1, 0
    for word in words:
        add = len(word) + (1 if cur else 0)
        if cur + add > per_line:
            lines += 1
            cur = len(word)
        else:
            cur += add
    return lines


def numbered(slide, x, y, w, items, accent, size=19, gap=0.28, color=WHITE, start=1):
    """Пункты с номером в цветном круге. Возвращает нижнюю границу."""
    dot = Inches(0.46)
    for i, item in enumerate(items, start=start):
        circle = shape(slide, x, y, dot, dot, accent, MSO_SHAPE.OVAL)
        tf = circle.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = str(i)
        r.font.name = FONT
        r.font.size = Pt(16)
        r.font.bold = True
        r.font.color.rgb = DEEP
        tx = x + dot + Inches(0.22)
        tw = w - dot - Inches(0.22)
        n = lines_needed(item, tw / 914400, size)
        th = Inches(n * size * 1.22 / 72)
        text(slide, tx, y + Inches(0.03), tw, th, item, size, False, color, spacing=1.05)
        y += max(th, dot) + Inches(gap)
    return y


class Builder:
    def __init__(self, module: Module):
        self.m = module
        self.total = len(module.slides)

    def is_photo(self, s: Slide) -> bool:
        return s.image in (s.origin or self.m).photos

    def sec(self, s: Slide):
        return self.m.sections[s.section]

    def label(self, slide, s: Slide, x=Inches(0.6), y=Inches(0.42)):
        num, name, accent = self.sec(s)
        shape(slide, x, y + Inches(0.04), Inches(0.08), Inches(0.26), accent)
        text(slide, x + Inches(0.2), y, Inches(8), Inches(0.34), f"{num}  ·  {name.upper()}", 13, True, accent)

    def source(self, slide, s: Slide, index: int, light=False):
        y = SLIDE_H - Inches(0.45)
        color = ICE if light else MUTED
        line = s.extra.get("src")
        if line is None and s.page:
            line = f"Пособие «Школа альпинизма», с. {s.page}"
        if line:
            text(slide, Inches(0.6), y, Inches(10), Inches(0.3), line, 11, False, color)
        text(slide, SLIDE_W - Inches(1.6), y, Inches(1.0), Inches(0.3), f"{index:02d} / {self.total}", 11, True,
             color, align=PP_ALIGN.RIGHT)

    def title(self, slide, s: Slide):
        self.label(slide, s)
        text(slide, Inches(0.6), Inches(0.82), Inches(12.2), Inches(0.7), s.title, 32, True, WHITE)

    def figure(self, slide, s: Slide, im: Image.Image, index):
        dark(slide)
        accent = self.sec(s)[2]
        self.title(slide, s)
        stream = to_stream(im, self.is_photo(s))
        aspect = im.width / im.height
        top = Inches(1.75)
        pad = Inches(0.16)
        if aspect >= 1.9:
            w, h = SLIDE_W - Inches(1.2), Inches(3.55)
            shape(slide, Inches(0.6), top, w, h, WHITE, MSO_SHAPE.ROUNDED_RECTANGLE, 0.03)
            fit_picture(slide, stream, im.size, Inches(0.6) + pad, top + pad, w - pad * 2, h - pad * 2)
            y = top + h + Inches(0.35)
            n = len(s.items)
            col_gap = Inches(0.3)
            col_w = (SLIDE_W - Inches(1.2) - col_gap * (n - 1)) // n
            for i, item in enumerate(s.items):
                numbered(slide, Inches(0.6) + i * (col_w + col_gap), y, col_w, [item], accent, size=17, start=i + 1)
        else:
            h = SLIDE_H - top - Inches(0.65)
            w = Inches(7.4)
            if s.extra.get("narrow"):
                w = min(w, int((h - pad * 2) * aspect) + pad * 2)
            shape(slide, Inches(0.6), top, w, h, WHITE, MSO_SHAPE.ROUNDED_RECTANGLE, 0.03)
            fit_picture(slide, stream, im.size, Inches(0.6) + pad, top + pad, w - pad * 2, h - pad * 2)
            tx = Inches(0.6) + w + Inches(0.5)
            tw = SLIDE_W - tx - Inches(0.6)
            numbered(slide, tx, top + Inches(0.15), tw, s.items, accent, size=19)
            if s.warning:
                warning(slide, tx, top + h - Inches(0.56), tw, s.warning)
        self.source(slide, s, index)

    def photo(self, slide, s: Slide, im: Image.Image, index):
        side = s.extra.get("side", "left")
        full_photo(slide, im, side, 0.9, 0.66)
        accent = self.sec(s)[2]
        x = Inches(0.6) if side == "left" else SLIDE_W - Inches(6.4)
        self.label(slide, s, x=x)
        text(slide, x, Inches(0.85), Inches(6.0), Inches(1.4), s.title, 36, True, WHITE, spacing=0.95)
        numbered(slide, x, Inches(2.75), Inches(5.6), s.items, accent, size=20, gap=0.32)
        if s.caption:
            text(slide, x, SLIDE_H - Inches(0.8), Inches(5.8), Inches(0.3), s.caption, 12, True, ICE)
        self.source(slide, s, index, light=True)

    def cover(self, slide, s: Slide, im: Image.Image):
        if s.extra.get("style") == "card":
            bg = cover_px(im, PX_W, PX_H).filter(ImageFilter.GaussianBlur(28))
            bg = shade(bg, "left", 0.95, 1.0)
            bright = sum(bg.convert("L").crop((PX_W // 2, 0, PX_W, PX_H)).resize((64, 36)).getdata()) / (64 * 36)
            if bright > 90:
                bg = ImageEnhance.Brightness(bg).enhance(90 / bright)
            slide.shapes.add_picture(to_stream(bg, True), 0, 0, SLIDE_W, SLIDE_H)
            cw, ch = Inches(5.4), Inches(5.4) * im.height // im.width
            cx, cy = SLIDE_W - cw - Inches(0.6), (SLIDE_H - ch) // 2 - Inches(0.2)
            border = Inches(0.08)
            shape(slide, cx - border, cy - border, cw + border * 2, ch + border * 2, WHITE,
                  MSO_SHAPE.ROUNDED_RECTANGLE, 0.02)
            slide.shapes.add_picture(to_stream(im, True), cx, cy, cw, ch)
            text(slide, cx, cy + ch + Inches(0.2), cw, Inches(0.3), s.caption, 12, True, ICE, align=PP_ALIGN.RIGHT)
            title_w = Inches(6.6)
        else:
            full_photo(slide, im, "left", 0.92, 0.72, ax=0.55)
            text(slide, SLIDE_W - Inches(4.6), SLIDE_H - Inches(0.5), Inches(4.0), Inches(0.3), s.caption, 11, False,
                 ICE, align=PP_ALIGN.RIGHT)
            title_w = Inches(7.2)
        shape(slide, Inches(0.6), Inches(0.75), Inches(0.9), Inches(0.07), GOLD)
        text(slide, Inches(0.6), Inches(1.0), Inches(7), Inches(0.4),
             self.m.kicker or f"ШКОЛА АЛЬПИНИЗМА  ·  МОДУЛЬ {int(self.m.number)}", 15, True, GOLD)
        size = s.extra.get("size", 66)
        text(slide, Inches(0.6), Inches(1.6), title_w, Inches(2.4), s.title, size, True, WHITE, spacing=0.92)
        lines = s.title.count("\n") + 1
        sub_y = max(Inches(4.05), Inches(1.85 + lines * size * 1.05 / 72))
        text(slide, Inches(0.6), sub_y, Inches(6.2), Inches(1.0), s.extra["subtitle"], 21, False, ICE, spacing=1.1)
        text(slide, Inches(0.6), Inches(6.35), Inches(7), Inches(0.6), s.extra["footer"], 12, False, ICE)

    def divider(self, slide, s: Slide, index):
        dark(slide)
        num, name, accent = self.sec(s)
        shape(slide, 0, 0, Inches(0.18), SLIDE_H, accent)
        text(slide, Inches(0.9), Inches(0.9), Inches(6), Inches(3.2), num, 190, True, accent)
        text(slide, Inches(0.95), Inches(3.75), Inches(7), Inches(0.4), "ЧАСТЬ", 15, True, MUTED)
        text(slide, Inches(0.95), Inches(4.1), Inches(7.5), Inches(2.0), name, 46, True, WHITE)
        y = Inches(1.6)
        for topic in s.extra["topics"]:
            shape(slide, Inches(8.2), y, Inches(4.5), Inches(1.15), PANEL, MSO_SHAPE.ROUNDED_RECTANGLE, 0.12)
            shape(slide, Inches(8.2), y, Inches(0.09), Inches(1.15), accent)
            text(slide, Inches(8.55), y, Inches(4.0), Inches(1.15), topic, 20, True, WHITE, anchor=MSO_ANCHOR.MIDDLE)
            y += Inches(1.4)
        self.source(slide, s, index)

    def chapter(self, slide, s: Slide, im: Image.Image, index):
        dark(slide)
        num, name, accent = self.sec(s)
        bar = Inches(0.9)
        fit_picture(slide, to_stream(im, True), im.size, 0, 0, SLIDE_W, SLIDE_H - bar)
        shape(slide, 0, SLIDE_H - bar, SLIDE_W, bar, DEEP)
        shape(slide, 0, SLIDE_H - bar, SLIDE_W, Inches(0.05), accent)
        text(slide, Inches(0.6), SLIDE_H - bar, Inches(6), bar, f"{num}  ·  {(s.title or name).upper()}", 15, True,
             accent, anchor=MSO_ANCHOR.MIDDLE)
        text(slide, Inches(5.2), SLIDE_H - bar, Inches(6.2), bar, f"{s.caption} · с. {s.page}", 12, False, ICE,
             align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        text(slide, SLIDE_W - Inches(1.6), SLIDE_H - bar, Inches(1.0), bar, f"{index:02d} / {self.total}", 11, True,
             MUTED, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)

    def numbers(self, slide, s: Slide, index):
        dark(slide)
        accent = self.sec(s)[2]
        self.title(slide, s)
        cards = s.extra["cards"]
        n = len(cards)
        gap = Inches(0.35)
        cw = (SLIDE_W - Inches(1.2) - gap * (n - 1)) // n
        y, h = Inches(2.0), Inches(4.1)
        big_size = s.extra.get("size", 40 if n <= 3 else 34)
        for i, (big, small) in enumerate(cards):
            x = Inches(0.6) + i * (cw + gap)
            shape(slide, x, y, cw, h, PANEL, MSO_SHAPE.ROUNDED_RECTANGLE, 0.06)
            shape(slide, x + Inches(0.4), y + Inches(0.5), Inches(0.7), Inches(0.07), accent)
            text(slide, x + Inches(0.4), y + Inches(0.85), cw - Inches(0.8), Inches(1.6), big, big_size, True, accent,
                 spacing=0.95)
            text(slide, x + Inches(0.4), y + Inches(2.55), cw - Inches(0.8), Inches(1.3), small, 20 if n <= 3 else 18,
                 False, WHITE, spacing=1.1)
        self.source(slide, s, index)

    def flags(self, slide, s: Slide, index):
        dark(slide)
        self.title(slide, s)
        flags = s.extra["flags"]
        stripe = s.extra.get("accent", RED)
        cols = 2
        rows = math.ceil(len(flags) / cols)
        gap_x, gap_y = Inches(0.3), Inches(0.16)
        cw = (SLIDE_W - Inches(1.2) - gap_x) // cols
        ch = Inches(0.62)
        top = Inches(1.75)
        for i, flag in enumerate(flags):
            c, r = divmod(i, rows)
            x = Inches(0.6) + c * (cw + gap_x)
            y = top + r * (ch + gap_y)
            shape(slide, x, y, cw, ch, PANEL, MSO_SHAPE.ROUNDED_RECTANGLE, 0.18)
            shape(slide, x, y, Inches(0.09), ch, stripe)
            text(slide, x + Inches(0.35), y, cw - Inches(0.5), ch, flag, 18, True, WHITE, anchor=MSO_ANCHOR.MIDDLE)
        cy = top + rows * (ch + gap_y) + Inches(0.15)
        shape(slide, Inches(0.6), cy, SLIDE_W - Inches(1.2), Inches(0.75), GOLD, MSO_SHAPE.ROUNDED_RECTANGLE, 0.2)
        text(slide, Inches(0.95), cy, SLIDE_W - Inches(1.9), Inches(0.75), s.extra["callout"], 19, True, DEEP,
             anchor=MSO_ANCHOR.MIDDLE)
        self.source(slide, s, index)

    def timeline(self, slide, s: Slide, index):
        """До шести дат: год крупно, под ним событие."""
        dark(slide)
        accent = self.sec(s)[2]
        self.title(slide, s)
        events = s.extra["events"]
        cols = 3
        rows = math.ceil(len(events) / cols)
        gap = Inches(0.3)
        cw = (SLIDE_W - Inches(1.2) - gap * (cols - 1)) // cols
        top = Inches(1.85)
        ch = (SLIDE_H - top - Inches(0.75) - gap * (rows - 1)) // rows
        for i, (year, what) in enumerate(events):
            r, c = divmod(i, cols)
            x = Inches(0.6) + c * (cw + gap)
            y = top + r * (ch + gap)
            shape(slide, x, y, cw, ch, PANEL, MSO_SHAPE.ROUNDED_RECTANGLE, 0.07)
            shape(slide, x, y, cw, Inches(0.07), accent)
            text(slide, x + Inches(0.35), y + Inches(0.28), cw - Inches(0.7), Inches(0.7), year, 34, True, accent)
            text(slide, x + Inches(0.35), y + Inches(1.0), cw - Inches(0.7), ch - Inches(1.1), what, 18, False, WHITE,
                 spacing=1.08)
        self.source(slide, s, index)

    def columns(self, slide, s: Slide, index):
        dark(slide)
        self.title(slide, s)
        self.column_cards(slide, s.extra["columns"], Inches(1.85), SLIDE_H - Inches(1.85) - Inches(0.75))
        self.source(slide, s, index)

    def terms(self, slide, s: Slide, index):
        """Карточки «термин — определение» в две колонки, до восьми штук."""
        dark(slide)
        accent = self.sec(s)[2]
        self.title(slide, s)
        terms = s.extra["terms"]
        cols = 2 if len(terms) > 3 else 1
        rows = math.ceil(len(terms) / cols)
        gap = Inches(0.22)
        top = Inches(1.75)
        cw = (SLIDE_W - Inches(1.2) - gap * (cols - 1)) // cols
        ch = (SLIDE_H - top - Inches(0.7) - gap * (rows - 1)) // rows
        size = s.extra.get("size", 16 if rows >= 4 else 17)
        for i, (term, meaning) in enumerate(terms):
            c, r = divmod(i, rows)
            x = Inches(0.6) + c * (cw + gap)
            y = top + r * (ch + gap)
            shape(slide, x, y, cw, ch, PANEL, MSO_SHAPE.ROUNDED_RECTANGLE, 0.08)
            shape(slide, x, y, Inches(0.08), ch, accent)
            box = text(slide, x + Inches(0.32), y, cw - Inches(0.55), ch, term, size + 3, True, accent,
                       anchor=MSO_ANCHOR.MIDDLE, spacing=1.05)
            p = box.text_frame.add_paragraph()
            p.line_spacing = 1.05
            r_ = p.add_run()
            r_.text = meaning
            r_.font.name = FONT
            r_.font.size = Pt(size)
            r_.font.color.rgb = WHITE
        self.source(slide, s, index)

    def column_cards(self, slide, cols, y, h, size=17):
        n = len(cols)
        gap = Inches(0.35)
        cw = (SLIDE_W - Inches(1.2) - gap * (n - 1)) // n
        for i, (head, accent, items) in enumerate(cols):
            x = Inches(0.6) + i * (cw + gap)
            shape(slide, x, y, cw, h, PANEL, MSO_SHAPE.ROUNDED_RECTANGLE, 0.06)
            shape(slide, x, y, cw, Inches(0.09), accent)
            text(slide, x + Inches(0.4), y + Inches(0.4), cw - Inches(0.8), Inches(0.5), head, 24, True, accent)
            numbered(slide, x + Inches(0.4), y + Inches(1.2), cw - Inches(0.7), items, accent, size=size, gap=0.22)

    def final(self, slide, s: Slide, index):
        dark(slide)
        shape(slide, Inches(0.6), Inches(0.6), Inches(0.9), Inches(0.07), GOLD)
        text(slide, Inches(0.6), Inches(0.85), Inches(12), Inches(0.8), s.title, 40, True, WHITE)
        self.column_cards(slide, s.extra["columns"], Inches(2.0), Inches(4.1))
        text(slide, Inches(0.6), Inches(6.45), Inches(11), Inches(0.4),
             "Урок не допуск, не квалификация и не официальный экзамен ФАР.", 14, True, GOLD)
        text(slide, SLIDE_W - Inches(1.6), SLIDE_H - Inches(0.45), Inches(1.0), Inches(0.3), f"{index:02d} / {self.total}",
             11, True, MUTED, align=PP_ALIGN.RIGHT)

    def build(self) -> Path:
        docs: dict[str, pymupdf.Document] = {}
        images: dict[tuple[str, str], Image.Image] = {}
        for s in self.m.slides:
            src = s.origin or self.m
            key = (src.number, s.image)
            if not s.image or key in images:
                continue
            if src.number not in docs:
                docs[src.number] = pymupdf.open(find_pdf(src))
            im = crop_page(docs[src.number], src, s.image)
            images[key] = im if s.image in src.photos else trim_margin(im)

        prs = Presentation()
        prs.slide_width = SLIDE_W
        prs.slide_height = SLIDE_H
        blank = prs.slide_layouts[6]
        for index, s in enumerate(self.m.slides, start=1):
            slide = prs.slides.add_slide(blank)
            im = images.get(((s.origin or self.m).number, s.image))
            if s.kind == "cover":
                self.cover(slide, s, im)
            elif s.kind == "divider":
                self.divider(slide, s, index)
            elif s.kind == "chapter":
                self.chapter(slide, s, im, index)
            elif s.kind == "photo":
                self.photo(slide, s, im, index)
            elif s.kind == "numbers":
                self.numbers(slide, s, index)
            elif s.kind == "flags":
                self.flags(slide, s, index)
            elif s.kind == "timeline":
                self.timeline(slide, s, index)
            elif s.kind == "columns":
                self.columns(slide, s, index)
            elif s.kind == "terms":
                self.terms(slide, s, index)
            elif s.kind == "final":
                self.final(slide, s, index)
            else:
                self.figure(slide, s, im, index)
            slide.notes_slide.notes_text_frame.text = s.narration
        prs.save(self.m.out)
        print(f"{self.total} slides -> {self.m.out}")
        return self.m.out


def build(module: Module) -> Path:
    return Builder(module).build()


def warning(slide, x, y, w, s):
    pill = shape(slide, x, y, w, Inches(0.56), RED, MSO_SHAPE.ROUNDED_RECTANGLE, 0.5)
    tf = pill.text_frame
    tf.margin_left = tf.margin_right = Inches(0.15)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = s
    r.font.name = FONT
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = WHITE


def dark(slide):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = DEEP


def full_photo(slide, im: Image.Image, side="left", strength=0.88, reach=0.62, ax=0.5, ay=0.5):
    bg = shade(cover_px(im, PX_W, PX_H, ax, ay), side, strength, reach)
    slide.shapes.add_picture(to_stream(bg, True), 0, 0, SLIDE_W, SLIDE_H)


def fit_picture(slide, stream, size, x, y, w, h):
    iw, ih = size
    scale = min(w / iw, h / ih)
    pw, ph = int(iw * scale), int(ih * scale)
    return slide.shapes.add_picture(stream, x + (w - pw) // 2, y + (h - ph) // 2, pw, ph)
