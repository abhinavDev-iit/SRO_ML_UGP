"""Command-line entry point for modular local pipeline stages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ingestion.hea84k import build_manifest, ingest_hea84k
from src.analysis.phase4 import run_phase4
from src.analysis.phase6 import run_phase6
from src.dft.phase7 import analyze_dft_results, prepare_dft_inputs, run_dft, select_dft_configurations
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
    dft_select = sub.add_parser("dft-select", help="select four fixed-composition low/high-SRO DFT structures")
    dft_select.add_argument("--data", type=Path, default=Path("data/processed/ml_dataset.parquet"))
    dft_select.add_argument("--master", type=Path, default=Path("data/raw/dataset_84k_hea/hea.2023-04-06.csv"))
    dft_select.add_argument("--max-nions", type=int, default=16)
    dft_prepare = sub.add_parser("dft-prepare", help="prepare QE templates or runnable local inputs")
    dft_prepare.add_argument("--config", type=Path, default=Path("dft_inputs/qe_config.json"))
    dft_prepare.add_argument("--pseudo-dir", type=Path)
    dft_run = sub.add_parser("dft-run", help="run four prepared static QE SCF calculations")
    dft_run.add_argument("--config", type=Path, default=Path("dft_inputs/qe_config.json"))
    sub.add_parser("dft-analyze", help="parse completed QE outputs and build compact Phase 7 results")
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
    elif args.command == "dft-select":
        print(json.dumps(select_dft_configurations(data_path=args.data, master_path=args.master, max_nions=args.max_nions), indent=2))
    elif args.command == "dft-prepare":
        print(json.dumps(prepare_dft_inputs(config_path=args.config, pseudo_dir=args.pseudo_dir), indent=2))
    elif args.command == "dft-run":
        print(json.dumps(run_dft(config_path=args.config), indent=2))
    elif args.command == "dft-analyze":
        print(json.dumps(analyze_dft_results(), indent=2))


if __name__ == "__main__":
    main()
