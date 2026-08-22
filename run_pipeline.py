"""Command-line entry point for modular local pipeline stages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ingestion.hea84k import build_manifest, ingest_hea84k


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest-84k", help="validate or ingest the 84k initial-structure dataset")
    ingest.add_argument("--raw-dir", type=Path, default=Path("data/raw/dataset_84k_hea"))
    ingest.add_argument("--output-dir", type=Path, default=Path("data/processed/hea_84k"))
    ingest.add_argument("--dry-run", action="store_true", help="validate and print a manifest without writing datasets")
    args = parser.parse_args()

    if args.command == "ingest-84k":
        result = build_manifest(args.raw_dir) if args.dry_run else ingest_hea84k(args.raw_dir, args.output_dir)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
