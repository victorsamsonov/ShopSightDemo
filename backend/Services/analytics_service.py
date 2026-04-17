from __future__ import annotations

from typing import Any
from domain.models import Config
from domain.actions import (
    CATEGORY_REVENUE_THIS_WEEK,
    PRODUCTS_SALES_COUNT_OVERVIEW,
    REVENUE_WITHIN_TIMEFRAME,
    SALES_TREND_BY_DAY_LAST_30,
    PRODUCTS_SALES_REVENUE_OVERVIEW,
)
from domain.models import (
    ChatResponse,
    ChartPayload,
    KpiPayload,
    TablePayload,
)


def run_sqlite_analytics_demo(
    *,
    action_type: str,
    params: dict[str, Any],
    user_message: str,
    config: Config,
) -> ChatResponse:
    """
    Demo-only analytics outputs.

    Once SQLite + CSV import are in place, this function will become a real
    analytics executor. For now, it returns consistent structured payloads
    so the frontend + UX can be built and demoed end-to-end.
    """

    # Real path first: if `processed_data.csv` is available and columns match
    # our assumptions, we import into SQLite and run parameterized queries.
    try:
        from infrastructure.data.csv_importer import DataNotReadyError, ensure_sqlite_imported
        from infrastructure.data.sqlite_repository import query_action, query_revenue_with_timeframe

        ensure_sqlite_imported()
        if action_type == REVENUE_WITHIN_TIMEFRAME:
            resp = query_revenue_with_timeframe(params=params)
        else:
            resp = query_action(action_type=action_type)

        # LLM follow-up step: generate insight + followups grounded in SQL results.
        if action_type in (PRODUCTS_SALES_REVENUE_OVERVIEW, PRODUCTS_SALES_COUNT_OVERVIEW, REVENUE_WITHIN_TIMEFRAME) and resp.table and config.is_llm_configured():
            from infrastructure.llm.insight_generator import generate_insight_json

            table_rows = resp.table.rows
            kpi_dict = resp.kpi.model_dump() if resp.kpi else None

            llm_payload = generate_insight_json(
                config=config,
                user_message=user_message,
                action_type=action_type,
                kpi=kpi_dict,
                table_columns=resp.table.columns,
                table_rows=table_rows,
            )

            resp_data = resp.model_dump()
            resp_data["insight"] = llm_payload.get("insight") or resp_data.get("insight")
            resp_data["followups"] = llm_payload.get("followups") or resp_data.get("followups") or []
            return ChatResponse(**resp_data)

        return resp
    except Exception:
        # Fall back to deterministic demo outputs so the prototype remains
        # usable even before the real CSV lands.
        # Note: keep the error silent to avoid leaking internals to the UI.
        pass

    if action_type == PRODUCTS_SALES_REVENUE_OVERVIEW:
        kpi = KpiPayload(label="Revenue (last month)", value=125430.75, unit="USD")
        chart = ChartPayload(
            title="Top products by revenue (last month)",
            x=["Astra Sneakers", "Nova Hoodie", "Sierra Bottle", "Orbit Tee", "Vanta Cap"],
            series=[48210.5, 32990.0, 21440.25, 16320.75, 12369.25],
            series_label="Revenue",
        )
        table = TablePayload(
            columns=["Metric", "Product", "Transactions", "Total revenue"],
            rows=[
                ["Most sold", "Astra Sneakers", 680, 48210.5],
                ["Least sold", "Vanta Cap", 290, 12369.25],
                ["Most revenue", "Astra Sneakers", 680, 48210.5],
                ["Least revenue", "Vanta Cap", 290, 12369.25],
                ["Top revenue", "Astra Sneakers", 680, 48210.5],
                ["Top revenue", "Nova Hoodie", 520, 32990.0],
                ["Top revenue", "Sierra Bottle", 430, 21440.25],
                ["Top revenue", "Orbit Tee", 610, 16320.75],
                ["Top revenue", "Vanta Cap", 290, 12369.25],
            ],
        )
        return ChatResponse(
            action_type=action_type,
            output_type="table",
            insight="Your best-performing product category is driving most of the revenue. Consider bundling the top 2 items to raise conversion.",
            kpi=kpi,
            chart=chart,
            table=table,
            followups=[
                "What's the trend for these top products over time?",
                "Which customers bought Astra Sneakers the most?",
            ],
        )

    if action_type == PRODUCTS_SALES_COUNT_OVERVIEW:
        return ChatResponse(
            action_type=action_type,
            output_type="table",
            insight="Top products by transaction count are concentrated around a few high-volume items.",
            kpi=KpiPayload(label="Total transactions", value=2530.0, unit=None),
            chart=ChartPayload(
                title="Top products by transaction count",
                x=["Astra Sneakers", "Orbit Tee", "Nova Hoodie", "Sierra Bottle", "Vanta Cap"],
                series=[680, 610, 520, 430, 290],
                series_label="Transactions",
            ),
            table=TablePayload(
                columns=["Metric", "Product", "Transactions"],
                rows=[
                    ["Most sold", "Astra Sneakers", 680],
                    ["Least sold", "Vanta Cap", 290],
                    ["Top transactions", "Astra Sneakers", 680],
                    ["Top transactions", "Orbit Tee", 610],
                    ["Top transactions", "Nova Hoodie", 520],
                    ["Top transactions", "Sierra Bottle", 430],
                    ["Top transactions", "Vanta Cap", 290],
                ],
            ),
            followups=["Show the same products by revenue.", "Which high-transaction products underperform on revenue?"],
        )

    if action_type == REVENUE_WITHIN_TIMEFRAME:
        x = [f"Day {i}" for i in range(1, 8)]
        series = [320, 410, 380, 525, 610, 590, 640]
        return ChatResponse(
            action_type=action_type,
            output_type="line_chart",
            insight="Revenue in the requested timeframe trends upward with a stronger finish in the latest days.",
            kpi=KpiPayload(label="Revenue (timeframe)", value=float(sum(series)), unit="USD"),
            chart=ChartPayload(
                title="Revenue trend (timeframe)",
                x=x,
                series=series,
                series_label="Revenue",
            ),
            table=TablePayload(
                columns=["Date", "Total revenue"],
                rows=[[x[i], series[i]] for i in range(len(x))],
            ),
            followups=["Compare this timeframe with the previous one.", "Which products drove this timeframe revenue?"],
        )

    if action_type == CATEGORY_REVENUE_THIS_WEEK:
        kpi = KpiPayload(label="Revenue (this week)", value=34220.5, unit="USD")
        chart = ChartPayload(
            title="Revenue by category (this week)",
            x=["Shoes", "Apparel", "Accessories", "Beverage"],
            series=[12450.0, 10530.5, 6840.0, 4400.0],
            series_label="Revenue",
        )
        return ChatResponse(
            action_type=action_type,
            output_type="kpi_chart",
            insight="Revenue is concentrated in `Shoes` this week. If inventory is limited, prioritize restocks and targeted promos for that category.",
            kpi=kpi,
            chart=chart,
            table=None,
            followups=["Which category has the fastest growth vs last week?"],
        )

    if action_type == SALES_TREND_BY_DAY_LAST_30:
        x = [f"Day {i}" for i in range(1, 11)]
        series = [1200, 980, 1120, 1400, 1550, 1300, 1680, 1900, 1750, 2100]
        chart = ChartPayload(
            title="Sales trend (last 10 days preview)",
            x=x,
            series=series,
            series_label="Revenue",
        )
        return ChatResponse(
            action_type=action_type,
            output_type="line_chart",
            insight="Sales show a steady upward momentum across the last 10 days. A well-timed discount mid-period could help sustain the late peak.",
            kpi=KpiPayload(label="Latest revenue", value=float(series[-1]), unit="USD"),
            chart=chart,
            table=None,
            followups=["Can you compare this trend to last month?"],
        )

    # Unsupported action_type fallback.
    return ChatResponse(
        action_type=action_type,
        output_type="unknown",
        insight="I can’t map that request to a supported analytics action yet. Try asking for top products, revenue by category, or sales trends.",
        kpi=None,
        chart=None,
        table=None,
        followups=["Try: “Show top products last month”"],
    )

