"""WebSocket event dispatcher. Routes incoming agent events to brain logic."""

from __future__ import annotations

from typing import Any

from brain.src.logger import get_logger

log = get_logger("ws_events")


async def dispatch_event(
    event: str,
    message: dict,
    device_id: str,
    brain: Any,
    connection_manager: Any,
) -> dict | None:
    """Dispatch a WebSocket event to the appropriate handler."""

    if event == "user_input":
        return await _handle_user_input(message, device_id, brain)
    elif event == "action_result":
        return await _handle_action_result(message, device_id, brain)
    elif event == "context_update":
        return await _handle_context_update(message, device_id, brain)
    elif event == "ping":
        return {"event": "pong"}
    else:
        log.warning("unknown_event", event=event, device=device_id)
        return {"event": "error", "detail": f"Unknown event: {event}"}


async def _handle_user_input(message: dict, device_id: str, brain: Any) -> dict:
    """Process user input: retrieve context, call LLM, return response."""
    text = message.get("text", "")
    if not text:
        return {"event": "error", "detail": "text required"}

    # Full loop: context retrieval -> LLM call -> memory update
    llm_result = await brain.chat(device_id, text)

    response_text = llm_result.get("response", "")
    actions = llm_result.get("actions", [])

    # If LLM returned actions, include them for the agent to execute
    if actions:
        return {
            "event": "response",
            "text": response_text,
            "tts": True,
            "actions": actions,
        }

    return {
        "event": "response",
        "text": response_text,
        "tts": True,
    }


async def _handle_action_result(message: dict, device_id: str, brain: Any) -> dict | None:
    """Handle action execution results from an agent."""
    action_id = message.get("action_id", "")
    status = message.get("status", "unknown")
    details = message.get("details", "")

    from brain.src.cognitive.models import EpisodeOutcome
    outcome = EpisodeOutcome.SUCCESS if status == "success" else EpisodeOutcome.FAILURE

    await brain.episodic.record(
        event_type="action",
        title=f"Action {action_id}: {status}",
        description=details,
        device=device_id,
        outcome=outcome,
    )

    log.info("action_result", action_id=action_id, status=status, device=device_id)
    return None  # No response needed


async def _handle_context_update(message: dict, device_id: str, brain: Any) -> dict | None:
    """Handle context updates from an agent (active app, active file, etc.)."""
    active_app = message.get("active_app", "")
    active_file = message.get("active_file", "")

    if active_app:
        await brain.short_term.add_command(f"switched to {active_app}", device_id)
        # Strengthen association between app and current topic
        ctx = await brain.working.get_device_context(device_id)
        if ctx.current_topic:
            brain.associations.add_association(active_app.lower(), ctx.current_topic)

    log.debug("context_update", device=device_id, app=active_app, file=active_file)
    return None
