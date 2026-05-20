import pytest
import uuid
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
    assert isinstance(response.json(), list)


def test_list_stocks_with_pagination():
    response = client.get("/api/v1/market/stocks?page=1&page_size=5")
    assert response.status_code == 200
    assert len(response.json()) <= 5


def test_get_kline():
    response = client.get("/api/v1/market/stocks/000001.SZ/kline?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_realtime():
    response = client.get("/api/v1/market/stocks/000001.SZ/realtime")
    assert response.status_code == 200
    assert "symbol" in response.json()


# ── Strategy ──

def test_strategy_crud():
    name = f"test_strategy_{uuid.uuid4().hex[:8]}"

    resp = client.post("/api/v1/strategies", json={
        "name": name, "description": "test", "code": "pass", "params": {}
    })
    assert resp.status_code == 201
    sid = resp.json()["id"]

    resp = client.get(f"/api/v1/strategies/{sid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == name

    resp = client.get("/api/v1/strategies")
    assert resp.status_code == 200
    assert len(resp.json()) > 0

    resp = client.put(f"/api/v1/strategies/{sid}", json={"description": "updated"})
    assert resp.status_code == 200
    assert resp.json()["description"] == "updated"

    resp = client.delete(f"/api/v1/strategies/{sid}")
    assert resp.status_code == 204


# ── Templates ──

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
    assert "items" in resp.json()


# ── Dashboard ──

def test_dashboard():
    resp = client.get("/api/v1/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "market" in data
    assert "strategy" in data
    assert "backtest" in data
