"""
Shared utilities for TADPOLE data connectors.
"""

import re

# Identifiers must be alphanumeric + underscores only (no spaces, dots, quotes,
# etc.).  Schema-qualified names ("SCHEMA.TABLE") are allowed as well.
_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


def validate_identifier(name: str, label: str = "identifier") -> str:
    """
    Return *name* unchanged if it is a safe SQL identifier, otherwise raise.

    A safe identifier contains only letters, digits, and underscores, and may
    include a single dot to separate a schema/database qualifier from a name
    (e.g. ``MY_SCHEMA.MY_TABLE``).

    Parameters
    ----------
    name : str
        The identifier to validate.
    label : str
        A human-readable label used in the error message.

    Returns
    -------
    str
        *name* when it passes validation.

    Raises
    ------
    ValueError
        When *name* does not match the safe identifier pattern.
    """
    if not _SAFE_IDENTIFIER_RE.match(name):
        raise ValueError(
            f"Unsafe SQL {label} '{name}'. "
            "Identifiers must contain only letters, digits, and underscores."
        )
    return name
