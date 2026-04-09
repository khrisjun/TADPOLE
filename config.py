"""
Configuration loader for the TADPOLE Teams bot.

All settings are read from environment variables (with sensible defaults).
Copy .env.example to .env and fill in your values, then load with:
    python-dotenv or export manually before running app.py
"""

import os


class DefaultConfig:
    """Bot and data-source configuration."""

    # ── Microsoft Bot Framework credentials ──────────────────────────────────
    APP_ID: str = os.environ.get("MicrosoftAppId", "")
    APP_PASSWORD: str = os.environ.get("MicrosoftAppPassword", "")

    # ── Web server ────────────────────────────────────────────────────────────
    PORT: int = int(os.environ.get("PORT", 3978))

    # ── Data source selection ─────────────────────────────────────────────────
    # Supported values: "snowflake", "oracle", "csv"
    # If not set the lookup layer will try each source in that priority order.
    DATA_SOURCE: str = os.environ.get("DATA_SOURCE", "")

    # ── Snowflake ─────────────────────────────────────────────────────────────
    SNOWFLAKE_ACCOUNT: str = os.environ.get("SNOWFLAKE_ACCOUNT", "tf78969.eu-west-1")
    SNOWFLAKE_USER: str = os.environ.get("SNOWFLAKE_USER", "")
    SNOWFLAKE_PASSWORD: str = os.environ.get("SNOWFLAKE_PASSWORD", "")
    SNOWFLAKE_DATABASE: str = os.environ.get(
        "SNOWFLAKE_DATABASE", "ORGDATACLOUD$INTERNAL$BLUE_YONDER"
    )
    SNOWFLAKE_SCHEMA: str = os.environ.get("SNOWFLAKE_SCHEMA", "BLUE_YONDER")
    SNOWFLAKE_WAREHOUSE: str = os.environ.get(
        "SNOWFLAKE_WAREHOUSE", "LAB_10_COMPUTE_DEFAULT_VWH"
    )
    SNOWFLAKE_ROLE: str = os.environ.get("SNOWFLAKE_ROLE", "LAB10_FULL_ROLE")
    # "externalbrowser" triggers SSO sign-in on first use and caches the token.
    # Use "snowflake" for username/password auth (requires SNOWFLAKE_PASSWORD).
    SNOWFLAKE_AUTHENTICATOR: str = os.environ.get(
        "SNOWFLAKE_AUTHENTICATOR", "externalbrowser"
    )
    # Cache the browser auth token so the bot process does not need to
    # re-open a browser on every request.
    SNOWFLAKE_CLIENT_STORE_TEMP_CREDENTIAL: bool = (
        os.environ.get("SNOWFLAKE_CLIENT_STORE_TEMP_CREDENTIAL", "true").lower()
        not in ("false", "0", "no")
    )
    SNOWFLAKE_TABLE: str = os.environ.get("SNOWFLAKE_TABLE", "BY_DMDUNIT")
    SNOWFLAKE_TAID_COLUMN: str = os.environ.get("SNOWFLAKE_TAID_COLUMN", "DMDUNIT")
    SNOWFLAKE_RS_COLUMN: str = os.environ.get("SNOWFLAKE_RS_COLUMN", "U_RS_PRODUCT_CODE")

    # ── Oracle (over TLS 1.2) ─────────────────────────────────────────────────
    ORACLE_DSN: str = os.environ.get("ORACLE_DSN", "")          # e.g. host:port/service
    ORACLE_USER: str = os.environ.get("ORACLE_USER", "")
    ORACLE_PASSWORD: str = os.environ.get("ORACLE_PASSWORD", "")
    # Path to Oracle Wallet or certificate bundle for TLS 1.2
    ORACLE_WALLET_DIR: str = os.environ.get("ORACLE_WALLET_DIR", "")
    ORACLE_TABLE: str = os.environ.get("ORACLE_TABLE", "TAID_RS_MAPPING")
    ORACLE_TAID_COLUMN: str = os.environ.get("ORACLE_TAID_COLUMN", "TAID")
    ORACLE_RS_COLUMN: str = os.environ.get("ORACLE_RS_COLUMN", "RS_CODE")

    # ── CSV / SQLite fallback ─────────────────────────────────────────────────
    CSV_PATH: str = os.environ.get(
        "CSV_PATH",
        os.path.join(os.path.dirname(__file__), "data", "sample_taid_rs_codes.csv"),
    )
    CSV_TAID_COLUMN: str = os.environ.get("CSV_TAID_COLUMN", "DMDUNIT")
    CSV_RS_COLUMN: str = os.environ.get("CSV_RS_COLUMN", "U_RS_PRODUCT_CODE")
