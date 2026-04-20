// Tiny loopback HTTP API the Python agent talks to.
// Endpoints:
//   GET  /health           -> {ok, waConnected, queued}
//   POST /send  {to, text} -> {ok, to}
//   GET  /poll?since=N     -> {messages, cursor}
// Auth: every request must carry `Authorization: Bearer <BRIDGE_TOKEN>`.
// The bridge binds to 127.0.0.1 only; the bearer token is the final gate in
// case anything else on the loopback tries to reach it.

import Fastify from 'fastify';
import { config } from './config.js';

export function buildApi({ queue, wa }) {
  const app = Fastify({ logger: false });

  app.addHook('onRequest', async (req, reply) => {
    if (req.url === '/health') return;
    const auth = req.headers['authorization'] || '';
    if (auth !== `Bearer ${config.token}`) {
      reply.code(401).send({ error: 'unauthorized' });
    }
  });

  app.get('/health', async () => ({
    ok: true,
    waConnected: wa.isConnected(),
    queued: queue.size(),
  }));

  app.post('/send', async (req, reply) => {
    const { to, text } = req.body || {};
    if (!to || !text) return reply.code(400).send({ error: 'to and text required' });
    try {
      const res = await wa.send(to, String(text));
      return { ok: true, to: res.to };
    } catch (e) {
      req.log.error(e);
      return reply.code(500).send({ error: String(e?.message || e) });
    }
  });

  app.get('/poll', async (req) => {
    const cursor = req.query?.since ?? 0;
    return queue.pollSince(cursor);
  });

  return app;
}
