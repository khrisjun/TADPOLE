"""
CSV / SQLite connector for TAID → RS Code lookups.

This connector loads a CSV file into an in-memory SQLite database on first
use (lazy initialisation) and caches the result, making repeated lookups fast
without any external dependencies beyond the Python standard library and pandas.

Install pandas with:  pip install pandas
"""

import logging
import sqlite3
import threading
from typing import Optional

from data.utils import validate_identifier

logger = logging.getLogger(__name__)

_cache_lock = threading.Lock()
_db_conn: Optional[sqlite3.Connection] = None
_loaded_path: Optional[str] = None


def _load_csv_into_sqlite(csv_path: str, taid_col: str, rs_col: str) -> sqlite3.Connection:
    """Load the CSV at *csv_path* into a fresh in-memory SQLite database."""
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "pandas is required for CSV lookups. "
            "Install it with: pip install pandas"
        ) from exc

    df = pd.read_csv(csv_path, dtype=str)

    if taid_col not in df.columns:
        raise ValueError(
            f"CSV file '{csv_path}' does not contain a column named '{taid_col}'. "
            f"Available columns: {list(df.columns)}"
        )
    if rs_col not in df.columns:
        raise ValueError(
            f"CSV file '{csv_path}' does not contain a column named '{rs_col}'. "
            f"Available columns: {list(df.columns)}"
        )

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    df[[taid_col, rs_col]].to_sql("taid_rs_mapping", conn, index=False, if_exists="replace")
    safe_taid_col = validate_identifier(taid_col, "TAID column")
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_taid ON taid_rs_mapping ({safe_taid_col})")
    conn.commit()
    logger.info("CSV connector: loaded %d rows from '%s'", len(df), csv_path)
    return conn


def _get_connection(config) -> sqlite3.Connection:
    """Return the cached in-memory SQLite connection, loading the CSV if needed."""
    global _db_conn, _loaded_path
    with _cache_lock:
        if _db_conn is None or _loaded_path != config.CSV_PATH:
            _db_conn = _load_csv_into_sqlite(
                config.CSV_PATH, config.CSV_TAID_COLUMN, config.CSV_RS_COLUMN
            )
            _loaded_path = config.CSV_PATH
    return _db_conn


def get_rs_code(taid: str, config) -> Optional[str]:
    """
    Look up the RS Code for a given TAID from the CSV / SQLite fallback.

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
    """
    conn = _get_connection(config)
    cur = conn.cursor()
    taid_col = validate_identifier(config.CSV_TAID_COLUMN, "TAID column")
    rs_col = validate_identifier(config.CSV_RS_COLUMN, "RS_CODE column")
    cur.execute(
        f"SELECT {rs_col} FROM taid_rs_mapping "
        f"WHERE {taid_col} = ? LIMIT 1",
        (taid,),
    )
    row = cur.fetchone()
    if row:
        logger.info("CSV connector: found RS Code for TAID=%s", taid)
        return str(row[0])
    logger.info("CSV connector: no RS Code found for TAID=%s", taid)
    return None


def reload(config) -> None:
    """Force a reload of the CSV data (useful after the file is updated)."""
    global _db_conn, _loaded_path
    with _cache_lock:
        if _db_conn is not None:
            _db_conn.close()
        _db_conn = None
        _loaded_path = None
    _get_connection(config)
