import crypto from 'crypto';

export function hashToken(token) {
  return crypto.createHash('sha256').update(token, 'utf8').digest('hex');
}

export function generateToken() {
  return crypto.randomBytes(24).toString('base64url');
}

/** @returns {{ id, name, role, employee_id } | null} */
export function resolveUser(db, bearerToken, envAdminToken) {
  if (!bearerToken) return null;
  if (envAdminToken && bearerToken === envAdminToken) {
    return {
      id: 0,
      name: 'Администратор (env)',
      role: 'admin',
      employee_id: null,
    };
  }
  const hash = hashToken(bearerToken);
  const row = db
    .prepare(
      `SELECT id, name, role, employee_id FROM users
       WHERE token_hash = ? AND active = 1`,
    )
    .get(hash);
  return row || null;
}

export function isManager(user) {
  return user && (user.role === 'admin' || user.role === 'manager');
}
