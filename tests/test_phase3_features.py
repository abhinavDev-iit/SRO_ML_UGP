import unittest
from pathlib import Path

import pandas as pd

from src.features.hea_features import engineer_features
from src.ingestion.hea84k import (
    DIRECT_SRO_PROXIES,
    FINAL_OR_UNSAFE_FIELDS,
    INITIAL_FILENAME,
    select_default_feature_columns,
)


class TestPhase3Features(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw_path = Path("data/raw/dataset_84k_hea") / INITIAL_FILENAME
        header = pd.read_csv(raw_path, nrows=0).columns.tolist()
        cls.source = pd.read_csv(raw_path, usecols=select_default_feature_columns(header), nrows=2000)
        cls.features, cls.provenance, _, cls.errors = engineer_features(cls.source)

    def test_feature_count_and_provenance(self):
        self.assertEqual(self.features.shape[1] - 1, 348)
        self.assertEqual(set(self.features.columns) - {"fid"}, set(self.provenance["feature"]))
        self.assertEqual(len(self.provenance), 348)

    def test_no_leakage_fields(self):
        forbidden = FINAL_OR_UNSAFE_FIELDS | DIRECT_SRO_PROXIES
        self.assertFalse(forbidden.intersection(self.features.columns))

    def test_reference_reconstruction(self):
        self.assertLess(max(self.errors.values()), 1e-7)

    def test_major_features_complete(self):
        major = [
            "configurational_entropy_j_mol_k", "atomic_size_mismatch_percent",
            "pair_electronegativity_mean_abs_diff", "pair_vec_mean_abs_diff",
            "pair_melting_point_mean_abs_diff",
        ]
        self.assertFalse(self.features[major].isna().any().any())


if __name__ == "__main__":
    unittest.main()
