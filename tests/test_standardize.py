import math
import unittest

from src.cleaning.standardize import canonical_pair, normalize_phase, parse_formula_fractions


class TestStandardize(unittest.TestCase):
    def test_formula_fractions(self):
        result = parse_formula_fractions("Al1Co2Cr1")
        self.assertEqual(set(result), {"Al", "Co", "Cr"})
        self.assertTrue(math.isclose(sum(result.values()), 1.0))
        self.assertTrue(math.isclose(result["Co"], 0.5))

    def test_implicit_amount(self):
        self.assertEqual(parse_formula_fractions("CrCoNi"), {"Co": 1 / 3, "Cr": 1 / 3, "Ni": 1 / 3})

    def test_invalid_formula(self):
        with self.assertRaises(ValueError):
            parse_formula_fractions("Cr-Fe")

    def test_phase(self):
        self.assertEqual(normalize_phase("fcc"), "FCC")
        self.assertEqual(normalize_phase(None), "UNKNOWN")

    def test_pair(self):
        self.assertEqual(canonical_pair("Ni", "Cr"), ("Cr", "Ni"))


if __name__ == "__main__":
    unittest.main()
