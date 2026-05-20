"""内置策略模板 — 经典 + 进阶"""

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
    # ═══════════════════════════════════════════
    #  进阶策略
    # ═══════════════════════════════════════════
    "momentum": {
        "name": "动量策略",
        "description": "过去 N 天涨幅最大的股票买入，跌幅最大的卖出",
        "params": {"lookback": 20, "hold_days": 5},
        "code": '''import pandas as pd

def generate_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    lookback = params.get("lookback", 20)
    hold_days = params.get("hold_days", 5)

    df["momentum"] = df["close"].pct_change(lookback)
    df["ma20"] = df["close"].rolling(20).mean()

    df["signal"] = 0
    in_position = False
    hold_count = 0

    for i in range(lookback + 20, len(df)):
        mom = df.iloc[i]["momentum"]
        close = df.iloc[i]["close"]
        ma20 = df.iloc[i]["ma20"]

        if pd.isna(mom) or pd.isna(ma20):
            continue

        if in_position:
            hold_count += 1
            # 动量反转 或 跌破均线 → 卖出
            if mom < 0 or close < ma20 or hold_count >= hold_days:
                df.iloc[i, df.columns.get_loc("signal")] = -1
                in_position = False
                hold_count = 0
        else:
            # 强动量 + 站上均线 → 买入
            if mom > 0.05 and close > ma20:
                df.iloc[i, df.columns.get_loc("signal")] = 1
                in_position = True

    return df
''',
    },
    "mean_reversion": {
        "name": "均值回归策略",
        "description": "价格偏离均线过多时反向操作，超跌买入超涨卖出",
        "params": {"period": 20, "entry_std": 2.0, "exit_std": 0.5},
        "code": '''import pandas as pd

def generate_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    period = params.get("period", 20)
    entry_std = params.get("entry_std", 2.0)
    exit_std = params.get("exit_std", 0.5)

    df["ma"] = df["close"].rolling(period).mean()
    df["std"] = df["close"].rolling(period).std()
    df["zscore"] = (df["close"] - df["ma"]) / df["std"]

    df["signal"] = 0
    in_position = False

    for i in range(period, len(df)):
        z = df.iloc[i]["zscore"]
        if pd.isna(z):
            continue

        if not in_position:
            # 超跌买入
            if z < -entry_std:
                df.iloc[i, df.columns.get_loc("signal")] = 1
                in_position = True
        else:
            # 回归均值附近卖出，或继续下跌止损
            if abs(z) < exit_std or z > entry_std:
                df.iloc[i, df.columns.get_loc("signal")] = -1
                in_position = False

    return df
''',
    },
    "turtle": {
        "name": "海龟交易策略",
        "description": "突破 N 日最高价买入，跌破 N 日最低价卖出",
        "params": {"entry_period": 20, "exit_period": 10},
        "code": '''import pandas as pd

def generate_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    entry_period = params.get("entry_period", 20)
    exit_period = params.get("exit_period", 10)

    df["entry_high"] = df["high"].rolling(entry_period).max()
    df["exit_low"] = df["low"].rolling(exit_period).min()

    df["signal"] = 0
    in_position = False

    for i in range(max(entry_period, exit_period), len(df)):
        close = df.iloc[i]["close"]
        entry_high = df.iloc[i - 1]["entry_high"]  # 用前一天的通道
        exit_low = df.iloc[i - 1]["exit_low"]

        if pd.isna(entry_high) or pd.isna(exit_low):
            continue

        if not in_position:
            # 突破上轨买入
            if close > entry_high:
                df.iloc[i, df.columns.get_loc("signal")] = 1
                in_position = True
        else:
            # 跌破下轨卖出
            if close < exit_low:
                df.iloc[i, df.columns.get_loc("signal")] = -1
                in_position = False

    return df
''',
    },
    "grid": {
        "name": "网格交易策略",
        "description": "价格下跌到网格线买入，上涨到网格线卖出，适合震荡市",
        "params": {"grid_pct": 3.0, "max_grids": 5},
        "code": '''import pandas as pd

def generate_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    grid_pct = params.get("grid_pct", 3.0) / 100
    max_grids = params.get("max_grids", 5)

    df["signal"] = 0
    base_price = df.iloc[0]["close"]
    grid_level = 0  # 当前网格层级（正=持仓，0=空仓，负=不应出现）

    for i in range(1, len(df)):
        close = df.iloc[i]["close"]
        change_from_base = (close - base_price) / base_price

        # 计算当前应该在的网格层级
        target_level = int(change_from_base / grid_pct)

        if target_level > grid_level and grid_level < max_grids:
            # 价格下跌到新的网格线 → 买入
            df.iloc[i, df.columns.get_loc("signal")] = 1
            grid_level += 1
            if grid_level == 1:
                base_price = close  # 首次买入后重置基准
        elif target_level < grid_level and grid_level > 0:
            # 价格上涨到网格线 → 卖出
            df.iloc[i, df.columns.get_loc("signal")] = -1
            grid_level -= 1
            if grid_level == 0:
                base_price = close  # 清仓后重置基准

    return df
''',
    },
    "kdj": {
        "name": "KDJ 策略",
        "description": "KDJ 金叉买入，死叉卖出，经典超买超卖指标",
        "params": {"n": 9, "m1": 3, "m2": 3},
        "code": '''import pandas as pd

def generate_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    n = params.get("n", 9)
    m1 = params.get("m1", 3)
    m2 = params.get("m2", 3)

    low_n = df["low"].rolling(n).min()
    high_n = df["high"].rolling(n).max()
    rsv = (df["close"] - low_n) / (high_n - low_n) * 100
    rsv = rsv.fillna(50)

    k = rsv.ewm(com=m1 - 1, adjust=False).mean()
    d = k.ewm(com=m2 - 1, adjust=False).mean()
    j = 3 * k - 2 * d

    df["k"] = k
    df["d"] = d
    df["j"] = j

    df["signal"] = 0
    in_position = False
    prev_k, prev_d = 50, 50

    for i in range(n, len(df)):
        cur_k = df.iloc[i]["k"]
        cur_d = df.iloc[i]["d"]
        cur_j = df.iloc[i]["j"]

        # 金叉：K 上穿 D 且 J < 100（非超买区）
        if cur_k > cur_d and prev_k <= prev_d and cur_j < 100 and not in_position:
            df.iloc[i, df.columns.get_loc("signal")] = 1
            in_position = True
        # 死叉：K 下穿 D 且 J > 0（非超卖区）
        elif cur_k < cur_d and prev_k >= prev_d and cur_j > 0 and in_position:
            df.iloc[i, df.columns.get_loc("signal")] = -1
            in_position = False

        prev_k, prev_d = cur_k, cur_d

    return df
''',
    },
    "volume_price": {
        "name": "量价齐升策略",
        "description": "放量上涨买入，缩量下跌卖出",
        "params": {"vol_ratio": 1.5, "price_pct": 2.0, "period": 20},
        "code": '''import pandas as pd

def generate_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    vol_ratio = params.get("vol_ratio", 1.5)
    price_pct = params.get("price_pct", 2.0) / 100
    period = params.get("period", 20)

    df["vol_ma"] = df["volume"].rolling(period).mean()
    df["pct_change"] = df["close"].pct_change()

    df["signal"] = 0
    in_position = False

    for i in range(period, len(df)):
        vol = df.iloc[i]["volume"]
        vol_ma = df.iloc[i]["vol_ma"]
        pct = df.iloc[i]["pct_change"]

        if pd.isna(vol_ma) or pd.isna(pct):
            continue

        is_volume_up = vol > vol_ma * vol_ratio
        is_price_up = pct > price_pct
        is_price_down = pct < -price_pct

        if not in_position:
            # 放量上涨 → 买入
            if is_volume_up and is_price_up:
                df.iloc[i, df.columns.get_loc("signal")] = 1
                in_position = True
        else:
            # 缩量下跌 或 放量暴跌 → 卖出
            if is_price_down or (pct < 0 and vol < vol_ma * 0.5):
                df.iloc[i, df.columns.get_loc("signal")] = -1
                in_position = False

    return df
''',
    },
    "trend_follow": {
        "name": "趋势跟踪策略",
        "description": "多均线共振判断趋势，顺势交易",
        "params": {"fast": 5, "mid": 20, "slow": 60},
        "code": '''import pandas as pd

def generate_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    fast = params.get("fast", 5)
    mid = params.get("mid", 20)
    slow = params.get("slow", 60)

    df["ma_fast"] = df["close"].rolling(fast).mean()
    df["ma_mid"] = df["close"].rolling(mid).mean()
    df["ma_slow"] = df["close"].rolling(slow).mean()

    df["signal"] = 0
    in_position = False

    for i in range(slow, len(df)):
        mf = df.iloc[i]["ma_fast"]
        mm = df.iloc[i]["ma_mid"]
        ms = df.iloc[i]["ma_slow"]

        if pd.isna(mf) or pd.isna(mm) or pd.isna(ms):
            continue

        # 多头排列（短>中>长）且未持仓 → 买入
        if mf > mm > ms and not in_position:
            df.iloc[i, df.columns.get_loc("signal")] = 1
            in_position = True
        # 空头排列 或 短均线下穿中均线 → 卖出
        elif in_position and (mf < mm or mf < ms):
            df.iloc[i, df.columns.get_loc("signal")] = -1
            in_position = False

    return df
''',
    },
}
