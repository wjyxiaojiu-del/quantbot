"""
策略代码安全执行沙箱

限制策略代码只能使用 pandas/numpy 数学操作，禁止：
- 文件 I/O (open, read, write)
- 网络访问 (socket, requests, urllib)
- 系统调用 (os, sys, subprocess)
- 危险内置函数 (eval, exec, compile, __import__)
- 环境变量访问 (os.environ)

安全加固：
- 代码长度上限 10KB
- AST 白名单校验（仅允许函数定义、赋值、表达式等安全节点）
- 执行超时 30 秒（线程级）
"""

import ast
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

MAX_CODE_LENGTH = 10_000  # 10KB
EXECUTION_TIMEOUT = 30    # 30 秒

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
    "eval(", "exec(", "compile(",
    "open(", "file(", "os.", "sys.", "subprocess.",
    "environ", "getenv", "system(",
    "__subclasses__", "__bases__", "__mro__", "__globals__",
    "__builtins__", "__code__", "__class__",
]

# 允许的 AST 节点类型
ALLOWED_AST_NODES = (
    ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
    ast.arguments, ast.arg,
    ast.Return, ast.Assign, ast.AugAssign, ast.AnnAssign,
    ast.If, ast.For, ast.While, ast.Break, ast.Continue,
    ast.Expr, ast.Call, ast.Attribute, ast.Subscript,
    ast.Name, ast.Load, ast.Store, ast.Del,
    ast.Constant,
    ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare,
    ast.List, ast.Tuple, ast.Dict, ast.Set,
    ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Not,
    ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn, ast.Is, ast.IsNot,
    ast.comprehension, ast.keyword,
    ast.Index, ast.Slice, ast.ExtSlice,
    ast.Starred, ast.Tuple,
    # 允许 import pandas/numpy（会被 _restricted_import 拦截其他模块）
    ast.Import, ast.ImportFrom, ast.alias,
    # 允许 with/try（策略可能用到上下文管理）
    ast.With, ast.withitem, ast.Try, ast.ExceptHandler, ast.Raise,
    # 允许 f-string
    ast.JoinedStr, ast.FormattedValue,
    # 允许 walrus :=
    ast.NamedExpr,
)


def _check_ast_safety(tree: ast.AST) -> Tuple[bool, str]:
    """递归检查 AST 节点是否全部在白名单内"""
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_AST_NODES):
            return False, f"不允许的语法结构: {type(node).__name__}"
    return True, "通过"


def validate_strategy_code(code: str) -> Tuple[bool, str]:
    """验证策略代码是否安全"""
    # 长度检查
    if len(code) > MAX_CODE_LENGTH:
        return False, f"代码长度超过限制 ({MAX_CODE_LENGTH} 字节)"

    code_lower = code.lower()

    # 检查禁止关键字
    for keyword in BLOCKED_KEYWORDS:
        if keyword.lower() in code_lower:
            return False, f"不允许使用: {keyword}"

    # 检查是否定义了 generate_signals
    if "def generate_signals" not in code:
        return False, "必须定义 generate_signals(df, params) 函数"

    # AST 安全检查
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"语法错误: {e}"

    ast_ok, ast_msg = _check_ast_safety(tree)
    if not ast_ok:
        return False, ast_msg

    return True, "通过"


def _restricted_import(name, *args, **kwargs):
    """限制 import 只允许 pandas/numpy"""
    allowed = {"pandas", "numpy", "pd", "np"}
    if name in allowed:
        return __import__(name, *args, **kwargs)
    raise ImportError(f"不允许导入模块: {name}")


def _exec_in_namespace(code: str, namespace: dict) -> None:
    """在受限命名空间中执行策略代码定义"""
    compiled = compile(code, "<strategy>", "exec")
    exec(compiled, namespace)


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
    valid, msg = validate_strategy_code(code)
    if not valid:
        raise ValueError(f"策略代码不安全: {msg}")

    restricted_builtins = {
        **ALLOWED_BUILTINS,
        "__import__": _restricted_import,
    }
    namespace = {
        "__builtins__": restricted_builtins,
        **ALLOWED_MODULES,
    }

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_exec_in_namespace, code, namespace)
            future.result(timeout=EXECUTION_TIMEOUT)
    except FutureTimeout:
        raise ValueError(f"策略代码执行超时（>{EXECUTION_TIMEOUT}秒）")
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
