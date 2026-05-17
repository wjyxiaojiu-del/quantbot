"""内置策略模板"""

STRATEGY_TEMPLATES = {
    "dual_ma": {
        "name": "双均线策略",
        "description": "短期均线上穿长期均线买入，下穿卖出",
        "params": {"short_window": 5, "long_window": 20},
        "code": '''import pandas as pd

def generate_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    short = params.get("short_window", 5)
    long = params.get("long_window", 20)

    df["ma_short"] = df["close"].rolling(short).mean()
    df["ma_long"] = df["close"].rolling(long).mean()

    df["signal"] = 0
    df["signal_change"] = 0
    prev_signal = 0
    for i in range(1, len(df)):
        if pd.isna(df.iloc[i]["ma_short"]) or pd.isna(df.iloc[i]["ma_long"]):
            continue
        cur_signal = 1 if df.iloc[i]["ma_short"] > df.iloc[i]["ma_long"] else -1
        if cur_signal != prev_signal:
            df.iloc[i, df.columns.get_loc("signal")] = cur_signal
            prev_signal = cur_signal

    return df
''',
    },
    "macd": {
        "name": "MACD 策略",
        "description": "MACD 金叉买入，死叉卖出",
        "params": {"fast": 12, "slow": 26, "signal_period": 9},
        "code": '''import pandas as pd

def generate_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    fast = params.get("fast", 12)
    slow = params.get("slow", 26)
    signal_period = params.get("signal_period", 9)

    df["ema_fast"] = df["close"].ewm(span=fast, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=slow, adjust=False).mean()
    df["dif"] = df["ema_fast"] - df["ema_slow"]
    df["dea"] = df["dif"].ewm(span=signal_period, adjust=False).mean()
    df["macd_hist"] = (df["dif"] - df["dea"]) * 2

    df["signal"] = 0
    prev_hist = 0
    for i in range(1, len(df)):
        cur_hist = df.iloc[i]["macd_hist"]
        if cur_hist > 0 and prev_hist <= 0:
            df.iloc[i, df.columns.get_loc("signal")] = 1
        elif cur_hist < 0 and prev_hist >= 0:
            df.iloc[i, df.columns.get_loc("signal")] = -1
        prev_hist = cur_hist

    return df
''',
    },
    "rsi": {
        "name": "RSI 超买超卖策略",
        "description": "RSI 低于超卖线买入，高于超买线卖出",
        "params": {"period": 14, "oversold": 30, "overbought": 70},
        "code": '''import pandas as pd

def generate_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    period = params.get("period", 14)
    oversold = params.get("oversold", 30)
    overbought = params.get("overbought", 70)

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    df["signal"] = 0
    in_position = False
    for i in range(period, len(df)):
        rsi = df.iloc[i]["rsi"]
        if pd.isna(rsi):
            continue
        if rsi < oversold and not in_position:
            df.iloc[i, df.columns.get_loc("signal")] = 1
            in_position = True
        elif rsi > overbought and in_position:
            df.iloc[i, df.columns.get_loc("signal")] = -1
            in_position = False

    return df
''',
    },
    "bollinger": {
        "name": "布林带策略",
        "description": "价格触及下轨买入，触及上轨卖出",
        "params": {"period": 20, "num_std": 2},
        "code": '''import pandas as pd

def generate_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    period = params.get("period", 20)
    num_std = params.get("num_std", 2)

    df["ma"] = df["close"].rolling(period).mean()
    df["std"] = df["close"].rolling(period).std()
    df["upper"] = df["ma"] + num_std * df["std"]
    df["lower"] = df["ma"] - num_std * df["std"]

    df["signal"] = 0
    in_position = False
    for i in range(period, len(df)):
        close = df.iloc[i]["close"]
        lower = df.iloc[i]["lower"]
        upper = df.iloc[i]["upper"]
        if pd.isna(lower) or pd.isna(upper):
            continue
        if close < lower and not in_position:
            df.iloc[i, df.columns.get_loc("signal")] = 1
            in_position = True
        elif close > upper and in_position:
            df.iloc[i, df.columns.get_loc("signal")] = -1
            in_position = False

    return df
''',
    },
    "knn": {
        "name": "KNN 趋势策略",
        "description": "基于 K 近邻的趋势判断策略",
        "params": {"k": 5, "lookback": 20},
        "code": '''import pandas as pd
import numpy as np

def generate_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    k = params.get("k", 5)
    lookback = params.get("lookback", 20)

    df["return_1d"] = df["close"].pct_change()
    df["volatility"] = df["return_1d"].rolling(lookback).std()
    df["momentum"] = df["close"] / df["close"].shift(lookback) - 1

    df["signal"] = 0
    in_position = False

    for i in range(lookback + 10, len(df)):
        features = ["return_1d", "volatility", "momentum"]
        current = df.iloc[i][features].values
        if pd.isna(current).any():
            continue

        # 计算与历史窗口的欧氏距离
        history = df.iloc[i-lookback:i][features].dropna()
        if len(history) < k:
            continue

        distances = np.sqrt(((history.values - current) ** 2).sum(axis=1))
        nearest_idx = np.argsort(distances)[:k]
        future_returns = df.iloc[i-lookback:i].iloc[nearest_idx]["return_1d"].shift(-1).dropna()

        if len(future_returns) == 0:
            continue

        avg_future = future_returns.mean()
        if avg_future > 0 and not in_position:
            df.iloc[i, df.columns.get_loc("signal")] = 1
            in_position = True
        elif avg_future < 0 and in_position:
            df.iloc[i, df.columns.get_loc("signal")] = -1
            in_position = False

    return df
''',
    },
}
