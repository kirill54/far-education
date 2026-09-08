# -*- coding: utf-8 -*-
"""Пересборка: /obuchenie/ и /attestaciya/ вместо лендингов по направлениям."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALP = ROOT / "alpinizm" / "index.html"
SKI = ROOT / "ski" / "index.html"
# после первого прогона alpinizm/ski становятся редиректами — берём снимки
if ALP.exists() and ALP.stat().st_size < 5000:
    for cand in (Path("/tmp/alpinizm.source.html"), ROOT / "sources" / "alpinizm.html"):
        if cand.exists():
            ALP = cand
            break
if SKI.exists() and SKI.stat().st_size < 5000:
    for cand in (Path("/tmp/ski.source.html"), ROOT / "sources" / "ski.html"):
        if cand.exists():
            SKI = cand
            break

TOPBAR = """<header style="position:fixed;top:0;left:0;right:0;z-index:60;background:rgba(255,255,255,.92);backdrop-filter:blur(12px);border-bottom:1px solid #e9edf1">
  <div style="background:#0b2f4a;color:#fff">
    <div style="max-width:1200px;margin:0 auto;padding:0 28px;display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:36px;flex-wrap:wrap">
      <div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap">
        <a href="./" style="padding:6px 11px;border-radius:7px;font-size:13px;font-weight:600;color:#fff;background:rgba(255,255,255,.16)">Обучение</a>
        <a href="../attestaciya/" style="padding:6px 11px;border-radius:7px;font-size:13px;font-weight:500;color:rgba(255,255,255,.78)">Аттестация</a>
      </div>
      <div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;margin-left:auto">
        <span style="font-size:12px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;opacity:.75;margin-right:6px">Направление</span>
        <button type="button" class="track-btn is-on" data-track="alpinizm">Альпинизм и ГТ</button>
        <button type="button" class="track-btn" data-track="ski">Ски-альпинизм</button>
      </div>
    </div>
  </div>
  <div style="max-width:1200px;margin:0 auto;padding:0 28px">
    <nav style="display:flex;align-items:center;gap:22px;min-height:64px;flex-wrap:nowrap">"""

TRACK_CSS = """<style id="track-switch">
.track-btn{appearance:none;border:0;cursor:pointer;padding:6px 11px;border-radius:7px;font-size:13px;font-weight:500;color:rgba(255,255,255,.78);background:transparent;font-family:inherit}
.track-btn.is-on{font-weight:600;color:#fff;background:rgba(255,255,255,.16)}
</style>
"""

TRACK_JS = r"""<script id="track-switch-js">
(function(){
  var tracks = {
    alpinizm: {
      title: "Обучение · Альпинизм и горный туризм · ФАР",
      h1: "Инструктор-проводник по альпинизму и горному туризму",
      lead: "Федерация альпинизма России объявляет набор на программу профессиональной переподготовки. Превратите опыт в профессию: систематизированные знания, практика в горах и официальная квалификация инструктора-проводника.",
      anonsH: "Набор на программу профессиональной переподготовки",
      anonsP: "Федерация альпинизма России приглашает целеустремлённых и опытных спортсменов пройти обучение и получить квалификацию инструктора-проводника.",
      who: "Спортсмены-альпинисты, горные туристы, действующие гиды без диплома, сотрудники МЧС и туриндустрии.",
      exp: "Подтверждённый опыт альпинизма или горного туризма: книжка альпиниста / горного туриста, справки.",
      qual: "Спортивный разряд по альпинизму / горному туризму, либо маршруты 2 к.с. (горный туризм) или 12 восхождений (альпинизм).",
      mod4: "Модуль 4. Методика и технология обучения в альпинизме и горном туризме",
      cta: "Сделайте первый шаг к новой профессиональной вершине",
      methHref: "../Методика_аттестации_альпинизм_горный_туризм.docx",
      methLabel: "Методика аттестации (альпинизм и горный туризм) — проект"
    },
    ski: {
      title: "Обучение · Ски-альпинизм и фрирайд · ФАР",
      h1: "Инструктор-проводник: ски-альпинизм и фрирайд",
      lead: "Направление Федерации альпинизма России по сопровождению на неподготовленных склонах: лавинная безопасность, тактика подъёма и спуска, управление группой во фрирайде и ски-туре, отдельный квалификационный экзамен.",
      anonsH: "Набор: ски-альпинизм и фрирайд на неподготовленных склонах",
      anonsP: "ФАР приглашает скитуристов, фрирайдеров и гидов пройти подготовку и аттестацию по подвиду «ски-альпинизм и фрирайд». Экзамен проводится отдельно от альпинизма и горного туризма.",
      who: "Скитуристы и фрирайдеры, инструкторы горнолыжных школ, гиды без аттестации по подвиду, специалисты туриндустрии и спасательных служб с зимним горным опытом.",
      exp: "Подтверждённый опыт ски-тура / фрирайда / ски-альпинизма: маршруты, дневники, справки.",
      qual: "Опыт движения вне трасс и работы с лавинным комплектом; требования к разряду / стажу — по перечню АК на сайте.",
      mod4: "Модуль: ски-альпинизм, фрирайд, лавинная безопасность на склонах",
      cta: "Запишитесь на направление ски-альпинизм и фрирайд",
      methHref: "../Методика_аттестации_ски_альпинизм_фрирайд.docx",
      methLabel: "Методика аттестации (ски-альпинизм и фрирайд) — проект"
    }
  };

  function apply(name){
    var t = tracks[name] || tracks.alpinizm;
    document.documentElement.setAttribute("data-track", name);
    document.title = t.title;
    var h1 = document.querySelector("h1");
    if (h1) h1.textContent = t.h1;
      var h1p = h1 && h1.nextElementSibling;
    if (h1p && h1p.tagName==="P") h1p.textContent = t.lead;
    var anonsH = document.querySelector("#anons h2");
    if (anonsH) anonsH.textContent = t.anonsH;
    var anonsP = document.querySelector("#anons h2 + p");
    if (anonsP) anonsP.textContent = t.anonsP;
    // requirement cards — first three text blocks after headings
    var req = document.querySelector("#trebovaniya");
    if (req) {
      var blocks = req.innerHTML;
      // targeted unique strings
    }
    var html = document.body.innerHTML;
    // safer: text nodes via unique current→new from both dictionaries
    swapText(tracks.alpinizm.who, t.who);
    swapText(tracks.ski.who, t.who);
    swapText(tracks.alpinizm.exp, t.exp);
    swapText(tracks.ski.exp, t.exp);
    swapText(tracks.alpinizm.qual, t.qual);
    swapText(tracks.ski.qual, t.qual);
    swapText(tracks.alpinizm.mod4, t.mod4);
    swapText(tracks.ski.mod4, t.mod4);
    swapText(tracks.alpinizm.cta, t.cta);
    swapText(tracks.ski.cta, t.cta);
    var meth = document.querySelector('a[href*="Методика_аттестации"]');
    if (meth) { meth.setAttribute("href", t.methHref); meth.textContent = t.methLabel; }
    document.querySelectorAll(".track-btn").forEach(function(b){
      b.classList.toggle("is-on", b.getAttribute("data-track")===name);
    });
    var heroAlp = document.getElementById("hero-img-alp");
    var heroSki = document.getElementById("hero-img-ski");
    if (heroAlp && heroSki) {
      heroAlp.style.display = name==="ski" ? "none" : "block";
      heroSki.style.display = name==="ski" ? "block" : "none";
    }
    try { history.replaceState(null, "", "#"+name); } catch(e){}
  }
  function swapText(from, to){
    if (!from || from===to) return;
    var w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
    var n;
    while (n = w.nextNode()) {
      if (n.nodeValue.indexOf(from) !== -1) n.nodeValue = n.nodeValue.split(from).join(to);
    }
  }
  document.addEventListener("click", function(e){
    var b = e.target.closest(".track-btn");
    if (!b) return;
    e.preventDefault();
    apply(b.getAttribute("data-track"));
  });
  var start = (location.hash||"").replace("#","") || "alpinizm";
  if (start!=="alpinizm" && start!=="ski") start = "alpinizm";
  if (document.readyState==="loading") document.addEventListener("DOMContentLoaded", function(){ apply(start); });
  else apply(start);
})();
</script>
"""


def extract_hero_src(html: str) -> str:
    imgs = re.findall(r'<img src="(data:image/webp;base64,[^"]+)"', html)
    if not imgs:
        raise SystemExit("hero webp not found")
    return imgs[0]


def build_obuchenie() -> None:
    html = ALP.read_text(encoding="utf-8")
    ski = SKI.read_text(encoding="utf-8")
    hero_alp = extract_hero_src(html)
    hero_ski = extract_hero_src(ski)

    html = re.sub(
        r'<header style="position:fixed;top:0;left:0;right:0;z-index:60;background:rgba\(255,255,255,\.92\);backdrop-filter:blur\(12px\);border-bottom:1px solid #e9edf1">\s*'
        r'<div style="background:#0b2f4a;color:#fff">.*?</div>\s*</div>\s*'
        r'<div style="max-width:1200px;margin:0 auto;padding:0 28px">\s*'
        r'<nav style="display:flex;align-items:center;gap:22px;min-height:64px;flex-wrap:nowrap">',
        TOPBAR,
        html,
        count=1,
        flags=re.S,
    )
    html = html.replace(
        '<a href="./" style="display:flex;align-items:center;gap:14px;flex-shrink:0">',
        '<a href="../" style="display:flex;align-items:center;gap:14px;flex-shrink:0">',
        1,
    )
    # dual hero: keep alpine visible, hide ski copy
    m = re.search(r'<img src="' + re.escape(hero_alp) + r'"[^>]*>', html)
    if not m:
        raise SystemExit("hero img tag not found")
    alp_tag = m.group(0).replace("<img ", '<img id="hero-img-alp" ', 1)
    ski_tag = (
        '<img id="hero-img-ski" src="' + hero_ski +
        '" alt="Ски-альпинизм и фрирайд" '
        'style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:none">'
    )
    html = html.replace(m.group(0), alp_tag + ski_tag, 1)
    # drop "отдельное направление" note that pointed to the other site
    html = re.sub(
        r'<p style="margin:0 0 22px;font-size:14\.5px;color:#626c78">Отдельное направление:.*?</p>\s*',
        "",
        html,
        count=1,
        flags=re.S,
    )
    html = html.replace(
        "<title>Альпинизм и горный туризм · Обучение инструкторов-проводников · ФАР</title>",
        "<title>Обучение · инструкторы-проводники · ФАР</title>",
    )
    if 'id="track-switch"' not in html:
        html = html.replace("</head>", TRACK_CSS + TRACK_JS + "</head>", 1)
    out = ROOT / "obuchenie"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")
    print("wrote obuchenie/index.html", (out / "index.html").stat().st_size)


REDIRECT = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Перенаправление · ФАР</title>
<link rel="canonical" href="{to}">
<meta http-equiv="refresh" content="0; url={to}">
<script>location.replace("{to}");</script>
</head>
<body>
<p><a href="{to}">Перейти на обновлённую страницу</a></p>
</body>
</html>
"""


def write_redirects() -> None:
    (ROOT / "alpinizm" / "index.html").write_text(
        REDIRECT.format(to="../obuchenie/#alpinizm"), encoding="utf-8"
    )
    (ROOT / "ski" / "index.html").write_text(
        REDIRECT.format(to="../obuchenie/#ski"), encoding="utf-8"
    )
    print("wrote redirects for /alpinizm/ and /ski/")


if __name__ == "__main__":
    build_obuchenie()
    write_redirects()
