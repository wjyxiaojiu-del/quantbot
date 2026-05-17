import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// 自动附加 token
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// ── 认证 ──
export const authApi = {
  login: (data: { username: string; password: string }) =>
    api.post("/auth/login", data),
  register: (data: { username: string; email: string; password: string }) =>
    api.post("/auth/register", data),
  me: () => api.get("/auth/me"),
};

// ── 策略模板 ──
export const templateApi = {
  list: () => api.get("/templates"),
  get: (id: string) => api.get(`/templates/${id}`),
};

// ── 行情 ──
export const marketApi = {
  getStocks: (params?: { exchange?: string; page?: number; page_size?: number }) =>
    api.get("/market/stocks", { params }),
  getKLine: (symbol: string, params?: { period?: string; start_date?: string; end_date?: string; limit?: number }) =>
    api.get(`/market/stocks/${symbol}/kline`, { params }),
  getRealtime: (symbol: string) =>
    api.get(`/market/stocks/${symbol}/realtime`),
  syncStocks: () =>
    api.post("/market/stocks/sync-all"),
  syncKLine: (data: { symbols?: string[]; period?: string; start_date?: string; end_date?: string }) =>
    api.post("/market/sync", data),
};

// ── 策略 ──
export const strategyApi = {
  list: (params?: { status?: string; page?: number; page_size?: number }) =>
    api.get("/strategies", { params }),
  get: (id: string) => api.get(`/strategies/${id}`),
  create: (data: { name: string; description?: string; code: string; params?: Record<string, any> }) =>
    api.post("/strategies", data),
  update: (id: string, data: Record<string, any>) =>
    api.put(`/strategies/${id}`, data),
  delete: (id: string) => api.delete(`/strategies/${id}`),
};

// ── 回测 ──
export const backtestApi = {
  run: (data: {
    strategy_code: string;
    symbols: string[];
    start_date: string;
    end_date: string;
    initial_cash?: number;
    params?: Record<string, any>;
  }) => api.post("/backtest/run", data),
  history: (params?: { page?: number; page_size?: number }) =>
    api.get("/backtest/history", { params }),
  getDetail: (id: string) => api.get(`/backtest/${id}`),
};

// ── Dashboard ──
export const dashboardApi = {
  get: () => api.get("/dashboard"),
};

// ── 交易 ──
export const tradeApi = {
  listPortfolios: () => api.get("/trade/portfolios"),
  createPortfolio: (data: { name: string; initial_cash?: number }) =>
    api.post("/trade/portfolios", data),
  getPortfolio: (id: string) => api.get(`/trade/portfolios/${id}`),
  placeOrder: (portfolioId: string, data: { symbol: string; side: string; price: number; quantity: number }) =>
    api.post(`/trade/portfolios/${portfolioId}/orders`, data),
  listOrders: (portfolioId: string, params?: { page?: number; page_size?: number }) =>
    api.get(`/trade/portfolios/${portfolioId}/orders`, { params }),
};

export default api;
