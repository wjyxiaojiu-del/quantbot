type MessageHandler = (data: any) => void;

class QuoteSocket {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pendingSubscribes: Set<string> = new Set();
  private url: string;

  constructor() {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    this.url = base.replace(/^http/, "ws") + "/api/v1/ws/quotes";
  }

  private safeSend(msg: object) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) return;

    const ws = new WebSocket(this.url);
    this.ws = ws;

    ws.onopen = () => {
      if (this.ws !== ws) return; // stale instance
      console.log("[WS] connected");
      for (const symbol of Array.from(this.handlers.keys())) {
        this.safeSend({ action: "subscribe", symbol });
      }
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "quote" && msg.symbol) {
          this.handlers.get(msg.symbol)?.forEach(fn => fn(msg.data));
        }
      } catch {}
    };

    ws.onclose = () => {
      if (this.ws !== ws) return;
      this.ws = null;
      console.log("[WS] disconnected, reconnecting in 3s...");
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }

  subscribe(symbol: string, handler: MessageHandler) {
    if (!this.handlers.has(symbol)) {
      this.handlers.set(symbol, new Set());
    }
    this.handlers.get(symbol)!.add(handler);
    this.safeSend({ action: "subscribe", symbol });
  }

  unsubscribe(symbol: string) {
    this.handlers.delete(symbol);
    this.safeSend({ action: "unsubscribe", symbol });
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
    this.handlers.clear();
  }
}

// 单例
let instance: QuoteSocket | null = null;

export function getQuoteSocket(): QuoteSocket {
  if (typeof window === "undefined") {
    // SSR 环境返回空壳
    return { connect() {}, subscribe() {}, unsubscribe() {}, disconnect() {} } as any;
  }
  if (!instance) {
    instance = new QuoteSocket();
  }
  return instance;
}
