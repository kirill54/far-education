#!/usr/bin/env python3
"""Презентация модуля 3: рисунки пособия «Школа альпинизма» и текст для озвучки.

Иллюстрации вырезаются со страниц 104–139 (главы 6 и 7) и не перерисовываются.
Заметки к слайдам — готовый текст диктора, его же читает make_alp03_video.py.

PDF ищется в таком порядке: аргумент командной строки, переменная ALP03_PDF,
затем типичные пути загрузки. Сам файл пособия в репозиторий не кладётся.
"""

from __future__ import annotations

import io
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw
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
OUT = ROOT / "ALP-03_laviny-naglyadno.pptx"

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
PX_W, PX_H = 1920, 1080

# book page, clip in PDF points (origin top-left)
CROPS: dict[str, tuple[int, tuple[float, float, float, float]]] = {
    "debris": (104, (0, 160, 468, 308)),
    "forces": (105, (236, 148, 428, 292)),
    "slab": (105, (240, 302, 428, 520)),
    "zones": (106, (68, 172, 405, 422)),
    "sizes": (107, (52, 28, 418, 270)),
    "wind": (108, (38, 92, 434, 252)),
    "tuyuksu": (108, (57, 256, 420, 478)),
    "cornice": (109, (48, 41, 411, 252)),
    "temp": (109, (90, 500, 380, 622)),
    "aspect": (110, (288, 468, 430, 628)),
    "angles": (111, (24, 240, 428, 434)),
    "convex": (112, (16, 252, 258, 400)),
    "bezengi": (112, (57, 406, 420, 601)),
    "anchors": (113, (46, 146, 414, 364)),
    "route": (114, (96, 398, 400, 628)),
    "time": (119, (36, 120, 432, 420)),
    "kit": (121, (40, 172, 424, 492)),
    "ch7": (122, (0, 0, 468, 292)),
    "sun": (131, (83, 233, 411, 427)),
    "lenin": (132, (57, 78, 420, 281)),
    "acclim": (134, (44, 318, 428, 622)),
    "elbrus": (135, (44, 348, 416, 624)),
}
PHOTOS = {"debris", "tuyuksu", "cornice", "bezengi", "ch7", "sun", "lenin"}

SECTIONS = {
    1: ("01", "Как рождается лавина", GOLD),
    2: ("02", "Погода", GOLD),
    3: ("03", "Рельеф", GOLD),
    4: ("04", "На маршруте", GOLD),
    5: ("05", "Высота", GREEN),
}


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


SLIDES: list[Slide] = [
    Slide(
        "cover",
        image="bezengi",
        page="112",
        caption="Лавина в Безенги, Кавказ",
        narration=(
            "Здравствуйте! Это третий модуль курса «Школа альпинизма». Он посвящён лавинам и тому, "
            "как высокогорная среда действует на человека. Все схемы и фотографии в этом уроке взяты "
            "из пособия «Школа альпинизма». Сразу важная оговорка. Урок объясняет, как замечать "
            "опасность и принимать решения. Поиску в лавине, зондированию, откапыванию и первой помощи "
            "по видео не научиться — это отрабатывают только на очных занятиях. Прохождение модуля не "
            "является допуском и не заменяет аттестацию."
        ),
    ),
    Slide(
        "divider",
        section=1,
        extra={"topics": ["Что такое лавина", "Слабый слой и «доска»", "Типы и размеры лавин"]},
        narration="Начнём с главного: что такое лавина и почему снег вообще срывается со склона.",
    ),
    Slide(
        "figure",
        section=1,
        title="Лавина — это не только огромный обвал",
        image="debris",
        page="104",
        items=[
            "Снег быстрее 1 м в минуту — уже лавина",
            "10 м³ снега могут убить",
            "Чаще гибнут в лавинах на 100–500 м³",
            "Чаще всего лавину запускает человек",
        ],
        narration=(
            "Лавиной называют любое движение снега вниз по склону быстрее одного метра в минуту. "
            "Специалисты считают лавиной объём от десяти кубометров — этого уже достаточно, чтобы "
            "травмировать или убить человека. Причём большинство несчастных случаев происходит не в "
            "гигантских лавинах, а в небольших — от ста до пятисот кубометров. И ещё одна важная мысль: "
            "большая часть лавинных происшествий с людьми случается по вине самих людей. А значит, на "
            "риск можно влиять — выбором цели, времени и пути."
        ),
    ),
    Slide(
        "figure",
        section=1,
        title="Снег держится, пока сцепление сильнее тяжести",
        image="forces",
        page="105",
        items=[
            "Снег лежит на склоне слоями",
            "Тяжесть постоянно тянет каждый слой вниз",
            "Где тяжесть победила сцепление — начинается разрушение",
        ],
        narration=(
            "Снег на склоне лежит не сплошной массой, а слоями. Каждый слой появляется в своё время: "
            "после снегопада, метели или ветра, из-за изморози или солнечной корки. На все слои "
            "действует сила тяжести. На схеме видно, как она раскладывается на сдвиг вдоль склона и "
            "сжатие, которое прижимает снег к склону. Чем круче склон, тем сильнее сдвиг. Пока "
            "сцепление удерживает снег, ничего не происходит. Но как только в каком-то месте тяжесть "
            "оказывается сильнее, начинается разрушение — и оно может пойти во все стороны."
        ),
    ),
    Slide(
        "figure",
        section=1,
        title="«Доска» отрывается по слабому слою",
        image="slab",
        page="105",
        items=[
            "Разрушение начинается на границе слоёв",
            "Трещина бежит по слабому слою, как домино",
            "«Вумпс» и просадка под ногами — сигнал тревоги",
        ],
        narration=(
            "Самое важное в этой теме — слабый слой. Разрушение обычно начинается не в толще снега, "
            "а на границе между слоями. Сначала рушится слабый слой, и только потом из склона "
            "вырезается доска. Внизу рисунка это показано как домино: стоит нагрузить склон в одном "
            "месте, и разрушение бежит дальше. Если под ногами раздаётся глухой звук «вумпс» или снег "
            "проседает — это и есть разрушение слабого слоя. Последствия серьёзные: от двадцати пяти "
            "до тридцати процентов попавших в лавину гибнут от травм, а из тех, кого засыпало "
            "полностью, выживает меньше половины."
        ),
    ),
    Slide(
        "photo",
        section=1,
        title="Так выглядит сошедшая «доска»",
        image="tuyuksu",
        page="108",
        caption="Туюксу, Заилийский Алатау",
        items=[
            "Ровная линия отрыва поперёк склона",
            "Снег ушёл пластом с большой площади",
            "Свежий сход рядом — «красный флаг»",
        ],
        narration=(
            "Вот как это выглядит в реальности. На фотографии — сошедшая доска в районе Туюксу, "
            "Заилийский Алатау. Обратите внимание на чёткую линию отрыва поперёк склона: снег ушёл не "
            "ручейком из одной точки, а целым пластом. Такие следы хорошо видны с соседних склонов. "
            "И если вы замечаете свежий сход рядом со своим маршрутом — это один из главных признаков "
            "опасности. О них мы поговорим чуть позже."
        ),
    ),
    Slide(
        "figure",
        section=1,
        title="Два типа лавин: от линии и из точки",
        image="zones",
        page="106",
        items=[
            "«Доска» (А) — много снега сразу, самая опасная",
            "Лавина из точки (Б) стартует медленно — из неё чаще уходят",
            "Мокрые лавины опаснее сухих",
        ],
        narration=(
            "По тому, как лавина начинается, их делят на два типа. Слева, под буквой А, — лавина от "
            "линии, та самая доска. В движение сразу приходит много снега на большой площади, "
            "выбраться из неё очень трудно, а блоки снега травмируют. На доски приходится большая часть "
            "несчастных случаев. Справа, под буквой Б, — лавина из точки. Она начинается с небольшого "
            "объёма и сначала движется медленно, поэтому из неё часто удаётся уйти. Цифрами отмечен "
            "путь лавины: зона зарождения, зона транзита и конус выноса. И запомните: при прочих "
            "равных мокрые лавины всегда опаснее сухих."
        ),
    ),
    Slide(
        "figure",
        section=1,
        title="Человеку опасен уже второй размер",
        image="sizes",
        page="107",
        items=[
            "Пять размеров — по массе и длине пути",
            "Размер 1 — относительно безвреден",
            "Размер 2 может засыпать и убить человека",
        ],
        narration=(
            "Есть и классификация по размеру — от первого до пятого. Лавина первого размера, около "
            "десяти тонн, относительно безвредна для людей. А второй размер — это уже около ста тонн "
            "снега и сто метров пути. Такая лавина может засыпать, травмировать или убить человека. "
            "Третий, четвёртый и пятый размеры разрушают машины, дома и целые участки леса. Вывод "
            "простой: для человека опасна уже небольшая лавина."
        ),
    ),
    Slide(
        "divider",
        section=2,
        extra={"topics": ["Снегопад", "Ветер и карнизы", "Температура, солнце и дождь"]},
        narration=(
            "Вторая часть — погода. Посмотрим, как снегопад, ветер, температура и солнце меняют "
            "устойчивость снега."
        ),
    ),
    Slide(
        "numbers",
        section=2,
        title="Снегопад: важно и сколько, и как быстро",
        page="107",
        extra={
            "cards": [
                ("30 см", "за сутки — заметно растёт риск схода"),
                ("1,5–2 см/ч", "критическая скорость снегопада"),
                ("20 см за часы", "опаснее метра снега за трое суток"),
            ]
        },
        narration=(
            "Свежий снег — это дополнительная нагрузка на склон. Считается, что если за сутки выпало "
            "больше тридцати сантиметров, вероятность схода лавин заметно растёт. Но важно не только "
            "сколько выпало, но и как быстро. Критической считают скорость снегопада от полутора до "
            "двух сантиметров в час. Поэтому двадцать сантиметров, выпавшие за несколько часов, могут "
            "быть опаснее метра снега, который шёл равномерно трое суток."
        ),
    ),
    Slide(
        "figure",
        section=2,
        title="Ветер перегружает подветренный склон",
        image="wind",
        page="108",
        items=[
            "Ветер переносит снег через хребет",
            "Следы: карнизы, заструги, сугробы",
            "Сильный перенос — уже с 5–7 м/с",
        ],
        narration=(
            "Ветер умеет переносить огромные массы снега. Посмотрите на правую схему: с наветренной "
            "стороны хребта снег выдувается, а с подветренной оседает и накапливается. Поэтому даже "
            "после небольшого снегопада подветренный склон может оказаться перегружен. Следы ветра "
            "легко заметить: карнизы, заструги, сугробы, снежные флаги на гребнях. В высоких горах "
            "сильный перенос снега начинается уже при ветре от пяти до семи метров в секунду, а в "
            "предгорьях — от трёх до четырёх."
        ),
    ),
    Slide(
        "photo",
        section=2,
        title="Карниз — след ветра и угроза сверху",
        image="cornice",
        page="109",
        caption="Пик Актру, Алтай",
        items=[
            "Карниз нависает над подветренным склоном",
            "Под ним обычно много надутого снега",
            "Обвал карниза может спустить лавину",
        ],
        narration=(
            "Это карнизы на пике Актру на Алтае. Карниз — прямое доказательство ветрового переноса: "
            "ветер перевалил снег через гребень и навесил его над склоном. Значит, склон под карнизом, "
            "скорее всего, перегружен. Кроме того, сам карниз может обрушиться и спустить лавину на "
            "тех, кто стоит ниже, — даже на пологом и, казалось бы, безопасном месте."
        ),
    ),
    Slide(
        "figure",
        section=2,
        title="Резкое потепление через ноль — опасно",
        image="temp",
        page="109",
        items=[
            "Резкое потепление выше нуля — опасность растёт",
            "Плавное потепление и ночной холод укрепляют снег",
            "Долгий мороз создаёт слабые слои",
        ],
        narration=(
            "Температура влияет на снег по-разному. На рисунке пять типичных сценариев. Сильное и "
            "быстрое потепление с переходом через ноль резко повышает опасность. Медленное потепление "
            "без перехода через ноль, а также тепло днём и холод ночью, наоборот, стабилизируют снег. "
            "Холодная погода консервирует ту ситуацию, что была. А долгий сильный мороз приводит к "
            "образованию слабых слоёв. Отдельно про солнце и дождь. Весной, когда солнце прогревает "
            "снег выше нуля, обстановка может измениться за считанные десятки минут. А дождь — всегда "
            "тревожный сигнал: вода нагружает склон и ослабляет сцепление снега."
        ),
    ),
    Slide(
        "divider",
        section=3,
        extra={"topics": ["Куда смотрит склон", "Крутизна и перегибы", "Что лежит под снегом"]},
        narration=(
            "Третья часть — рельеф. Куда смотрит склон, какой он крутизны и формы, и что на нём "
            "растёт. Помните: чем выше в горы, тем сильнее снегопады, ветер и солнце и тем сложнее "
            "рельеф. Поэтому самая высокая лавинная опасность обычно в высокогорной, альпийской зоне."
        ),
    ),
    Slide(
        "figure",
        section=3,
        title="Зимой опаснее восток и северо-восток",
        image="aspect",
        page="110",
        items=[
            "Оцениваем склон по солнцу и ветру",
            "Зимой безопаснее южные склоны, летом — северные",
            "Западные ветра сносят снег на восточные склоны",
        ],
        narration=(
            "Экспозиция — это то, куда смотрит склон. Оценивая её, задайте два вопроса: освещает ли "
            "склон солнце и с какой он стороны от ветра — наветренной или подветренной. Зимой при "
            "прочих равных самые комфортные склоны — южные, а весной и летом — северные. В горах "
            "умеренного пояса нашего полушария — на Кавказе, в Альпах, на Тянь-Шане — зимой опаснее "
            "всего северо-восточные и восточные склоны. Там преобладают западные ветра, и снег "
            "копится с подветренной стороны. Но это общее правило, и у него есть исключения."
        ),
    ),
    Slide(
        "figure",
        section=3,
        title="Чаще всего лавины сходят на 35–40°",
        image="angles",
        page="111",
        items=[
            "Большинство «досок» — на склонах 25–60°",
            "Пик несчастных случаев — около 38°",
            "Смотрите и на склон выше себя",
        ],
        narration=(
            "Крутизна — один из главных факторов. Большинство досок сходит на склонах от двадцати "
            "пяти до шестидесяти градусов. Но больше всего несчастных случаев — на склонах от "
            "тридцати пяти до сорока градусов, с пиком около тридцати восьми. На очень крутых склонах "
            "снег регулярно ссыпается и не успевает накопиться, а на пологих он устойчивее. Но лавины "
            "бывают и там, и там. И очень важно смотреть не только на угол под ногами, но и на склон "
            "выше: лавину можно запустить снизу, а сойдёт она сверху — прямо на вас."
        ),
    ),
    Slide(
        "figure",
        section=3,
        title="На перегибе снег рвётся первым",
        image="convex",
        page="112",
        items=[
            "На выпуклостях снег растянут и слабее",
            "Во впадинах снег сжат и устойчивее",
            "Опасные места видны по рельефу заранее",
        ],
        narration=(
            "Снег на склоне медленно сползает вниз и при этом взаимодействует с рельефом. На "
            "выпуклостях и перегибах он растягивается и становится менее устойчивым. Во впадинах, "
            "наоборот, сжимается и держится лучше. На схеме показана вероятная линия перелома — она "
            "проходит как раз по выпуклости. Такие места напряжения привязаны к рельефу, их можно "
            "заметить заранее и обойти. Отдельные камни и кусты тоже создают точки напряжения: "
            "с нагрузкой отсюда может стартовать доска."
        ),
    ),
    Slide(
        "figure",
        section=3,
        title="Лес и камни держат снег, гладкий склон — нет",
        image="anchors",
        page="113",
        items=[
            "Трава и гладкие плиты — риск схода до земли",
            "Густой лес и крупные камни работают как якоря",
            "Поломанные деревья — след прошлых лавин",
        ],
        narration=(
            "Важно и то, на что лёг снег. Гладкие поверхности — скальные плиты, трава, заросли "
            "рододендрона — провоцируют лавины на всю толщину, до самой земли. Склоны с камнями, "
            "кустами и уступами гораздо безопаснее: эти неровности работают как якоря. На рисунке "
            "видно: редкие деревья почти не помогают, а густой лес держит снег лучше всего. Замечайте "
            "и следы прошлых лавин: поломанный лес внизу склона, деревья, наклонённые вниз, наледь на "
            "стволах со стороны горы. Если видите такое — лучше обойти это место."
        ),
    ),
    Slide(
        "divider",
        section=4,
        extra={"topics": ["Как проходить опасные места", "«Красные флаги»", "Время и снаряжение"]},
        narration=(
            "Четвёртая часть — поведение на маршруте. Как проходить опасные места, какие признаки "
            "нельзя пропускать и почему в лавине решают минуты."
        ),
    ),
    Slide(
        "figure",
        section=4,
        title="Опасное место — по одному, от укрытия к укрытию",
        image="route",
        page="114",
        items=[
            "Опасный участок проходим по одному",
            "Идём от одной безопасной зоны к другой",
            "Остальные следят за идущим",
        ],
        narration=(
            "Полностью обойти лавиноопасный рельеф удаётся не всегда, но риск можно сильно снизить. "
            "Очевидно опасные участки проходят по одному или с большой дистанцией. Движение строится "
            "от одной безопасной зоны к другой — это могут быть скалы, нависания, гребни. Пока один "
            "идёт, остальные стоят в безопасном месте и следят за ним. По возможности выбирайте "
            "гребни: если лавина сойдёт, снег уйдёт вниз из-под группы. А кулуары — естественные "
            "лавинные желоба и самые опасные места зимнего рельефа."
        ),
    ),
    Slide(
        "flags",
        section=4,
        title="«Красные флаги»: заметил — пересмотри план",
        page="118",
        extra={
            "flags": [
                "Сход лавин на соседних склонах",
                "Трещины в снежном покрове",
                "«Вумпс» и просадки снега",
                "Переход температуры через 0 °C",
                "Дождь",
                "Резкие перепады температуры",
                "Сильный ветровой перенос",
                "Сильный снегопад за сутки",
                "Плохой лавинный прогноз",
                "Плохие результаты тестов",
            ],
            "callout": "Даже 1–2 флага — повод быть осторожнее и, возможно, сменить план",
        },
        narration=(
            "Красные флаги — это явные признаки лавинной опасности. Естественный сход лавин на "
            "соседних склонах. Трещины в снежном покрове. Звук «вумпс» и просадки снега. Переход "
            "температуры через ноль, дождь, резкие перепады температуры. Сильный ветровой перенос и "
            "сильный снегопад за последние сутки. Плохой лавинный прогноз и плохие результаты снежных "
            "тестов. Если вы видите хотя бы один или два таких признака — нужна повышенная "
            "осторожность и, возможно, другой план. Не идите дальше по инерции."
        ),
    ),
    Slide(
        "figure",
        section=4,
        title="Под снегом счёт идёт на минуты",
        image="time",
        page="119",
        items=[
            "15 минут: живы 9 из 10",
            "20 минут: уже 4 из 10",
            "Успеть может только своя группа",
        ],
        warning="Поиск и откапывание — только очно",
        narration=(
            "Если человек попал под лавину, всё решает время. Среди тех, кто не получил смертельных "
            "травм, через пятнадцать минут под снегом живы девять из десяти. Через двадцать минут — "
            "уже только четверо из десяти. Спасатели со стороны за это время не успеют. Поэтому "
            "единственный реальный шанс — спасательные работы силами самой группы. Искать "
            "пострадавшего, зондировать и откапывать учатся на практике, с инструктором. По видео "
            "этот навык не освоить."
        ),
    ),
    Slide(
        "figure",
        section=4,
        title="Датчик, щуп и лопата — у каждого",
        image="kit",
        page="121",
        items=[
            "Лавинный датчик, щуп и лопата — минимум",
            "Комплект нужен каждому, не один на группу",
            "Без навыка снаряжение не спасёт",
        ],
        warning="Пользоваться учатся на практике",
        narration=(
            "Минимальный набор для лавиноопасных склонов — лавинный датчик, щуп и лопата. Комплект "
            "нужен каждому участнику, а не один на всю группу. Если у засыпанного нет датчика, а у "
            "остальных нет щупов и лопат, драгоценные минуты уходят впустую. Но одного снаряжения "
            "мало: им нужно уметь пользоваться. Этому учатся на очных занятиях."
        ),
    ),
    Slide(
        "chapter",
        section=5,
        image="ch7",
        page="122",
        caption="«Райские ночевки», ущелье Адыр-су, Кавказ",
        narration=(
            "Последняя часть урока — о том, как горы действуют на человека. Холод, яркое солнце, "
            "сухой воздух и недостаток кислорода постепенно отнимают силы. Поговорим о солнце, горной "
            "болезни и акклиматизации."
        ),
    ),
    Slide(
        "figure",
        section=5,
        title="В горах солнце жёстче",
        image="sun",
        page="131",
        items=[
            "+15–20% радиации на каждые 1000 м",
            "Снег отражает до 80% лучей",
            "Крем SPF 50, очки не ниже 3-й категории",
        ],
        narration=(
            "В горах солнце гораздо опаснее, чем внизу. Солнечная радиация растёт на пятнадцать — "
            "двадцать процентов с каждой тысячей метров высоты, а снег отражает до восьмидесяти "
            "процентов лучей. Повторяющиеся ожоги повышают риск рака кожи, а без очков можно временно "
            "потерять зрение. Поэтому пользуйтесь кремом с фактором защиты пятьдесят и обновляйте его "
            "каждые два часа, а на снегу и весной — каждый час. Защищайте губы, носите шляпу с полями "
            "и закрытую одежду. И не выходите на снег и лёд без солнцезащитных очков — минимум третьей "
            "категории."
        ),
    ),
    Slide(
        "photo",
        section=5,
        title="Горная болезнь: у каждого по-своему",
        image="lenin",
        page="132",
        caption="Пик Ленина, 7134 м",
        items=[
            "Может начаться уже с 2000 м",
            "Головная боль, тошнота, слабость",
            "Реакция на высоту у всех разная",
        ],
        narration=(
            "Это пик Ленина, семь тысяч сто тридцать четыре метра. Чем выше, тем меньше кислорода "
            "получает организм. Из-за этого возникает горная болезнь: головная боль, тошнота, "
            "слабость. Она может начаться уже с высоты двух тысяч метров. Усугубляют её усталость, "
            "холод, обезвоживание, ультрафиолет и плохая погода. Важно понимать: реакция на высоту у "
            "всех разная, даже в одной группе. Она зависит от скорости набора высоты, тренированности, "
            "опыта и даже возраста. При отёке лёгких или мозга единственное надёжное средство — как "
            "можно быстрее спуститься вниз."
        ),
    ),
    Slide(
        "figure",
        section=5,
        title="Акклиматизация идёт пилой",
        image="acclim",
        page="134",
        items=[
            "Поднялись выше — спустились ниже ночевать",
            "Каждый выход — чуть выше прежнего",
            "Ночёвка — минимум на 1000 м ниже цели",
        ],
        narration=(
            "Организм может привыкнуть к высоте — это называется акклиматизацией. Обычно она "
            "занимает от недели до месяца. Схема простая: поднялись выше — спустились ниже на отдых, "
            "потом поднялись ещё выше — и снова вниз. На графике это похоже на пилу. Здесь показаны "
            "варианты для пика Ленина: для сильной, обычной и слабой группы. Считается, что во сне "
            "акклиматизация закрепляется лучше всего, поэтому перед вершиной нужна ночёвка минимум на "
            "тысячу метров ниже. Для пика Ленина это вершина Раздельная, шесть тысяч сто метров."
        ),
    ),
    Slide(
        "figure",
        section=5,
        title="Эльбрус: ускоренный график на 8 дней",
        image="elbrus",
        page="135",
        items=[
            "Дни 2–3: выходы до 3800 м",
            "Дни 4–5: ночёвка на 4100 м, выход до 5000 м",
            "День 6 — отдых, дни 7–8 — вершина 5642 м",
        ],
        narration=(
            "А это ускоренный график акклиматизации для Эльбруса. Первый день — приезд на поляну "
            "Азау. Второй и третий дни — выходы до трёх тысяч восьмисот метров и спуск. На четвёртый "
            "день — подъём до четырёх тысяч ста метров и ночёвка. На пятый — выход до пяти тысяч и "
            "спуск вниз. Шестой день — отдых. На седьмой снова ночёвка на четырёх тысячах ста, а на "
            "восьмой — восхождение на вершину, пять тысяч шестьсот сорок два метра, и спуск. Видите, "
            "та же пила. Но это ускоренный вариант, и график под конкретную группу выбирает "
            "руководитель."
        ),
    ),
    Slide(
        "final",
        title="Главное из модуля",
        extra={
            "columns": [
                ("Запомнить", GOLD, [
                    "Опасность — это снег, погода, рельеф и люди",
                    "«Красные флаги» — повод сменить план",
                    "На высоте каждый реагирует по-своему",
                ]),
                ("Дальше", GOLD, [
                    "Тест из шести вопросов",
                    "Рисунки — пособие, с. 104–139",
                ]),
                ("Только очно", RED, [
                    "Поиск в лавине и откапывание",
                    "Первая помощь",
                    "Техника на снегу и льду",
                ]),
            ]
        },
        narration=(
            "Подведём итог. Лавинная опасность складывается из снега, погоды, рельефа и действий "
            "людей. Красные флаги — повод пересмотреть план, а не идти дальше по инерции. На высоте "
            "каждый реагирует по-своему, а акклиматизация идёт пилой. Теперь пройдите тест из шести "
            "вопросов. И помните: этот урок не является допуском и не заменяет аттестацию. Поиск в "
            "лавине, первую помощь и технику на снегу и льду осваивают только на очных занятиях с "
            "инструктором. Спасибо и до встречи в следующем модуле!"
        ),
    ),
]


def find_pdf() -> Path:
    candidates = []
    if len(sys.argv) > 1:
        candidates.append(Path(sys.argv[1]))
    if os.environ.get("ALP03_PDF"):
        candidates.append(Path(os.environ["ALP03_PDF"]))
    candidates.extend(
        [
            Path("/home/ubuntu/.cursor/projects/agent-repos-far-education/uploads/ALP_Module_03__1__35db.pdf"),
            ROOT / "ALP_Module_03.pdf",
        ]
    )
    for path in candidates:
        if path.is_file():
            return path
    raise SystemExit("Не найден PDF модуля 3. Передайте путь аргументом или ALP03_PDF.")


def crop_page(doc: pymupdf.Document, name: str) -> Image.Image:
    book, (x0, y0, x1, y1) = CROPS[name]
    dpi = 300 if name in PHOTOS else 200
    pix = doc[book - 94].get_pixmap(dpi=dpi, clip=pymupdf.Rect(x0, y0, x1, y1), alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


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
    dark = Image.new("RGB", (w, h), (7, 30, 48))
    return Image.composite(dark, im, mask)


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


def label(slide, section: int, x=Inches(0.6), y=Inches(0.42), on_photo=False):
    num, name, accent = SECTIONS[section]
    shape(slide, x, y + Inches(0.04), Inches(0.08), Inches(0.26), accent)
    text(slide, x + Inches(0.2), y, Inches(8), Inches(0.34), f"{num}  ·  {name.upper()}", 13, True, accent)


def source(slide, page: str, index: int, total: int, light=False):
    y = SLIDE_H - Inches(0.45)
    color = ICE if light else MUTED
    if page:
        text(slide, Inches(0.6), y, Inches(8), Inches(0.3), f"Пособие «Школа альпинизма», с. {page}", 11, False, color)
    text(slide, SLIDE_W - Inches(1.6), y, Inches(1.0), Inches(0.3), f"{index:02d} / {total}", 11, True, color,
         align=PP_ALIGN.RIGHT)


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


def add_figure(slide, s: Slide, im: Image.Image, index, total):
    dark(slide)
    accent = SECTIONS[s.section][2]
    label(slide, s.section)
    text(slide, Inches(0.6), Inches(0.82), Inches(12.2), Inches(0.7), s.title, 32, True, WHITE)
    stream = to_stream(im, s.image in PHOTOS)
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
        w, h = Inches(7.4), SLIDE_H - top - Inches(0.65)
        shape(slide, Inches(0.6), top, w, h, WHITE, MSO_SHAPE.ROUNDED_RECTANGLE, 0.03)
        fit_picture(slide, stream, im.size, Inches(0.6) + pad, top + pad, w - pad * 2, h - pad * 2)
        tx = Inches(0.6) + w + Inches(0.5)
        tw = SLIDE_W - tx - Inches(0.6)
        numbered(slide, tx, top + Inches(0.15), tw, s.items, accent, size=19)
        if s.warning:
            warning(slide, tx, top + h - Inches(0.56), tw, s.warning)
    source(slide, s.page, index, total)


def fit_picture(slide, stream, size, x, y, w, h):
    iw, ih = size
    scale = min(w / iw, h / ih)
    pw, ph = int(iw * scale), int(ih * scale)
    return slide.shapes.add_picture(stream, x + (w - pw) // 2, y + (h - ph) // 2, pw, ph)


def add_photo(slide, s: Slide, im: Image.Image, index, total):
    side = s.extra.get("side", "left")
    full_photo(slide, im, side, 0.9, 0.66)
    accent = SECTIONS[s.section][2]
    x = Inches(0.6) if side == "left" else SLIDE_W - Inches(6.4)
    label(slide, s.section, x=x)
    text(slide, x, Inches(0.85), Inches(6.0), Inches(1.4), s.title, 36, True, WHITE, spacing=0.95)
    numbered(slide, x, Inches(2.75), Inches(5.6), s.items, accent, size=20, gap=0.32)
    if s.caption:
        text(slide, x, SLIDE_H - Inches(0.8), Inches(5.8), Inches(0.3), s.caption, 12, True, ICE)
    source(slide, s.page, index, total, light=True)


def add_cover(slide, s: Slide, im: Image.Image):
    full_photo(slide, im, "left", 0.92, 0.72, ax=0.55)
    shape(slide, Inches(0.6), Inches(0.75), Inches(0.9), Inches(0.07), GOLD)
    text(slide, Inches(0.6), Inches(1.0), Inches(7), Inches(0.4), "ШКОЛА АЛЬПИНИЗМА  ·  МОДУЛЬ 3", 15, True, GOLD)
    text(slide, Inches(0.6), Inches(1.6), Inches(7.2), Inches(2.4), "Лавины\nи высота", 66, True, WHITE, spacing=0.92)
    text(slide, Inches(0.6), Inches(4.05), Inches(6.2), Inches(1.0),
         "Как читать снег, погоду и рельеф —\nи как горы действуют на человека", 21, False, ICE, spacing=1.1)
    text(slide, Inches(0.6), Inches(6.35), Inches(7), Inches(0.6),
         "Схемы и фото — из пособия «Школа альпинизма», главы 6–7.\nНе допуск и не аттестация.", 12, False, ICE)
    text(slide, SLIDE_W - Inches(4.6), SLIDE_H - Inches(0.5), Inches(4.0), Inches(0.3), s.caption, 11, False, ICE,
         align=PP_ALIGN.RIGHT)


def add_divider(slide, s: Slide, index, total):
    dark(slide)
    num, name, accent = SECTIONS[s.section]
    shape(slide, 0, 0, Inches(0.18), SLIDE_H, accent)
    text(slide, Inches(0.9), Inches(0.9), Inches(6), Inches(3.2), num, 190, True, accent)
    text(slide, Inches(0.95), Inches(3.75), Inches(7), Inches(0.4), "ЧАСТЬ", 15, True, MUTED)
    text(slide, Inches(0.95), Inches(4.1), Inches(7.5), Inches(1.0), name, 46, True, WHITE)
    y = Inches(1.6)
    for topic in s.extra["topics"]:
        shape(slide, Inches(8.2), y, Inches(4.5), Inches(1.15), PANEL, MSO_SHAPE.ROUNDED_RECTANGLE, 0.12)
        shape(slide, Inches(8.2), y, Inches(0.09), Inches(1.15), accent)
        text(slide, Inches(8.55), y, Inches(4.0), Inches(1.15), topic, 20, True, WHITE, anchor=MSO_ANCHOR.MIDDLE)
        y += Inches(1.4)
    source(slide, "", index, total)


def add_chapter(slide, s: Slide, im: Image.Image, index, total):
    dark(slide)
    accent = SECTIONS[s.section][2]
    bar = Inches(0.9)
    fit_picture(slide, to_stream(im, True), im.size, 0, 0, SLIDE_W, SLIDE_H - bar)
    shape(slide, 0, SLIDE_H - bar, SLIDE_W, bar, DEEP)
    shape(slide, 0, SLIDE_H - bar, SLIDE_W, Inches(0.05), accent)
    text(slide, Inches(0.6), SLIDE_H - bar, Inches(6), bar, "05  ·  ВЫСОТА И ЧЕЛОВЕК", 15, True, accent,
         anchor=MSO_ANCHOR.MIDDLE)
    text(slide, Inches(5.2), SLIDE_H - bar, Inches(6.2), bar, f"{s.caption} · с. {s.page}", 12, False, ICE,
         align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    text(slide, SLIDE_W - Inches(1.6), SLIDE_H - bar, Inches(1.0), bar, f"{index:02d} / {total}", 11, True, MUTED,
         align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)


def add_numbers(slide, s: Slide, index, total):
    dark(slide)
    accent = SECTIONS[s.section][2]
    label(slide, s.section)
    text(slide, Inches(0.6), Inches(0.82), Inches(12.2), Inches(0.7), s.title, 32, True, WHITE)
    cards = s.extra["cards"]
    gap = Inches(0.35)
    cw = (SLIDE_W - Inches(1.2) - gap * 2) // 3
    y, h = Inches(2.0), Inches(4.1)
    for i, (big, small) in enumerate(cards):
        x = Inches(0.6) + i * (cw + gap)
        shape(slide, x, y, cw, h, PANEL, MSO_SHAPE.ROUNDED_RECTANGLE, 0.06)
        shape(slide, x + Inches(0.4), y + Inches(0.5), Inches(0.7), Inches(0.07), accent)
        text(slide, x + Inches(0.4), y + Inches(0.85), cw - Inches(0.8), Inches(1.6), big, 40, True, accent,
             spacing=0.95)
        text(slide, x + Inches(0.4), y + Inches(2.55), cw - Inches(0.8), Inches(1.3), small, 20, False, WHITE,
             spacing=1.1)
    source(slide, s.page, index, total)


def add_flags(slide, s: Slide, index, total):
    dark(slide)
    label(slide, s.section)
    text(slide, Inches(0.6), Inches(0.82), Inches(12.2), Inches(0.7), s.title, 32, True, WHITE)
    flags = s.extra["flags"]
    cols, rows = 2, 5
    gap_x, gap_y = Inches(0.3), Inches(0.16)
    cw = (SLIDE_W - Inches(1.2) - gap_x) // cols
    ch = Inches(0.62)
    top = Inches(1.75)
    for i, flag in enumerate(flags):
        c, r = divmod(i, rows)
        x = Inches(0.6) + c * (cw + gap_x)
        y = top + r * (ch + gap_y)
        shape(slide, x, y, cw, ch, PANEL, MSO_SHAPE.ROUNDED_RECTANGLE, 0.18)
        shape(slide, x, y, Inches(0.09), ch, RED)
        text(slide, x + Inches(0.35), y, cw - Inches(0.5), ch, flag, 18, True, WHITE, anchor=MSO_ANCHOR.MIDDLE)
    cy = top + rows * (ch + gap_y) + Inches(0.15)
    shape(slide, Inches(0.6), cy, SLIDE_W - Inches(1.2), Inches(0.75), GOLD, MSO_SHAPE.ROUNDED_RECTANGLE, 0.2)
    text(slide, Inches(0.95), cy, SLIDE_W - Inches(1.9), Inches(0.75), s.extra["callout"], 19, True, DEEP,
         anchor=MSO_ANCHOR.MIDDLE)
    source(slide, s.page, index, total)


def add_final(slide, s: Slide, index, total):
    dark(slide)
    shape(slide, Inches(0.6), Inches(0.6), Inches(0.9), Inches(0.07), GOLD)
    text(slide, Inches(0.6), Inches(0.85), Inches(12), Inches(0.8), s.title, 40, True, WHITE)
    cols = s.extra["columns"]
    gap = Inches(0.35)
    cw = (SLIDE_W - Inches(1.2) - gap * 2) // 3
    y, h = Inches(2.0), Inches(4.1)
    for i, (head, accent, items) in enumerate(cols):
        x = Inches(0.6) + i * (cw + gap)
        shape(slide, x, y, cw, h, PANEL, MSO_SHAPE.ROUNDED_RECTANGLE, 0.06)
        shape(slide, x, y, cw, Inches(0.09), accent)
        text(slide, x + Inches(0.4), y + Inches(0.4), cw - Inches(0.8), Inches(0.5), head, 24, True, accent)
        numbered(slide, x + Inches(0.4), y + Inches(1.2), cw - Inches(0.7), items, accent, size=17, gap=0.22)
    text(slide, Inches(0.6), Inches(6.45), Inches(11), Inches(0.4),
         "Урок не допуск, не квалификация и не официальный экзамен ФАР.", 14, True, GOLD)
    text(slide, SLIDE_W - Inches(1.6), SLIDE_H - Inches(0.45), Inches(1.0), Inches(0.3), f"{index:02d} / {total}",
         11, True, MUTED, align=PP_ALIGN.RIGHT)


def main() -> None:
    doc = pymupdf.open(find_pdf())
    images: dict[str, Image.Image] = {}
    for name in CROPS:
        im = crop_page(doc, name)
        images[name] = im if name in PHOTOS else trim_margin(im)

    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]
    total = len(SLIDES)
    for index, s in enumerate(SLIDES, start=1):
        slide = prs.slides.add_slide(blank)
        im = images.get(s.image)
        if s.kind == "cover":
            add_cover(slide, s, im)
        elif s.kind == "divider":
            add_divider(slide, s, index, total)
        elif s.kind == "chapter":
            add_chapter(slide, s, im, index, total)
        elif s.kind == "photo":
            add_photo(slide, s, im, index, total)
        elif s.kind == "numbers":
            add_numbers(slide, s, index, total)
        elif s.kind == "flags":
            add_flags(slide, s, index, total)
        elif s.kind == "final":
            add_final(slide, s, index, total)
        else:
            add_figure(slide, s, im, index, total)
        slide.notes_slide.notes_text_frame.text = s.narration
    prs.save(OUT)
    print(f"{total} slides -> {OUT}")


if __name__ == "__main__":
    main()
