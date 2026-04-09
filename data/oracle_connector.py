"""
Oracle connector for TAID → RS Code lookups over TLS 1.2.

Requires the 'python-oracledb' package (thin mode – no Oracle Client needed).
Install via:  pip install oracledb

TLS 1.2 is enforced via the wallet/SSL configuration passed through
ORACLE_WALLET_DIR (an Oracle Wallet directory containing cwallet.sso and
tnsnames.ora, or a PEM certificate bundle directory recognised by
python-oracledb thin mode).
"""

import logging
from typing import Optional

from data.utils import validate_identifier

logger = logging.getLogger(__name__)


def get_rs_code(taid: str, config) -> Optional[str]:
    """
    Look up the RS Code for a given TAID in Oracle.

    The connection uses TLS 1.2 when ORACLE_WALLET_DIR is set by configuring
    the thin-mode SSL parameters (ssl_context / wallet_location).

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
        If 'oracledb' is not installed.
    Exception
        On connection or query failures.
    """
    try:
        import oracledb  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "oracledb is required for Oracle lookups. "
            "Install it with: pip install oracledb"
        ) from exc

    connect_params: dict = {
        "user": config.ORACLE_USER,
        "password": config.ORACLE_PASSWORD,
        "dsn": config.ORACLE_DSN,
    }

    if config.ORACLE_WALLET_DIR:
        # Enable TLS 1.2 via Oracle Wallet / SSL certificate bundle.
        # python-oracledb thin mode accepts 'wallet_location' and uses it to
        # locate the certificate bundle, enforcing SSL/TLS on the connection.
        connect_params["wallet_location"] = config.ORACLE_WALLET_DIR
        connect_params["wallet_password"] = None  # SSO wallet (no password)

        # Build a custom ssl.SSLContext locked to TLS 1.2.
        import ssl

        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ssl_ctx.load_verify_locations(capath=config.ORACLE_WALLET_DIR)
        connect_params["ssl_context"] = ssl_ctx

    conn = oracledb.connect(**connect_params)
    try:
        cur = conn.cursor()
        table = validate_identifier(config.ORACLE_TABLE, "table")
        taid_col = validate_identifier(config.ORACLE_TAID_COLUMN, "TAID column")
        rs_col = validate_identifier(config.ORACLE_RS_COLUMN, "RS_CODE column")
        query = (
            f"SELECT {rs_col} "
            f"FROM {table} "
            f"WHERE {taid_col} = :taid "
            "FETCH FIRST 1 ROWS ONLY"
        )
        cur.execute(query, taid=taid)
        row = cur.fetchone()
        if row:
            logger.info("Oracle: found RS Code for TAID=%s", taid)
            return str(row[0])
        logger.info("Oracle: no RS Code found for TAID=%s", taid)
        return None
    finally:
        conn.close()
