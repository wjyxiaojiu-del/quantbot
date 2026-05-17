"""
交易引擎 — 模拟交易核心逻辑
"""
from decimal import Decimal
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
import logging

from app.models.trade import Portfolio, Position, Order
from app.services.risk.manager import RiskManager, RiskConfig

logger = logging.getLogger(__name__)

# A 股交易规则
MIN_LOT = 100
COMMISSION_RATE = 0.0003       # 万三佣金
MIN_COMMISSION = 5.0           # 最低 5 元
STAMP_TAX_RATE = 0.001         # 卖出印花税千一
PRICE_LIMIT_PCT = 0.10         # 涨跌停 10%


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

        market_value = sum(float(p.avg_cost) * p.quantity for p in positions)
        total_equity = float(portfolio.cash) + market_value
        total_return = (total_equity - float(portfolio.initial_cash)) / float(portfolio.initial_cash) * 100

        return {
            "id": str(portfolio.id),
            "name": portfolio.name,
            "initial_cash": float(portfolio.initial_cash),
            "cash": float(portfolio.cash),
            "market_value": round(market_value, 2),
            "total_equity": round(total_equity, 2),
            "total_return_pct": round(total_return, 2),
            "position_count": len(positions),
            "positions": [
                {
                    "id": str(p.id),
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_cost": float(p.avg_cost),
                    "market_value": round(float(p.avg_cost) * p.quantity, 2),
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

        # 风控校验
        positions = self.db.query(Position).filter(Position.portfolio_id == portfolio_id).all()
        pos_dict = {
            p.symbol: {"quantity": p.quantity, "market_value": float(p.avg_cost) * p.quantity}
            for p in positions
        }
        total_equity = float(portfolio.cash) + sum(v["market_value"] for v in pos_dict.values())

        valid, msg = self.risk.validate_order(
            side=side, symbol=symbol, price=price, quantity=quantity,
            cash=float(portfolio.cash), positions=pos_dict, total_equity=total_equity
        )
        if not valid:
            return {"success": False, "error": msg}

        amount = price * quantity
        commission = max(amount * COMMISSION_RATE, MIN_COMMISSION)

        if side == "buy":
            total_cost = amount + commission
            portfolio.cash = float(portfolio.cash) - total_cost

            position = self.db.query(Position).filter(
                Position.portfolio_id == portfolio_id, Position.symbol == symbol
            ).first()

            if position:
                total_qty = position.quantity + quantity
                position.avg_cost = (
                    float(position.avg_cost) * position.quantity + price * quantity
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
                amount=amount, commission=commission, status="filled"
            )

        elif side == "sell":
            position = self.db.query(Position).filter(
                Position.portfolio_id == portfolio_id, Position.symbol == symbol
            ).first()
            if not position or position.quantity < quantity:
                return {"success": False, "error": "持仓不足"}

            stamp_tax = amount * STAMP_TAX_RATE
            total_income = amount - commission - stamp_tax
            portfolio.cash = float(portfolio.cash) + total_income

            position.quantity -= quantity
            if position.quantity == 0:
                self.db.delete(position)

            order = Order(
                portfolio_id=portfolio_id, symbol=symbol,
                side="sell", price=price, quantity=quantity,
                amount=amount, commission=commission + stamp_tax, status="filled"
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
            "amount": round(amount, 2),
            "commission": round(commission, 2),
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
                    "price": float(o.price),
                    "quantity": o.quantity,
                    "amount": float(o.amount),
                    "commission": float(o.commission),
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

        avg_cost = float(position.avg_cost)
        quantity = position.quantity
        market_value = avg_cost * quantity

        # 计算止损/止盈价
        stop_loss_price = self.risk.get_stop_loss_price(avg_cost)
        take_profit_price = self.risk.get_take_profit_price(avg_cost)

        return {
            "symbol": symbol,
            "quantity": quantity,
            "avg_cost": avg_cost,
            "market_value": round(market_value, 2),
            "stop_loss_price": round(stop_loss_price, 2),
            "take_profit_price": round(take_profit_price, 2),
        }
