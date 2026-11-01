import 'dotenv/config';
import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { openDb, unitBySlug } from './db.js';
import {
  createSession,
  generateToken,
  hashToken,
  isManager,
  normalizeEmail,
  readSessionCookie,
  resolveUser,
  sessionCookie,
} from './auth.js';
import { sendLoginCode, smtpConfigured } from './mail.js';
import { listItemsWithStock, stockForItem } from './warehouse.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT) || 3847;
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || '';
const db = openDb(process.env.DB_PATH || './data/aktru.db');
ensureBootstrapAdmin(db);

function ensureBootstrapAdmin(database) {
  const email = normalizeEmail(process.env.ADMIN_EMAIL || '');
  if (!email) return;
  const existing = database.prepare('SELECT id FROM users WHERE email = ?').get(email);
  if (existing) return;
  database
    .prepare(
      `INSERT INTO users (name, role, token_hash, email, active) VALUES (?, 'admin', ?, ?, 1)`,
    )
    .run('Администратор', hashToken(generateToken()), email);
  console.log(`Создан администратор: ${email}`);
}

const app = express();
app.use(express.json());

function attachUser(req, res, next) {
  const header = req.get('authorization') || '';
  const bearer = header.startsWith('Bearer ') ? header.slice(7) : '';
  const token = bearer || readSessionCookie(req);
  req.user = resolveUser(db, token, ADMIN_TOKEN || null);
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
  res.json({ ok: true, name: 'aktru-uchet', mail: smtpConfigured() });
});

app.post('/api/auth/request-code', async (req, res) => {
  const email = normalizeEmail(req.body?.email);
  if (!email || !email.includes('@')) {
    return res.status(400).json({ error: 'Укажите email' });
  }
  const user = db
    .prepare('SELECT id, active FROM users WHERE email = ?')
    .get(email);
  if (!user || !user.active) {
    return res.status(403).json({
      error: 'Этот адрес не в списке доступа. Попросите администратора добавить его.',
    });
  }
  const recent = db
    .prepare(
      `SELECT created_at FROM login_codes WHERE email = ? ORDER BY id DESC LIMIT 1`,
    )
    .get(email);
  if (recent) {
    const age = Date.now() - new Date(recent.created_at + 'Z').getTime();
    if (Number.isFinite(age) && age >= 0 && age < 30000) {
      return res.status(429).json({ error: 'Код уже отправлен. Подождите полминуты.' });
    }
  }
  const code = String(Math.floor(100000 + Math.random() * 900000));
  const expires = new Date(Date.now() + 30 * 60 * 1000).toISOString();
  db.prepare(
    `INSERT INTO login_codes (email, code_hash, expires_at) VALUES (?, ?, ?)`,
  ).run(email, hashToken(code), expires);
  try {
    const result = await sendLoginCode(email, code);
    const body = { ok: true, delivered: result.delivered };
    if (!result.delivered) body.dev_code = code;
    res.json(body);
  } catch (err) {
    console.error(err);
    res.status(502).json({ error: 'Не удалось отправить письмо' });
  }
});

function expiresMs(value) {
  const raw = String(value ?? '').trim();
  if (/^\d+$/.test(raw)) return Number(raw);
  const hasZone = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(raw);
  const iso = raw.includes('T') ? raw : raw.replace(' ', 'T');
  const parsed = Date.parse(hasZone ? iso : `${iso}Z`);
  return Number.isNaN(parsed) ? 0 : parsed;
}

app.post('/api/auth/verify', (req, res) => {
  const email = normalizeEmail(req.body?.email);
  const code = String(req.body?.code || '').replace(/\D/g, '');
  if (!email || code.length < 6) {
    return res.status(400).json({ error: 'Нужны email и код из 6 цифр' });
  }
  const user = db
    .prepare('SELECT * FROM users WHERE email = ? AND active = 1')
    .get(email);
  if (!user) return res.status(403).json({ error: 'Нет доступа' });
  const rows = db
    .prepare(
      `SELECT * FROM login_codes WHERE email = ? ORDER BY id DESC LIMIT 8`,
    )
    .all(email);
  const row = rows.find((item) => item.code_hash === hashToken(code));
  if (!row) {
    return res.status(400).json({
      error: 'Неверный код. Запросите новый — на экране появится актуальный.',
    });
  }
  if (expiresMs(row.expires_at) < Date.now()) {
    return res.status(400).json({ error: 'Срок этого кода вышел (30 минут). Запросите новый.' });
  }
  if (!row.used) {
    db.prepare('UPDATE login_codes SET used = 1 WHERE id = ?').run(row.id);
  }
  const token = createSession(db, user.id);
  res.setHeader('Set-Cookie', sessionCookie(token));
  res.json({
    ok: true,
    user: { id: user.id, name: user.name, role: user.role, email: user.email },
  });
});

app.post('/api/auth/logout', (req, res) => {
  const token = readSessionCookie(req);
  if (token) {
    db.prepare('DELETE FROM sessions WHERE token_hash = ?').run(hashToken(token));
  }
  res.setHeader('Set-Cookie', sessionCookie(''));
  res.json({ ok: true });
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

app.get('/api/dashboard', requireAuth, requireManager, (req, res) => {
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
  const units = db
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
    .map((row) => ({ ...row, balance: row.income - row.expense }));
  const total = units.reduce(
    (acc, u) => ({
      income: acc.income + u.income,
      expense: acc.expense + u.expense,
    }),
    { income: 0, expense: 0 },
  );
  total.balance = total.income - total.expense;

  const saleParams = [];
  let saleWhere = '';
  if (from) {
    saleWhere += ' AND occurred_on >= ?';
    saleParams.push(from);
  }
  if (to) {
    saleWhere += ' AND occurred_on <= ?';
    saleParams.push(to);
  }
  const reported = db
    .prepare(
      `SELECT COALESCE(SUM(amount_rub), 0) AS total, COUNT(*) AS cnt FROM employee_sales WHERE 1=1 ${saleWhere}`,
    )
    .get(...saleParams);

  const stock = listItemsWithStock(db, true);
  const low = stock.filter((i) => i.below_min);

  const txParams = [];
  const txClauses = [];
  if (from) {
    txClauses.push('t.occurred_on >= ?');
    txParams.push(from);
  }
  if (to) {
    txClauses.push('t.occurred_on <= ?');
    txParams.push(to);
  }
  const txWhere = txClauses.length ? `WHERE ${txClauses.join(' AND ')}` : '';
  const recent = db
    .prepare(
      `SELECT t.id, u.name AS unit_name, t.kind, t.amount_rub, t.occurred_on, t.description
       FROM transactions t JOIN units u ON u.id = t.unit_id
       ${txWhere}
       ORDER BY t.occurred_on DESC, t.id DESC LIMIT 8`,
    )
    .all(...txParams);

  res.json({
    from: from || null,
    to: to || null,
    total,
    units,
    reported_sales_rub: reported.total,
    reported_sales_count: reported.cnt,
    low_stock: low.map((i) => ({
      name: i.name,
      balance: i.stock_balance,
      unit_label: i.unit_label,
      min_stock: i.min_stock,
    })),
    recent,
  });
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
      `SELECT u.id, u.name, u.role, u.email, u.employee_id, e.name AS employee_name, u.active, u.created_at
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
  const { name, role, employee_id, email } = req.body || {};
  const normalized = normalizeEmail(email);
  if (!name || !role || !normalized) {
    return res.status(400).json({ error: 'Нужны name, email и role' });
  }
  if (!['admin', 'manager', 'staff'].includes(role)) {
    return res.status(400).json({ error: 'role: admin | manager | staff' });
  }
  if (role === 'staff' && !employee_id) {
    return res.status(400).json({ error: 'Для сотрудника укажите карточку в справочнике' });
  }
  try {
    const info = db
      .prepare(
        `INSERT INTO users (name, role, token_hash, employee_id, email) VALUES (?, ?, ?, ?, ?)`,
      )
      .run(
        name.trim(),
        role,
        hashToken(generateToken()),
        employee_id ? Number(employee_id) : null,
        normalized,
      );
    res.status(201).json({
      id: info.lastInsertRowid,
      name: name.trim(),
      role,
      email: normalized,
      employee_id: employee_id ? Number(employee_id) : null,
    });
  } catch {
    res.status(409).json({ error: 'Такой email уже есть' });
  }
});

app.patch('/api/users/:id', requireAuth, (req, res) => {
  if (req.user.role !== 'admin' && !(req.user.id === 0)) {
    return res.status(403).json({ error: 'Только администратор' });
  }
  const id = Number(req.params.id);
  const existing = db.prepare('SELECT * FROM users WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Не найдено' });
  const { active, name, role, employee_id, email } = req.body || {};
  const nextEmail = email !== undefined ? normalizeEmail(email) : existing.email;
  try {
    db.prepare(
      `UPDATE users SET name = ?, role = ?, employee_id = ?, active = ?, email = ? WHERE id = ?`,
    ).run(
      name !== undefined ? String(name).trim() : existing.name,
      role !== undefined ? role : existing.role,
      employee_id !== undefined ? (employee_id ? Number(employee_id) : null) : existing.employee_id,
      active !== undefined ? (active ? 1 : 0) : existing.active,
      nextEmail,
      id,
    );
  } catch {
    return res.status(409).json({ error: 'Такой email уже есть' });
  }
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

app.get('/api/warehouse/items', requireAuth, (req, res) => {
  const all = req.query.all === '1' && isManager(req.user);
  res.json(listItemsWithStock(db, !all));
});

app.post('/api/warehouse/items', requireAuth, requireManager, (req, res) => {
  const { name, unit_label, min_stock, sort_order } = req.body || {};
  if (!name) return res.status(400).json({ error: 'Нужно название позиции' });
  try {
    const info = db
      .prepare(
        `INSERT INTO warehouse_items (name, unit_label, min_stock, sort_order)
         VALUES (?, ?, ?, ?)`,
      )
      .run(
        String(name).trim(),
        (unit_label || 'шт').trim(),
        Number(min_stock) || 0,
        Number(sort_order) || 0,
      );
    res.status(201).json({ id: info.lastInsertRowid });
  } catch {
    res.status(409).json({ error: 'Такая позиция уже есть' });
  }
});

app.patch('/api/warehouse/items/:id', requireAuth, requireManager, (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare('SELECT * FROM warehouse_items WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Не найдено' });
  const body = req.body || {};
  db.prepare(
    `UPDATE warehouse_items SET name = ?, unit_label = ?, min_stock = ?, sort_order = ?, active = ?
     WHERE id = ?`,
  ).run(
    body.name !== undefined ? String(body.name).trim() : existing.name,
    body.unit_label !== undefined ? String(body.unit_label).trim() : existing.unit_label,
    body.min_stock !== undefined ? Number(body.min_stock) : existing.min_stock,
    body.sort_order !== undefined ? Number(body.sort_order) : existing.sort_order,
    body.active !== undefined ? (body.active ? 1 : 0) : existing.active,
    id,
  );
  res.json({ ok: true });
});

app.get('/api/warehouse/movements', requireAuth, (req, res) => {
  const { from, to, item_id, kind, employee_id } = req.query;
  const clauses = [];
  const params = [];

  if (req.user.role === 'staff') {
    if (req.user.employee_id) {
      clauses.push('(m.employee_id = ? OR m.created_by_user_id = ?)');
      params.push(req.user.employee_id, req.user.id > 0 ? req.user.id : -1);
    } else if (req.user.id > 0) {
      clauses.push('m.created_by_user_id = ?');
      params.push(req.user.id);
    }
  } else if (employee_id) {
    clauses.push('m.employee_id = ?');
    params.push(Number(employee_id));
  }
  if (from) {
    clauses.push('m.occurred_on >= ?');
    params.push(from);
  }
  if (to) {
    clauses.push('m.occurred_on <= ?');
    params.push(to);
  }
  if (item_id) {
    clauses.push('m.item_id = ?');
    params.push(Number(item_id));
  }
  if (kind) {
    clauses.push('m.kind = ?');
    params.push(kind);
  }
  const where = clauses.length ? `WHERE ${clauses.join(' AND ')}` : '';
  const rows = db
    .prepare(
      `SELECT m.id, m.item_id, w.name AS item_name, w.unit_label, m.kind, m.quantity,
              m.occurred_on, m.employee_id, e.name AS employee_name, m.taken_by,
              m.destination, m.note, m.created_at, u.name AS created_by_name
       FROM warehouse_movements m
       JOIN warehouse_items w ON w.id = m.item_id
       LEFT JOIN employees e ON e.id = m.employee_id
       LEFT JOIN users u ON u.id = m.created_by_user_id
       ${where}
       ORDER BY m.occurred_on DESC, m.id DESC
       LIMIT 500`,
    )
    .all(...params);
  res.json(rows);
});

app.post('/api/warehouse/movements', requireAuth, (req, res) => {
  const {
    item_id,
    kind,
    quantity,
    occurred_on,
    employee_id,
    taken_by,
    destination,
    note,
  } = req.body || {};

  if (!item_id || !kind || !quantity || !occurred_on) {
    return res.status(400).json({ error: 'Нужны item_id, kind, quantity, occurred_on' });
  }
  if (!['receipt', 'issue'].includes(kind)) {
    return res.status(400).json({ error: 'kind: receipt или issue' });
  }
  if (kind === 'receipt' && !isManager(req.user)) {
    return res.status(403).json({ error: 'Приход на склад вносит управляющий' });
  }

  const qty = Number(quantity);
  if (!Number.isFinite(qty) || qty <= 0) {
    return res.status(400).json({ error: 'Количество должно быть больше 0' });
  }

  const item = db.prepare('SELECT * FROM warehouse_items WHERE id = ? AND active = 1').get(item_id);
  if (!item) return res.status(400).json({ error: 'Позиция не найдена' });

  if (kind === 'issue') {
    const { balance } = stockForItem(db, item.id);
    if (qty > balance + 1e-9) {
      return res.status(400).json({
        error: `Недостаточно на складе: остаток ${balance} ${item.unit_label}`,
      });
    }
  }

  let empId = employee_id ? Number(employee_id) : null;
  let takenBy = (taken_by || '').trim();
  if (req.user.role === 'staff') {
    if (req.user.employee_id) empId = req.user.employee_id;
    if (!takenBy) takenBy = req.user.name;
  }
  if (kind === 'issue' && !destination?.trim() && !note?.trim()) {
    return res.status(400).json({ error: 'Укажите куда (кафе, баня…) или комментарий' });
  }

  const creatorId = req.user.id > 0 ? req.user.id : null;
  const info = db
    .prepare(
      `INSERT INTO warehouse_movements
         (item_id, kind, quantity, occurred_on, employee_id, taken_by, destination, note, created_by_user_id)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    )
    .run(
      item.id,
      kind,
      qty,
      occurred_on,
      empId,
      takenBy,
      (destination || '').trim(),
      (note || '').trim(),
      creatorId,
    );
  res.status(201).json({ id: info.lastInsertRowid });
});

app.delete('/api/warehouse/movements/:id', requireAuth, requireManager, (req, res) => {
  const id = Number(req.params.id);
  const info = db.prepare('DELETE FROM warehouse_movements WHERE id = ?').run(id);
  if (info.changes === 0) return res.status(404).json({ error: 'Не найдено' });
  res.json({ ok: true });
});

app.use(express.static(path.join(__dirname, 'public')));

app.listen(PORT, () => {
  console.log(`Актру учёт: http://localhost:${PORT}`);
  if (!ADMIN_TOKEN) {
    console.warn('ADMIN_TOKEN не задан — режим разработки без проверки токена');
  }
});
