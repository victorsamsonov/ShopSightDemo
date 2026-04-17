from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


class DataNotReadyError(RuntimeError):
    pass


def _shop_root() -> Path:
    # .../Shop/backend/Infrastructure/data -> .../Shop
    return Path(__file__).resolve().parents[3]


def _csv_path() -> Path:
    # Source for the prototype analytics.
    return _shop_root() / "backend" / "infrastructure" / "data" / "transactions_sampled_articles.csv"


def _db_path() -> Path:
    return _shop_root() / "backend" / "shopsight.db"


def _try_parse_date(value: str) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None

    # Common ISO variants.
    s = s.replace("Z", "+00:00")
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%f",
    ):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.date().isoformat()
        except ValueError:
            continue

    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.date().isoformat()
    except ValueError:
        return None


def _find_column(fieldnames: list[str], candidates: list[str]) -> Optional[str]:
    lower_map = {f.lower(): f for f in fieldnames}
    for cand in candidates:
        for f in fieldnames:
            if f.lower() == cand.lower():
                return f
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]

    # Loose contains match
    for cand in candidates:
        for f in fieldnames:
            if cand.lower() in f.lower():
                return f
    return None


def ensure_sqlite_imported() -> None:
    """
    Import `transactions_sampled_articles.csv` into a small SQLite schema
    the analytics queries can use.

    If the CSV is missing or required columns can't be mapped, we raise
    DataNotReadyError so the API can fail gracefully.
    """

    csv_path = _csv_path()
    if not csv_path.exists():
        raise DataNotReadyError(f"Missing CSV: {csv_path}")

    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Load header first.
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise DataNotReadyError("CSV has no header")
        fieldnames = reader.fieldnames

        article_id_col = _find_column(fieldnames, ["article_id"])
        t_dat_col = _find_column(fieldnames, ["t_dat"])
        price_col = _find_column(fieldnames, ["price"])
        prod_name_col = _find_column(fieldnames, ["prod_name"])

        required = [
            ("article_id", article_id_col),
            ("t_dat", t_dat_col),
            ("price", price_col),
            ("prod_name", prod_name_col),
        ]
        missing = [name for name, col in required if not col]
        if missing:
            raise DataNotReadyError(f"Missing/unknown columns in CSV: {', '.join(missing)}")

        conn = sqlite3.connect(db_path)
        try:
            # Recreate the schema on every import to keep the prototype consistent.
            conn.execute("DROP TABLE IF EXISTS transactions;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  article_id INTEGER NOT NULL,
                  t_dat TEXT NOT NULL,
                  price REAL NOT NULL,
                  prod_name TEXT NOT NULL
                );
                """
            )
            conn.commit()

            insert_sql = """
              INSERT INTO transactions(article_id, t_dat, price, prod_name)
              VALUES (?, ?, ?, ?)
            """
            rows_inserted = 0
            for row in reader:
                article_id_raw = row.get(article_id_col, "")
                t_dat = _try_parse_date(row.get(t_dat_col, ""))
                price_raw = row.get(price_col, "")
                prod_name = str(row.get(prod_name_col, "")).strip()

                if not article_id_raw or not t_dat or not price_raw or not prod_name:
                    continue
                try:
                    article_id = int(float(str(article_id_raw).replace(",", "").strip()))
                    price = float(str(price_raw).replace(",", "").strip())
                except ValueError:
                    continue

                conn.execute(
                    insert_sql,
                    (article_id, t_dat, price, prod_name)
                )
                rows_inserted += 1

            conn.commit()

            if rows_inserted == 0:
                raise DataNotReadyError("CSV import produced 0 usable rows")
        except Exception as e:
            raise DataNotReadyError(f"Error importing CSV: {e}")
        finally:
            conn.close()

