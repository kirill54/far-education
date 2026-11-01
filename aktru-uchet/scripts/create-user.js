#!/usr/bin/env node
/**
 * Создание пользователя с персональным токеном.
 * Пример:
 *   node scripts/create-user.js --name "Иванова" --role staff --employee-id 1
 */
import 'dotenv/config';
import { openDb } from '../db.js';
import { generateToken, hashToken } from '../auth.js';

function arg(name) {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : undefined;
}

const name = arg('--name');
const role = arg('--role') || 'staff';
const employeeId = arg('--employee-id');

if (!name) {
  console.error('Укажите --name');
  process.exit(1);
}
if (!['admin', 'manager', 'staff'].includes(role)) {
  console.error('role: admin | manager | staff');
  process.exit(1);
}
if (role === 'staff' && !employeeId) {
  console.error('Для staff нужен --employee-id (карточка сотрудника в системе)');
  process.exit(1);
}

const db = openDb(process.env.DB_PATH || './data/aktru.db');
const token = generateToken();
const info = db
  .prepare(
    `INSERT INTO users (name, role, token_hash, employee_id) VALUES (?, ?, ?, ?)`,
  )
  .run(
    name,
    role,
    hashToken(token),
    employeeId ? Number(employeeId) : null,
  );

console.log(JSON.stringify({
  id: info.lastInsertRowid,
  name,
  role,
  employee_id: employeeId ? Number(employeeId) : null,
  token,
}, null, 2));
console.error('\nСохраните token — повторно он не показывается.');
