"""
数据质量校验模块

检查 K 线数据的完整性、一致性和异常值
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class DataQualityIssue:
    level: str  # "error" | "warning"
    type: str
    message: str
    count: int = 0
    dates: List[str] = None


def check_kline_quality(df: pd.DataFrame, symbol: str = "") -> List[DataQualityIssue]:
    """校验 K 线数据质量

    Args:
        df: K 线数据 DataFrame，需包含 trade_date, open, high, low, close, volume
        symbol: 股票代码（用于报告）

    Returns:
        问题列表
    """
    issues = []

    if df.empty:
        issues.append(DataQualityIssue("error", "empty_data", f"{symbol}: 数据为空"))
        return issues

    # 1. 必需列检查
    required_cols = ["trade_date", "open", "high", "low", "close", "volume"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        issues.append(DataQualityIssue("error", "missing_columns", f"缺少列: {missing_cols}"))
        return issues

    # 2. 日期连续性检查
    if "trade_date" in df.columns:
        dates = pd.to_datetime(df["trade_date"]).sort_values()
        date_diff = dates.diff().dt.days
        # 跳过周末，超过 4 天认为缺失
        gaps = date_diff[date_diff > 4]
        if len(gaps) > 0:
            issues.append(DataQualityIssue(
                "warning", "date_gaps",
                f"存在 {len(gaps)} 个日期间隔超过 4 天",
                count=len(gaps)
            ))

    # 3. 重复日期检查
    if "trade_date" in df.columns:
        dup_dates = df["trade_date"].duplicated().sum()
        if dup_dates > 0:
            issues.append(DataQualityIssue(
                "error", "duplicate_dates",
                f"存在 {dup_dates} 条重复日期记录",
                count=dup_dates
            ))

    # 4. OHLC 逻辑检查
    # high >= max(open, close), low <= min(open, close)
    invalid_high = df[df["high"] < df[["open", "close"]].max(axis=1)]
    if len(invalid_high) > 0:
        issues.append(DataQualityIssue(
            "error", "invalid_high",
            f"high < max(open, close) 的记录有 {len(invalid_high)} 条",
            count=len(invalid_high)
        ))

    invalid_low = df[df["low"] > df[["open", "close"]].min(axis=1)]
    if len(invalid_low) > 0:
        issues.append(DataQualityIssue(
            "error", "invalid_low",
            f"low > min(open, close) 的记录有 {len(invalid_low)} 条",
            count=len(invalid_low)
        ))

    # 5. 价格为 0 或负数
    price_cols = ["open", "high", "low", "close"]
    for col in price_cols:
        invalid = df[df[col] <= 0]
        if len(invalid) > 0:
            issues.append(DataQualityIssue(
                "error", f"invalid_{col}",
                f"{col} <= 0 的记录有 {len(invalid)} 条",
                count=len(invalid)
            ))

    # 6. 成交量为 0（非停牌）
    zero_vol = df[df["volume"] == 0]
    if len(zero_vol) > 0 and len(zero_vol) < len(df):
        issues.append(DataQualityIssue(
            "warning", "zero_volume",
            f"成交量为 0 的记录有 {len(zero_vol)} 条（可能是停牌）",
            count=len(zero_vol)
        ))

    # 7. 异常涨跌幅（单日超过 20%）
    if len(df) > 1:
        pct_change = df["close"].pct_change().abs()
        extreme = pct_change[pct_change > 0.2]
        if len(extreme) > 0:
            issues.append(DataQualityIssue(
                "warning", "extreme_change",
                f"单日涨跌幅超过 20% 的记录有 {len(extreme)} 条",
                count=len(extreme)
            ))

    # 8. NaN 检查
    nan_counts = df[required_cols].isna().sum()
    total_nans = nan_counts.sum()
    if total_nans > 0:
        issues.append(DataQualityIssue(
            "error", "nan_values",
            f"存在 {total_nans} 个 NaN 值",
            count=total_nans
        ))

    return issues


def fill_missing_trading_days(df: pd.DataFrame) -> pd.DataFrame:
    """填充缺失的交易日（用前值填充）

    Args:
        df: K 线数据，需有 trade_date 列

    Returns:
        填充后的 DataFrame
    """
    if df.empty or "trade_date" not in df.columns:
        return df

    df = df.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values("trade_date").reset_index(drop=True)

    # 创建完整日期范围（仅工作日）
    date_range = pd.bdate_range(df["trade_date"].min(), df["trade_date"].max())
    full_df = pd.DataFrame({"trade_date": date_range})

    # 合并并前值填充
    merged = full_df.merge(df, on="trade_date", how="left")
    merged = merged.ffill()

    return merged
