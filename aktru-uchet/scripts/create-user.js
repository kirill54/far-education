#!/usr/bin/env node
/**
 * Добавить email в список доступа.
 *   node scripts/create-user.js --email a@aktru.ru --name "Иванова" --role staff --employee-id 1
 */
import 'dotenv/config';
import { openDb } from '../db.js';
import { generateToken, hashToken, normalizeEmail } from '../auth.js';

function arg(name) {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : undefined;
}

const name = arg('--name');
const role = arg('--role') || 'staff';
const employeeId = arg('--employee-id');
const email = normalizeEmail(arg('--email'));

if (!name || !email) {
  console.error('Укажите --name и --email');
  process.exit(1);
}
if (!['admin', 'manager', 'staff'].includes(role)) {
  console.error('role: admin | manager | staff');
  process.exit(1);
}
if (role === 'staff' && !employeeId) {
  console.error('Для staff нужен --employee-id');
  process.exit(1);
}

const db = openDb(process.env.DB_PATH || './data/aktru.db');
const info = db
  .prepare(
    `INSERT INTO users (name, role, token_hash, employee_id, email) VALUES (?, ?, ?, ?, ?)`,
  )
  .run(name, role, hashToken(generateToken()), employeeId ? Number(employeeId) : null, email);

console.log(JSON.stringify({
  id: info.lastInsertRowid,
  name,
  role,
  email,
  employee_id: employeeId ? Number(employeeId) : null,
}, null, 2));
