"""
Tests for the TADPOLE bot.

Run with:  pytest tests/
"""

import asyncio
import os
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure project root is importable without installing the package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Minimal stubs for botbuilder so tests run without installing the SDK.
# ---------------------------------------------------------------------------

def _make_botbuilder_stubs():
    """Inject lightweight stub modules so imports in bot.py succeed."""
    # botbuilder.core
    core = types.ModuleType("botbuilder.core")
    core.ActivityHandler = object
    core.TurnContext = object
    sys.modules.setdefault("botbuilder", types.ModuleType("botbuilder"))
    sys.modules["botbuilder.core"] = core

    # botbuilder.schema
    schema = types.ModuleType("botbuilder.schema")
    schema.Activity = object
    schema.ActivityTypes = object
    sys.modules["botbuilder.schema"] = schema


_make_botbuilder_stubs()


# ---------------------------------------------------------------------------
# Tests: CSV connector
# ---------------------------------------------------------------------------

class TestCSVConnector(unittest.TestCase):
    """Unit tests for data/csv_connector.py."""

    def setUp(self):
        # Reset the in-memory SQLite cache before each test.
        import data.csv_connector as mod
        mod._db_conn = None
        mod._loaded_path = None

    def _make_config(self, csv_path):
        cfg = MagicMock()
        cfg.CSV_PATH = csv_path
        cfg.CSV_TAID_COLUMN = "TAID"
        cfg.CSV_RS_COLUMN = "RS_CODE"
        return cfg

    def test_lookup_existing_taid(self):
        from data.csv_connector import get_rs_code

        csv_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "sample_taid_rs_codes.csv"
        )
        config = self._make_config(os.path.abspath(csv_path))
        result = get_rs_code("TAID-001", config)
        self.assertEqual(result, "RS-A100")

    def test_lookup_missing_taid(self):
        from data.csv_connector import get_rs_code

        csv_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "sample_taid_rs_codes.csv"
        )
        config = self._make_config(os.path.abspath(csv_path))
        result = get_rs_code("TAID-UNKNOWN", config)
        self.assertIsNone(result)

    def test_lookup_all_sample_entries(self):
        from data.csv_connector import get_rs_code

        csv_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "sample_taid_rs_codes.csv"
        )
        config = self._make_config(os.path.abspath(csv_path))
        expected = {
            "TAID-001": "RS-A100",
            "TAID-002": "RS-B200",
            "TAID-010": "RS-J000",
        }
        for taid, rs in expected.items():
            with self.subTest(taid=taid):
                self.assertEqual(get_rs_code(taid, config), rs)

    def test_missing_column_raises(self):
        import tempfile
        import pandas as pd
        from data.csv_connector import get_rs_code
        import data.csv_connector as mod

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("WRONG_COL,RS_CODE\nX,Y\n")
            tmp = f.name

        mod._db_conn = None
        mod._loaded_path = None

        try:
            config = self._make_config(tmp)
            with self.assertRaises(ValueError):
                get_rs_code("X", config)
        finally:
            os.unlink(tmp)


# ---------------------------------------------------------------------------
# Tests: unified lookup layer
# ---------------------------------------------------------------------------

class TestLookup(unittest.TestCase):
    """Unit tests for data/lookup.py."""

    def _make_config(self, data_source="csv", **kwargs):
        cfg = MagicMock()
        cfg.DATA_SOURCE = data_source
        cfg.SNOWFLAKE_ACCOUNT = kwargs.get("SNOWFLAKE_ACCOUNT", "")
        cfg.ORACLE_DSN = kwargs.get("ORACLE_DSN", "")
        csv_path = os.path.join(
            os.path.dirname(__file__), "..", "data", "sample_taid_rs_codes.csv"
        )
        cfg.CSV_PATH = os.path.abspath(csv_path)
        cfg.CSV_TAID_COLUMN = "TAID"
        cfg.CSV_RS_COLUMN = "RS_CODE"
        return cfg

    def setUp(self):
        import data.csv_connector as mod
        mod._db_conn = None
        mod._loaded_path = None

    def test_csv_source_found(self):
        from data.lookup import get_rs_code

        config = self._make_config(data_source="csv")
        self.assertEqual(get_rs_code("TAID-003", config), "RS-C300")

    def test_csv_source_not_found(self):
        from data.lookup import get_rs_code

        config = self._make_config(data_source="csv")
        self.assertIsNone(get_rs_code("TAID-NOPE", config))

    def test_auto_detect_falls_through_to_csv(self):
        """With no Snowflake/Oracle credentials, auto-detect should reach CSV."""
        from data.lookup import get_rs_code

        config = self._make_config(data_source="")
        # No credentials → Snowflake and Oracle skipped → CSV consulted.
        self.assertEqual(get_rs_code("TAID-005", config), "RS-E500")

    def test_snowflake_returns_result(self):
        from data.lookup import get_rs_code

        config = self._make_config(data_source="snowflake", SNOWFLAKE_ACCOUNT="acct")
        with patch("data.snowflake_connector.get_rs_code", return_value="RS-X999") as mock_sf:
            result = get_rs_code("TAID-001", config)
        mock_sf.assert_called_once_with("TAID-001", config)
        self.assertEqual(result, "RS-X999")

    def test_oracle_returns_result(self):
        from data.lookup import get_rs_code

        config = self._make_config(data_source="oracle", ORACLE_DSN="host:1521/svc")
        with patch("data.oracle_connector.get_rs_code", return_value="RS-O001") as mock_ora:
            result = get_rs_code("TAID-002", config)
        mock_ora.assert_called_once_with("TAID-002", config)
        self.assertEqual(result, "RS-O001")


# ---------------------------------------------------------------------------
# Tests: bot message parsing helpers
# ---------------------------------------------------------------------------

class TestBotHelpers(unittest.TestCase):
    """Unit tests for helper functions in bot.py."""

    def test_extract_taid_plain(self):
        from bot import _extract_taid

        self.assertEqual(_extract_taid("TAID-001"), "TAID-001")

    def test_extract_taid_in_sentence(self):
        from bot import _extract_taid

        self.assertEqual(
            _extract_taid("Can you convert TAID-005 for me?"), "TAID-005"
        )

    def test_extract_taid_case_insensitive(self):
        from bot import _extract_taid

        result = _extract_taid("what is the rs code for taid-007")
        self.assertIsNotNone(result)
        self.assertEqual(result.upper(), "TAID-007")

    def test_extract_taid_no_match(self):
        from bot import _extract_taid

        self.assertIsNone(_extract_taid("hello there"))

    def test_extract_taid_underscore_separator(self):
        from bot import _extract_taid

        self.assertEqual(_extract_taid("TAID_010"), "TAID_010")


if __name__ == "__main__":
    unittest.main()
