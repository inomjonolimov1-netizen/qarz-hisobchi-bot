"""Oddiy parser testlari (pytest)."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.environ.setdefault("BOT_TOKEN", "0:TEST_TOKEN_FOR_PYTEST")

import pytest
from bot import parse_debt


@pytest.mark.parametrize("text,expect_name", [
    ("Alisher 500000 qarz", "Alisher"),
    ("inomjon6000", "inomjon"),
    ("Ali 100000қарз", "Ali"),
])
def test_parse_debt_name(text, expect_name):
    r = parse_debt(text)
    assert r is not None
    assert r["name"].lower().startswith(expect_name.lower()) or r["name"] == expect_name


def test_parse_repayment():
    r = parse_debt("Alisher 200000 berdi")
    assert r and r["is_repayment"]


def test_parse_too_short():
    assert parse_debt("ab") is None
