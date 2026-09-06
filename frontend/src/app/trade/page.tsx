"use client";

import { useState, useEffect, useCallback } from "react";
import { tradeApi, marketApi } from "@/lib/api";
import PnLChart from "@/components/trade/PnLChart";

interface Portfolio {
  id: string;
  name: string;
  initial_cash: number;
  cash: number;
  total_equity: number;
  total_return_pct: number;
  position_count: number;
  positions: Position[];
  status: string;
}

interface Position {
  id: string;
  symbol: string;
  quantity: number;
  avg_cost: number;
  market_value: number;
}

interface Order {
  id: string;
  symbol: string;
  side: string;
  price: number;
  quantity: number;
  amount: number;
  commission: number;
  status: string;
  created_at: string;
}

interface RealtimeSummary {
  totalEquity: number;
  totalPnl: number;
  totalPnlPct: number;
  marketValue: number;
}

export default function TradePage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState<Portfolio | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [rtSummary, setRtSummary] = useState<RealtimeSummary | null>(null);
  const [rtLoading, setRtLoading] = useState(false);

  // 新建组合
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCash, setNewCash] = useState(1000000);

  // 下单
  const [orderSymbol, setOrderSymbol] = useState("");
  const [orderSide, setOrderSide] = useState<"buy" | "sell">("buy");
  const [orderPrice, setOrderPrice] = useState("");
  const [orderQuantity, setOrderQuantity] = useState("");
  const [orderLoading, setOrderLoading] = useState(false);

  const loadPortfolios = useCallback(async () => {
    try {
      const res = await tradeApi.listPortfolios();
      setPortfolios(res.data || []);
    } catch (err: any) {
      setMessage("加载组合失败: " + (err.response?.data?.detail || err.message));
    }
  }, []);

  useEffect(() => {
    loadPortfolios();
  }, [loadPortfolios]);

  const fetchRealtimeForPortfolio = async (portfolio: Portfolio) => {
    setRtLoading(true);
    const positions = portfolio.positions || [];
    if (positions.length === 0) {
      setRtSummary({
        totalEquity: portfolio.cash,
        totalPnl: 0,
        totalPnlPct: 0,
        marketValue: 0,
      });
      setRtLoading(false);
      return;
    }
    const priceMap: Record<string, number> = {};
    await Promise.all(
      positions.map(async (p) => {
        try {
          const res = await marketApi.getRealtime(p.symbol);
          const price = res.data?.data?.["最新"];
          if (typeof price === "number") priceMap[p.symbol] = price;
        } catch {}
      })
    );
    let marketValue = 0;
    let costValue = 0;
    const enriched = positions.map((p) => {
      const cp = priceMap[p.symbol] || p.avg_cost;
      const mv = cp * p.quantity;
      marketValue += mv;
      costValue += p.avg_cost * p.quantity;
      return { ...p, current_price: cp, market_value: mv };
    });
    const totalEquity = portfolio.cash + marketValue;
    const totalPnl = marketValue - costValue;
    const totalPnlPct = costValue > 0 ? (totalPnl / costValue) * 100 : 0;
    setSelectedPortfolio({ ...portfolio, positions: enriched });
    setRtSummary({ totalEquity, totalPnl, totalPnlPct, marketValue });
    setRtLoading(false);
  };

  const loadPortfolioDetail = async (id: string) => {
    setLoading(true);
    try {
      const res = await tradeApi.getPortfolio(id);
      const portfolio = res.data;
      // 加载订单
      const oRes = await tradeApi.listOrders(id, { page_size: 50 });
      setOrders(oRes.data || []);
      // 并行加载实时行情
      await fetchRealtimeForPortfolio(portfolio);
    } catch (err: any) {
      setMessage("加载详情失败: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePortfolio = async () => {
    if (!newName) return;
    try {
      await tradeApi.createPortfolio({ name: newName, initial_cash: newCash });
      setShowCreate(false);
      setNewName("");
      setNewCash(1000000);
      loadPortfolios();
      setMessage("组合创建成功");
    } catch (err: any) {
      setMessage("创建失败: " + (err.response?.data?.detail || err.message));
    }
  };

  const handlePlaceOrder = async () => {
    if (!selectedPortfolio || !orderSymbol || !orderPrice || !orderQuantity) return;
    setOrderLoading(true);
    try {
      await tradeApi.placeOrder(selectedPortfolio.id, {
        symbol: orderSymbol,
        side: orderSide,
        price: Number(orderPrice),
        quantity: Number(orderQuantity),
      });
      setMessage("下单成功");
      setOrderSymbol("");
      setOrderPrice("");
      setOrderQuantity("");
      loadPortfolioDetail(selectedPortfolio.id);
    } catch (err: any) {
      setMessage("下单失败: " + (err.response?.data?.detail || err.message));
    } finally {
      setOrderLoading(false);
    }
  };

  const fetchRealtimePrice = async () => {
    if (!orderSymbol) return;
    try {
      const res = await marketApi.getRealtime(orderSymbol);
      if (res.data?.data?.["最新"]) {
        setOrderPrice(String(res.data.data["最新"]));
      }
    } catch {}
  };

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-2xl font-bold">模拟交易</h2>
            <p className="text-sm text-slate-500 mt-1">管理虚拟投资组合，执行模拟下单</p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium w-fit"
          >
            + 新建组合
          </button>
        </div>

        {message && (
          <div className="mb-4 p-3 bg-slate-100 dark:bg-slate-800 rounded-lg text-sm flex justify-between items-center">
            <span>{message}</span>
            <button onClick={() => setMessage("")} className="text-slate-400 hover:text-slate-600">✕</button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 组合列表 */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-white dark:bg-slate-900 rounded-xl border overflow-hidden">
              <div className="p-4 border-b">
                <h3 className="font-semibold">投资组合</h3>
              </div>
              {portfolios.length === 0 ? (
                <div className="p-8 text-center text-sm text-slate-400">
                  暂无组合，点击「新建组合」开始
                </div>
              ) : (
                <div className="divide-y">
                  {portfolios.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => loadPortfolioDetail(p.id)}
                      className={`w-full text-left px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors ${
                        selectedPortfolio?.id === p.id ? "bg-blue-50 dark:bg-blue-900/20 border-l-4 border-l-blue-600" : "border-l-4 border-l-transparent"
                      }`}
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-medium text-sm">{p.name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          p.status === "active" ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"
                        }`}>
                          {p.status === "active" ? "运行中" : "已关闭"}
                        </span>
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        资产 ¥{p.total_equity?.toLocaleString?.() ?? "-"} · 收益 {p.total_return_pct != null ? `${p.total_return_pct}%` : "-"}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 组合详情 */}
          <div className="lg:col-span-2 space-y-4">
            {selectedPortfolio ? (
              <>
                {/* 资产概览 */}
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">资产概览</h3>
                  <button
                    onClick={() => fetchRealtimeForPortfolio(selectedPortfolio)}
                    disabled={rtLoading}
                    className="px-3 py-1 text-xs border rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
                  >
                    {rtLoading ? "更新中..." : "刷新行情"}
                  </button>
                </div>
                <PnLChart
                  positions={selectedPortfolio.positions || []}
                  initialCash={selectedPortfolio.initial_cash}
                  currentCash={selectedPortfolio.cash}
                />
                {rtSummary && (
                  <div className="text-xs text-slate-500 -mt-2 mb-2">
                    基于实时行情计算：总资产 ¥{rtSummary.totalEquity.toLocaleString()} · 浮动盈亏{" "}
                    <span className={rtSummary.totalPnl >= 0 ? "text-red-600" : "text-green-600"}>
                      {rtSummary.totalPnl >= 0 ? "+" : ""}¥{rtSummary.totalPnl.toLocaleString()} ({rtSummary.totalPnlPct.toFixed(2)}%)
                    </span>
                  </div>
                )}

                {/* 下单面板 */}
                <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
                  <h3 className="font-semibold mb-3">下单</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
                    <div className="sm:col-span-2">
                      <label className="text-xs text-slate-500">股票代码</label>
                      <div className="flex gap-2">
                        <input
                          value={orderSymbol}
                          onChange={(e) => setOrderSymbol(e.target.value)}
                          placeholder="000001.SZ"
                          className="flex-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700"
                        />
                        <button
                          onClick={fetchRealtimePrice}
                          className="px-3 py-2 border rounded-lg text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
                          title="获取最新价"
                        >
                          询价
                        </button>
                      </div>
                    </div>
                    <div>
                      <label className="text-xs text-slate-500">方向</label>
                      <select
                        value={orderSide}
                        onChange={(e) => setOrderSide(e.target.value as "buy" | "sell")}
                        className="w-full px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700"
                      >
                        <option value="buy">买入</option>
                        <option value="sell">卖出</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-slate-500">价格</label>
                      <input
                        type="number"
                        value={orderPrice}
                        onChange={(e) => setOrderPrice(e.target.value)}
                        placeholder="0.00"
                        className="w-full px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-slate-500">数量</label>
                      <input
                        type="number"
                        value={orderQuantity}
                        onChange={(e) => setOrderQuantity(e.target.value)}
                        placeholder="100的整数倍"
                        step={100}
                        className="w-full px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handlePlaceOrder}
                    disabled={orderLoading || !orderSymbol || !orderPrice || !orderQuantity}
                    className="mt-3 w-full sm:w-auto px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    {orderLoading ? "提交中..." : "提交订单"}
                  </button>
                </div>

                {/* 订单历史 */}
                <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
                  <h3 className="font-semibold mb-3">最近订单</h3>
                  {orders.length === 0 ? (
                    <div className="text-center text-sm text-slate-400 py-6">暂无订单记录</div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-slate-500 border-b">
                            <th className="py-2 pr-4">时间</th>
                            <th className="py-2 pr-4">代码</th>
                            <th className="py-2 pr-4">方向</th>
                            <th className="py-2 pr-4">价格</th>
                            <th className="py-2 pr-4">数量</th>
                            <th className="py-2 pr-4">金额</th>
                            <th className="py-2">手续费</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {orders.map((o) => (
                            <tr key={o.id}>
                              <td className="py-2 pr-4 text-slate-500 text-xs whitespace-nowrap">
                                {new Date(o.created_at).toLocaleString("zh-CN")}
                              </td>
                              <td className="py-2 pr-4 font-mono">{o.symbol}</td>
                              <td className={`py-2 pr-4 font-medium ${o.side === "buy" ? "text-red-600" : "text-green-600"}`}>
                                {o.side === "buy" ? "买入" : "卖出"}
                              </td>
                              <td className="py-2 pr-4">{o.price.toFixed(2)}</td>
                              <td className="py-2 pr-4">{o.quantity}</td>
                              <td className="py-2 pr-4">¥{o.amount.toLocaleString()}</td>
                              <td className="py-2 text-slate-500">¥{o.commission?.toFixed(2) ?? "-"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="bg-white dark:bg-slate-900 rounded-xl border p-12 text-center text-slate-400">
                {loading ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full" />
                  </div>
                ) : (
                  <>
                    <p className="mb-2">选择一个投资组合查看详情</p>
                    <p className="text-sm">或创建新组合开始模拟交易</p>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 创建组合弹窗 */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl border p-6 w-full max-w-md">
            <h3 className="font-bold text-lg mb-4">新建投资组合</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-500">组合名称</label>
                <input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="例如：我的第一个组合"
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700"
                />
              </div>
              <div>
                <label className="text-xs text-slate-500">初始资金</label>
                <input
                  type="number"
                  value={newCash}
                  onChange={(e) => setNewCash(Number(e.target.value))}
                  step={10000}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700"
                />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowCreate(false)} className="flex-1 py-2 border rounded-lg text-sm">
                取消
              </button>
              <button
                onClick={handleCreatePortfolio}
                disabled={!newName}
                className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg text-sm font-medium"
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
