Extract every charge line from the provided January credit-card statement.

Return a JSON object with a single key `rows` whose value is an array. Include one row per charge and exclude payments, credits, fees, totals, and balance lines. Each row must contain:
- date: the charge date exactly as shown, when available
- merchant: the merchant name shown on the statement
- amount_usd: the charge amount in dollars as a positive number
- classification: exactly `business` or `personal`
- expense-category: the business expense label for shop charges, such as cogs_parts, tools_equipment, shipping, or software; use null for personal rows

Do not invent values. Use null for a missing or unreadable field. Classify from the merchant and the business context of Spoke & Wrench Bicycle Repair. Preserve merchant names as shown on the statement.
