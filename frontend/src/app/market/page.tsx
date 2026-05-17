"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { marketApi } from "@/lib/api";
import KLineChart from "@/components/charts/KLineChart";
import { getQuoteSocket } from "@/lib/ws";

interface Stock {
  symbol: string;
  name: string;
  exchange: string;
  industry?: string;
}

interface KLineData {
  symbol: string;
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export default function MarketPage() {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState("000001.SZ");
  const [klineData, setKlineData] = useState<KLineData[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [quote, setQuote] = useState<Record<string, any> | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [search, setSearch] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const prevSymbol = useRef("");
  const searchTimer = useRef<ReturnType<typeof setTimeout>>();

  // 加载股票列表
  const loadStocks = useCallback(async (searchText?: string) => {
    setSearchLoading(true);
    try {
      const params: any = { page: 1, page_size: 100 };
      if (searchText) params.search = searchText;
      const res = await marketApi.getStocks(params);
      setStocks(res.data || []);
    } catch (err) {
      console.error("加载股票列表失败", err);
    } finally {
      setSearchLoading(false);
    }
  }, []);

  // 搜索防抖
  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => loadStocks(search || undefined), 300);
    return () => { if (searchTimer.current) clearTimeout(searchTimer.current); };
  }, [search, loadStocks]);

  // 加载 K 线
  const loadKLine = useCallback(async () => {
    setLoading(true);
    try {
      const res = await marketApi.getKLine(selectedSymbol, { period: "daily", limit: 500 });
      setKlineData(res.data || []);
    } catch {
      setKlineData([]);
    } finally {
      setLoading(false);
    }
  }, [selectedSymbol]);

  useEffect(() => { loadKLine(); }, [loadKLine]);

  // WebSocket 实时行情
  useEffect(() => {
    const ws = getQuoteSocket();
    ws.connect();
    setWsConnected(true);

    if (prevSymbol.current && prevSymbol.current !== selectedSymbol) {
      ws.unsubscribe(prevSymbol.current);
    }
    setQuote(null);
    ws.subscribe(selectedSymbol, (data: Record<string, any>) => setQuote(data));
    prevSymbol.current = selectedSymbol;
    return () => { ws.unsubscribe(selectedSymbol); };
  }, [selectedSymbol]);

  const loadRealtime = async () => {
    try {
      const res = await marketApi.getRealtime(selectedSymbol);
      if (res.data?.data) setQuote(res.data.data);
    } catch {}
  };

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <header className="border-b bg-white dark:bg-slate-900 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-bold">行情看板</h1>
            <span className={`w-2 h-2 rounded-full ${wsConnected ? "bg-green-500" : "bg-slate-300"}`} title={wsConnected ? "WS 已连接" : "WS 未连接"} />
          </div>
          <a href="/" className="text-sm text-slate-500 hover:text-blue-600">← 返回首页</a>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6 flex gap-6" style={{ height: "calc(100vh - 3.5rem)" }}>
        {/* 股票列表 */}
        <div className="w-64 flex-shrink-0 bg-white dark:bg-slate-900 rounded-xl border overflow-hidden flex flex-col">
          <div className="p-3 border-b">
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="搜索代码或名称..."
              className="w-full px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex-1 overflow-y-auto">
            {searchLoading ? (
              <div className="p-4 space-y-3">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-20 mb-1" />
                    <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-16" />
                  </div>
                ))}
              </div>
            ) : stocks.length === 0 ? (
              <div className="p-4 text-center text-sm text-slate-400">
                {search ? "未找到匹配股票" : "暂无数据，请先同步股票列表"}
              </div>
            ) : (
              stocks.map(stock => (
                <button
                  key={stock.symbol}
                  onClick={() => setSelectedSymbol(stock.symbol)}
                  className={`w-full text-left px-4 py-3 border-b last:border-b-0 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors ${
                    selectedSymbol === stock.symbol
                      ? "bg-blue-50 dark:bg-blue-900/20 border-l-4 border-l-blue-600"
                      : "border-l-4 border-l-transparent"
                  }`}
                >
                  <div className="font-medium text-sm">{stock.name}</div>
                  <div className="text-xs text-slate-500">{stock.symbol}</div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* 右侧区域 */}
        <div className="flex-1 flex flex-col gap-4 overflow-hidden">
          {/* 实时行情面板 */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border p-4 flex-shrink-0">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <h2 className="font-bold text-lg">{selectedSymbol}</h2>
                <button onClick={loadRealtime} className="px-3 py-1 text-xs border rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800">刷新行情</button>
              </div>
            </div>
            {quote ? (
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
                {[
                  { label: "最新价", key: "最新", color: "text-slate-900 dark:text-white" },
                  { label: "涨跌幅", key: "涨跌幅", color: "text-red-600" },
                  { label: "最高", key: "最高", color: "text-red-600" },
                  { label: "最低", key: "最低", color: "text-green-600" },
                  { label: "成交量", key: "成交量", color: "" },
                  { label: "成交额", key: "成交额", color: "" },
                ].map(({ label, key, color }) => {
                  const val = quote[key];
                  return (
                    <div key={key}>
                      <div className="text-xs text-slate-500">{label}</div>
                      <div className={`text-sm font-bold ${color}`}>
                        {val != null
                          ? typeof val === "number"
                            ? key === "成交额" ? `¥${(val / 1e8).toFixed(2)}亿`
                            : key === "成交量" ? `${(val / 1e4).toFixed(0)}万手`
                            : key === "涨跌幅" ? `${val}%`
                            : val.toLocaleString()
                          : String(val)
                          : "-"}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-sm text-slate-400">点击「刷新行情」获取实时数据</div>
            )}
          </div>

          {/* K 线图 */}
          <div className="flex-1 bg-white dark:bg-slate-900 rounded-xl border overflow-hidden flex flex-col min-h-0">
            <div className="p-4 border-b flex items-center justify-between flex-shrink-0">
              <h2 className="font-bold">{selectedSymbol} — 日 K 线图</h2>
              <button onClick={loadKLine} disabled={loading} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg text-sm font-medium">
                {loading ? "加载中..." : "刷新"}
              </button>
            </div>
            <div className="flex-1 p-4">
              {loading ? (
                <div className="h-full flex items-center justify-center">
                  <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full" />
                </div>
              ) : klineData.length > 0 ? (
                <KLineChart data={klineData} />
              ) : (
                <div className="h-full flex items-center justify-center text-slate-400">暂无数据，请先同步 K 线数据</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
