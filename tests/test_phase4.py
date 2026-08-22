import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from src.analysis.phase4 import TARGET, build_feature_mapping, classify_feature, preliminary_sets


class TestPhase4Utilities(unittest.TestCase):
    def test_feature_classification_and_leakage_flag(self):
        self.assertEqual(classify_feature("derived_vec_mean", "elemental-reference-derived")["feature_group"], "valence / VEC")
        self.assertEqual(classify_feature("mean CN_VoronoiNN", "structure-derived")["target_proxy_risk"], "possible_initial_geometry_proxy")
        self.assertTrue(classify_feature("mean SRO shell 1", "direct source")["unsuitable_for_analysis"])

    def test_mapping_covers_phase3_features(self):
        provenance = pd.read_csv("reports/tables/feature_provenance.csv")
        mapping = build_feature_mapping(provenance)
        self.assertEqual(len(mapping), 348)
        self.assertFalse(mapping["feature_group"].isna().any())
        self.assertFalse(mapping["origin"].isna().any())


class TestPhase4Outputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metrics = json.loads(Path("reports/phase4_metrics.json").read_text(encoding="utf-8"))
        cls.assoc = pd.read_csv("results/tables/phase4/feature_target_associations.csv")
        cls.mapping = pd.read_csv("results/tables/phase4/feature_group_mapping.csv")

    def test_exact_validated_cohort_and_hcp_exclusion(self):
        self.assertEqual(self.metrics["rows"], 83797)
        self.assertEqual(self.metrics["fcc_observations"], 40425)
        self.assertEqual(self.metrics["bcc_observations"], 43372)
        self.assertEqual(self.metrics["validated_hcp_observations"], 0)
        self.assertEqual(self.metrics["provisional_hcp_excluded"], 255)

    def test_associations_cover_three_cohorts_without_proxies(self):
        self.assertEqual(set(self.assoc["cohort"]), {"ALL", "FCC", "BCC"})
        self.assertFalse(self.assoc["feature"].str.contains("sro|ordering parameter|target_", case=False, regex=True).any())
        self.assertEqual(self.mapping["unsuitable_for_analysis"].sum(), 0)

    def test_preliminary_sets_are_nested_and_nonempty(self):
        table = pd.read_csv("results/tables/phase4/preliminary_feature_sets.csv")
        sets = {name: set(group.feature) for name, group in table.groupby("set")}
        self.assertTrue(sets["MINIMAL_PRELIMINARY"] <= sets["FULL_CLEAN"])
        self.assertTrue(sets["BALANCED_PRELIMINARY"] <= sets["FULL_CLEAN"])
        self.assertEqual(len(sets["MINIMAL_PRELIMINARY"]), 19)

    def test_figures_are_thesis_resolution(self):
        paths = list(Path("thesis_outputs/figures/phase4").glob("*.png"))
        self.assertGreaterEqual(len(paths), 18)
        for path in paths:
            with self.subTest(path=path.name), Image.open(path) as image:
                self.assertGreaterEqual(image.width, 1200)
                self.assertGreaterEqual(image.info.get("dpi", (0, 0))[0], 299)


if __name__ == "__main__":
    unittest.main()
