"""Unit tests for the lookup_order builtin skill."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestLookupOrder:
    def test_found_order(self, monkeypatch):
        monkeypatch.chdir(PROJECT_ROOT)
        from skills.builtin.lookup_order import lookup_order
        orders_path = PROJECT_ROOT / "data" / "orders.json"
        if not orders_path.exists():
            pytest.skip("data/orders.json not generated yet")
        orders = json.loads(orders_path.read_text())
        first_order_id = orders[0]["order_id"]
        result = lookup_order(first_order_id)
        assert result["found"] is True
        assert result["order"]["order_id"] == first_order_id

    def test_not_found_returns_found_false(self, monkeypatch):
        monkeypatch.chdir(PROJECT_ROOT)
        from skills.builtin.lookup_order import lookup_order
        orders_path = PROJECT_ROOT / "data" / "orders.json"
        if not orders_path.exists():
            pytest.skip("data/orders.json not generated yet")
        result = lookup_order("NONEXISTENT-ORDER-ID-ZZZ-99999")
        assert result["found"] is False
        assert result["order_id"] == "NONEXISTENT-ORDER-ID-ZZZ-99999"

    def test_missing_database_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from skills.builtin.lookup_order import lookup_order
        result = lookup_order("any-id")
        assert "error" in result

    def test_prefix_match(self, monkeypatch):
        monkeypatch.chdir(PROJECT_ROOT)
        from skills.builtin.lookup_order import lookup_order
        orders_path = PROJECT_ROOT / "data" / "orders.json"
        if not orders_path.exists():
            pytest.skip("data/orders.json not generated yet")
        orders = json.loads(orders_path.read_text())
        first_order_id = orders[0]["order_id"]
        prefix = first_order_id[:6]
        result = lookup_order(prefix)
        assert result["found"] is True

    def test_kwargs_ignored(self, monkeypatch):
        monkeypatch.chdir(PROJECT_ROOT)
        from skills.builtin.lookup_order import lookup_order
        orders_path = PROJECT_ROOT / "data" / "orders.json"
        if not orders_path.exists():
            pytest.skip("data/orders.json not generated yet")
        result = lookup_order("NONEXISTENT-999", extra_param="ignored")
        assert result["found"] is False
