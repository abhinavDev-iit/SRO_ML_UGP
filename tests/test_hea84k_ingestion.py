import unittest
from pathlib import Path

from src.ingestion.hea84k import (
    DIRECT_SRO_PROXIES,
    FINAL_OR_UNSAFE_FIELDS,
    build_manifest,
    read_header,
    select_default_feature_columns,
)


RAW = Path("data/raw/dataset_84k_hea")


class TestHEA84kIngestion(unittest.TestCase):
    def test_default_feature_policy(self):
        header = read_header(RAW / "structure_ini_featurized.dat_all.csv")
        selected = set(select_default_feature_columns(header))
        self.assertFalse(selected & FINAL_OR_UNSAFE_FIELDS)
        self.assertFalse(selected & DIRECT_SRO_PROXIES)
        self.assertIn("space_group_number_ini", selected)
        self.assertIn("MagpieData mean AtomicWeight", selected)

    def test_manifest_relationships(self):
        manifest = build_manifest(RAW)
        self.assertTrue(manifest["one_to_one_key_match"])
        self.assertEqual(manifest["initial_rows"], 83797)
        self.assertEqual(manifest["phase_counts"], {"FCC": 40425, "BCC": 43372})
        self.assertEqual(manifest["primary_target"], "mean abs SRO1")


if __name__ == "__main__":
    unittest.main()
