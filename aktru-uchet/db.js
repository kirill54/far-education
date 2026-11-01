import Database from 'better-sqlite3';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export function openDb(dbPath) {
  const resolved = path.isAbsolute(dbPath)
    ? dbPath
    : path.join(__dirname, dbPath);
  fs.mkdirSync(path.dirname(resolved), { recursive: true });
  const db = new Database(resolved);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');
  migrate(db);
  seedIfEmpty(db);
  return db;
}

function migrate(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS units (
      id INTEGER PRIMARY KEY,
      slug TEXT NOT NULL UNIQUE,
      name TEXT NOT NULL,
      sort_order INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS categories (
      id INTEGER PRIMARY KEY,
      unit_id INTEGER REFERENCES units(id),
      kind TEXT NOT NULL CHECK (kind IN ('income', 'expense')),
      name TEXT NOT NULL,
      UNIQUE(unit_id, kind, name)
    );

    CREATE TABLE IF NOT EXISTS transactions (
      id INTEGER PRIMARY KEY,
      unit_id INTEGER NOT NULL REFERENCES units(id),
      kind TEXT NOT NULL CHECK (kind IN ('income', 'expense')),
      category_id INTEGER REFERENCES categories(id),
      amount_rub REAL NOT NULL CHECK (amount_rub > 0),
      occurred_on TEXT NOT NULL,
      description TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS employees (
      id INTEGER PRIMARY KEY,
      unit_id INTEGER NOT NULL REFERENCES units(id),
      name TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT '',
      monthly_base_rub REAL NOT NULL DEFAULT 0,
      turnover_bonus_pct REAL NOT NULL DEFAULT 0,
      active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS payroll_settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_tx_unit_date ON transactions(unit_id, occurred_on);
    CREATE INDEX IF NOT EXISTS idx_tx_kind ON transactions(kind);

    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'staff')),
      token_hash TEXT NOT NULL UNIQUE,
      employee_id INTEGER REFERENCES employees(id),
      active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS employee_sales (
      id INTEGER PRIMARY KEY,
      employee_id INTEGER NOT NULL REFERENCES employees(id),
      unit_id INTEGER NOT NULL REFERENCES units(id),
      amount_rub REAL NOT NULL CHECK (amount_rub > 0),
      occurred_on TEXT NOT NULL,
      note TEXT NOT NULL DEFAULT '',
      created_by_user_id INTEGER REFERENCES users(id),
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_sales_emp_date ON employee_sales(employee_id, occurred_on);
    CREATE INDEX IF NOT EXISTS idx_sales_unit_date ON employee_sales(unit_id, occurred_on);

    CREATE TABLE IF NOT EXISTS warehouse_items (
      id INTEGER PRIMARY KEY,
      name TEXT NOT NULL UNIQUE,
      unit_label TEXT NOT NULL DEFAULT 'шт',
      min_stock REAL NOT NULL DEFAULT 0,
      sort_order INTEGER NOT NULL DEFAULT 0,
      active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS warehouse_movements (
      id INTEGER PRIMARY KEY,
      item_id INTEGER NOT NULL REFERENCES warehouse_items(id),
      kind TEXT NOT NULL CHECK (kind IN ('receipt', 'issue')),
      quantity REAL NOT NULL CHECK (quantity > 0),
      occurred_on TEXT NOT NULL,
      employee_id INTEGER REFERENCES employees(id),
      taken_by TEXT NOT NULL DEFAULT '',
      destination TEXT NOT NULL DEFAULT '',
      note TEXT NOT NULL DEFAULT '',
      created_by_user_id INTEGER REFERENCES users(id),
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_wh_mov_item ON warehouse_movements(item_id, occurred_on);
    CREATE INDEX IF NOT EXISTS idx_wh_mov_kind ON warehouse_movements(kind);

    CREATE TABLE IF NOT EXISTS login_codes (
      id INTEGER PRIMARY KEY,
      email TEXT NOT NULL,
      code_hash TEXT NOT NULL,
      expires_at TEXT NOT NULL,
      used INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS sessions (
      id INTEGER PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id),
      token_hash TEXT NOT NULL UNIQUE,
      expires_at TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);
  ensureColumn(db, 'users', 'email', 'TEXT');
  db.exec(
    `CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL`,
  );
  seedWarehouseItems(db);
}

function ensureColumn(db, table, column, ddl) {
  const cols = db.prepare(`PRAGMA table_info(${table})`).all();
  if (!cols.some((c) => c.name === column)) {
    db.exec(`ALTER TABLE ${table} ADD COLUMN ${column} ${ddl}`);
  }
}

function seedWarehouseItems(db) {
  const count = db.prepare('SELECT COUNT(*) AS c FROM warehouse_items').get().c;
  if (count > 0) return;
  const items = [
    ['Молоко сгущённое', 'банка', 10, 1],
    ['Сахар', 'кг', 5, 2],
    ['Кофе молотый', 'кг', 2, 3],
    ['Чай пакетированный', 'уп', 5, 4],
    ['Бумажные стаканы', 'уп', 3, 5],
    ['Салфетки', 'уп', 5, 6],
    ['Мыло хозяйственное', 'шт', 5, 7],
    ['Дрова', 'м³', 2, 8],
  ];
  const ins = db.prepare(
    `INSERT INTO warehouse_items (name, unit_label, min_stock, sort_order) VALUES (?, ?, ?, ?)`,
  );
  for (const row of items) ins.run(...row);
}

function seedIfEmpty(db) {
  const count = db.prepare('SELECT COUNT(*) AS c FROM units').get().c;
  if (count > 0) return;

  const units = [
    ['cafe', 'Кафе', 1],
    ['dining', 'Столовая', 2],
    ['warehouse', 'Склад', 3],
    ['bath', 'Баня', 4],
    ['common', 'Общее', 5],
  ];
  const insUnit = db.prepare(
    'INSERT INTO units (slug, name, sort_order) VALUES (?, ?, ?)',
  );
  for (const row of units) insUnit.run(...row);

  const unitIds = Object.fromEntries(
    db.prepare('SELECT slug, id FROM units').all().map((u) => [u.slug, u.id]),
  );

  const categories = [
    ['cafe', 'income', 'Выручка касса'],
    ['cafe', 'income', 'Безнал / перевод'],
    ['cafe', 'expense', 'Закуп продуктов'],
    ['cafe', 'expense', 'ФОТ'],
    ['cafe', 'expense', 'Коммунальные'],
    ['dining', 'income', 'Выручка'],
    ['dining', 'expense', 'Продукты'],
    ['dining', 'expense', 'ФОТ'],
    ['warehouse', 'income', 'Продажа со склада'],
    ['warehouse', 'expense', 'Закуп товара'],
    ['warehouse', 'expense', 'Логистика'],
    ['bath', 'income', 'Посещения / абонементы'],
    ['bath', 'expense', 'Дрова / расходники'],
    ['bath', 'expense', 'ФОТ'],
    ['common', 'income', 'Прочие поступления'],
    ['common', 'expense', 'Общехозяйственные'],
    ['common', 'expense', 'Ремонт / техника'],
  ];
  const insCat = db.prepare(
    'INSERT INTO categories (unit_id, kind, name) VALUES (?, ?, ?)',
  );
  for (const [slug, kind, name] of categories) {
    insCat.run(unitIds[slug], kind, name);
  }

  db.prepare(
    `INSERT INTO payroll_settings (key, value) VALUES (?, ?)`,
  ).run(
    'season',
    JSON.stringify({ from_month: 5, to_month: 9, note: 'Летний сезон' }),
  );
}

export function unitBySlug(db, slug) {
  return db.prepare('SELECT * FROM units WHERE slug = ?').get(slug);
}
