import unittest
from pathlib import Path

import pyarrow.parquet as pq


class TestPhase3Outputs(unittest.TestCase):
    def test_required_parquet_shapes(self):
        expected = {
            "structures.parquet": (83797, 12),
            "sro_long.parquet": (335188, 14),
            "features.parquet": (83797, 349),
            "ml_dataset.parquet": (83797, 361),
        }
        for name, (rows, columns) in expected.items():
            with self.subTest(name=name):
                metadata = pq.ParquetFile(Path("data/processed") / name).metadata
                self.assertEqual(metadata.num_rows, rows)
                self.assertEqual(metadata.num_columns, columns)


if __name__ == "__main__":
    unittest.main()
