const TOKEN_KEY = 'aktru_admin_token';

function getToken() {
  return localStorage.getItem(TOKEN_KEY) || '';
}

function setToken(v) {
  if (v) localStorage.setItem(TOKEN_KEY, v);
  else localStorage.removeItem(TOKEN_KEY);
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(path, { ...options, headers });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { error: text };
  }
  if (!res.ok) throw new Error(data?.error || res.statusText);
  return data;
}

function fmtRub(n) {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0,
  }).format(n);
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function seasonRange(year) {
  return { from: `${year}-05-01`, to: `${year}-09-30` };
}

let units = [];
let categories = [];

function initTabs() {
  document.querySelectorAll('nav.tabs button').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('nav.tabs button').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`panel-${btn.dataset.tab}`).classList.add('active');
    });
  });
}

function fillUnitSelects() {
  for (const sel of ['txUnit', 'txFilterUnit', 'empUnit']) {
    const el = document.getElementById(sel);
    const keepAll = sel === 'txFilterUnit';
    el.innerHTML = keepAll ? '<option value="">Все</option>' : '';
    for (const u of units) {
      const opt = document.createElement('option');
      opt.value = u.id;
      opt.textContent = u.name;
      el.appendChild(opt);
    }
  }
}

function categoriesForUnitKind(unitId, kind) {
  return categories.filter(
    (c) => c.unit_id === unitId && c.kind === kind,
  );
}

function refreshCategorySelect() {
  const unitId = Number(document.getElementById('txUnit').value);
  const kind = document.getElementById('txKind').value;
  const sel = document.getElementById('txCategory');
  sel.innerHTML = '<option value="">—</option>';
  for (const c of categoriesForUnitKind(unitId, kind)) {
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = c.name;
    sel.appendChild(opt);
  }
}

async function loadMeta() {
  units = await api('/api/units');
  categories = await api('/api/categories');
  fillUnitSelects();
  refreshCategorySelect();
}

async function loadBalance(from, to) {
  const q = new URLSearchParams();
  if (from) q.set('from', from);
  if (to) q.set('to', to);
  const data = await api(`/api/balance?${q}`);
  const root = document.getElementById('balanceCards');
  root.innerHTML = '';
  for (const u of data.units) {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="label">${u.name}</div>
      <div class="value ${u.balance >= 0 ? 'positive' : 'negative'}">${fmtRub(u.balance)}</div>
      <div class="label" style="margin-top:8px">+ ${fmtRub(u.income)} / − ${fmtRub(u.expense)}</div>`;
    root.appendChild(card);
  }
  const total = document.createElement('div');
  total.className = 'card total';
  total.innerHTML = `
    <div class="label">Итого по базе</div>
    <div class="value">${fmtRub(data.total.balance)}</div>
    <div class="label" style="margin-top:8px">+ ${fmtRub(data.total.income)} / − ${fmtRub(data.total.expense)}</div>`;
  root.appendChild(total);
}

function renderTxTable(rows, withDelete) {
  if (!rows.length) return '<p class="hint">Пока нет операций.</p>';
  let html = `<table><thead><tr>
    <th>Дата</th><th>Подразделение</th><th>Тип</th><th>Категория</th>
    <th class="num">Сумма</th><th>Комментарий</th>${withDelete ? '<th></th>' : ''}
  </tr></thead><tbody>`;
  for (const t of rows) {
    html += `<tr>
      <td>${t.occurred_on}</td>
      <td>${t.unit_name}</td>
      <td>${t.kind === 'income' ? 'Доход' : 'Расход'}</td>
      <td>${t.category_name || '—'}</td>
      <td class="num">${fmtRub(t.amount_rub)}</td>
      <td>${escapeHtml(t.description || '')}</td>`;
    if (withDelete) {
      html += `<td><button type="button" class="btn danger" data-del-tx="${t.id}">×</button></td>`;
    }
    html += '</tr>';
  }
  html += '</tbody></table>';
  return html;
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]),
  );
}

async function loadRecentTx(from, to) {
  const q = new URLSearchParams();
  if (from) q.set('from', from);
  if (to) q.set('to', to);
  const rows = await api(`/api/transactions?${q}`);
  document.getElementById('recentTx').innerHTML = renderTxTable(rows.slice(0, 15), false);
}

async function loadTxJournal() {
  const q = new URLSearchParams();
  const from = document.getElementById('txFilterFrom').value;
  const to = document.getElementById('txFilterTo').value;
  const unit = document.getElementById('txFilterUnit').value;
  if (from) q.set('from', from);
  if (to) q.set('to', to);
  if (unit) q.set('unit_id', unit);
  const rows = await api(`/api/transactions?${q}`);
  const wrap = document.getElementById('txTable');
  wrap.innerHTML = renderTxTable(rows, true);
  wrap.querySelectorAll('[data-del-tx]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!confirm('Удалить операцию?')) return;
      try {
        await api(`/api/transactions/${btn.dataset.delTx}`, { method: 'DELETE' });
        await loadTxJournal();
        await refreshDashboard();
      } catch (e) {
        alert(e.message);
      }
    });
  });
}

async function refreshDashboard() {
  const from = document.getElementById('dashFrom').value;
  const to = document.getElementById('dashTo').value;
  await loadBalance(from, to);
  await loadRecentTx(from, to);
}

async function loadEmployees() {
  const rows = await api('/api/employees');
  if (!rows.length) {
    document.getElementById('empTable').innerHTML = '<p class="hint">Добавьте сотрудников кафе и других точек.</p>';
    return;
  }
  let html = `<table><thead><tr>
    <th>ФИО</th><th>Подразделение</th><th>Должность</th>
    <th class="num">Оклад</th><th class="num">% фонда</th><th>Активен</th>
  </tr></thead><tbody>`;
  for (const e of rows) {
    html += `<tr>
      <td>${escapeHtml(e.name)}</td>
      <td>${e.unit_name}</td>
      <td>${escapeHtml(e.role || '')}</td>
      <td class="num">${fmtRub(e.monthly_base_rub)}</td>
      <td class="num">${e.turnover_bonus_pct}%</td>
      <td>${e.active ? 'да' : 'нет'}</td>
    </tr>`;
  }
  html += '</tbody></table>';
  document.getElementById('empTable').innerHTML = html;
}

async function loadPayrollSettings() {
  const s = await api('/api/payroll/settings');
  const v = s.cafe_bonus_pool_pct?.value ?? 8;
  document.getElementById('payPoolPct').value = v;
}

async function calcPayroll() {
  const from = document.getElementById('payFrom').value;
  const to = document.getElementById('payTo').value;
  if (!from || !to) {
    alert('Укажите период');
    return;
  }
  const data = await api(
    `/api/payroll/preview?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&unit_slug=cafe`,
  );
  document.getElementById('paySummary').innerHTML = `
    <p class="hint">Выручка кафе за период: <strong>${fmtRub(data.turnover_rub)}</strong>.
    Премийный фонд (${data.bonus_pool_pct}%): <strong>${fmtRub(data.bonus_pool_rub)}</strong>.
    Итого к выплате: <strong>${fmtRub(data.grand_total_rub)}</strong>.</p>`;
  let html = `<table><thead><tr>
    <th>Сотрудник</th><th>Должность</th>
    <th class="num">Оклад (пропорц.)</th><th class="num">Премия</th><th class="num">Итого</th>
  </tr></thead><tbody>`;
  for (const line of data.employees) {
    html += `<tr>
      <td>${escapeHtml(line.name)}</td>
      <td>${escapeHtml(line.role || '')}</td>
      <td class="num">${fmtRub(line.base_prorated_rub)}</td>
      <td class="num">${fmtRub(line.bonus_from_pool_rub)}</td>
      <td class="num"><strong>${fmtRub(line.total_rub)}</strong></td>
    </tr>`;
  }
  html += '</tbody></table>';
  document.getElementById('payTable').innerHTML = html;
}

function bindForms() {
  document.getElementById('saveToken').addEventListener('click', () => {
    setToken(document.getElementById('tokenInput').value.trim());
    alert('Токен сохранён в браузере');
  });
  document.getElementById('tokenInput').value = getToken();

  document.getElementById('txUnit').addEventListener('change', refreshCategorySelect);
  document.getElementById('txKind').addEventListener('change', refreshCategorySelect);

  document.getElementById('txForm').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const err = document.getElementById('txError');
    err.hidden = true;
    const fd = new FormData(ev.target);
    try {
      await api('/api/transactions', {
        method: 'POST',
        body: JSON.stringify({
          occurred_on: fd.get('occurred_on'),
          unit_id: Number(fd.get('unit_id')),
          kind: fd.get('kind'),
          category_id: fd.get('category_id') ? Number(fd.get('category_id')) : null,
          amount_rub: Number(fd.get('amount_rub')),
          description: fd.get('description'),
        }),
      });
      ev.target.reset();
      ev.target.querySelector('[name=occurred_on]').value = todayIso();
      await loadTxJournal();
      await refreshDashboard();
    } catch (e) {
      err.textContent = e.message;
      err.hidden = false;
    }
  });

  document.getElementById('empForm').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const err = document.getElementById('empError');
    err.hidden = true;
    const fd = new FormData(ev.target);
    try {
      await api('/api/employees', {
        method: 'POST',
        body: JSON.stringify({
          name: fd.get('name'),
          unit_id: Number(fd.get('unit_id')),
          role: fd.get('role'),
          monthly_base_rub: Number(fd.get('monthly_base_rub')),
          turnover_bonus_pct: Number(fd.get('turnover_bonus_pct')),
        }),
      });
      ev.target.reset();
      await loadEmployees();
    } catch (e) {
      err.textContent = e.message;
      err.hidden = false;
    }
  });

  document.getElementById('dashApply').addEventListener('click', refreshDashboard);
  document.getElementById('dashSeason').addEventListener('click', () => {
    const y = new Date().getFullYear();
    const { from, to } = seasonRange(y);
    document.getElementById('dashFrom').value = from;
    document.getElementById('dashTo').value = to;
    refreshDashboard();
  });
  document.getElementById('txRefresh').addEventListener('click', loadTxJournal);
  document.getElementById('payCalc').addEventListener('click', calcPayroll);
  document.getElementById('paySaveSettings').addEventListener('click', async () => {
    try {
      await api('/api/payroll/settings', {
        method: 'PUT',
        body: JSON.stringify({
          cafe_bonus_pool_pct: {
            value: Number(document.getElementById('payPoolPct').value),
          },
        }),
      });
      alert('Сохранено');
    } catch (e) {
      alert(e.message);
    }
  });
}

async function main() {
  initTabs();
  bindForms();
  const y = new Date().getFullYear();
  const season = seasonRange(y);
  for (const id of ['dashFrom', 'txFilterFrom', 'payFrom']) {
    document.getElementById(id).value = season.from;
  }
  for (const id of ['dashTo', 'txFilterTo', 'payTo']) {
    document.getElementById(id).value = todayIso();
  }
  document.querySelector('#txForm [name=occurred_on]').value = todayIso();

  await loadMeta();
  await loadPayrollSettings();
  await refreshDashboard();
  await loadTxJournal();
  await loadEmployees();
}

main().catch((e) => {
  console.error(e);
  alert('Ошибка загрузки: ' + e.message);
});
