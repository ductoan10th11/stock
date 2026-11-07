import os

import pytest

os.environ["AUTO_REFRESH"] = "0"


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setattr("app.db.PAPER_DB_PATH", tmp_path / "paper.db")
