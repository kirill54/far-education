import nodemailer from 'nodemailer';

export function smtpConfigured() {
  return Boolean(process.env.SMTP_HOST);
}

export async function sendLoginCode(to, code) {
  const subject = 'Код входа — учёт Актру';
  const text = `Код для входа в учёт базы Актру: ${code}\n\nОн действует 10 минут. Если вы не запрашивали код, проигнорируйте письмо.`;

  if (!smtpConfigured()) {
    console.log(`[aktru] SMTP не настроен. Код для ${to}: ${code}`);
    return { delivered: false };
  }

  const port = Number(process.env.SMTP_PORT) || 587;
  const transport = nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port,
    secure: process.env.SMTP_SECURE === '1' || port === 465,
    auth: process.env.SMTP_USER
      ? { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS || '' }
      : undefined,
  });

  await transport.sendMail({
    from: process.env.SMTP_FROM || process.env.SMTP_USER,
    to,
    subject,
    text,
  });
  return { delivered: true };
}
