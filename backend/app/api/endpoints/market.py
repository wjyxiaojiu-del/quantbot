from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.services.data import get_data_source
from app.services.data.sync_manager import DataSyncManager
from app.schemas.market import StockOut, KLineOut, SyncRequest, SyncResponse

router = APIRouter()


@router.get("/stocks", response_model=List[StockOut])
async def list_stocks(
    exchange: Optional[str] = Query(None, description="交易所: SZ/SH/BJ"),
    industry: Optional[str] = None,
    search: Optional[str] = Query(None, description="搜索代码或名称"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """获取股票列表（支持搜索）"""
    from app.models.stock import Stock

    query = db.query(Stock)
    if exchange:
        query = query.filter(Stock.exchange == exchange)
    if industry:
        query = query.filter(Stock.industry == industry)
    if search:
        like = f"%{search}%"
        query = query.filter((Stock.symbol.like(like)) | (Stock.name.like(like)))

    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items


@router.get("/stocks/{symbol}/kline", response_model=List[KLineOut])
async def get_kline(
    symbol: str,
    period: str = Query("daily", pattern="^(daily|weekly|monthly|1m|5m|15m|30m|60m)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db)
):
    """获取 K 线数据"""
    from app.models.kline import StockDailyKline
    from sqlalchemy import desc
    
    query = db.query(StockDailyKline).filter(StockDailyKline.symbol == symbol)
    
    if start_date:
        query = query.filter(StockDailyKline.trade_date >= start_date)
    if end_date:
        query = query.filter(StockDailyKline.trade_date <= end_date)
    
    query = query.order_by(desc(StockDailyKline.trade_date))
    
    if not start_date and not end_date:
        query = query.limit(limit)
    
    items = query.all()
    return sorted(items, key=lambda x: x.trade_date)


@router.get("/stocks/{symbol}/realtime")
async def get_realtime_quote(symbol: str):
    """获取实时行情（直接调 AKShare）"""
    try:
        ds = get_data_source()
        data = ds.get_realtime_quote(symbol)
        return {"symbol": symbol, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync", response_model=SyncResponse)
async def sync_stock_data(request: SyncRequest, db: Session = Depends(get_db)):
    """手动触发数据同步"""
    manager = DataSyncManager(db)
    
    if request.symbols:
        symbols = request.symbols
    else:
        # 同步全市场
        symbols = manager.get_all_stock_symbols()
    
    result = await manager.sync_kline_batch(
        symbols=symbols,
        period=request.period,
        start_date=request.start_date,
        end_date=request.end_date
    )
    
    return SyncResponse(
        success=result["success"],
        total=len(symbols),
        success_count=result["success_count"],
        failed_count=result["failed_count"],
        errors=result.get("errors", [])
    )


@router.post("/stocks/sync-all")
async def sync_all_stocks(db: Session = Depends(get_db)):
    """同步全市场股票列表"""
    manager = DataSyncManager(db)
    count = await manager.sync_stock_list()
    return {"message": f"同步完成，共 {count} 只股票"}


# ── 全球市场（yfinance）──

@router.get("/global/quote/{symbol}")
async def get_global_quote(symbol: str):
    """获取全球市场实时行情（美股/港股/加密货币/指数）"""
    from app.services.data import get_data_source_for_symbol
    try:
        ds = get_data_source_for_symbol(symbol)
        data = ds.get_realtime_quote(symbol)
        return {"symbol": symbol, "source": ds.name, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/global/kline/{symbol}")
async def get_global_kline(
    symbol: str,
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """获取全球市场 K 线数据（美股/港股/加密货币/指数）"""
    from app.services.data import get_data_source_for_symbol
    try:
        ds = get_data_source_for_symbol(symbol)
        df = ds.fetch_kline(symbol, period, start_date, end_date)
        if df.empty:
            return {"symbol": symbol, "data": [], "message": "无数据"}
        records = []
        for _, row in df.iterrows():
            records.append({
                "trade_date": str(row["trade_date"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
            })
        return {"symbol": symbol, "source": ds.name, "count": len(records), "data": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/global/watchlist")
async def get_global_watchlist():
    """获取全球市场关注列表（美股/港股/加密货币/指数）"""
    from app.services.data.yfinance_adapter import YFinanceDataSource
    ds = YFinanceDataSource()
    df = ds.fetch_stock_list()
    return df.to_dict("records")
