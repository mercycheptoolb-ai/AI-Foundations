# HW1 Submission

This package processes the Spoke & Wrench January 2026 document pack. The document pack itself is intentionally not included in the submission zip.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a local `.env` file in the project root (or set the variable in your shell):

```dotenv
PORTKEY_API_KEY=your_key_here
```

Never commit or share the real key. The scripts use OpenAI through Portkey with model `gpt-5.6-luna`.

## Run each step

Run from this directory. `DOCS_DIR` should point to the unzipped document pack.

```bash
python3 read_receipts.py --docs-dir "$DOCS_DIR/pdfs" --out-dir output
python3 read_bank.py --docs-dir "$DOCS_DIR/pdfs" --out-dir output
python3 read_card.py --docs-dir "$DOCS_DIR/pdfs" --out-dir output
python3 reconcile.py --docs-dir "$DOCS_DIR/pdfs" --json-dir output --out-dir output
python3 income_statement.py --json-dir output --out-dir output
python3 report.py --json-dir output --out output/income_statement.html
```

To run the complete chain:

```bash
python3 run_all.py --docs-dir "$DOCS_DIR/pdfs" --out-dir output
```

The scripts write extracted transactions, reconciliation decisions, the income statement JSON, and the HTML report to `output/`. `pipeline.html` is a static process-flow diagram.
