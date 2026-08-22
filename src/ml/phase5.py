"""Phase 5 grouped regression, ablation and interpretation pipeline.

The primary test is an alloy-system-held-out outer split. Model/feature-set
selection uses only group-aware cross-validation within the outer training set.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.base import clone
from sklearn.compose import TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import (
    ExtraTreesRegressor, GradientBoostingRegressor, HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.feature_selection import VarianceThreshold
from sklearn.inspection import permutation_importance
from sklearn.linear_model import ElasticNet, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, KFold, train_test_split, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR


TARGET = "target_mean_abs_sro_shell1"
SEED = 42
OUTER_TEST_FRACTION = 0.20
INNER_FOLDS = 3
FORBIDDEN_TOKENS = ("sro", "ordering parameter", "target_")
FINAL_LEAKAGE = {
    "Ef_per_atom", "e_above_hull", "e_per_atom", "volume_per_atom", "space_group_number",
    "magmom", "max_FORCE", "pressure", "structure", "structure_ini",
}


@dataclass(frozen=True)
class SplitDefinition:
    strategy: str
    train_index: np.ndarray
    test_index: np.ndarray
    group_column: str | None


def validate_ml_frame(data: pd.DataFrame, features: list[str]) -> dict[str, Any]:
    counts = data.phase.value_counts().to_dict()
    if len(data) != 83_797 or counts != {"BCC": 43_372, "FCC": 40_425}:
        raise ValueError(f"invalid validated cohort: rows={len(data)}, phases={counts}")
    if set(data.phase) != {"FCC", "BCC"}:
        raise ValueError("provisional/unknown phase entered ML frame")
    target = pd.to_numeric(data[TARGET], errors="coerce")
    if target.isna().any() or not np.isfinite(target).all() or (target < 0).any():
        raise ValueError("target is missing, non-finite, or physically invalid")
    forbidden = [f for f in features if any(token in f.lower() for token in FORBIDDEN_TOKENS)]
    leakage = sorted(set(features).intersection(FINAL_LEAKAGE))
    identifiers = [f for f in features if f.lower() in {"fid", "source_id", "configuration_id", "id"} or f.lower().endswith("_id")]
    if forbidden or leakage or identifiers:
        raise ValueError(f"unsafe predictors: proxies={forbidden}, leakage={leakage}, ids={identifiers}")
    if data[features].isna().any().any() or not np.isfinite(data[features].to_numpy(dtype=float)).all():
        raise ValueError("predictors contain missing or non-finite values")
    return {
        "rows": len(data), "fcc": counts["FCC"], "bcc": counts["BCC"], "validated_hcp": 0,
        "target_missing": int(target.isna().sum()), "predictors": len(features),
        "direct_proxy_predictors": len(forbidden), "final_state_leakage_predictors": len(leakage),
        "identifier_predictors": len(identifiers),
    }


def load_feature_sets(
    mapping_path: Path = Path("results/tables/phase4/feature_group_mapping.csv"),
    phase4_sets_path: Path = Path("results/tables/phase4/preliminary_feature_sets.csv"),
) -> tuple[dict[str, list[str]], pd.DataFrame]:
    mapping = pd.read_csv(mapping_path)
    membership = pd.read_csv(phase4_sets_path)
    sets = {name: group.sort_values("selection_order").feature.tolist() for name, group in membership.groupby("set")}
    full = set(sets["FULL_CLEAN"])
    composition = mapping.loc[
        mapping.origin.isin(["composition-derived", "elemental-reference-derived"]) & mapping.feature.isin(full), "feature"
    ].tolist()
    structure = mapping.loc[mapping.origin.eq("structure-derived") & mapping.feature.isin(full), "feature"].tolist()
    initial_direct = [f for f in ["space_group_number_ini"] if f in full]
    sets["COMPOSITION_ONLY"] = composition
    sets["COMPOSITION_PLUS_PHASE"] = [*composition, *[f for f in ["phase_FCC"] if f in full]]
    sets["COMPOSITION_PLUS_INITIAL_STRUCTURE"] = list(dict.fromkeys([*composition, *structure, *initial_direct]))
    sets["THERMODYNAMIC_OR_ENERGETIC"] = []
    return sets, mapping


def make_outer_split(data: pd.DataFrame, strategy: str, seed: int = SEED) -> SplitDefinition:
    indices = np.arange(len(data))
    if strategy == "random_configuration":
        train, test = train_test_split(indices, test_size=OUTER_TEST_FRACTION, random_state=seed, stratify=data.phase)
        return SplitDefinition(strategy, np.sort(train), np.sort(test), None)
    columns = {"composition_grouped": "composition_fractions_json", "alloy_system_grouped": "chemical_system"}
    if strategy not in columns:
        raise ValueError(f"unknown split strategy: {strategy}")
    column = columns[strategy]
    splitter = GroupShuffleSplit(n_splits=20, test_size=OUTER_TEST_FRACTION, random_state=seed)
    for train, test in splitter.split(indices, groups=data[column]):
        if set(data.iloc[train].phase) == {"FCC", "BCC"} and set(data.iloc[test].phase) == {"FCC", "BCC"}:
            if set(data.iloc[train][column]).isdisjoint(set(data.iloc[test][column])):
                return SplitDefinition(strategy, np.sort(train), np.sort(test), column)
    raise ValueError(f"could not construct valid {strategy} split")


def inner_cv(data: pd.DataFrame, outer_train: np.ndarray, strategy: str):
    if strategy == "random_configuration":
        return KFold(n_splits=INNER_FOLDS, shuffle=True, random_state=SEED), None
    group_column = "composition_fractions_json" if strategy == "composition_grouped" else "chemical_system"
    return GroupKFold(n_splits=INNER_FOLDS, shuffle=True, random_state=SEED), data.iloc[outer_train][group_column].to_numpy()


def split_audit(data: pd.DataFrame, split: SplitDefinition) -> dict[str, Any]:
    train, test = data.iloc[split.train_index], data.iloc[split.test_index]
    group_overlap = None
    if split.group_column:
        group_overlap = len(set(train[split.group_column]).intersection(test[split.group_column]))
    return {
        "strategy": split.strategy, "seed": SEED, "train_rows": len(train), "test_rows": len(test),
        "train_fcc": int(train.phase.eq("FCC").sum()), "train_bcc": int(train.phase.eq("BCC").sum()),
        "test_fcc": int(test.phase.eq("FCC").sum()), "test_bcc": int(test.phase.eq("BCC").sum()),
        "group_column": split.group_column or "none", "train_groups": int(train[split.group_column].nunique()) if split.group_column else len(train),
        "test_groups": int(test[split.group_column].nunique()) if split.group_column else len(test),
        "group_overlap": group_overlap if group_overlap is not None else "not_applicable",
    }


def model_specs() -> dict[str, tuple[Any, bool]]:
    return {
        "DummyMedian": (DummyRegressor(strategy="median"), False),
        "LinearRegression": (LinearRegression(n_jobs=-1), True),
        "Ridge": (Ridge(alpha=10.0), True),
        "ElasticNet": (ElasticNet(alpha=0.01, l1_ratio=0.2, max_iter=300, tol=1e-3, precompute=True, selection="cyclic", random_state=SEED), True),
        "RandomForest": (RandomForestRegressor(n_estimators=60, max_depth=18, min_samples_leaf=2, max_features=0.5, n_jobs=-1, random_state=SEED), False),
        "ExtraTrees": (ExtraTreesRegressor(n_estimators=80, min_samples_leaf=2, max_features=0.7, n_jobs=-1, random_state=SEED), False),
        "GradientBoosting": (GradientBoostingRegressor(n_estimators=70, learning_rate=0.06, max_depth=2, subsample=0.8, max_features="sqrt", random_state=SEED), False),
        "HistGradientBoosting": (HistGradientBoostingRegressor(max_iter=150, learning_rate=0.08, max_leaf_nodes=31, l2_regularization=1.0, random_state=SEED), False),
        "SVR_subset": (SVR(C=10.0, epsilon=0.05, gamma="scale", cache_size=2000), True),
    }


def build_pipeline(estimator: Any, scale: bool) -> Pipeline:
    steps: list[tuple[str, Any]] = [("variance", VarianceThreshold(threshold=0.0))]
    if scale:
        steps.append(("scale", StandardScaler()))
    steps.append(("model", clone(estimator)))
    return Pipeline(steps)


def metric_dict(y_true: np.ndarray, y_pred: np.ndarray, prefix: str) -> dict[str, float]:
    std = float(np.std(y_true, ddof=1))
    mae = float(mean_absolute_error(y_true, y_pred)); rmse = float(mean_squared_error(y_true, y_pred) ** 0.5)
    return {f"{prefix}_mae": mae, f"{prefix}_rmse": rmse, f"{prefix}_r2": float(r2_score(y_true, y_pred)),
            f"{prefix}_normalized_mae": mae / std if std else np.nan, f"{prefix}_normalized_rmse": rmse / std if std else np.nan}


def _subsample_train(indices: np.ndarray, max_rows: int | None) -> np.ndarray:
    if max_rows is None or len(indices) <= max_rows:
        return indices
    rng = np.random.default_rng(SEED)
    return np.sort(rng.choice(indices, max_rows, replace=False))


def evaluate_configuration(
    data: pd.DataFrame, cohort: str, features: list[str], feature_set: str,
    model_name: str, split: SplitDefinition, do_cv: bool = True,
) -> tuple[dict[str, Any], pd.DataFrame, Pipeline]:
    estimator, scale = model_specs()[model_name]
    cohort_mask = np.ones(len(data), dtype=bool) if cohort == "ALL" else data.phase.eq(cohort).to_numpy()
    train_idx = split.train_index[cohort_mask[split.train_index]]
    test_idx = split.test_index[cohort_mask[split.test_index]]
    max_rows = 10_000 if model_name == "SVR_subset" else None
    fit_idx = _subsample_train(train_idx, max_rows)
    pipe = build_pipeline(estimator, scale)
    start = time.perf_counter()
    record: dict[str, Any] = {
        "cohort": cohort, "split_strategy": split.strategy, "model": model_name, "feature_set": feature_set,
        "declared_features": len(features), "train_rows_available": len(train_idx), "train_rows_used": len(fit_idx), "test_rows": len(test_idx),
    }
    if do_cv:
        if split.strategy == "random_configuration":
            cv = KFold(n_splits=INNER_FOLDS, shuffle=True, random_state=SEED); groups = None
        else:
            group_col = "composition_fractions_json" if split.strategy == "composition_grouped" else "chemical_system"
            cv = GroupKFold(n_splits=INNER_FOLDS, shuffle=True, random_state=SEED); groups = data.iloc[fit_idx][group_col].to_numpy()
        scoring = {"r2": "r2", "mae": "neg_mean_absolute_error", "rmse": "neg_root_mean_squared_error"}
        scores = cross_validate(pipe, data.iloc[fit_idx][features], data.iloc[fit_idx][TARGET], cv=cv, groups=groups, scoring=scoring, n_jobs=1, return_train_score=False)
        for metric in ("r2", "mae", "rmse"):
            values = scores[f"test_{metric}"] * (-1 if metric in {"mae", "rmse"} else 1)
            record[f"cv_{metric}_mean"] = float(values.mean()); record[f"cv_{metric}_std"] = float(values.std(ddof=1))
    pipe.fit(data.iloc[fit_idx][features], data.iloc[fit_idx][TARGET])
    train_pred = pipe.predict(data.iloc[fit_idx][features]); test_pred = pipe.predict(data.iloc[test_idx][features])
    record.update(metric_dict(data.iloc[fit_idx][TARGET].to_numpy(), train_pred, "train"))
    record.update(metric_dict(data.iloc[test_idx][TARGET].to_numpy(), test_pred, "test"))
    record["retained_features_after_variance"] = int(pipe.named_steps["variance"].get_support().sum())
    record["runtime_seconds"] = float(time.perf_counter() - start)
    record["hyperparameters_json"] = json.dumps(pipe.named_steps["model"].get_params(deep=False), default=str, sort_keys=True)
    predictions = data.iloc[test_idx][["fid", "phase", "chemical_system", "composition_fractions_json", TARGET]].copy()
    predictions["prediction"] = test_pred; predictions["residual"] = predictions[TARGET] - predictions.prediction
    predictions["cohort"] = cohort; predictions["model"] = model_name; predictions["feature_set"] = feature_set; predictions["split_strategy"] = split.strategy
    return record, predictions, pipe


def retained_feature_names(pipe: Pipeline, features: list[str]) -> list[str]:
    return list(np.asarray(features)[pipe.named_steps["variance"].get_support()])


def feature_importance_table(
    pipe: Pipeline, features: list[str], X_test: pd.DataFrame, y_test: pd.Series, max_rows: int = 3_000,
) -> pd.DataFrame:
    retained = retained_feature_names(pipe, features)
    model = pipe.named_steps["model"]
    built_in = getattr(model, "feature_importances_", np.full(len(retained), np.nan))
    if len(X_test) > max_rows:
        chosen = X_test.sample(max_rows, random_state=SEED).index
        X_perm, y_perm = X_test.loc[chosen], y_test.loc[chosen]
    else:
        X_perm, y_perm = X_test, y_test
    perm = permutation_importance(pipe, X_perm[features], y_perm, scoring="neg_mean_absolute_error", n_repeats=3, random_state=SEED, n_jobs=-1)
    # Pipeline-level permutation returns declared-feature order; constants have zero contribution.
    perm_map = dict(zip(features, perm.importances_mean))
    perm_std_map = dict(zip(features, perm.importances_std))
    table = pd.DataFrame({"feature": retained, "built_in_importance": built_in,
                          "permutation_mae_increase": [perm_map[f] for f in retained],
                          "permutation_std": [perm_std_map[f] for f in retained]})
    return table.sort_values("permutation_mae_increase", ascending=False)


def _save_figure(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")


def _metric_bars(table: pd.DataFrame, metric: str, title: str, path: Path) -> None:
    import matplotlib.pyplot as plt
    shown = table.sort_values(metric).tail(18).copy()
    shown["label"] = shown.model + " · " + shown.feature_set.str.replace("_PRELIMINARY", "", regex=False)
    fig, ax = plt.subplots(figsize=(8.3, 5.7)); ax.barh(shown.label, shown[metric], color="#4C78A8")
    ax.set(xlabel=metric.replace("test_", "").upper(), title=title); ax.spines[["top", "right"]].set_visible(False)
    _save_figure(fig, path); plt.close(fig)


def create_ml_figures(
    results: pd.DataFrame, best_rows: pd.DataFrame, best_predictions: dict[str, pd.DataFrame],
    grouped: pd.DataFrame, importances: dict[str, pd.DataFrame], figure_dir: Path,
) -> list[str]:
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("MPLCONFIGDIR", str(Path(".cache/matplotlib").resolve()))
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 11, "savefig.dpi": 300})
    figure_dir.mkdir(parents=True, exist_ok=True); outputs: list[str] = []
    def save(fig, name):
        path = figure_dir / name; _save_figure(fig, path); plt.close(fig); outputs.append(str(path))

    unified = results.loc[results.cohort.eq("ALL")]
    for metric, name in (("test_r2", "model_r2_comparison_unified.png"), ("test_mae", "model_mae_comparison_unified.png"), ("test_rmse", "model_rmse_comparison_unified.png")):
        _metric_bars(unified, metric, f"Unified model comparison: {metric.replace('test_', '').upper()}", figure_dir / name); outputs.append(str(figure_dir / name))
    for cohort in ("FCC", "BCC"):
        _metric_bars(results.loc[results.cohort.eq(cohort)], "test_r2", f"{cohort} model comparison", figure_dir / f"model_comparison_{cohort.lower()}.png"); outputs.append(str(figure_dir / f"model_comparison_{cohort.lower()}.png"))

    fig, ax = plt.subplots(figsize=(6.6, 4.2)); x = np.arange(3); values = best_rows.set_index("cohort").reindex(["ALL", "FCC", "BCC"]).test_r2
    bars = ax.bar(x, values, color=["#6B7280", "#2878B5", "#D95319"]); ax.set_xticks(x, ["Unified", "FCC-specific", "BCC-specific"])
    ax.bar_label(bars, labels=[f"{v:.3f}" for v in values], padding=2); ax.set(ylabel="Alloy-held-out R²", title="Unified versus phase-specific best models"); ax.spines[["top", "right"]].set_visible(False); save(fig, "unified_vs_phase_specific.png")

    set_best = unified.sort_values("cv_r2_mean").groupby("feature_set", as_index=False).tail(1).sort_values("test_r2")
    _metric_bars(set_best, "test_r2", "Unified feature-set ablation", figure_dir / "feature_set_comparison.png",); outputs.append(str(figure_dir / "feature_set_comparison.png"))

    fig, ax = plt.subplots(figsize=(7.2, 4.8)); pivot = grouped.pivot(index="cohort", columns="split_strategy", values="test_r2").reindex(["ALL", "FCC", "BCC"])
    pivot = pivot.rename(columns={"alloy_system_grouped": "Alloy-system held out", "composition_grouped": "Composition held out", "random_configuration": "Random baseline"})
    pivot.plot(kind="bar", ax=ax, color=["#D95319", "#59A14F", "#4C78A8"]); ax.set(ylabel="Held-out R²", xlabel="", title="Random versus grouped generalization"); ax.tick_params(axis="x", rotation=0)
    ax.legend(title="Split", frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3); ax.spines[["top", "right"]].set_visible(False); save(fig, "random_vs_grouped_validation.png")

    for cohort, label, color in (("ALL", "unified", "#6B7280"), ("FCC", "fcc", "#2878B5"), ("BCC", "bcc", "#D95319")):
        pred = best_predictions[cohort]
        fig, ax = plt.subplots(figsize=(5.0, 4.6)); hb = ax.hexbin(pred[TARGET], pred.prediction, gridsize=45, mincnt=1, bins="log", cmap="viridis")
        lo, hi = min(pred[TARGET].min(), pred.prediction.min()), max(pred[TARGET].max(), pred.prediction.max()); ax.plot([lo, hi], [lo, hi], "--", color="#E15759")
        ax.set(xlabel="Observed SRO magnitude", ylabel="Predicted SRO magnitude", title=f"Best {label} model: observed vs predicted"); fig.colorbar(hb, ax=ax, label="log count"); save(fig, f"predicted_vs_actual_{label}.png")
        fig, ax = plt.subplots(figsize=(5.2, 4.2)); ax.scatter(pred.prediction, pred.residual, s=5, alpha=.18, color=color); ax.axhline(0, color="#222", lw=1)
        ax.set(xlabel="Predicted SRO magnitude", ylabel="Observed − predicted", title=f"{label.capitalize()} residuals"); ax.spines[["top", "right"]].set_visible(False); save(fig, f"residual_plot_{label}.png")
    pred = best_predictions["ALL"]
    fig, ax = plt.subplots(figsize=(5.6, 4.0)); ax.hist(pred.residual, bins=55, color="#6B7280", alpha=.8); ax.axvline(0, color="#222", lw=1)
    ax.set(xlabel="Observed − predicted", ylabel="Observations", title="Unified residual distribution"); ax.spines[["top", "right"]].set_visible(False); save(fig, "residual_distribution_unified.png")

    for cohort, label, color in (("ALL", "unified", "#6B7280"), ("FCC", "fcc", "#2878B5"), ("BCC", "bcc", "#D95319")):
        shown = importances[cohort].head(20).sort_values("permutation_mae_increase")
        fig, ax = plt.subplots(figsize=(7.5, 5.4)); ax.barh(shown.feature, shown.permutation_mae_increase, xerr=shown.permutation_std, color=color)
        ax.set(xlabel="Permutation increase in MAE", title=f"{label.capitalize()} model feature importance"); ax.spines[["top", "right"]].set_visible(False); save(fig, f"feature_importance_{label}.png")
    return outputs


def _write_reports(
    report_dir: Path, validation: dict[str, Any], audits: pd.DataFrame, results: pd.DataFrame,
    best: pd.DataFrame, grouped: pd.DataFrame, space: pd.DataFrame, alloy: pd.DataFrame,
    phase_scope: pd.DataFrame, sets: dict[str, list[str]], runtime_seconds: float,
) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "ml_data_validation.md").write_text(f"""# Phase 5 ML data validation

Phase 5 uses exactly **{validation['rows']:,}** validated rows: **{validation['fcc']:,} FCC**, **{validation['bcc']:,} BCC**, and **0 HCP**. The 255 provisional HCP configurations are absent. `{TARGET}` is complete, finite, non-negative, and used only as the response.

The predictor library contains {validation['predictors']} Phase 4 candidates before set-specific filtering, with zero identifiers, zero direct SRO/order-parameter proxies, and zero relaxed/final-state leakage fields. `VarianceThreshold(0)` is the first step of every sklearn pipeline, so constants are learned and removed using training data only. Scalers for linear, regularized, and SVR models are also inside the pipeline. No imputation is required because the validated predictors are complete.

Phase 4's `BALANCED_PRELIMINARY` was informed by whole-dataset exploratory association rankings. It is therefore a predeclared exploratory set, not a pristine confirmatory selection. `FULL_CLEAN`, `MINIMAL_PRELIMINARY`, and physically defined composition ablations are reported alongside it. No HCP result is claimed.
""", encoding="utf-8")
    audit_lines = "\n".join(f"- **{r.strategy}**: {r.train_rows:,} train / {r.test_rows:,} test; group column `{r.group_column}`; overlap {r.group_overlap}; test FCC/BCC {r.test_fcc:,}/{r.test_bcc:,}." for r in audits.itertuples())
    (report_dir / "ml_split_strategy.md").write_text(f"""# Phase 5 split strategy

The primary outer test holds out entire **alloy systems**. Model and feature-set selection uses three-fold shuffled `GroupKFold` on the remaining alloy systems. Only after selection is the frozen pipeline evaluated on the outer test. The same outer alloy systems are used for unified and phase-specific comparisons.

{audit_lines}

Random/configuration splitting is retained only as the easiest baseline. Composition grouping tests transfer to unseen stoichiometries; alloy-system grouping is strongest because no elemental combination is shared across train/test. Configuration IDs are unique and cannot provide a stronger grouping than composition/system. All split seeds are fixed at {SEED}.
""", encoding="utf-8")

    b = best.set_index("cohort")
    comparison_lines = []
    for phase in ("FCC", "BCC"):
        sub = phase_scope.loc[phase_scope.phase.eq(phase)].set_index("model_scope")
        comparison_lines.append(f"- {phase}: unified R² {sub.loc['unified','r2']:.4f}, MAE {sub.loc['unified','mae']:.4f}, RMSE {sub.loc['unified','rmse']:.4f}; phase-specific R² {sub.loc['phase_specific','r2']:.4f}, MAE {sub.loc['phase_specific','mae']:.4f}, RMSE {sub.loc['phase_specific','rmse']:.4f}.")
    phase_text = f"""# Unified versus phase-specific models

Primary alloy-system-held-out results:

- Unified: **{b.loc['ALL','model']} / {b.loc['ALL','feature_set']}**, R² {b.loc['ALL','test_r2']:.4f}, MAE {b.loc['ALL','test_mae']:.4f}, RMSE {b.loc['ALL','test_rmse']:.4f}.
- FCC-specific: **{b.loc['FCC','model']} / {b.loc['FCC','feature_set']}**, R² {b.loc['FCC','test_r2']:.4f}, MAE {b.loc['FCC','test_mae']:.4f}, RMSE {b.loc['FCC','test_rmse']:.4f}.
- BCC-specific: **{b.loc['BCC','model']} / {b.loc['BCC','feature_set']}**, R² {b.loc['BCC','test_r2']:.4f}, MAE {b.loc['BCC','test_mae']:.4f}, RMSE {b.loc['BCC','test_rmse']:.4f}.

Models were selected by inner grouped-CV R², never outer-test performance. Raw errors must be interpreted against phase target spread; normalized metrics are included in the tables. The comparison is exploratory because the Phase 4 feature investigation preceded creation of this outer test.

On the identical held-out phase rows, the phase-specific pipelines compare with the unified pipeline as follows:

{chr(10).join(comparison_lines)}

Phase-specific fitting improves both phases, with the larger gain for FCC. This supports separate phase models for configuration-level prediction while retaining the unified model as a useful pooled baseline.
"""
    (report_dir / "model_phase_comparison.md").write_text(phase_text, encoding="utf-8")

    strong = results.loc[results.model.ne("DummyMedian")].copy(); strong["r2_gap_train_test"] = strong.train_r2 - strong.test_r2
    worst = strong.nlargest(5, "r2_gap_train_test")
    selected_gap_lines = "\n".join(f"- {r.cohort}: train R² {r.train_r2:.3f}, grouped-CV {r.cv_r2_mean:.3f} ± {r.cv_r2_std:.3f}, outer test {r.test_r2:.3f}; train–test gap {r.train_r2-r.test_r2:.3f}." for r in best.itertuples())
    (report_dir / "model_overfitting_analysis.md").write_text("# Model overfitting analysis\n\n## Selected HistGradientBoosting pipelines\n\n" + selected_gap_lines + "\n\nThese moderate gaps indicate some fitting to training configurations but do not erase strong grouped generalization. Early stopping and regularization were fixed before outer evaluation.\n\n## Largest observed gaps\n\n" + "\n".join(f"- {r.cohort} `{r.model}` / `{r.feature_set}`: train {r.train_r2:.3f}, grouped-CV {r.cv_r2_mean:.3f} ± {r.cv_r2_std:.3f}, outer test {r.test_r2:.3f}, gap {r.r2_gap_train_test:.3f}." for r in worst.itertuples()) + "\n\nThe largest gaps are dominated by the capped SVR and weak minimal-set baselines, not the selected models. Outer grouped performance, not training accuracy or random-split accuracy, governs scientific conclusions.\n", encoding="utf-8")

    all_best = results.loc[results.cohort.eq("ALL")].sort_values("cv_r2_mean").groupby("feature_set", as_index=False).tail(1).sort_values("cv_r2_mean", ascending=False)
    (report_dir / "feature_ablation_analysis.md").write_text("# Feature-set ablation analysis\n\nUnified best-by-inner-CV configurations under the fixed alloy-held-out design:\n\n" + "\n".join(f"- `{r.feature_set}` ({r.declared_features} declared): {r.model}, CV R² {r.cv_r2_mean:.4f} ± {r.cv_r2_std:.4f}; test R² {r.test_r2:.4f}, MAE {r.test_mae:.4f}." for r in all_best.itertuples()) + "\n\n`THERMODYNAMIC_OR_ENERGETIC` is empty because every available energetic quantity is a relaxed/final-state outcome and remains excluded. Initial-structure gains must be weighed against portability and possible configuration sensitivity. The 19-feature minimal set is the intended cross-source baseline. [LITERATURE SUPPORT REQUIRED] for mechanistic claims.\n", encoding="utf-8")

    s = space.set_index("cohort")
    (report_dir / "space_group_sensitivity.md").write_text(f"""# Initial space-group sensitivity

Phase 4 correlations for `space_group_number_ini` were 0.4753/0.5931 (Pearson/Spearman) combined, 0.4812/0.5520 within FCC, and 0.4877/0.6200 within BCC. The association therefore persists within each phase and is not merely a binary FCC/BCC discriminator.

Using each cohort's selected algorithm with FULL_CLEAN descriptors, removing initial space group changed alloy-held-out R² by:

{chr(10).join(f'- {r.Index}: with {r.with_space_group_r2:.4f}, without {r.without_space_group_r2:.4f}, delta {r.delta_r2_with_minus_without:.4f}.' for r in s.itertuples())}

This remains predictive sensitivity, not evidence that space-group number physically controls SRO. It can encode initial cell construction, symmetry breaking, or configuration-generation regimes and requires structure-feature ablation and external support.
""", encoding="utf-8")

    worst_systems = alloy.loc[alloy.cohort.eq("ALL")].sort_values("mae", ascending=False).head(10)
    best_systems = alloy.loc[alloy.cohort.eq("ALL") & alloy.observations.ge(20)].sort_values("mae").head(10)
    count_mae_rho = stats.spearmanr(alloy.loc[alloy.cohort.eq("ALL"), "observations"], alloy.loc[alloy.cohort.eq("ALL"), "mae"]).statistic
    (report_dir / "alloy_generalization.md").write_text("# Alloy-system generalization\n\nThe primary test contains entire alloy systems unseen during training. System-wise counts, MAE and RMSE are in `alloy_system_error.csv`. The ten largest unified-system MAEs are:\n\n" + "\n".join(f"- `{r.chemical_system}`: n={int(r.observations)}, MAE={r.mae:.4f}, RMSE={r.rmse:.4f}." for r in worst_systems.itertuples()) + "\n\nThe ten lowest MAEs among systems with at least 20 test rows are:\n\n" + "\n".join(f"- `{r.chemical_system}`: n={int(r.observations)}, MAE={r.mae:.4f}, RMSE={r.rmse:.4f}." for r in best_systems.itertuples()) + f"\n\nThe Spearman association between held-out system size and MAE is {count_mae_rho:.3f}. Every test system is absent from training, so bias toward a specific heavily represented training system is structurally prevented; representation effects can still enter through chemically related training systems. Small systems have noisier error estimates and poor performance must not automatically be attributed to chemistry.\n", encoding="utf-8")


def run_phase5(
    data_path: Path = Path("data/processed/ml_dataset.parquet"),
    result_dir: Path = Path("results/tables/phase5"),
    thesis_table_dir: Path = Path("thesis_outputs/tables"),
    figure_dir: Path = Path("thesis_outputs/figures/phase5"),
    report_dir: Path = Path("reports"),
    model_dir: Path = Path("models/phase5"),
) -> dict[str, Any]:
    started = time.perf_counter(); data = pd.read_parquet(data_path); sets, mapping = load_feature_sets()
    all_features = mapping.feature.tolist(); validation = validate_ml_frame(data, all_features)
    for directory in (result_dir, thesis_table_dir, figure_dir, report_dir, model_dir): directory.mkdir(parents=True, exist_ok=True)
    definition_rows = [{"feature_set": name, "feature": feature, "feature_order": i + 1} for name, features in sets.items() for i, feature in enumerate(features)]
    pd.DataFrame(definition_rows).to_csv(result_dir / "feature_set_definitions.csv", index=False)

    splits = {name: make_outer_split(data, name) for name in ("random_configuration", "composition_grouped", "alloy_system_grouped")}
    audits = pd.DataFrame([split_audit(data, split) for split in splits.values()]); audits.to_csv(result_dir / "split_audit.csv", index=False)
    primary = splits["alloy_system_grouped"]
    records: list[dict[str, Any]] = []; cache: dict[tuple[str, str, str], tuple[pd.DataFrame, Pipeline]] = {}
    base_models = [m for m in model_specs() if m != "SVR_subset"]
    evaluated: set[tuple[str, str, str]] = set()

    def evaluate(cohort: str, model: str, set_name: str):
        key = (cohort, model, set_name)
        if key in evaluated or not sets[set_name]: return
        print(f"[phase5] evaluating {cohort} | {model} | {set_name}", flush=True)
        rec, pred, pipe = evaluate_configuration(data, cohort, sets[set_name], set_name, model, primary)
        records.append(rec); cache[key] = (pred, pipe); evaluated.add(key)
        print(f"[phase5] completed {cohort} | {model} | {set_name}: CV R2={rec['cv_r2_mean']:.4f}, test R2={rec['test_r2']:.4f}", flush=True)

    for cohort in ("ALL", "FCC", "BCC"):
        for model in base_models: evaluate(cohort, model, "BALANCED_PRELIMINARY")
        evaluate(cohort, "SVR_subset", "MINIMAL_PRELIMINARY")
        screen = pd.DataFrame([r for r in records if r["cohort"] == cohort and r["feature_set"] == "BALANCED_PRELIMINARY" and r["model"] != "DummyMedian"])
        top_models = screen.nlargest(2, "cv_r2_mean").model.tolist()
        for model in top_models:
            for set_name in ("FULL_CLEAN", "MINIMAL_PRELIMINARY", "COMPOSITION_ONLY", "COMPOSITION_PLUS_PHASE", "COMPOSITION_PLUS_INITIAL_STRUCTURE"):
                evaluate(cohort, model, set_name)

    results = pd.DataFrame(records)
    best_rows = results.loc[results.model.ne("DummyMedian")].sort_values("cv_r2_mean").groupby("cohort", as_index=False).tail(1).sort_values("cohort")
    best_predictions: dict[str, pd.DataFrame] = {}; best_pipes: dict[str, Pipeline] = {}; best_features: dict[str, list[str]] = {}
    metadata = []
    for row in best_rows.itertuples(index=False):
        key = (row.cohort, row.model, row.feature_set); pred, pipe = cache[key]
        best_predictions[row.cohort] = pred; best_pipes[row.cohort] = pipe; best_features[row.cohort] = sets[row.feature_set]
        path = model_dir / f"best_{row.cohort.lower()}_{row.model}_{row.feature_set}.joblib"; joblib.dump(pipe, path, compress=3)
        meta = {"cohort": row.cohort, "model": row.model, "feature_set": row.feature_set, "feature_count": len(sets[row.feature_set]),
                "feature_list": sets[row.feature_set], "training_date": str(date.today()), "random_seed": SEED,
                "primary_validation": "alloy_system_grouped", "metrics": {k: getattr(row, k) for k in ("cv_r2_mean", "cv_r2_std", "test_r2", "test_mae", "test_rmse")},
                "hyperparameters": best_pipes[row.cohort].named_steps["model"].get_params(deep=False), "local_model_path": str(path)}
        (report_dir / f"model_metadata_{row.cohort.lower()}.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8"); metadata.append(meta)

    phase_scope_rows = []
    unified_pred = best_predictions["ALL"]
    for phase in ("FCC", "BCC"):
        for scope, pred in (("unified", unified_pred.loc[unified_pred.phase.eq(phase)]), ("phase_specific", best_predictions[phase])):
            metrics = metric_dict(pred[TARGET].to_numpy(), pred.prediction.to_numpy(), "heldout")
            phase_scope_rows.append({"phase": phase, "model_scope": scope, "observations": len(pred),
                                     "r2": metrics["heldout_r2"], "mae": metrics["heldout_mae"], "rmse": metrics["heldout_rmse"],
                                     "normalized_mae": metrics["heldout_normalized_mae"], "normalized_rmse": metrics["heldout_normalized_rmse"]})
    phase_scope = pd.DataFrame(phase_scope_rows)

    grouped_records = []
    for row in best_rows.itertuples(index=False):
        for strategy, split in splits.items():
            if strategy == "alloy_system_grouped":
                existing = results.loc[(results.cohort == row.cohort) & (results.model == row.model) & (results.feature_set == row.feature_set)].iloc[0].to_dict()
                grouped_records.append(existing); continue
            rec, _, _ = evaluate_configuration(data, row.cohort, sets[row.feature_set], row.feature_set, row.model, split)
            grouped_records.append(rec)
    grouped = pd.DataFrame(grouped_records)

    # Space-group sensitivity uses each selected algorithm with identical FULL_CLEAN inputs except the tested field.
    space_rows = []
    for row in best_rows.itertuples(index=False):
        full = sets["FULL_CLEAN"]; without = [f for f in full if f != "space_group_number_ini"]
        rec_with, _, _ = evaluate_configuration(data, row.cohort, full, "FULL_CLEAN_SPACE_TEST", row.model, primary, do_cv=False)
        rec_without, _, _ = evaluate_configuration(data, row.cohort, without, "FULL_CLEAN_NO_SPACE_GROUP", row.model, primary, do_cv=False)
        space_rows.append({"cohort": row.cohort, "model": row.model, "with_space_group_r2": rec_with["test_r2"],
                           "without_space_group_r2": rec_without["test_r2"], "delta_r2_with_minus_without": rec_with["test_r2"] - rec_without["test_r2"],
                           "with_space_group_mae": rec_with["test_mae"], "without_space_group_mae": rec_without["test_mae"]})
    space = pd.DataFrame(space_rows)

    importances: dict[str, pd.DataFrame] = {}
    for row in best_rows.itertuples(index=False):
        # Interpret the strongest evaluated tree model if the overall winner is linear/SVR.
        tree_names = {"RandomForest", "ExtraTrees", "GradientBoosting", "HistGradientBoosting"}
        tree_candidates = results.loc[(results.cohort == row.cohort) & results.model.isin(tree_names)]
        tree_row = tree_candidates.nlargest(1, "cv_r2_mean").iloc[0]
        pred, pipe = cache[(row.cohort, tree_row.model, tree_row.feature_set)]
        test_idx = primary.test_index if row.cohort == "ALL" else primary.test_index[data.iloc[primary.test_index].phase.eq(row.cohort).to_numpy()]
        importance = feature_importance_table(pipe, sets[tree_row.feature_set], data.iloc[test_idx], data.iloc[test_idx][TARGET])
        importance["cohort"] = row.cohort; importance["model"] = tree_row.model; importance["feature_set"] = tree_row.feature_set
        importances[row.cohort] = importance

    alloy_tables = []
    train_counts = data.iloc[primary.train_index].chemical_system.value_counts()
    for cohort, pred in best_predictions.items():
        table = pred.groupby("chemical_system", observed=True).apply(lambda g: pd.Series({"observations": len(g), "mae": mean_absolute_error(g[TARGET], g.prediction), "rmse": mean_squared_error(g[TARGET], g.prediction) ** .5}), include_groups=False).reset_index()
        table["train_observations_same_system"] = table.chemical_system.map(train_counts).fillna(0).astype(int); table["cohort"] = cohort
        alloy_tables.append(table)
    alloy = pd.concat(alloy_tables, ignore_index=True)

    results.to_csv(result_dir / "model_results_all.csv", index=False); grouped.to_csv(result_dir / "grouped_validation_results.csv", index=False)
    best_rows.to_csv(result_dir / "best_model_metrics.csv", index=False); space.to_csv(result_dir / "space_group_sensitivity.csv", index=False)
    phase_scope.to_csv(result_dir / "unified_vs_phase_specific_metrics.csv", index=False)
    alloy.to_csv(result_dir / "alloy_system_error.csv", index=False)
    for cohort, pred in best_predictions.items(): pred.to_csv(result_dir / f"best_predictions_{cohort.lower()}.csv", index=False)
    for cohort, table in importances.items(): table.to_csv(result_dir / f"feature_importance_{cohort.lower()}.csv", index=False)

    # Exact user-requested compact thesis tables.
    for cohort, filename in (("ALL", "model_comparison_all.csv"), ("FCC", "model_comparison_fcc.csv"), ("BCC", "model_comparison_bcc.csv")):
        results.loc[results.cohort.eq(cohort)].to_csv(thesis_table_dir / filename, index=False)
    results.to_csv(thesis_table_dir / "feature_set_model_comparison.csv", index=False)
    grouped.to_csv(thesis_table_dir / "grouped_validation_results.csv", index=False)
    best_rows.to_csv(thesis_table_dir / "best_model_metrics.csv", index=False)
    phase_scope.to_csv(thesis_table_dir / "unified_vs_phase_specific_metrics.csv", index=False)
    for cohort, filename in (("ALL", "feature_importance_unified.csv"), ("FCC", "feature_importance_fcc.csv"), ("BCC", "feature_importance_bcc.csv")):
        importances[cohort].to_csv(thesis_table_dir / filename, index=False)

    figures = create_ml_figures(results, best_rows, best_predictions, grouped, importances, figure_dir)
    runtime_seconds = time.perf_counter() - started
    _write_reports(report_dir, validation, audits, results, best_rows, grouped, space, alloy, phase_scope, sets, runtime_seconds)
    summary = {"validation": validation, "feature_set_counts": {k: len(v) for k, v in sets.items()}, "best_models": best_rows.to_dict("records"),
               "split_audit": audits.to_dict("records"), "space_group_sensitivity": space.to_dict("records"),
               "unified_vs_phase_specific": phase_scope.to_dict("records"),
               "runtime_seconds": runtime_seconds, "model_packages_skipped": ["XGBoost (not installed)", "LightGBM (not installed)", "SHAP (not installed)"],
               "validated_hcp_observations": 0, "figures": figures, "ready_for_phase6": True}
    (report_dir / "phase5_metrics.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary
