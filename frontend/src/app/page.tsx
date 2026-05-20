"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { dashboardApi, marketApi } from "@/lib/api";

interface DashboardData {
  market: { stock_count: number; kline_count: number; latest_synced: { symbol: string; date: string }[] };
  strategy: { total: number; active: number };
  backtest: { total: number; best_return: number | null; best_name: string | null };
  portfolio: { count: number; total_cash: number; total_equity: number; items: { id: string; name: string; equity: number; return_pct: number }[] };
  recent_orders: { id: string; symbol: string; side: string; price: number; quantity: number; created_at: string }[];
}

export default function Home() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncMsg, setSyncMsg] = useState("");
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    if (!token) {
      setLoading(false);
      setError("unauthenticated");
      return;
    }
    dashboardApi.get().then((r) => { setData(r.data); setLoading(false); }).catch((e) => {
      setLoading(false);
      if (e.response?.status === 401) {
        setError("unauthenticated");
      } else {
        setError("network");
      }
    });
  }, []);

  const handleSyncAll = async () => {
    setSyncing(true);
    setSyncMsg("正在同步...");
    try {
      const res = await marketApi.syncStocks();
      setSyncMsg(res.data.message);
    } catch (e: any) {
      setSyncMsg("失败: " + (e.response?.data?.detail || e.message));
    } finally {
      setSyncing(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <header className="border-b bg-white/80 dark:bg-slate-950/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">Q</span>
            </div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">QuantBot</h1>
          </div>
          <nav className="flex items-center gap-4 text-sm font-medium text-slate-600 dark:text-slate-400">
            <Link href="/" className="text-blue-600">首页</Link>
            <Link href="/market" className="hover:text-blue-600 transition-colors">行情</Link>
            <Link href="/strategies" className="hover:text-blue-600 transition-colors">策略</Link>
            <Link href="/backtest" className="hover:text-blue-600 transition-colors">回测</Link>
            <Link href="/trade" className="hover:text-blue-600 transition-colors">交易</Link>
            <Link href="/login" className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-medium transition-colors">登录</Link>
          </nav>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white mb-2">Dashboard</h2>
          <p className="text-slate-500">个人量化交易平台总览</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full" />
          </div>
        ) : error === "unauthenticated" ? (
          <div className="text-center py-16">
            <p className="text-slate-500 mb-4">请先登录后查看 Dashboard</p>
            <Link href="/login" className="px-4 py-2 bg-blue-600 text-white rounded-lg inline-block">去登录</Link>
          </div>
        ) : error === "network" ? (
          <div className="text-center py-16">
            <p className="text-slate-500 mb-4">加载失败，请检查后端是否运行</p>
            <button onClick={() => window.location.reload()} className="px-4 py-2 bg-blue-600 text-white rounded-lg">重试</button>
          </div>
        ) : (
          <>
            {/* 统计卡片 */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <StatCard title="股票数量" value={data.market.stock_count.toLocaleString()} icon="stock" />
              <StatCard title="K 线记录" value={data.market.kline_count.toLocaleString()} icon="chart" />
              <StatCard title="策略数量" value={`${data.strategy.total} / ${data.strategy.active} 活跃`} icon="strategy" />
              <StatCard title="回测次数" value={String(data.backtest.total)} sub={data.backtest.best_return != null ? `最佳 ${data.backtest.best_return}%` : undefined} icon="backtest" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
              {/* 资产概览 */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border p-6">
                <h3 className="font-semibold mb-4 text-slate-700 dark:text-slate-300">资产概览</h3>
                <div className="space-y-3">
                  <div className="flex justify-between"><span className="text-slate-500">组合数量</span><span className="font-medium">{data.portfolio.count}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">总现金</span><span className="font-medium">{data.portfolio.total_cash.toLocaleString()}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">总权益</span><span className="font-bold text-lg">{data.portfolio.total_equity.toLocaleString()}</span></div>
                </div>
                {data.portfolio.items.length > 0 && (
                  <div className="mt-4 pt-4 border-t space-y-2">
                    {data.portfolio.items.map((p) => (
                      <div key={p.id} className="flex justify-between items-center text-sm">
                        <span className="text-slate-600 dark:text-slate-400">{p.name}</span>
                        <span className={p.return_pct >= 0 ? "text-red-600" : "text-green-600"}>
                          {p.return_pct >= 0 ? "+" : ""}{p.return_pct}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                <Link href="/trade" className="mt-4 block text-center text-sm text-blue-600 hover:underline">进入交易 →</Link>
              </div>

              {/* 最近同步 */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border p-6">
                <h3 className="font-semibold mb-4 text-slate-700 dark:text-slate-300">最近同步</h3>
                {data.market.latest_synced.length === 0 ? (
                  <p className="text-slate-400 text-sm">暂无数据</p>
                ) : (
                  <div className="space-y-2">
                    {data.market.latest_synced.map((s) => (
                      <div key={s.symbol} className="flex justify-between text-sm">
                        <span className="font-mono">{s.symbol}</span>
                        <span className="text-slate-500">{s.date}</span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="mt-4 flex gap-2">
                  <button onClick={handleSyncAll} disabled={syncing} className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm rounded-lg transition-colors">
                    {syncing ? "同步中..." : "同步股票列表"}
                  </button>
                </div>
                {syncMsg && <p className="mt-2 text-xs text-slate-500">{syncMsg}</p>}
              </div>

              {/* 最近交易 */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border p-6">
                <h3 className="font-semibold mb-4 text-slate-700 dark:text-slate-300">最近交易</h3>
                {data.recent_orders.length === 0 ? (
                  <p className="text-slate-400 text-sm">暂无交易记录</p>
                ) : (
                  <div className="space-y-2">
                    {data.recent_orders.slice(0, 5).map((o) => (
                      <div key={o.id} className="flex justify-between items-center text-sm">
                        <div className="flex items-center gap-2">
                          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${o.side === "buy" ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"}`}>
                            {o.side === "buy" ? "买" : "卖"}
                          </span>
                          <span className="font-mono">{o.symbol}</span>
                        </div>
                        <span className="text-slate-500">{o.quantity}股 @{o.price}</span>
                      </div>
                    ))}
                  </div>
                )}
                <Link href="/trade" className="mt-4 block text-center text-sm text-blue-600 hover:underline">查看全部 →</Link>
              </div>
            </div>

            {/* 快速入口 */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <QuickLink href="/market" title="行情中心" desc="实时行情与 K 线" color="blue" />
              <QuickLink href="/strategies" title="策略管理" desc="编写与管理策略" color="green" />
              <QuickLink href="/backtest" title="策略回测" desc="历史回测验证" color="purple" />
              <QuickLink href="/trade" title="模拟交易" desc="虚拟资金实战" color="orange" />
            </div>
          </>
        )}
      </div>
    </main>
  );
}

function StatCard({ title, value, sub, icon }: { title: string; value: string; sub?: string; icon: string }) {
  const colors: Record<string, string> = { stock: "bg-blue-100 text-blue-600", chart: "bg-green-100 text-green-600", strategy: "bg-purple-100 text-purple-600", backtest: "bg-orange-100 text-orange-600" };
  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border p-5">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[icon] || colors.stock}`}>
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
        </div>
        <div>
          <p className="text-xs text-slate-500">{title}</p>
          <p className="text-lg font-bold">{value}</p>
          {sub && <p className="text-xs text-slate-400">{sub}</p>}
        </div>
      </div>
    </div>
  );
}

function QuickLink({ href, title, desc, color }: { href: string; title: string; desc: string; color: string }) {
  const border: Record<string, string> = { blue: "hover:border-blue-300", green: "hover:border-green-300", purple: "hover:border-purple-300", orange: "hover:border-orange-300" };
  return (
    <Link href={href} className={`bg-white dark:bg-slate-900 rounded-xl border p-5 transition-all hover:shadow-md ${border[color] || ""}`}>
      <h4 className="font-semibold mb-1">{title}</h4>
      <p className="text-sm text-slate-500">{desc}</p>
    </Link>
  );
}
