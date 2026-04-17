from __future__ import annotations

import json
import re
from typing import Any, Optional

from openai import OpenAI

from domain.models import Config


def _safe_int(v: Any) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


def _safe_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except Exception:
        return None


def _build_overview_context(
    table_columns: list[str],
    table_rows: list[list[Any]],
) -> dict[str, Any]:
    """
    Convert the overview `table.rows` into a compact JSON context the LLM can use.

    Expected schema:
      columns = ["Metric", "Product", "Transactions", "Total revenue"]
      rows = [ [metric, product, transactions, total_revenue], ...]
    """
    context: dict[str, Any] = {}
    top_revenue: list[dict[str, Any]] = []

    col_map = {str(c).strip().lower(): i for i, c in enumerate(table_columns)}
    metric_idx = col_map.get("metric", 0)
    product_idx = col_map.get("product", 1)
    tx_idx = col_map.get("transactions")
    rev_idx = col_map.get("total revenue")

    for row in table_rows:
        if not row:
            continue

        metric = str(row[metric_idx]) if metric_idx < len(row) else ""
        product = str(row[product_idx]) if product_idx < len(row) else ""
        transactions = _safe_int(row[tx_idx]) if tx_idx is not None and tx_idx < len(row) else None
        total_revenue = _safe_float(row[rev_idx]) if rev_idx is not None and rev_idx < len(row) else None

        # For compact 3-column schemas:
        # ["Metric","Product","Transactions"] or ["Metric","Product","Total revenue"]
        if len(row) >= 3 and (transactions is None and total_revenue is None):
            third_col = str(table_columns[2]).strip().lower() if len(table_columns) > 2 else ""
            if "transaction" in third_col:
                transactions = _safe_int(row[2])
            elif "revenue" in third_col or "price" in third_col or "amount" in third_col:
                total_revenue = _safe_float(row[2])

        if metric == "Most sold":
            context["most_sold"] = {
                "product": product,
                "transactions": transactions,
                "total_revenue": total_revenue,
            }
        elif metric == "Least sold":
            context["least_sold"] = {
                "product": product,
                "transactions": transactions,
                "total_revenue": total_revenue,
            }
        elif metric == "Most revenue":
            context["most_revenue"] = {
                "product": product,
                "transactions": transactions,
                "total_revenue": total_revenue,
            }
        elif metric == "Least revenue":
            context["least_revenue"] = {
                "product": product,
                "transactions": transactions,
                "total_revenue": total_revenue,
            }
        elif metric == "Top revenue":
            top_revenue.append(
                {
                    "product": product,
                    "transactions": transactions,
                    "total_revenue": total_revenue,
                }
            )

    context["top_revenue"] = top_revenue
    return context


def generate_insight_json(
    *,
    config: Config,
    user_message: str,
    action_type: str,
    kpi: Optional[dict[str, Any]],
    table_columns: list[str],
    table_rows: list[list[Any]],
) -> dict[str, Any]:
    """
    Call the OpenAI Responses API to produce structured JSON:
      { "insight": string, "followups": string[] }
    """
    if not config.is_llm_configured():
        return {"insight": "LLM not configured.", "followups": []}

    overview_context = _build_overview_context(
        table_columns=table_columns,
        table_rows=table_rows,
    )

    llm_input = {
        "user_message": user_message,
        "action_type": action_type,
        "kpi": kpi,
        "overview_context": overview_context,
    }

    llm = OpenAI(api_key=config.OPENAI_API_KEY)

    instructions = (
        "You are ShopSight. Create an analytics insight and suggested follow-up questions.\n"
        "Rules:\n"
        "- Use ONLY the provided SQL/aggregation results.\n"
        "- The user asked a natural-language question; tailor wording but keep facts accurate.\n"
        "- Insight must be a concise 2-4 sentence explanation, not a raw data dump.\n"
        "- Include an actionable recommendation based on the strongest signal in the data.\n"
        "- When mentioning money, format monetary values with a leading '$' sign.\n"
        "- Mention most/least sold items if transaction counts are present.\n"
        "- Mention most/least revenue items if revenue fields are present.\n"
        "- Your followups MUST include at least one recommendation question focused on what to prioritize based on revenue.\n"
        "- Return ONLY valid JSON.\n"
        "Return JSON schema:\n"
        '{ "insight": string, "followups": string[] }'
    )

    response = llm.responses.create(
        model=config.OPENAI_MODEL,
        # Keep "json" in input to satisfy Responses API json_object validation.
        input=f"json payload:\n{json.dumps(llm_input)}",
        instructions=instructions,
        temperature=0,
        text={"format": {"type": "json_object"}},
    )

    raw = (getattr(response, "output_text", "") or "").strip()
    parsed: dict[str, Any] = {}
    try:
        parsed = json.loads(raw) if raw else {}
    except Exception:
        parsed = {}

    insight = parsed.get("insight") or "Computed product performance from the dataset."
    followups = parsed.get("followups") if isinstance(parsed.get("followups"), list) else []
    followups = [str(f) for f in followups][:6]

    return {"insight": insight, "followups": followups}


def generate_followup_from_context_json(
    *,
    config: Config,
    followup_question: str,
    followup_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Answer follow-up questions using ONLY the previous query context.

    Returns:
      { "insight": string, "followups": string[] }
    """
    if not config.is_llm_configured():
        # Deterministic fallback that avoids selecting/running any new action.
        base = (
            (followup_context.get("last_response") or {}).get("insight")
            if isinstance(followup_context, dict)
            else None
        )
        return {
            "insight": str(base or "I can answer follow-ups from the last query context only."),
            "followups": [],
        }

    llm = OpenAI(api_key=config.OPENAI_API_KEY)
    llm_input = {
        "followup_question": followup_question,
        "followup_context": followup_context,
    }

    instructions = (
        "You are ShopSight. Answer the follow-up question using ONLY the provided followup_context.\n"
        "Rules:\n"
        "- Do NOT classify actions.\n"
        "- Do NOT assume external data.\n"
        "- Provide a concise analytical explanation, not a raw data dump.\n"
        "- If the answer is not present in context, say that clearly and suggest one constrained next question.\n"
        "- Keep answer concise and factual.\n"
        "- Return ONLY valid JSON.\n"
        "Return JSON schema:\n"
        '{ "insight": string, "followups": string[] }'
    )

    response = llm.responses.create(
        model=config.OPENAI_MODEL,
        input=f"json payload:\n{json.dumps(llm_input)}",
        instructions=instructions,
        temperature=0,
        text={"format": {"type": "json_object"}},
    )

    raw = (getattr(response, "output_text", "") or "").strip()
    parsed: dict[str, Any] = {}
    try:
        parsed = json.loads(raw) if raw else {}
    except Exception:
        parsed = {}

    insight = parsed.get("insight") or "I answered using only the previous query context."
    followups = parsed.get("followups") if isinstance(parsed.get("followups"), list) else []
    followups = [str(f) for f in followups][:6]
    return {"insight": insight, "followups": followups}


def _heuristic_is_followup(question: str) -> bool:
    q = (question or "").strip().lower()
    if not q:
        return False
    # Typical conversational continuations that rely on prior context.
    followup_starts = (
        "and ",
        "what about",
        "how about",
        "based on that",
        "from that",
        "also",
        "then",
        "can you compare",
        "compare that",
    )
    if q.startswith(followup_starts):
        return True
    # Pronoun-heavy references often imply context carryover.
    if re.search(r"\b(it|that|those|these|them|same)\b", q):
        return True
    return False


def detect_followup_intent(
    *,
    config: Config,
    question: str,
    followup_context: dict[str, Any],
) -> bool:
    """
    Decide if a message is a follow-up that should be answered from context
    rather than routed as a brand-new analytics query.
    """
    if not config.is_llm_configured():
        return _heuristic_is_followup(question)

    llm = OpenAI(api_key=config.OPENAI_API_KEY)
    llm_input = {
        "question": question,
        "followup_context": followup_context,
    }
    instructions = (
        "Decide whether the question is a follow-up to the provided context.\n"
        "Rules:\n"
        "- Follow-up means the answer depends on previous context.\n"
        "- New query means it should be routed independently.\n"
        "- Return ONLY JSON.\n"
        "Return JSON schema:\n"
        '{ "is_followup": boolean }'
    )
    try:
        response = llm.responses.create(
            model=config.OPENAI_MODEL,
            input=f"json payload:\n{json.dumps(llm_input)}",
            instructions=instructions,
            temperature=0,
            text={"format": {"type": "json_object"}},
        )
        raw = (getattr(response, "output_text", "") or "").strip()
        parsed = json.loads(raw) if raw else {}
        return bool(parsed.get("is_followup"))
    except Exception:
        return _heuristic_is_followup(question)

