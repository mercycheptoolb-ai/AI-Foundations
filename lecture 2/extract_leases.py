"""Extract structured lease data from the PDFs with Portkey's OpenAI-compatible API."""
import argparse
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

MODEL = os.getenv("PORTKEY_MODEL", "gpt-5.6-luna")
PORTKEY_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1/chat/completions")

SCHEMA = {
    "property_name": "string",
    "address": "string",
    "city": "string",
    "state": "string",
    "latitude": "number|null",
    "longitude": "number|null",
    "tenant": "string|null",
    "lease_start": "YYYY-MM-DD|null",
    "lease_end": "YYYY-MM-DD|null",
    "annual_base_rent": "number|null",
    "monthly_base_rent": "number|null",
    "annual_escalation_pct": "number|null",
    "security_deposit": "number|null",
    "notes": "string",
}

PROMPT = f"""Extract the lease facts from the supplied text. Return ONLY one valid JSON object, no markdown.
Use null when a value is absent or uncertain. Monetary values must be numbers in USD, without symbols or commas.
Schema: {json.dumps(SCHEMA)}"""


def pdf_text(path: Path) -> str:
    return "\n\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def extract_one(path: Path, api_key: str) -> dict:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": f"Filename: {path.name}\n\nLease text:\n{pdf_text(path)}"},
        ],
        "response_format": {"type": "json_object"},
    }
    response = requests.post(
        PORTKEY_URL,
        headers={"x-portkey-api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=180,
    )
    if not response.ok:
        raise RuntimeError(f"Portkey returned HTTP {response.status_code}: {response.text[:1000]}")
    content = response.json()["choices"][0]["message"]["content"]
    data = json.loads(content)
    data["source_file"] = path.name
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("sample_leases"))
    parser.add_argument("--output", type=Path, default=Path("leases.json"))
    args = parser.parse_args()
    api_key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("PORTKEY_API_KEY is empty. Add it to ../.env, then rerun this command.")
    records = [extract_one(path, api_key) for path in sorted(args.input.glob("*.pdf"))]
    args.output.write_text(json.dumps({"model": MODEL, "leases": records}, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} leases to {args.output}")


if __name__ == "__main__":
    main()
