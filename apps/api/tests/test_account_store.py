import pytest

from app.db import MIGRATIONS, connect
from app.services.account_store import delete_account, load_account, save_account
from app.services.engine import Params
from app.services.paper import new_account


def sample() -> dict:
    return new_account({"model": 1.0, "momentum_60d": 0.5}, Params(buffer=2.0, min_hold=2), 1e9, "2026-11-06", 10.0)


def trade(date: str, symbol: str = "PVD", side: str = "buy") -> dict:
    return {"date": date, "symbol": symbol, "side": side, "shares": 100, "price": 17.0, "value": 1.7e6, "fee": 2550.0}


def test_round_trip_keeps_every_field():
    account = sample()
    save_account(account)
    loaded = load_account()
    assert loaded == {**account, "id": account["id"]}
    assert loaded["params"]["min_score"] is None and loaded["weights"] == {"model": 1.0, "momentum_60d": 0.5}


def test_save_appends_only_new_rows_and_replaces_positions():
    account = sample()
    save_account(account)
    account["trades"].append(trade("2026-11-09"))
    account["equity"].append({"date": "2026-11-09", "cash": 9e8, "value": 1e8, "equity": 1e9})
    account["positions"]["PVD"] = {"shares": 100, "held": 0, "cost": 17.0}
    account["cash"], account["last_date"] = 9e8, "2026-11-09"
    save_account(account)
    account["trades"].append(trade("2026-11-10", side="sell"))
    account["positions"].clear()
    save_account(account)
    loaded = load_account()
    assert [t["date"] for t in loaded["trades"]] == ["2026-11-09", "2026-11-10"]
    assert len(loaded["equity"]) == 1 and loaded["positions"] == {}
    assert loaded["cash"] == 9e8 and loaded["last_date"] == "2026-11-09"


def test_delete_removes_children():
    account = sample()
    account["trades"].append(trade("2026-11-09"))
    save_account(account)
    delete_account(account["id"])
    assert load_account() is None
    assert connect().execute("SELECT COUNT(*) FROM trade").fetchone()[0] == 0


def test_two_accounts_stay_separate():
    first, second = sample(), sample()
    first["trades"].append(trade("2026-11-09"))
    save_account(first)
    save_account(second)
    assert len(load_account(first["id"])["trades"]) == 1
    assert load_account(second["id"])["trades"] == []


def test_constraints_reject_bad_rows():
    account = sample()
    account["trades"].append({**trade("2026-11-09"), "side": "hold"})
    with pytest.raises(Exception):
        save_account(account)
    assert load_account() is None


def test_schema_version_matches_migrations():
    assert connect().execute("PRAGMA user_version").fetchone()[0] == len(MIGRATIONS)
