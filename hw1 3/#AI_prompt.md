# AI Prompt Log

## 2026-09-11

> I'll be working on hw1 folder. Please put my things in there. Please create #AI_prompt.md which will have a log what I type here.

## 2026-09-11

> I will prompt you to separate the different sections in the document. For each problem, make sure to include the problem number and title, all the prompts I typed in, one sentence on what was lacking after the first prompt if I needed a second prompt and evidence I worked problem by problem.

## 2026-09-11

> but before I start, create folders in hw1 and name them prompts/ and outputs/

## 2026-09-11

> Also use OpenAI API via Portkey for all my work today

## 2026-09-11 — Problem 2: Read Receipts

> We are now starting problem 2 which is titled Read Receipts. For this problem, create a script read_receipt.py that calls OpenAI using the prompt in prompts/receipts_extract.md to extract one row per purchase receipt PDF in the documet pack. Save a JSON arraye of those rows to output/receipts.json. In each row, include the following
> vendor - which is the store or seller name
> date - which is the transaction date
> description - which is what was purchased
> amount_usd - which is the total for this receipt in dollars
> category - which is the expense label (e.g. cogs_parts, tools_equipment, shipping)
> source_file - which is the filename of the PDF this row came from
>
> For any missing fields, put them in fields_not_found. Please do not invent values
>
> run the script with this command format: python read_receipts.py --docs-dir PATH --out-dir output

## 2026-09-11 — Problem 3: Read Bank Statement

> I am now moving to problem 3 which is titled Read bank statement. I want to turn the January bank statement into structured rows. Each line will need a business/personal label and an accounting categoty before youc an reconcile it with receipts and credit card charges
>
> So create a script read_bank.py that calls OpenAI using the prompt in prompts/bank_extract.md to extract each line from bank_statement_jan2026.pdf, then save a JSON array of those rows to output/bank_transactions.json
>
> Each bank line must include:
> date - which shows posting or transaction date
> description - which is the text shown on the statement
> amount_usd - which is the dollar amount (this is a positive number)
> classification - this can either be business or personal
> direction - which can either be credit for money that is coming in or debit for money that is going out
> accounting_label - which shows what kind of row it is (e.g. revenue, expense, owner_draw, transfer)
> expense_type - which is a subcategory when the row is a bank expense (e.g. rent, utitilities, cogs_parts. Omit or null otherwise
>
> The script should run with this command format: python read_receipts.py --docs-dir PATH --out-dir output
>
> --docs-dir is the unzipped pack

## 2026-09-11 — Problem 4: Read Credit Card Statement

> We are now moving to problem 4 titled Reach credit card statement. In this problem we will extract the credit card transactions
>
> Create a script read_card.py that calls OpenAI using the prompt in prompts/card_extract.md to extract each charge from credit_catd_jan2026.pdf, then save a JSON array of those rows to output/credit_card_transactions.json. Each credit card charge must include:
> date - which is the charge date
> merchant - which is the name on the statement
> amount_usd - which is the charge amount in dollars
> classification - which can either be business or personal
> expense-category - which is the business label for shop charges. use null for personal rows
>
> Run the script with this command format: python read_card.py --docs-dir PATH --out-dir output

## 2026-09-11 — Problem 5: Reconciliation Log

> We are now moving to problem 5 titled Reconciliation log. We will reconcile the receipts, bank lines and credit card charges extracted.
>
> So create a script called reconcile.py that calls OpenAI using the prompt in prompts/reconcile.md to reconcile amounts that appear in more than one document or need a single income-statement decision. Each row in the log is one reconciled amount, not every raw line from problems 2 to 4. Pass in output/receipts.json, output/bank_transactions.json, output/credit_card_transactions.json, plus text from relevant documents, then save a JSON array of those rows to output/reconciliation_log.json.
>
> Each row must include:
> id - which is a short slug for this reconciled item (e.g. park_tool_card_vs_receipt)
> sources - which is the list of document filenames you use for this row
> amounts_seen - which is the object mapping each source filename to the dollar amount seen in the document (e.g. "receipt_park_tool.pdf": 88.7)
> included_in_income_statement - which can either be yes or no; should this row count toward January revenue or expenses?
> amount_used_in_income_statement - which is the dollar amount to book after reconciliation (use 0 if excluded)
> resolution - which is plain English explaining how you would matched the documents and chose the final amount
>
> Run the script in the following command format: python reconcile.py --docs-dir PATH --json-dir output --out-dir output

## 2026-09-11 — Problem 6: Judgment Calls

> Ok. We are now moving to problem 6 titled Judgement calls.
>
> Create output/judgment_calls.json as JSON array of three objects. Pick three rows from the reconciliation log where it was the hardest to set included_in_income_statement or amount_used_in_income_statement
>
> For each judgement call include transation_id (the reconcialiation id), included_in_income_statement, amount_used_in_income_statement, evidence_for (bullet list with document names), and confidence (high, medium, or low; at least one must be low)

## 2026-09-11 — Problem 7: January Income Statement

> Ok. We are now moving to probme 7 titled January income statement
>
> With the reconciled log, roll the included rows into the January income statement
>
> Then create a script income_statement.py that reads output/reconciliation_log.json, rolls every row with included_in_income_statement set to yes into revenue and expense lines, and saves the January income statement to output/income_statement_jan2026.json. Roll-up math can be plain Python, but the inputs must come from the reconcile step, not hardcoded values
>
> The JSON must include period (2026-01), revenue_usd, expense_lines (each with label), amount_usd, category, sources), total_expenses_usd, and net_income_usd
>
> The script should run with this command format: python income_statement.py --json-dir output --out-dir output

## 2026-09-11 — Problem 8: Income Statement Webpage

> We are now moving to problem 8 titled Income statement webpage.
>
> Here we will make a webpage for the income statement that makes it easier for a human to process.
>
> Create a script report.py that reads my JSON files from output/ and builds a one-page HTML summary. Save the page to output/income_statement.html. Use the same numbers as my JSON.
>
> The page must include:
> January income statement (revenue, expenses, net income)
> Personal and business rows excluded from the income statement
> The three judgement calls from Problem 6
>
> Run the script with the following command format: python report.py --json-dir output --out output/income_statement.html

## 2026-09-11 — Problem 9: Process Flow Diagram

> We are now moving to question 9 titled Process flow diagram
>
> Create a one-page HTML file output/pipeline.html with a block diagram of the pipeline. Look back at problems 2 to 8: One block per script, plus blocks for key inputs (document pack, PDFs, emails) and outputs (each JSON/HTML file). Show arrows from inputs through scripts to outputs. Mark where OpenAI is called.
>
> The diagram must make clear:
> Each script name and what it reads/writes
> Which steps OpenAI took
> The path from document pack to income_statement.html

## 2026-09-11 — Problem 10: Submission Format

> We are now moving to problem 10 titled Submission format
>
> Confirm everything we have done today is in the folder named hw1 and zip this folder as hw1.zip.
>
> In the zip, include:
> All scripts from problems 2 to 8
> prompts/ with my runtime prompts files (the prompts/*.md files my scripts read)
> requirements.txt (OpenAI and my PDF library)
> README.md with install steps, how to set environment variables (e.g. PORTKEY_API_KEY) in a local .env file, my model name, and how to run each script. Do not include my actual API key in the README or the zip.
> AI_prompts.md from problem 1
> A sample output/ from one successful run, including pipeline.html
> Run_all.py to chain the scripts in order.
>
> Do not zip the document pack or my API key
