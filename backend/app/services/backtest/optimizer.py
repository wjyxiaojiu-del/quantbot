"""
参数优化模块

支持：
- 网格搜索（Grid Search）
- 训练集/验证集分割
- Walk-Forward 分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass
from itertools import product
import logging

from app.services.backtest.engine import BacktestEngine

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    params: Dict[str, Any]
    train_metric: float
    val_metric: float
    train_metrics: dict
    val_metrics: dict


@dataclass
class WalkForwardResult:
    fold: int
    train_start: str
    train_end: str
    val_start: str
    val_end: str
    best_params: Dict[str, Any]
    train_metric: float
    val_metric: float
    val_metrics: dict


def grid_search(
    strategy_code: str,
    kline_data: pd.DataFrame,
    param_grid: Dict[str, List[Any]],
    metric: str = "sharpe",
    initial_cash: float = 1_000_000,
) -> List[OptimizationResult]:
    """网格搜索最优参数

    Args:
        strategy_code: 策略代码
        kline_data: K 线数据
        param_grid: 参数网格，如 {"short_window": [5, 10, 20], "long_window": [30, 50, 100]}
        metric: 优化目标指标 ("sharpe" | "total_return" | "win_rate")
        initial_cash: 初始资金

    Returns:
        按指标排序的结果列表
    """
    # 生成参数组合
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))

    results = []

    for combo in combinations:
        params = dict(zip(param_names, combo))

        # 跳过无效组合（如短期 > 长期）
        if "short_window" in params and "long_window" in params:
            if params["short_window"] >= params["long_window"]:
                continue

        engine = BacktestEngine(initial_cash=initial_cash)
        result = engine.run(strategy_code, kline_data, params)

        if result["status"] == "completed":
            metrics = result.get("metrics", {})
            train_metric = metrics.get(metric, 0)
            results.append(OptimizationResult(
                params=params,
                train_metric=train_metric,
                val_metric=0,
                train_metrics=metrics,
                val_metrics={},
            ))

    # 按指标降序排序
    results.sort(key=lambda x: x.train_metric, reverse=True)
    return results


def train_val_split(
    kline_data: pd.DataFrame,
    train_ratio: float = 0.7,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """按时间顺序分割训练集和验证集

    Args:
        kline_data: K 线数据
        train_ratio: 训练集比例

    Returns:
        (train_data, val_data)
    """
    if "trade_date" in kline_data.columns:
        kline_data = kline_data.sort_values("trade_date")

    split_idx = int(len(kline_data) * train_ratio)
    train_data = kline_data.iloc[:split_idx].reset_index(drop=True)
    val_data = kline_data.iloc[split_idx:].reset_index(drop=True)

    return train_data, val_data


def optimize_with_val(
    strategy_code: str,
    kline_data: pd.DataFrame,
    param_grid: Dict[str, List[Any]],
    metric: str = "sharpe",
    train_ratio: float = 0.7,
    initial_cash: float = 1_000_000,
) -> List[OptimizationResult]:
    """带验证集的参数优化

    在训练集上搜索最优参数，在验证集上评估表现

    Args:
        strategy_code: 策略代码
        kline_data: K 线数据
        param_grid: 参数网格
        metric: 优化目标
        train_ratio: 训练集比例
        initial_cash: 初始资金

    Returns:
        按验证集指标排序的结果列表
    """
    train_data, val_data = train_val_split(kline_data, train_ratio)

    # 在训练集上搜索
    train_results = grid_search(strategy_code, train_data, param_grid, metric, initial_cash)

    # 在验证集上评估每个结果
    for result in train_results[:20]:  # 只评估 top 20
        engine = BacktestEngine(initial_cash=initial_cash)
        val_result = engine.run(strategy_code, val_data, result.params)

        if val_result["status"] == "completed":
            result.val_metrics = val_result.get("metrics", {})
            result.val_metric = result.val_metrics.get(metric, 0)

    # 按验证集指标排序
    train_results.sort(key=lambda x: x.val_metric, reverse=True)
    return train_results


def walk_forward(
    strategy_code: str,
    kline_data: pd.DataFrame,
    param_grid: Dict[str, List[Any]],
    metric: str = "sharpe",
    n_splits: int = 5,
    train_ratio: float = 0.7,
    initial_cash: float = 1_000_000,
) -> List[WalkForwardResult]:
    """Walk-Forward 分析

    滚动窗口优化，更接近真实交易场景

    Args:
        strategy_code: 策略代码
        kline_data: K 线数据
        param_grid: 参数网格
        metric: 优化目标
        n_splits: 分割数量
        train_ratio: 每个窗口的训练集比例
        initial_cash: 初始资金

    Returns:
        每个窗口的结果列表
    """
    if "trade_date" in kline_data.columns:
        kline_data = kline_data.sort_values("trade_date").reset_index(drop=True)

    total_len = len(kline_data)
    window_size = total_len // n_splits
    results = []

    for i in range(n_splits):
        start_idx = i * window_size
        end_idx = min((i + 1) * window_size, total_len)
        window_data = kline_data.iloc[start_idx:end_idx].reset_index(drop=True)

        if len(window_data) < 100:  # 数据太少跳过
            continue

        # 分割训练/验证
        train_data, val_data = train_val_split(window_data, train_ratio)

        # 在训练集上优化
        train_results = grid_search(strategy_code, train_data, param_grid, metric, initial_cash)

        if not train_results:
            continue

        best = train_results[0]

        # 在验证集上评估
        engine = BacktestEngine(initial_cash=initial_cash)
        val_result = engine.run(strategy_code, val_data, best.params)

        val_metrics = {}
        val_metric = 0
        if val_result["status"] == "completed":
            val_metrics = val_result.get("metrics", {})
            val_metric = val_metrics.get(metric, 0)

        train_start = str(window_data.iloc[0].get("trade_date", start_idx))
        train_end = str(train_data.iloc[-1].get("trade_date", ""))
        val_start = str(val_data.iloc[0].get("trade_date", ""))
        val_end = str(val_data.iloc[-1].get("trade_date", ""))

        results.append(WalkForwardResult(
            fold=i + 1,
            train_start=train_start,
            train_end=train_end,
            val_start=val_start,
            val_end=val_end,
            best_params=best.params,
            train_metric=best.train_metric,
            val_metric=val_metric,
            val_metrics=val_metrics,
        ))

    return results
