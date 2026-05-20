# QuantBot - 个人量化交易平台

基于 FastAPI + Next.js 构建的策略研究、回测验证、模拟交易一体化平台。

## 功能模块

| 模块 | 功能 | 状态 |
|------|------|------|
| 数据源 | akshare(默认)/baostock/yfinance/eastmoney + 实时行情 | ✅ |
| 策略管理 | CRUD + 代码验证 + 内置模板（双均线/MACD/RSI/布林/KNN） | ✅ |
| 回测引擎 | 信号驱动 + 多股票 + 风控（止损止盈/仓位控制/回撤熔断） | ✅ |
| 模拟交易 | 虚拟资金 + 佣金印花税 + A 股整手规则 | ✅ |
| 实时行情 | WebSocket 推送 + 自动重连 | ✅ |
| 用户认证 | JWT + SHA256 | ✅ |
| 定时任务 | Celery + Redis（每日 K 线同步、每周股票列表） | ✅ |
| Dashboard | 资产概览 + 市场统计 + 最近交易 | ✅ |

## 技术栈

**后端：** FastAPI / SQLAlchemy / SQLite(开发) + PostgreSQL(生产) / Redis / Celery / akshare / yfinance

**前端：** Next.js 14 / Tailwind CSS / lightweight-charts / axios

## 快速开始

### 本地开发

```bash
# 后端
cd backend
cp .env.example .env  # 按需修改
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

### Docker 部署

```bash
cp backend/.env.example backend/.env  # 按需修改 SECRET_KEY 等
docker-compose up -d
```

服务：
- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 项目结构

```
quantbot/
├── backend/
│   ├── app/
│   │   ├── api/endpoints/     # API 端点
│   │   ├── core/              # 配置、数据库、认证、兼容层
│   │   ├── models/            # SQLAlchemy 模型
│   │   ├── schemas/           # Pydantic 校验
│   │   ├── services/
│   │   │   ├── backtest/      # 回测引擎 + 策略模板
│   │   │   ├── data/          # 数据源适配器（baostock/eastmoney/akshare/mock）
│   │   │   ├── risk/          # 风控管理
│   │   │   ├── strategy/      # 策略执行器
│   │   │   └── trade/         # 交易引擎
│   │   ├── tasks.py           # Celery 定时任务
│   │   └── main.py            # FastAPI 应用
│   └── tests/                 # 测试（37 个）
├── frontend/
│   └── src/app/               # Next.js 页面
│       ├── page.tsx           # Dashboard
│       ├── market/            # 行情中心
│       ├── strategies/        # 策略管理
│       ├── backtest/          # 策略回测
│       ├── trade/             # 模拟交易
│       └── login/             # 登录
├── docker-compose.yml
└── README.md
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/dashboard | Dashboard 数据 |
| GET | /api/v1/market/stocks | 股票列表 |
| GET | /api/v1/market/stocks/{symbol}/kline | K 线数据 |
| GET | /api/v1/market/stocks/{symbol}/realtime | 实时行情 |
| POST | /api/v1/market/sync | 同步 K 线 |
| GET/POST | /api/v1/strategies | 策略 CRUD |
| POST | /api/v1/strategies/{id}/execute | 执行策略生成信号 |
| POST | /api/v1/backtest/run | 运行回测 |
| GET | /api/v1/backtest/history | 回测历史 |
| GET/POST | /api/v1/trade/portfolios | 交易组合 |
| POST | /api/v1/trade/portfolios/{id}/orders | 下单 |
| WS | /api/v1/ws/quotes | 实时行情推送 |
| POST | /api/v1/auth/register | 注册 |
| POST | /api/v1/auth/login | 登录 |

## 策略编写规范

策略代码必须定义 `generate_signals(df, params)` 函数，返回包含 `signal` 列的 DataFrame：
- `1` = 买入
- `-1` = 卖出
- `0` = 持有

```python
import pandas as pd

def generate_signals(df, params):
    short = params.get("short_window", 5)
    long = params.get("long_window", 20)
    df["ma_short"] = df["close"].rolling(short).mean()
    df["ma_long"] = df["close"].rolling(long).mean()
    df["signal"] = 0
    df.loc[df["ma_short"] > df["ma_long"], "signal"] = 1
    df.loc[df["ma_short"] < df["ma_long"], "signal"] = -1
    return df
```

## 风控规则

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 单只最大仓位 | 20% | 防止单股集中 |
| 总仓位上限 | 80% | 保留现金缓冲 |
| 止损线 | 8% | 自动清仓 |
| 止盈线 | 20% | 自动止盈 |
| 单日亏损限制 | 3% | 暂停交易 |
| 最大回撤 | 15% | 全仓熔断 |

## 测试

```bash
cd backend
python -m pytest tests/ -v
```

38 个测试覆盖：风控引擎、回测引擎、API 端点、认证保护。
