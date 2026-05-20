"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { tradeApi } from "@/lib/api";
import PnLChart from "@/components/trade/PnLChart";

interface Portfolio {
  id: string;
  name: string;
  initial_cash: number;
  cash: number;
  market_value?: number;
  total_equity?: number;
  total_return_pct?: number;
  positions?: Position[];
  status: string;
  created_at: string;
}

interface Position {
  id: string;
  symbol: string;
  quantity: number;
  avg_cost: number;
  market_value?: number;
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

export default function TradePage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCash, setNewCash] = useState(1000000);
  const [showOrder, setShowOrder] = useState(false);
  const [orderForm, setOrderForm] = useState({ symbol: "", side: "buy", price: "", quantity: "" });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const loadPortfolios = useCallback(async () => {
    try {
      const res = await tradeApi.listPortfolios();
      setPortfolios(res.data || []);
      if (res.data?.length && !selectedId) {
        setSelectedId(res.data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  }, [selectedId]);

  const loadPortfolioDetail = useCallback(async () => {
    if (!selectedId) return;
    try {
      const res = await tradeApi.getPortfolio(selectedId);
      setPortfolio(res.data);
    } catch (err) {
      console.error(err);
    }
  }, [selectedId]);

  const loadOrders = useCallback(async () => {
    if (!selectedId) return;
    try {
      const res = await tradeApi.listOrders(selectedId);
      setOrders(res.data || []);
    } catch (err) {
      console.error(err);
    }
  }, [selectedId]);

  useEffect(() => { loadPortfolios(); }, [loadPortfolios]);
  useEffect(() => { loadPortfolioDetail(); loadOrders(); }, [loadPortfolioDetail, loadOrders]);

  const handleCreate = async () => {
    if (!newName) return;
    setLoading(true);
    try {
      await tradeApi.createPortfolio({ name: newName, initial_cash: newCash });
      setShowCreate(false);
      setNewName("");
      loadPortfolios();
    } catch (err: any) {
      setMessage("创建失败: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleOrder = async () => {
    if (!selectedId || !orderForm.symbol || !orderForm.price || !orderForm.quantity) return;
    setLoading(true);
    setMessage("");
    try {
      await tradeApi.placeOrder(selectedId, {
        symbol: orderForm.symbol,
        side: orderForm.side,
        price: Number(orderForm.price),
        quantity: Number(orderForm.quantity),
      });
      setShowOrder(false);
      setOrderForm({ symbol: "", side: "buy", price: "", quantity: "" });
      loadPortfolioDetail();
      loadOrders();
      setMessage("下单成功");
    } catch (err: any) {
      setMessage("下单失败: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <header className="border-b bg-white dark:bg-slate-900 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <h1 className="text-lg font-bold">模拟交易</h1>
          <Link href="/" className="text-sm text-slate-500 hover:text-blue-600">← 返回首页</Link>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6 flex gap-6">
        {/* 左侧：组合列表 */}
        <div className="w-56 flex-shrink-0 space-y-3">
          <button
            onClick={() => setShowCreate(true)}
            className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
          >
            + 新建组合
          </button>
          {portfolios.map(p => (
            <button
              key={p.id}
              onClick={() => setSelectedId(p.id)}
              className={`w-full text-left px-4 py-3 rounded-lg border transition-colors ${
                selectedId === p.id
                  ? "bg-blue-50 dark:bg-blue-900/20 border-blue-300"
                  : "bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800"
              }`}
            >
              <div className="font-medium text-sm">{p.name}</div>
              <div className="text-xs text-slate-500">¥{Number(p.cash).toLocaleString()}</div>
            </button>
          ))}
        </div>

        {/* 右侧：详情 */}
        <div className="flex-1 space-y-4">
          {portfolio ? (
            <>
              {/* 资产概览 */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="font-bold">{portfolio.name}</h2>
                  <button
                    onClick={() => setShowOrder(true)}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
                  >
                    下单
                  </button>
                </div>
                <div className="grid grid-cols-4 gap-4">
                  <div>
                    <div className="text-xs text-slate-500">可用现金</div>
                    <div className="text-lg font-bold">¥{Number(portfolio.cash).toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">持仓市值</div>
                    <div className="text-lg font-bold">¥{(portfolio.market_value || 0).toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">总资产</div>
                    <div className="text-lg font-bold">¥{(portfolio.total_equity || 0).toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">总收益</div>
                    <div className={`text-lg font-bold ${(portfolio.total_return_pct || 0) >= 0 ? "text-red-600" : "text-green-600"}`}>
                      {(portfolio.total_return_pct || 0).toFixed(2)}%
                    </div>
                  </div>
                </div>
              </div>

              {/* 盈亏分析 */}
              {portfolio.positions && portfolio.positions.length > 0 && (
                <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
                  <h3 className="font-bold mb-3">盈亏分析</h3>
                  <PnLChart
                    positions={portfolio.positions}
                    initialCash={portfolio.initial_cash}
                    currentCash={portfolio.cash}
                    height={250}
                  />
                </div>
              )}

              {/* 持仓 */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
                <h3 className="font-bold mb-3">持仓</h3>
                {portfolio.positions && portfolio.positions.length > 0 ? (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-slate-500 border-b">
                        <th className="py-2">股票</th>
                        <th>数量</th>
                        <th>成本价</th>
                        <th>市值</th>
                      </tr>
                    </thead>
                    <tbody>
                      {portfolio.positions.map(p => (
                        <tr key={p.id} className="border-b last:border-0">
                          <td className="py-2 font-medium">{p.symbol}</td>
                          <td>{p.quantity}</td>
                          <td>¥{Number(p.avg_cost).toFixed(2)}</td>
                          <td>¥{(p.market_value || 0).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="text-sm text-slate-400 py-4 text-center">暂无持仓</div>
                )}
              </div>

              {/* 委托记录 */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
                <h3 className="font-bold mb-3">委托记录</h3>
                {orders.length > 0 ? (
                  <div className="max-h-48 overflow-y-auto">
                    <table className="w-full text-xs">
                      <thead className="sticky top-0 bg-white dark:bg-slate-900">
                        <tr className="text-left text-slate-500 border-b">
                          <th className="py-2">时间</th>
                          <th>股票</th>
                          <th>方向</th>
                          <th>价格</th>
                          <th>数量</th>
                          <th>金额</th>
                          <th>状态</th>
                        </tr>
                      </thead>
                      <tbody>
                        {orders.map(o => (
                          <tr key={o.id} className="border-b last:border-0">
                            <td className="py-1.5">{new Date(o.created_at).toLocaleString("zh-CN")}</td>
                            <td>{o.symbol}</td>
                            <td className={o.side === "buy" ? "text-red-600" : "text-green-600"}>
                              {o.side === "buy" ? "买入" : "卖出"}
                            </td>
                            <td>¥{Number(o.price).toFixed(2)}</td>
                            <td>{o.quantity}</td>
                            <td>¥{Number(o.amount).toLocaleString()}</td>
                            <td>{o.status === "filled" ? "已成交" : o.status}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-sm text-slate-400 py-4 text-center">暂无委托</div>
                )}
              </div>
            </>
          ) : (
            <div className="bg-white dark:bg-slate-900 rounded-xl border p-12 text-center text-slate-400">
              请选择或创建一个投资组合
            </div>
          )}

          {message && (
            <div className="p-3 bg-slate-100 dark:bg-slate-800 rounded-lg text-sm">{message}</div>
          )}
        </div>
      </div>

      {/* 创建组合弹窗 */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-slate-900 rounded-xl border p-6 w-96">
            <h3 className="font-bold text-lg mb-4">新建投资组合</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-500">组合名称</label>
                <input value={newName} onChange={e => setNewName(e.target.value)}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700"
                  placeholder="如：我的第一个组合" />
              </div>
              <div>
                <label className="text-xs text-slate-500">初始资金</label>
                <input type="number" value={newCash} onChange={e => setNewCash(Number(e.target.value))}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700" />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowCreate(false)} className="flex-1 py-2 border rounded-lg text-sm">取消</button>
              <button onClick={handleCreate} disabled={loading}
                className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg text-sm font-medium">
                {loading ? "创建中..." : "创建"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 下单弹窗 */}
      {showOrder && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-slate-900 rounded-xl border p-6 w-96">
            <h3 className="font-bold text-lg mb-4">委托下单</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-500">股票代码</label>
                <input value={orderForm.symbol} onChange={e => setOrderForm(f => ({ ...f, symbol: e.target.value }))}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700"
                  placeholder="如 000001.SZ" />
              </div>
              <div>
                <label className="text-xs text-slate-500">方向</label>
                <div className="flex gap-2 mt-1">
                  <button
                    onClick={() => setOrderForm(f => ({ ...f, side: "buy" }))}
                    className={`flex-1 py-2 rounded-lg text-sm font-medium ${orderForm.side === "buy" ? "bg-red-600 text-white" : "border"}`}
                  >
                    买入
                  </button>
                  <button
                    onClick={() => setOrderForm(f => ({ ...f, side: "sell" }))}
                    className={`flex-1 py-2 rounded-lg text-sm font-medium ${orderForm.side === "sell" ? "bg-green-600 text-white" : "border"}`}
                  >
                    卖出
                  </button>
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-500">价格</label>
                <input type="number" step="0.01" value={orderForm.price}
                  onChange={e => setOrderForm(f => ({ ...f, price: e.target.value }))}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700" />
              </div>
              <div>
                <label className="text-xs text-slate-500">数量（股）</label>
                <input type="number" step="100" value={orderForm.quantity}
                  onChange={e => setOrderForm(f => ({ ...f, quantity: e.target.value }))}
                  className="w-full mt-1 px-3 py-2 border rounded-lg text-sm dark:bg-slate-800 dark:border-slate-700" />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowOrder(false)} className="flex-1 py-2 border rounded-lg text-sm">取消</button>
              <button onClick={handleOrder} disabled={loading}
                className={`flex-1 py-2 text-white rounded-lg text-sm font-medium ${
                  orderForm.side === "buy" ? "bg-red-600 hover:bg-red-700" : "bg-green-600 hover:bg-green-700"
                } disabled:opacity-50`}>
                {loading ? "提交中..." : "确认下单"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
