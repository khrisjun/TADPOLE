"""
Snowflake connector for TAID → RS Code lookups.

Requires the 'snowflake-connector-python' package.
Install via:  pip install snowflake-connector-python
"""

import logging
from typing import Optional

from data.utils import validate_identifier

logger = logging.getLogger(__name__)


def get_rs_code(taid: str, config) -> Optional[str]:
    """
    Look up the RS Code for a given TAID in Snowflake.

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

    conn = snowflake.connector.connect(
        account=config.SNOWFLAKE_ACCOUNT,
        user=config.SNOWFLAKE_USER,
        password=config.SNOWFLAKE_PASSWORD,
        database=config.SNOWFLAKE_DATABASE,
        schema=config.SNOWFLAKE_SCHEMA,
        warehouse=config.SNOWFLAKE_WAREHOUSE,
    )
    try:
        cur = conn.cursor()
        db = validate_identifier(config.SNOWFLAKE_DATABASE, "database")
        schema = validate_identifier(config.SNOWFLAKE_SCHEMA, "schema")
        table = validate_identifier(config.SNOWFLAKE_TABLE, "table")
        taid_col = validate_identifier(config.SNOWFLAKE_TAID_COLUMN, "TAID column")
        rs_col = validate_identifier(config.SNOWFLAKE_RS_COLUMN, "RS_CODE column")
        query = (
            f"SELECT {rs_col} "
            f"FROM {db}.{schema}.{table} "
            f"WHERE {taid_col} = %s "
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
        conn.close()
