(function () {
  const ALL = window.FAR_QUESTIONS || [];
  const home = document.getElementById("home");
  const quiz = document.getElementById("quiz");
  const done = document.getElementById("done");
  const optsEl = document.getElementById("opts");
  const timerEl = document.getElementById("timer");

  let pack = [];
  let i = 0;
  let score = 0;
  let locked = false;
  let tLeft = 0;
  let tick = null;
  let lastMode = "exam-alpine";

  function shuffle(arr) {
    const a = arr.slice();
    for (let k = a.length - 1; k > 0; k--) {
      const j = Math.floor(Math.random() * (k + 1));
      [a[k], a[j]] = [a[j], a[k]];
    }
    return a;
  }

  function poolFor(mode) {
    const track = mode === "exam-ski" ? "ski" : "alpine";
    return ALL.filter((q) => q.track === track);
  }

  function show(el) {
    home.classList.add("hidden");
    quiz.classList.add("hidden");
    done.classList.add("hidden");
    el.classList.remove("hidden");
  }

  function start(mode) {
    lastMode = mode;
    pack = shuffle(poolFor(mode)).slice(0, 25);
    i = 0;
    score = 0;
    locked = false;
    clearInterval(tick);
    tLeft = 60 * 60;
    tick = setInterval(function () {
      tLeft -= 1;
      renderTimer();
      if (tLeft <= 0) finish(true);
    }, 1000);
    show(quiz);
    render();
  }

  function renderTimer() {
    const m = Math.floor(tLeft / 60);
    const s = tLeft % 60;
    timerEl.textContent = m + ":" + String(s).padStart(2, "0");
    timerEl.classList.toggle("warn", tLeft < 5 * 60);
  }

  function render() {
    const q = pack[i];
    if (!q) {
      finish(false);
      return;
    }
    locked = false;
    document.getElementById("sec").textContent = q.section;
    document.getElementById("q").textContent = q.q;
    document.getElementById("count").textContent = i + 1 + " / " + pack.length;
    document.getElementById("bar").style.width = ((i / pack.length) * 100) + "%";
    renderTimer();

    const letters = [
      { k: "a", t: q.a },
      { k: "b", t: q.b },
      { k: "c", t: q.c },
    ];
    optsEl.innerHTML = "";
    shuffle(letters).forEach(function (o) {
      const b = document.createElement("button");
      b.className = "opt";
      b.type = "button";
      b.textContent = o.t;
      b.addEventListener("click", function () {
        choose(o.k, b);
      });
      optsEl.appendChild(b);
    });
  }

  function choose(k, btn) {
    if (locked) return;
    locked = true;
    if (k === pack[i].correct) score += 1;
    Array.prototype.forEach.call(optsEl.children, function (el) {
      el.disabled = true;
    });
    btn.classList.add("on");
    setTimeout(function () {
      i += 1;
      render();
    }, 180);
  }

  function finish(timeout) {
    clearInterval(tick);
    show(done);
    const total = pack.length;
    const pass = score >= 20;
    document.getElementById("resTitle").textContent = timeout
      ? "Время вышло"
      : pass
        ? "Зачёт"
        : "Незачёт";
    document.getElementById("resLine").textContent =
      "Верно: " + score + " из " + total + ". Порог экзамена — 20 из 25." +
      (timeout ? " Таймер истёк." : "");
    document.getElementById("resLine").className = pass ? "pass" : "fail";
  }

  document.querySelectorAll("[data-start]").forEach(function (b) {
    b.addEventListener("click", function () {
      start(b.getAttribute("data-start"));
    });
  });
  document.getElementById("quit").addEventListener("click", function () {
    clearInterval(tick);
    show(home);
  });
  document.getElementById("again").addEventListener("click", function () {
    start(lastMode);
  });
  document.getElementById("homeBtn").addEventListener("click", function () {
    show(home);
  });
})();
