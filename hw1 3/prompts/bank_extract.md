Extract every transaction line from the provided January bank statement.

Return a JSON object with a single key `rows` whose value is an array. Include one row per bank transaction line and no summary or balance rows. Each row must contain:
- date: the posting or transaction date exactly as shown, when available
- description: the text shown on the statement
- amount_usd: the dollar amount as a positive number
- classification: exactly `business` or `personal`
- direction: exactly `credit` for money coming in or `debit` for money going out
- accounting_label: the accounting kind, such as revenue, expense, owner_draw, or transfer
- expense_type: the expense subcategory when accounting_label is expense, such as rent, utilities, or cogs_parts; otherwise null

Do not invent values. Use null for a missing or unreadable field. Classify only from evidence in the statement and the business context provided; use personal when the transaction is clearly personal. Preserve the statement's transaction descriptions.
