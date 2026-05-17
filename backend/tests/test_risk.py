import pytest
from app.services.risk.manager import RiskManager, RiskConfig


def test_default_config():
    rm = RiskManager()
    assert rm.config.max_single_position_pct == 0.20
    assert rm.config.stop_loss_pct == 0.08
    assert rm.config.take_profit_pct == 0.20


def test_calc_max_buy_quantity():
    rm = RiskManager()
    # 100万总权益，单只最大20%，当前仓位0
    qty = rm.calc_max_buy_quantity(cash=1000000, price=10.0, current_position_value=0, total_equity=1000000)
    # 20万 / 10元 = 20000股，取整到100
    assert qty == 20000


def test_calc_max_buy_quantity_limited_by_cash():
    rm = RiskManager()
    # 现金不足
    qty = rm.calc_max_buy_quantity(cash=5000, price=10.0, current_position_value=0, total_equity=1000000)
    # 5000 / 10 = 500，取整到100
    assert qty == 500


def test_calc_max_buy_quantity_position_limit():
    rm = RiskManager()
    # 已有18万仓位
    qty = rm.calc_max_buy_quantity(cash=1000000, price=10.0, current_position_value=180000, total_equity=1000000)
    # 20万 - 18万 = 2万 / 10 = 2000
    assert qty == 2000


def test_stop_loss():
    rm = RiskManager()
    assert rm.check_stop_loss(avg_cost=100, current_price=92) is True   # 8% loss
    assert rm.check_stop_loss(avg_cost=100, current_price=93) is False  # 7% loss
    assert rm.check_stop_loss(avg_cost=100, current_price=100) is False


def test_take_profit():
    rm = RiskManager()
    assert rm.check_take_profit(avg_cost=100, current_price=120) is True   # 20% profit
    assert rm.check_take_profit(avg_cost=100, current_price=119) is False  # 19% profit
    assert rm.check_take_profit(avg_cost=100, current_price=100) is False


def test_daily_loss_limit():
    rm = RiskManager()
    assert rm.check_daily_loss(daily_pnl=-30000, total_equity=1000000) is True
    assert rm.check_daily_loss(daily_pnl=-29000, total_equity=1000000) is False


def test_max_drawdown():
    rm = RiskManager()
    assert rm.check_max_drawdown(peak_equity=1000000, current_equity=850000) is True
    assert rm.check_max_drawdown(peak_equity=1000000, current_equity=860000) is False


def test_validate_order_buy_ok():
    rm = RiskManager()
    valid, msg = rm.validate_order(
        side="buy", symbol="000001.SZ", price=10.0, quantity=1000,
        cash=100000, positions={}, total_equity=100000
    )
    assert valid is True


def test_validate_order_buy_insufficient_cash():
    rm = RiskManager()
    valid, msg = rm.validate_order(
        side="buy", symbol="000001.SZ", price=10.0, quantity=10000,
        cash=50000, positions={}, total_equity=100000
    )
    assert valid is False
    assert "不足" in msg


def test_validate_order_sell_no_position():
    rm = RiskManager()
    valid, msg = rm.validate_order(
        side="sell", symbol="000001.SZ", price=10.0, quantity=1000,
        cash=100000, positions={}, total_equity=100000
    )
    assert valid is False
    assert "无持仓" in msg


def test_validate_order_lot_size():
    rm = RiskManager()
    valid, msg = rm.validate_order(
        side="buy", symbol="000001.SZ", price=10.0, quantity=150,
        cash=100000, positions={}, total_equity=100000
    )
    assert valid is False
    assert "100" in msg


def test_stop_loss_price():
    rm = RiskManager()
    assert rm.get_stop_loss_price(100) == 92.0


def test_take_profit_price():
    rm = RiskManager()
    assert rm.get_take_profit_price(100) == 120.0


def test_custom_config():
    config = RiskConfig(stop_loss_pct=0.05, take_profit_pct=0.10)
    rm = RiskManager(config)
    assert rm.check_stop_loss(100, 95) is True
    assert rm.check_take_profit(100, 110) is True
