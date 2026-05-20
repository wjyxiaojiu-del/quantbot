"""initial schema

Revision ID: 1af74b29141e
Revises:
Create Date: 2026-05-20 17:56:18.072533

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1af74b29141e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── stocks ──
    op.create_table(
        "stocks",
        sa.Column("symbol", sa.String(20), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("exchange", sa.String(10), nullable=False),
        sa.Column("industry", sa.String(50), nullable=True),
        sa.Column("list_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── users ──
    op.create_table(
        "users",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("username", sa.String(50), unique=True, nullable=False),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("hashed_password", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── strategies ──
    op.create_table(
        "strategies",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("user_id", sa.CHAR(36), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── stock_daily_kline ──
    op.create_table(
        "stock_daily_kline",
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(12, 4), nullable=False),
        sa.Column("high", sa.Numeric(12, 4), nullable=False),
        sa.Column("low", sa.Numeric(12, 4), nullable=False),
        sa.Column("close", sa.Numeric(12, 4), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("change_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("turnover", sa.Numeric(8, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("symbol", "trade_date"),
        sa.CheckConstraint("high >= low AND high >= close AND high >= open", name="chk_daily_price"),
    )

    # ── stock_minute_kline ──
    op.create_table(
        "stock_minute_kline",
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("trade_time", sa.DateTime(), nullable=False),
        sa.Column("period", sa.String(10), nullable=False),
        sa.Column("open", sa.Numeric(12, 4), nullable=False),
        sa.Column("high", sa.Numeric(12, 4), nullable=False),
        sa.Column("low", sa.Numeric(12, 4), nullable=False),
        sa.Column("close", sa.Numeric(12, 4), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.PrimaryKeyConstraint("symbol", "trade_time", "period"),
    )

    # ── backtest_results ──
    op.create_table(
        "backtest_results",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("strategy_id", sa.String(50), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("symbols", sa.JSON(), nullable=False),
        sa.Column("initial_cash", sa.Numeric(18, 4), server_default="1000000"),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("total_return", sa.Numeric(10, 4), nullable=True),
        sa.Column("annual_return", sa.Numeric(10, 4), nullable=True),
        sa.Column("sharpe_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_drawdown_period", sa.Integer(), nullable=True),
        sa.Column("volatility", sa.Numeric(10, 4), nullable=True),
        sa.Column("win_rate", sa.Numeric(6, 4), nullable=True),
        sa.Column("profit_loss_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("trade_count", sa.Integer(), nullable=True),
        sa.Column("daily_pnl", sa.JSON(), nullable=True),
        sa.Column("trades", sa.JSON(), nullable=True),
        sa.Column("equity_curve", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), server_default="running"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── portfolios ──
    op.create_table(
        "portfolios",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("initial_cash", sa.Numeric(18, 4), server_default="1000000"),
        sa.Column("cash", sa.Numeric(18, 4), server_default="1000000"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── positions ──
    op.create_table(
        "positions",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("portfolio_id", sa.CHAR(36), sa.ForeignKey("portfolios.id"), nullable=False, index=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_cost", sa.Numeric(12, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── orders ──
    op.create_table(
        "orders",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("portfolio_id", sa.CHAR(36), sa.ForeignKey("portfolios.id"), nullable=False, index=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("order_type", sa.String(20), server_default="market"),
        sa.Column("price", sa.Numeric(12, 4), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("commission", sa.Numeric(12, 4), server_default="0"),
        sa.Column("status", sa.String(20), server_default="filled"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("orders")
    op.drop_table("positions")
    op.drop_table("portfolios")
    op.drop_table("backtest_results")
    op.drop_table("stock_minute_kline")
    op.drop_table("stock_daily_kline")
    op.drop_table("strategies")
    op.drop_table("users")
