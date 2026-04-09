"""
Microsoft Teams bot that converts a TAID into an RS Code.

The bot understands two styles of request:
  • "convert TAID-001"
  • "TAID-001"  (bare TAID)

It replies with the corresponding RS Code fetched from the configured data
source (Snowflake, Oracle, or CSV fallback).
"""

import re
import logging
from typing import Optional

from botbuilder.core import ActivityHandler, TurnContext  # type: ignore
from botbuilder.schema import Activity, ActivityTypes  # type: ignore

from data import lookup

logger = logging.getLogger(__name__)

# Matches common TAID patterns, e.g. "TAID-001", "TAID001", "taid-001"
_TAID_PATTERN = re.compile(r"\b(TAID[-_]?\w+)\b", re.IGNORECASE)

_HELP_TEXT = (
    "👋 **TADPOLE – TAID & Data Product Lookup Engine**\n\n"
    "Send me a TAID and I'll return the corresponding RS Code.\n\n"
    "**Examples:**\n"
    "- `TAID-001`\n"
    "- `convert TAID-001`\n"
    "- `what is the RS code for TAID-005?`\n\n"
    "Type `help` to see this message again."
)


class TAIDBot(ActivityHandler):
    """A Bot Framework bot that resolves TAID → RS Code lookups."""

    def __init__(self, config):
        super().__init__()
        self._config = config

    # ── Lifecycle handlers ─────────────────────────────────────────────────────

    async def on_members_added_activity(self, members_added, turn_context: TurnContext):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(_HELP_TEXT)

    # ── Message handler ────────────────────────────────────────────────────────

    async def on_message_activity(self, turn_context: TurnContext):
        text: str = (turn_context.activity.text or "").strip()

        if text.lower() in ("help", "?", "hi", "hello"):
            await turn_context.send_activity(_HELP_TEXT)
            return

        taid = _extract_taid(text)
        if not taid:
            await turn_context.send_activity(
                f"❓ I couldn't find a TAID in your message: **{text}**\n\n"
                "Please include a TAID such as `TAID-001`.\n"
                "Type `help` for usage examples."
            )
            return

        rs_code = await _lookup_rs_code(taid.upper(), self._config)
        if rs_code:
            await turn_context.send_activity(
                f"✅ **{taid.upper()}** → **{rs_code}**"
            )
        else:
            await turn_context.send_activity(
                f"⚠️ No RS Code found for **{taid.upper()}**.\n\n"
                "Please check that the TAID is correct and that the mapping "
                "exists in the data source."
            )


# ── Helpers ────────────────────────────────────────────────────────────────────


def _extract_taid(text: str) -> Optional[str]:
    """Return the first TAID found in *text*, or None."""
    match = _TAID_PATTERN.search(text)
    return match.group(1) if match else None


async def _lookup_rs_code(taid: str, config) -> Optional[str]:
    """Async wrapper around the synchronous lookup layer."""
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lookup.get_rs_code, taid, config)
