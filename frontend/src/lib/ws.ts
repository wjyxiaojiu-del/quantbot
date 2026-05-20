type MessageHandler = (data: any) => void;

class QuoteSocket {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private url: string;

  constructor() {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    this.url = base.replace(/^http/, "ws") + "/api/v1/ws/quotes";
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log("[WS] connected");
      // 重新订阅
      for (const symbol of Array.from(this.handlers.keys())) {
        this.ws?.send(JSON.stringify({ action: "subscribe", symbol }));
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "quote" && msg.symbol) {
          this.handlers.get(msg.symbol)?.forEach(fn => fn(msg.data));
        }
      } catch {}
    };

    this.ws.onclose = () => {
      console.log("[WS] disconnected, reconnecting in 3s...");
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  subscribe(symbol: string, handler: MessageHandler) {
    if (!this.handlers.has(symbol)) {
      this.handlers.set(symbol, new Set());
    }
    this.handlers.get(symbol)!.add(handler);

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: "subscribe", symbol }));
    }
  }

  unsubscribe(symbol: string) {
    this.handlers.delete(symbol);
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: "unsubscribe", symbol }));
    }
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
