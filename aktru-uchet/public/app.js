const TOKEN_KEY = 'aktru_access_token';

let me = null;
let units = [];
let categories = [];
let employees = [];

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

function seasonToDate(year) {
  const s = seasonRange(year);
  const today = todayIso();
  return today <= s.to && today >= s.from ? today : s.to;
}

function roleAllowed(rolesStr) {
  if (!me) return false;
  const roles = rolesStr.split(',').map((r) => r.trim());
  if (me.role === 'admin') return true;
  return roles.includes(me.role);
}

function applyRoleUI() {
  document.querySelectorAll('[data-roles]').forEach((el) => {
    const ok = roleAllowed(el.dataset.roles);
    el.hidden = !ok;
    if (el.classList.contains('panel') && !ok) el.classList.remove('active');
  });
  document.querySelectorAll('nav.tabs button').forEach((btn) => {
    btn.hidden = !roleAllowed(btn.dataset.roles);
  });
  const badge = document.getElementById('userBadge');
  if (me) {
    badge.hidden = false;
    badge.textContent = `${me.name} · ${me.role}`;
  } else {
    badge.hidden = true;
  }
  const firstVisible = document.querySelector('nav.tabs button:not([hidden])');
  if (firstVisible && !document.querySelector('.panel.active:not([hidden])')) {
    firstVisible.click();
  }
  const empLabel = document.getElementById('salesEmpLabel');
  if (me?.is_manager) {
    empLabel.hidden = false;
  } else {
    empLabel.hidden = true;
  }
}

function initTabs() {
  document.querySelectorAll('nav.tabs button').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (btn.hidden) return;
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
    if (!el) continue;
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

function fillEmployeeSelects() {
  const salesSel = document.getElementById('salesEmployee');
  const userSel = document.getElementById('userEmployee');
  if (salesSel) {
    salesSel.innerHTML = '';
    for (const e of employees) {
      const opt = document.createElement('option');
      opt.value = e.id;
      opt.textContent = `${e.name} (${e.unit_name})`;
      salesSel.appendChild(opt);
    }
  }
  if (userSel) {
    userSel.innerHTML = '<option value="">—</option>';
    for (const e of employees) {
      const opt = document.createElement('option');
      opt.value = e.id;
      opt.textContent = `${e.name} · id ${e.id}`;
      userSel.appendChild(opt);
    }
  }
}

function categoriesForUnitKind(unitId, kind) {
  return categories.filter((c) => c.unit_id === unitId && c.kind === kind);
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

async function loadMe() {
  me = await api('/api/me');
  applyRoleUI();
}

async function loadMeta() {
  units = await api('/api/units');
  if (me?.is_manager) {
    categories = await api('/api/categories');
  }
  employees = await api('/api/employees');
  fillUnitSelects();
  fillEmployeeSelects();
  if (me?.is_manager) refreshCategorySelect();
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
  return String(s).replace(/[&<>"']/g, (c) =>
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
  if (!me?.is_manager) return;
  const from = document.getElementById('dashFrom').value;
  const to = document.getElementById('dashTo').value;
  await loadBalance(from, to);
  await loadRecentTx(from, to);
}

function renderSalesTable(rows, canDelete) {
  if (!rows.length) return '<p class="hint">Продаж пока нет — внесите первую сумму.</p>';
  let html = `<table><thead><tr>
    <th>Дата</th><th>Сотрудник</th><th class="num">Сумма</th><th>Комментарий</th>
    ${canDelete ? '<th></th>' : ''}
  </tr></thead><tbody>`;
  for (const s of rows) {
    html += `<tr>
      <td>${s.occurred_on}</td>
      <td>${escapeHtml(s.employee_name)}</td>
      <td class="num">${fmtRub(s.amount_rub)}</td>
      <td>${escapeHtml(s.note || '')}</td>`;
    if (canDelete) {
      html += `<td><button type="button" class="btn danger" data-del-sale="${s.id}">×</button></td>`;
    }
    html += '</tr>';
  }
  html += '</tbody></table>';
  return html;
}

async function loadSalesJournal() {
  const q = new URLSearchParams();
  const from = document.getElementById('salesFilterFrom').value;
  const to = document.getElementById('salesFilterTo').value;
  if (from) q.set('from', from);
  if (to) q.set('to', to);
  const rows = await api(`/api/sales?${q}`);
  const total = rows.reduce((s, r) => s + r.amount_rub, 0);
  const wrap = document.getElementById('salesTable');
  wrap.innerHTML = renderSalesTable(rows, true);
  document.getElementById('salesTotal').textContent =
    rows.length ? `Итого за период: ${fmtRub(total)}` : '';
  wrap.querySelectorAll('[data-del-sale]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!confirm('Удалить запись?')) return;
      try {
        await api(`/api/sales/${btn.dataset.delSale}`, { method: 'DELETE' });
        await loadSalesJournal();
      } catch (e) {
        alert(e.message);
      }
    });
  });
}

async function loadEmployees() {
  employees = await api('/api/employees');
  fillEmployeeSelects();
  if (!me?.is_manager) return;
  if (!employees.length) {
    document.getElementById('empTable').innerHTML =
      '<p class="hint">Добавьте сотрудников и выдайте им токены на вкладке «Доступ».</p>';
    return;
  }
  let html = `<table><thead><tr>
    <th>id</th><th>ФИО</th><th>Подразделение</th><th>Должность</th>
    <th class="num">Оклад</th><th class="num">% премии</th><th>Активен</th>
  </tr></thead><tbody>`;
  for (const e of employees) {
    html += `<tr>
      <td>${e.id}</td>
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
  let summary = `<p class="hint">`;
  if (me?.is_manager) {
    summary += `Доход кафе в журнале операций: <strong>${fmtRub(data.ledger_income_rub)}</strong>.
    Сумма внесённых продаж (на премии): <strong>${fmtRub(data.reported_sales_total_rub)}</strong>. `;
  }
  summary += `Итого к выплате: <strong>${fmtRub(data.grand_total_rub)}</strong>.</p>`;
  document.getElementById('paySummary').innerHTML = summary;

  let html = `<table><thead><tr>
    <th>Сотрудник</th><th>Должность</th>
    <th class="num">Оклад</th><th class="num">Внесённые продажи</th>
    <th class="num">% премии</th><th class="num">Премия</th><th class="num">Итого</th>
  </tr></thead><tbody>`;
  for (const line of data.employees) {
    html += `<tr>
      <td>${escapeHtml(line.name)}</td>
      <td>${escapeHtml(line.role || '')}</td>
      <td class="num">${fmtRub(line.base_prorated_rub)}</td>
      <td class="num">${fmtRub(line.reported_sales_rub)}</td>
      <td class="num">${line.sales_bonus_pct}%</td>
      <td class="num">${fmtRub(line.bonus_rub)}</td>
      <td class="num"><strong>${fmtRub(line.total_rub)}</strong></td>
    </tr>`;
  }
  html += '</tbody></table>';
  document.getElementById('payTable').innerHTML = html;
}

async function loadUsers() {
  if (me?.role !== 'admin' && me?.id !== 0) return;
  const rows = await api('/api/users');
  if (!rows.length) {
    document.getElementById('usersTable').innerHTML = '<p class="hint">Пока никого нет.</p>';
    return;
  }
  let html = `<table><thead><tr>
    <th>id</th><th>Имя</th><th>Роль</th><th>Сотрудник</th><th>Активен</th>
  </tr></thead><tbody>`;
  for (const u of rows) {
    html += `<tr>
      <td>${u.id}</td>
      <td>${escapeHtml(u.name)}</td>
      <td>${u.role}</td>
      <td>${escapeHtml(u.employee_name || '—')}</td>
      <td>${u.active ? 'да' : 'нет'}</td>
    </tr>`;
  }
  html += '</tbody></table>';
  document.getElementById('usersTable').innerHTML = html;
}

function applySeasonDates() {
  const y = new Date().getFullYear();
  const s = seasonRange(y);
  const to = seasonToDate(y);
  for (const id of ['dashFrom', 'txFilterFrom', 'salesFilterFrom', 'payFrom']) {
    const el = document.getElementById(id);
    if (el) el.value = s.from;
  }
  for (const id of ['dashTo', 'txFilterTo', 'salesFilterTo', 'payTo']) {
    const el = document.getElementById(id);
    if (el) el.value = to;
  }
}

function bindForms() {
  document.getElementById('saveToken').addEventListener('click', async () => {
    setToken(document.getElementById('tokenInput').value.trim());
    try {
      await bootstrap();
    } catch (e) {
      setToken('');
      alert('Не удалось войти: ' + e.message);
    }
  });
  document.getElementById('tokenInput').value = getToken();

  document.getElementById('txUnit')?.addEventListener('change', refreshCategorySelect);
  document.getElementById('txKind')?.addEventListener('change', refreshCategorySelect);

  document.getElementById('txForm')?.addEventListener('submit', async (ev) => {
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

  document.getElementById('salesForm')?.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const err = document.getElementById('salesError');
    err.hidden = true;
    const fd = new FormData(ev.target);
    const body = {
      occurred_on: fd.get('occurred_on'),
      amount_rub: Number(fd.get('amount_rub')),
      note: fd.get('note'),
    };
    if (me?.is_manager && fd.get('employee_id')) {
      body.employee_id = Number(fd.get('employee_id'));
    }
    try {
      await api('/api/sales', { method: 'POST', body: JSON.stringify(body) });
      ev.target.reset();
      ev.target.querySelector('[name=occurred_on]').value = todayIso();
      await loadSalesJournal();
    } catch (e) {
      err.textContent = e.message;
      err.hidden = false;
    }
  });

  document.getElementById('empForm')?.addEventListener('submit', async (ev) => {
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

  document.getElementById('userForm')?.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const err = document.getElementById('userError');
    const reveal = document.getElementById('newUserToken');
    err.hidden = true;
    reveal.hidden = true;
    const fd = new FormData(ev.target);
    const role = fd.get('role');
    const body = { name: fd.get('name'), role };
    if (role === 'staff') {
      const eid = fd.get('employee_id');
      if (!eid) {
        err.textContent = 'Выберите сотрудника для staff';
        err.hidden = false;
        return;
      }
      body.employee_id = Number(eid);
    }
    try {
      const created = await api('/api/users', { method: 'POST', body: JSON.stringify(body) });
      reveal.hidden = false;
      reveal.textContent = `Токен для ${created.name} (скопируйте сейчас):\n\n${created.token}`;
      ev.target.reset();
      await loadUsers();
    } catch (e) {
      err.textContent = e.message;
      err.hidden = false;
    }
  });

  document.getElementById('userRole')?.addEventListener('change', (ev) => {
    document.getElementById('userEmpLabel').style.opacity =
      ev.target.value === 'staff' ? '1' : '0.5';
  });

  document.getElementById('dashApply')?.addEventListener('click', refreshDashboard);
  document.getElementById('dashSeason')?.addEventListener('click', () => {
    const y = new Date().getFullYear();
    const s = seasonRange(y);
    document.getElementById('dashFrom').value = s.from;
    document.getElementById('dashTo').value = seasonToDate(y);
    refreshDashboard();
  });
  document.getElementById('txRefresh')?.addEventListener('click', loadTxJournal);
  document.getElementById('salesRefresh')?.addEventListener('click', loadSalesJournal);
  document.getElementById('payCalc')?.addEventListener('click', calcPayroll);
  document.getElementById('paySeason')?.addEventListener('click', () => {
    const y = new Date().getFullYear();
    const s = seasonRange(y);
    document.getElementById('payFrom').value = s.from;
    document.getElementById('payTo').value = seasonToDate(y);
    calcPayroll();
  });
}

async function bootstrap() {
  if (!getToken()) {
    alert('Введите токен — его выдаёт управляющий');
    return;
  }
  await loadMe();
  await loadMeta();
  applySeasonDates();
  document.querySelector('#salesForm [name=occurred_on]') &&
    (document.querySelector('#salesForm [name=occurred_on]').value = todayIso());
  document.querySelector('#txForm [name=occurred_on]') &&
    (document.querySelector('#txForm [name=occurred_on]').value = todayIso());

  await refreshDashboard();
  if (me?.is_manager) await loadTxJournal();
  await loadSalesJournal();
  await loadEmployees();
  await loadUsers();
  if (me?.role === 'staff') {
    document.querySelector('nav.tabs button[data-tab="sales"]')?.click();
  }
}

async function main() {
  initTabs();
  bindForms();
  applySeasonDates();
  if (getToken()) {
    try {
      await bootstrap();
    } catch (e) {
      console.error(e);
    }
  }
}

main();
