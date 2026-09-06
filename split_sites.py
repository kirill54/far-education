# -*- coding: utf-8 -*-
"""
Делит лендинг far-education на:
  index.html          — хаб выбора трека
  alpinizm/index.html — альпинизм и горный туризм
  ski/index.html      — ски-альпинизм и фрирайд
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent if False else Path(
    r"C:\Users\Пользователь\ФАР\far-education"
)
# allow running from attestation or far-education
if not (ROOT / "index.html").exists():
    ROOT = Path(r"C:\Users\Пользователь\ФАР\far-education")

SRC = ROOT / "index.html"
ALP_DIR = ROOT / "alpinizm"
SKI_DIR = ROOT / "ski"

TOPBAR_ALP = '''<header style="position:fixed;top:0;left:0;right:0;z-index:60;background:rgba(255,255,255,.92);backdrop-filter:blur(12px);border-bottom:1px solid #e9edf1">
  <div style="background:#0b2f4a;color:#fff">
    <div style="max-width:1200px;margin:0 auto;padding:0 28px;display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:36px;flex-wrap:wrap">
      <span style="font-size:12px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;opacity:.75">Направление</span>
      <div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;margin-left:auto">
        <a href="../" style="padding:6px 11px;border-radius:7px;font-size:13px;font-weight:500;color:rgba(255,255,255,.78)">Все направления</a>
        <a href="./" style="padding:6px 11px;border-radius:7px;font-size:13px;font-weight:600;color:#fff;background:rgba(255,255,255,.16)">Альпинизм и ГТ</a>
        <a href="../ski/" style="padding:6px 11px;border-radius:7px;font-size:13px;font-weight:500;color:rgba(255,255,255,.78)">Ски-альпинизм</a>
      </div>
    </div>
  </div>
  <div style="max-width:1200px;margin:0 auto;padding:0 28px">
    <nav style="display:flex;align-items:center;gap:22px;min-height:64px;flex-wrap:nowrap">'''

TOPBAR_SKI = '''<header style="position:fixed;top:0;left:0;right:0;z-index:60;background:rgba(255,255,255,.92);backdrop-filter:blur(12px);border-bottom:1px solid #e9edf1">
  <div style="background:#0b2f4a;color:#fff">
    <div style="max-width:1200px;margin:0 auto;padding:0 28px;display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:36px;flex-wrap:wrap">
      <span style="font-size:12px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;opacity:.75">Направление</span>
      <div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;margin-left:auto">
        <a href="../" style="padding:6px 11px;border-radius:7px;font-size:13px;font-weight:500;color:rgba(255,255,255,.78)">Все направления</a>
        <a href="../alpinizm/" style="padding:6px 11px;border-radius:7px;font-size:13px;font-weight:500;color:rgba(255,255,255,.78)">Альпинизм и ГТ</a>
        <a href="./" style="padding:6px 11px;border-radius:7px;font-size:13px;font-weight:600;color:#fff;background:rgba(255,255,255,.16)">Ски-альпинизм</a>
      </div>
    </div>
  </div>
  <div style="max-width:1200px;margin:0 auto;padding:0 28px">
    <nav style="display:flex;align-items:center;gap:22px;min-height:64px;flex-wrap:nowrap">'''

HEADER_OPEN_RE = re.compile(
    r'<header style="position:fixed;top:0;left:0;right:0;z-index:60;background:rgba\(255,255,255,\.92\);backdrop-filter:blur\(12px\);border-bottom:1px solid #e9edf1">\s*'
    r'<div style="max-width:1200px;margin:0 auto;padding:0 28px">\s*'
    r'<nav style="display:flex;align-items:center;gap:22px;min-height:74px;flex-wrap:wrap">',
    re.S,
)


def fix_asset_paths(html: str) -> str:
    """Paths from subfolder: favicon, docx, mailto ok."""
    html = html.replace('href="favicon.ico"', 'href="../favicon.ico"')
    for name in (
        "ДПП_профпереподготовка_инструктор-проводник_по_Приказу-266_256ч.docx",
        "Программа_повышение_квалификации_72ч.docx",
        "ДПП_повышение_квалификации_первая_помощь_72ч.docx",
        "Методика_аттестации_альпинизм_горный_туризм.docx",
        "Методика_аттестации_ски_альпинизм_фрирайд.docx",
    ):
        html = html.replace(f'href="{name}"', f'href="../{name}"')
    html = html.replace('href="#top"', 'href="./"', 1)
    return html


def inject_track_nav(html: str, topbar: str) -> str:
    if not HEADER_OPEN_RE.search(html):
        raise SystemExit("Header open not found — cannot inject top track bar")
    html = HEADER_OPEN_RE.sub(topbar, html, count=1)
    html = html.replace(
        'style="display:flex;align-items:center;gap:1px;margin-left:auto;flex-wrap:wrap"',
        'style="display:flex;align-items:center;gap:0;margin-left:auto;flex-wrap:nowrap"',
        1,
    )
    html = html.replace(
        "align-items:center;padding:74px 0 84px",
        "align-items:center;padding:110px 0 84px",
        1,
    )
    return html


MOBILE_FIXES = '''<style id="mobile-fixes">
/* ==== Мобильная адаптация (поверх инлайновых стилей Claude Design) ==== */
img{max-width:100%;height:auto}
.nav-toggle{position:absolute!important;width:1px;height:1px;opacity:0;overflow:hidden;pointer-events:none;margin:0}
.nav-burger{display:none}
@media (max-width:820px){
  [style*="grid-template-columns:1.05fr .95fr"]{grid-template-columns:1fr!important;gap:28px!important}
  [style*="grid-template-columns:1.2fr 1fr 1fr"]{grid-template-columns:1fr!important;gap:22px!important}
}
@media (max-width:640px){
  html,body{overflow-x:hidden}
  [style*="text-transform:uppercase"]{white-space:normal!important;flex-wrap:wrap!important}
  [style*="display:inline-flex"]{max-width:100%!important}
  [style*="display:grid"]>*{min-width:0!important}
  [style*="minmax(340px"],[style*="minmax(330px"],[style*="minmax(300px"]{grid-template-columns:1fr!important}
  header[style*="position:fixed"]{position:static!important;backdrop-filter:none!important}
  div[style*="height:75px"]{display:none!important}
  [style*="max-width:1200px"]{padding-left:16px!important;padding-right:16px!important}
  section[style*="padding:88px 0"]{padding:46px 0!important}
  [style*="grid-template-columns:1.05fr .95fr"]{padding-top:22px!important;padding-bottom:48px!important}
  header nav{flex-wrap:wrap!important;gap:12px!important;min-height:56px!important;position:relative}
  .nav-burger{display:inline-flex!important;flex-direction:column;justify-content:center;gap:5px;width:46px;height:40px;padding:8px 11px;margin-left:auto;cursor:pointer;border-radius:9px;border:1px solid #e6eaee;background:#fff}
  .nav-burger span{display:block;height:2px;width:24px;background:#12161b;border-radius:2px;transition:transform .25s,opacity .2s}
  #nav-toggle:checked ~ .nav-burger span:nth-child(1){transform:translateY(7px) rotate(45deg)}
  #nav-toggle:checked ~ .nav-burger span:nth-child(2){opacity:0}
  #nav-toggle:checked ~ .nav-burger span:nth-child(3){transform:translateY(-7px) rotate(-45deg)}
  header nav>div{display:none!important;width:100%!important;order:3;flex-direction:column!important;align-items:stretch!important;gap:2px!important;margin:8px 0 6px!important;padding-top:10px!important;border-top:1px solid #eef1f4}
  #nav-toggle:checked ~ div{display:flex!important}
  header nav>div>a{padding:13px 12px!important;border-radius:10px!important;font-size:16px!important;margin-left:0!important}
  header nav>div>a[style*="background:#1466a8"],header nav>div>a[style*="background:#0b2f4a"]{color:#fff!important;text-align:center;margin-top:6px!important}
}
</style>
<script id="mobile-fixes-js">document.addEventListener("click",function(e){var a=e.target.closest("header nav > div a");if(a){var t=document.getElementById("nav-toggle");if(t)t.checked=false;}});</script>
'''


def inject_mobile(html: str) -> str:
    """Адаптив: бургер-меню + свёртка гридов. Идемпотентно."""
    html = re.sub(r'<style id="mobile-fixes">.*?</style>\n?', '', html, flags=re.S)
    html = re.sub(r'<script id="mobile-fixes-js">.*?</script>\n?', '', html, flags=re.S)
    links_div = '<div style="display:flex;align-items:center;gap:0;margin-left:auto;flex-wrap:nowrap">'
    burger = ('<input type="checkbox" id="nav-toggle" class="nav-toggle" aria-hidden="true">'
              '<label class="nav-burger" for="nav-toggle" aria-label="Меню"><span></span><span></span><span></span></label>')
    if 'id="nav-toggle"' not in html and links_div in html:
        html = html.replace(links_div, burger + links_div, 1)
    return html.replace("</head>", MOBILE_FIXES + "</head>", 1)


def make_alpine(html: str) -> str:
    html = html.replace(
        "<title>Обучение инструкторов-проводников · Федерация альпинизма России</title>",
        "<title>Альпинизм и горный туризм · Обучение инструкторов-проводников · ФАР</title>",
    )
    # subtle note under hero lead
    note = (
        '<p style="margin:0 0 22px;font-size:14.5px;color:#626c78">'
        "Отдельное направление: "
        '<a href="../ski/" style="color:#1466a8;font-weight:600;border-bottom:1px solid rgba(20,102,168,.35)">'
        "ски-альпинизм и фрирайд на неподготовленных склонах</a>.</p>"
    )
    html = html.replace(
        "официальная квалификация инструктора-проводника.</p>",
        "официальная квалификация инструктора-проводника.</p>\n        " + note,
        1,
    )
    # add methodology link in documents if section exists — append before closing of dokumenty list
    meth = (
        '<li style="display:flex;gap:10px;margin-bottom:9px;align-items:baseline">'
        '<span style="color:#1466a8;font-weight:700">—</span>'
        '<a class="doclink" href="../Методика_аттестации_альпинизм_горный_туризм.docx" target="_blank" rel="noopener">'
        "Методика аттестации (альпинизм и горный туризм) — проект</a>"
        '<span class="docbadge docx">DOCX</span></li>'
    )
    if "Методика_аттестации_альпинизм" not in html:
        html = html.replace(
            "Правила соотнесения количества инструкторов-проводников и туристов в группе (ФАР)</a>"
            '<span class="docbadge">PDF ↗</span></li>',
            "Правила соотнесения количества инструкторов-проводников и туристов в группе (ФАР)</a>"
            '<span class="docbadge">PDF ↗</span></li>\n        ' + meth,
            1,
        )
    html = inject_track_nav(html, TOPBAR_ALP)
    html = fix_asset_paths(html)
    html = inject_mobile(html)
    return html


def make_ski(html: str) -> str:
    html = html.replace(
        "<title>Обучение инструкторов-проводников · Федерация альпинизма России</title>",
        "<title>Ски-альпинизм и фрирайд · Обучение инструкторов-проводников · ФАР</title>",
    )

    replacements = [
        (
            "Инструктор-проводник по альпинизму и горному туризму",
            "Инструктор-проводник: ски-альпинизм и фрирайд",
        ),
        (
            "Федерация альпинизма России объявляет набор на программу профессиональной переподготовки. "
            "Превратите опыт в профессию: систематизированные знания, практика в горах и официальная "
            "квалификация инструктора-проводника.",
            "Направление Федерации альпинизма России по сопровождению на неподготовленных склонах: "
            "лавинная безопасность, тактика подъёма и спуска, управление группой во фрирайде и "
            "ски-туре, отдельный квалификационный экзамен.",
        ),
        (
            "Набор на программу профессиональной переподготовки",
            "Набор: ски-альпинизм и фрирайд на неподготовленных склонах",
        ),
        (
            "Федерация альпинизма России приглашает целеустремлённых и опытных спортсменов пройти "
            "обучение и получить квалификацию инструктора-проводника.",
            "ФАР приглашает скитуристов, фрирайдеров и гидов пройти подготовку и аттестацию "
            "по подвиду «ски-альпинизм и фрирайд». Экзамен проводится отдельно от альпинизма "
            "и горного туризма.",
        ),
        (
            "Спортсмены-альпинисты, горные туристы, действующие гиды без диплома, сотрудники МЧС и туриндустрии.",
            "Скитуристы и фрирайдеры, инструкторы горнолыжных школ, гиды без аттестации по подвиду, "
            "специалисты туриндустрии и спасательных служб с зимним горным опытом.",
        ),
        (
            "Подтверждённый опыт альпинизма или горного туризма: книжка альпиниста / горного туриста, справки.",
            "Подтверждённый опыт ски-тура / фрирайда / ски-альпинизма: маршруты, дневники, справки.",
        ),
        (
            "Спортивный разряд по альпинизму / горному туризму, либо маршруты 2 к.с. (горный туризм) "
            "или 12 восхождений (альпинизм).",
            "Опыт движения вне трасс и работы с лавинным комплектом; требования к разряду / стажу "
            "— по перечню АК на сайте.",
        ),
        (
            "Инструктор-проводник по альпинизму и горному туризму",
            "Инструктор-проводник (ски-альпинизм и фрирайд)",
        ),
        (
            "Модуль 4. Методика и технология обучения в альпинизме и горном туризме",
            "Модуль: ски-альпинизм, фрирайд, лавинная безопасность на склонах",
        ),
        (
            "Сделайте первый шаг к новой профессиональной вершине",
            "Запишитесь на направление ски-альпинизм и фрирайд",
        ),
    ]
    for a, b in replacements:
        html = html.replace(a, b)

    note = (
        '<p style="margin:0 0 22px;font-size:14.5px;color:#626c78">'
        "Смежное направление: "
        '<a href="../alpinizm/" style="color:#1466a8;font-weight:600;border-bottom:1px solid rgba(20,102,168,.35)">'
        "альпинизм и горный туризм</a>.</p>"
    )
    if "Смежное направление" not in html:
        html = html.replace(
            "отдельный квалификационный экзамен.</p>",
            "отдельный квалификационный экзамен.</p>\n        " + note,
            1,
        )

    # highlight ski methodology in documents
    meth = (
        '<li style="display:flex;gap:10px;margin-bottom:9px;align-items:baseline">'
        '<span style="color:#1466a8;font-weight:700">—</span>'
        '<a class="doclink" href="../Методика_аттестации_ски_альпинизм_фрирайд.docx" target="_blank" rel="noopener">'
        "Методика аттестации (ски-альпинизм и фрирайд) — проект</a>"
        '<span class="docbadge docx">DOCX</span></li>'
    )
    if "Методика_аттестации_ски" not in html:
        html = html.replace(
            "Правила соотнесения количества инструкторов-проводников и туристов в группе (ФАР)</a>"
            '<span class="docbadge">PDF ↗</span></li>',
            "Правила соотнесения количества инструкторов-проводников и туристов в группе (ФАР)</a>"
            '<span class="docbadge">PDF ↗</span></li>\n        ' + meth,
            1,
        )

    # programs blurb tweak near DPP card
    html = html.replace(
        "полный состав ДПП",
        "ДПП с модулем «Ски-альпинизм и фрирайд»; полный состав",
        1,
    )

    html = inject_track_nav(html, TOPBAR_SKI)
    html = fix_asset_paths(html)
    html = inject_mobile(html)
    return html


HUB = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Обучение инструкторов-проводников · Федерация альпинизма России</title>
<link rel="icon" type="image/x-icon" href="favicon.ico">
<meta name="description" content="Два направления аттестации и обучения инструкторов-проводников ФАР: альпинизм и горный туризм; ски-альпинизм и фрирайд на неподготовленных склонах.">
<style>
  @font-face{font-family:'Formular';src:local('Formular'),local('Formular-Regular');font-weight:400;font-display:swap}
  @font-face{font-family:'Formular';src:local('Formular Medium'),local('Formular-Medium');font-weight:500;font-display:swap}
  @font-face{font-family:'Formular';src:local('Formular Bold'),local('Formular-Bold');font-weight:700;font-display:swap}
  *{box-sizing:border-box}
  body{margin:0;min-height:100vh;color:#12161b;font-family:'Formular','Helvetica Neue',Arial,'Segoe UI',sans-serif;
    background:
      radial-gradient(1200px 600px at 10% -10%, rgba(14,92,138,.10), transparent 55%),
      radial-gradient(900px 500px at 90% 0%, rgba(233,113,50,.08), transparent 50%),
      linear-gradient(180deg, #f7f8fa 0%, #f5f7f9 100%);
    -webkit-font-smoothing:antialiased}
  a{color:inherit;text-decoration:none}
  .wrap{max-width:1100px;margin:0 auto;padding:28px 24px 8px}
  header{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:48px}
  .brand{display:flex;align-items:center;gap:14px;color:#12161b}
  .brand img{height:43px;width:auto;display:block}
  .brand span{font-size:14px;opacity:.85;max-width:28ch;line-height:1.35;color:#3b4650}
  .top-link{color:#0b2f4a;font-weight:600;font-size:14.5px;padding:10px 16px;border-radius:10px;border:1px solid #c5d0da}
  .top-link:hover{background:#e9f1f8}
  .hero{color:#12161b;margin-bottom:36px;max-width:34em}
  .hero .eyebrow{font-size:13px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:#0e5c8a;margin:0 0 12px}
  .hero h1{font-size:clamp(32px,5vw,48px);line-height:1.08;letter-spacing:-.03em;margin:0 0 16px;font-weight:700}
  .hero p{font-size:18px;line-height:1.55;margin:0;color:#4a5560}
  .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}
  @media(max-width:820px){.grid{grid-template-columns:1fr}}
  .card{background:#fff;border-radius:18px;padding:0 0 24px;border:1px solid #e9edf1;
    box-shadow:0 18px 40px rgba(11,47,74,.08);display:flex;flex-direction:column;min-height:280px;
    overflow:hidden;transition:transform .2s ease, box-shadow .2s ease}
  .card:hover{transform:translateY(-3px);box-shadow:0 22px 48px rgba(11,47,74,.12)}
  .card .preview{display:block;width:100%;height:280px;object-fit:cover;object-position:center 35%;background:#d8dee6}
  @media(max-width:820px){.card .preview{height:220px}}
  .card .body{padding:22px 26px 0;display:flex;flex-direction:column;flex:1}
  .card .tag{display:inline-flex;align-self:flex-start;font-size:12px;font-weight:700;letter-spacing:.03em;
    padding:5px 10px;border-radius:999px;margin-bottom:14px}
  .card.alpine .tag{background:#e9f1f8;color:#0e5c8a}
  .card.ski .tag{background:#0b2f4a;color:#fff}
  .card h2{font-size:26px;letter-spacing:-.02em;margin:0 0 16px;line-height:1.2}
  .card p{color:#4a5560;font-size:16px;line-height:1.55;margin:0 0 18px;flex:1}
  .card ul{margin:0 0 22px;padding:0;list-style:none;color:#3b4650;font-size:14.5px}
  .card li{display:flex;gap:8px;margin-bottom:6px}
  .card li::before{content:"—";color:#1466a8;font-weight:700}
  .card .cta{display:inline-flex;align-items:center;gap:8px;padding:13px 20px;border-radius:11px;
    font-weight:600;font-size:15px;align-self:flex-start}
  .card.alpine .cta{background:#1466a8;color:#fff}
  .card.ski .cta{background:#0b2f4a;color:#fff}
  .card .cta:hover{filter:brightness(1.06)}
  footer{margin-top:48px;padding:28px 24px 36px;background:linear-gradient(180deg,#0e5c8a 0%,#0b2f4a 100%);
    color:rgba(255,255,255,.82);font-size:14px}
  footer .inner{max-width:1100px;margin:0 auto;display:flex;flex-wrap:wrap;gap:12px 24px;justify-content:space-between}
  footer a{color:#fff;font-weight:600}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <a class="brand" href="./">
        <img src="logo-far.png" alt="Федерация альпинизма России" width="140" height="43">
      </a>
      <a class="top-link" href="alpinizm/#svedeniya">Сведения об организации</a>
    </header>

    <div class="hero">
      <p class="eyebrow">Обучение и аттестация инструкторов-проводников</p>
      <h1>Выберите направление</h1>
      <p>Два самостоятельных трека обучения и аттестации.</p>
    </div>

    <div class="grid">
      <a class="card alpine" href="alpinizm/">
        <img class="preview" src="preview-alpinizm.webp" alt="Практика на скальном рельефе" width="1080" height="720">
        <div class="body">
        <h2>Альпинизм и горный туризм</h2>
        <ul>
          <li>Методика аттестации и требования к кандидатам</li>
          <li>Дополнительное обучение: профпереподготовка и повышение квалификации</li>
        </ul>
        <span class="cta">Узнать подробнее</span>
        </div>
      </a>

      <a class="card ski" href="ski/">
        <img class="preview" src="preview-ski.webp" alt="Фрирайд на неподготовленном склоне" width="1080" height="720">
        <div class="body">
        <h2>Ски-альпинизм и фрирайд</h2>
        <ul>
          <li>Методика аттестации и требования к кандидатам</li>
          <li>Дополнительное обучение по ски-альпинизму и фрирайду</li>
        </ul>
        <span class="cta">Узнать подробнее</span>
        </div>
      </a>
    </div>

  </div>
  <footer>
    <div class="inner">
      <span>© 2024–2026 Федерация альпинизма России</span>
      <span><a href="mailto:dpo@alpfederation.ru">dpo@alpfederation.ru</a> · <a href="alpinizm/#dokumenty">Документы</a></span>
    </div>
  </footer>
</body>
</html>
"""


def extract_logo_src(html: str) -> str:
    m = re.search(r'<img src="(data:image/png;base64,[^"]+)" alt="Федерация альпинизма России"', html)
    if not m:
        raise SystemExit("Logo data URI not found")
    return m.group(1)


def copy_methodologies() -> None:
    src_dir = Path(
        r"C:\Users\Пользователь\ФАР\_context\ФАР_лендинг_передача\programs\attestation"
    )
    for name in (
        "Методика_аттестации_альпинизм_горный_туризм.docx",
        "Методика_аттестации_ски_альпинизм_фрирайд.docx",
    ):
        src = src_dir / name
        if src.exists():
            shutil.copy2(src, ROOT / name)
            print("copied", name)


def main() -> None:
    original = SRC.read_text(encoding="utf-8")
    # backup once
    bak = ROOT / "index.pre-split.html"
    if not bak.exists():
        bak.write_text(original, encoding="utf-8")
        print("backup:", bak.name)

    ALP_DIR.mkdir(exist_ok=True)
    SKI_DIR.mkdir(exist_ok=True)

    alpine = make_alpine(original)
    ski = make_ski(original)
    (ALP_DIR / "index.html").write_text(alpine, encoding="utf-8")
    (SKI_DIR / "index.html").write_text(ski, encoding="utf-8")
    print("wrote alpinizm/index.html", len(alpine))
    print("wrote ski/index.html", len(ski))

    SRC.write_text(HUB, encoding="utf-8")
    print("wrote hub index.html", len(hub))

    copy_methodologies()
    print("done")


if __name__ == "__main__":
    main()
