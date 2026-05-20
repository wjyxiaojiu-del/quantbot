from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.trade import Portfolio, Position, Order
from app.schemas.trade import PortfolioCreate, PortfolioOut, OrderCreate, OrderOut
from app.services.trade.engine import TradeEngine

router = APIRouter()


@router.get("/portfolios", response_model=List[PortfolioOut])
async def list_portfolios(db: Session = Depends(get_db)):
    return db.query(Portfolio).order_by(Portfolio.created_at.desc()).all()


@router.post("/portfolios", response_model=PortfolioOut, status_code=201)
async def create_portfolio(data: PortfolioCreate, db: Session = Depends(get_db)):
    portfolio = Portfolio(name=data.name, initial_cash=data.initial_cash, cash=data.initial_cash)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


@router.get("/portfolios/{portfolio_id}")
async def get_portfolio(portfolio_id: UUID, db: Session = Depends(get_db)):
    engine = TradeEngine(db)
    summary = engine.get_portfolio_summary(portfolio_id)
    if not summary:
        raise HTTPException(status_code=404, detail="组合不存在")
    return summary


@router.post("/portfolios/{portfolio_id}/orders", response_model=OrderOut, status_code=201)
async def place_order(portfolio_id: UUID, data: OrderCreate, db: Session = Depends(get_db)):
    engine = TradeEngine(db)
    result = engine.execute_order(
        portfolio_id=portfolio_id,
        symbol=data.symbol, side=data.side,
        price=data.price, quantity=data.quantity,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    # 返回完整订单
    order = db.query(Order).filter(Order.id == result["order_id"]).first()
    return order


@router.get("/portfolios/{portfolio_id}/orders", response_model=List[OrderOut])
async def list_orders(
    portfolio_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    engine = TradeEngine(db)
    result = engine.get_order_history(portfolio_id, page, page_size)
    return result["items"]


@router.get("/portfolios/{portfolio_id}/positions/{symbol}")
async def get_position_detail(
    portfolio_id: UUID, symbol: str, db: Session = Depends(get_db),
):
    engine = TradeEngine(db)
    detail = engine.get_position_detail(portfolio_id, symbol)
    if not detail:
        raise HTTPException(status_code=404, detail="无此持仓")
    return detail
