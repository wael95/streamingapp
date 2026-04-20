const MAX = 500;

export class MessageQueue {
  constructor() {
    this.items = [];
    this.nextId = 1;
  }

  push(msg) {
    const entry = { id: this.nextId++, ...msg };
    this.items.push(entry);
    if (this.items.length > MAX) this.items.splice(0, this.items.length - MAX);
    return entry;
  }

  pollSince(cursor) {
    const since = Number(cursor) || 0;
    const msgs = this.items.filter(m => m.id > since);
    const nextCursor = msgs.length ? msgs[msgs.length - 1].id : since;
    return { messages: msgs, cursor: nextCursor };
  }

  size() {
    return this.items.length;
  }
}
