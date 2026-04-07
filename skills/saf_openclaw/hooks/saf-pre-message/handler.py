"""OpenClaw hook handler for message:received.

Runs the SAF pipeline with the incoming message and refreshes the
briefing file.
"""

import os
import sys

_saf_root = os.environ.get("SAF_ROOT", os.getcwd())
if _saf_root not in sys.path:
    sys.path.insert(0, _saf_root)

from skills.saf_openclaw.adapter import OpenClawAdapter


def handler(event):
    """OpenClaw lifecycle hook entry point.

    event is expected to have:
      - event.type == "message"
      - event.action == "received"
      - event.context.content (the user's message text)
    """
    if event.type != "message" or event.action != "received":
        return

    message = _extract_message(event)
    if message is None:
        return

    adapter = OpenClawAdapter()
    context = adapter.on_pre_message(message)
    adapter.write_briefing(context)


def _extract_message(event):
    """Pulls the message text out of event.context, handling both
    attribute-style and dict-style context objects."""
    ctx = event.context
    if hasattr(ctx, "content"):
        return ctx.content
    if isinstance(ctx, dict):
        return ctx.get("content")
    return None
