import unittest
from pathlib import Path

from src.ingestion.mlp_hcp import audit_mlp_hcp


class TestMLPHCPAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path("data/raw/mlp_csro/MLP-cSRO-main/training_datasets")
        cls.frame, cls.summary = audit_mlp_hcp(
            root / "Training_TS-4_Cao.cfg", root / "Training_TS-5_Cao.cfg"
        )

    def test_candidate_identity(self):
        self.assertEqual(self.summary["candidate_configurations"], 255)
        self.assertTrue(self.summary["all_144_atoms"])
        self.assertTrue(self.summary["all_equiatomic"])
        self.assertTrue((self.frame["temperature_K"] == 500.0).all())

    def test_reference_validation_not_claimed(self):
        self.assertFalse(self.summary["validated_reference_arrays_available"])
        self.assertEqual(self.summary["validated_hcp_observations"], 0)
        self.assertGreater(self.summary["configurations_with_shell_gap_below_1_02"], 0)


if __name__ == "__main__":
    unittest.main()
