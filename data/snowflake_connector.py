"""
Snowflake connector for TAID → RS Code lookups.

Requires the 'snowflake-connector-python' package.
Install via:  pip install snowflake-connector-python

Authentication
--------------
The default authenticator is ``externalbrowser``, which opens a browser window
for SSO sign-in on first use and then caches the credential locally (when
``SNOWFLAKE_CLIENT_STORE_TEMP_CREDENTIAL=true``).  Subsequent connections reuse
the cached token without requiring a browser.

For unattended / CI deployments set ``SNOWFLAKE_AUTHENTICATOR`` to
``snowflake`` (or ``snowflake_jwt`` for key-pair) and supply the corresponding
``SNOWFLAKE_PASSWORD`` / key configuration.
"""

import logging
from typing import Optional

from data.utils import validate_identifier

logger = logging.getLogger(__name__)

# Authenticators that use browser-based or token-based flows and therefore do
# not accept a password in the connect() call.
_PASSWORDLESS_AUTHENTICATORS = {"externalbrowser", "oauth", "snowflake_jwt"}


def get_rs_code(taid: str, config) -> Optional[str]:
    """
    Look up the RS Code for a given TAID in Snowflake.

    Queries::

        SELECT "<RS_COL>" FROM "<DB>"."<SCHEMA>"."<TABLE>"
        WHERE "<TAID_COL>" = %s
        LIMIT 1

    All identifier names are validated and double-quoted so that names
    containing special characters (e.g. the ``$`` in the database name
    ``ORGDATACLOUD$INTERNAL$BLUE_YONDER``) are handled safely.

    Parameters
    ----------
    taid : str
        The TAID value to look up.
    config : DefaultConfig
        Application configuration (see config.py).

    Returns
    -------
    str | None
        The RS Code if found, otherwise None.

    Raises
    ------
    ImportError
        If the 'snowflake-connector-python' package is not installed.
    Exception
        On connection or query failures.
    """
    try:
        import snowflake.connector  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "snowflake-connector-python is required for Snowflake lookups. "
            "Install it with: pip install snowflake-connector-python"
        ) from exc

    authenticator = config.SNOWFLAKE_AUTHENTICATOR

    connect_kwargs: dict = {
        "account": config.SNOWFLAKE_ACCOUNT,
        "user": config.SNOWFLAKE_USER,
        "database": config.SNOWFLAKE_DATABASE,
        "schema": config.SNOWFLAKE_SCHEMA,
        "warehouse": config.SNOWFLAKE_WAREHOUSE,
        "authenticator": authenticator,
    }

    if config.SNOWFLAKE_ROLE:
        connect_kwargs["role"] = config.SNOWFLAKE_ROLE

    if authenticator.lower() in _PASSWORDLESS_AUTHENTICATORS:
        # Browser / token-based auth: cache the credential so that the Teams
        # bot process does not need to re-open a browser on every request.
        connect_kwargs["client_store_temporary_credential"] = (
            config.SNOWFLAKE_CLIENT_STORE_TEMP_CREDENTIAL
        )
    else:
        # Password-based auth (e.g. authenticator="snowflake").
        connect_kwargs["password"] = config.SNOWFLAKE_PASSWORD

    conn = snowflake.connector.connect(**connect_kwargs)
    try:
        cur = conn.cursor()
        try:
            # Validate all identifiers before embedding them in SQL.
            db = validate_identifier(config.SNOWFLAKE_DATABASE, "database")
            schema = validate_identifier(config.SNOWFLAKE_SCHEMA, "schema")
            table = validate_identifier(config.SNOWFLAKE_TABLE, "table")
            taid_col = validate_identifier(config.SNOWFLAKE_TAID_COLUMN, "TAID column")
            rs_col = validate_identifier(config.SNOWFLAKE_RS_COLUMN, "RS_CODE column")

            # Double-quote identifiers so that special characters (e.g. "$")
            # in names like ORGDATACLOUD$INTERNAL$BLUE_YONDER are handled
            # correctly by Snowflake.
            query = (
                f'SELECT "{rs_col}" '
                f'FROM "{db}"."{schema}"."{table}" '
                f'WHERE "{taid_col}" = %s '
                "LIMIT 1"
            )
            cur.execute(query, (taid,))
            row = cur.fetchone()
            if row:
                logger.info("Snowflake: found RS Code for TAID=%s", taid)
                return str(row[0])
            logger.info("Snowflake: no RS Code found for TAID=%s", taid)
            return None
        finally:
            cur.close()
    finally:
        conn.close()
