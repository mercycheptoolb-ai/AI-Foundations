#!/usr/bin/env python3
"""Extract purchase-receipt rows from PDFs through OpenAI via Portkey."""

import argparse
import base64
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


MODEL = "gpt-5.6-luna"
PORTKEY_BASE = "https://api.portkey.ai/v1"


def headers() -> dict[str, str]:
    key = os.environ.get("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set")
    return {"Authorization": f"Bearer {key}", "x-portkey-api-key": key}


def api_post(path: str, **kwargs):
    response = requests.post(PORTKEY_BASE + path, headers=headers(), timeout=180, **kwargs)
    if not response.ok:
        raise RuntimeError(f"Portkey request failed ({response.status_code}): {response.text}")
    return response.json()


def extract(pdf: Path, prompt: str) -> dict:
    file_data = "data:application/pdf;base64," + base64.b64encode(pdf.read_bytes()).decode("ascii")
    payload = {
        "model": MODEL,
        "input": [{"role": "user", "content": [
            {"type": "input_file", "filename": pdf.name, "file_data": file_data},
            {"type": "input_text", "text": prompt + f"\n\nProcess only this receipt. source_file must be {pdf.name!r}."},
        ]}],
        "text": {"format": {"type": "json_object"}},
    }
    result = api_post("/responses", json=payload)
    text = result.get("output_text")
    if not text:
        for item in result.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    text = content.get("text")
                    break
    if not text:
        raise RuntimeError(f"No text returned for {pdf.name}")
    row = json.loads(text)
    if isinstance(row, dict) and "rows" in row:
        row = row["rows"][0]
    if isinstance(row, list):
        row = row[0]
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    load_dotenv(Path(__file__).parents[1] / ".env")
    prompt = (Path(__file__).parent / "prompts" / "receipts_extract.md").read_text()
    pdfs = sorted(args.docs_dir.glob("*.pdf"))
    rows = [extract(pdf, prompt) for pdf in pdfs if pdf.name.startswith("receipt_")]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "receipts.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
