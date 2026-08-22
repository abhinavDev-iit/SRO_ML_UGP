"""Leakage-aware ingestion for the 84k FCC/BCC DFT/SRO source.

The default feature view uses descriptors calculated from the initial structure
and removes final DFT outcomes plus explicit chemical-ordering proxies. It does
not train a model or perform feature selection.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from src.cleaning.standardize import normalize_phase, parse_formula_fractions


SOURCE_ID = "hea_84k_dft_2023"
INITIAL_FILENAME = "structure_ini_featurized.dat_all.csv"
SRO_FILENAME = "SROs_structure_ini.csv"

SAFE_METADATA = {
    "fid", "reduced_formula", "chemical_system", "lattice", "nelements",
    "NIONS", "space_group_number_ini", "formula",
}

# These fields are present in the initial-feature file but describe final DFT
# outputs, relaxed geometry/symmetry, or raw objects unsuitable as predictors.
FINAL_OR_UNSAFE_FIELDS = {
    "Ef_per_atom", "e_above_hull", "magmom", "volume_per_atom",
    "e_per_atom", "space_group_number", "structure", "structure_ini",
    "pressure", "max_FORCE", "elements",
}

DIRECT_SRO_PROXIES = {
    "mean ordering parameter shell 1",
    "mean ordering parameter shell 2",
    "mean ordering parameter shell 3",
}

TARGET_COLUMNS = [
    f"{stat}{shell}"
    for shell in range(1, 5)
    for stat in (
        "mean SRO", "max SRO", "min SRO", "std SRO", "range SRO",
        "mean abs SRO", "max abs SRO", "min abs SRO", "std abs SRO", "range abs SRO",
    )
]


def read_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return next(csv.reader(handle))


def select_default_feature_columns(header: Iterable[str]) -> list[str]:
    """Select initial/pre-relaxation predictors and reject target-family proxies."""
    columns = list(header)
    first_descriptor = columns.index("minimum CN_VoronoiNN")
    descriptors = columns[first_descriptor:]
    return [
        column for column in columns
        if (column in SAFE_METADATA or column in descriptors)
        and column not in FINAL_OR_UNSAFE_FIELDS
        and column not in DIRECT_SRO_PROXIES
    ]


def _count_and_keys(path: Path) -> tuple[int, set[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader)
        keys = {row[0] for row in reader}
    return len(keys), keys


def build_manifest(raw_dir: Path) -> dict:
    initial_path = raw_dir / INITIAL_FILENAME
    sro_path = raw_dir / SRO_FILENAME
    initial_header = read_header(initial_path)
    sro_header = read_header(sro_path)
    initial_count, initial_keys = _count_and_keys(initial_path)
    sro_count, sro_keys = _count_and_keys(sro_path)

    phase_counts: dict[str, int] = {}
    with initial_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            phase = normalize_phase(row["lattice"])
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

    selected = select_default_feature_columns(initial_header)
    return {
        "source_id": SOURCE_ID,
        "raw_dir": str(raw_dir),
        "initial_rows": initial_count,
        "sro_rows": sro_count,
        "one_to_one_key_match": initial_keys == sro_keys,
        "phase_counts": phase_counts,
        "primary_target": "mean abs SRO1",
        "target_interpretation": "mean absolute first-shell WC alpha across unique unlike-element pairs",
        "target_columns": sro_header[1:],
        "default_feature_count": len(selected),
        "default_feature_columns": selected,
        "excluded_final_or_unsafe_fields": sorted(FINAL_OR_UNSAFE_FIELDS),
        "excluded_direct_sro_proxies": sorted(DIRECT_SRO_PROXIES),
        "prediction_scenario": "initial_structure_only",
    }


def ingest_hea84k(raw_dir: Path, output_dir: Path, chunksize: int = 5000) -> dict:
    """Write standardized CSV tables in chunks.

    CSV is used for this dependency-light stage. The output directory is under
    ``data/processed`` and ignored by Git. Later stages may convert it to
    Parquet once pyarrow is installed.
    """
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("pandas is required; install requirements.txt") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(raw_dir)
    if not manifest["one_to_one_key_match"]:
        raise ValueError("initial-feature and SRO fid sets do not match exactly")

    sro = pd.read_csv(raw_dir / SRO_FILENAME, index_col=0)
    sro.index.name = "fid"
    selected = manifest["default_feature_columns"]
    feature_output = output_dir / "features_initial_safe.csv"
    ml_output = output_dir / "ml_dataset_initial_safe.csv"
    structures_output = output_dir / "structures.csv"
    for path in (feature_output, ml_output, structures_output):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite existing processed file: {path}")

    first = True
    written = 0
    for chunk in pd.read_csv(raw_dir / INITIAL_FILENAME, usecols=selected, chunksize=chunksize):
        chunk["phase"] = chunk["lattice"].map(normalize_phase)
        chunk["source_id"] = SOURCE_ID
        chunk["composition_fractions_json"] = chunk["formula"].map(
            lambda value: json.dumps(parse_formula_fractions(value), sort_keys=True)
        )
        joined = chunk.set_index("fid").join(sro, how="inner", validate="one_to_one").reset_index()
        if len(joined) != len(chunk):
            raise ValueError("SRO join dropped initial-feature rows")

        structures = joined[[
            "fid", "source_id", "chemical_system", "formula",
            "composition_fractions_json", "phase", "NIONS", "nelements",
            "space_group_number_ini",
        ]].rename(columns={"fid": "source_structure_id", "NIONS": "number_of_atoms"})
        features = joined[["fid"] + [c for c in selected if c != "fid"] + ["phase", "source_id", "composition_fractions_json"]]

        structures.to_csv(structures_output, mode="w" if first else "a", header=first, index=False)
        features.to_csv(feature_output, mode="w" if first else "a", header=first, index=False)
        joined.to_csv(ml_output, mode="w" if first else "a", header=first, index=False)
        written += len(joined)
        first = False

    manifest["rows_written"] = written
    manifest["outputs"] = [str(structures_output), str(feature_output), str(ml_output)]
    (output_dir / "ingestion_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
