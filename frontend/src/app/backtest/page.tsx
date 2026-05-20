"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { backtestApi, templateApi } from "@/lib/api";
import KLineChart from "@/components/charts/KLineChart";
import EquityChart from "@/components/charts/EquityChart";
import CodeEditor from "@/components/strategy/CodeEditor";

const DEFAULT_STRATEGY = `import pandas as pd

def generate_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    \"\"\"
    双均线策略示例
    必须返回包含 'signal' 列的 DataFrame
    signal: 1=买入, -1=卖出, 0=持有
    \"\"\"
    short = params.get("short_window", 5)
    long = params.get("long_window", 20)

    df["ma_short"] = df["close"].rolling(short).mean()
    df["ma_long"] = df["close"].rolling(long).mean()

    df["signal"] = 0
    df.loc[df["ma_short"] > df["ma_long"], "signal"] = 1
    df.loc[df["ma_short"] <= df["ma_long"], "signal"] = -1

    # 只在交叉点产生信号
    df["signal_change"] = df["signal"].diff()
    df["signal"] = 0
    df.loc[df["signal_change"] > 0, "signal"] = 1   # 金叉买入
    df.loc[df["signal_change"] < 0, "signal"] = -1   # 死叉卖出

    return df
`;

interface Metrics {
  total_return: number;
  annual_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  volatility: number;
  win_rate: number;
  profit_loss_ratio: number;
  trade_count: number;
  initial_cash: number;
  final_equity: number;
}

export default function BacktestPage() {
  const [code, setCode] = useState(DEFAULT_STRATEGY);
  const [symbol, setSymbol] = useState("000001.SZ");
  const [symbols, setSymbols] = useState<string[]>(["000001.SZ"]);
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2024-12-31");
  const [initialCash, setInitialCash] = useState(1000000);
  const [shortWindow, setShortWindow] = useState(5);
  const [longWindow, setLongWindow] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [equityCurve, setEquityCurve] = useState<any[]>([]);
  const [trades, setTrades] = useState<any[]>([]);
  const [klineData, setKlineData] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    templateApi.list().then(res => setTemplates(res.data || [])).catch(() => {});
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const res = await backtestApi.history({ page_size: 10 });
      setHistory(res.data?.items || []);
    } catch {}
  };

  const loadTemplate = (id: string) => {
    const t = templates.find(t => t.id === id);
    if (t) {
      setCode(t.code);
      setShortWindow(t.params?.short_window || t.params?.fast || t.params?.period || 5);
      setLongWindow(t.params?.long_window || t.params?.slow || t.params?.overbought || 20);
    }
  };

  const handleRun = async () => {
    setLoading(true);
    setError("");
    setMetrics(null);
    try {
      const res = await backtestApi.run({
        strategy_code: code,
        symbols: symbols.length > 0 ? symbols : [symbol],
        start_date: startDate,
        end_date: endDate,
        initial_cash: initialCash,
        params: { short_window: shortWindow, long_window: longWindow },
      });
      setMetrics(res.data.metrics);
      setEquityCurve(res.data.equity_curve || []);
      setTrades(res.data.trades || []);

      // 同时加载 K 线数据用于展示
      const displaySymbol = symbols[0] || symbol;
      const { marketApi } = await import("@/lib/api");
      const kRes = await marketApi.getKLine(displaySymbol, {
        start_date: startDate,
        end_date: endDate,
        limit: 2000,
      });
      setKlineData(kRes.data || []);
      loadHistory(); // 刷新历史
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <header className="border-b bg-white dark:bg-slate-900 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <h1 className="text-lg font-bold">策略回测</h1>
          <Link href="/" className="text-sm text-slate-500 hover:text-blue-600">← 返回首页</Link>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 左侧：策略编辑 */}
        <div className="space-y-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
            <h2 className="font-bold mb-3">回测参数</h2>
            {templates.length > 0 && (
              <div className="mb-3">
                <label className="text-xs text-slate-500">策略模板</label>
                <select
                  onChange={e => loadTemplate(e.target.value)}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700"
                  defaultValue=""
                >
                  <option value="" disabled>选择内置策略模板...</option>
                  {templates.map(t => (
                    <option key={t.id} value={t.id}>{t.name} — {t.description}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="text-xs text-slate-500">股票代码（多只用逗号分隔）</label>
                <input
                  value={symbols.join(",")}
                  onChange={e => {
                    const raw = e.target.value;
                    const arr = raw.split(",").map(s => s.trim()).filter(Boolean);
                    setSymbols(arr);
                    if (arr.length === 1) setSymbol(arr[0]);
                  }}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700"
                  placeholder="000001.SZ,600519.SH"
                />
              </div>
              <div>
                <label className="text-xs text-slate-500">初始资金</label>
                <input type="number" value={initialCash} onChange={e => setInitialCash(Number(e.target.value))}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div>
                <label className="text-xs text-slate-500">开始日期</label>
                <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div>
                <label className="text-xs text-slate-500">结束日期</label>
                <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div>
                <label className="text-xs text-slate-500">短均线</label>
                <input type="number" value={shortWindow} onChange={e => setShortWindow(Number(e.target.value))}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div>
                <label className="text-xs text-slate-500">长均线</label>
                <input type="number" value={longWindow} onChange={e => setLongWindow(Number(e.target.value))}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700" />
              </div>
            </div>
          </div>

          <div>
            <h2 className="font-bold mb-3">策略代码</h2>
            <CodeEditor
              value={code}
              onChange={setCode}
              height={350}
            />
          </div>

          <button
            onClick={handleRun}
            disabled={loading}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
          >
            {loading && (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            )}
            {loading ? "回测中..." : "运行回测"}
          </button>

          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300 whitespace-pre-wrap">
              {error}
            </div>
          )}
        </div>

        {/* 右侧：结果 */}
        <div className="space-y-4">
          {metrics && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
              <h2 className="font-bold mb-3">绩效指标</h2>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "总收益率", value: `${metrics.total_return}%`, color: metrics.total_return >= 0 ? "text-red-600" : "text-green-600" },
                  { label: "年化收益", value: `${metrics.annual_return}%`, color: metrics.annual_return >= 0 ? "text-red-600" : "text-green-600" },
                  { label: "夏普比率", value: metrics.sharpe_ratio.toFixed(4) },
                  { label: "最大回撤", value: `${metrics.max_drawdown}%`, color: "text-green-600" },
                  { label: "波动率", value: `${metrics.volatility}%` },
                  { label: "胜率", value: `${metrics.win_rate}%` },
                  { label: "盈亏比", value: metrics.profit_loss_ratio.toFixed(2) },
                  { label: "交易次数", value: String(metrics.trade_count) },
                ].map((item) => (
                  <div key={item.label} className="flex justify-between items-center py-2 px-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                    <span className="text-xs text-slate-500">{item.label}</span>
                    <span className={`text-sm font-bold ${item.color || ""}`}>{item.value}</span>
                  </div>
                ))}
              </div>
              <div className="mt-3 flex justify-between text-sm">
                <span className="text-slate-500">初始资金: ¥{metrics.initial_cash.toLocaleString()}</span>
                <span className="font-bold">最终资产: ¥{metrics.final_equity.toLocaleString()}</span>
              </div>
            </div>
          )}

          {equityCurve.length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
              <h2 className="font-bold mb-3">资金曲线</h2>
              <EquityChart
                data={equityCurve}
                benchmark={[]}
                height={250}
              />
            </div>
          )}

          {klineData.length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
              <h2 className="font-bold mb-3">K 线图</h2>
              <div className="h-64">
                <KLineChart data={klineData} />
              </div>
            </div>
          )}

          {trades.length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
              <h2 className="font-bold mb-3">交易记录</h2>
              <div className="max-h-64 overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-white dark:bg-slate-900">
                    <tr className="text-left text-slate-500 border-b">
                      <th className="py-2">日期</th>
                      <th>方向</th>
                      <th>价格</th>
                      <th>数量</th>
                      <th>金额</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-1.5">{t.trade_date}</td>
                        <td className={t.side === "buy" ? "text-red-600" : "text-green-600"}>
                          {t.side === "buy" ? "买入" : "卖出"}
                        </td>
                        <td>{t.price.toFixed(2)}</td>
                        <td>{t.quantity}</td>
                        <td>¥{t.amount.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {history.length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-bold">回测历史</h2>
                <button onClick={() => setShowHistory(!showHistory)} className="text-xs text-blue-600 hover:underline">
                  {showHistory ? "收起" : `展开 (${history.length})`}
                </button>
              </div>
              {showHistory && (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {history.map((h: any) => (
                    <div key={h.id} className="flex items-center justify-between py-2 px-3 bg-slate-50 dark:bg-slate-800 rounded-lg text-xs">
                      <div>
                        <div className="font-medium">{h.name}</div>
                        <div className="text-slate-400">{new Date(h.created_at).toLocaleString("zh-CN")}</div>
                      </div>
                      <div className="text-right">
                        <div className={h.total_return >= 0 ? "text-red-600 font-bold" : "text-green-600 font-bold"}>
                          {h.total_return != null ? `${h.total_return}%` : "-"}
                        </div>
                        <div className="text-slate-400">夏普 {h.sharpe_ratio?.toFixed(2) ?? "-"}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {!metrics && !loading && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border p-12 text-center text-slate-400">
              配置参数后点击「运行回测」查看结果
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

