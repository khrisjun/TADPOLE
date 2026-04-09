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
# Tests: identifier validator (data/utils.py)
# ---------------------------------------------------------------------------

class TestValidateIdentifier(unittest.TestCase):
    """Unit tests for data/utils.validate_identifier."""

    def test_plain_name(self):
        from data.utils import validate_identifier
        self.assertEqual(validate_identifier("BY_DMDUNIT"), "BY_DMDUNIT")

    def test_name_with_dollar_sign(self):
        """Snowflake database names may contain '$'."""
        from data.utils import validate_identifier
        name = "ORGDATACLOUD$INTERNAL$BLUE_YONDER"
        self.assertEqual(validate_identifier(name, "database"), name)

    def test_schema_qualified_name(self):
        from data.utils import validate_identifier
        self.assertEqual(
            validate_identifier("BLUE_YONDER.BY_DMDUNIT"), "BLUE_YONDER.BY_DMDUNIT"
        )

    def test_invalid_name_raises(self):
        from data.utils import validate_identifier
        with self.assertRaises(ValueError):
            validate_identifier("bad name; DROP TABLE x--", "table")

    def test_invalid_name_with_quote_raises(self):
        from data.utils import validate_identifier
        with self.assertRaises(ValueError):
            validate_identifier("col' OR '1'='1", "column")


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
        cfg.CSV_TAID_COLUMN = "DMDUNIT"
        cfg.CSV_RS_COLUMN = "U_RS_PRODUCT_CODE"
        return cfg

    def _csv_path(self):
        return os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data", "sample_taid_rs_codes.csv")
        )

    def test_lookup_existing_taid(self):
        from data.csv_connector import get_rs_code

        config = self._make_config(self._csv_path())
        result = get_rs_code("DMDUNIT-001", config)
        self.assertEqual(result, "RS-A100")

    def test_lookup_missing_taid(self):
        from data.csv_connector import get_rs_code

        config = self._make_config(self._csv_path())
        result = get_rs_code("DMDUNIT-UNKNOWN", config)
        self.assertIsNone(result)

    def test_lookup_all_sample_entries(self):
        from data.csv_connector import get_rs_code

        config = self._make_config(self._csv_path())
        expected = {
            "DMDUNIT-001": "RS-A100",
            "DMDUNIT-002": "RS-B200",
            "DMDUNIT-010": "RS-J000",
        }
        for taid, rs in expected.items():
            with self.subTest(taid=taid):
                self.assertEqual(get_rs_code(taid, config), rs)

    def test_missing_column_raises(self):
        import tempfile
        from data.csv_connector import get_rs_code
        import data.csv_connector as mod

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("WRONG_COL,U_RS_PRODUCT_CODE\nX,Y\n")
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
        cfg.CSV_PATH = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data", "sample_taid_rs_codes.csv")
        )
        cfg.CSV_TAID_COLUMN = "DMDUNIT"
        cfg.CSV_RS_COLUMN = "U_RS_PRODUCT_CODE"
        return cfg

    def setUp(self):
        import data.csv_connector as mod
        mod._db_conn = None
        mod._loaded_path = None

    def test_csv_source_found(self):
        from data.lookup import get_rs_code

        config = self._make_config(data_source="csv")
        self.assertEqual(get_rs_code("DMDUNIT-003", config), "RS-C300")

    def test_csv_source_not_found(self):
        from data.lookup import get_rs_code

        config = self._make_config(data_source="csv")
        self.assertIsNone(get_rs_code("DMDUNIT-NOPE", config))

    def test_auto_detect_falls_through_to_csv(self):
        """With no Snowflake/Oracle credentials, auto-detect should reach CSV."""
        from data.lookup import get_rs_code

        config = self._make_config(data_source="")
        # No credentials → Snowflake and Oracle skipped → CSV consulted.
        self.assertEqual(get_rs_code("DMDUNIT-005", config), "RS-E500")

    def test_snowflake_returns_result(self):
        from data.lookup import get_rs_code

        config = self._make_config(data_source="snowflake", SNOWFLAKE_ACCOUNT="acct")
        with patch("data.snowflake_connector.get_rs_code", return_value="RS-X999") as mock_sf:
            result = get_rs_code("DMDUNIT-001", config)
        mock_sf.assert_called_once_with("DMDUNIT-001", config)
        self.assertEqual(result, "RS-X999")

    def test_oracle_returns_result(self):
        from data.lookup import get_rs_code

        config = self._make_config(data_source="oracle", ORACLE_DSN="host:1521/svc")
        with patch("data.oracle_connector.get_rs_code", return_value="RS-O001") as mock_ora:
            result = get_rs_code("DMDUNIT-002", config)
        mock_ora.assert_called_once_with("DMDUNIT-002", config)
        self.assertEqual(result, "RS-O001")


# ---------------------------------------------------------------------------
# Tests: Snowflake connector – connect_kwargs construction
# ---------------------------------------------------------------------------

class TestSnowflakeConnector(unittest.TestCase):
    """Unit tests for data/snowflake_connector.py (without a real connection)."""

    def _make_config(self, authenticator="externalbrowser", password=""):
        cfg = MagicMock()
        cfg.SNOWFLAKE_ACCOUNT = "tf78969.eu-west-1"
        cfg.SNOWFLAKE_USER = "user@rsgroup.com"
        cfg.SNOWFLAKE_PASSWORD = password
        cfg.SNOWFLAKE_DATABASE = "ORGDATACLOUD$INTERNAL$BLUE_YONDER"
        cfg.SNOWFLAKE_SCHEMA = "BLUE_YONDER"
        cfg.SNOWFLAKE_WAREHOUSE = "LAB_10_COMPUTE_DEFAULT_VWH"
        cfg.SNOWFLAKE_ROLE = "LAB10_FULL_ROLE"
        cfg.SNOWFLAKE_AUTHENTICATOR = authenticator
        cfg.SNOWFLAKE_CLIENT_STORE_TEMP_CREDENTIAL = True
        cfg.SNOWFLAKE_TABLE = "BY_DMDUNIT"
        cfg.SNOWFLAKE_TAID_COLUMN = "DMDUNIT"
        cfg.SNOWFLAKE_RS_COLUMN = "U_RS_PRODUCT_CODE"
        return cfg

    def test_externalbrowser_omits_password_includes_cache_flag(self):
        """externalbrowser auth must not pass a password and must set the cache flag."""
        import types as _types
        import sys as _sys
        import importlib

        captured = {}

        def fake_connect(**kwargs):
            captured.update(kwargs)
            raise RuntimeError("stop")  # abort before cursor usage

        # Inject a minimal snowflake.connector stub so the test runs without
        # the real package being installed.
        sf_stub = _types.ModuleType("snowflake.connector")
        sf_stub.connect = fake_connect
        sf_parent = _types.ModuleType("snowflake")
        sf_parent.connector = sf_stub
        _sys.modules["snowflake"] = sf_parent
        _sys.modules["snowflake.connector"] = sf_stub

        import data.snowflake_connector
        importlib.reload(data.snowflake_connector)

        from data.snowflake_connector import get_rs_code
        with self.assertRaises(RuntimeError):
            get_rs_code("DMDUNIT-001", self._make_config())

        self.assertNotIn("password", captured)
        self.assertTrue(captured.get("client_store_temporary_credential"))
        self.assertEqual(captured.get("authenticator"), "externalbrowser")
        self.assertEqual(captured.get("role"), "LAB10_FULL_ROLE")

    def test_password_auth_includes_password_no_cache_flag(self):
        """Password-based auth must pass password and must not set the cache flag."""
        import types as _types
        import sys as _sys
        import importlib

        captured = {}

        def fake_connect(**kwargs):
            captured.update(kwargs)
            raise RuntimeError("stop")

        sf_stub = _types.ModuleType("snowflake.connector")
        sf_stub.connect = fake_connect
        sf_parent = _types.ModuleType("snowflake")
        sf_parent.connector = sf_stub
        _sys.modules["snowflake"] = sf_parent
        _sys.modules["snowflake.connector"] = sf_stub

        import data.snowflake_connector
        importlib.reload(data.snowflake_connector)

        from data.snowflake_connector import get_rs_code
        with self.assertRaises(RuntimeError):
            get_rs_code(
                "DMDUNIT-001",
                self._make_config(authenticator="snowflake", password="s3cr3t"),
            )

        self.assertEqual(captured.get("password"), "s3cr3t")
        self.assertNotIn("client_store_temporary_credential", captured)

    def test_dollar_sign_database_passes_validation(self):
        """ORGDATACLOUD$INTERNAL$BLUE_YONDER must not be rejected by the validator."""
        from data.utils import validate_identifier
        result = validate_identifier("ORGDATACLOUD$INTERNAL$BLUE_YONDER", "database")
        self.assertEqual(result, "ORGDATACLOUD$INTERNAL$BLUE_YONDER")


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
