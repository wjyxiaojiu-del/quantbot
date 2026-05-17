import pandas as pd
import numpy as np
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import logging
import traceback

from app.services.risk.manager import RiskManager, RiskConfig

logger = logging.getLogger(__name__)


@dataclass
class Position:
    symbol: str
    quantity: int = 0
    avg_cost: float = 0.0
    market_value: float = 0.0

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.avg_cost * self.quantity


@dataclass
class Trade:
    symbol: str
    side: str  # "buy" / "sell"
    price: float
    quantity: int
    amount: float
    commission: float
    trade_date: str
    reason: str = ""


@dataclass
class Portfolio:
    cash: float = 1_000_000.0
    initial_cash: float = 1_000_000.0
    positions: Dict[str, Position] = field(default_factory=dict)
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[dict] = field(default_factory=list)
    daily_pnl: List[float] = field(default_factory=list)

    @property
    def total_market_value(self) -> float:
        return sum(p.market_value for p in self.positions.values())

    @property
    def total_equity(self) -> float:
        return self.cash + self.total_market_value

    def update_market_price(self, symbol: str, price: float):
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos.market_value = pos.quantity * price

    def buy(self, symbol: str, price: float, quantity: int, trade_date: str, commission_rate: float = 0.0003, reason: str = "") -> Optional[Trade]:
        amount = price * quantity
        commission = max(amount * commission_rate, 5.0)  # 最低5元
        total_cost = amount + commission
        if total_cost > self.cash:
            return None
        if quantity <= 0:
            return None

        self.cash -= total_cost
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_qty = pos.quantity + quantity
            pos.avg_cost = (pos.avg_cost * pos.quantity + price * quantity) / total_qty
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

    def sell(self, symbol: str, price: float, quantity: int, trade_date: str, commission_rate: float = 0.0003, reason: str = "") -> Optional[Trade]:
        if symbol not in self.positions:
            return None
        pos = self.positions[symbol]
        if quantity > pos.quantity:
            quantity = pos.quantity
        if quantity <= 0:
            return None

        amount = price * quantity
        # 卖出印花税 0.1%
        stamp_tax = amount * 0.001
        commission = max(amount * commission_rate, 5.0)
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
            "cash": round(self.cash, 2),
            "market_value": round(self.total_market_value, 2),
            "equity": round(self.total_equity, 2),
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
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.portfolio = Portfolio(cash=initial_cash, initial_cash=initial_cash)
        self.risk = RiskManager(risk_config)
        self.peak_equity = initial_cash
        self._halted = False

    def run(self, strategy_code: str, kline_data: pd.DataFrame, params: Dict[str, Any] = None) -> dict:
        """
        执行回测
        strategy_code: 策略 Python 代码，必须定义 generate_signals(df, params) 函数
            返回 DataFrame，包含 signal 列: 1=买入, -1=卖出, 0=持有
        kline_data: K 线数据 DataFrame
        params: 策略参数
        """
        if params is None:
            params = {}

        try:
            # 执行策略代码
            namespace = {}
            exec(strategy_code, namespace)

            if "generate_signals" not in namespace:
                return {"status": "failed", "error": "策略代码必须定义 generate_signals(df, params) 函数"}

            generate_signals = namespace["generate_signals"]
            signals_df = generate_signals(kline_data.copy(), params)

            if not isinstance(signals_df, pd.DataFrame) or "signal" not in signals_df.columns:
                return {"status": "failed", "error": "generate_signals 必须返回包含 'signal' 列的 DataFrame"}

        except Exception as e:
            return {"status": "failed", "error": f"策略代码执行错误: {str(e)}\n{traceback.format_exc()}"}

        # 按日期遍历执行信号
        symbol = kline_data["symbol"].iloc[0] if "symbol" in kline_data.columns else "UNKNOWN"
        prev_equity = self.initial_cash

        for i, row in signals_df.iterrows():
            trade_date = str(row.get("trade_date", i))
            close_price = float(row["close"])
            signal = int(row.get("signal", 0))

            # 更新持仓市值
            self.portfolio.update_market_price(symbol, close_price)

            # 风控检查：最大回撤熔断
            if self._halted:
                continue

            current_equity_val = self.portfolio.total_equity
            if self.risk.check_max_drawdown(self.peak_equity, current_equity_val):
                self._halted = True
                # 清仓
                for sym in list(self.portfolio.positions.keys()):
                    if sym in self.portfolio.positions:
                        pos = self.portfolio.positions[sym]
                        sell_price = close_price * (1 - self.slippage)
                        self.portfolio.sell(sym, sell_price, pos.quantity, trade_date, self.commission_rate, reason="回撤熔断")
                continue

            # 止损/止盈检查
            if symbol in self.portfolio.positions:
                pos = self.portfolio.positions[symbol]
                if self.risk.check_stop_loss(pos.avg_cost, close_price):
                    sell_price = close_price * (1 - self.slippage)
                    self.portfolio.sell(symbol, sell_price, pos.quantity, trade_date, self.commission_rate, reason="止损")
                    continue
                if self.risk.check_take_profit(pos.avg_cost, close_price):
                    sell_price = close_price * (1 - self.slippage)
                    self.portfolio.sell(symbol, sell_price, pos.quantity, trade_date, self.commission_rate, reason="止盈")
                    continue

            # 执行信号
            if signal == 1:  # 买入
                buy_price = close_price * (1 + self.slippage)
                current_pos_value = 0
                if symbol in self.portfolio.positions:
                    current_pos_value = self.portfolio.positions[symbol].market_value
                quantity = self.risk.calc_max_buy_quantity(
                    self.portfolio.cash, buy_price, current_pos_value, self.portfolio.total_equity
                )
                if quantity >= 100:
                    self.portfolio.buy(symbol, buy_price, quantity, trade_date, self.commission_rate)

            elif signal == -1:  # 卖出
                if symbol in self.portfolio.positions:
                    pos = self.portfolio.positions[symbol]
                    sell_price = close_price * (1 - self.slippage)
                    self.portfolio.sell(symbol, sell_price, pos.quantity, trade_date, self.commission_rate)

            # 更新峰值
            if self.portfolio.total_equity > self.peak_equity:
                self.peak_equity = self.portfolio.total_equity

            # 记录每日状态
            current_equity = self.portfolio.total_equity
            self.portfolio.daily_pnl.append(current_equity - prev_equity)
            self.portfolio.snapshot(trade_date)
            prev_equity = current_equity

        return self._calc_metrics()

    def _calc_metrics(self) -> dict:
        equity_curve = self.portfolio.equity_curve
        if not equity_curve:
            return {"status": "completed", "metrics": {}, "equity_curve": [], "trades": []}

        equities = [e["equity"] for e in equity_curve]
        initial = self.portfolio.initial_cash
        final = equities[-1]

        # 收益率序列
        returns = pd.Series(self.portfolio.daily_pnl) / pd.Series(equities[:-1] + [initial])
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
        total_profit = 0
        total_loss = 0

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
        profit_loss_ratio = total_profit / total_loss if total_loss > 0 else float("inf")

        # 年化收益
        days = len(equities)
        total_return = (final - initial) / initial
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
            "initial_cash": self.portfolio.initial_cash,
            "final_equity": round(final, 2),
        }

        trades_out = [
            {
                "symbol": t.symbol, "side": t.side, "price": round(t.price, 4),
                "quantity": t.quantity, "amount": round(t.amount, 2),
                "commission": round(t.commission, 2), "trade_date": t.trade_date,
                "reason": t.reason,
            }
            for t in trades
        ]

        return {
            "status": "completed",
            "metrics": metrics,
            "equity_curve": equity_curve,
            "trades": trades_out,
        }

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
            namespace = {}
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
                    price = float(indexed[symbol][trade_date]["close"])
                    self.portfolio.update_market_price(symbol, price)

            # 风控检查：最大回撤熔断
            if self._halted:
                continue

            current_equity_val = self.portfolio.total_equity
            if self.risk.check_max_drawdown(self.peak_equity, current_equity_val):
                self._halted = True
                for sym in list(self.portfolio.positions.keys()):
                    if sym in indexed and trade_date in indexed[sym]:
                        price = float(indexed[sym][trade_date]["close"]) * (1 - self.slippage)
                        pos = self.portfolio.positions.get(sym)
                        if pos:
                            self.portfolio.sell(sym, price, pos.quantity, trade_date, self.commission_rate, reason="回撤熔断")
                continue

            # 执行每只股票的信号
            for symbol, date_map in indexed.items():
                if trade_date not in date_map:
                    continue
                row = date_map[trade_date]
                close_price = float(row["close"])
                signal = int(row.get("signal", 0))

                # 止损/止盈检查
                if symbol in self.portfolio.positions:
                    pos = self.portfolio.positions[symbol]
                    if self.risk.check_stop_loss(pos.avg_cost, close_price):
                        sell_price = close_price * (1 - self.slippage)
                        self.portfolio.sell(symbol, sell_price, pos.quantity, trade_date, self.commission_rate, reason="止损")
                        continue
                    if self.risk.check_take_profit(pos.avg_cost, close_price):
                        sell_price = close_price * (1 - self.slippage)
                        self.portfolio.sell(symbol, sell_price, pos.quantity, trade_date, self.commission_rate, reason="止盈")
                        continue

                if signal == 1:
                    buy_price = close_price * (1 + self.slippage)
                    current_pos_value = 0
                    if symbol in self.portfolio.positions:
                        current_pos_value = self.portfolio.positions[symbol].market_value
                    quantity = self.risk.calc_max_buy_quantity(
                        self.portfolio.cash, buy_price, current_pos_value, self.portfolio.total_equity
                    )
                    if quantity >= 100:
                        self.portfolio.buy(symbol, buy_price, quantity, trade_date, self.commission_rate)

                elif signal == -1:
                    if symbol in self.portfolio.positions:
                        pos = self.portfolio.positions[symbol]
                        sell_price = close_price * (1 - self.slippage)
                        self.portfolio.sell(symbol, sell_price, pos.quantity, trade_date, self.commission_rate)

            # 更新峰值
            if self.portfolio.total_equity > self.peak_equity:
                self.peak_equity = self.portfolio.total_equity

            current_equity = self.portfolio.total_equity
            self.portfolio.daily_pnl.append(current_equity - prev_equity)
            self.portfolio.snapshot(trade_date)
            prev_equity = current_equity

        return self._calc_metrics()
