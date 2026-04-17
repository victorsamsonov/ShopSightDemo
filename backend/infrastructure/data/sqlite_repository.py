from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Any

from domain.actions import (
    CATEGORY_REVENUE_THIS_WEEK,
    SALES_TREND_BY_DAY_LAST_30,
    PRODUCTS_SALES_COUNT_OVERVIEW,
    PRODUCTS_SALES_REVENUE_OVERVIEW,
    REVENUE_WITHIN_TIMEFRAME,
)
from domain.models import ChatResponse, ChartPayload, KpiPayload, TablePayload

from .csv_importer import DataNotReadyError, _db_path

# Fixed "present" date for timeframe actions.
TIMEFRAME_PRESENT_DATE = date(2020, 9, 12)


def _date_range_for_action(action_type: str) -> tuple[str, str]:
    """
    Keep date behavior for non-overview actions (demo-only).
    For the products overview we use min/max directly from the DB.
    """
    # Demo interpretation:
    # - last month: last 30 days
    # - this week: last 7 days
    # - last 30 days: last 30 days
    now = datetime.now(timezone.utc).date()
    if action_type == CATEGORY_REVENUE_THIS_WEEK:
        start = now - timedelta(days=7)
        end = now
    elif action_type == SALES_TREND_BY_DAY_LAST_30:
        start = now - timedelta(days=30)
        end = now
    else:
        start = now - timedelta(days=30)
        end = now
    return start.isoformat(), end.isoformat()


def _open_conn() -> sqlite3.Connection:
    path = _db_path()
    if not path.exists():
        raise DataNotReadyError(f"Missing SQLite DB: {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def query_action(action_type: str) -> ChatResponse:
    conn = _open_conn()
    try:
        if action_type in (PRODUCTS_SALES_REVENUE_OVERVIEW, PRODUCTS_SALES_COUNT_OVERVIEW):
            # Use the entire dataset range (min/max t_dat) so “overview”
            # matches the “use all data” requirement.
            date_bounds = conn.execute(
                """
                SELECT MIN(t_dat) AS min_d, MAX(t_dat) AS max_d
                FROM transactions
                """
            ).fetchone()

            start_date = date_bounds["min_d"]
            end_date = date_bounds["max_d"]

            if not start_date or not end_date:
                raise DataNotReadyError("No t_dat values found in transactions")

            if action_type == PRODUCTS_SALES_COUNT_OVERVIEW:
                rows_by_count = conn.execute(
                    """
                    SELECT
                      prod_name,
                      COUNT(*) AS transaction_count
                    FROM transactions
                    WHERE t_dat BETWEEN ? AND ?
                    GROUP BY prod_name
                    ORDER BY transaction_count DESC
                    """,
                    (start_date, end_date),
                ).fetchall()

                if not rows_by_count:
                    raise DataNotReadyError("No rows matched for PRODUCTS_SALES_COUNT_OVERVIEW (count query)")

                most_sold_row = rows_by_count[0]
                least_sold_row = min(rows_by_count, key=lambda r: int(r["transaction_count"]))

                top_n = 5
                top_count_rows = rows_by_count[:top_n]
                labels = [r["prod_name"] for r in top_count_rows]
                counts = [int(r["transaction_count"]) for r in top_count_rows]
                total_transactions = sum(int(r["transaction_count"]) for r in rows_by_count)

                return ChatResponse(
                    action_type=action_type,
                    output_type="table",
                    insight=(
                        "Computed product transaction counts from the transactions dataset. "
                        f"Most sold: `{most_sold_row['prod_name']}` ({int(most_sold_row['transaction_count'])} transactions). "
                        f"Least sold: `{least_sold_row['prod_name']}` ({int(least_sold_row['transaction_count'])} transactions)."
                    ),
                    kpi=KpiPayload(
                        label="Total transactions",
                        value=float(total_transactions),
                        unit=None,
                    ),
                    chart=ChartPayload(
                        title="Top products by transaction count",
                        x=labels,
                        series=[float(c) for c in counts],
                        series_label="Transactions",
                    ),
                    table=TablePayload(
                        columns=["Metric", "Product", "Transactions"],
                        rows=[
                            ["Most sold", most_sold_row["prod_name"], int(most_sold_row["transaction_count"])],
                            ["Least sold", least_sold_row["prod_name"], int(least_sold_row["transaction_count"])],
                            *[
                                ["Top transactions", labels[i], counts[i]]
                                for i in range(len(labels))
                            ],
                        ],
                    ),
                    followups=["Which products have high transactions but low revenue?", "Show top products by revenue as well."],
                )

            # Revenue-only overview branch.
            rows_by_revenue = conn.execute(
                """
                SELECT
                  prod_name,
                  SUM(price) AS total_revenue
                FROM transactions
                WHERE t_dat BETWEEN ? AND ?
                GROUP BY prod_name
                ORDER BY total_revenue DESC
                """,
                (start_date, end_date),
            ).fetchall()

            if not rows_by_revenue:
                raise DataNotReadyError("No rows matched for PRODUCTS_SALES_REVENUE_OVERVIEW (revenue query)")

            most_revenue_row = rows_by_revenue[0]
            least_revenue_row = min(rows_by_revenue, key=lambda r: float(r["total_revenue"]))
            top_n = 5
            top_revenue_rows = rows_by_revenue[:top_n]

            labels = [r["prod_name"] for r in top_revenue_rows]
            revenues = [float(r["total_revenue"]) for r in top_revenue_rows]
            total_revenue = sum(float(r["total_revenue"]) for r in rows_by_revenue)

            return ChatResponse(
                action_type=action_type,
                output_type="table",
                insight=(
                    "Computed product revenue from the transactions dataset. "
                    f"Most revenue: `{most_revenue_row['prod_name']}` (${float(most_revenue_row['total_revenue']):.2f}). "
                    f"Least revenue: `{least_revenue_row['prod_name']}` (${float(least_revenue_row['total_revenue']):.2f})."
                ),
                kpi=KpiPayload(
                    label="Total revenue (selected window)",
                    value=float(total_revenue),
                    unit="USD",
                ),
                chart=ChartPayload(
                    title="Top products by total revenue",
                    x=labels,
                    series=revenues,
                    series_label="Total revenue",
                ),
                table=TablePayload(
                    columns=["Metric", "Product", "Total revenue"],
                    rows=[
                        ["Most revenue", most_revenue_row["prod_name"], float(most_revenue_row["total_revenue"])],
                        ["Least revenue", least_revenue_row["prod_name"], float(least_revenue_row["total_revenue"])],
                        *[
                            # IMPORTANT: Include *all* products so the LLM insight generator
                            # has complete revenue context (not just the top 5).
                            ["Top revenue", r["prod_name"], float(r["total_revenue"])]
                            for r in rows_by_revenue
                        ],
                    ],
                ),
                followups=["Which products are rising fastest over time?", "Show transaction count ranking as well."],
            )

        if action_type == CATEGORY_REVENUE_THIS_WEEK:
            # The simplified transactions schema has no `product_category` column.
            raise DataNotReadyError("CATEGORY_REVENUE_THIS_WEEK is not supported for the transactions schema")

        if action_type == SALES_TREND_BY_DAY_LAST_30:
            # We could implement this using `t_dat`, but the user request only
            # requires the two “top products” queries; keep the other actions demo-only.
            raise DataNotReadyError("SALES_TREND_BY_DAY_LAST_30 is not implemented for the transactions schema")
        if action_type == REVENUE_WITHIN_TIMEFRAME:
            raise DataNotReadyError("REVENUE_WITHIN_TIMEFRAME requires params but none were provided")
    except Exception:
        raise
    finally:
        conn.close()

    # Fallback for unknown action_type
    return ChatResponse(
        action_type=action_type,
        output_type="unknown",
        insight="Unsupported analytics action for this prototype.",
        kpi=None,
        chart=None,
        table=None,
        followups=[],
    )


def _latest_data_date(conn: sqlite3.Connection) -> date:
    row = conn.execute("SELECT MAX(t_dat) AS max_d FROM transactions").fetchone()
    if not row or not row["max_d"]:
        raise DataNotReadyError("No t_dat values found in transactions")
    return date.fromisoformat(str(row["max_d"]))


def _resolve_timeframe_range(conn: sqlite3.Connection, timeframe: str, days: int | None = None) -> tuple[str, str]:
    # Product requirement: treat 2020-09-12 as "today" for timeframe queries.
    present = TIMEFRAME_PRESENT_DATE
    tf = str(timeframe or "").strip().lower()
    if days is not None and days > 0:
        start = present - timedelta(days=days)
    elif tf in {"all_time", "historical", "history"}:
        min_row = conn.execute("SELECT MIN(t_dat) AS min_d FROM transactions").fetchone()
        if not min_row or not min_row["min_d"]:
            raise DataNotReadyError("No t_dat values found in transactions")
        start = date.fromisoformat(str(min_row["min_d"]))
    elif tf == "last_week":
        start = present - timedelta(days=7)
    elif tf == "last_month":
        start = present - timedelta(days=30)
    else:
        # Unknown timeframe: prefer full history over a misleading short default.
        min_row = conn.execute("SELECT MIN(t_dat) AS min_d FROM transactions").fetchone()
        if not min_row or not min_row["min_d"]:
            raise DataNotReadyError("No t_dat values found in transactions")
        start = date.fromisoformat(str(min_row["min_d"]))
    return start.isoformat(), present.isoformat()


def query_revenue_with_timeframe(params: dict[str, Any] | None = None) -> ChatResponse:
    params = params or {}
    timeframe = str(params.get("timeframe") or "all_time")
    raw_days = params.get("days")
    days = int(raw_days) if isinstance(raw_days, (int, float, str)) and str(raw_days).strip().isdigit() else None

    conn = _open_conn()
    try:
        start_date, end_date = _resolve_timeframe_range(conn, timeframe, days=days)
        rows = conn.execute(
            """
            SELECT
              prod_name,
              SUM(price) AS total_revenue
            FROM transactions
            WHERE t_dat BETWEEN ? AND ?
            GROUP BY prod_name
            ORDER BY total_revenue DESC
            """,
            (start_date, end_date),
        ).fetchall()

        if not rows:
            raise DataNotReadyError("No rows matched for REVENUE_WITHIN_TIMEFRAME")

        labels = [str(r["prod_name"]) for r in rows]
        series = [float(r["total_revenue"]) for r in rows]
        total_revenue = sum(series)
        top_item = rows[0]

        return ChatResponse(
            action_type=REVENUE_WITHIN_TIMEFRAME,
            output_type="table",
            insight=(
                f"From {start_date} to {end_date} (using 2020-09-12 as present), "
                f"the highest-revenue item is `{top_item['prod_name']}` with ${float(top_item['total_revenue']):.2f}. "
                f"Total revenue in the timeframe is ${total_revenue:.2f}."
            ),
            kpi=KpiPayload(
                label=f"Revenue (last {days} days)" if days else f"Revenue ({timeframe})",
                value=float(total_revenue),
                unit="USD",
            ),
            chart=ChartPayload(
                title=f"Top items by revenue (last {days} days)" if days else f"Top items by revenue ({timeframe})",
                x=labels,
                series=series,
                series_label="Revenue",
            ),
            table=TablePayload(
                columns=["Product", "Total revenue"],
                rows=[[labels[i], series[i]] for i in range(min(len(labels), 10))],
            ),
            followups=["Break down the same timeframe by product.", "Compare this timeframe with the previous one."],
        )
    finally:
        conn.close()

