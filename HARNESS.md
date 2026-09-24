# Agent Harness

This harness keeps the sales research agent bounded, evidence-based, and safe to run. It is the operating contract for the agent; a user should not need to read `hw2/sales_agent.py` to understand the limits.

## 1. Allowed Tools

The agent may use only the tools explicitly provided for the current task:

- **Website crawler:** Visit the requested company website and relevant same-domain pages to collect source-backed facts.
- **Web search:** Find possible customer companies when the user requests customer discovery. Search results are leads only and must be verified on each company’s own website.
- **Profile reader:** Read the supplied company profile before customer discovery.
- **File writer:** Write only the requested assignment outputs:
  - `hw2/assets/company_profile.json`
  - `hw2/assets/company-profile.json` when compatibility is required
  - `hw2/output/targets.json`
  - `hw2/output/emails.json`
  - `hw2/output/audit_log.json`
- **Audit logger:** Record each meaningful step with its timestamp, tool name, arguments, result summary, and stop reason.

The agent must not use tools outside this allow-list. In particular, it must not send email, make purchases, submit forms, modify external systems, or access unrelated websites or files.

## 2. Stopping Rules

Every run must have a clear completion condition and a hard step limit.

- **Company-profile run:** Stop when the requested profile fields have been researched, validated, and written, or when the maximum step budget is reached.
- **Customer-discovery run:** Stop after three qualified customer targets have been verified and three outreach drafts have been written, or when the maximum step budget is reached.
- **Maximum step budget:** 12 meaningful agent steps per run.
- **Website crawl limit:** Crawl no more than 6 pages on one company domain per research task.
- **No retries without new evidence:** Do not repeat a failed search or tool call unless the input or approach changes.
- **Stop on missing evidence:** Leave a field empty or record a limitation when the source does not support a claim. Do not continue searching indefinitely to fill a gap.
- **Finalization:** Before stopping, validate the JSON output, write the audit entry with `stop_reason: "completed"` or `stop_reason: "max_steps_reached"`, and return a concise run summary.

## 3. Guardrails

### Accuracy and evidence

- Use official company websites and clearly associated same-domain pages as the primary evidence.
- Do not invent facts, statistics, customers, competitors, prices, revenue, contact details, or business claims.
- Every material profile or target claim must have at least one source URL.
- Treat search results as discovery hints, not proof.
- If information is unavailable, use `null`, an empty list, or a limitation note.

### Communication and external actions

- Draft emails only when requested; never send them.
- Do not submit contact forms, create accounts, post content, or contact a person or company.
- Do not expose `PORTKEY_API_KEY` or any other secret in output, logs, prompts, or errors.
- Refuse unsafe, unlawful, deceptive, or unrelated requests.

### Cost and runaway prevention

- Use the configured OpenAI model through Portkey and load the API key from the environment.
- Do not create parallel or recursive agent runs.
- Keep one bounded crawl and one bounded search pass per task.
- Do not repeatedly call the model to repair an output; validate locally first and stop when the budget is exhausted.
- Do not crawl unrelated domains, download large files, or process unnecessary media.
- If a tool repeatedly fails, record the failure and stop instead of spending more calls.
- Keep output concise and structured so retries and token usage remain predictable.

## 4. Required Audit Record

For every run, `hw2/output/audit_log.json` must record:

- UTC timestamp
- Agent thought or step summary
- Tool name and arguments
- Result summary or failure
- Stop reason

The audit record must never contain API keys, passwords, or other secrets.
