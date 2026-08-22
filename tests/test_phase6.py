import unittest
from pathlib import Path

import pandas as pd
from PIL import Image
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.analysis.phase6 import ROBUSTNESS_SEEDS, coarse_feature_group
from src.ml.phase5 import TARGET


class TestPhase6Protocol(unittest.TestCase):
    def test_physical_group_mapping(self):
        self.assertEqual(coarse_feature_group("initial symmetry"), "symmetry")
        self.assertEqual(coarse_feature_group("initial structural geometry"), "structural_geometry")
        self.assertEqual(coarse_feature_group("configurational entropy"), "configurational_entropy")

    def test_compact_choice_uses_inner_validation_only(self):
        table = pd.read_csv("results/tables/phase6/compact_feature_count_validation.csv")
        self.assertEqual(int(table["selected"].sum()), 1)
        self.assertFalse(any("test" in column.lower() for column in table.columns))
        selected = table.loc[table["selected"]].iloc[0]
        self.assertGreaterEqual(selected["mean_cv_r2"], selected["acceptance_threshold"])

    def test_repeated_grouped_splits_are_complete(self):
        detail = pd.read_csv("results/tables/phase6/model_robustness_detail.csv")
        self.assertEqual(set(detail["seed"]), set(ROBUSTNESS_SEEDS))
        self.assertEqual(set(detail["cohort"]), {"ALL", "FCC", "BCC"})
        self.assertEqual(len(detail), len(ROBUSTNESS_SEEDS) * 3)


class TestPhase6Outputs(unittest.TestCase):
    def test_compact_metrics_recompute_from_saved_predictions(self):
        metrics = pd.read_csv("results/tables/phase6/compact_outer_test_metrics.csv").set_index("cohort")
        for cohort in ("ALL", "FCC", "BCC"):
            with self.subTest(cohort=cohort):
                pred = pd.read_csv(f"results/tables/phase6/compact_outer_predictions_{cohort.lower()}.csv")
                self.assertFalse(pred["phase"].eq("HCP").any())
                y, yhat = pred[TARGET], pred["prediction"]
                self.assertAlmostEqual(r2_score(y, yhat), metrics.loc[cohort, "test_r2"], places=12)
                self.assertAlmostEqual(mean_absolute_error(y, yhat), metrics.loc[cohort, "test_mae"], places=12)
                self.assertAlmostEqual(mean_squared_error(y, yhat) ** 0.5, metrics.loc[cohort, "test_rmse"], places=12)

    def test_feature_lists_and_leakage_exclusion(self):
        expected = {
            "full.txt": 324,
            "balanced.txt": 198,
            "compact_high_performance.txt": 10,
            "minimal_common.txt": 18,
        }
        for filename, count in expected.items():
            features = (Path("results/feature_sets") / filename).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(features), count)
            self.assertFalse(any("sro" in feature.lower() or feature.lower().startswith("target_") for feature in features))

    def test_requested_tables_have_stable_schema(self):
        robust = pd.read_csv("thesis_outputs/tables/model_robustness_summary.csv")
        ablation = pd.read_csv("thesis_outputs/tables/feature_group_ablation.csv")
        self.assertEqual(set(robust["cohort"]), {"ALL", "FCC", "BCC"})
        self.assertEqual(set(ablation["cohort"]), {"ALL", "FCC", "BCC"})
        self.assertIn("delta_r2_vs_baseline", ablation.columns)
        self.assertIn("delta_mae_vs_baseline", ablation.columns)

    def test_phase6_figures_are_300_dpi(self):
        names = {
            "model_robustness.png", "compact_feature_refinement.png",
            "feature_group_ablation.png", "configuration_descriptor_sensitivity.png",
            "error_by_target_decile.png", "extrapolation_feature_ranges.png",
            "fcc_bcc_final_comparison.png", "focused_partial_dependence.png",
        }
        for name in names:
            path = Path("thesis_outputs/figures") / name
            self.assertTrue(path.exists())
            with Image.open(path) as image:
                self.assertGreaterEqual(image.width, 1200)
                self.assertGreaterEqual(image.info.get("dpi", (0, 0))[0], 299)


if __name__ == "__main__":
    unittest.main()
