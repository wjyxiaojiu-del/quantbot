"""
策略代码安全执行沙箱

限制策略代码只能使用 pandas/numpy 数学操作，禁止：
- 文件 I/O (open, read, write)
- 网络访问 (socket, requests, urllib)
- 系统调用 (os, sys, subprocess)
- 危险内置函数 (eval, exec, compile, __import__)
- 环境变量访问 (os.environ)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple

# 允许的内置函数白名单
ALLOWED_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "frozenset": frozenset,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "pow": pow,
    "print": print,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
    # 数学
    "True": True,
    "False": False,
    "None": None,
}

# 允许的模块白名单
ALLOWED_MODULES = {
    "pandas": pd,
    "pd": pd,
    "numpy": np,
    "np": np,
}

# 禁止的关键字和函数
BLOCKED_KEYWORDS = [
    "import os", "import sys", "import subprocess", "import socket",
    "import urllib", "import requests", "import http",
    "import shutil", "import pathlib", "import io",
    "__import__", "eval(", "exec(", "compile(",
    "open(", "file(", "os.", "sys.", "subprocess.",
    "environ", "getenv", "system(",
]


def validate_strategy_code(code: str) -> Tuple[bool, str]:
    """验证策略代码是否安全"""
    code_lower = code.lower()

    # 检查禁止关键字
    for keyword in BLOCKED_KEYWORDS:
        if keyword.lower() in code_lower:
            return False, f"不允许使用: {keyword}"

    # 检查是否定义了 generate_signals
    if "def generate_signals" not in code:
        return False, "必须定义 generate_signals(df, params) 函数"

    return True, "通过"


def safe_exec_strategy(code: str, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """在沙箱中执行策略代码

    Args:
        code: 策略 Python 代码
        df: K线数据 DataFrame
        params: 策略参数

    Returns:
        包含 signal 列的 DataFrame

    Raises:
        ValueError: 代码不安全或执行失败
    """
    # 先验证安全性
    valid, msg = validate_strategy_code(code)
    if not valid:
        raise ValueError(f"策略代码不安全: {msg}")

    # 构建受限命名空间
    namespace = {
        "__builtins__": ALLOWED_BUILTINS,
        **ALLOWED_MODULES,
    }

    try:
        # 编译并执行策略定义
        compiled = compile(code, "<strategy>", "exec")
        exec(compiled, namespace)
    except SyntaxError as e:
        raise ValueError(f"策略代码语法错误: {e}")
    except Exception as e:
        raise ValueError(f"策略代码执行错误: {e}")

    if "generate_signals" not in namespace:
        raise ValueError("策略代码必须定义 generate_signals(df, params) 函数")

    generate_signals = namespace["generate_signals"]

    try:
        result = generate_signals(df.copy(), params)
    except Exception as e:
        raise ValueError(f"generate_signals 执行失败: {e}")

    if not isinstance(result, pd.DataFrame):
        raise ValueError("generate_signals 必须返回 DataFrame")

    if "signal" not in result.columns:
        raise ValueError("generate_signals 返回的 DataFrame 必须包含 'signal' 列")

    return result
