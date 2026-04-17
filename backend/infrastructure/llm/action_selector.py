from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import re
from typing import Any
from openai import OpenAI

from domain.actions import (
    CATEGORY_REVENUE_THIS_WEEK,
    SALES_TREND_BY_DAY_LAST_30,
    PRODUCTS_SALES_COUNT_OVERVIEW,
    PRODUCTS_SALES_REVENUE_OVERVIEW,
    REVENUE_WITHIN_TIMEFRAME,
)
from domain.models import Config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SelectedAction:
    action_type: str
    output_type: str
    params: dict[str, Any]


def _is_revenue_time_query(msg: str) -> bool:
    return "revenue" in msg and (
        "within" in msg
        or "last month" in msg
        or "last week" in msg
        or "last " in msg
        or "historical" in msg
        or "history" in msg
        or "past" in msg
        or "over time" in msg
        or "trend" in msg
    )

def _is_historical_query(msg: str) -> bool:
    return (
        "historical" in msg
        or "history" in msg
        or "all time" in msg
        or "entire history" in msg
        or "full history" in msg
        or "since beginning" in msg
    )


def select_action_from_message(
    message: str,
    action_catalog: list[dict[str, Any]],
) -> SelectedAction:
    """
    Lightweight agent selection.

    In the full version, an LLM would choose among the allowed `action_type`s
    using the provided `action_catalog` metadata. For now, we keep it robust
    via deterministic keyword matching so the prototype works without data.
    """

    msg = message.lower()

    def find(action_type: str) -> dict[str, Any]:
        for entry in action_catalog:
            if entry.get("action_type") == action_type:
                return entry
        # Fallback: keep output_type stable even if catalog entry changes.
        return {"action_type": action_type, "output_type": "kpi"}

    if "count" in msg or "number of transactions" in msg or "how many transactions" in msg:
        entry = find(PRODUCTS_SALES_COUNT_OVERVIEW)
        return SelectedAction(entry["action_type"], entry["output_type"], params={})

    if "sold" in msg and "revenue" not in msg and "price" not in msg:
        entry = find(PRODUCTS_SALES_COUNT_OVERVIEW)
        return SelectedAction(entry["action_type"], entry["output_type"], params={})

    if ("top" in msg or "best" in msg or "best-selling" in msg or "top-selling" in msg) and "month" in msg:
        entry = find(PRODUCTS_SALES_REVENUE_OVERVIEW)
        return SelectedAction(entry["action_type"], entry["output_type"], params={})

    if _is_revenue_time_query(msg):
        entry = find(REVENUE_WITHIN_TIMEFRAME)
        last_days_match = re.search(r"last\s+(\d+)\s+days?", msg)
        if last_days_match:
            days = int(last_days_match.group(1))
            params = {"timeframe": "last_n_days", "days": days}
        elif _is_historical_query(msg):
            params = {"timeframe": "all_time"}
        elif "last month" in msg:
            params = {"timeframe": "last_month"}
        elif "last week" in msg:
            params = {"timeframe": "last_week"}
        else:
            params = {"timeframe": "last_30_days"}
        return SelectedAction(entry["action_type"], entry["output_type"], params=params)

    if "category" in msg and ("revenue" in msg or "sales" in msg) and "week" in msg:
        entry = find(CATEGORY_REVENUE_THIS_WEEK)
        return SelectedAction(entry["action_type"], entry["output_type"], params={})

    if ("trend" in msg or "over time" in msg) and "day" in msg:
        entry = find(SALES_TREND_BY_DAY_LAST_30)
        return SelectedAction(entry["action_type"], entry["output_type"], params={})

    # Default for “demo reliability”.
    entry = find(PRODUCTS_SALES_REVENUE_OVERVIEW)
    return SelectedAction(entry["action_type"], entry["output_type"], params={})


async def agentic_select_action_from_message(
    message: str,
    action_catalog: list[dict[str, Any]],
    config: Config,
) -> SelectedAction:
    """
    Action classifier using OpenAI Responses API.

    The classifier must only pick an allowed `action_type` from the catalog
    and return JSON: {action_type, output_type, params}.
    """

    # Fallback if OpenAI isn't configured.
    if not config.is_llm_configured():
        selected = select_action_from_message(message=message, action_catalog=action_catalog)
        logger.info("LLM selected action %s (deterministic fallback)", selected.action_type)
        return selected

    action_to_output_type = {a["action_type"]: a.get("output_type") for a in action_catalog if "action_type" in a}

    llm = OpenAI(api_key=config.OPENAI_API_KEY)

    catalog_lines = "\n".join(
        [f"- {a.get('action_type')} (output_type={a.get('output_type')})" for a in action_catalog]
    )
    instructions = (
        "You are ShopSight. Classify the user's analytics question into ONE action_type from the provided catalog.\n"
        "Rules:\n"
        "- Choose exactly one action_type.\n"
        "- output_type must correspond to the chosen action_type in the catalog.\n"
        "- params must be a JSON object (may be empty {}).\n"
        "- For REVENUE_WITHIN_TIMEFRAME, params MUST include timeframe.\n"
        "- Allowed timeframe values: all_time, last_n_days, last_week, last_month.\n"
        "- If timeframe is last_n_days, params MUST include days as a positive integer.\n"
        "- Return ONLY valid JSON.\n"
        "Catalog:\n"
        f"{catalog_lines}\n"
        "Return JSON schema:\n"
        "{\n"
        '  "action_type": string,\n'
        '  "output_type": string,\n'
        '  "params": object\n'
        "}"
    )

    # Responses API: enforce json_object output.
    # The Responses API requires the word "json" to appear in the input when
    # using `text.format={"type": "json_object"}`.
    response = llm.responses.create(
        model=config.OPENAI_MODEL,
        input=f"Return json.\nUser question: {message}",
        instructions=instructions,
        temperature=0,
        text={"format": {"type": "json_object"}},
    )

    raw = (getattr(response, "output_text", "") or "").strip()
    try:
        parsed = json.loads(raw) if raw else {}
        action_type = parsed.get("action_type")
        params = parsed.get("params") if isinstance(parsed.get("params"), dict) else {}
    except Exception:
        action_type = None
        params = {}

    if not action_type or action_type not in action_to_output_type:
        # Last-resort deterministic mapping to keep the demo reliable.
        selected = select_action_from_message(message=message, action_catalog=action_catalog)
        logger.info("LLM selected action %s (fallback after invalid JSON)", selected.action_type)
        return selected

    output_type = action_to_output_type.get(action_type) or "kpi"

    logger.info("LLM selected action %s", action_type)
    return SelectedAction(action_type=action_type, output_type=output_type, params=params)