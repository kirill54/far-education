"""Схемы к урокам 8.2 и 9.1. Свои рисунки, не копии из книг."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT8 = ROOT / "m08" / "figures"
OUT9 = ROOT / "m09" / "figures"

SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

INK = (28, 36, 48)
MUTED = (90, 102, 120)
PAPER = (244, 247, 251)
WHITE = (255, 255, 255)
LINE = (210, 220, 230)
ROCK = (186, 164, 140)
ROCK_D = (132, 110, 90)
GREEN = (27, 122, 64)
GREEN_BG = (232, 245, 236)
RED = (176, 48, 42)
RED_BG = (252, 234, 232)
ROPE = (36, 86, 158)
SLING = (36, 130, 72)
METAL = (96, 108, 124)
SNOW = (214, 224, 234)
ICE = (150, 196, 220)


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else SANS, size)


def wrap(draw, text, fnt, width):
    lines, cur = [], ""
    for word in text.split():
        trial = word if not cur else cur + " " + word
        if draw.textlength(trial, font=fnt) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def center(draw, text, y, fnt, fill, box):
    lines = wrap(draw, text, fnt, box[2] - box[0] - 36)
    h = sum(draw.textbbox((0, 0), line, font=fnt)[3] + 6 for line in lines)
    yy = y
    for line in lines:
        w = draw.textlength(line, font=fnt)
        draw.text((box[0] + (box[2] - box[0] - w) / 2, yy), line, font=fnt, fill=fill)
        yy += draw.textbbox((0, 0), line, font=fnt)[3] + 6
    return yy


def card(base, box, tone):
    bg = GREEN_BG if tone == "good" else RED_BG if tone == "bad" else WHITE
    edge = GREEN if tone == "good" else RED if tone == "bad" else LINE
    d = ImageDraw.Draw(base)
    d.rounded_rectangle(box, 28, fill=bg, outline=edge, width=3)
    return d


def tag(draw, xy, text, tone):
    fnt = font(28, True)
    fill = GREEN if tone == "good" else RED
    bg = (255, 255, 255)
    w = draw.textlength(text, font=fnt)
    x, y = xy
    draw.rounded_rectangle((x, y, x + w + 28, y + 46), 12, fill=bg, outline=fill, width=2)
    draw.text((x + 14, y + 6), text, font=fnt, fill=fill)


def carabiner(draw, cx, cy, scale=1.0, color=METAL, bg=WHITE):
    w, h = 22 * scale, 40 * scale
    draw.ellipse((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), outline=color, width=max(4, int(5 * scale)))
    draw.line((cx + w * 0.22, cy - h * 0.18, cx + w * 0.22, cy + h * 0.28), fill=color, width=max(3, int(4 * scale)))


def horn(draw, x, y, w, h):
    body = [(x, y + h), (x + w * 0.08, y + h * 0.42), (x + w * 0.55, y + h * 0.28),
            (x + w * 0.72, y + h * 0.05), (x + w, y + h * 0.22), (x + w * 0.78, y + h * 0.55),
            (x + w * 0.9, y + h)]
    draw.polygon(body, fill=ROCK)
    draw.line(body + [body[0]], fill=ROCK_D, width=3)


def new(w, h):
    im = Image.new("RGB", (w, h), PAPER)
    return im, ImageDraw.Draw(im)


def title(draw, text, w):
    f = font(40, True)
    tw = draw.textlength(text, font=f)
    draw.text(((w - tw) / 2, 28), text, font=f, fill=INK)


def sling_figure():
    w, h = 1500, 900
    im, d = new(w, h)
    title(d, "Петля на выступ", w)
    boxes = [(36, 100, 492, 850), (522, 100, 978, 850), (1008, 100, 1464, 850)]
    tones = ["good", "bad", "good"]
    heads = ["Корзина", "Лапка жаворонка", "Чтобы не сползла"]
    notes = [
        "Петля лежит на выступе двумя ветвями и работает всей шириной.",
        "Затянутая удавка забирает у петли до трёх четвертей прочности.",
        "Тяжёлый карабин тянет петлю вниз и не даёт ей уйти с выступа.",
    ]
    bgs = [GREEN_BG, RED_BG, GREEN_BG]
    for box, tone, head in zip(boxes, tones, heads):
        card(im, box, tone)
        d = ImageDraw.Draw(im)
        tag(d, (box[0] + 24, box[1] + 20), head, tone)
        horn(d, box[0] + 80, box[1] + 130, 300, 200)
    def basket(box, color, width, biner_scale, biner_color):
        top_l = (box[0] + 210, box[1] + 175)
        top_r = (box[0] + 300, box[1] + 188)
        low = (box[0] + 255, box[1] + 455)
        d.line([top_l, (box[0] + 175, box[1] + 390), low], fill=color, width=width, joint="curve")
        d.line([top_r, (box[0] + 345, box[1] + 390), low], fill=color, width=width, joint="curve")
        carabiner(d, low[0], low[1] + 36, biner_scale, biner_color)

    basket(boxes[0], SLING, 18, 1.35, METAL)
    # удавка пережимает петлю на самом выступе
    b = boxes[1]
    d.line([(b[0] + 230, b[1] + 175), (b[0] + 255, b[1] + 250)], fill=RED, width=18)
    d.line([(b[0] + 320, b[1] + 185), (b[0] + 275, b[1] + 250)], fill=RED, width=18)
    d.line([(b[0] + 255, b[1] + 250), (b[0] + 265, b[1] + 310)], fill=RED, width=6)
    d.polygon([(b[0] + 248, b[1] + 248), (b[0] + 282, b[1] + 248), (b[0] + 265, b[1] + 268)], fill=RED)
    d.line([(b[0] + 200, b[1] + 330), (b[0] + 255, b[1] + 455)], fill=RED, width=16)
    d.line([(b[0] + 340, b[1] + 330), (b[0] + 275, b[1] + 455)], fill=RED, width=16)
    carabiner(d, b[0] + 265, b[1] + 500, 1.35, RED)
    # тяжёлый карабин и стрелка сползания
    basket(boxes[2], SLING, 18, 1.85, METAL)
    b = boxes[2]
    d.line([(b[0] + 330, b[1] + 188), (b[0] + 410, b[1] + 188)], fill=RED, width=5)
    d.polygon([(b[0] + 410, b[1] + 176), (b[0] + 410, b[1] + 200), (b[0] + 432, b[1] + 188)], fill=RED)
    for box, note in zip(boxes, notes):
        center(ImageDraw.Draw(im), note, box[3] - 150, font(24), INK, box)
    im.save(OUT8 / "petlya.png", quality=95)


def crack(draw, x, y, w, h, narrow="down"):
    if narrow == "down":
        pts = [(x, y), (x + w, y), (x + w * 0.72, y + h), (x + w * 0.28, y + h)]
    elif narrow == "none":
        pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    else:
        pts = [(x + w * 0.18, y), (x + w * 0.82, y), (x + w, y + h), (x, y + h)]
    draw.polygon([(x - 80, y - 20), (x + w + 80, y - 20), (x + w + 80, y + h + 20), (x - 80, y + h + 20)], fill=ROCK)
    draw.polygon(pts, fill=(232, 236, 240))
    return pts


def nut(draw, x, y, w, h, color=(70, 78, 90)):
    draw.polygon([(x, y + h), (x + w * 0.2, y), (x + w * 0.8, y), (x + w, y + h)], fill=color)
    draw.line([(x + w / 2, y + h), (x + w / 2, y + h + 46)], fill=METAL, width=4)


def quickdraw_figure():
    w, h = 1500, 900
    im, d = new(w, h)
    title(d, "Верёвка не встёгивается в карабин закладки", w)
    boxes = [(40, 100, 730, 840), (770, 100, 1460, 840)]
    for box, tone, head in zip(boxes, ["bad", "good"], ["Плохо", "Через оттяжку"]):
        card(im, box, tone)
        d = ImageDraw.Draw(im)
        tag(d, (box[0] + 28, box[1] + 22), head, tone)
    b = boxes[0]
    crack(d, b[0] + 230, b[1] + 110, 200, 220, "down")
    nut(d, b[0] + 275, b[1] + 200, 110, 58)
    cy = b[1] + 400
    d.line([(b[0] + 330, b[1] + 258), (b[0] + 330, cy - 22)], fill=METAL, width=5)
    d.line([(b[0] + 70, cy), (b[0] + 250, cy + 28), (b[0] + 410, cy), (b[0] + 640, cy + 36)], fill=ROPE, width=12, joint="curve")
    carabiner(d, b[0] + 330, cy + 8, 1.35, RED, RED_BG)
    center(d, "Верёвка идёт в тот же карабин: она двигает закладку и может лечь на защёлку.", 690, font(26), INK, b)
    b = boxes[1]
    crack(d, b[0] + 230, b[1] + 90, 200, 190, "down")
    nut(d, b[0] + 275, b[1] + 160, 110, 54)
    y1 = b[1] + 300
    d.line([(b[0] + 330, b[1] + 214), (b[0] + 330, y1 - 24)], fill=METAL, width=5)
    carabiner(d, b[0] + 330, y1, 1.15, METAL, GREEN_BG)
    d.line([(b[0] + 300, y1 + 24), (b[0] + 300, y1 + 130), (b[0] + 360, y1 + 130), (b[0] + 360, y1 + 24)], fill=SLING, width=14, joint="curve")
    y2 = y1 + 168
    carabiner(d, b[0] + 330, y2, 1.25, METAL, GREEN_BG)
    d.line([(b[0] + 80, y2), (b[0] + 250, y2 + 30), (b[0] + 410, y2), (b[0] + 650, y2 + 24)], fill=ROPE, width=12, joint="curve")
    center(d, "Между закладкой и верёвкой — оттяжка. Движение верёвки до точки не доходит.", 700, font(26), INK, b)
    im.save(OUT8 / "ottyazhka.png", quality=95)


def opposition_figure():
    w, h = 1500, 780
    im, d = new(w, h)
    title(d, "Если щель не сужается", w)
    boxes = [(40, 110, 730, 720), (770, 110, 1460, 720)]
    for box, tone, head in zip(boxes, ["bad", "good"], ["Одна закладка", "Оппозиция"]):
        card(im, box, tone)
        d = ImageDraw.Draw(im)
        tag(d, (box[0] + 28, box[1] + 24), head, tone)
    b = boxes[0]
    crack(d, b[0] + 230, b[1] + 140, 200, 340, "none")
    nut(d, b[0] + 275, b[1] + 250, 110, 64)
    d.line([(b[0] + 330, b[1] + 360), (b[0] + 330, b[1] + 430)], fill=RED, width=6)
    d.polygon([(b[0] + 314, b[1] + 430), (b[0] + 346, b[1] + 430), (b[0] + 330, b[1] + 454)], fill=RED)
    center(d, "В параллельной щели одну закладку тянет вниз и вынимает.", 600, font(26), INK, b)
    b = boxes[1]
    crack(d, b[0] + 230, b[1] + 130, 200, 360, "none")
    nut(d, b[0] + 270, b[1] + 180, 100, 58)
    # second nut flipped: wide end down
    d.polygon([(b[0] + 275, b[1] + 390), (b[0] + 365, b[1] + 390), (b[0] + 345, b[1] + 448), (b[0] + 295, b[1] + 448)], fill=(70, 78, 90))
    d.line([(b[0] + 320, b[1] + 238), (b[0] + 520, b[1] + 300)], fill=SLING, width=8)
    d.line([(b[0] + 320, b[1] + 390), (b[0] + 520, b[1] + 340)], fill=SLING, width=8)
    carabiner(d, b[0] + 555, b[1] + 320, 1.15, METAL, GREEN_BG)
    # arrows toward each other
    d.line([(b[0] + 200, b[1] + 210), (b[0] + 200, b[1] + 280)], fill=GREEN, width=5)
    d.polygon([(b[0] + 188, b[1] + 280), (b[0] + 212, b[1] + 280), (b[0] + 200, b[1] + 304)], fill=GREEN)
    d.line([(b[0] + 560, b[1] + 430), (b[0] + 560, b[1] + 360)], fill=GREEN, width=5)
    d.polygon([(b[0] + 548, b[1] + 360), (b[0] + 572, b[1] + 360), (b[0] + 560, b[1] + 336)], fill=GREEN)
    center(d, "Две закладки стоят навстречу и держат друг друга.", 600, font(26), INK, b)
    im.save(OUT8 / "oppoziciya.png", quality=95)


def cams(draw, cx, cy, reach, color=(58, 68, 82)):
    """Кулачки влево и вправо. reach — насколько они выходят от оси."""
    draw.rounded_rectangle((cx - reach, cy - 24, cx - 6, cy + 16), 14, fill=color)
    draw.rounded_rectangle((cx + 6, cy - 24, cx + reach, cy + 16), 14, fill=color)
    draw.rectangle((cx - 6, cy - 8, cx + 6, cy + 72), fill=(32, 38, 48))
    draw.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=(230, 234, 238))


def cam_figure():
    w, h = 1560, 900
    im, d = new(w, h)
    title(d, "Френд держит в середине хода", w)
    # одна и та же ширина щели, разный ход кулачков
    specs = [
        (30, "bad", "Почти раскрыт", 58, "Кулачки раскрыты до предела и не достают до стен. Френд выпадет."),
        (400, "good", "Середина хода", 100, "Кулачки упираются в обе стены и ещё могут сжаться."),
        (770, "bad", "Зажат до упора", 60, "Кулачки зажаты в узкой щели. Поставить можно, вынуть трудно."),
    ]
    for x, tone, head, reach, note in specs:
        box = (x, 100, x + 350, 860)
        card(im, box, tone)
        d = ImageDraw.Draw(im)
        tag(d, (x + 16, 118), head, tone)
        width = 120 if "Зажат" in head else 200
        crack(d, x + 170 - width / 2, 230, width, 280, "none")
        cams(d, x + 170, 340, reach)
        center(d, note, 680, font(24), INK, box)
    box = (1140, 100, 1525, 860)
    card(im, box, "bad")
    d = ImageDraw.Draw(im)
    tag(d, (1156, 118), "Горизонталь", "bad")
    d.rounded_rectangle((1170, 300, 1495, 520), 12, fill=ROCK)
    d.rounded_rectangle((1190, 350, 1360, 470), 8, fill=(232, 236, 240))
    cy = 410
    d.rounded_rectangle((1240, cy - 58, 1288, cy - 6), 12, fill=(58, 68, 82))
    d.rounded_rectangle((1240, cy + 6, 1288, cy + 58), 12, fill=(58, 68, 82))
    d.rectangle((1258, cy - 6, 1425, cy + 6), fill=(32, 38, 48))
    d.line([(1425, cy), (1460, 640)], fill=RED, width=12)
    d.polygon([(1444, 618), (1476, 654), (1426, 646)], fill=RED)
    center(d, "Жёсткий стержень торчит наружу и при срыве работает рычагом.", 680, font(24), INK, box)
    im.save(OUT8 / "frend.png", quality=95)


def boot(draw, x, y, fill=(40, 48, 58)):
    draw.rounded_rectangle((x, y, x + 90, y + 36), 8, fill=fill)
    draw.polygon([(x + 8, y), (x + 48, y - 48), (x + 78, y - 20), (x + 70, y)], fill=fill)
    draw.rectangle((x - 4, y + 30, x + 98, y + 42), fill=(24, 28, 34))


def snow_figure():
    w, h = 1500, 860
    im, d = new(w, h)
    title(d, "Где снег, а где уже лёд", w)
    boxes = [(40, 100, 730, 800), (770, 100, 1460, 800)]
    for box in boxes:
        card(im, box, "neutral")
    d = ImageDraw.Draw(im)
    tag(d, (68, 122), "Снег", "good")
    tag(d, (798, 122), "Лёд", "bad")
    b = boxes[0]
    d.polygon([
        (b[0] + 70, b[1] + 530), (b[0] + 230, b[1] + 430),
        (b[0] + 230, b[1] + 392), (b[0] + 390, b[1] + 392),
        (b[0] + 640, b[1] + 230), (b[0] + 640, b[1] + 530),
    ], fill=SNOW, outline=METAL)
    boot(d, b[0] + 255, b[1] + 350)
    center(d, "Ступени рубятся, идти можно без кошек. В снегу по пояс лидера меняют часто: колею пробивать тяжелее всего.", 620, font(26), INK, b)
    b = boxes[1]
    d.polygon([(b[0] + 70, b[1] + 530), (b[0] + 640, b[1] + 230), (b[0] + 640, b[1] + 530)], fill=ICE, outline=(90, 130, 160))
    boot(d, b[0] + 270, b[1] + 359)
    for i in range(5):
        x = b[0] + 278 + i * 20
        d.polygon([(x, b[1] + 401), (x + 7, b[1] + 401), (x + 3, b[1] + 432)], fill=(24, 28, 34))
    center(d, "На льду без кошек не идут. Ледоруб остаётся при себе, как только склон может стать срывом.", 620, font(26), INK, b)
    im.save(OUT9 / "sneg-i-led.png", quality=95)


def main():
    OUT8.mkdir(parents=True, exist_ok=True)
    OUT9.mkdir(parents=True, exist_ok=True)
    sling_figure()
    quickdraw_figure()
    opposition_figure()
    cam_figure()
    snow_figure()
    print("ok")


if __name__ == "__main__":
    main()
