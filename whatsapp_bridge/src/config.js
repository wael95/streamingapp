import dotenv from 'dotenv';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// .env lives at the repo root (two levels up from src/). Load it
// regardless of where the process was started.
dotenv.config({ path: path.resolve(__dirname, '..', '..', '.env') });

export const config = {
  port: Number(process.env.BRIDGE_PORT || 8787),
  host: process.env.BRIDGE_HOST || '127.0.0.1',
  token: process.env.BRIDGE_TOKEN || '',
  allowedNumbers: (process.env.ALLOWED_NUMBERS || '')
    .split(',')
    .map(s => s.trim())
    .filter(Boolean),
  authDir: path.resolve(__dirname, '..', 'auth'),
  logDir: path.resolve(__dirname, '..', '..', 'logs'),
};

if (!config.token) {
  console.error('BRIDGE_TOKEN is required. Set it in .env');
  process.exit(1);
}
