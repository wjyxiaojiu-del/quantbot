import pytest
import pandas as pd
import numpy as np
from app.services.backtest.engine import BacktestEngine


def _make_kline(days=100, start_price=10.0):
    """生成测试用 K 线数据"""
    dates = pd.date_range("2026-01-01", periods=days, freq="B")
    prices = [start_price]
    for _ in range(days - 1):
        change = np.random.uniform(-0.03, 0.03)
        prices.append(prices[-1] * (1 + change))
    return pd.DataFrame({
        "symbol": "TEST.SH",
        "trade_date": dates.strftime("%Y-%m-%d"),
        "open": prices,
        "high": [p * 1.01 for p in prices],
        "low": [p * 0.99 for p in prices],
        "close": prices,
        "volume": [1000000] * days,
    })


def test_engine_basic():
    """基本回测：无信号，权益不变"""
    code = """
def generate_signals(df, params):
    df['signal'] = 0
    return df
"""
    engine = BacktestEngine(initial_cash=1000000)
    kline = _make_kline(50)
    result = engine.run(code, kline)
    assert result["status"] == "completed"
    assert result["metrics"]["total_return"] == 0.0
    assert result["metrics"]["trade_count"] == 0


def test_engine_buy_and_sell():
    """买入后卖出"""
    code = """
def generate_signals(df, params):
    df['signal'] = 0
    if len(df) > 10:
        df.loc[df.index[5], 'signal'] = 1   # 第6天买入
        df.loc[df.index[15], 'signal'] = -1  # 第16天卖出
    return df
"""
    engine = BacktestEngine(initial_cash=1000000)
    kline = _make_kline(30)
    result = engine.run(code, kline)
    assert result["status"] == "completed"
    assert result["metrics"]["trade_count"] == 1


def test_engine_multi_stock():
    """多股票回测"""
    code = """
def generate_signals(df, params):
    df['signal'] = 0
    if len(df) > 5:
        df.loc[df.index[3], 'signal'] = 1
        df.loc[df.index[8], 'signal'] = -1
    return df
"""
    kline1 = _make_kline(20, start_price=10.0)
    kline1["symbol"] = "A.SH"
    kline2 = _make_kline(20, start_price=20.0)
    kline2["symbol"] = "B.SH"

    engine = BacktestEngine(initial_cash=1000000)
    result = engine.run_multi(code, {"A.SH": kline1, "B.SH": kline2})
    assert result["status"] == "completed"


def test_engine_invalid_code():
    """无效策略代码"""
    engine = BacktestEngine()
    kline = _make_kline(10)
    result = engine.run("invalid code", kline)
    assert result["status"] == "failed"
    assert "error" in result


def test_engine_missing_function():
    """缺少 generate_signals 函数"""
    engine = BacktestEngine()
    kline = _make_kline(10)
    result = engine.run("x = 1", kline)
    assert result["status"] == "failed"
    assert "generate_signals" in result["error"]


def test_engine_risk_metrics():
    """验证风控指标"""
    code = """
def generate_signals(df, params):
    df['signal'] = 0
    # 在价格下跌时买入（触发止损逻辑）
    for i in range(5, len(df)):
        if df.iloc[i]['close'] < df.iloc[i-1]['close']:
            df.iloc[i, df.columns.get_loc('signal')] = 1
    return df
"""
    engine = BacktestEngine(initial_cash=1000000)
    kline = _make_kline(50)
    result = engine.run(code, kline)
    assert result["status"] == "completed"
    assert "stop_loss_count" in result["metrics"]
    assert "take_profit_count" in result["metrics"]


def test_engine_no_trade_below_lot():
    """不足一手不交易"""
    code = """
def generate_signals(df, params):
    df['signal'] = 0
    if len(df) > 2:
        df.iloc[1, df.columns.get_loc('signal')] = 1
    return df
"""
    # 初始资金很少，不够买一手
    engine = BacktestEngine(initial_cash=100)
    kline = _make_kline(10, start_price=50.0)
    result = engine.run(code, kline)
    assert result["status"] == "completed"
    assert result["metrics"]["trade_count"] == 0
