import unittest

import numpy as np
import pandas as pd
from PIL import Image
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.linear_model import Ridge

from src.ml.phase5 import TARGET, build_pipeline, load_feature_sets, make_outer_split, split_audit, validate_ml_frame


class TestPhase5SplitsAndLeakage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = pd.read_parquet("data/processed/ml_dataset.parquet")
        cls.sets, cls.mapping = load_feature_sets()

    def test_validated_counts_and_hcp_absence(self):
        audit = validate_ml_frame(self.data, self.mapping.feature.tolist())
        self.assertEqual((audit["rows"], audit["fcc"], audit["bcc"], audit["validated_hcp"]), (83797, 40425, 43372, 0))

    def test_grouped_splits_have_zero_group_overlap(self):
        for strategy in ("composition_grouped", "alloy_system_grouped"):
            with self.subTest(strategy=strategy):
                split = make_outer_split(self.data, strategy)
                audit = split_audit(self.data, split)
                self.assertEqual(audit["group_overlap"], 0)
                self.assertEqual(set(split.train_index).intersection(split.test_index), set())

    def test_feature_sets_contain_no_target_proxy(self):
        for name, features in self.sets.items():
            with self.subTest(feature_set=name):
                self.assertFalse(any("sro" in f.lower() or "ordering parameter" in f.lower() or f.lower().startswith("target_") for f in features))

    def test_training_pipeline_owns_variance_filter_and_scaler(self):
        pipe = build_pipeline(Ridge(alpha=1), scale=True)
        self.assertEqual(list(pipe.named_steps), ["variance", "scale", "model"])
        X = pd.DataFrame({"constant": [1, 1, 1, 1], "variable": [0, 1, 2, 3]})
        pipe.fit(X.iloc[:3], np.array([0.0, 1.0, 2.0]))
        self.assertEqual(pipe.named_steps["variance"].get_support().tolist(), [False, True])


class TestPhase5Outputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.best = pd.read_csv("results/tables/phase5/best_model_metrics.csv").set_index("cohort")

    def test_reported_best_metrics_recompute_from_predictions(self):
        for cohort in ("ALL", "FCC", "BCC"):
            with self.subTest(cohort=cohort):
                pred = pd.read_csv(f"results/tables/phase5/best_predictions_{cohort.lower()}.csv")
                self.assertFalse(pred["phase"].eq("HCP").any())
                y, yhat = pred[TARGET], pred["prediction"]
                self.assertAlmostEqual(r2_score(y, yhat), self.best.loc[cohort, "test_r2"], places=12)
                self.assertAlmostEqual(mean_absolute_error(y, yhat), self.best.loc[cohort, "test_mae"], places=12)
                self.assertAlmostEqual(mean_squared_error(y, yhat) ** 0.5, self.best.loc[cohort, "test_rmse"], places=12)

    def test_grouped_validation_contains_required_strategies(self):
        table = pd.read_csv("results/tables/phase5/grouped_validation_results.csv")
        self.assertEqual(set(table["split_strategy"]), {"random_configuration", "composition_grouped", "alloy_system_grouped"})
        self.assertEqual(set(table["cohort"]), {"ALL", "FCC", "BCC"})

    def test_phase5_figures_are_300_dpi(self):
        figures = list(Path("thesis_outputs/figures/phase5").glob("*.png"))
        self.assertEqual(len(figures), 18)
        for path in figures:
            with self.subTest(path=path.name), Image.open(path) as image:
                self.assertGreaterEqual(image.width, 1200)
                self.assertGreaterEqual(image.info.get("dpi", (0, 0))[0], 299)


if __name__ == "__main__":
    unittest.main()
