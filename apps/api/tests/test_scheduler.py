from datetime import datetime

from app.services.scheduler import next_run
from crawl import VN


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=VN)


def test_before_the_run_time_runs_today():
    assert next_run(at(9, 10)) == at(9, 15, 30)


def test_after_the_run_time_runs_next_weekday():
    assert next_run(at(10, 16)) == at(11, 15, 30)


def test_friday_evening_and_weekend_run_on_monday():
    for now in (at(6, 16), at(7, 9), at(8, 20)):
        assert next_run(now) == at(9, 15, 30)


def test_exactly_at_the_run_time_waits_for_the_next_one():
    assert next_run(at(9, 15, 30)) == at(10, 15, 30)
