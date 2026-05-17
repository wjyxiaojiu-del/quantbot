"""
风控管理器 — 仓位控制、止损止盈、回撤限制
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class RiskConfig:
    max_single_position_pct: float = 0.20   # 单只最大仓位 20%
    max_total_position_pct: float = 0.80    # 最大总仓位 80%
    stop_loss_pct: float = 0.08             # 止损 8%
    take_profit_pct: float = 0.20           # 止盈 20%
    daily_loss_limit_pct: float = 0.03      # 单日最大亏损 3%
    max_drawdown_pct: float = 0.15          # 最大回撤 15%
    min_lot_size: int = 100                 # 最小交易单位（A 股 100 股）
    max_lot_size: int = 100000              # 单笔最大数量


class RiskManager:
    """风控管理器"""

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()

    def calc_max_buy_quantity(
        self, cash: float, price: float, current_position_value: float, total_equity: float
    ) -> int:
        """计算允许的最大买入数量"""
        cfg = self.config

        # 单只仓位限制
        max_single = total_equity * cfg.max_single_position_pct
        remaining_single = max_single - current_position_value
        if remaining_single <= 0:
            return 0

        # 总仓位限制
        max_total = total_equity * cfg.max_total_position_pct
        remaining_total = max_total - current_position_value
        if remaining_total <= 0:
            return 0

        # 取最小值
        available = min(cash, remaining_single, remaining_total)
        quantity = int(available / price / cfg.min_lot_size) * cfg.min_lot_size
        return min(quantity, cfg.max_lot_size)

    def check_stop_loss(self, avg_cost: float, current_price: float) -> bool:
        """检查是否触发止损"""
        if avg_cost <= 0:
            return False
        loss_pct = (avg_cost - current_price) / avg_cost
        return loss_pct >= self.config.stop_loss_pct

    def check_take_profit(self, avg_cost: float, current_price: float) -> bool:
        """检查是否触发止盈"""
        if avg_cost <= 0:
            return False
        profit_pct = (current_price - avg_cost) / avg_cost
        return profit_pct >= self.config.take_profit_pct

    def check_daily_loss(self, daily_pnl: float, total_equity: float) -> bool:
        """检查是否超过单日亏损限制"""
        if total_equity <= 0:
            return False
        return daily_pnl / total_equity <= -self.config.daily_loss_limit_pct

    def check_max_drawdown(self, peak_equity: float, current_equity: float) -> bool:
        """检查是否超过最大回撤限制"""
        if peak_equity <= 0:
            return False
        drawdown = (peak_equity - current_equity) / peak_equity
        return drawdown >= self.config.max_drawdown_pct

    def validate_order(
        self, side: str, symbol: str, price: float, quantity: int,
        cash: float, positions: dict, total_equity: float
    ) -> tuple[bool, str]:
        """验证订单是否符合风控规则"""
        cfg = self.config

        # 基本检查
        if quantity <= 0:
            return False, "数量必须大于 0"
        if quantity % cfg.min_lot_size != 0:
            return False, f"数量必须是 {cfg.min_lot_size} 的整数倍"
        if price <= 0:
            return False, "价格必须大于 0"

        if side == "buy":
            # 资金检查
            amount = price * quantity
            commission = max(amount * 0.0003, 5.0)
            if cash < amount + commission:
                return False, "现金不足"

            # 单只仓位检查
            current_value = 0
            if symbol in positions:
                pos = positions[symbol]
                current_value = pos.get("market_value", 0)
            max_single = total_equity * cfg.max_single_position_pct
            if current_value + amount > max_single:
                return False, f"超过单只最大仓位 {cfg.max_single_position_pct*100:.0f}%"

        elif side == "sell":
            if symbol not in positions:
                return False, "无持仓"
            pos = positions[symbol]
            if pos.get("quantity", 0) < quantity:
                return False, "持仓不足"

        return True, "通过"

    def get_stop_loss_price(self, avg_cost: float) -> float:
        """获取止损价"""
        return avg_cost * (1 - self.config.stop_loss_pct)

    def get_take_profit_price(self, avg_cost: float) -> float:
        """获取止盈价"""
        return avg_cost * (1 + self.config.take_profit_pct)
