import pandas as pd
import numpy as np
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import logging
import traceback

from app.services.risk.manager import RiskManager, RiskConfig
from app.services.strategy.sandbox import safe_exec_strategy

logger = logging.getLogger(__name__)


def _d(value, precision: str = "0.0001") -> Decimal:
    """将 float/int/str 转为 Decimal，统一精度"""
    if isinstance(value, Decimal):
        return value.quantize(Decimal(precision), rounding=ROUND_HALF_UP)
    return Decimal(str(value)).quantize(Decimal(precision), rounding=ROUND_HALF_UP)


def _f(value) -> float:
    """Decimal → float，用于输出边界"""
    if isinstance(value, Decimal):
        return float(value)
    return value


# A 股交易费率
_COMMISSION_RATE = Decimal("0.0003")
_MIN_COMMISSION = Decimal("5.0")
_STAMP_TAX_RATE = Decimal("0.001")


@dataclass
class Position:
    symbol: str
    quantity: int = 0
    avg_cost: Decimal = Decimal("0")
    market_value: Decimal = Decimal("0")

    @property
    def unrealized_pnl(self) -> Decimal:
        return self.market_value - self.avg_cost * self.quantity


@dataclass
class Trade:
    symbol: str
    side: str  # "buy" / "sell"
    price: Decimal
    quantity: int
    amount: Decimal
    commission: Decimal
    trade_date: str
    reason: str = ""


@dataclass
class Portfolio:
    cash: Decimal = Decimal("1000000")
    initial_cash: Decimal = Decimal("1000000")
    positions: Dict[str, Position] = field(default_factory=dict)
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[dict] = field(default_factory=list)
    daily_pnl: List[Decimal] = field(default_factory=list)

    @property
    def total_market_value(self) -> Decimal:
        if not self.positions:
            return Decimal("0")
        return sum(p.market_value for p in self.positions.values())

    @property
    def total_equity(self) -> Decimal:
        return self.cash + self.total_market_value

    def update_market_price(self, symbol: str, price: Decimal):
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos.market_value = pos.quantity * price

    def buy(self, symbol: str, price: Decimal, quantity: int, trade_date: str, commission_rate: Decimal = _COMMISSION_RATE, reason: str = "") -> Optional[Trade]:
        amount = price * quantity
        commission = max(amount * commission_rate, _MIN_COMMISSION)
        total_cost = amount + commission
        if total_cost > self.cash:
            return None
        if quantity <= 0:
            return None

        self.cash -= total_cost
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_qty = pos.quantity + quantity
            pos.avg_cost = _d((pos.avg_cost * pos.quantity + price * quantity) / total_qty)
            pos.quantity = total_qty
            pos.market_value = total_qty * price
        else:
            self.positions[symbol] = Position(
                symbol=symbol, quantity=quantity,
                avg_cost=price, market_value=quantity * price
            )

        trade = Trade(
            symbol=symbol, side="buy", price=price,
            quantity=quantity, amount=amount, commission=commission,
            trade_date=trade_date, reason=reason
        )
        self.trades.append(trade)
        return trade

    def sell(self, symbol: str, price: Decimal, quantity: int, trade_date: str, commission_rate: Decimal = _COMMISSION_RATE, reason: str = "") -> Optional[Trade]:
        if symbol not in self.positions:
            return None
        pos = self.positions[symbol]
        if quantity > pos.quantity:
            quantity = pos.quantity
        if quantity <= 0:
            return None

        amount = price * quantity
        stamp_tax = amount * _STAMP_TAX_RATE
        commission = max(amount * commission_rate, _MIN_COMMISSION)
        total_income = amount - commission - stamp_tax

        self.cash += total_income
        pos.quantity -= quantity
        if pos.quantity == 0:
            del self.positions[symbol]
        else:
            pos.market_value = pos.quantity * price

        trade = Trade(
            symbol=symbol, side="sell", price=price,
            quantity=quantity, amount=amount,
            commission=commission + stamp_tax,
            trade_date=trade_date, reason=reason
        )
        self.trades.append(trade)
        return trade

    def snapshot(self, trade_date: str):
        self.equity_curve.append({
            "date": trade_date,
            "cash": _f(self.cash.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "market_value": _f(self.total_market_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "equity": _f(self.total_equity.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        })


class BacktestEngine:
    """回测引擎：基于信号的回测框架"""

    def __init__(
        self,
        initial_cash: float = 1_000_000,
        commission_rate: float = 0.0003,
        slippage: float = 0.001,  # 0.1% 滑点
        risk_config: Optional[RiskConfig] = None,
    ):
        self.initial_cash = _d(initial_cash, "0.01")
        self.commission_rate = _d(commission_rate)
        self.slippage = _d(slippage)
        self.portfolio = Portfolio(cash=self.initial_cash, initial_cash=self.initial_cash)
        self.risk = RiskManager(risk_config)
        self.peak_equity = self.initial_cash
        self._halted = False

    def run(self, strategy_code: str, kline_data: pd.DataFrame, params: Dict[str, Any] = None, benchmark_kline: pd.DataFrame = None) -> dict:
        """
        执行回测
        strategy_code: 策略 Python 代码，必须定义 generate_signals(df, params) 函数
            返回 DataFrame，包含 signal 列: 1=买入, -1=卖出, 0=持有
        kline_data: K 线数据 DataFrame
        params: 策略参数
        benchmark_kline: 基准 K 线数据（如沪深300），用于对比
        """
        if params is None:
            params = {}

        # 构建基准日期→收盘价映射
        benchmark_map = {}
        if benchmark_kline is not None and not benchmark_kline.empty:
            for _, row in benchmark_kline.iterrows():
                benchmark_map[str(row["trade_date"])] = _d(row["close"])

        try:
            # 使用安全沙箱执行策略代码
            signals_df = safe_exec_strategy(strategy_code, kline_data, params)
        except ValueError as e:
            return {"status": "failed", "error": str(e)}
        except Exception as e:
            return {"status": "failed", "error": f"策略代码执行错误: {str(e)}\n{traceback.format_exc()}"}

        # 按日期遍历执行信号
        # 规则：T 日收盘产生信号，T+1 日开盘成交（避免未来函数）
        symbol = kline_data["symbol"].iloc[0] if "symbol" in kline_data.columns else "UNKNOWN"
        prev_equity = self.initial_cash
        rows = list(signals_df.iterrows())
        pending_signal = None  # 待执行的信号

        for idx in range(len(rows)):
            i, row = rows[idx]
            trade_date = str(row.get("trade_date", i))
            close_price = _d(row["close"])
            open_price = _d(row.get("open", row["close"]))  # 用开盘价成交
            signal = int(row.get("signal", 0))

            # 更新持仓市值（用当日收盘价）
            self.portfolio.update_market_price(symbol, close_price)

            # 风控检查：最大回撤熔断
            if self._halted:
                continue

            current_equity_val = _f(self.portfolio.total_equity)
            if self.risk.check_max_drawdown(_f(self.peak_equity), current_equity_val):
                self._halted = True
                # 清仓（用当日开盘价）
                for sym in list(self.portfolio.positions.keys()):
                    if sym in self.portfolio.positions:
                        pos = self.portfolio.positions[sym]
                        sell_price = open_price * (Decimal("1") - self.slippage)
                        self.portfolio.sell(sym, sell_price, pos.quantity, trade_date, self.commission_rate, reason="回撤熔断")
                continue

            # 止损/止盈检查（用当日开盘价触发）
            if symbol in self.portfolio.positions:
                pos = self.portfolio.positions[symbol]
                if self.risk.check_stop_loss(_f(pos.avg_cost), _f(open_price)):
                    sell_price = open_price * (Decimal("1") - self.slippage)
                    self.portfolio.sell(symbol, sell_price, pos.quantity, trade_date, self.commission_rate, reason="止损")
                    continue
                if self.risk.check_take_profit(_f(pos.avg_cost), _f(open_price)):
                    sell_price = open_price * (Decimal("1") - self.slippage)
                    self.portfolio.sell(symbol, sell_price, pos.quantity, trade_date, self.commission_rate, reason="止盈")
                    continue

            # 执行前一日的待定信号（T 日信号在 T+1 日开盘成交）
            if pending_signal is not None:
                if pending_signal == 1:
                    exec_price = open_price * (Decimal("1") + self.slippage)
                else:
                    exec_price = open_price * (Decimal("1") - self.slippage)

                if pending_signal == 1:  # 买入
                    current_pos_value = Decimal("0")
                    if symbol in self.portfolio.positions:
                        current_pos_value = self.portfolio.positions[symbol].market_value
                    quantity = self.risk.calc_max_buy_quantity(
                        _f(self.portfolio.cash), _f(exec_price), _f(current_pos_value), _f(self.portfolio.total_equity)
                    )
                    if quantity >= 100:
                        self.portfolio.buy(symbol, exec_price, quantity, trade_date, self.commission_rate)

                elif pending_signal == -1:  # 卖出
                    if symbol in self.portfolio.positions:
                        pos = self.portfolio.positions[symbol]
                        self.portfolio.sell(symbol, exec_price, pos.quantity, trade_date, self.commission_rate)

                pending_signal = None

            # 记录当日信号（下一日执行）
            if signal != 0:
                pending_signal = signal

            # 更新峰值
            if self.portfolio.total_equity > self.peak_equity:
                self.peak_equity = self.portfolio.total_equity

            # 记录每日状态
            current_equity = self.portfolio.total_equity
            self.portfolio.daily_pnl.append(current_equity - prev_equity)
            self.portfolio.snapshot(trade_date)
            prev_equity = current_equity

        return self._calc_metrics(benchmark_map)

    def _calc_metrics(self, benchmark_map: dict = None) -> dict:
        equity_curve = self.portfolio.equity_curve
        if not equity_curve:
            return {"status": "completed", "metrics": {}, "equity_curve": [], "trades": []}

        equities = [e["equity"] for e in equity_curve]  # already float from snapshot
        initial = _f(self.portfolio.initial_cash)
        final = equities[-1]

        # 收益率序列：daily_pnl[i] / equities[i-1]，第一天用 initial
        equity_prev = [initial] + equities[:-1]
        daily_pnl_float = [_f(v) for v in self.portfolio.daily_pnl]
        returns = pd.Series(daily_pnl_float) / pd.Series(equity_prev)
        returns = returns.replace([np.inf, -np.inf], 0)

        # 最大回撤
        equity_series = pd.Series(equities)
        cummax = equity_series.cummax()
        drawdown = (equity_series - cummax) / cummax
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0

        # 交易统计
        trades = self.portfolio.trades
        sell_trades = [t for t in trades if t.side == "sell"]
        win_count = 0
        total_profit = Decimal("0")
        total_loss = Decimal("0")

        # 简单配对计算盈亏
        buy_stack = []
        for t in trades:
            if t.side == "buy":
                buy_stack.append(t)
            elif t.side == "sell" and buy_stack:
                buy_t = buy_stack.pop(0)
                pnl = (t.price - buy_t.price) * t.quantity - t.commission - buy_t.commission
                if pnl > 0:
                    win_count += 1
                    total_profit += pnl
                else:
                    total_loss += abs(pnl)

        trade_count = len(sell_trades)
        win_rate = win_count / trade_count if trade_count > 0 else 0
        total_loss_f = _f(total_loss)
        profit_loss_ratio = _f(total_profit) / total_loss_f if total_loss_f > 0 else float("inf")

        # 年化收益
        days = len(equities)
        total_return = (final - initial) / initial if initial else 0
        annual_return = (1 + total_return) ** (252 / max(days, 1)) - 1 if days > 0 else 0

        # 夏普比率（假设无风险利率 3%）
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() - 0.03 / 252) / returns.std() * np.sqrt(252)
        else:
            sharpe = 0

        # 波动率
        volatility = returns.std() * np.sqrt(252) if len(returns) > 1 else 0

        # 统计止损/止盈次数
        stop_loss_count = sum(1 for t in trades if "止损" in t.reason)
        take_profit_count = sum(1 for t in trades if "止盈" in t.reason)
        halt_count = sum(1 for t in trades if "熔断" in t.reason)

        metrics = {
            "total_return": round(total_return * 100, 2),
            "annual_return": round(annual_return * 100, 2),
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown": round(max_drawdown * 100, 2),
            "volatility": round(volatility * 100, 2),
            "win_rate": round(win_rate * 100, 2),
            "profit_loss_ratio": round(profit_loss_ratio, 2),
            "trade_count": trade_count,
            "stop_loss_count": stop_loss_count,
            "take_profit_count": take_profit_count,
            "halt_count": halt_count,
            "initial_cash": initial,
            "final_equity": round(final, 2),
        }

        # 基准对比
        benchmark_metrics = {}
        if benchmark_map and len(benchmark_map) > 1:
            bm_dates = sorted(benchmark_map.keys())
            bm_first = _f(benchmark_map[bm_dates[0]])
            bm_last = _f(benchmark_map[bm_dates[-1]])
            bm_return = (bm_last - bm_first) / bm_first if bm_first else 0
            bm_days = len(bm_dates)
            bm_annual = (1 + bm_return) ** (252 / max(bm_days, 1)) - 1 if bm_days > 0 else 0

            # 基准最大回撤
            bm_prices = [_f(benchmark_map[d]) for d in bm_dates]
            bm_series = pd.Series(bm_prices)
            bm_cummax = bm_series.cummax()
            bm_dd = (bm_series - bm_cummax) / bm_cummax
            bm_max_dd = abs(bm_dd.min()) if len(bm_dd) > 0 else 0

            # 超额收益
            alpha = total_return - bm_return

            benchmark_metrics = {
                "benchmark_return": round(bm_return * 100, 2),
                "benchmark_annual_return": round(bm_annual * 100, 2),
                "benchmark_max_drawdown": round(bm_max_dd * 100, 2),
                "alpha": round(alpha * 100, 2),
            }
            metrics.update(benchmark_metrics)

        trades_out = [
            {
                "symbol": t.symbol, "side": t.side,
                "price": _f(t.price.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
                "quantity": t.quantity,
                "amount": _f(t.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "commission": _f(t.commission.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "trade_date": t.trade_date,
                "reason": t.reason,
            }
            for t in trades
        ]

        # 基准曲线
        benchmark_curve = []
        if benchmark_map and len(benchmark_map) > 1:
            bm_dates = sorted(benchmark_map.keys())
            bm_first = _f(benchmark_map[bm_dates[0]])
            for d in bm_dates:
                bm_curve_val = _f(benchmark_map[d]) / bm_first * initial
                benchmark_curve.append({
                    "date": d,
                    "equity": round(bm_curve_val, 2),
                })

        result = {
            "status": "completed",
            "metrics": metrics,
            "equity_curve": equity_curve,
            "trades": trades_out,
        }
        if benchmark_curve:
            result["benchmark_curve"] = benchmark_curve

        return result

    def run_multi(self, strategy_code: str, kline_dict: Dict[str, pd.DataFrame], params: Dict[str, Any] = None) -> dict:
        """
        多股票回测
        kline_dict: {symbol: DataFrame} 字典
        策略代码必须定义 generate_signals_multi(data_dict, params)
            返回 {symbol: DataFrame} 字典，每个 DataFrame 包含 signal 列
        """
        if params is None:
            params = {}

        try:
            # 使用安全沙箱
            from app.services.strategy.sandbox import safe_exec_strategy, validate_strategy_code
            valid, msg = validate_strategy_code(strategy_code)
            if not valid:
                return {"status": "failed", "error": f"策略代码不安全: {msg}"}

            # 构建受限命名空间
            from app.services.strategy.sandbox import ALLOWED_BUILTINS, ALLOWED_MODULES, _restricted_import
            restricted_builtins = {
                **ALLOWED_BUILTINS,
                "__import__": _restricted_import,
            }
            namespace = {
                "__builtins__": restricted_builtins,
                **ALLOWED_MODULES,
            }
            exec(strategy_code, namespace)

            if "generate_signals_multi" in namespace:
                signals_dict = namespace["generate_signals_multi"](kline_dict, params)
            elif "generate_signals" in namespace:
                # 兼容单股票策略：对每只股票分别调用
                signals_dict = {}
                for symbol, df in kline_dict.items():
                    signals_dict[symbol] = namespace["generate_signals"](df.copy(), params)
            else:
                return {"status": "failed", "error": "策略代码必须定义 generate_signals(df, params) 或 generate_signals_multi(data_dict, params)"}

            for symbol, sdf in signals_dict.items():
                if not isinstance(sdf, pd.DataFrame) or "signal" not in sdf.columns:
                    return {"status": "failed", "error": f"{symbol}: generate_signals 必须返回包含 'signal' 列的 DataFrame"}

        except Exception as e:
            return {"status": "failed", "error": f"策略代码执行错误: {str(e)}\n{traceback.format_exc()}"}

        # 合并所有股票的日期轴，按日期遍历
        all_dates = set()
        for sdf in signals_dict.values():
            all_dates.update(str(r) for r in sdf["trade_date"].tolist())
        all_dates = sorted(all_dates)

        # 为每只股票建立日期索引映射
        indexed = {}
        for symbol, sdf in signals_dict.items():
            indexed[symbol] = {str(row["trade_date"]): row for _, row in sdf.iterrows()}

        prev_equity = self.initial_cash

        for trade_date in all_dates:
            # 更新所有持仓市值
            for symbol in list(self.portfolio.positions.keys()):
                if symbol in indexed and trade_date in indexed[symbol]:
                    price = _d(indexed[symbol][trade_date]["close"])
                    self.portfolio.update_market_price(symbol, price)

            # 风控检查：最大回撤熔断
            if self._halted:
                continue

            current_equity_val = _f(self.portfolio.total_equity)
            if self.risk.check_max_drawdown(_f(self.peak_equity), current_equity_val):
                self._halted = True
                for sym in list(self.portfolio.positions.keys()):
                    if sym in indexed and trade_date in indexed[sym]:
                        price = _d(indexed[sym][trade_date]["close"]) * (Decimal("1") - self.slippage)
                        pos = self.portfolio.positions.get(sym)
                        if pos:
                            self.portfolio.sell(sym, price, pos.quantity, trade_date, self.commission_rate, reason="回撤熔断")
                continue

            # 执行每只股票的信号
            for symbol, date_map in indexed.items():
                if trade_date not in date_map:
                    continue
                row = date_map[trade_date]
                close_price = _d(row["close"])
                signal = int(row.get("signal", 0))

                # 止损/止盈检查
                if symbol in self.portfolio.positions:
                    pos = self.portfolio.positions[symbol]
                    if self.risk.check_stop_loss(_f(pos.avg_cost), _f(close_price)):
                        sell_price = close_price * (Decimal("1") - self.slippage)
                        self.portfolio.sell(symbol, sell_price, pos.quantity, trade_date, self.commission_rate, reason="止损")
                        continue
                    if self.risk.check_take_profit(_f(pos.avg_cost), _f(close_price)):
                        sell_price = close_price * (Decimal("1") - self.slippage)
                        self.portfolio.sell(symbol, sell_price, pos.quantity, trade_date, self.commission_rate, reason="止盈")
                        continue

                if signal == 1:
                    buy_price = close_price * (Decimal("1") + self.slippage)
                    current_pos_value = Decimal("0")
                    if symbol in self.portfolio.positions:
                        current_pos_value = self.portfolio.positions[symbol].market_value
                    quantity = self.risk.calc_max_buy_quantity(
                        _f(self.portfolio.cash), _f(buy_price), _f(current_pos_value), _f(self.portfolio.total_equity)
                    )
                    if quantity >= 100:
                        self.portfolio.buy(symbol, buy_price, quantity, trade_date, self.commission_rate)

                elif signal == -1:
                    if symbol in self.portfolio.positions:
                        pos = self.portfolio.positions[symbol]
                        sell_price = close_price * (Decimal("1") - self.slippage)
                        self.portfolio.sell(symbol, sell_price, pos.quantity, trade_date, self.commission_rate)

            # 更新峰值
            if self.portfolio.total_equity > self.peak_equity:
                self.peak_equity = self.portfolio.total_equity

            current_equity = self.portfolio.total_equity
            self.portfolio.daily_pnl.append(current_equity - prev_equity)
            self.portfolio.snapshot(trade_date)
            prev_equity = current_equity

        return self._calc_metrics()
