#!/usr/bin/env python3
"""Run Problems 2–8 in order."""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-dir", required=True, type=Path)
    parser.add_argument("--out-dir", default=Path("output"), type=Path)
    args = parser.parse_args()
    root = Path(__file__).parent
    commands = [
        ["read_receipts.py", "--docs-dir", str(args.docs_dir), "--out-dir", str(args.out_dir)],
        ["read_bank.py", "--docs-dir", str(args.docs_dir), "--out-dir", str(args.out_dir)],
        ["read_card.py", "--docs-dir", str(args.docs_dir), "--out-dir", str(args.out_dir)],
        ["reconcile.py", "--docs-dir", str(args.docs_dir), "--json-dir", str(args.out_dir), "--out-dir", str(args.out_dir)],
        ["income_statement.py", "--json-dir", str(args.out_dir), "--out-dir", str(args.out_dir)],
        ["report.py", "--json-dir", str(args.out_dir), "--out", str(args.out_dir / "income_statement.html")],
    ]
    for command in commands:
        print("$", "python3", *command, flush=True)
        subprocess.run([sys.executable, *command], cwd=root, check=True)


if __name__ == "__main__":
    main()
