"""
Unified TAID → RS Code lookup interface.

Priority order (first successful result wins):
  1. Snowflake  (if DATA_SOURCE == "snowflake" or DATA_SOURCE is unset and credentials available)
  2. Oracle     (if DATA_SOURCE == "oracle"    or DATA_SOURCE is unset and credentials available)
  3. CSV        (always available as fallback)

Set the DATA_SOURCE environment variable to one of "snowflake", "oracle", or
"csv" to pin a specific backend and skip the auto-detection logic.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_rs_code(taid: str, config) -> Optional[str]:
    """
    Return the RS Code for *taid*, or None if the TAID is not found.

    The lookup order follows the DATA_SOURCE setting in config:
    - "snowflake" → Snowflake only
    - "oracle"    → Oracle only
    - "csv"       → CSV/SQLite only
    - ""          → try Snowflake, then Oracle, then CSV (auto-detect)

    Parameters
    ----------
    taid : str
        The TAID value to convert.
    config : DefaultConfig
        Application configuration (see config.py).

    Returns
    -------
    str | None
        RS Code string, or None when the TAID is not found in any source.
    """
    source = (config.DATA_SOURCE or "").strip().lower()

    if source == "snowflake":
        return _try_snowflake(taid, config)

    if source == "oracle":
        return _try_oracle(taid, config)

    if source == "csv":
        return _try_csv(taid, config)

    # Auto-detect: try each source in priority order.
    for attempt in (_try_snowflake, _try_oracle, _try_csv):
        try:
            result = attempt(taid, config)
            if result is not None:
                return result
        except Exception as exc:  # noqa: BLE001
            logger.warning("Lookup attempt %s failed: %s", attempt.__name__, exc)

    return None


# ── Private helpers ────────────────────────────────────────────────────────────


def _try_snowflake(taid: str, config) -> Optional[str]:
    if not config.SNOWFLAKE_ACCOUNT:
        logger.debug("Snowflake not configured (SNOWFLAKE_ACCOUNT is empty), skipping.")
        return None
    from data.snowflake_connector import get_rs_code as sf_lookup

    return sf_lookup(taid, config)


def _try_oracle(taid: str, config) -> Optional[str]:
    if not config.ORACLE_DSN:
        logger.debug("Oracle not configured (ORACLE_DSN is empty), skipping.")
        return None
    from data.oracle_connector import get_rs_code as ora_lookup

    return ora_lookup(taid, config)


def _try_csv(taid: str, config) -> Optional[str]:
    from data.csv_connector import get_rs_code as csv_lookup

    return csv_lookup(taid, config)
