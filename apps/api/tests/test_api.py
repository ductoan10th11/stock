import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_meta_lists_strategies_and_presets(client):
    body = client.get("/api/meta").json()
    assert body["backtest_ready"] is True
    assert {"model", "blend"} <= {s["id"] for s in body["strategies"]}
    assert {p["id"] for p in body["presets"]} == {"next_open", "close"}


def test_backtest_returns_aligned_series(client):
    response = client.post("/api/backtest", json={"strategies": ["model", "momentum_12_1"], "period": "confirm"})
    assert response.status_code == 200
    body = response.json()
    assert body["sessions"] == len(body["dates"]) > 100
    assert {m["key"] for m in body["metrics"]} == {"model", "momentum_12_1", "equal_weight", "vnindex"}
    assert all(len(c["wealth"]) == len(c["drawdown"]) == body["sessions"] for c in body["curves"])
    assert body["dates"][0] >= "2025-01-01"
    assert body["yearly"]["columns"] == ["2025", "2026"]


def test_random_baseline_is_a_separate_cached_request(client):
    request = {"strategies": ["model"], "period": "confirm"}
    row = client.post("/api/backtest/random", json=request).json()
    assert row["key"] == "random" and row["kind"] == "random" and row["total_return"] is not None
    assert client.post("/api/backtest/random", json=request).json() == row


def test_backtest_rejects_blend_without_weights(client):
    response = client.post("/api/backtest", json={"strategies": ["blend"], "blend_weights": {"model": 0}})
    assert response.status_code == 422


def test_backtest_rejects_unknown_strategy(client):
    assert client.post("/api/backtest", json={"strategies": ["nope"]}).status_code == 422


def test_paper_state_is_readable(client):
    response = client.get("/api/paper")
    assert response.status_code == 200
    assert response.json()["trained_until"] == "2026-11-04"


def test_model_review_list_and_detail_share_the_window(client):
    listing = client.get("/api/backtest/predictions", params={"span": "month"}).json()
    assert listing["end"] == listing["last_date"] and len(listing["rows"]) == 19
    assert listing["total"] == sum(row["total"] for row in listing["rows"]) > 0
    detail = client.get("/api/backtest/predictions/ACB", params={"start": listing["start"], "end": listing["end"]}).json()
    assert detail["next_session"] is None and detail["candles"][0]["date"] >= listing["start"]
    row = next(row for row in listing["rows"] if row["symbol"] == "ACB")
    assert detail["hit_rate"] is None or (detail["hit_rate"]["correct"], detail["hit_rate"]["total"]) == (row["correct"], row["total"])


def test_model_review_rejects_bad_requests(client):
    assert client.get("/api/backtest/predictions/NOPE").status_code == 404
    assert client.get("/api/backtest/predictions", params={"start": "2030-01-01"}).status_code == 422
