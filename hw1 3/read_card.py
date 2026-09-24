#!/usr/bin/env python3
"""Extract credit-card charges through OpenAI via Portkey."""

import argparse
import base64
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

MODEL = "gpt-5.6-luna"
PORTKEY_BASE = "https://api.portkey.ai/v1"


def extract(pdf: Path, prompt: str) -> list[dict]:
    key = os.environ.get("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set")
    data_uri = "data:application/pdf;base64," + base64.b64encode(pdf.read_bytes()).decode("ascii")
    payload = {
        "model": MODEL,
        "input": [{"role": "user", "content": [
            {"type": "input_file", "filename": pdf.name, "file_data": data_uri},
            {"type": "input_text", "text": prompt + "\nBusiness: Spoke & Wrench Bicycle Repair. Accounting period: January 2026."},
        ]}],
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
    return parsed["rows"] if isinstance(parsed, dict) else parsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    load_dotenv(Path(__file__).parents[1] / ".env")
    pdf = args.docs_dir / "credit_card_jan2026.pdf"
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    prompt = (Path(__file__).parent / "prompts" / "card_extract.md").read_text()
    rows = extract(pdf, prompt)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "credit_card_transactions.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
