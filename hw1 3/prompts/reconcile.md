You are reconciling January 2026 records for Spoke & Wrench Bicycle Repair.

Using the extracted receipts, bank transactions, credit-card transactions, and the supplied document text, create a concise reconciliation log. Each row must represent one reconciled amount or one income-statement decision, not every raw transaction line. Group duplicates across documents when they refer to the same purchase. Include decisions needed to determine whether a bank or card amount belongs in January revenue or expenses.

Return a JSON object with one key, `rows`, containing an array. Every row must contain:
- id: a unique short snake_case slug
- sources: a list of document filenames used for this row
- amounts_seen: an object mapping each source filename to the amount seen in that source
- included_in_income_statement: exactly `yes` or `no`
- amount_used_in_income_statement: the dollar amount booked after reconciliation, or 0 when excluded
- resolution: plain-English explanation of how the documents were matched and how the final amount was chosen

Do not invent matches, amounts, or source documents. Use only evidence supplied. A source filename in amounts_seen must also appear in sources. Preserve amounts as positive numbers. Include important unmatched or ambiguous items when they require an income-statement decision, and explain the uncertainty in resolution.
