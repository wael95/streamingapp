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
      if (type !== 'notify' && type !== 'append') return;
      for (const m of messages) {
        if (!m.message) continue;
        const fromMe = !!m.key?.fromMe;
        const echo = fromMe && sentByUs.has(m.key?.id);
        if (echo) continue;
        const jid = m.key?.remoteJid || '';
        if (!jid || jid.endsWith('@g.us')) continue;
        // WhatsApp now uses @lid (Linked-ID) JIDs for some chats. The
        // phone-number form is exposed via several optional fields
        // depending on the Baileys version. Collect every candidate
        // and accept the message if ANY resolves to an allowlisted
        // phone number.
        const candidates = [
          jid,
          m.key?.participant,
          m.key?.participantPn,
          m.key?.senderPn,
          m.key?.remoteJidAlt,
        ].filter(Boolean);
        const numbers = candidates.map(numberFromJid).filter(Boolean);
        const matched = numbers.find((n) =>
          config.allowedNumbers.includes(n)
        );
        const text = extractText(m.message).trim();
        console.log(
          `[upsert] jid=${jid} fromMe=${fromMe} cands=${numbers.join('|')} ` +
          `matched=${matched || '-'} text=${JSON.stringify(text).slice(0, 80)}`
        );
        if (!matched) continue;
        if (!text) continue;
        queue.push({
          from: jid,
          number: matched,
          text,
          ts: Number(m.messageTimestamp) || Math.floor(Date.now() / 1000),
        });
        console.log(`[upsert] queued from=${matched} jid=${jid}`);
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
