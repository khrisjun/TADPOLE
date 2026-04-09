"""
Shared utilities for TADPOLE data connectors.
"""

import re

# Identifiers must be alphanumeric, underscores, or dollar signs (Snowflake
# database names such as "ORGDATACLOUD$INTERNAL$BLUE_YONDER" contain "$").
# A single dot is allowed to separate a schema/database qualifier from a name
# (e.g. "MY_SCHEMA.MY_TABLE").
_SAFE_IDENTIFIER_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_$]*(\.[A-Za-z_][A-Za-z0-9_$]*)*$"
)


def validate_identifier(name: str, label: str = "identifier") -> str:
    """
    Return *name* unchanged if it is a safe SQL identifier, otherwise raise.

    A safe identifier contains only letters, digits, underscores, and dollar
    signs, and may include a single dot to separate a schema/database qualifier
    from a name (e.g. ``MY_SCHEMA.MY_TABLE`` or
    ``ORGDATACLOUD$INTERNAL$BLUE_YONDER``).

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
            "Identifiers must contain only letters, digits, underscores, "
            "and dollar signs."
        )
    return name
