let me = null;
let pendingLoginEmail = '';
let units = [];
let categories = [];
let employees = [];
let warehouseItems = [];

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(path, { credentials: 'include', ...options, headers });
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

function currentMonthRange() {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth();
  const month = String(m + 1).padStart(2, '0');
  const last = String(new Date(y, m + 1, 0).getDate()).padStart(2, '0');
  return { from: `${y}-${month}-01`, to: `${y}-${month}-${last}` };
}

function seasonToDate(year) {
  const s = seasonRange(year);
  const today = todayIso();
  return today <= s.to && today >= s.from ? today : s.to;
}

function roleAllowed(rolesStr) {
  if (!me) return false;
  const roles = rolesStr.split(',').map((r) => r.trim());
  if (me.role === 'admin' || me.role === 'owner') return true;
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
    const roleName = {
      owner: 'владелец',
      admin: 'администратор',
      manager: 'управляющий',
      staff: 'сотрудник',
      instructor: 'инструктор',
    }[me.role] || me.role;
    badge.textContent = `${me.name} · ${roleName}`;
  } else {
    badge.hidden = true;
  }
  const firstVisible = document.querySelector('nav.tabs button:not([hidden])');
  if (firstVisible && !document.querySelector('.panel.active:not([hidden])')) {
    firstVisible.click();
  }
  for (const id of ['salesEmpLabel', 'whIssueEmpLabel']) {
    const el = document.getElementById(id);
    if (el) el.hidden = !me?.is_manager;
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
  const whEmpSel = document.getElementById('whIssueEmployee');
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
  if (whEmpSel) {
    whEmpSel.innerHTML = '';
    for (const e of employees) {
      const opt = document.createElement('option');
      opt.value = e.id;
      opt.textContent = e.name;
      whEmpSel.appendChild(opt);
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

async function loadDashboard(from, to) {
  const q = new URLSearchParams();
  if (from) q.set('from', from);
  if (to) q.set('to', to);
  const data = await api(`/api/dashboard?${q}`);
  document.getElementById('kpiRow').innerHTML = `
    <div class="kpi income"><div class="label">Доход</div><div class="value">${fmtRub(data.total.income)}</div></div>
    <div class="kpi expense"><div class="label">Расход</div><div class="value">${fmtRub(data.total.expense)}</div></div>
    <div class="kpi balance"><div class="label">Баланс</div><div class="value">${fmtRub(data.total.balance)}</div></div>`;
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
  document.getElementById('dashExtra').innerHTML = `
    <p class="hint" style="margin:0">Продажи сотрудников для премий: <strong>${fmtRub(data.reported_sales_rub)}</strong> (${data.reported_sales_count} записей).</p>`;
  const low = document.getElementById('dashLowStock');
  if (!data.low_stock.length) {
    low.innerHTML = '<p class="hint" style="margin:0">Все позиции выше минимума.</p>';
  } else {
    low.innerHTML = '<ul class="hint">' + data.low_stock.map((i) =>
      `<li>${escapeHtml(i.name)}: ${i.balance} ${escapeHtml(i.unit_label)} (мин. ${i.min_stock})</li>`,
    ).join('') + '</ul>';
  }
  document.getElementById('recentTx').innerHTML = renderTxTable(data.recent || [], false);
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
  await loadDashboard(from, to);
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
  const canEditPay = !!me?.is_admin;
  let html = `<table><thead><tr>
    <th>ФИО</th><th>Подразделение</th><th>Должность</th>
    <th class="num">Оклад</th><th class="num">% премии</th><th></th>
  </tr></thead><tbody>`;
  for (const e of employees) {
    const payCells = canEditPay
      ? `<td class="num"><input data-pay-base="${e.id}" type="number" min="0" step="100" value="${e.monthly_base_rub}" class="w-28 text-right"></td>
         <td class="num"><input data-pay-pct="${e.id}" type="number" min="0" max="100" step="0.1" value="${e.turnover_bonus_pct}" class="w-20 text-right"></td>
         <td><button type="button" class="btn secondary" data-save-pay="${e.id}">Сохранить</button></td>`
      : `<td class="num">${fmtRub(e.monthly_base_rub)}</td>
         <td class="num">${e.turnover_bonus_pct}%</td><td></td>`;
    html += `<tr>
      <td>${escapeHtml(e.name)}</td>
      <td>${e.unit_name}</td>
      <td>${escapeHtml(e.role || '')}</td>
      ${payCells}
    </tr>`;
  }
  html += '</tbody></table>';
  const empWrap = document.getElementById('empTable');
  empWrap.innerHTML = html;
  empWrap.querySelectorAll('[data-save-pay]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.savePay;
      const base = empWrap.querySelector(`[data-pay-base="${id}"]`).value;
      const pct = empWrap.querySelector(`[data-pay-pct="${id}"]`).value;
      try {
        await api(`/api/employees/${id}`, {
          method: 'PATCH',
          body: JSON.stringify({
            monthly_base_rub: Number(base),
            turnover_bonus_pct: Number(pct),
          }),
        });
        btn.textContent = 'Сохранено';
      } catch (err) {
        alert(err.message);
      }
    });
  });
}

async function calcPayroll() {
  const from = document.getElementById('payFrom').value;
  const to = document.getElementById('payTo').value;
  if (!from || !to) {
    alert('Укажите период');
    return;
  }
  let data;
  try {
    data = await api(
      `/api/payroll/preview?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&unit_slug=cafe`,
    );
  } catch (e) {
    document.getElementById('paySummary').innerHTML = `<p class="hint">${escapeHtml(e.message)}</p>`;
    document.getElementById('payTable').innerHTML = '';
    return;
  }
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

function fillWarehouseItemSelects() {
  for (const id of ['whIssueItem', 'whReceiptItem']) {
    const sel = document.getElementById(id);
    if (!sel) continue;
    sel.innerHTML = '';
    for (const it of warehouseItems) {
      const opt = document.createElement('option');
      opt.value = it.id;
      const bal = it.stock_balance ?? 0;
      opt.textContent = `${it.name} (ост. ${bal} ${it.unit_label})`;
      sel.appendChild(opt);
    }
  }
}

async function loadWarehouseItems() {
  warehouseItems = await api('/api/warehouse/items');
  fillWarehouseItemSelects();
  const wrap = document.getElementById('whStockTable');
  if (!wrap) return;
  if (!warehouseItems.length) {
    wrap.innerHTML = '<p class="hint">Нет позиций — управляющий добавит номенклатуру.</p>';
    return;
  }
  const canEditItems = !!me?.is_manager;
  let html = `<table><thead><tr>
    <th>Позиция</th><th>Ед.</th><th class="num">Остаток</th><th class="num">Мин.</th>${canEditItems ? '<th></th>' : ''}
  </tr></thead><tbody>`;
  for (const it of warehouseItems) {
    const cls = it.below_min ? ' class="low-stock"' : '';
    html += `<tr${cls}>
      <td>${escapeHtml(it.name)}</td>
      <td>${escapeHtml(it.unit_label)}</td>
      <td class="num stock-num">${it.stock_balance}</td>
      <td class="num">${it.min_stock || '—'}</td>
      ${canEditItems ? `<td><button type="button" class="btn secondary" data-edit-item="${it.id}">Изменить</button></td>` : ''}
    </tr>`;
  }
  html += '</tbody></table>';
  wrap.innerHTML = html;
  wrap.querySelectorAll('[data-edit-item]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const item = warehouseItems.find((row) => row.id === Number(btn.dataset.editItem));
      if (!item) return;
      document.getElementById('editItemId').value = item.id;
      document.getElementById('editItemName').value = item.name;
      document.getElementById('editItemUnit').value = item.unit_label;
      document.getElementById('editItemMin').value = item.min_stock;
      document.getElementById('whEditError').hidden = true;
      openModal('modalEditItem');
    });
  });
}

function renderWhMoveTable(rows, canDelete) {
  if (!rows.length) return '<p class="hint">Движений пока нет.</p>';
  let html = `<table><thead><tr>
    <th>Дата</th><th>Позиция</th><th>Тип</th><th class="num">Кол-во</th>
    <th>Кто</th><th>Куда</th><th>Комментарий</th>${canDelete ? '<th></th>' : ''}
  </tr></thead><tbody>`;
  for (const m of rows) {
    const who = m.employee_name || m.taken_by || m.created_by_name || '—';
    html += `<tr>
      <td>${m.occurred_on}</td>
      <td>${escapeHtml(m.item_name)}</td>
      <td>${m.kind === 'receipt' ? 'Приход' : 'Списание'}</td>
      <td class="num">${m.quantity} ${escapeHtml(m.unit_label)}</td>
      <td>${escapeHtml(who)}</td>
      <td>${escapeHtml(m.destination || '—')}</td>
      <td>${escapeHtml(m.note || '')}</td>`;
    if (canDelete) {
      html += `<td><button type="button" class="btn danger" data-del-wh="${m.id}">×</button></td>`;
    }
    html += '</tr>';
  }
  html += '</tbody></table>';
  return html;
}

async function loadWarehouseMovements() {
  const q = new URLSearchParams();
  const from = document.getElementById('whFilterFrom')?.value;
  const to = document.getElementById('whFilterTo')?.value;
  if (from) q.set('from', from);
  if (to) q.set('to', to);
  const rows = await api(`/api/warehouse/movements?${q}`);
  const wrap = document.getElementById('whMoveTable');
  if (!wrap) return;
  wrap.innerHTML = renderWhMoveTable(rows, !!me?.is_manager);
  wrap.querySelectorAll('[data-del-wh]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!confirm('Удалить запись? Остаток пересчитается.')) return;
      try {
        await api(`/api/warehouse/movements/${btn.dataset.delWh}`, { method: 'DELETE' });
        await loadWarehouseItems();
        await loadWarehouseMovements();
      } catch (e) {
        alert(e.message);
      }
    });
  });
}

let guideInstructors = [];
let guideServices = [];

async function loadGuides() {
  const servicesEl = document.getElementById('guideServices');
  if (!servicesEl) return;
  guideServices = await api('/api/guide-services');
  guideInstructors = await api('/api/instructors');
  servicesEl.innerHTML = guideServices.length
    ? `<table><thead><tr><th>Услуга</th><th class="num">Цена</th><th class="num">Выплата</th></tr></thead><tbody>${
      guideServices.map((s) => `<tr><td>${escapeHtml(s.name)}</td><td class="num">${fmtRub(s.price_rub)}</td><td class="num">${fmtRub(s.payout_rub)}</td></tr>`).join('')
    }</tbody></table>`
    : '<p class="hint">Услуг пока нет.</p>';
  const serviceSel = document.getElementById('guideService');
  serviceSel.innerHTML = guideServices.map((s) => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join('');
  const instSel = document.getElementById('guideInstructor');
  if (instSel) {
    instSel.innerHTML = guideInstructors.map((i) => `<option value="${i.id}">${escapeHtml(i.name)}</option>`).join('');
  }
  const userInst = document.getElementById('userInstructor');
  if (userInst && me?.is_admin) {
    const keep = userInst.value;
    userInst.innerHTML = '<option value="">—</option>' + guideInstructors.map((i) => `<option value="${i.id}">${escapeHtml(i.name)}</option>`).join('');
    userInst.value = keep;
  }
}

async function loadGuideReport() {
  const from = document.getElementById('guideFrom').value;
  const to = document.getElementById('guideTo').value;
  if (!from || !to) return;
  const data = await api(`/api/guide-payout?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`);
  const jobs = await api(`/api/guide-jobs?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`);
  document.getElementById('guidePayout').innerHTML = `
    <p class="hint">Туристам начислено <strong>${fmtRub(data.totals.revenue_rub)}</strong>.
    К выплате инструкторам <strong>${fmtRub(data.totals.payout_rub)}</strong>.</p>
    <table><thead><tr><th>Инструктор</th><th class="num">Услуг</th><th class="num">Туристов</th><th class="num">Выручка</th><th class="num">Выплата</th></tr></thead><tbody>
    ${data.instructors.map((row) => `<tr><td>${escapeHtml(row.name)}</td><td class="num">${row.quantity}</td><td class="num">${row.tourists}</td><td class="num">${fmtRub(row.revenue_rub)}</td><td class="num">${fmtRub(row.payout_rub)}</td></tr>`).join('') || '<tr><td colspan="5">Нет данных</td></tr>'}
    </tbody></table>`;
  document.getElementById('guideJobs').innerHTML = jobs.length
    ? `<table><thead><tr><th>Дата</th><th>Инструктор</th><th>Услуга</th><th class="num">Кол-во</th><th class="num">Выплата</th>${me?.is_manager ? '<th></th>' : ''}</tr></thead><tbody>${
      jobs.map((j) => `<tr><td>${j.occurred_on}</td><td>${escapeHtml(j.instructor_name)}</td><td>${escapeHtml(j.service_name)}</td><td class="num">${j.quantity}</td><td class="num">${fmtRub(j.payout_rub_total)}</td>${me?.is_manager ? `<td><button type="button" class="btn danger" data-del-job="${j.id}">×</button></td>` : ''}</tr>`).join('')
    }</tbody></table>`
    : '';
  document.querySelectorAll('[data-del-job]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!confirm('Удалить запись?')) return;
      await api(`/api/guide-jobs/${btn.dataset.delJob}`, { method: 'DELETE' });
      await loadGuideReport();
    });
  });
}

async function loadUsers() {
  if (!me?.is_admin && me?.id !== 0) return;
  const rows = await api('/api/users');
  if (!rows.length) {
    document.getElementById('usersTable').innerHTML = '<p class="hint">Пока никого нет.</p>';
    return;
  }
  const roleLabel = {
    staff: 'Сотрудник',
    instructor: 'Инструктор',
    manager: 'Управляющий',
    admin: 'Администратор',
    owner: 'Владелец',
  };
  const roleOpts = (current) =>
    Object.entries(roleLabel)
      .map(([r, label]) => `<option value="${r}" ${r === current ? 'selected' : ''}>${label}</option>`)
      .join('');
  let html = `<table><thead><tr>
    <th>Email</th><th>Имя</th><th>Роль</th><th>Сотрудник</th><th>Доступ</th>
  </tr></thead><tbody>`;
  for (const u of rows) {
    html += `<tr>
      <td>${escapeHtml(u.email || '— нет email')}</td>
      <td>${escapeHtml(u.name)}</td>
      <td><select data-role-user="${u.id}">${roleOpts(u.role)}</select></td>
      <td>${escapeHtml(u.employee_name || '—')}</td>
      <td><button type="button" class="btn secondary" data-toggle-user="${u.id}" data-active="${u.active ? '1' : '0'}">${u.active ? 'Отключить' : 'Включить'}</button></td>
    </tr>`;
  }
  html += '</tbody></table>';
  const wrap = document.getElementById('usersTable');
  wrap.innerHTML = html;
  wrap.querySelectorAll('[data-role-user]').forEach((sel) => {
    sel.addEventListener('change', async () => {
      try {
        await api(`/api/users/${sel.dataset.roleUser}`, {
          method: 'PATCH',
          body: JSON.stringify({ role: sel.value }),
        });
      } catch (e) {
        alert(e.message);
        await loadUsers();
      }
    });
  });
  wrap.querySelectorAll('[data-toggle-user]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const active = btn.dataset.active !== '1';
      try {
        await api(`/api/users/${btn.dataset.toggleUser}`, {
          method: 'PATCH',
          body: JSON.stringify({ active }),
        });
        await loadUsers();
      } catch (e) {
        alert(e.message);
      }
    });
  });
}

function applySeasonDates() {
  const y = new Date().getFullYear();
  const s = seasonRange(y);
  const to = seasonToDate(y);
  for (const id of ['dashFrom', 'txFilterFrom', 'whFilterFrom', 'guideFrom']) {
    const el = document.getElementById(id);
    if (el) el.value = s.from;
  }
  for (const id of ['dashTo', 'txFilterTo', 'whFilterTo', 'guideTo']) {
    const el = document.getElementById(id);
    if (el) el.value = to;
  }
  const month = currentMonthRange();
  for (const id of ['salesFilterFrom', 'payFrom']) {
    const el = document.getElementById(id);
    if (el) el.value = month.from;
  }
  for (const id of ['salesFilterTo', 'payTo']) {
    const el = document.getElementById(id);
    if (el) el.value = month.to;
  }
}

function openModal(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.hidden = false;
  const date = el.querySelector('input[type=date]');
  if (date && !date.value) date.value = todayIso();
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.hidden = true;
}

function showLogin() {
  document.getElementById('loginScreen').hidden = false;
  document.getElementById('appRoot').hidden = true;
}

function showApp() {
  document.getElementById('loginScreen').hidden = true;
  document.getElementById('appRoot').hidden = false;
}

function bindForms() {
  document.getElementById('emailForm').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const err = document.getElementById('loginError');
    const hint = document.getElementById('loginHint');
    err.hidden = true;
    hint.textContent = '';
    const email = document.getElementById('loginEmail').value.trim();
    const btn = document.getElementById('sendCodeBtn');
    btn.disabled = true;
    try {
      const data = await api('/api/auth/request-code', {
        method: 'POST',
        body: JSON.stringify({ email }),
      });
      pendingLoginEmail = email;
      document.getElementById('emailForm').hidden = true;
      document.getElementById('codeForm').hidden = false;
      const codeInput = document.getElementById('loginCode');
      codeInput.value = data.dev_code || '';
      codeInput.focus();
      if (data.dev_code) {
        hint.textContent = `Почта на сервере ещё не настроена. Код уже подставлен в поле — нажмите «Войти». Он действует 30 минут.`;
      } else {
        hint.textContent = `Код отправлен на ${email}. Действует 30 минут.`;
      }
    } catch (e) {
      err.textContent = e.message;
      err.hidden = false;
    } finally {
      btn.disabled = false;
    }
  });

  document.getElementById('codeForm').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const err = document.getElementById('loginError');
    const submit = ev.target.querySelector('button[type="submit"]');
    err.hidden = true;
    submit.disabled = true;
    const prevLabel = submit.textContent;
    submit.textContent = 'Входим…';
    try {
      await api('/api/auth/verify', {
        method: 'POST',
        body: JSON.stringify({
          email: pendingLoginEmail || document.getElementById('loginEmail').value.trim(),
          code: document.getElementById('loginCode').value.trim(),
        }),
      });
      await bootstrap();
    } catch (e) {
      showLogin();
      err.textContent = e.message || 'Не удалось войти';
      err.hidden = false;
      submit.textContent = prevLabel;
    } finally {
      submit.disabled = false;
    }
  });

  document.getElementById('backToEmail').addEventListener('click', () => {
    document.getElementById('codeForm').hidden = true;
    document.getElementById('emailForm').hidden = false;
    document.getElementById('loginHint').textContent = '';
  });

  document.getElementById('logoutBtn').addEventListener('click', async () => {
    await api('/api/auth/logout', { method: 'POST' });
    me = null;
    showLogin();
  });

  document.getElementById('openIssue').addEventListener('click', () => openModal('modalIssue'));
  document.getElementById('openReceipt')?.addEventListener('click', () => openModal('modalReceipt'));
  document.getElementById('openItem')?.addEventListener('click', () => openModal('modalItem'));
  document.getElementById('openJournal').addEventListener('click', () => {
    openModal('modalJournal');
    loadWarehouseMovements();
  });
  document.querySelectorAll('[data-close]').forEach((btn) => {
    btn.addEventListener('click', () => closeModal(btn.dataset.close));
  });
  document.querySelectorAll('.modal-backdrop').forEach((backdrop) => {
    backdrop.addEventListener('click', (ev) => {
      if (ev.target === backdrop) backdrop.hidden = true;
    });
  });

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

  document.getElementById('whIssueForm')?.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const err = document.getElementById('whIssueError');
    err.hidden = true;
    const fd = new FormData(ev.target);
    const body = {
      item_id: Number(fd.get('item_id')),
      kind: 'issue',
      quantity: Number(fd.get('quantity')),
      occurred_on: fd.get('occurred_on'),
      destination: fd.get('destination'),
      note: fd.get('note'),
    };
    if (me?.is_manager && fd.get('employee_id')) {
      body.employee_id = Number(fd.get('employee_id'));
    }
    try {
      await api('/api/warehouse/movements', { method: 'POST', body: JSON.stringify(body) });
      ev.target.reset();
      ev.target.querySelector('[name=occurred_on]').value = todayIso();
      await loadWarehouseItems();
      await loadWarehouseMovements();
      closeModal('modalIssue');
    } catch (e) {
      err.textContent = e.message;
      err.hidden = false;
    }
  });

  document.getElementById('whReceiptForm')?.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const err = document.getElementById('whReceiptError');
    err.hidden = true;
    const fd = new FormData(ev.target);
    try {
      await api('/api/warehouse/movements', {
        method: 'POST',
        body: JSON.stringify({
          item_id: Number(fd.get('item_id')),
          kind: 'receipt',
          quantity: Number(fd.get('quantity')),
          occurred_on: fd.get('occurred_on'),
          note: fd.get('note'),
        }),
      });
      ev.target.reset();
      ev.target.querySelector('[name=occurred_on]').value = todayIso();
      await loadWarehouseItems();
      await loadWarehouseMovements();
      closeModal('modalReceipt');
    } catch (e) {
      err.textContent = e.message;
      err.hidden = false;
    }
  });

  document.getElementById('whEditForm')?.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const err = document.getElementById('whEditError');
    err.hidden = true;
    const fd = new FormData(ev.target);
    try {
      await api(`/api/warehouse/items/${fd.get('id')}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name: fd.get('name'),
          unit_label: fd.get('unit_label'),
          min_stock: Number(fd.get('min_stock')),
        }),
      });
      closeModal('modalEditItem');
      await loadWarehouseItems();
    } catch (e) {
      err.textContent = e.message;
      err.hidden = false;
    }
  });

  document.getElementById('whItemForm')?.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const fd = new FormData(ev.target);
    try {
      await api('/api/warehouse/items', {
        method: 'POST',
        body: JSON.stringify({
          name: fd.get('name'),
          unit_label: fd.get('unit_label'),
          min_stock: Number(fd.get('min_stock')),
        }),
      });
      ev.target.reset();
      ev.target.querySelector('[name=unit_label]').value = 'шт';
      await loadWarehouseItems();
      closeModal('modalItem');
    } catch (e) {
      alert(e.message);
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
    err.hidden = true;
    const fd = new FormData(ev.target);
    const role = fd.get('role');
    const body = { name: fd.get('name'), role, email: fd.get('email') };
    if (fd.get('employee_id')) body.employee_id = Number(fd.get('employee_id'));
    if (role === 'instructor') {
      const iid = fd.get('instructor_id');
      if (!iid) {
        err.textContent = 'Выберите карточку инструктора';
        err.hidden = false;
        return;
      }
      body.instructor_id = Number(iid);
    }
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
      await api('/api/users', { method: 'POST', body: JSON.stringify(body) });
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
  document.getElementById('whRefresh')?.addEventListener('click', () => {
    loadWarehouseItems();
    loadWarehouseMovements();
  });
  document.getElementById('payCalc')?.addEventListener('click', calcPayroll);
  document.getElementById('guideJobForm')?.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const err = document.getElementById('guideJobError');
    err.hidden = true;
    const fd = new FormData(ev.target);
    const body = {
      service_id: Number(fd.get('service_id')),
      occurred_on: fd.get('occurred_on'),
      quantity: Number(fd.get('quantity')),
      tourists: Number(fd.get('tourists')) || 1,
      note: fd.get('note'),
    };
    if (me?.is_manager && fd.get('instructor_id')) body.instructor_id = Number(fd.get('instructor_id'));
    try {
      await api('/api/guide-jobs', { method: 'POST', body: JSON.stringify(body) });
      await loadGuideReport();
    } catch (e) {
      err.textContent = e.message;
      err.hidden = false;
    }
  });
  document.getElementById('guideServiceForm')?.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const fd = new FormData(ev.target);
    try {
      await api('/api/guide-services', {
        method: 'POST',
        body: JSON.stringify({
          name: fd.get('name'),
          price_rub: Number(fd.get('price_rub')),
          payout_rub: Number(fd.get('payout_rub')),
        }),
      });
      ev.target.reset();
      await loadGuides();
    } catch (e) {
      alert(e.message);
    }
  });
  document.getElementById('instructorForm')?.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const fd = new FormData(ev.target);
    try {
      await api('/api/instructors', {
        method: 'POST',
        body: JSON.stringify({ name: fd.get('name'), note: fd.get('note') }),
      });
      ev.target.reset();
      await loadGuides();
    } catch (e) {
      alert(e.message);
    }
  });
  document.getElementById('guideCalc')?.addEventListener('click', () => loadGuideReport().catch((e) => alert(e.message)));
  document.getElementById('guideSeason')?.addEventListener('click', () => {
    const y = new Date().getFullYear();
    const s = seasonRange(y);
    document.getElementById('guideFrom').value = s.from;
    document.getElementById('guideTo').value = seasonToDate(y);
    loadGuideReport().catch((e) => alert(e.message));
  });

  document.getElementById('paySeason')?.addEventListener('click', () => {
    const y = new Date().getFullYear();
    const s = seasonRange(y);
    document.getElementById('payFrom').value = s.from;
    document.getElementById('payTo').value = seasonToDate(y);
    calcPayroll();
  });
}

async function bootstrap() {
  await loadMe();
  showApp();
  await loadMeta();
  applySeasonDates();
  document.querySelector('#salesForm [name=occurred_on]') &&
    (document.querySelector('#salesForm [name=occurred_on]').value = todayIso());
  document.querySelector('#txForm [name=occurred_on]') &&
    (document.querySelector('#txForm [name=occurred_on]').value = todayIso());
  document.querySelector('#whIssueForm [name=occurred_on]') &&
    (document.querySelector('#whIssueForm [name=occurred_on]').value = todayIso());
  document.querySelector('#whReceiptForm [name=occurred_on]') &&
    (document.querySelector('#whReceiptForm [name=occurred_on]').value = todayIso());
  document.querySelector('#guideJobForm [name=occurred_on]') &&
    (document.querySelector('#guideJobForm [name=occurred_on]').value = todayIso());

  await refreshDashboard();
  if (me?.is_manager) await loadTxJournal();
  await loadSalesJournal();
  if (me?.is_manager || me?.role === 'staff') await calcPayroll();
  await loadWarehouseItems();
  await loadWarehouseMovements();
  await loadEmployees();
  if (me?.is_manager || me?.role === 'instructor') {
    await loadGuides();
    await loadGuideReport();
  }
  await loadUsers();
  if (me?.role === 'instructor') {
    document.querySelector('nav.tabs button[data-tab="guides"]')?.click();
  } else if (me?.role === 'staff') {
    document.querySelector('nav.tabs button[data-tab="sales"]')?.click();
  }
}

async function main() {
  initTabs();
  bindForms();
  applySeasonDates();
  try {
    await bootstrap();
  } catch {
    showLogin();
  }
}

main();
