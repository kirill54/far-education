import crypto from 'crypto';

export function hashToken(token) {
  return crypto.createHash('sha256').update(token, 'utf8').digest('hex');
}

export function generateToken() {
  return crypto.randomBytes(24).toString('base64url');
}

export function normalizeEmail(email) {
  return String(email || '').trim().toLowerCase();
}

export function resolveSession(db, token) {
  if (!token) return null;
  const row = db
    .prepare(
      `SELECT u.id, u.name, u.role, u.employee_id, u.email, s.expires_at
       FROM sessions s
       JOIN users u ON u.id = s.user_id
       WHERE s.token_hash = ? AND u.active = 1`,
    )
    .get(hashToken(token));
  if (!row) return null;
  if (new Date(row.expires_at).getTime() < Date.now()) return null;
  return row;
}

/** Сессия, старый персональный токен или ADMIN_TOKEN. */
export function resolveUser(db, bearerToken, envAdminToken) {
  const sessionUser = resolveSession(db, bearerToken);
  if (sessionUser) return sessionUser;
  if (!bearerToken) return null;
  if (envAdminToken && bearerToken === envAdminToken) {
    return {
      id: 0,
      name: 'Администратор (env)',
      role: 'admin',
      employee_id: null,
      email: null,
    };
  }
  const hash = hashToken(bearerToken);
  const row = db
    .prepare(
      `SELECT id, name, role, employee_id, email FROM users
       WHERE token_hash = ? AND active = 1`,
    )
    .get(hash);
  return row || null;
}

export function createSession(db, userId) {
  const token = generateToken();
  const expires = new Date(Date.now() + 30 * 86400000).toISOString();
  db.prepare(
    `INSERT INTO sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)`,
  ).run(userId, hashToken(token), expires);
  return token;
}

export function sessionCookie(token) {
  const maxAge = token ? 30 * 86400 : 0;
  const value = token ? encodeURIComponent(token) : '';
  return `aktru_session=${value}; HttpOnly; Path=/; SameSite=Lax; Max-Age=${maxAge}`;
}

export function readSessionCookie(req) {
  const cookie = req.get('cookie') || '';
  const match = cookie.match(/(?:^|;\s*)aktru_session=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : '';
}

export function isManager(user) {
  return user && (user.role === 'admin' || user.role === 'manager');
}
