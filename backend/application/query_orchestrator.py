from typing import Any
import logging

from domain.action_catalog import load_action_catalog
from infrastructure.llm.action_selector import agentic_select_action_from_message
from infrastructure.llm.insight_generator import (
    detect_followup_intent,
    generate_followup_from_context_json,
)
from Services.analytics_service import run_sqlite_analytics_demo
from domain.models import Config

logger = logging.getLogger(__name__)


async def answer_question(
    message: str,
    config: Config,
    is_followup: bool = False,
    followup_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    action_catalog = load_action_catalog()
    selected = await agentic_select_action_from_message(
        message=message, action_catalog=action_catalog, config=config
    )

    should_followup = False
    if followup_context:
        should_followup = is_followup or detect_followup_intent(
            config=config,
            question=message,
            followup_context=followup_context,
        )

        # If selected action is different from previous action, treat this as a
        # new query and not a follow-up.
        last_response = followup_context.get("last_response") if isinstance(followup_context, dict) else {}
        previous_action = last_response.get("action_type") if isinstance(last_response, dict) else None
        if previous_action and previous_action != selected.action_type:
            should_followup = False
        # Parameterized actions should execute as fresh queries rather than
        # being absorbed into follow-up free-text.
        if selected.params:
            should_followup = False

    if should_followup and followup_context:
        logger.info("Follow-up detected; skipping action selection")
        followup_payload = generate_followup_from_context_json(
            config=config,
            followup_question=message,
            followup_context=followup_context,
        )

        last_response = followup_context.get("last_response") if isinstance(followup_context, dict) else {}
        if not isinstance(last_response, dict):
            last_response = {}

        merged = {
            "action_type": last_response.get("action_type", "FOLLOWUP_CONTEXT_ANSWER"),
            "output_type": "text",
            "insight": followup_payload.get("insight") or "Answered from previous context.",
            # Do not re-send old visuals on every follow-up.
            "kpi": None,
            "chart": None,
            "table": None,
            "followups": followup_payload.get("followups") or [],
        }
        return merged

    logger.info("LLM selected action %s", selected.action_type)

    response = run_sqlite_analytics_demo(
        action_type=selected.action_type,
        params=selected.params,
        user_message=message,
        config=config,
    )
    return response.model_dump()

