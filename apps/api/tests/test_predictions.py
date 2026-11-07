import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


def test_latest_ranks_every_symbol_with_probabilities_that_sum_to_one(client):
    body = client.get("/api/predictions").json()
    assert [row["rank"] for row in body["rows"]] == list(range(1, len(body["rows"]) + 1)) and len(body["rows"]) == 19
    assert body["in_sample"] is False
    for row in body["rows"]:
        assert abs(row["p_down"] + row["p_flat"] + row["p_up"] - 1) < 1e-6
        top = max(("down", row["p_down"]), ("flat", row["p_flat"]), ("up", row["p_up"]), key=lambda pair: pair[1])
        assert row["direction"] == top[0]


def test_symbol_history_joins_candles_with_honest_predictions(client):
    body = client.get("/api/predictions/PVD?days=120").json()
    candle_dates = {c["date"] for c in body["candles"]}
    assert len(candle_dates) == 120
    assert all(p["date"] in candle_dates for p in body["predictions"])
    for p in body["predictions"]:
        assert (p["date"] <= body["last_oos_date"]) == (p["source"] == "oos") or p["date"] > body["trained_until"]
        assert not (body["last_oos_date"] < p["date"] <= body["trained_until"]), "in-sample dates must have no prediction"
    assert body["next_session"]["date"] == body["candles"][-1]["date"]
    assert body["predictions"][-1]["correct"] is None
    assert 0 < body["hit_rate"]["total"] and body["hit_rate"]["correct"] <= body["hit_rate"]["total"]


def test_unknown_symbol_is_404(client):
    assert client.get("/api/predictions/XXX").status_code == 404
