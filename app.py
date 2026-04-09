"""
Entry point for the TADPOLE Microsoft Teams bot.

Run with:
    python app.py

The bot listens on http://localhost:3978/api/messages by default.
"""

import sys
import asyncio
import logging

from aiohttp import web  # type: ignore
from aiohttp.web import Request, Response, json_response
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings  # type: ignore
from botbuilder.schema import Activity  # type: ignore

from config import DefaultConfig
from bot import TAIDBot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CONFIG = DefaultConfig()

SETTINGS = BotFrameworkAdapterSettings(CONFIG.APP_ID, CONFIG.APP_PASSWORD)
ADAPTER = BotFrameworkAdapter(SETTINGS)
BOT = TAIDBot(CONFIG)


async def on_error(context, error: Exception):
    """Global error handler – logs the error and sends a user-friendly reply."""
    logger.exception("Unhandled error: %s", error)
    await context.send_activity("⚠️ An internal error occurred. Please try again.")


ADAPTER.on_turn_error = on_error


# ── Route handlers ─────────────────────────────────────────────────────────────


async def messages(req: Request) -> Response:
    """Main bot endpoint – receives all activity POSTs from the Bot Framework."""
    if "application/json" not in req.content_type:
        return Response(status=415, reason="Unsupported Media Type")

    body = await req.json()
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return json_response(data=response.body, status=response.status)
    return Response(status=201)


async def health(_: Request) -> Response:
    """Simple health-check endpoint."""
    return json_response({"status": "ok"})


# ── App bootstrap ──────────────────────────────────────────────────────────────

APP = web.Application()
APP.router.add_post("/api/messages", messages)
APP.router.add_get("/health", health)


def main():
    logger.info("TADPOLE bot starting on port %d", CONFIG.PORT)
    web.run_app(APP, host="0.0.0.0", port=CONFIG.PORT)


if __name__ == "__main__":
    main()
