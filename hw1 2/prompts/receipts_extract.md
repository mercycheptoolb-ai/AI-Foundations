Extract one row for each purchase receipt PDF provided.

Return only a JSON array. Each row must contain exactly these fields:
- vendor: the store or seller name
- date: the transaction date
- description: what was purchased
- amount_usd: the total for this receipt in dollars
- category: the expense label, such as cogs_parts, tools_equipment, or shipping
- source_file: the provided PDF filename
- fields_not_found: an array of field names whose values are missing or unreadable

Do not invent or infer values that are not supported by the receipt. Use null for a missing scalar field and list its name in fields_not_found. Include one row per PDF, even when fields are missing. Ignore non-purchase documents.
