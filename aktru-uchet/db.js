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
  `);
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
    'cafe_bonus_pool_pct',
    JSON.stringify({ value: 8, note: 'Доля выручки кафе в общий премиальный фонд (%)' }),
  );
}

export function unitBySlug(db, slug) {
  return db.prepare('SELECT * FROM units WHERE slug = ?').get(slug);
}
