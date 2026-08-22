"""Command-line entry point for modular local pipeline stages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ingestion.hea84k import build_manifest, ingest_hea84k
from src.analysis.phase4 import run_phase4
from src.analysis.phase6 import run_phase6
from src.ml.phase5 import run_phase5
from src.pipeline.phase3 import build_phase3_database


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest-84k", help="validate or ingest the 84k initial-structure dataset")
    ingest.add_argument("--raw-dir", type=Path, default=Path("data/raw/dataset_84k_hea"))
    ingest.add_argument("--output-dir", type=Path, default=Path("data/processed/hea_84k"))
    ingest.add_argument("--dry-run", action="store_true", help="validate and print a manifest without writing datasets")
    phase3 = sub.add_parser("build-phase3", help="construct the validated Parquet database and feature library")
    phase3.add_argument("--raw-dir", type=Path, default=Path("data/raw/dataset_84k_hea"))
    phase3.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    sub.add_parser("analyze-phase4", help="run EDA, association and preliminary feature-set analysis")
    sub.add_parser("train-phase5", help="run leakage-controlled grouped ML evaluation independently")
    sub.add_parser("interpret-phase6", help="run final robustness, compact refinement and scientific audit")
    args = parser.parse_args()

    if args.command == "ingest-84k":
        result = build_manifest(args.raw_dir) if args.dry_run else ingest_hea84k(args.raw_dir, args.output_dir)
        print(json.dumps(result, indent=2))
    elif args.command == "build-phase3":
        print(json.dumps(build_phase3_database(raw_dir=args.raw_dir, output_dir=args.output_dir), indent=2))
    elif args.command == "analyze-phase4":
        print(json.dumps(run_phase4(), indent=2))
    elif args.command == "train-phase5":
        print(json.dumps(run_phase5(), indent=2))
    elif args.command == "interpret-phase6":
        print(json.dumps(run_phase6(), indent=2))


if __name__ == "__main__":
    main()
