// WhatsApp bridge entrypoint.
//
// Responsibilities:
//   1. Boot a Baileys socket that logs into WhatsApp via the personal phone.
//      On first run it prints a QR code to stdout; you scan it with your
//      phone (WhatsApp -> Linked devices). Session files are saved in ./auth
//      so subsequent boots are automatic.
//   2. Keep an in-memory ring buffer of inbound messages from allowlisted
//      senders only.
//   3. Expose a tiny HTTP API on 127.0.0.1 that the Python agent polls for
//      new messages and posts to for outbound messages.
//
// This file is kept short; wiring lives here, logic lives in ./baileys.js
// and ./api.js. Launch directly with `node src/index.js` or via launchd.

import { config } from './config.js';
import { MessageQueue } from './queue.js';
import { startBaileys } from './baileys.js';
import { buildApi } from './api.js';

async function main() {
  const queue = new MessageQueue();
  const wa = await startBaileys({ queue });
  const app = buildApi({ queue, wa });

  await app.listen({ host: config.host, port: config.port });
  console.log(`[bridge] listening on http://${config.host}:${config.port}`);
  console.log(`[bridge] allowlist: ${config.allowedNumbers.join(',') || '(empty)'}`);
}

main().catch((e) => {
  console.error('[bridge] fatal', e);
  process.exit(1);
});
