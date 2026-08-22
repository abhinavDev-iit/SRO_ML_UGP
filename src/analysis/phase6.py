"""Phase 6 robustness, compact refinement and final scientific audits."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.inspection import PartialDependenceDisplay, permutation_importance
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from src.ml.phase5 import (
    SEED, TARGET, build_pipeline, evaluate_configuration, load_feature_sets,
    make_outer_split, metric_dict, model_specs, validate_ml_frame,
)


ROBUSTNESS_SEEDS = (7, 19, 42, 73, 101)
COMPACT_SIZES = (10, 20, 30, 50, 75, 100, 150, 198)


def coarse_feature_group(feature_group: str) -> str:
    if feature_group.startswith("composition"):
        return "composition"
    if feature_group == "configurational entropy":
        return "configurational_entropy"
    if feature_group == "atomic size":
        return "atomic_size"
    if feature_group == "electronegativity / ionic":
        return "electronegativity"
    if feature_group in {"valence / VEC", "atomic number", "periodic-table position", "elemental electronic proxy"}:
        return "electronic_VEC_periodic"
    if feature_group in {"atomic mass", "melting point", "elemental magnetic proxy"}:
        return "elemental_thermophysical"
    if feature_group == "initial structural geometry":
        return "structural_geometry"
    if feature_group == "initial symmetry":
        return "symmetry"
    if feature_group == "phase metadata":
        return "phase_metadata"
    return "other"


def transferability_class(row: pd.Series) -> str:
    high_risk_terms = (
        "space_group_number_ini", "NIONS", "packing efficiency",
        "neighbor distance variation", "relative cell size", "SpaceGroupNumber",
    )
    if any(term in row["feature"] for term in high_risk_terms):
        return "D_POTENTIAL_CONFIGURATION_ENCODING"
    if row["availability_class"] == "initial-structure-dependent":
        return "B_STRUCTURE_DERIVABLE"
    if row["availability_class"] in {"composition-universal", "composition-plus-elemental-reference", "phase-label-dependent"}:
        return "A_UNIVERSALLY_DERIVABLE"
    return "C_SOURCE_METHOD_SPECIFIC"


def _hist_pipeline():
    estimator, scale = model_specs()["HistGradientBoosting"]
    return build_pipeline(estimator, scale)


def repeated_robustness(data: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, predictions = [], []
    for seed in ROBUSTNESS_SEEDS:
        split = make_outer_split(data, "alloy_system_grouped", seed=seed)
        for cohort in ("ALL", "FCC", "BCC"):
            print(f"[phase6] robustness seed={seed} cohort={cohort}", flush=True)
            record, pred, _ = evaluate_configuration(data, cohort, features, "BALANCED", "HistGradientBoosting", split, do_cv=False)
            rows.append({"seed": seed, **record})
            pred["seed"] = seed; predictions.append(pred)
    detail = pd.DataFrame(rows)
    summary = detail.groupby("cohort", as_index=False).agg(
        seeds=("seed", "nunique"), mean_r2=("test_r2", "mean"), std_r2=("test_r2", "std"),
        min_r2=("test_r2", "min"), max_r2=("test_r2", "max"), mean_mae=("test_mae", "mean"),
        std_mae=("test_mae", "std"), mean_rmse=("test_rmse", "mean"), std_rmse=("test_rmse", "std"),
    )
    return detail, summary


def _rank_features_on_training_only(data: pd.DataFrame, fold_train: np.ndarray, features: list[str], seed: int) -> pd.DataFrame:
    groups = data.iloc[fold_train].chemical_system.to_numpy()
    inner_train_local, rank_val_local = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed).split(fold_train, groups=groups))
    rank_train = fold_train[inner_train_local]; rank_val = fold_train[rank_val_local]
    pipe = _hist_pipeline(); pipe.fit(data.iloc[rank_train][features], data.iloc[rank_train][TARGET])
    sample = data.iloc[rank_val].sample(min(2_000, len(rank_val)), random_state=seed)
    importance = permutation_importance(pipe, sample[features], sample[TARGET], scoring="neg_mean_absolute_error", n_repeats=2, random_state=seed, n_jobs=-1)
    result = pd.DataFrame({"feature": features, "importance": importance.importances_mean})
    result["rank"] = result.importance.rank(method="average", ascending=False)
    return result.sort_values("rank")


def nested_compact_selection(data: pd.DataFrame, outer_train: np.ndarray, features: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, int, list[str]]:
    groups = data.iloc[outer_train].chemical_system.to_numpy()
    cv = GroupKFold(n_splits=3, shuffle=True, random_state=SEED)
    performance_rows, ranking_rows = [], []
    for fold, (train_local, val_local) in enumerate(cv.split(outer_train, groups=groups), 1):
        fold_train, fold_val = outer_train[train_local], outer_train[val_local]
        ranking = _rank_features_on_training_only(data, fold_train, features, seed=SEED + fold)
        ranking["fold"] = fold; ranking_rows.append(ranking)
        ordered = ranking.feature.tolist()
        for size in COMPACT_SIZES:
            chosen = ordered[:min(size, len(ordered))]
            pipe = _hist_pipeline(); pipe.fit(data.iloc[fold_train][chosen], data.iloc[fold_train][TARGET])
            pred = pipe.predict(data.iloc[fold_val][chosen]); y = data.iloc[fold_val][TARGET].to_numpy()
            performance_rows.append({"fold": fold, "feature_count": len(chosen), "r2": r2_score(y, pred),
                                     "mae": mean_absolute_error(y, pred), "rmse": mean_squared_error(y, pred) ** .5})
            print(f"[phase6] compact fold={fold} size={size} r2={performance_rows[-1]['r2']:.4f}", flush=True)
    rankings = pd.concat(ranking_rows, ignore_index=True)
    stable = rankings.groupby("feature", as_index=False).agg(mean_rank=("rank", "mean"), std_rank=("rank", "std"), mean_importance=("importance", "mean"), folds=("fold", "nunique")).sort_values(["mean_rank", "mean_importance"], ascending=[True, False])
    perf = pd.DataFrame(performance_rows).groupby("feature_count", as_index=False).agg(
        mean_cv_r2=("r2", "mean"), std_cv_r2=("r2", "std"), mean_cv_mae=("mae", "mean"), std_cv_mae=("mae", "std"), mean_cv_rmse=("rmse", "mean"), std_cv_rmse=("rmse", "std"),
    )
    baseline = float(perf.loc[perf.feature_count.eq(max(COMPACT_SIZES)), "mean_cv_r2"].iloc[0])
    threshold = max(0.95 * baseline, baseline - 0.03)
    eligible = perf.loc[perf.mean_cv_r2.ge(threshold)]
    chosen_size = int(eligible.feature_count.min()) if len(eligible) else int(perf.loc[perf.mean_cv_r2.idxmax(), "feature_count"])
    compact = stable.feature.head(chosen_size).tolist()
    perf["balanced_cv_r2"] = baseline; perf["acceptance_threshold"] = threshold; perf["selected"] = perf.feature_count.eq(chosen_size)
    return perf, stable, chosen_size, compact


def evaluate_compact_once(data: pd.DataFrame, compact: list[str]) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    split = make_outer_split(data, "alloy_system_grouped", seed=SEED); rows, preds = [], {}
    for cohort in ("ALL", "FCC", "BCC"):
        record, pred, _ = evaluate_configuration(data, cohort, compact, "COMPACT_HIGH_PERFORMANCE", "HistGradientBoosting", split, do_cv=False)
        rows.append(record); preds[cohort] = pred
    return pd.DataFrame(rows), preds


def group_ablation(data: pd.DataFrame, outer_train: np.ndarray, balanced: list[str], mapping: pd.DataFrame) -> pd.DataFrame:
    map_index = mapping.set_index("feature"); feature_groups = {f: coarse_feature_group(map_index.loc[f, "feature_group"]) for f in balanced}
    rows = []
    for cohort in ("ALL", "FCC", "BCC"):
        cohort_train = outer_train if cohort == "ALL" else outer_train[data.iloc[outer_train].phase.eq(cohort).to_numpy()]
        groups = data.iloc[cohort_train].chemical_system.to_numpy(); cv = GroupKFold(n_splits=3, shuffle=True, random_state=SEED)
        cohort_rows = []
        for removed in ["NONE_BASELINE", *sorted(set(feature_groups.values()))]:
            chosen = balanced if removed == "NONE_BASELINE" else [f for f in balanced if feature_groups[f] != removed]
            fold_metrics = []
            for train_local, val_local in cv.split(cohort_train, groups=groups):
                tr, va = cohort_train[train_local], cohort_train[val_local]; pipe = _hist_pipeline()
                pipe.fit(data.iloc[tr][chosen], data.iloc[tr][TARGET]); pred = pipe.predict(data.iloc[va][chosen]); y = data.iloc[va][TARGET]
                fold_metrics.append((r2_score(y, pred), mean_absolute_error(y, pred), mean_squared_error(y, pred) ** .5))
            arr = np.asarray(fold_metrics); cohort_rows.append({"cohort": cohort, "removed_group": removed, "removed_features": 0 if removed == "NONE_BASELINE" else sum(v == removed for v in feature_groups.values()),
                                                            "retained_features": len(chosen), "mean_cv_r2": arr[:, 0].mean(), "std_cv_r2": arr[:, 0].std(ddof=1),
                                                            "mean_cv_mae": arr[:, 1].mean(), "std_cv_mae": arr[:, 1].std(ddof=1), "mean_cv_rmse": arr[:, 2].mean()})
            print(f"[phase6] group ablation cohort={cohort} {removed}: r2={cohort_rows[-1]['mean_cv_r2']:.4f}", flush=True)
        baseline = next(row for row in cohort_rows if row["removed_group"] == "NONE_BASELINE")
        for row in cohort_rows:
            row["delta_r2_vs_baseline"] = row["mean_cv_r2"] - baseline["mean_cv_r2"]
            row["delta_mae_vs_baseline"] = row["mean_cv_mae"] - baseline["mean_cv_mae"]
        rows.extend(cohort_rows)
    return pd.DataFrame(rows).sort_values(["cohort", "delta_r2_vs_baseline"])


def configuration_sensitivity(data: pd.DataFrame, balanced: list[str], mapping: pd.DataFrame) -> pd.DataFrame:
    split = make_outer_split(data, "alloy_system_grouped", seed=SEED); map_index = mapping.set_index("feature")
    structural = [f for f in balanced if coarse_feature_group(map_index.loc[f, "feature_group"]) == "structural_geometry"]
    symmetry = [f for f in balanced if coarse_feature_group(map_index.loc[f, "feature_group"]) == "symmetry"]
    tests = {
        "remove_space_group_number_ini": [f for f in balanced if f != "space_group_number_ini"],
        "remove_max_packing_efficiency": [f for f in balanced if f != "max packing efficiency"],
        "remove_range_neighbor_distance_variation": [f for f in balanced if f != "range neighbor distance variation"],
        "remove_structural_geometry_group": [f for f in balanced if f not in structural],
        "remove_symmetry_group": [f for f in balanced if f not in symmetry],
    }
    rows = []
    for cohort in ("ALL", "FCC", "BCC"):
        baseline, _, _ = evaluate_configuration(data, cohort, balanced, "BALANCED", "HistGradientBoosting", split, do_cv=False)
        for name, features in tests.items():
            record, _, _ = evaluate_configuration(data, cohort, features, name, "HistGradientBoosting", split, do_cv=False)
            rows.append({"cohort": cohort, "sensitivity_test": name, "removed_features": len(balanced) - len(features),
                         "baseline_r2": baseline["test_r2"], "test_r2": record["test_r2"], "delta_r2": record["test_r2"] - baseline["test_r2"],
                         "baseline_mae": baseline["test_mae"], "test_mae": record["test_mae"], "delta_mae": record["test_mae"] - baseline["test_mae"]})
    return pd.DataFrame(rows)


def error_and_extrapolation(data: pd.DataFrame, compact: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, float]]:
    split = make_outer_split(data, "alloy_system_grouped", seed=SEED)
    pred = pd.read_csv("results/tables/phase5/best_predictions_all.csv")
    joined = pred.merge(data[["fid", "number_of_elements", *compact]], on="fid", validate="one_to_one")
    joined["absolute_error"] = joined.residual.abs(); joined["high_error"] = joined.absolute_error.ge(joined.absolute_error.quantile(.95))
    train = data.iloc[split.train_index]; test = data.iloc[split.test_index]
    range_rows = []
    for feature in compact:
        tr, te = train[feature], test[feature]
        range_rows.append({"feature": feature, "train_min": tr.min(), "train_max": tr.max(), "train_p01": tr.quantile(.01), "train_p99": tr.quantile(.99),
                           "test_min": te.min(), "test_max": te.max(), "outside_train_range_fraction": float(((te < tr.min()) | (te > tr.max())).mean()),
                           "outside_train_p01_p99_fraction": float(((te < tr.quantile(.01)) | (te > tr.quantile(.99))).mean())})
    extrap = pd.DataFrame(range_rows).sort_values("outside_train_p01_p99_fraction", ascending=False)
    top_nn = compact[:min(10, len(compact))]; scaler = StandardScaler().fit(train[top_nn]); rng = np.random.default_rng(SEED)
    train_sample = rng.choice(len(train), min(20_000, len(train)), replace=False)
    nn = NearestNeighbors(n_neighbors=1, n_jobs=-1).fit(scaler.transform(train.iloc[train_sample][top_nn]))
    distance = nn.kneighbors(scaler.transform(test[top_nn]), return_distance=True)[0][:, 0]
    distance_map = dict(zip(test.fid, distance)); joined["nearest_training_distance"] = joined.fid.map(distance_map)
    outside_counts = np.zeros(len(test), dtype=int)
    for feature in compact:
        outside_counts += ((test[feature] < train[feature].min()) | (test[feature] > train[feature].max())).to_numpy()
    joined["outside_training_range_feature_count"] = joined.fid.map(dict(zip(test.fid, outside_counts)))
    joined["target_bin"] = pd.qcut(joined[TARGET].rank(method="first"), 10, labels=False)
    summary = pd.concat([
        joined.groupby("phase", observed=True).agg(observations=("fid", "size"), mae=("absolute_error", "mean"), high_error_fraction=("high_error", "mean")).assign(group_type="phase").reset_index(names="group_value"),
        joined.groupby("number_of_elements", observed=True).agg(observations=("fid", "size"), mae=("absolute_error", "mean"), high_error_fraction=("high_error", "mean")).assign(group_type="number_of_elements").reset_index(names="group_value"),
        joined.groupby("target_bin", observed=True).agg(observations=("fid", "size"), mae=("absolute_error", "mean"), high_error_fraction=("high_error", "mean")).assign(group_type="target_decile").reset_index(names="group_value"),
    ], ignore_index=True)
    diagnostics = {"spearman_abs_error_vs_nn_distance": float(stats.spearmanr(joined.absolute_error, joined.nearest_training_distance).statistic),
                   "spearman_abs_error_vs_target": float(stats.spearmanr(joined.absolute_error, joined[TARGET]).statistic),
                   "high_error_threshold": float(joined.absolute_error.quantile(.95)), "high_error_rows": int(joined.high_error.sum())}
    high = joined.nlargest(250, "absolute_error")
    return high, summary, extrap, diagnostics


def _save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")


def create_phase6_figures(robust: pd.DataFrame, compact_perf: pd.DataFrame, ablation: pd.DataFrame, sensitivity: pd.DataFrame,
                          error_summary: pd.DataFrame, extrap: pd.DataFrame, data: pd.DataFrame, balanced: list[str], output_dir: Path) -> list[str]:
    os.environ.setdefault("MPLBACKEND", "Agg"); os.environ.setdefault("MPLCONFIGDIR", str(Path(".cache/matplotlib").resolve()))
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 11, "savefig.dpi": 300}); outputs=[]
    fig, ax = plt.subplots(figsize=(6.7, 4.3))
    for i, (cohort, color) in enumerate((("ALL", "#6B7280"), ("FCC", "#2878B5"), ("BCC", "#D95319"))):
        sub=robust[robust.cohort.eq(cohort)]; ax.scatter(np.full(len(sub),i)+np.linspace(-.08,.08,len(sub)),sub.test_r2,color=color,s=35); ax.errorbar(i,sub.test_r2.mean(),yerr=sub.test_r2.std(ddof=1),fmt="o",color="black",capsize=5)
    ax.set_xticks(range(3),["Unified","FCC","BCC"]); ax.set(ylabel="Alloy-held-out R²",title="Robustness across five deterministic alloy splits"); ax.spines[["top","right"]].set_visible(False); p=output_dir/"model_robustness.png"; _save(fig,p); plt.close(fig); outputs.append(str(p))
    fig,ax=plt.subplots(figsize=(6.5,4.2)); ax.errorbar(compact_perf.feature_count,compact_perf.mean_cv_r2,yerr=compact_perf.std_cv_r2,marker="o",capsize=3); selected=compact_perf[compact_perf.selected].iloc[0]; ax.axhline(selected.acceptance_threshold,ls="--",color="#E15759",label="Acceptance threshold"); ax.scatter([selected.feature_count],[selected.mean_cv_r2],s=90,color="#59A14F",zorder=3,label="Selected"); ax.set(xlabel="Predictor count",ylabel="Nested grouped-CV R²",title="Training-only compact feature refinement"); ax.legend(frameon=False); ax.spines[["top","right"]].set_visible(False); p=output_dir/"compact_feature_refinement.png"; _save(fig,p); plt.close(fig); outputs.append(str(p))
    shown=ablation[ablation.cohort.eq("ALL") & ~ablation.removed_group.eq("NONE_BASELINE")].sort_values("delta_r2_vs_baseline"); fig,ax=plt.subplots(figsize=(7.3,4.8)); ax.barh(shown.removed_group,shown.delta_r2_vs_baseline,color=["#E15759" if x<0 else "#59A14F" for x in shown.delta_r2_vs_baseline]); ax.axvline(0,color="#222",lw=1); ax.set(xlabel="Δ grouped-CV R² after group removal",title="Unified feature-group ablation"); ax.spines[["top","right"]].set_visible(False); p=output_dir/"feature_group_ablation.png"; _save(fig,p); plt.close(fig); outputs.append(str(p))
    shown=sensitivity[sensitivity.cohort.eq("ALL")].sort_values("delta_r2"); fig,ax=plt.subplots(figsize=(7.2,4.2)); ax.barh(shown.sensitivity_test,shown.delta_r2,color="#E15759"); ax.set(xlabel="Δ outer R² after removal",title="Configuration-descriptor sensitivity"); ax.spines[["top","right"]].set_visible(False); p=output_dir/"configuration_descriptor_sensitivity.png"; _save(fig,p); plt.close(fig); outputs.append(str(p))
    target=error_summary[error_summary.group_type.eq("target_decile")]; fig,ax=plt.subplots(figsize=(6.3,4.0)); ax.plot(target.group_value.astype(int)+1,target.mae,marker="o",color="#4C78A8"); ax.set(xlabel="Observed-target decile",ylabel="MAE",title="Error across the target distribution"); ax.spines[["top","right"]].set_visible(False); p=output_dir/"error_by_target_decile.png"; _save(fig,p); plt.close(fig); outputs.append(str(p))
    shown=extrap.head(15).sort_values("outside_train_p01_p99_fraction"); fig,ax=plt.subplots(figsize=(7.3,5.0)); ax.barh(shown.feature,100*shown.outside_train_p01_p99_fraction,color="#F28E2B"); ax.set(xlabel="Test rows outside training 1st–99th percentile (%)",title="Descriptor-distribution extrapolation screen"); ax.spines[["top","right"]].set_visible(False); p=output_dir/"extrapolation_feature_ranges.png"; _save(fig,p); plt.close(fig); outputs.append(str(p))
    target_stats=pd.read_csv("results/tables/phase4/target_statistics.csv").set_index("cohort"); best=pd.read_csv("results/tables/phase5/best_model_metrics.csv").set_index("cohort"); fig,axes=plt.subplots(1,2,figsize=(8.5,3.8)); axes[0].bar(["FCC","BCC"],target_stats.loc[["FCC","BCC"],"mean"],color=["#2878B5","#D95319"]); axes[0].set(ylabel="Mean SRO magnitude",title="Target contrast"); axes[1].bar(["FCC","BCC"],best.loc[["FCC","BCC"],"test_r2"],color=["#2878B5","#D95319"]); axes[1].set(ylabel="Alloy-held-out R²",title="Phase-specific predictability",ylim=(0.8,1)); [a.spines[["top","right"]].set_visible(False) for a in axes]; p=output_dir/"fcc_bcc_final_comparison.png"; _save(fig,p); plt.close(fig); outputs.append(str(p))
    model=joblib.load("models/phase5/best_all_HistGradientBoosting_BALANCED_PRELIMINARY.joblib"); sample=data.sample(min(5_000,len(data)),random_state=SEED); pdp_features=[f for f in ["configurational_entropy_j_mol_k","max packing efficiency","NIONS","range neighbor distance variation"] if f in balanced]; fig,axes=plt.subplots(2,2,figsize=(9,6.8)); PartialDependenceDisplay.from_estimator(model,sample[balanced].astype(float),pdp_features,ax=axes,kind="average",grid_resolution=25); fig.suptitle("Focused partial dependence (descriptive, not causal)",y=1.02); p=output_dir/"focused_partial_dependence.png"; _save(fig,p); plt.close(fig); outputs.append(str(p))
    return outputs


def _write_feature_lists(output_dir: Path, full: list[str], balanced: list[str], compact: list[str], minimal: list[str]) -> None:
    output_dir.mkdir(parents=True,exist_ok=True)
    for name,features in (("full",full),("balanced",balanced),("compact_high_performance",compact),("minimal_common",minimal)):
        (output_dir/f"{name}.txt").write_text("\n".join(features)+"\n",encoding="utf-8")


def run_phase6(data_path: Path=Path("data/processed/ml_dataset.parquet")) -> dict[str,Any]:
    started=time.perf_counter(); data=pd.read_parquet(data_path); sets,mapping=load_feature_sets(); validate_ml_frame(data,mapping.feature.tolist())
    balanced=sets["BALANCED_PRELIMINARY"]; full=sets["FULL_CLEAN"]; outer=make_outer_split(data,"alloy_system_grouped",seed=SEED)
    output=Path("results/tables/phase6"); thesis=Path("thesis_outputs/tables"); figures=Path("thesis_outputs/figures"); reports=Path("reports")
    for d in (output,thesis,figures,reports): d.mkdir(parents=True,exist_ok=True)
    robust_detail,robust_summary=repeated_robustness(data,balanced)
    compact_perf,stable_rank,compact_size,compact=nested_compact_selection(data,outer.train_index,balanced)
    compact_metrics,compact_predictions=evaluate_compact_once(data,compact)
    mapping=mapping.copy(); mapping["coarse_group"]=mapping.feature_group.map(coarse_feature_group); mapping["transferability_class"]=mapping.apply(transferability_class,axis=1)
    ablation=group_ablation(data,outer.train_index,balanced,mapping); sensitivity=configuration_sensitivity(data,balanced,mapping)
    high_errors,error_summary,extrap,diagnostics=error_and_extrapolation(data,compact)
    minimal=[f for f in sets["MINIMAL_PRELIMINARY"] if f!="phase_FCC"]
    _write_feature_lists(Path("results/feature_sets"),full,balanced,compact,minimal)
    robust_detail.to_csv(output/"model_robustness_detail.csv",index=False); robust_summary.to_csv(thesis/"model_robustness_summary.csv",index=False)
    compact_perf.to_csv(output/"compact_feature_count_validation.csv",index=False); stable_rank.to_csv(output/"training_only_stable_feature_ranking.csv",index=False); compact_metrics.to_csv(output/"compact_outer_test_metrics.csv",index=False)
    for cohort, predictions in compact_predictions.items():
        predictions.to_csv(output/f"compact_outer_predictions_{cohort.lower()}.csv", index=False)
    mapping.to_csv(output/"feature_transferability_mapping.csv",index=False); ablation.to_csv(thesis/"feature_group_ablation.csv",index=False); sensitivity.to_csv(output/"configuration_descriptor_sensitivity.csv",index=False)
    high_errors.to_csv(output/"highest_error_observations.csv",index=False); error_summary.to_csv(output/"error_group_summary.csv",index=False); extrap.to_csv(output/"feature_extrapolation_audit.csv",index=False)
    figure_paths=create_phase6_figures(robust_detail,compact_perf,ablation,sensitivity,error_summary,extrap,data,balanced,figures)
    summary={"validated_rows":len(data),"fcc":int(data.phase.eq("FCC").sum()),"bcc":int(data.phase.eq("BCC").sum()),"hcp":0,"target":TARGET,
             "robustness":robust_summary.to_dict("records"),"compact_size":compact_size,"compact_outer_metrics":compact_metrics.to_dict("records"),
             "top_compact_features":compact[:20],"group_ablation":ablation.to_dict("records"),"error_diagnostics":diagnostics,
             "runtime_seconds":time.perf_counter()-started,"figures":figure_paths}
    (reports/"phase6_metrics.json").write_text(json.dumps(summary,indent=2,default=str),encoding="utf-8")
    return summary
