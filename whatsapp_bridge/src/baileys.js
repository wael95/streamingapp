import {
  makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
} from '@whiskeysockets/baileys';
import qrcode from 'qrcode-terminal';
import pino from 'pino';
import { config } from './config.js';

const logger = pino({ level: 'warn' });

function numberFromJid(jid) {
  if (!jid) return '';
  return jid.split('@')[0].split(':')[0];
}

function extractText(message) {
  if (!message) return '';
  if (message.conversation) return message.conversation;
  if (message.extendedTextMessage?.text) return message.extendedTextMessage.text;
  if (message.imageMessage?.caption) return message.imageMessage.caption;
  return '';
}

export function normalizeJid(to) {
  if (!to) return '';
  if (to.includes('@')) return to;
  return `${to.replace(/\D/g, '')}@s.whatsapp.net`;
}

export async function startBaileys({ queue, onConnected }) {
  const { state, saveCreds } = await useMultiFileAuthState(config.authDir);
  const { version } = await fetchLatestBaileysVersion();

  const state_ = { sock: null, connected: false };
  // Track IDs of messages we sent via the bridge so we can ignore them
  // coming back through messages.upsert as fromMe=true. Messages the
  // user types on their phone (even in self-chat) are also fromMe=true
  // but won't be in this set, so they flow through.
  const sentByUs = new Set();
  const markSent = (id) => {
    sentByUs.add(id);
    setTimeout(() => sentByUs.delete(id), 5 * 60 * 1000);
  };

  const connect = () => {
    const sock = makeWASocket({
      version,
      auth: state,
      logger,
      printQRInTerminal: false,
      syncFullHistory: false,
      markOnlineOnConnect: false,
    });
    state_.sock = sock;

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
      const { connection, lastDisconnect, qr } = update;
      if (qr) {
        console.log('\nScan this QR with WhatsApp on your phone:\n');
        qrcode.generate(qr, { small: true });
      }
      if (connection === 'open') {
        state_.connected = true;
        console.log('[baileys] connected');
        onConnected?.();
      }
      if (connection === 'close') {
        state_.connected = false;
        const code = lastDisconnect?.error?.output?.statusCode;
        const loggedOut = code === DisconnectReason.loggedOut;
        console.log(`[baileys] disconnected (${code}); reconnect=${!loggedOut}`);
        if (!loggedOut) setTimeout(connect, 3000);
      }
    });

    sock.ev.on('messages.upsert', ({ messages, type }) => {
      console.log(`[upsert] type=${type} count=${messages?.length || 0}`);
      if (type !== 'notify' && type !== 'append') return;
      for (const m of messages) {
        const jid = m.key?.remoteJid || '';
        const number = numberFromJid(jid);
        const fromMe = !!m.key?.fromMe;
        const echo = fromMe && sentByUs.has(m.key?.id);
        const text = extractText(m.message || {}).trim();
        console.log(
          `[upsert] from=${jid} fromMe=${fromMe} echo=${echo} ` +
          `allowed=${config.allowedNumbers.includes(number)} text=${JSON.stringify(text).slice(0,80)}`
        );
        if (!m.message) continue;
        if (echo) continue;
        if (!jid || jid.endsWith('@g.us')) continue;
        if (!config.allowedNumbers.includes(number)) continue;
        if (!text) continue;
        queue.push({
          from: jid,
          number,
          text,
          ts: Number(m.messageTimestamp) || Math.floor(Date.now() / 1000),
        });
        console.log(`[upsert] queued from=${number} text=${JSON.stringify(text).slice(0,80)}`);
      }
    });
  };

  connect();

  return {
    isConnected: () => state_.connected,
    send: async (to, text) => {
      if (!state_.sock) throw new Error('socket not ready');
      const jid = normalizeJid(to);
      const res = await state_.sock.sendMessage(jid, { text });
      if (res?.key?.id) markSent(res.key.id);
      return { to: jid };
    },
  };
}
