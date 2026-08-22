"""Phase 3 database construction, feature engineering, QA and figures."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from src.cleaning.standardize import normalize_phase, parse_formula_fractions
from src.features.hea_features import ELEMENTS, engineer_features
from src.ingestion.hea84k import (
    DIRECT_SRO_PROXIES,
    FINAL_OR_UNSAFE_FIELDS,
    INITIAL_FILENAME,
    SOURCE_ID,
    SRO_FILENAME,
    build_manifest,
    select_default_feature_columns,
)
from src.ingestion.mlp_hcp import audit_mlp_hcp


OUTPUT_NAMES = ("structures.parquet", "sro_long.parquet", "features.parquet", "ml_dataset.parquet")


def _save_figure(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")


def _make_figures(
    structures: pd.DataFrame,
    source: pd.DataFrame,
    features: pd.DataFrame,
    provenance: pd.DataFrame,
    figure_dir: Path,
    table_dir: Path,
) -> dict[str, str]:
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("MPLCONFIGDIR", str(Path(".cache/matplotlib").resolve()))
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.size": 9, "axes.titlesize": 11, "axes.labelsize": 9,
        "figure.dpi": 120, "savefig.dpi": 300,
    })
    colors = {"FCC": "#2878B5", "BCC": "#D95319", "HCP": "#5B9E6F"}
    figure_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, str] = {}

    phase_counts = structures["phase"].value_counts().reindex(["FCC", "BCC", "HCP"], fill_value=0).rename_axis("phase").reset_index(name="observations")
    phase_counts.to_csv(table_dir / "phase_counts.csv", index=False)
    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    bars = ax.bar(phase_counts["phase"], phase_counts["observations"], color=[colors[x] for x in phase_counts["phase"]])
    ax.bar_label(bars, labels=[f"{value:,}" for value in phase_counts["observations"]], padding=3)
    ax.set(ylabel="Validated observations", title="Phase coverage of the ML-ready SRO database")
    ax.spines[["top", "right"]].set_visible(False)
    _save_figure(fig, figure_dir / "phase_counts.png"); plt.close(fig)
    outputs["phase_counts"] = str(figure_dir / "phase_counts.png")

    systems = source["chemical_system"].value_counts().rename_axis("chemical_system").reset_index(name="observations")
    systems.to_csv(table_dir / "alloy_system_coverage.csv", index=False)
    shown = systems.head(20).sort_values("observations")
    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    ax.barh(shown["chemical_system"], shown["observations"], color="#4C78A8")
    ax.set(xlabel="Observations", title=f"Leading alloy systems (20 of {len(systems)})")
    ax.spines[["top", "right"]].set_visible(False)
    _save_figure(fig, figure_dir / "alloy_system_coverage.png"); plt.close(fig)
    outputs["alloy_system_coverage"] = str(figure_dir / "alloy_system_coverage.png")

    element_counts = {element: 0 for element in ELEMENTS}
    for formula in source["formula"]:
        for element in parse_formula_fractions(formula):
            element_counts[element] += 1
    elements = pd.DataFrame({"element": list(element_counts), "observations": list(element_counts.values())}).sort_values("observations", ascending=False)
    elements.to_csv(table_dir / "element_coverage.csv", index=False)
    fig, ax = plt.subplots(figsize=(6.4, 3.7))
    bars = ax.bar(elements["element"], elements["observations"], color="#59A14F")
    ax.bar_label(bars, labels=[f"{value/1000:.1f}k" for value in elements["observations"]], fontsize=7, padding=2)
    ax.set(ylabel="Observations containing element", title="Element coverage")
    ax.spines[["top", "right"]].set_visible(False)
    _save_figure(fig, figure_dir / "element_coverage.png"); plt.close(fig)
    outputs["element_coverage"] = str(figure_dir / "element_coverage.png")

    missing = features.drop(columns="fid").isna().mean()
    availability = provenance.set_index("feature").assign(
        availability_fraction=(1.0 - missing.reindex(provenance["feature"]).fillna(1.0).to_numpy())
    ).groupby("origin").agg(features=("availability_fraction", "size"), mean_availability=("availability_fraction", "mean")).reset_index()
    availability.to_csv(table_dir / "feature_availability_by_origin.csv", index=False)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    bars = ax.bar(availability["origin"], 100 * availability["mean_availability"], color="#B279A2")
    ax.bar_label(bars, labels=[f"{value:.1f}%" for value in 100 * availability["mean_availability"]], padding=2)
    ax.set(ylabel="Mean availability (%)", title="Feature availability by scientific origin", ylim=(0, 105))
    ax.tick_params(axis="x", rotation=18)
    ax.spines[["top", "right"]].set_visible(False)
    _save_figure(fig, figure_dir / "feature_availability.png"); plt.close(fig)
    outputs["feature_availability"] = str(figure_dir / "feature_availability.png")

    missing_table = missing.rename("missing_fraction").reset_index()
    missing_table.columns = ["feature", "missing_fraction"]
    missing_table = missing_table.sort_values("missing_fraction", ascending=False)
    missing_table.to_csv(table_dir / "feature_missingness.csv", index=False)
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    if float(missing.max()) == 0.0:
        ax.axis("off")
        ax.text(0.5, 0.62, "No missing feature values", ha="center", va="center", fontsize=22, weight="bold", color="#2E7D32")
        ax.text(0.5, 0.40, f"0 of {len(missing):,} candidate features · {len(features):,} observations", ha="center", va="center", fontsize=12)
        ax.text(0.5, 0.22, "Temperature remains structurally absent and is not an ML feature.", ha="center", va="center", fontsize=9, color="#555555")
    else:
        shown = missing_table.head(25).sort_values("missing_fraction")
        ax.barh(shown["feature"], 100 * shown["missing_fraction"], color="#E15759")
        ax.set(xlabel="Missing values (%)", title="Largest feature-level missingness")
        ax.spines[["top", "right"]].set_visible(False)
    _save_figure(fig, figure_dir / "missing_data_patterns.png"); plt.close(fig)
    outputs["missing_data_patterns"] = str(figure_dir / "missing_data_patterns.png")
    return outputs


def build_phase3_database(
    raw_dir: Path = Path("data/raw/dataset_84k_hea"),
    output_dir: Path = Path("data/processed"),
    mlp_dir: Path = Path("data/raw/mlp_csro/MLP-cSRO-main/training_datasets"),
    figure_dir: Path = Path("figures/phase3"),
    table_dir: Path = Path("thesis_outputs/tables/phase3"),
    report_dir: Path = Path("reports"),
) -> dict[str, object]:
    manifest = build_manifest(raw_dir)
    if manifest["initial_rows"] != 83_797 or not manifest["one_to_one_key_match"]:
        raise ValueError("84k source no longer matches the validated 83,797-row manifest")

    header = pd.read_csv(raw_dir / INITIAL_FILENAME, nrows=0).columns.tolist()
    selected = select_default_feature_columns(header)
    source = pd.read_csv(raw_dir / INITIAL_FILENAME, usecols=selected, low_memory=False)
    source["fid"] = source["fid"].astype(str)
    phases = source["lattice"].map(normalize_phase)
    if set(phases) != {"FCC", "BCC"}:
        raise ValueError("validated initial table must contain only FCC and BCC rows")

    sro = pd.read_csv(raw_dir / SRO_FILENAME, low_memory=False).rename(columns={"Unnamed: 0": "fid"})
    sro["fid"] = sro["fid"].astype(str)
    if set(source["fid"]) != set(sro["fid"]):
        raise ValueError("SRO and feature identifiers do not match")

    structures = pd.DataFrame({
        "fid": source["fid"], "source_id": SOURCE_ID,
        "configuration_id": source["fid"], "phase": phases,
        "formula": source["formula"], "chemical_system": source["chemical_system"],
        "composition_fractions_json": source["formula"].map(lambda x: json.dumps(parse_formula_fractions(x), sort_keys=True)),
        "number_of_elements": pd.to_numeric(source["nelements"]),
        "number_of_atoms": pd.to_numeric(source["NIONS"]),
        "initial_space_group_number": pd.to_numeric(source["space_group_number_ini"], errors="coerce"),
        "temperature_K": pd.Series(pd.NA, index=source.index, dtype="Float64"),
        "sro_validation_status": "validated_source_aggregate",
    })

    renamed_stats = {
        "mean SRO": "mean_sro", "max SRO": "max_sro", "min SRO": "min_sro",
        "std SRO": "std_sro", "range SRO": "range_sro",
        "mean abs SRO": "mean_abs_sro", "max abs SRO": "max_abs_sro",
        "min abs SRO": "min_abs_sro", "std abs SRO": "std_abs_sro", "range abs SRO": "range_abs_sro",
    }
    shell_frames = []
    for shell in range(1, 5):
        frame = pd.DataFrame({"fid": sro["fid"], "shell": shell})
        for raw_stat, standard_stat in renamed_stats.items():
            frame[standard_stat] = pd.to_numeric(sro[f"{raw_stat}{shell}"], errors="raise")
        frame["metric_family"] = "shell_aggregate_warren_cowley"
        frame["pair_resolution"] = "aggregate_over_unique_unlike_pairs"
        shell_frames.append(frame)
    sro_long = pd.concat(shell_frames, ignore_index=True)

    features, provenance, elemental_reference, reconstruction_errors = engineer_features(source)
    if max(reconstruction_errors.values()) > 1e-7:
        raise ValueError(f"supplied Magpie elemental means could not be reconstructed: {reconstruction_errors}")
    forbidden = FINAL_OR_UNSAFE_FIELDS | DIRECT_SRO_PROXIES
    if forbidden.intersection(features.columns):
        raise ValueError(f"leakage fields entered feature table: {sorted(forbidden.intersection(features.columns))}")

    target = sro[["fid", "mean abs SRO1"]].rename(columns={"mean abs SRO1": "target_mean_abs_sro_shell1"})
    ml_dataset = structures.merge(features, on="fid", validate="one_to_one").merge(target, on="fid", validate="one_to_one")
    if ml_dataset["target_mean_abs_sro_shell1"].isna().any():
        raise ValueError("primary target contains missing values")

    output_dir.mkdir(parents=True, exist_ok=True)
    structures.to_parquet(output_dir / "structures.parquet", index=False, compression="zstd")
    sro_long.to_parquet(output_dir / "sro_long.parquet", index=False, compression="zstd")
    features.to_parquet(output_dir / "features.parquet", index=False, compression="zstd")
    ml_dataset.to_parquet(output_dir / "ml_dataset.parquet", index=False, compression="zstd")

    hcp_candidates, hcp_summary = audit_mlp_hcp(
        mlp_dir / "Training_TS-4_Cao.cfg", mlp_dir / "Training_TS-5_Cao.cfg"
    )
    hcp_candidates.to_parquet(output_dir / "hcp_candidates_provisional.parquet", index=False, compression="zstd")

    report_tables = report_dir / "tables"
    report_tables.mkdir(parents=True, exist_ok=True)
    provenance.to_csv(report_tables / "feature_provenance.csv", index=False)
    pd.DataFrame(elemental_reference).rename_axis("element").reset_index().to_csv(report_tables / "reconstructed_elemental_reference.csv", index=False)
    hcp_candidates.drop(columns=[column for column in hcp_candidates if column.startswith("wc_")]).to_csv(
        report_tables / "hcp_candidate_inventory.csv", index=False
    )
    figures = _make_figures(structures, source, features, provenance, figure_dir, table_dir)

    missing = features.drop(columns="fid").isna().mean()
    phase_counts = structures["phase"].value_counts().to_dict()
    metrics: dict[str, object] = {
        "rows": len(structures), "fcc_observations": int(phase_counts.get("FCC", 0)),
        "bcc_observations": int(phase_counts.get("BCC", 0)),
        "validated_hcp_observations": int(hcp_summary["validated_hcp_observations"]),
        "provisional_hcp_configurations": int(hcp_summary["candidate_configurations"]),
        "candidate_features": int(len(features.columns) - 1),
        "features_with_any_missing": int((missing > 0).sum()),
        "overall_feature_missing_fraction": float(features.drop(columns="fid").isna().to_numpy().mean()),
        "major_feature_missingness": {
            name: float(missing[name]) for name in (
                "configurational_entropy_j_mol_k", "atomic_size_mismatch_percent",
                "derived_electronegativity_mean", "pair_electronegativity_mean_abs_diff",
                "derived_vec_mean", "pair_vec_mean_abs_diff", "derived_melting_point_mean",
                "space_group_number_ini",
            )
        },
        "elemental_reference_reconstruction_max_abs_error": reconstruction_errors,
        "hcp_audit": hcp_summary,
        "figures": figures,
        "processed_outputs": {name: str(output_dir / name) for name in OUTPUT_NAMES},
        "ready_for_eda_correlation": True,
        "leakage_fields_excluded": sorted(forbidden),
    }
    (report_dir / "phase3_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
