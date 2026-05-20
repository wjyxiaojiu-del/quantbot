import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Health ──

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ── Market ──

def test_list_stocks():
    response = client.get("/api/v1/market/stocks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_list_stocks_with_pagination():
    response = client.get("/api/v1/market/stocks?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5


def test_get_kline():
    response = client.get("/api/v1/market/stocks/000001.SZ/kline?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_realtime():
    response = client.get("/api/v1/market/stocks/000001.SZ/realtime")
    assert response.status_code == 200
    data = response.json()
    assert "symbol" in data


# ── Auth ──

def test_register_and_login():
    import uuid
    username = f"test_{uuid.uuid4().hex[:8]}"
    email = f"{username}@test.com"

    # Register
    resp = client.post("/api/v1/auth/register", json={
        "username": username, "email": email, "password": "test123456"
    })
    assert resp.status_code == 201
    user = resp.json()
    assert user["username"] == username

    # Login
    resp = client.post("/api/v1/auth/login", json={
        "username": username, "password": "test123456"
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    # Me
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == username


def test_login_wrong_password():
    resp = client.post("/api/v1/auth/login", json={
        "username": "nonexistent", "password": "wrong"
    })
    assert resp.status_code == 401


# ── Strategy ──

def test_strategy_crud():
    import uuid
    name = f"test_strategy_{uuid.uuid4().hex[:8]}"

    # Create
    resp = client.post("/api/v1/strategies/", json={
        "name": name, "description": "test", "code": "pass", "params": {}
    })
    assert resp.status_code == 201
    strategy = resp.json()
    sid = strategy["id"]

    # Get
    resp = client.get(f"/api/v1/strategies/{sid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == name

    # List
    resp = client.get("/api/v1/strategies/")
    assert resp.status_code == 200
    assert len(resp.json()) > 0

    # Update
    resp = client.put(f"/api/v1/strategies/{sid}", json={"description": "updated"})
    assert resp.status_code == 200
    assert resp.json()["description"] == "updated"

    # Delete
    resp = client.delete(f"/api/v1/strategies/{sid}")
    assert resp.status_code == 204


# ── Templates ──

def test_list_templates():
    resp = client.get("/api/v1/templates/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "code" in data[0]


def test_get_template():
    resp = client.get("/api/v1/templates/")
    templates = resp.json()
    tid = templates[0]["id"]
    resp = client.get(f"/api/v1/templates/{tid}")
    assert resp.status_code == 200


# ── Backtest ──

def test_backtest_run():
    resp = client.post("/api/v1/backtest/run", json={
        "strategy_code": "import pandas as pd\ndef generate_signals(df, params):\n    df['signal'] = 0\n    return df",
        "symbols": ["000001.SZ"],
        "start_date": "2026-01-01",
        "end_date": "2026-05-15",
        "initial_cash": 1000000,
        "params": {}
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert "metrics" in data
    assert "equity_curve" in data


def test_backtest_history():
    resp = client.get("/api/v1/backtest/history")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


# ── Trade ──

def test_portfolio_crud():
    import uuid
    name = f"test_pf_{uuid.uuid4().hex[:8]}"

    # Create
    resp = client.post("/api/v1/trade/portfolios", json={
        "name": name, "initial_cash": 500000
    })
    assert resp.status_code == 201
    pf = resp.json()
    pid = pf["id"]

    # List
    resp = client.get("/api/v1/trade/portfolios")
    assert resp.status_code == 200

    # Get detail
    resp = client.get(f"/api/v1/trade/portfolios/{pid}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["name"] == name
    assert detail["total_equity"] == 500000.0


def test_place_order():
    import uuid
    name = f"trade_{uuid.uuid4().hex[:8]}"

    # Create portfolio
    resp = client.post("/api/v1/trade/portfolios", json={"name": name, "initial_cash": 1000000})
    pid = resp.json()["id"]

    # Buy order
    resp = client.post(f"/api/v1/trade/portfolios/{pid}/orders", json={
        "symbol": "000001.SZ", "side": "buy", "price": 15.0, "quantity": 1000
    })
    assert resp.status_code == 201
    order = resp.json()
    assert order["side"] == "buy"
    assert order["quantity"] == 1000

    # Check portfolio
    resp = client.get(f"/api/v1/trade/portfolios/{pid}")
    detail = resp.json()
    assert detail["position_count"] == 1
    assert detail["cash"] < 1000000


# ── Dashboard ──

def test_dashboard():
    resp = client.get("/api/v1/dashboard/")
    assert resp.status_code == 200
    data = resp.json()
    assert "market" in data
    assert "strategy" in data
    assert "backtest" in data
    assert "portfolio" in data
