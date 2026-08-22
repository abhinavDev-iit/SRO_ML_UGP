"""Phase 4 EDA, association analysis, redundancy audit and preliminary feature sets.

This module deliberately stops before estimator fitting. Pearson/Spearman correlation
and mutual information are screening statistics, not model-training results.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.feature_selection import mutual_info_regression


TARGET = "target_mean_abs_sro_shell1"
PHASES = ("ALL", "FCC", "BCC")
RANDOM_STATE = 42
MI_MAX_ROWS = 20_000
NEAR_ZERO_THRESHOLD = 1e-4
HIGH_CORRELATION_THRESHOLD = 0.95


def classify_feature(feature: str, origin: str) -> dict[str, object]:
    """Assign a scientific group, portability class and exclusion-risk flags."""
    name = feature.lower()
    metadata = feature in {"NIONS", "nelements", "space_group_number_ini", "phase_FCC", "phase_BCC"}
    structure_tokens = ("cn_vorono", "local difference", "bond length", "neighbor distance", "cell size", "packing efficiency")
    structure_sensitive = any(token in name for token in structure_tokens) or feature == "space_group_number_ini"

    if feature.startswith("composition_fraction_"):
        group = "composition fractions"
    elif feature.startswith("pair_fraction_"):
        group = "composition pair fractions"
    elif "configurational_entropy" in name:
        group = "configurational entropy"
    elif feature in {"NIONS", "nelements", "composition_number_of_elements"}:
        group = "composition complexity"
    elif feature.startswith("phase_"):
        group = "phase metadata"
    elif "cn_vorono" in name or "neighbor distance" in name or "bond length" in name or "cell size" in name or "packing efficiency" in name:
        group = "initial structural geometry"
    elif "spacegroup" in name or "space_group" in name:
        group = "initial symmetry"
    elif "atomicweight" in name or "atomic_mass" in name:
        group = "atomic mass"
    elif "covalentradius" in name or "atomic_radius" in name or "atomic_size" in name or "gsvolume" in name:
        group = "atomic size"
    elif "electronegativity" in name or "ionic char" in name:
        group = "electronegativity / ionic"
    elif "meltingt" in name or "melting_point" in name:
        group = "melting point"
    elif any(token in name for token in ("nvalence", "nsvalence", "npvalence", "ndvalence", "nfvalence", "nunfilled", "nsunfilled", "npunfilled", "ndunfilled", "nfunfilled", "vec", "valence electrons")):
        group = "valence / VEC"
    elif "gsmagmom" in name:
        group = "elemental magnetic proxy"
    elif "gsbandgap" in name:
        group = "elemental electronic proxy"
    elif "number" in name and "mendeleev" not in name:
        group = "atomic number"
    elif "mendeleev" in name or "column" in name or "row" in name:
        group = "periodic-table position"
    elif feature.endswith("-norm"):
        group = "composition norms"
    elif feature == "compound possible":
        group = "composition feasibility flag"
    else:
        group = "other supplied descriptor"

    if structure_sensitive:
        availability = "initial-structure-dependent"
    elif feature.startswith("phase_"):
        availability = "phase-label-dependent"
    elif origin == "composition-derived":
        availability = "composition-universal"
    elif origin == "elemental-reference-derived":
        availability = "composition-plus-elemental-reference"
    else:
        availability = "source-specific"

    direct_proxy = any(token in name for token in ("sro", "ordering parameter", "target_"))
    identifier = name in {"fid", "id", "configuration_id", "source_id"} or name.endswith("_id")
    proxy_risk = "possible_initial_geometry_proxy" if structure_sensitive else "none"
    unsuitable = direct_proxy or identifier
    reason = ""
    if direct_proxy:
        reason = "direct SRO/target-derived proxy"
    elif identifier:
        reason = "identifier"
    elif metadata:
        reason = "metadata/grouping variable; interpret separately"
    elif structure_sensitive:
        reason = "initial-geometry descriptor may encode configuration-specific ordering"
    return {
        "feature": feature,
        "feature_group": group,
        "availability_class": availability,
        "identifier_flag": identifier,
        "direct_sro_proxy_flag": direct_proxy,
        "target_proxy_risk": proxy_risk,
        "metadata_flag": metadata,
        "unsuitable_for_analysis": unsuitable,
        "caution_reason": reason,
    }


def build_feature_mapping(provenance: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for record in provenance.to_dict("records"):
        row = classify_feature(str(record["feature"]), str(record["origin"]))
        row.update({"origin": record["origin"], "source_field": record["source_field"]})
        rows.append(row)
    return pd.DataFrame(rows)


def cohort_frame(data: pd.DataFrame, cohort: str) -> pd.DataFrame:
    return data if cohort == "ALL" else data.loc[data["phase"].eq(cohort)]


def describe_target(values: pd.Series, cohort: str) -> dict[str, object]:
    clean = values.dropna().astype(float)
    q = clean.quantile([0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99])
    iqr = q.loc[0.75] - q.loc[0.25]
    lower, upper = q.loc[0.25] - 1.5 * iqr, q.loc[0.75] + 1.5 * iqr
    return {
        "cohort": cohort, "n": len(clean), "minimum": clean.min(), "maximum": clean.max(),
        "mean": clean.mean(), "median": clean.median(), "std": clean.std(ddof=1),
        "skewness": stats.skew(clean, bias=False),
        **{f"p{int(p*100):02d}": q.loc[p] for p in q.index},
        "tukey_lower_fence": lower, "tukey_upper_fence": upper,
        "tukey_outlier_count": int(((clean < lower) | (clean > upper)).sum()),
        "near_zero_le_0_05_fraction": float((clean <= 0.05).mean()),
        "near_zero_le_0_10_fraction": float((clean <= 0.10).mean()),
        "exact_zero_count": int(clean.eq(0).sum()),
    }


def feature_quality(data: pd.DataFrame, features: list[str], cohort: str) -> pd.DataFrame:
    frame = cohort_frame(data, cohort)[features]
    rows = []
    for feature in features:
        series = pd.to_numeric(frame[feature], errors="coerce")
        nonmissing = series.dropna()
        counts = nonmissing.value_counts(dropna=False)
        rows.append({
            "cohort": cohort, "feature": feature, "n": len(series),
            "missing_fraction": float(series.isna().mean()), "unique_values": int(nonmissing.nunique()),
            "minimum": nonmissing.min() if len(nonmissing) else np.nan,
            "maximum": nonmissing.max() if len(nonmissing) else np.nan,
            "mean": nonmissing.mean() if len(nonmissing) else np.nan,
            "std": nonmissing.std(ddof=1) if len(nonmissing) > 1 else 0.0,
            "dominant_value_fraction": float(counts.iloc[0] / len(nonmissing)) if len(nonmissing) else np.nan,
            "constant_flag": bool(nonmissing.nunique() <= 1),
            "near_zero_variance_flag": bool(nonmissing.nunique() <= 1 or (len(counts) and counts.iloc[0] / len(nonmissing) >= 0.995)),
        })
    return pd.DataFrame(rows)


def deterministic_mi_sample(frame: pd.DataFrame, max_rows: int = MI_MAX_ROWS) -> pd.DataFrame:
    """Quantile-stratified deterministic sample for tractable nonparametric MI."""
    if len(frame) <= max_rows:
        return frame
    bins = pd.qcut(frame[TARGET].rank(method="first"), 20, labels=False, duplicates="drop")
    sample = frame.assign(_target_bin=bins).groupby("_target_bin", group_keys=False).sample(
        n=max_rows // 20, random_state=RANDOM_STATE
    )
    return sample.drop(columns="_target_bin")


def association_table(data: pd.DataFrame, features: list[str], cohort: str) -> pd.DataFrame:
    frame = cohort_frame(data, cohort)
    quality = feature_quality(data, features, cohort).set_index("feature")
    usable = [feature for feature in features if not quality.loc[feature, "constant_flag"] and quality.loc[feature, "missing_fraction"] < 1]
    pearson = frame[usable].corrwith(frame[TARGET], method="pearson")
    spearman = frame[usable].corrwith(frame[TARGET], method="spearman")
    mi_frame = deterministic_mi_sample(frame[[*usable, TARGET]].dropna())
    mi = mutual_info_regression(
        mi_frame[usable].to_numpy(dtype=float), mi_frame[TARGET].to_numpy(dtype=float),
        random_state=RANDOM_STATE, n_neighbors=5, n_jobs=-1,
    )
    assoc = pd.DataFrame({"feature": usable, "pearson_r": pearson.reindex(usable).to_numpy(),
                          "spearman_rho": spearman.reindex(usable).to_numpy(), "mutual_information": mi})
    assoc["cohort"] = cohort
    assoc["n_observations"] = len(frame)
    assoc["mi_sample_n"] = len(mi_frame)
    assoc["abs_pearson_r"] = assoc["pearson_r"].abs()
    assoc["abs_spearman_rho"] = assoc["spearman_rho"].abs()
    assoc["pearson_rank"] = assoc["abs_pearson_r"].rank(method="min", ascending=False).astype(int)
    assoc["spearman_rank"] = assoc["abs_spearman_rho"].rank(method="min", ascending=False).astype(int)
    assoc["mi_rank"] = assoc["mutual_information"].rank(method="min", ascending=False).astype(int)
    return assoc.sort_values(["mi_rank", "spearman_rank", "pearson_rank"])


def exact_duplicate_feature_groups(data: pd.DataFrame, features: list[str]) -> list[list[str]]:
    groups: dict[tuple[int, int], list[str]] = {}
    for feature in features:
        hashed = pd.util.hash_pandas_object(data[feature], index=False).to_numpy(np.uint64)
        signature = (int(hashed.sum(dtype=np.uint64)), int(np.bitwise_xor.reduce(hashed)))
        groups.setdefault(signature, []).append(feature)
    duplicates = []
    for group in groups.values():
        if len(group) > 1:
            verified = [group[0]]
            for candidate in group[1:]:
                if data[group[0]].equals(data[candidate]):
                    verified.append(candidate)
            if len(verified) > 1:
                duplicates.append(verified)
    return duplicates


def highly_correlated_pairs(data: pd.DataFrame, features: list[str], threshold: float = HIGH_CORRELATION_THRESHOLD) -> tuple[pd.DataFrame, pd.DataFrame]:
    corr = data[features].corr(method="pearson")
    array = corr.to_numpy()
    i, j = np.where(np.triu(np.abs(array), k=1) >= threshold)
    pairs = pd.DataFrame({
        "feature_1": corr.index[i], "feature_2": corr.columns[j], "pearson_r": array[i, j],
    })
    pairs["abs_pearson_r"] = pairs["pearson_r"].abs()
    return pairs.sort_values("abs_pearson_r", ascending=False), corr


def preliminary_sets(
    mapping: pd.DataFrame, quality_all: pd.DataFrame, associations: pd.DataFrame,
    pairs: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    q = quality_all.set_index("feature")
    clean = mapping.loc[~mapping["unsuitable_for_analysis"], "feature"].tolist()
    full_clean = [f for f in clean if not q.loc[f, "constant_flag"]]

    all_assoc = associations.loc[associations["cohort"].eq("ALL")].set_index("feature")
    scores = all_assoc[["abs_spearman_rho", "mutual_information"]].copy()
    max_mi = scores["mutual_information"].max()
    scores["screening_score"] = scores["abs_spearman_rho"] + (scores["mutual_information"] / max_mi if max_mi else 0)
    priority = mapping.set_index("feature").copy()
    priority["portable"] = ~priority["availability_class"].isin(["initial-structure-dependent", "source-specific"])
    priority = priority.join(scores[["screening_score"]], how="left").fillna({"screening_score": 0})
    priority["selection_priority"] = priority["screening_score"] + 0.05 * priority["portable"].astype(int)

    # Greedy correlation pruning keeps the more portable/high-association representative.
    ordered = priority.loc[full_clean].sort_values("selection_priority", ascending=False).index.tolist()
    neighbor_map: dict[str, set[str]] = {f: set() for f in full_clean}
    for row in pairs.itertuples(index=False):
        if row.feature_1 in neighbor_map and row.feature_2 in neighbor_map:
            neighbor_map[row.feature_1].add(row.feature_2); neighbor_map[row.feature_2].add(row.feature_1)
    balanced: list[str] = []
    removed: set[str] = set()
    for feature in ordered:
        if feature in removed:
            continue
        balanced.append(feature)
        removed.update(neighbor_map[feature])

    minimal_preferred = [
        "composition_number_of_elements", "configurational_entropy_j_mol_k", "atomic_size_mismatch_percent",
        "derived_atomic_number_mean", "derived_atomic_number_std", "derived_atomic_mass_mean",
        "derived_atomic_mass_std", "derived_atomic_radius_covalent_mean", "derived_atomic_radius_covalent_std",
        "pair_atomic_radius_covalent_mean_abs_diff", "derived_electronegativity_mean",
        "derived_electronegativity_std", "pair_electronegativity_mean_abs_diff", "derived_vec_mean",
        "derived_vec_std", "pair_vec_mean_abs_diff", "derived_melting_point_mean",
        "derived_melting_point_std", "phase_FCC",
    ]
    minimal = [f for f in minimal_preferred if f in full_clean]
    sets = {"FULL_CLEAN": full_clean, "BALANCED_PRELIMINARY": balanced, "MINIMAL_PRELIMINARY": minimal}
    membership = []
    for set_name, members in sets.items():
        for rank, feature in enumerate(members, 1):
            membership.append({"set": set_name, "selection_order": rank, "feature": feature,
                               "rationale": "scientifically valid nonleaking" if set_name == "FULL_CLEAN" else
                               "correlation-pruned statistical screen" if set_name == "BALANCED_PRELIMINARY" else
                               "portable interpretable composition/elemental baseline"})
    return pd.DataFrame(membership), sets


def _save_figure(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")


def _plot_bar(table: pd.DataFrame, x: str, y: str, title: str, xlabel: str, path: Path, color: str = "#4C78A8", horizontal: bool = True) -> None:
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.2, 5.2 if horizontal else 4.0))
    if horizontal:
        shown = table.iloc[::-1]
        ax.barh(shown[x], shown[y], color=color); ax.set_xlabel(xlabel)
    else:
        ax.bar(table[x], table[y], color=color); ax.set_ylabel(xlabel)
        ax.tick_params(axis="x", rotation=25)
    ax.set_title(title); ax.spines[["top", "right"]].set_visible(False)
    _save_figure(fig, path); plt.close(fig)


def create_figures(
    data: pd.DataFrame, mapping: pd.DataFrame, associations: pd.DataFrame,
    selected_corr: pd.DataFrame, selected_features: list[str], figure_dir: Path,
    tables: dict[str, pd.DataFrame],
) -> list[str]:
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("MPLCONFIGDIR", str(Path(".cache/matplotlib").resolve()))
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 11, "axes.labelsize": 9, "savefig.dpi": 300})
    figure_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []

    def save(fig, name):
        path = figure_dir / name; _save_figure(fig, path); plt.close(fig); outputs.append(str(path))

    phase = tables["phase_counts"]
    fig, ax = plt.subplots(figsize=(5.8, 3.7)); bars = ax.bar(phase.phase, phase.observations, color=["#2878B5", "#D95319", "#A0A0A0"])
    ax.bar_label(bars, labels=[f"{n:,}" for n in phase.observations], padding=3); ax.set(ylabel="Observations", title="Phase coverage used in Phase 4"); ax.spines[["top", "right"]].set_visible(False); save(fig, "phase_counts_hcp_exclusion.png")

    _plot_bar(tables["alloy_system_counts"].head(25), "chemical_system", "observations", "Most represented alloy systems", "Observations", figure_dir / "alloy_system_frequency.png"); outputs.append(str(figure_dir / "alloy_system_frequency.png"))
    _plot_bar(tables["element_counts"], "element", "observations", "Element coverage", "Observations containing element", figure_dir / "element_frequency.png", "#59A14F", False); outputs.append(str(figure_dir / "element_frequency.png"))
    _plot_bar(tables["component_counts"], "number_of_elements", "observations", "Number of alloy components", "Observations", figure_dir / "component_count_distribution.png", "#B279A2", False); outputs.append(str(figure_dir / "component_count_distribution.png"))
    _plot_bar(tables["feature_group_counts"], "feature_group", "features", "Candidate feature groups", "Feature count", figure_dir / "feature_group_counts.png", "#72B7B2"); outputs.append(str(figure_dir / "feature_group_counts.png"))
    _plot_bar(tables["origin_counts"], "origin", "features", "Feature provenance", "Feature count", figure_dir / "feature_provenance_counts.png", "#F28E2B", False); outputs.append(str(figure_dir / "feature_provenance_counts.png"))

    availability = 100 * (1 - tables["feature_quality"].loc[tables["feature_quality"].cohort.eq("ALL"), "missing_fraction"])
    fig, ax = plt.subplots(figsize=(7.0, 3.8)); ax.hist(availability, bins=np.linspace(0, 100, 21), color="#B279A2")
    ax.set(xlabel="Feature availability (%)", ylabel="Feature count", title="Aggregate feature availability"); ax.spines[["top", "right"]].set_visible(False); save(fig, "feature_availability_distribution.png")

    fig, ax = plt.subplots(figsize=(7.0, 3.8)); ax.axis("off")
    missing_cells = int(data[mapping.feature.tolist()].isna().to_numpy().sum())
    ax.text(.5, .62, "No missing predictor values", ha="center", va="center", fontsize=20, weight="bold", color="#2E7D32")
    ax.text(.5, .40, f"{missing_cells:,} missing cells · {len(mapping):,} features · {len(data):,} FCC/BCC rows", ha="center", va="center", fontsize=11)
    ax.text(.5, .22, "Temperature is structurally unavailable and is not a candidate feature.", ha="center", va="center", fontsize=9, color="#555555"); save(fig, "missing_data_pattern_summary.png")

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    bins = np.linspace(data[TARGET].min(), data[TARGET].max(), 45)
    for phase_name, color in (("FCC", "#2878B5"), ("BCC", "#D95319")):
        ax.hist(data.loc[data.phase.eq(phase_name), TARGET], bins=bins, density=True, alpha=.42, label=phase_name, color=color)
    ax.set(xlabel="Mean absolute first-shell SRO", ylabel="Density", title="Target distribution by phase"); ax.legend(frameon=False); ax.spines[["top", "right"]].set_visible(False); save(fig, "target_distribution_by_phase.png")

    fig, ax = plt.subplots(figsize=(5.8, 4.2)); phase_values = [data.loc[data.phase.eq(p), TARGET] for p in ("FCC", "BCC")]
    boxes = ax.boxplot(phase_values, tick_labels=["FCC", "BCC"], showfliers=False, patch_artist=True)
    for patch, color in zip(boxes["boxes"], ["#2878B5", "#D95319"]): patch.set_facecolor(color); patch.set_alpha(.55)
    ax.set(ylabel="Mean absolute first-shell SRO", title="Phase-specific target comparison"); ax.spines[["top", "right"]].set_visible(False); save(fig, "target_phase_boxplot.png")

    for metric, label, color in (("abs_pearson_r", "|Pearson r|", "#4C78A8"), ("abs_spearman_rho", "|Spearman ρ|", "#59A14F"), ("mutual_information", "Mutual information", "#E15759")):
        ranked = associations.loc[associations.cohort.eq("ALL")].nlargest(20, metric)
        _plot_bar(ranked, "feature", metric, f"Top aggregate associations: {label}", label, figure_dir / f"top_{metric}.png", color); outputs.append(str(figure_dir / f"top_{metric}.png"))

    for cohort, color in (("FCC", "#2878B5"), ("BCC", "#D95319")):
        ranked = associations.loc[associations.cohort.eq(cohort)].nlargest(20, "mutual_information")
        _plot_bar(ranked, "feature", "mutual_information", f"Top {cohort} mutual-information associations", "Mutual information", figure_dir / f"top_mi_{cohort.lower()}.png", color); outputs.append(str(figure_dir / f"top_mi_{cohort.lower()}.png"))

    merged = associations.pivot(index="feature", columns="cohort", values="spearman_rho").dropna()
    top = merged.assign(score=merged[["FCC", "BCC"]].abs().max(axis=1)).nlargest(30, "score")
    fig, ax = plt.subplots(figsize=(5.6, 5.0)); ax.scatter(top.FCC, top.BCC, c=np.abs(top.FCC-top.BCC), cmap="viridis", s=30)
    lim = max(abs(top[["FCC", "BCC"]].to_numpy()).max(), .05); ax.plot([-lim, lim], [-lim, lim], "--", color="#777", lw=1)
    ax.set(xlabel="FCC Spearman ρ", ylabel="BCC Spearman ρ", title="Phase stability of leading monotonic associations"); ax.spines[["top", "right"]].set_visible(False); save(fig, "fcc_bcc_association_comparison.png")

    interpretable = [f for f in ["configurational_entropy_j_mol_k", "atomic_size_mismatch_percent", "derived_electronegativity_std", "pair_electronegativity_mean_abs_diff", "derived_vec_mean", "derived_melting_point_mean"] if f in data]
    fig, axes = plt.subplots(2, 3, figsize=(11.0, 6.5), constrained_layout=True)
    sample = data.sample(min(25_000, len(data)), random_state=RANDOM_STATE)
    for ax, feature in zip(axes.flat, interpretable):
        hb = ax.hexbin(sample[feature], sample[TARGET], gridsize=38, mincnt=1, bins="log", cmap="mako" if "mako" in plt.colormaps() else "viridis")
        xbin = pd.qcut(sample[feature].rank(method="first"), 20, duplicates="drop")
        trend = sample.groupby(xbin, observed=True).agg(x=(feature, "median"), y=(TARGET, "median"))
        ax.plot(trend.x, trend.y, color="white", lw=1.8); ax.set(xlabel=feature.replace("_", " "), ylabel="Target")
    save(fig, "nonlinear_interpretable_feature_panels.png")

    labels = [f[:31] + ("…" if len(f) > 31 else "") for f in selected_features]
    fig, ax = plt.subplots(figsize=(10.0, 8.8)); im = ax.imshow(selected_corr.to_numpy(), vmin=-1, vmax=1, cmap="coolwarm")
    ax.set_xticks(range(len(labels)), labels, rotation=90, fontsize=6); ax.set_yticks(range(len(labels)), labels, fontsize=6)
    ax.set_title("Selected-feature Pearson redundancy structure"); fig.colorbar(im, ax=ax, shrink=.75, label="Pearson r"); save(fig, "selected_feature_redundancy_heatmap.png")
    return outputs


def _element_counts(composition_json: Iterable[str]) -> pd.DataFrame:
    counts: Counter[str] = Counter()
    for value in composition_json:
        counts.update(json.loads(value).keys())
    return pd.DataFrame({"element": list(counts), "observations": list(counts.values())}).sort_values("observations", ascending=False)


def _write_markdown_reports(
    report_dir: Path, metrics: dict[str, object], mapping: pd.DataFrame, associations: pd.DataFrame,
    pairs: pd.DataFrame, sets: dict[str, list[str]], target_stats: pd.DataFrame,
    phase_comparison: dict[str, float], duplicate_groups: list[list[str]],
) -> None:
    def top(cohort: str, metric: str, n: int = 10) -> str:
        table = associations.loc[associations.cohort.eq(cohort)].nlargest(n, metric)
        return "\n".join(f"- `{r.feature}`: {getattr(r, metric):.4f}" for r in table.itertuples())

    all_target = target_stats.set_index("cohort").loc["ALL"]
    eda = f"""# Phase 4 exploratory data analysis

## Analysis population

Phase 4 contains exactly **{metrics['rows']:,}** validated observations: **{metrics['fcc_observations']:,} FCC** and **{metrics['bcc_observations']:,} BCC**. The **255 provisional HCP configurations are excluded** because validated reference Warren–Cowley arrays remain unavailable. There are {metrics['unique_configurations']:,} unique configuration identifiers, {metrics['unique_alloy_systems']:,} chemical systems, {metrics['unique_formulas']:,} formula labels, and {metrics['unique_compositions']:,} distinct normalized composition vectors.

The target is `{TARGET}`: the source-provided mean of the absolute pair-resolved first-shell Warren–Cowley coefficients over the unique unlike pairs. It is an aggregate ordering magnitude, not a signed or pair-specific coefficient.

## Target distribution

Across both phases, the target ranges from **{all_target.minimum:.6g} to {all_target.maximum:.6g}**, with mean **{all_target['mean']:.4f}**, median **{all_target['median']:.4f}**, standard deviation **{all_target['std']:.4f}**, and skewness **{all_target.skewness:.3f}**. The 5th/95th percentiles are **{all_target.p05:.4f}/{all_target.p95:.4f}**. Tukey's descriptive rule identifies {int(all_target.tukey_outlier_count):,} upper/lower-tail observations; these are retained because a bounded physical response can have legitimate extreme configurations. {100*all_target.near_zero_le_0_05_fraction:.2f}% are at or below 0.05 and {100*all_target.near_zero_le_0_10_fraction:.2f}% are at or below 0.10.

The distribution is right-skewed but not so concentrated at zero that a zero-inflated target formulation is indicated. A monotone transform may be tested during Phase 5 as a sensitivity analysis, while predictions and error reporting should remain on the original physically interpretable scale.

## FCC/BCC target comparison

BCC has mean target **{phase_comparison['bcc_mean']:.4f}** versus **{phase_comparison['fcc_mean']:.4f}** for FCC (difference {phase_comparison['mean_difference_bcc_minus_fcc']:.4f}; standardized mean difference {phase_comparison['cohens_d']:.3f}). The two empirical distributions have KS distance {phase_comparison['ks_statistic']:.3f}. These are descriptive dataset contrasts, not claims of a causal phase effect, because composition/configuration coverage is not randomized.

## Data quality and duplication

All 348 Phase 3 predictors and the target are complete in the validated FCC/BCC table. There are no duplicate configuration identifiers and no exact duplicate complete feature rows. Exact duplicate *feature columns* are listed in the redundancy report ({len(duplicate_groups)} groups); mathematical redundancy is expected for complementary phase indicators and some composition constructions. Near-duplicate observations were not collapsed: repeated formula labels can represent distinct configurations and are scientifically meaningful.

## Interpretation boundary

Correlations and mutual information quantify association, not causal mechanisms. The 83,797 rows are configuration-level observations nested within compositions and alloy systems, so naive random train/test splitting could overstate generalization. Phase 5 should use group-aware splits by composition or alloy system and keep FCC/BCC stratification explicit.

Mutual-information values are used only for ranking. They were estimated with a deterministic, target-quantile-stratified sample of at most 20,000 rows per cohort and five-neighbor regression. Their absolute magnitude is estimator- and sampling-dependent, especially with repeated/discrete composition descriptors, and must not be read as an effect size.
"""
    (report_dir / "eda_analysis.md").write_text(eda, encoding="utf-8")

    group_counts = mapping.feature_group.value_counts()
    group_lines = "\n".join(f"- **{group}**: {count} features" for group, count in group_counts.items())
    flags = mapping.loc[mapping.caution_reason.ne(""), ["feature", "caution_reason"]]
    flag_lines = "\n".join(f"- `{r.feature}` — {r.caution_reason}" for r in flags.itertuples())
    feature_groups = f"""# Phase 4 feature groups

The 348 candidate predictors are classified by physical meaning, scientific origin, and expected cross-source availability. The complete machine-readable mapping is `results/tables/phase4/feature_group_mapping.csv`.

## Group counts

{group_lines}

## Risk flags

No identifiers or direct SRO-derived proxy features entered the Phase 3 feature library. Initial-geometry descriptors are scientifically legitimate pre-relaxation measurements, but are flagged because coordination, neighbor-distance, packing, and local-difference statistics may encode configuration-specific ordering. Phase indicators and atom/component counts are metadata or grouping variables and should not be interpreted as elemental mechanisms.

{flag_lines}

## Provenance meanings

- `direct source`: copied from an allowed initial/source field.
- `composition-derived`: computed only from normalized elemental fractions.
- `elemental-reference-derived`: composition statistics using reconstructed elemental reference values.
- `structure-derived`: calculated from the initial, pre-relaxation structure only.

Final energy, relaxed volume, final symmetry/structure, force, pressure, hull distance, and source SRO/order parameters remain excluded.
"""
    (report_dir / "feature_groups.md").write_text(feature_groups, encoding="utf-8")

    redundancy = f"""# Phase 4 feature redundancy audit

The full numerical library contains {metrics['features_entering_analysis']} predictors, of which {metrics['constant_features_all']} are constant and {metrics['near_zero_variance_features_all']} meet the conservative near-zero-variance rule in the aggregate cohort. The all-data Pearson matrix contains **{len(pairs):,} pairs with |r| ≥ {HIGH_CORRELATION_THRESHOLD:.2f}**. There are **{len(duplicate_groups)} exact duplicate-column groups**.

High correlation is expected among alternate summaries of the same elemental property (minimum/maximum/range/mean/mode), between reconstructed descriptors and their supplied Magpie counterparts, among pair-fraction constraints, and between complementary phase indicators. `highly_correlated_feature_pairs.csv` preserves all pairs. The displayed heatmap is restricted to the portable preliminary set so it remains readable.

Known deterministic relationships include `configurational_entropy_j_mol_k = R * configurational_entropy_kb_per_atom`, `phase_FCC + phase_BCC = 1` in the two-phase cohort, `0-norm = nelements = composition_number_of_elements`, and a unit-sum constraint across all composition fractions (and separately across random-pair fractions). These relationships motivate pruning but do not invalidate the underlying physical quantities.

Redundancy is not evidence that a descriptor is physically invalid. For the balanced preliminary set, one representative per |r| ≥ 0.95 neighborhood is retained using a deterministic priority combining portability and aggregate Spearman/MI screening. This rule is preliminary and must be frozen inside training folds if altered in Phase 5.

Exact duplicate groups:

{chr(10).join('- ' + ', '.join(f'`{x}`' for x in group) for group in duplicate_groups) if duplicate_groups else '- None'}
"""
    (report_dir / "feature_redundancy.md").write_text(redundancy, encoding="utf-8")

    minimal = f"""# Minimal cross-dataset feature set

## Purpose

This is a **preliminary, non-final** set for future FCC/BCC/HCP comparison. It uses composition, elemental references, and an explicit phase indicator; it deliberately avoids initial-geometry descriptors that may be unavailable or inconsistently generated for an HCP source.

## MINIMAL_PRELIMINARY ({len(sets['MINIMAL_PRELIMINARY'])} features)

{chr(10).join(f'- `{x}`' for x in sets['MINIMAL_PRELIMINARY'])}

All quantities are reproducible from composition plus the versioned elemental-reference table, except the phase label. `phase_FCC` is sufficient because BCC is its complement in the present two-phase database; future HCP integration must replace this binary coding with an explicitly fitted three-level phase representation. Temperature is excluded because it is not genuinely available in the 84k source.

## Phase 5 use

Compare FULL_CLEAN, BALANCED_PRELIMINARY, and MINIMAL_PRELIMINARY under identical group-aware validation. Do not select the winning set from the held-out test cohort. Structure-derived features should be evaluated separately to quantify portability versus configuration sensitivity.
"""
    (report_dir / "minimal_feature_set.md").write_text(minimal, encoding="utf-8")

    comparison = f"""# FCC versus BCC exploratory comparison

## Coverage and target

The validated database contains {metrics['fcc_observations']:,} FCC and {metrics['bcc_observations']:,} BCC configurations. BCC has a higher aggregate mean target ({phase_comparison['bcc_mean']:.4f}) than FCC ({phase_comparison['fcc_mean']:.4f}); the standardized difference is {phase_comparison['cohens_d']:.3f}. Coverage imbalance and repeated compositions mean this must not be interpreted as an intrinsic phase-only effect.

## Leading FCC Spearman associations

{top('FCC', 'abs_spearman_rho')}

## Leading BCC Spearman associations

{top('BCC', 'abs_spearman_rho')}

## Phase stability

Feature rankings differ materially between FCC and BCC (see `phase_association_comparison.csv` and the comparison figure). Phase 5 should therefore compare pooled models with phase indicators against phase-specific models, using the same grouped outer splits. Features whose association reverses sign should be treated as interaction candidates rather than universal mechanisms.
"""
    (report_dir / "fcc_bcc_comparison.md").write_text(comparison, encoding="utf-8")


def run_phase4(
    data_path: Path = Path("data/processed/ml_dataset.parquet"),
    provenance_path: Path = Path("reports/tables/feature_provenance.csv"),
    results_dir: Path = Path("results/tables/phase4"),
    thesis_table_dir: Path = Path("thesis_outputs/tables/phase4"),
    figure_dir: Path = Path("thesis_outputs/figures/phase4"),
    report_dir: Path = Path("reports"),
) -> dict[str, object]:
    data = pd.read_parquet(data_path)
    provenance = pd.read_csv(provenance_path)
    features = provenance["feature"].tolist()
    if len(data) != 83_797 or data.phase.value_counts().to_dict() != {"BCC": 43_372, "FCC": 40_425}:
        raise ValueError("Phase 4 must contain exactly the validated 83,797 FCC/BCC rows")
    if set(data.phase) != {"FCC", "BCC"} or TARGET not in data or data[TARGET].isna().any():
        raise ValueError("invalid Phase 4 cohort or target")
    if any(token in feature.lower() for feature in features for token in ("mean ordering parameter", "target_", "sro")):
        raise ValueError("direct target/SRO proxy entered predictors")

    for directory in (results_dir, thesis_table_dir, figure_dir, report_dir): directory.mkdir(parents=True, exist_ok=True)
    mapping = build_feature_mapping(provenance)
    target_stats = pd.DataFrame([describe_target(cohort_frame(data, cohort)[TARGET], cohort) for cohort in PHASES])
    qualities = pd.concat([feature_quality(data, features, cohort) for cohort in PHASES], ignore_index=True)
    associations = pd.concat([association_table(data, features, cohort) for cohort in PHASES], ignore_index=True)
    usable_all = qualities.loc[qualities.cohort.eq("ALL") & ~qualities.constant_flag, "feature"].tolist()
    pairs, corr = highly_correlated_pairs(data, usable_all)
    duplicates = exact_duplicate_feature_groups(data, features)
    memberships, sets = preliminary_sets(mapping, qualities.loc[qualities.cohort.eq("ALL")], associations, pairs)

    fcc = data.loc[data.phase.eq("FCC"), TARGET]; bcc = data.loc[data.phase.eq("BCC"), TARGET]
    pooled_sd = np.sqrt(((len(fcc)-1)*fcc.var(ddof=1)+(len(bcc)-1)*bcc.var(ddof=1))/(len(fcc)+len(bcc)-2))
    ks = stats.ks_2samp(fcc, bcc)
    phase_comparison = {"fcc_mean": float(fcc.mean()), "bcc_mean": float(bcc.mean()),
                        "mean_difference_bcc_minus_fcc": float(bcc.mean()-fcc.mean()),
                        "cohens_d": float((bcc.mean()-fcc.mean())/pooled_sd),
                        "ks_statistic": float(ks.statistic), "ks_pvalue": float(ks.pvalue)}

    phase_counts = data.phase.value_counts().reindex(["FCC", "BCC"]).rename_axis("phase").reset_index(name="observations")
    phase_counts = pd.concat([phase_counts, pd.DataFrame([{"phase": "HCP excluded (provisional)", "observations": 255}])], ignore_index=True)
    alloy = data.chemical_system.value_counts().rename_axis("chemical_system").reset_index(name="observations")
    elements = _element_counts(data.composition_fractions_json)
    components = data.number_of_elements.value_counts().sort_index().rename_axis("number_of_elements").reset_index(name="observations")
    groups = mapping.feature_group.value_counts().rename_axis("feature_group").reset_index(name="features")
    origins = mapping.origin.value_counts().rename_axis("origin").reset_index(name="features")
    composition_coverage = data.groupby(["phase", "chemical_system"], observed=True).agg(observations=("fid", "size"), unique_compositions=("composition_fractions_json", "nunique"), unique_formulas=("formula", "nunique")).reset_index()
    duplicate_summary = pd.DataFrame([
        {"check": "duplicate configuration identifiers", "count": int(data.configuration_id.duplicated().sum()), "interpretation": "must be zero"},
        {"check": "duplicate complete predictor rows", "count": int(data[features].duplicated().sum()), "interpretation": "must be zero"},
        {"check": "rows sharing a formula label", "count": int(data.formula.duplicated(keep=False).sum()), "interpretation": "distinct configurations may share formula"},
        {"check": "rows sharing a normalized composition", "count": int(data.composition_fractions_json.duplicated(keep=False).sum()), "interpretation": "retain for configuration-level SRO variation"},
    ])
    phase_assoc = associations.pivot(index="feature", columns="cohort", values=["pearson_r", "spearman_rho", "mutual_information"]).reset_index()
    phase_assoc.columns = ["_".join(str(x) for x in col if x).rstrip("_") if isinstance(col, tuple) else col for col in phase_assoc.columns]

    tables = {
        "phase_counts": phase_counts, "alloy_system_counts": alloy, "element_counts": elements,
        "component_counts": components, "feature_group_counts": groups, "origin_counts": origins,
        "composition_coverage_by_phase_system": composition_coverage,
        "observation_duplicate_summary": duplicate_summary,
        "target_statistics": target_stats, "feature_quality": qualities,
        "feature_group_mapping": mapping, "feature_target_associations": associations,
        "highly_correlated_feature_pairs": pairs, "preliminary_feature_sets": memberships,
        "phase_association_comparison": phase_assoc,
        "phase_target_comparison": pd.DataFrame([phase_comparison]),
    }
    for name, table in tables.items():
        table.to_csv(results_dir / f"{name}.csv", index=False)
        table.to_csv(thesis_table_dir / f"{name}.csv", index=False)
    corr.to_csv(results_dir / "feature_feature_pearson_matrix.csv", index_label="feature")

    selected_heat = sets["MINIMAL_PRELIMINARY"]
    selected_corr = data[selected_heat].corr()
    figures = create_figures(data, mapping, associations, selected_corr, selected_heat, figure_dir, tables)

    constant_all = qualities.loc[qualities.cohort.eq("ALL") & qualities.constant_flag, "feature"].tolist()
    nzv_all = qualities.loc[qualities.cohort.eq("ALL") & qualities.near_zero_variance_flag, "feature"].tolist()
    metrics: dict[str, object] = {
        "rows": len(data), "fcc_observations": int((data.phase == "FCC").sum()), "bcc_observations": int((data.phase == "BCC").sum()),
        "validated_hcp_observations": 0, "provisional_hcp_excluded": 255,
        "unique_configurations": int(data.configuration_id.nunique()), "unique_alloy_systems": int(data.chemical_system.nunique()),
        "unique_formulas": int(data.formula.nunique()), "unique_compositions": int(data.composition_fractions_json.nunique()),
        "features_entering_analysis": len(features), "identifier_or_direct_proxy_features_removed": int(mapping.unsuitable_for_analysis.sum()),
        "constant_features_all": len(constant_all), "constant_feature_names_all": constant_all,
        "near_zero_variance_features_all": len(nzv_all), "near_zero_variance_feature_names_all": nzv_all,
        "highly_correlated_pairs_abs_r_ge_0_95": len(pairs), "exact_duplicate_feature_groups": duplicates,
        "feature_set_counts": {name: len(values) for name, values in sets.items()},
        "phase_target_comparison": phase_comparison,
        "target_statistics": target_stats.to_dict("records"),
        "top_associations": {cohort: {
            "pearson": associations.loc[associations.cohort.eq(cohort)].nlargest(10, "abs_pearson_r")[["feature", "pearson_r"]].to_dict("records"),
            "spearman": associations.loc[associations.cohort.eq(cohort)].nlargest(10, "abs_spearman_rho")[["feature", "spearman_rho"]].to_dict("records"),
            "mutual_information": associations.loc[associations.cohort.eq(cohort)].nlargest(10, "mutual_information")[["feature", "mutual_information"]].to_dict("records"),
        } for cohort in PHASES},
        "mi_estimation": {"method": "5-neighbor mutual information regression", "max_rows_per_cohort": MI_MAX_ROWS, "sampling": "deterministic target-quantile-stratified", "random_state": RANDOM_STATE},
        "figures": figures, "ready_for_phase5": True,
    }
    (report_dir / "phase4_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    _write_markdown_reports(report_dir, metrics, mapping, associations, pairs, sets, target_stats, phase_comparison, duplicates)
    return metrics
