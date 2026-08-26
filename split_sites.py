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

TRACK_NAV_ALP = (
        '<a class="dh-track" href="../" style="padding:9px 13px;border-radius:8px;color:#3b4650;'
        'font-weight:500;font-size:15px">Все направления</a>\n'
        '        <a href="./" style="padding:9px 13px;border-radius:8px;color:#fff;font-weight:600;'
        'font-size:15px;background:#1466a8">Альпинизм и ГТ</a>\n'
        '        <a class="dh-track" href="../ski/" style="padding:9px 13px;border-radius:8px;'
        'color:#3b4650;font-weight:500;font-size:15px">Ски-альпинизм</a>\n'
        '        <span style="width:1px;height:22px;background:#d5dbe1;margin:0 6px"></span>\n        '
)

TRACK_NAV_SKI = (
        '<a class="dh-track" href="../" style="padding:9px 13px;border-radius:8px;color:#3b4650;'
        'font-weight:500;font-size:15px">Все направления</a>\n'
        '        <a class="dh-track" href="../alpinizm/" style="padding:9px 13px;border-radius:8px;'
        'color:#3b4650;font-weight:500;font-size:15px">Альпинизм и ГТ</a>\n'
        '        <a href="./" style="padding:9px 13px;border-radius:8px;color:#fff;font-weight:600;'
        'font-size:15px;background:#0b2f4a">Ски-альпинизм</a>\n'
        '        <span style="width:1px;height:22px;background:#d5dbe1;margin:0 6px"></span>\n        '
)

NAV_DIV_RE = re.compile(
    r'(<div style="display:flex;align-items:center;gap:1px;margin-left:auto;flex-wrap:wrap">\s*)'
    r'(<a class="dh0")',
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


def inject_track_nav(html: str, track_nav: str) -> str:
    m = NAV_DIV_RE.search(html)
    if not m:
        raise SystemExit("Nav div not found — cannot inject track switcher")
    return NAV_DIV_RE.sub(m.group(1) + track_nav + m.group(2), html, count=1)


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
    html = inject_track_nav(html, TRACK_NAV_ALP)
    html = fix_asset_paths(html)
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
            "Подтверждённый опыт ски-тура / фрирайда / ски-альпинизма: маршруты, дневники, справки "
            "[уточняется АК].",
        ),
        (
            "Спортивный разряд по альпинизму / горному туризму, либо маршруты 2 к.с. (горный туризм) "
            "или 12 восхождений (альпинизм).",
            "Опыт движения вне трасс и работы с лавинным комплектом; требования к разряду / стажу "
            "— по перечню АК на сайте [уточняется].",
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

    html = inject_track_nav(html, TRACK_NAV_SKI)
    html = fix_asset_paths(html)
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
      radial-gradient(1200px 600px at 10% -10%, rgba(14,92,138,.18), transparent 55%),
      radial-gradient(900px 500px at 90% 0%, rgba(233,113,50,.14), transparent 50%),
      linear-gradient(180deg, #0b2f4a 0%, #0e5c8a 42%, #f5f7f9 42%, #f5f7f9 100%);
    -webkit-font-smoothing:antialiased}
  a{color:inherit;text-decoration:none}
  .wrap{max-width:1100px;margin:0 auto;padding:28px 24px 64px}
  header{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:48px}
  .brand{display:flex;align-items:center;gap:14px;color:#fff}
  .brand img{height:38px;width:auto;display:block;filter:brightness(0) invert(1)}
  .brand span{font-size:14px;opacity:.85;max-width:28ch;line-height:1.35}
  .top-link{color:#fff;font-weight:600;font-size:14.5px;padding:10px 16px;border-radius:10px;border:1px solid rgba(255,255,255,.35)}
  .top-link:hover{background:rgba(255,255,255,.12)}
  .hero{color:#fff;margin-bottom:36px;max-width:34em}
  .hero .eyebrow{font-size:13px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;opacity:.8;margin:0 0 12px}
  .hero h1{font-size:clamp(32px,5vw,48px);line-height:1.08;letter-spacing:-.03em;margin:0 0 16px;font-weight:700}
  .hero p{font-size:18px;line-height:1.55;margin:0;opacity:.92}
  .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}
  @media(max-width:820px){.grid{grid-template-columns:1fr}}
  .card{background:#fff;border-radius:18px;padding:28px 26px 24px;border:1px solid #e9edf1;
    box-shadow:0 18px 40px rgba(11,47,74,.08);display:flex;flex-direction:column;min-height:280px;
    transition:transform .2s ease, box-shadow .2s ease}
  .card:hover{transform:translateY(-3px);box-shadow:0 22px 48px rgba(11,47,74,.12)}
  .card .tag{display:inline-flex;align-self:flex-start;font-size:12px;font-weight:700;letter-spacing:.03em;
    padding:5px 10px;border-radius:999px;margin-bottom:14px}
  .card.alpine .tag{background:#e9f1f8;color:#0e5c8a}
  .card.ski .tag{background:#0b2f4a;color:#fff}
  .card h2{font-size:26px;letter-spacing:-.02em;margin:0 0 12px;line-height:1.2}
  .card p{color:#4a5560;font-size:16px;line-height:1.55;margin:0 0 18px;flex:1}
  .card ul{margin:0 0 22px;padding:0;list-style:none;color:#3b4650;font-size:14.5px}
  .card li{display:flex;gap:8px;margin-bottom:6px}
  .card li::before{content:"—";color:#1466a8;font-weight:700}
  .card .cta{display:inline-flex;align-items:center;gap:8px;padding:13px 20px;border-radius:11px;
    font-weight:600;font-size:15px;align-self:flex-start}
  .card.alpine .cta{background:#1466a8;color:#fff}
  .card.ski .cta{background:#0b2f4a;color:#fff}
  .card .cta:hover{filter:brightness(1.06)}
  footer{margin-top:40px;color:#626c78;font-size:14px;display:flex;flex-wrap:wrap;gap:12px 24px;justify-content:space-between}
  footer a{color:#1466a8;font-weight:600}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <a class="brand" href="./">
        <img src="LOGO_SRC" alt="Федерация альпинизма России" width="132" height="41">
        <span>Обучение и аттестация инструкторов-проводников</span>
      </a>
      <a class="top-link" href="alpinizm/#svedeniya">Сведения об организации</a>
    </header>

    <div class="hero">
      <p class="eyebrow">Федерация альпинизма России</p>
      <h1>Выберите направление</h1>
      <p>Два самостоятельных трека обучения и аттестации. Экзамен по ски-альпинизму и фрирайду проходит отдельно от альпинизма и горного туризма.</p>
    </div>

    <div class="grid">
      <a class="card alpine" href="alpinizm/">
        <span class="tag">Подвид маршрутов</span>
        <h2>Альпинизм и горный туризм</h2>
        <p>Скальный, снежно-ледовый и комбинированный рельеф, шортропинг, спасательные работы, программы ДПО и профобучения.</p>
        <ul>
          <li>Программы 256 ч и повышение квалификации</li>
          <li>Очный практикум в горах</li>
          <li>Методика аттестации по альпинизму / ГТ</li>
        </ul>
        <span class="cta">Перейти на сайт →</span>
      </a>

      <a class="card ski" href="ski/">
        <span class="tag">Неподготовленные склоны</span>
        <h2>Ски-альпинизм и фрирайд</h2>
        <p>Лавинная безопасность, тактика подъёма и спуска, сопровождение группы вне трасс, отдельный квалификационный экзамен.</p>
        <ul>
          <li>Отдельные билеты теории и практики</li>
          <li>Работа с бипером, щупом, лопатой</li>
          <li>Методика аттестации по ски / фрирайду</li>
        </ul>
        <span class="cta">Перейти на сайт →</span>
      </a>
    </div>

    <footer>
      <span>© 2024–2026 Федерация альпинизма России</span>
      <span><a href="mailto:dpo@alpfederation.ru">dpo@alpfederation.ru</a> · <a href="alpinizm/#dokumenty">Документы</a></span>
    </footer>
  </div>
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

    logo = extract_logo_src(original)
    hub = HUB.replace("LOGO_SRC", logo)
    SRC.write_text(hub, encoding="utf-8")
    print("wrote hub index.html", len(hub))

    copy_methodologies()
    print("done")


if __name__ == "__main__":
    main()
