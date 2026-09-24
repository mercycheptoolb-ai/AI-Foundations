#!/usr/bin/env python3
"""Build a human-readable January income-statement HTML report."""

import argparse
import html
import json
from pathlib import Path


def money(value):
    return f"${float(value):,.2f}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    statement = json.loads((args.json_dir / "income_statement_jan2026.json").read_text())
    reconciliation = json.loads((args.json_dir / "reconciliation_log.json").read_text())
    judgments = json.loads((args.json_dir / "judgment_calls.json").read_text())
    excluded = [r for r in reconciliation if r.get("included_in_income_statement") == "no"]
    expense_rows = "".join(
        f"<tr><td>{html.escape(str(row['label']))}</td><td>{html.escape(row['category'])}</td>"
        f"<td>{money(row['amount_usd'])}</td><td>{html.escape(', '.join(row['sources']))}</td></tr>"
        for row in statement["expense_lines"]
    )
    excluded_rows = "".join(
        f"<tr><td>{html.escape(row['id'])}</td><td>{html.escape(row['resolution'])}</td>"
        f"<td>{money(row['amount_seen']) if 'amount_seen' in row else money(row.get('amount_used_in_income_statement', 0))}</td></tr>"
        for row in excluded
    )
    judgment_cards = "".join(
        f"<article class='call'><h3>{html.escape(row['transation_id'])}</h3>"
        f"<p><span class='pill {html.escape(row['confidence'])}'>{html.escape(row['confidence'])}</span> "
        f"<strong>{html.escape(row['included_in_income_statement'])}</strong> · "
        f"{money(row['amount_used_in_income_statement'])} booked</p>"
        f"<ul>{''.join(f'<li>{html.escape(source)}</li>' for source in row['evidence_for'])}</ul></article>"
        for row in judgments
    )
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>January 2026 Income Statement</title>
<style>
:root {{ color-scheme: dark; --pink:#ff4fa3; --soft:#ffb7dc; --ink:#120b16; --panel:#211421; }}
* {{ box-sizing:border-box }} body {{ margin:0; background:var(--ink); color:#fff4fa; font:15px/1.5 system-ui,sans-serif }}
main {{ max-width:1100px; margin:auto; padding:42px 22px 64px }} h1 {{ font-size:clamp(2rem,5vw,4rem); margin:0 0 8px }}
h2 {{ color:var(--soft); margin-top:38px }} .sub {{ color:#d9b8ca }} .metrics {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin:28px 0 }}
.metric,.call,section {{ background:var(--panel); border:1px solid #542b49; border-radius:16px; padding:20px }} .metric strong {{ display:block; color:var(--pink); font-size:1.8rem }}
.metric.net strong {{ color:#82f5bd }} table {{ width:100%; border-collapse:collapse; overflow:hidden; background:var(--panel); border-radius:14px }} th,td {{ text-align:left; padding:12px; border-bottom:1px solid #45263d; vertical-align:top }} th {{ color:var(--soft) }}
.calls {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px }} .call h3 {{ color:var(--pink); margin-top:0; overflow-wrap:anywhere }} .pill {{ border-radius:99px; padding:3px 9px; background:#48253c; color:var(--soft) }} .pill.low {{ background:#78304f; color:#ffd5e9 }}
@media(max-width:760px) {{ .metrics,.calls {{ grid-template-columns:1fr }} table {{ display:block; overflow-x:auto; white-space:nowrap }} }}
</style></head><body><main>
<p class="sub">Spoke &amp; Wrench Bicycle Repair · January 2026</p><h1>Income statement</h1>
<div class="metrics"><div class="metric"><span>Revenue</span><strong>{money(statement['revenue_usd'])}</strong></div><div class="metric"><span>Total expenses</span><strong>{money(statement['total_expenses_usd'])}</strong></div><div class="metric net"><span>Net income</span><strong>{money(statement['net_income_usd'])}</strong></div></div>
<h2>Expense detail</h2><table><thead><tr><th>Line</th><th>Category</th><th>Amount</th><th>Sources</th></tr></thead><tbody>{expense_rows}</tbody></table>
<h2>Excluded from the income statement</h2><p class="sub">These reconciled rows were marked “no,” including both personal items and business items deferred or excluded from January.</p><table><thead><tr><th>Reconciliation ID</th><th>Reason</th><th>Booked</th></tr></thead><tbody>{excluded_rows}</tbody></table>
<h2>Judgment calls</h2><div class="calls">{judgment_cards}</div>
</main></body></html>"""
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
