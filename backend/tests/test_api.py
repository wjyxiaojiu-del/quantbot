import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ── 测试用户认证 ──

_test_token = None


def _auth_header() -> dict:
    """注册测试用户并返回 Authorization header（带缓存）"""
    global _test_token
    if _test_token is None:
        username = f"test_{uuid.uuid4().hex[:8]}"
        email = f"{username}@test.com"
        client.post("/api/v1/auth/register", json={
            "username": username, "email": email, "password": "test123456"
        })
        resp = client.post("/api/v1/auth/login", json={
            "username": username, "password": "test123456"
        })
        _test_token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {_test_token}"}


# ── Health（公开）──

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ── Auth（公开）──

def test_register_and_login():
    username = f"test_{uuid.uuid4().hex[:8]}"
    email = f"{username}@test.com"

    resp = client.post("/api/v1/auth/register", json={
        "username": username, "email": email, "password": "test123456"
    })
    assert resp.status_code == 201
    assert resp.json()["username"] == username

    resp = client.post("/api/v1/auth/login", json={
        "username": username, "password": "test123456"
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == username


def test_login_wrong_password():
    resp = client.post("/api/v1/auth/login", json={
        "username": "nonexistent", "password": "wrong"
    })
    assert resp.status_code == 401


def test_unauthenticated_rejected():
    """未认证请求受保护端点应被拒绝"""
    resp = client.get("/api/v1/dashboard")
    assert resp.status_code in (401, 403)


# ── Market（受保护）──

def test_list_stocks():
    response = client.get("/api/v1/market/stocks", headers=_auth_header())
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_stocks_with_pagination():
    response = client.get("/api/v1/market/stocks?page=1&page_size=5", headers=_auth_header())
    assert response.status_code == 200
    assert len(response.json()) <= 5


def test_get_kline():
    response = client.get("/api/v1/market/stocks/000001.SZ/kline?limit=10", headers=_auth_header())
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_realtime():
    response = client.get("/api/v1/market/stocks/000001.SZ/realtime", headers=_auth_header())
    assert response.status_code == 200
    assert "symbol" in response.json()


# ── Strategy（受保护）──

def test_strategy_crud():
    headers = _auth_header()
    name = f"test_strategy_{uuid.uuid4().hex[:8]}"

    resp = client.post("/api/v1/strategies", json={
        "name": name, "description": "test", "code": "pass", "params": {}
    }, headers=headers)
    assert resp.status_code == 201
    sid = resp.json()["id"]

    resp = client.get(f"/api/v1/strategies/{sid}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == name

    resp = client.get("/api/v1/strategies", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) > 0

    resp = client.put(f"/api/v1/strategies/{sid}", json={"description": "updated"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["description"] == "updated"

    resp = client.delete(f"/api/v1/strategies/{sid}", headers=headers)
    assert resp.status_code == 204


# ── Templates（公开）──

def test_list_templates():
    resp = client.get("/api/v1/templates")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "code" in data[0]


def test_get_template():
    resp = client.get("/api/v1/templates")
    templates = resp.json()
    tid = templates[0]["id"]
    resp = client.get(f"/api/v1/templates/{tid}")
    assert resp.status_code == 200


# ── Backtest（受保护）──

def test_backtest_run():
    headers = _auth_header()
    resp = client.post("/api/v1/backtest/run", json={
        "strategy_code": "import pandas as pd\ndef generate_signals(df, params):\n    df['signal'] = 0\n    return df",
        "symbols": ["000001.SZ"],
        "start_date": "2026-01-01",
        "end_date": "2026-05-15",
        "initial_cash": 1000000,
        "params": {}
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert "metrics" in data
    assert "equity_curve" in data


def test_backtest_history():
    resp = client.get("/api/v1/backtest/history", headers=_auth_header())
    assert resp.status_code == 200
    assert "items" in resp.json()


# ── Trade（受保护）──

def test_portfolio_crud():
    headers = _auth_header()
    name = f"test_pf_{uuid.uuid4().hex[:8]}"

    resp = client.post("/api/v1/trade/portfolios", json={
        "name": name, "initial_cash": 500000
    }, headers=headers)
    assert resp.status_code == 201
    pid = resp.json()["id"]

    resp = client.get("/api/v1/trade/portfolios", headers=headers)
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/trade/portfolios/{pid}", headers=headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["name"] == name
    assert detail["total_equity"] == 500000.0


def test_place_order():
    headers = _auth_header()
    name = f"trade_{uuid.uuid4().hex[:8]}"

    resp = client.post("/api/v1/trade/portfolios", json={"name": name, "initial_cash": 1000000}, headers=headers)
    pid = resp.json()["id"]

    resp = client.post(f"/api/v1/trade/portfolios/{pid}/orders", json={
        "symbol": "000001.SZ", "side": "buy", "price": 15.0, "quantity": 1000
    }, headers=headers)
    assert resp.status_code == 201
    order = resp.json()
    assert order["side"] == "buy"
    assert order["quantity"] == 1000

    resp = client.get(f"/api/v1/trade/portfolios/{pid}", headers=headers)
    detail = resp.json()
    assert detail["position_count"] == 1
    assert detail["cash"] < 1000000


# ── Dashboard（受保护）──

def test_dashboard():
    resp = client.get("/api/v1/dashboard", headers=_auth_header())
    assert resp.status_code == 200
    data = resp.json()
    assert "market" in data
    assert "strategy" in data
    assert "backtest" in data
    assert "portfolio" in data
