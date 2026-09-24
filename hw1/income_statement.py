#!/usr/bin/env python3
"""Roll the reconciliation log into a January income statement."""

import argparse
import json
from pathlib import Path


REVENUE_MARKERS = ("revenue", "deposit", "service", "jobs", "walkin", "walkins")
EXPENSE_CATEGORIES = {
    "rent": "rent",
    "electricity": "utilities",
    "comcast": "utilities",
    "park_tool": "tools_equipment",
    "staples": "office_supplies",
    "speedy_courier": "shipping",
    "home_depot": "tools_equipment",
    "printing": "printing",
    "nhbp": "cogs_parts",
    "amazon_web": "software",
    "state_farm": "insurance",
    "bank_fee": "bank_fees",
}


def is_revenue(row: dict) -> bool:
    text = f"{row['id']} {row.get('resolution', '')}".lower()
    return any(marker in text for marker in REVENUE_MARKERS)


def expense_category(row: dict) -> str:
    text = f"{row['id']} {row.get('resolution', '')}".lower()
    for marker, category in EXPENSE_CATEGORIES.items():
        if marker in text:
            return category
    return "other_expense"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    rows = json.loads((args.json_dir / "reconciliation_log.json").read_text())
    included = [row for row in rows if row.get("included_in_income_statement") == "yes"]

    revenue = sum(float(row["amount_used_in_income_statement"]) for row in included if is_revenue(row))
    expense_rows = [row for row in included if not is_revenue(row)]
    expense_lines = [
        {
            "label": row["id"],
            "amount_usd": float(row["amount_used_in_income_statement"]),
            "category": expense_category(row),
            "sources": row["sources"],
        }
        for row in expense_rows
    ]
    total_expenses = sum(line["amount_usd"] for line in expense_lines)
    statement = {
        "period": "2026-01",
        "revenue_usd": round(revenue, 2),
        "expense_lines": expense_lines,
        "total_expenses_usd": round(total_expenses, 2),
        "net_income_usd": round(revenue - total_expenses, 2),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "income_statement_jan2026.json").write_text(json.dumps(statement, indent=2) + "\n")
    print(f"Wrote income statement: revenue={revenue:.2f}, expenses={total_expenses:.2f}, net={revenue - total_expenses:.2f}")


if __name__ == "__main__":
    main()
