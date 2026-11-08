"""직접 추가(auto add)의 날짜 읽기 테스트."""

from datetime import date

import pytest

from autohub.cli import parse_date

TODAY = date(2026, 11, 8)


@pytest.mark.parametrize("text", ["12/1", "12.1", "12-01", "12월 1일", "2026-12-01", "26.12.1"])
def test_parse_date_formats(text):
    assert parse_date(text, TODAY) == date(2026, 12, 1)


def test_past_month_day_means_next_year():
    assert parse_date("3/2", TODAY) == date(2027, 3, 2)


def test_bad_date():
    with pytest.raises(ValueError):
        parse_date("다음주", TODAY)
