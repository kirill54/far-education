import 'dotenv/config';
import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { openDb, unitBySlug } from './db.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT) || 3847;
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || '';
const db = openDb(process.env.DB_PATH || './data/aktru.db');

const app = express();
app.use(express.json());

function requireAuth(req, res, next) {
  if (!ADMIN_TOKEN) return next();
  const header = req.get('authorization') || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : '';
  if (token !== ADMIN_TOKEN) {
    return res.status(401).json({ error: 'Неверный или отсутствующий токен' });
  }
  next();
}

app.get('/api/health', (_req, res) => {
  res.json({ ok: true, name: 'aktru-uchet' });
});

app.get('/api/units', (_req, res) => {
  const rows = db
    .prepare('SELECT id, slug, name FROM units ORDER BY sort_order')
    .all();
  res.json(rows);
});

app.get('/api/categories', (req, res) => {
  const unitId = req.query.unit_id ? Number(req.query.unit_id) : null;
  let rows;
  if (unitId) {
    rows = db
      .prepare(
        `SELECT c.id, c.unit_id, c.kind, c.name, u.name AS unit_name
         FROM categories c JOIN units u ON u.id = c.unit_id
         WHERE c.unit_id = ? ORDER BY c.kind, c.name`,
      )
      .all(unitId);
  } else {
    rows = db
      .prepare(
        `SELECT c.id, c.unit_id, c.kind, c.name, u.name AS unit_name
         FROM categories c JOIN units u ON u.id = c.unit_id
         ORDER BY u.sort_order, c.kind, c.name`,
      )
      .all();
  }
  res.json(rows);
});

app.post('/api/categories', requireAuth, (req, res) => {
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

app.get('/api/transactions', (req, res) => {
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

app.post('/api/transactions', requireAuth, (req, res) => {
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

app.delete('/api/transactions/:id', requireAuth, (req, res) => {
  const id = Number(req.params.id);
  const info = db.prepare('DELETE FROM transactions WHERE id = ?').run(id);
  if (info.changes === 0) return res.status(404).json({ error: 'Не найдено' });
  res.json({ ok: true });
});

app.get('/api/balance', (req, res) => {
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

app.get('/api/employees', (req, res) => {
  const unitId = req.query.unit_id ? Number(req.query.unit_id) : null;
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

app.post('/api/employees', requireAuth, (req, res) => {
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

app.patch('/api/employees/:id', requireAuth, (req, res) => {
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

app.get('/api/payroll/settings', (_req, res) => {
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

app.put('/api/payroll/settings', requireAuth, (req, res) => {
  const { cafe_bonus_pool_pct } = req.body || {};
  if (cafe_bonus_pool_pct !== undefined) {
    db.prepare(
      'INSERT INTO payroll_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value',
    ).run('cafe_bonus_pool_pct', JSON.stringify(cafe_bonus_pool_pct));
  }
  res.json({ ok: true });
});

app.get('/api/payroll/preview', (req, res) => {
  const { from, to, unit_slug = 'cafe' } = req.query;
  if (!from || !to) {
    return res.status(400).json({ error: 'Нужны from и to (YYYY-MM-DD)' });
  }
  const unit = unitBySlug(db, unit_slug);
  if (!unit) return res.status(400).json({ error: 'Неизвестное подразделение' });

  const turnover = db
    .prepare(
      `SELECT COALESCE(SUM(amount_rub), 0) AS total FROM transactions
       WHERE unit_id = ? AND kind = 'income' AND occurred_on >= ? AND occurred_on <= ?`,
    )
    .get(unit.id, from, to).total;

  const poolRow = db
    .prepare(`SELECT value FROM payroll_settings WHERE key = 'cafe_bonus_pool_pct'`)
    .get();
  let poolPct = 8;
  if (poolRow) {
    try {
      poolPct = JSON.parse(poolRow.value).value ?? poolRow.value;
    } catch {
      poolPct = Number(poolRow.value) || 8;
    }
  }
  const bonusPool = (turnover * Number(poolPct)) / 100;

  const employees = db
    .prepare(
      `SELECT * FROM employees WHERE unit_id = ? AND active = 1 ORDER BY name`,
    )
    .all(unit.id);

  const pctSum = employees.reduce((s, e) => s + e.turnover_bonus_pct, 0);

  const lines = employees.map((e) => {
    const share =
      pctSum > 0 ? (e.turnover_bonus_pct / pctSum) * bonusPool : 0;
    const base = prorateBase(e.monthly_base_rub, from, to);
    return {
      employee_id: e.id,
      name: e.name,
      role: e.role,
      monthly_base_rub: e.monthly_base_rub,
      base_prorated_rub: base,
      turnover_bonus_pct: e.turnover_bonus_pct,
      bonus_from_pool_rub: Math.round(share * 100) / 100,
      total_rub: Math.round((base + share) * 100) / 100,
    };
  });

  res.json({
    unit: { slug: unit.slug, name: unit.name },
    period: { from, to },
    turnover_rub: turnover,
    bonus_pool_pct: poolPct,
    bonus_pool_rub: Math.round(bonusPool * 100) / 100,
    employees: lines,
    grand_total_rub: Math.round(lines.reduce((s, l) => s + l.total_rub, 0) * 100) / 100,
  });
});

/** Оклад пропорционально календарным дням периода (упрощённо — 30 дней в месяце). */
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
    console.warn('ADMIN_TOKEN не задан — запись без авторизации (только для разработки)');
  }
});
