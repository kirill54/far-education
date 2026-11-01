import 'dotenv/config';
import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { openDb, unitBySlug } from './db.js';
import { generateToken, hashToken, isManager, resolveUser } from './auth.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT) || 3847;
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || '';
const db = openDb(process.env.DB_PATH || './data/aktru.db');

const app = express();
app.use(express.json());

function attachUser(req, res, next) {
  const header = req.get('authorization') || '';
  const bearer = header.startsWith('Bearer ') ? header.slice(7) : '';
  req.user = resolveUser(db, bearer, ADMIN_TOKEN || null);
  if (!ADMIN_TOKEN && !bearer) {
    req.user = { id: -1, name: 'dev', role: 'admin', employee_id: null };
  }
  next();
}

function requireAuth(req, res, next) {
  if (!req.user) {
    return res.status(401).json({ error: 'Нужен токен доступа' });
  }
  next();
}

function requireManager(req, res, next) {
  if (!isManager(req.user)) {
    return res.status(403).json({ error: 'Доступ только для управляющего' });
  }
  next();
}

app.use(attachUser);

app.get('/api/health', (_req, res) => {
  res.json({ ok: true, name: 'aktru-uchet' });
});

app.get('/api/me', requireAuth, (req, res) => {
  const body = {
    id: req.user.id,
    name: req.user.name,
    role: req.user.role,
    employee_id: req.user.employee_id,
    is_manager: isManager(req.user),
  };
  if (req.user.employee_id) {
    const emp = db
      .prepare('SELECT id, name, role, unit_id, monthly_base_rub, turnover_bonus_pct FROM employees WHERE id = ?')
      .get(req.user.employee_id);
    body.employee = emp || null;
  }
  res.json(body);
});

app.get('/api/units', requireAuth, (_req, res) => {
  const rows = db
    .prepare('SELECT id, slug, name FROM units ORDER BY sort_order')
    .all();
  res.json(rows);
});

app.get('/api/categories', requireAuth, requireManager, (req, res) => {
  const unitId = req.query.unit_id ? Number(req.query.unit_id) : null;
  const rows = unitId
    ? db
        .prepare(
          `SELECT c.id, c.unit_id, c.kind, c.name, u.name AS unit_name
           FROM categories c JOIN units u ON u.id = c.unit_id
           WHERE c.unit_id = ? ORDER BY c.kind, c.name`,
        )
        .all(unitId)
    : db
        .prepare(
          `SELECT c.id, c.unit_id, c.kind, c.name, u.name AS unit_name
           FROM categories c JOIN units u ON u.id = c.unit_id
           ORDER BY u.sort_order, c.kind, c.name`,
        )
        .all();
  res.json(rows);
});

app.post('/api/categories', requireAuth, requireManager, (req, res) => {
  const { unit_id, kind, name } = req.body || {};
  if (!unit_id || !kind || !name) {
    return res.status(400).json({ error: 'Нужны unit_id, kind, name' });
  }
  if (!['income', 'expense'].includes(kind)) {
    return res.status(400).json({ error: 'kind: income или expense' });
  }
  try {
    const info = db
      .prepare(
        'INSERT INTO categories (unit_id, kind, name) VALUES (?, ?, ?)',
      )
      .run(unit_id, kind, name.trim());
    res.status(201).json({ id: info.lastInsertRowid });
  } catch {
    res.status(409).json({ error: 'Такая категория уже есть' });
  }
});

app.get('/api/transactions', requireAuth, requireManager, (req, res) => {
  const { from, to, unit_id, kind } = req.query;
  const clauses = [];
  const params = [];
  if (from) {
    clauses.push('t.occurred_on >= ?');
    params.push(from);
  }
  if (to) {
    clauses.push('t.occurred_on <= ?');
    params.push(to);
  }
  if (unit_id) {
    clauses.push('t.unit_id = ?');
    params.push(Number(unit_id));
  }
  if (kind) {
    clauses.push('t.kind = ?');
    params.push(kind);
  }
  const where = clauses.length ? `WHERE ${clauses.join(' AND ')}` : '';
  const rows = db
    .prepare(
      `SELECT t.id, t.unit_id, u.name AS unit_name, t.kind, t.category_id,
              c.name AS category_name, t.amount_rub, t.occurred_on, t.description, t.created_at
       FROM transactions t
       JOIN units u ON u.id = t.unit_id
       LEFT JOIN categories c ON c.id = t.category_id
       ${where}
       ORDER BY t.occurred_on DESC, t.id DESC
       LIMIT 500`,
    )
    .all(...params);
  res.json(rows);
});

app.post('/api/transactions', requireAuth, requireManager, (req, res) => {
  const { unit_id, kind, category_id, amount_rub, occurred_on, description } =
    req.body || {};
  if (!unit_id || !kind || !amount_rub || !occurred_on) {
    return res
      .status(400)
      .json({ error: 'Нужны unit_id, kind, amount_rub, occurred_on' });
  }
  if (!['income', 'expense'].includes(kind)) {
    return res.status(400).json({ error: 'kind: income или expense' });
  }
  const amount = Number(amount_rub);
  if (!Number.isFinite(amount) || amount <= 0) {
    return res.status(400).json({ error: 'Сумма должна быть больше 0' });
  }
  const info = db
    .prepare(
      `INSERT INTO transactions (unit_id, kind, category_id, amount_rub, occurred_on, description)
       VALUES (?, ?, ?, ?, ?, ?)`,
    )
    .run(
      unit_id,
      kind,
      category_id || null,
      amount,
      occurred_on,
      (description || '').trim(),
    );
  res.status(201).json({ id: info.lastInsertRowid });
});

app.delete('/api/transactions/:id', requireAuth, requireManager, (req, res) => {
  const id = Number(req.params.id);
  const info = db.prepare('DELETE FROM transactions WHERE id = ?').run(id);
  if (info.changes === 0) return res.status(404).json({ error: 'Не найдено' });
  res.json({ ok: true });
});

app.get('/api/balance', requireAuth, requireManager, (req, res) => {
  const { from, to } = req.query;
  const params = [];
  let dateFilter = '';
  if (from) {
    dateFilter += ' AND occurred_on >= ?';
    params.push(from);
  }
  if (to) {
    dateFilter += ' AND occurred_on <= ?';
    params.push(to);
  }

  const joinExtra = dateFilter.replace(/^ AND /, '');
  const onClause = joinExtra
    ? `t.unit_id = u.id AND ${joinExtra}`
    : 't.unit_id = u.id';

  const byUnit = db
    .prepare(
      `SELECT u.id, u.slug, u.name,
              COALESCE(SUM(CASE WHEN t.kind = 'income' THEN t.amount_rub ELSE 0 END), 0) AS income,
              COALESCE(SUM(CASE WHEN t.kind = 'expense' THEN t.amount_rub ELSE 0 END), 0) AS expense
       FROM units u
       LEFT JOIN transactions t ON ${onClause}
       GROUP BY u.id
       ORDER BY u.sort_order`,
    )
    .all(...params)
    .map((row) => ({
      ...row,
      balance: row.income - row.expense,
    }));

  const totals = byUnit.reduce(
    (acc, u) => ({
      income: acc.income + u.income,
      expense: acc.expense + u.expense,
    }),
    { income: 0, expense: 0 },
  );

  res.json({
    from: from || null,
    to: to || null,
    units: byUnit,
    total: {
      ...totals,
      balance: totals.income - totals.expense,
    },
  });
});

app.get('/api/sales', requireAuth, (req, res) => {
  const { from, to, employee_id, unit_id } = req.query;
  const clauses = [];
  const params = [];

  if (req.user.role === 'staff') {
    if (!req.user.employee_id) {
      return res.status(403).json({ error: 'У учётной записи не привязан сотрудник' });
    }
    clauses.push('s.employee_id = ?');
    params.push(req.user.employee_id);
  } else if (employee_id) {
    clauses.push('s.employee_id = ?');
    params.push(Number(employee_id));
  }
  if (from) {
    clauses.push('s.occurred_on >= ?');
    params.push(from);
  }
  if (to) {
    clauses.push('s.occurred_on <= ?');
    params.push(to);
  }
  if (unit_id) {
    clauses.push('s.unit_id = ?');
    params.push(Number(unit_id));
  }
  const where = clauses.length ? `WHERE ${clauses.join(' AND ')}` : '';
  const rows = db
    .prepare(
      `SELECT s.id, s.employee_id, e.name AS employee_name, s.unit_id, u.name AS unit_name,
              s.amount_rub, s.occurred_on, s.note, s.created_at,
              cu.name AS created_by_name
       FROM employee_sales s
       JOIN employees e ON e.id = s.employee_id
       JOIN units u ON u.id = s.unit_id
       LEFT JOIN users cu ON cu.id = s.created_by_user_id
       ${where}
       ORDER BY s.occurred_on DESC, s.id DESC
       LIMIT 500`,
    )
    .all(...params);
  res.json(rows);
});

app.post('/api/sales', requireAuth, (req, res) => {
  const { employee_id, unit_id, amount_rub, occurred_on, note } = req.body || {};
  let empId = employee_id ? Number(employee_id) : null;
  const unitId = unit_id ? Number(unit_id) : null;

  if (req.user.role === 'staff') {
    if (!req.user.employee_id) {
      return res.status(403).json({ error: 'Нет привязки к сотруднику' });
    }
    empId = req.user.employee_id;
  }
  if (!empId || !amount_rub || !occurred_on) {
    return res.status(400).json({ error: 'Нужны employee_id, amount_rub, occurred_on' });
  }
  const emp = db.prepare('SELECT * FROM employees WHERE id = ? AND active = 1').get(empId);
  if (!emp) return res.status(400).json({ error: 'Сотрудник не найден' });
  const resolvedUnitId = unitId || emp.unit_id;

  const amount = Number(amount_rub);
  if (!Number.isFinite(amount) || amount <= 0) {
    return res.status(400).json({ error: 'Сумма должна быть больше 0' });
  }

  const creatorId = req.user.id > 0 ? req.user.id : null;
  const info = db
    .prepare(
      `INSERT INTO employee_sales (employee_id, unit_id, amount_rub, occurred_on, note, created_by_user_id)
       VALUES (?, ?, ?, ?, ?, ?)`,
    )
    .run(empId, resolvedUnitId, amount, occurred_on, (note || '').trim(), creatorId);
  res.status(201).json({ id: info.lastInsertRowid });
});

app.delete('/api/sales/:id', requireAuth, (req, res) => {
  const id = Number(req.params.id);
  const row = db.prepare('SELECT * FROM employee_sales WHERE id = ?').get(id);
  if (!row) return res.status(404).json({ error: 'Не найдено' });
  if (req.user.role === 'staff') {
    if (row.employee_id !== req.user.employee_id) {
      return res.status(403).json({ error: 'Можно удалять только свои продажи' });
    }
  } else if (!isManager(req.user)) {
    return res.status(403).json({ error: 'Недостаточно прав' });
  }
  db.prepare('DELETE FROM employee_sales WHERE id = ?').run(id);
  res.json({ ok: true });
});

app.get('/api/employees', requireAuth, (req, res) => {
  const unitId = req.query.unit_id ? Number(req.query.unit_id) : null;
  if (!isManager(req.user)) {
    if (!req.user.employee_id) return res.json([]);
    const one = db
      .prepare(
        `SELECT e.*, u.name AS unit_name FROM employees e
         JOIN units u ON u.id = e.unit_id WHERE e.id = ?`,
      )
      .get(req.user.employee_id);
    return res.json(one ? [one] : []);
  }
  const rows = unitId
    ? db
        .prepare(
          `SELECT e.*, u.name AS unit_name FROM employees e
           JOIN units u ON u.id = e.unit_id
           WHERE e.unit_id = ? ORDER BY e.name`,
        )
        .all(unitId)
    : db
        .prepare(
          `SELECT e.*, u.name AS unit_name FROM employees e
           JOIN units u ON u.id = e.unit_id
           WHERE e.active = 1 ORDER BY u.sort_order, e.name`,
        )
        .all();
  res.json(rows);
});

app.post('/api/employees', requireAuth, requireManager, (req, res) => {
  const {
    unit_id,
    name,
    role,
    monthly_base_rub,
    turnover_bonus_pct,
  } = req.body || {};
  if (!unit_id || !name) {
    return res.status(400).json({ error: 'Нужны unit_id и name' });
  }
  const info = db
    .prepare(
      `INSERT INTO employees (unit_id, name, role, monthly_base_rub, turnover_bonus_pct)
       VALUES (?, ?, ?, ?, ?)`,
    )
    .run(
      unit_id,
      name.trim(),
      (role || '').trim(),
      Number(monthly_base_rub) || 0,
      Number(turnover_bonus_pct) || 0,
    );
  res.status(201).json({ id: info.lastInsertRowid });
});

app.patch('/api/employees/:id', requireAuth, requireManager, (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare('SELECT * FROM employees WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Не найдено' });
  const body = req.body || {};
  db.prepare(
    `UPDATE employees SET
       name = ?, role = ?, monthly_base_rub = ?, turnover_bonus_pct = ?, active = ?
     WHERE id = ?`,
  ).run(
    body.name !== undefined ? String(body.name).trim() : existing.name,
    body.role !== undefined ? String(body.role).trim() : existing.role,
    body.monthly_base_rub !== undefined
      ? Number(body.monthly_base_rub)
      : existing.monthly_base_rub,
    body.turnover_bonus_pct !== undefined
      ? Number(body.turnover_bonus_pct)
      : existing.turnover_bonus_pct,
    body.active !== undefined ? (body.active ? 1 : 0) : existing.active,
    id,
  );
  res.json({ ok: true });
});

app.get('/api/users', requireAuth, (req, res) => {
  if (req.user.role !== 'admin' && !(req.user.id === 0)) {
    return res.status(403).json({ error: 'Только администратор' });
  }
  const rows = db
    .prepare(
      `SELECT u.id, u.name, u.role, u.employee_id, e.name AS employee_name, u.active, u.created_at
       FROM users u LEFT JOIN employees e ON e.id = u.employee_id
       ORDER BY u.id`,
    )
    .all();
  res.json(rows);
});

app.post('/api/users', requireAuth, (req, res) => {
  if (req.user.role !== 'admin' && !(req.user.id === 0)) {
    return res.status(403).json({ error: 'Только администратор' });
  }
  const { name, role, employee_id } = req.body || {};
  if (!name || !role) {
    return res.status(400).json({ error: 'Нужны name и role' });
  }
  if (!['admin', 'manager', 'staff'].includes(role)) {
    return res.status(400).json({ error: 'role: admin | manager | staff' });
  }
  if (role === 'staff' && !employee_id) {
    return res.status(400).json({ error: 'Для staff укажите employee_id' });
  }
  const token = generateToken();
  const info = db
    .prepare(
      `INSERT INTO users (name, role, token_hash, employee_id) VALUES (?, ?, ?, ?)`,
    )
    .run(name.trim(), role, hashToken(token), employee_id ? Number(employee_id) : null);
  res.status(201).json({
    id: info.lastInsertRowid,
    name: name.trim(),
    role,
    employee_id: employee_id ? Number(employee_id) : null,
    token,
  });
});

app.patch('/api/users/:id', requireAuth, (req, res) => {
  if (req.user.role !== 'admin' && !(req.user.id === 0)) {
    return res.status(403).json({ error: 'Только администратор' });
  }
  const id = Number(req.params.id);
  const existing = db.prepare('SELECT * FROM users WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Не найдено' });
  const { active, name, role, employee_id } = req.body || {};
  db.prepare(
    `UPDATE users SET name = ?, role = ?, employee_id = ?, active = ? WHERE id = ?`,
  ).run(
    name !== undefined ? String(name).trim() : existing.name,
    role !== undefined ? role : existing.role,
    employee_id !== undefined ? (employee_id ? Number(employee_id) : null) : existing.employee_id,
    active !== undefined ? (active ? 1 : 0) : existing.active,
    id,
  );
  res.json({ ok: true });
});

app.get('/api/payroll/settings', requireAuth, requireManager, (_req, res) => {
  const rows = db.prepare('SELECT key, value FROM payroll_settings').all();
  const settings = {};
  for (const row of rows) {
    try {
      settings[row.key] = JSON.parse(row.value);
    } catch {
      settings[row.key] = row.value;
    }
  }
  res.json(settings);
});

app.put('/api/payroll/settings', requireAuth, requireManager, (req, res) => {
  const body = req.body || {};
  for (const key of Object.keys(body)) {
    db.prepare(
      'INSERT INTO payroll_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value',
    ).run(key, JSON.stringify(body[key]));
  }
  res.json({ ok: true });
});

function sumEmployeeSales(employeeId, unitId, from, to) {
  return db
    .prepare(
      `SELECT COALESCE(SUM(amount_rub), 0) AS total FROM employee_sales
       WHERE employee_id = ? AND unit_id = ? AND occurred_on >= ? AND occurred_on <= ?`,
    )
    .get(employeeId, unitId, from, to).total;
}

app.get('/api/payroll/preview', requireAuth, (req, res) => {
  const { from, to, unit_slug = 'cafe' } = req.query;
  if (!from || !to) {
    return res.status(400).json({ error: 'Нужны from и to (YYYY-MM-DD)' });
  }
  const unit = unitBySlug(db, unit_slug);
  if (!unit) return res.status(400).json({ error: 'Неизвестное подразделение' });

  let employees = db
    .prepare(
      `SELECT * FROM employees WHERE unit_id = ? AND active = 1 ORDER BY name`,
    )
    .all(unit.id);

  if (req.user.role === 'staff') {
    employees = employees.filter((e) => e.id === req.user.employee_id);
    if (!employees.length) {
      return res.status(403).json({ error: 'Нет данных для вашей учётной записи' });
    }
  }

  const cafeIncomeLedger = db
    .prepare(
      `SELECT COALESCE(SUM(amount_rub), 0) AS total FROM transactions
       WHERE unit_id = ? AND kind = 'income' AND occurred_on >= ? AND occurred_on <= ?`,
    )
    .get(unit.id, from, to).total;

  const lines = employees.map((e) => {
    const reported = sumEmployeeSales(e.id, unit.id, from, to);
    const bonusPct = Number(e.turnover_bonus_pct) || 0;
    const bonus = (reported * bonusPct) / 100;
    const base = prorateBase(e.monthly_base_rub, from, to);
    return {
      employee_id: e.id,
      name: e.name,
      role: e.role,
      monthly_base_rub: e.monthly_base_rub,
      base_prorated_rub: base,
      reported_sales_rub: reported,
      sales_bonus_pct: bonusPct,
      bonus_rub: Math.round(bonus * 100) / 100,
      total_rub: Math.round((base + bonus) * 100) / 100,
    };
  });

  const reportedTotal = lines.reduce((s, l) => s + l.reported_sales_rub, 0);

  res.json({
    unit: { slug: unit.slug, name: unit.name },
    period: { from, to },
    ledger_income_rub: cafeIncomeLedger,
    reported_sales_total_rub: reportedTotal,
    note: 'Премия считается только от продаж, внесённых сотрудниками. % премии задаёт управляющий.',
    employees: lines,
    grand_total_rub: Math.round(lines.reduce((s, l) => s + l.total_rub, 0) * 100) / 100,
  });
});

function prorateBase(monthlyBase, from, to) {
  const start = new Date(from + 'T12:00:00');
  const end = new Date(to + 'T12:00:00');
  const days = Math.round((end - start) / 86400000) + 1;
  if (days <= 0 || !monthlyBase) return 0;
  return Math.round(((monthlyBase * days) / 30) * 100) / 100;
}

app.use(express.static(path.join(__dirname, 'public')));

app.listen(PORT, () => {
  console.log(`Актру учёт: http://localhost:${PORT}`);
  if (!ADMIN_TOKEN) {
    console.warn('ADMIN_TOKEN не задан — режим разработки без проверки токена');
  }
});
