#!/usr/bin/env node
/**
 * Тестовые данные летнего сезона. Повторный запуск заменяет только строки с меткой [демо].
 *   node scripts/seed-demo.js
 */
import 'dotenv/config';
import { openDb } from '../db.js';
import { generateToken, hashToken } from '../auth.js';

const db = openDb(process.env.DB_PATH || './data/aktru.db');

const unitId = Object.fromEntries(
  db.prepare('SELECT slug, id FROM units').all().map((u) => [u.slug, u.id]),
);

function categoryId(slug, kind, name) {
  const row = db
    .prepare(
      'SELECT id FROM categories WHERE unit_id = ? AND kind = ? AND name = ?',
    )
    .get(unitId[slug], kind, name);
  if (!row) throw new Error(`Нет категории ${slug}/${kind}/${name}`);
  return row.id;
}

function upsertEmployee({ name, slug, role, base, pct }) {
  const existing = db.prepare('SELECT id FROM employees WHERE name = ?').get(name);
  if (existing) {
    db.prepare(
      `UPDATE employees SET unit_id = ?, role = ?, monthly_base_rub = ?, turnover_bonus_pct = ?, active = 1 WHERE id = ?`,
    ).run(unitId[slug], role, base, pct, existing.id);
    return existing.id;
  }
  const info = db
    .prepare(
      `INSERT INTO employees (unit_id, name, role, monthly_base_rub, turnover_bonus_pct)
       VALUES (?, ?, ?, ?, ?)`,
    )
    .run(unitId[slug], name, role, base, pct);
  return info.lastInsertRowid;
}

function upsertUser({ email, name, role, employeeId }) {
  const existing = db.prepare('SELECT id FROM users WHERE email = ?').get(email);
  if (existing) {
    db.prepare(
      `UPDATE users SET name = ?, role = ?, employee_id = ?, active = 1 WHERE id = ?`,
    ).run(name, role, employeeId, existing.id);
    return;
  }
  db.prepare(
    `INSERT INTO users (name, role, token_hash, employee_id, email, active)
     VALUES (?, ?, ?, ?, ?, 1)`,
  ).run(name, role, hashToken(generateToken()), employeeId, email);
}

const tx = db.transaction(() => {
  db.prepare(`DELETE FROM transactions WHERE description LIKE '[демо] %'`).run();
  db.prepare(`DELETE FROM employee_sales WHERE note LIKE '[демо] %'`).run();
  db.prepare(`DELETE FROM warehouse_movements WHERE note LIKE '[демо] %'`).run();

  const anna = upsertEmployee({
    name: 'Анна Соколова',
    slug: 'cafe',
    role: 'Бариста',
    base: 55000,
    pct: 5,
  });
  const sergey = upsertEmployee({
    name: 'Сергей Волков',
    slug: 'cafe',
    role: 'Повар',
    base: 62000,
    pct: 4,
  });
  const marina = upsertEmployee({
    name: 'Марина Ким',
    slug: 'dining',
    role: 'Повар столовой',
    base: 48000,
    pct: 0,
  });
  upsertEmployee({
    name: 'Игорь Панов',
    slug: 'bath',
    role: 'Банщик',
    base: 45000,
    pct: 0,
  });

  upsertUser({ email: 'anna@aktru.local', name: 'Анна Соколова', role: 'staff', employeeId: anna });
  upsertUser({ email: 'sergey@aktru.local', name: 'Сергей Волков', role: 'staff', employeeId: sergey });
  upsertUser({ email: 'marina@aktru.local', name: 'Марина Ким', role: 'staff', employeeId: marina });
  upsertUser({ email: 'manager@aktru.local', name: 'Ольга Репина', role: 'manager', employeeId: null });

  const insTx = db.prepare(
    `INSERT INTO transactions (unit_id, kind, category_id, amount_rub, occurred_on, description)
     VALUES (?, ?, ?, ?, ?, ?)`,
  );
  const ops = [
    ['cafe', 'income', 'Выручка касса', 186000, '2026-06-15', '[демо] Кафе, смена выходных'],
    ['cafe', 'income', 'Безнал / перевод', 94000, '2026-06-28', '[демо] Кафе, безнал за неделю'],
    ['cafe', 'income', 'Выручка касса', 241000, '2026-07-12', '[демо] Кафе, пик сезона'],
    ['cafe', 'income', 'Выручка касса', 208000, '2026-07-26', '[демо] Кафе, вторая половина июля'],
    ['cafe', 'income', 'Безнал / перевод', 127000, '2026-08-09', '[демо] Кафе, безнал август'],
    ['cafe', 'income', 'Выручка касса', 163000, '2026-08-20', '[демо] Кафе, конец августа'],
    ['cafe', 'expense', 'Закуп продуктов', 74000, '2026-06-10', '[демо] Закуп на кафе'],
    ['cafe', 'expense', 'Закуп продуктов', 91000, '2026-07-08', '[демо] Закуп на кафе, июль'],
    ['cafe', 'expense', 'ФОТ', 117000, '2026-07-31', '[демо] Аванс и оклад кафе'],
    ['cafe', 'expense', 'Коммунальные', 18000, '2026-08-05', '[демо] Электричество кафе'],
    ['dining', 'income', 'Выручка', 96000, '2026-07-04', '[демо] Столовая, неделя'],
    ['dining', 'income', 'Выручка', 112000, '2026-07-18', '[демо] Столовая, заезд групп'],
    ['dining', 'income', 'Выручка', 88000, '2026-08-15', '[демо] Столовая, август'],
    ['dining', 'expense', 'Продукты', 54000, '2026-07-06', '[демо] Продукты столовой'],
    ['dining', 'expense', 'ФОТ', 48000, '2026-07-31', '[демо] Оклад столовой'],
    ['warehouse', 'expense', 'Закуп товара', 64000, '2026-06-05', '[демо] Поставка на склад'],
    ['warehouse', 'expense', 'Логистика', 12000, '2026-06-05', '[демо] Доставка в лагерь'],
    ['warehouse', 'income', 'Продажа со склада', 15000, '2026-07-20', '[демо] Продажа туристам'],
    ['bath', 'income', 'Посещения / абонементы', 42000, '2026-07-11', '[демо] Баня, неделя'],
    ['bath', 'income', 'Посещения / абонементы', 51000, '2026-08-02', '[демо] Баня, выходные'],
    ['bath', 'expense', 'Дрова / расходники', 16000, '2026-07-01', '[демо] Дрова'],
    ['bath', 'expense', 'ФОТ', 45000, '2026-07-31', '[демо] Оклад бани'],
    ['common', 'expense', 'Общехозяйственные', 22000, '2026-06-20', '[демо] Связь и расходники базы'],
    ['common', 'expense', 'Ремонт / техника', 35000, '2026-07-22', '[демо] Ремонт кофемашины'],
    ['common', 'income', 'Прочие поступления', 20000, '2026-08-01', '[демо] Компенсация от партнёра'],
  ];
  for (const [slug, kind, cat, amount, date, description] of ops) {
    insTx.run(unitId[slug], kind, categoryId(slug, kind, cat), amount, date, description);
  }

  const insSale = db.prepare(
    `INSERT INTO employee_sales (employee_id, unit_id, amount_rub, occurred_on, note)
     VALUES (?, ?, ?, ?, ?)`,
  );
  const sales = [
    [anna, 42000, '2026-06-14', '[демо] Смена Анны'],
    [anna, 61000, '2026-07-12', '[демо] Смена Анны, выходные'],
    [anna, 38000, '2026-08-09', '[демо] Смена Анны'],
    [sergey, 55000, '2026-07-13', '[демо] Кухня, Сергей'],
    [sergey, 47000, '2026-08-16', '[демо] Кухня, Сергей'],
  ];
  for (const [emp, amount, date, note] of sales) {
    insSale.run(emp, unitId.cafe, amount, date, note);
  }

  const itemId = Object.fromEntries(
    db.prepare('SELECT name, id FROM warehouse_items').all().map((i) => [i.name, i.id]),
  );
  const insMove = db.prepare(
    `INSERT INTO warehouse_movements
       (item_id, kind, quantity, occurred_on, employee_id, taken_by, destination, note)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
  );
  const moves = [
    ['Молоко сгущённое', 'receipt', 48, '2026-06-05', null, '', '', '[демо] Поставка'],
    ['Сахар', 'receipt', 40, '2026-06-05', null, '', '', '[демо] Поставка'],
    ['Кофе молотый', 'receipt', 12, '2026-06-05', null, '', '', '[демо] Поставка'],
    ['Чай пакетированный', 'receipt', 20, '2026-06-05', null, '', '', '[демо] Поставка'],
    ['Бумажные стаканы', 'receipt', 15, '2026-06-05', null, '', '', '[демо] Поставка'],
    ['Салфетки', 'receipt', 30, '2026-06-05', null, '', '', '[демо] Поставка'],
    ['Мыло хозяйственное', 'receipt', 24, '2026-06-05', null, '', '', '[демо] Поставка'],
    ['Дрова', 'receipt', 8, '2026-06-06', null, '', '', '[демо] Завоз дров'],
    ['Кофе молотый', 'issue', 11, '2026-07-10', anna, 'Анна Соколова', 'Кафе', '[демо] На смену'],
    ['Молоко сгущённое', 'issue', 18, '2026-07-10', anna, 'Анна Соколова', 'Кафе', '[демо] На смену'],
    ['Сахар', 'issue', 6, '2026-07-14', sergey, 'Сергей Волков', 'Кафе', '[демо] Кухня'],
    ['Бумажные стаканы', 'issue', 13, '2026-07-20', anna, 'Анна Соколова', 'Кафе', '[демо] Стаканы'],
    ['Дрова', 'issue', 3, '2026-07-18', null, 'Игорь Панов', 'Баня', '[демо] Топка'],
    ['Мыло хозяйственное', 'issue', 4, '2026-08-02', marina, 'Марина Ким', 'Столовая', '[демо] Кухня'],
    ['Салфетки', 'issue', 8, '2026-08-02', marina, 'Марина Ким', 'Столовая', '[демо] Зал'],
    ['Чай пакетированный', 'issue', 2, '2026-08-11', sergey, 'Сергей Волков', 'Кафе', '[демо] Чай'],
  ];
  for (const [name, kind, qty, date, emp, who, dest, note] of moves) {
    if (!itemId[name]) continue;
    insMove.run(itemId[name], kind, qty, date, emp, who, dest, note);
  }
});

tx();

const totals = db
  .prepare(
    `SELECT
       (SELECT COUNT(*) FROM transactions WHERE description LIKE '[демо] %') AS ops,
       (SELECT COUNT(*) FROM employee_sales WHERE note LIKE '[демо] %') AS sales,
       (SELECT COUNT(*) FROM warehouse_movements WHERE note LIKE '[демо] %') AS moves`,
  )
  .get();

console.log('Тестовые данные записаны.');
console.log(totals);
console.log(`
Вход (код на экране, пока нет SMTP):
  admin@aktru.local     администратор
  manager@aktru.local   управляющий
  anna@aktru.local      бариста, кафе
  sergey@aktru.local    повар, кафе
  marina@aktru.local    столовая
`);
