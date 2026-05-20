"""
交易引擎 — 模拟交易核心逻辑
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
import logging

from app.models.trade import Portfolio, Position, Order
from app.services.risk.manager import RiskManager, RiskConfig

logger = logging.getLogger(__name__)

# A 股交易规则
MIN_LOT = 100
COMMISSION_RATE = Decimal("0.0003")    # 万三佣金
MIN_COMMISSION = Decimal("5.0")        # 最低 5 元
STAMP_TAX_RATE = Decimal("0.001")      # 卖出印花税千一
PRICE_LIMIT_PCT = Decimal("0.10")      # 涨跌停 10%


def _to_decimal(value, precision: str = "0.0001") -> Decimal:
    """将 float/int/str 转为 Decimal，统一精度"""
    if isinstance(value, Decimal):
        return value.quantize(Decimal(precision), rounding=ROUND_HALF_UP)
    return Decimal(str(value)).quantize(Decimal(precision), rounding=ROUND_HALF_UP)


class TradeEngine:
    """模拟交易引擎"""

    def __init__(self, db: Session, risk_config: Optional[RiskConfig] = None):
        self.db = db
        self.risk = RiskManager(risk_config)

    def get_portfolio_summary(self, portfolio_id) -> Optional[Dict[str, Any]]:
        """获取组合摘要"""
        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            return None

        positions = self.db.query(Position).filter(
            Position.portfolio_id == portfolio_id, Position.quantity > 0
        ).all()

        cash = _to_decimal(portfolio.cash, "0.01")
        initial_cash = _to_decimal(portfolio.initial_cash, "0.01")
        market_value = sum(_to_decimal(p.avg_cost, "0.01") * p.quantity for p in positions)
        total_equity = cash + market_value
        total_return = (total_equity - initial_cash) / initial_cash * 100 if initial_cash else Decimal("0")

        return {
            "id": str(portfolio.id),
            "name": portfolio.name,
            "initial_cash": float(initial_cash),
            "cash": float(cash),
            "market_value": float(market_value),
            "total_equity": float(total_equity),
            "total_return_pct": float(total_return.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "position_count": len(positions),
            "positions": [
                {
                    "id": str(p.id),
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_cost": float(_to_decimal(p.avg_cost)),
                    "market_value": float(_to_decimal(p.avg_cost, "0.01") * p.quantity),
                }
                for p in positions
            ],
            "status": portfolio.status,
        }

    def execute_order(
        self, portfolio_id, symbol: str, side: str, price: float, quantity: int
    ) -> Dict[str, Any]:
        """执行订单"""
        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            return {"success": False, "error": "组合不存在"}
        if portfolio.status != "active":
            return {"success": False, "error": "组合已关闭"}

        price_d = _to_decimal(price)
        cash_d = _to_decimal(portfolio.cash)

        # 风控校验
        positions = self.db.query(Position).filter(Position.portfolio_id == portfolio_id).all()
        pos_dict = {
            p.symbol: {"quantity": p.quantity, "market_value": float(_to_decimal(p.avg_cost, "0.01") * p.quantity)}
            for p in positions
        }
        total_equity = float(cash_d) + sum(v["market_value"] for v in pos_dict.values())

        valid, msg = self.risk.validate_order(
            side=side, symbol=symbol, price=price, quantity=quantity,
            cash=float(cash_d), positions=pos_dict, total_equity=total_equity
        )
        if not valid:
            return {"success": False, "error": msg}

        amount = price_d * quantity
        commission = max(amount * COMMISSION_RATE, MIN_COMMISSION)

        if side == "buy":
            total_cost = amount + commission
            portfolio.cash = cash_d - total_cost

            position = self.db.query(Position).filter(
                Position.portfolio_id == portfolio_id, Position.symbol == symbol
            ).first()

            if position:
                total_qty = position.quantity + quantity
                position.avg_cost = (
                    _to_decimal(position.avg_cost) * position.quantity + price_d * quantity
                ) / total_qty
                position.quantity = total_qty
            else:
                position = Position(
                    portfolio_id=portfolio_id, symbol=symbol,
                    quantity=quantity, avg_cost=price
                )
                self.db.add(position)

            order = Order(
                portfolio_id=portfolio_id, symbol=symbol,
                side="buy", price=price, quantity=quantity,
                amount=float(amount), commission=float(commission), status="filled"
            )

        elif side == "sell":
            position = self.db.query(Position).filter(
                Position.portfolio_id == portfolio_id, Position.symbol == symbol
            ).first()
            if not position or position.quantity < quantity:
                return {"success": False, "error": "持仓不足"}

            stamp_tax = amount * STAMP_TAX_RATE
            total_income = amount - commission - stamp_tax
            portfolio.cash = cash_d + total_income

            position.quantity -= quantity
            if position.quantity == 0:
                self.db.delete(position)

            order = Order(
                portfolio_id=portfolio_id, symbol=symbol,
                side="sell", price=price, quantity=quantity,
                amount=float(amount), commission=float(commission + stamp_tax), status="filled"
            )
        else:
            return {"success": False, "error": "side 必须是 buy 或 sell"}

        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        return {
            "success": True,
            "order_id": str(order.id),
            "side": side,
            "symbol": symbol,
            "price": price,
            "quantity": quantity,
            "amount": float(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "commission": float(commission.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        }

    def get_order_history(
        self, portfolio_id, page: int = 1, page_size: int = 50
    ) -> Dict[str, Any]:
        """获取订单历史"""
        query = self.db.query(Order).filter(Order.portfolio_id == portfolio_id)
        total = query.count()
        orders = query.order_by(Order.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return {
            "items": [
                {
                    "id": str(o.id),
                    "symbol": o.symbol,
                    "side": o.side,
                    "price": float(_to_decimal(o.price)),
                    "quantity": o.quantity,
                    "amount": float(_to_decimal(o.amount, "0.01")),
                    "commission": float(_to_decimal(o.commission, "0.01")),
                    "status": o.status,
                    "created_at": str(o.created_at),
                }
                for o in orders
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_position_detail(self, portfolio_id, symbol: str) -> Optional[Dict[str, Any]]:
        """获取单只持仓详情"""
        position = self.db.query(Position).filter(
            Position.portfolio_id == portfolio_id, Position.symbol == symbol
        ).first()
        if not position:
            return None

        avg_cost = _to_decimal(position.avg_cost)
        quantity = position.quantity
        market_value = avg_cost * quantity

        stop_loss_price = self.risk.get_stop_loss_price(float(avg_cost))
        take_profit_price = self.risk.get_take_profit_price(float(avg_cost))

        return {
            "symbol": symbol,
            "quantity": quantity,
            "avg_cost": float(avg_cost),
            "market_value": float(market_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "stop_loss_price": round(stop_loss_price, 2),
            "take_profit_price": round(take_profit_price, 2),
        }
