#!/usr/bin/env python3
"""Reconcile extracted January records through OpenAI via Portkey."""

import argparse
import base64
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from pypdf import PdfReader

MODEL = "gpt-5.6-luna"
PORTKEY_BASE = "https://api.portkey.ai/v1"


def document_text(docs_dir: Path) -> str:
    chunks = []
    for path in sorted(docs_dir.glob("*.pdf")):
        text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        chunks.append(f"--- {path.name} ---\n{text}")
    for path in sorted(docs_dir.parent.glob("emails/*.txt")):
        chunks.append(f"--- {path.name} ---\n{path.read_text(errors='replace')}")
    return "\n\n".join(chunks)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-dir", required=True, type=Path)
    parser.add_argument("--json-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    load_dotenv(Path(__file__).parents[1] / ".env")
    key = os.environ.get("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set")

    required = ["receipts.json", "bank_transactions.json", "credit_card_transactions.json"]
    extracted = {}
    for name in required:
        extracted[name] = json.loads((args.json_dir / name).read_text())
    prompt = (Path(__file__).parent / "prompts" / "reconcile.md").read_text()
    evidence = prompt + "\n\nEXTRACTED JSON:\n" + json.dumps(extracted, indent=2)
    evidence += "\n\nDOCUMENT TEXT:\n" + document_text(args.docs_dir)
    payload = {
        "model": MODEL,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": evidence}]}],
        "text": {"format": {"type": "json_object"}},
    }
    response = requests.post(
        PORTKEY_BASE + "/responses",
        headers={"Authorization": f"Bearer {key}", "x-portkey-api-key": key},
        json=payload,
        timeout=180,
    )
    if not response.ok:
        raise RuntimeError(f"Portkey request failed ({response.status_code}): {response.text}")
    result = response.json()
    text = result.get("output_text")
    if not text:
        for item in result.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    text = content.get("text")
                    break
    if not text:
        raise RuntimeError("No text returned by OpenAI")
    parsed = json.loads(text)
    rows = parsed["rows"] if isinstance(parsed, dict) else parsed
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "reconciliation_log.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(f"Wrote {len(rows)} reconciliation rows")


if __name__ == "__main__":
    main()
