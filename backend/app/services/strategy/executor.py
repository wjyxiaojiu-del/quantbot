"""
策略执行器 — 编译运行策略代码，生成交易信号
"""
import pandas as pd
import traceback
import logging
from typing import Dict, Any, Optional, List
from app.services.strategy.sandbox import safe_exec_strategy, validate_strategy_code

logger = logging.getLogger(__name__)


class StrategyExecutor:
    """策略代码执行器"""

    @staticmethod
    def validate_code(code: str) -> tuple[bool, str]:
        """验证策略代码是否合法（安全检查 + 语法检查）"""
        return validate_strategy_code(code)

    @staticmethod
    def generate_signals(
        code: str, kline_data: pd.DataFrame, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """执行策略代码，生成信号（使用安全沙箱）"""
        if params is None:
            params = {}

        try:
            result = safe_exec_strategy(code, kline_data, params)

            # 提取信号
            signals = []
            for _, row in result.iterrows():
                sig = int(row.get("signal", 0))
                if sig != 0:
                    signals.append({
                        "trade_date": str(row.get("trade_date", "")),
                        "signal": sig,
                        "close": float(row["close"]),
                        "action": "buy" if sig == 1 else "sell",
                    })

            return {
                "status": "completed",
                "signals": signals,
                "total_bars": len(result),
                "signal_count": len(signals),
            }

        except ValueError as e:
            return {"status": "failed", "error": str(e)}
        except Exception as e:
            return {"status": "failed", "error": f"执行错误: {str(e)}\n{traceback.format_exc()}"}

    @staticmethod
    def generate_signals_multi(
        code: str, kline_dict: Dict[str, pd.DataFrame], params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """多股票信号生成"""
        if params is None:
            params = {}

        try:
            namespace = {}
            exec(code, namespace)

            if "generate_signals_multi" in namespace:
                signals_dict = namespace["generate_signals_multi"](kline_dict, params)
            elif "generate_signals" in namespace:
                signals_dict = {}
                for symbol, df in kline_dict.items():
                    signals_dict[symbol] = namespace["generate_signals"](df.copy(), params)
            else:
                return {"status": "failed", "error": "缺少 generate_signals 或 generate_signals_multi 函数"}

            result = {}
            for symbol, sdf in signals_dict.items():
                if not isinstance(sdf, pd.DataFrame) or "signal" not in sdf.columns:
                    result[symbol] = {"status": "failed", "error": "返回格式错误"}
                    continue

                signals = []
                for _, row in sdf.iterrows():
                    sig = int(row.get("signal", 0))
                    if sig != 0:
                        signals.append({
                            "trade_date": str(row.get("trade_date", "")),
                            "signal": sig,
                            "close": float(row["close"]),
                            "action": "buy" if sig == 1 else "sell",
                        })

                result[symbol] = {
                    "status": "completed",
                    "signals": signals,
                    "total_bars": len(sdf),
                    "signal_count": len(signals),
                }

            return {"status": "completed", "results": result}

        except Exception as e:
            return {"status": "failed", "error": f"执行错误: {str(e)}\n{traceback.format_exc()}"}
