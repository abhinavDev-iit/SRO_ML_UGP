import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.dft.phase7 import (
    TARGET,
    build_qe_input,
    choose_phase_pairs,
    parse_qe_output,
    validate_structure,
)


def structure_payload() -> dict:
    structure = {
        "lattice": {"matrix": [[3.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 3.0]]},
        "sites": [
            {"species": [{"element": "Co", "occu": 1}], "abc": [0.0, 0.0, 0.0]},
            {"species": [{"element": "Cr", "occu": 1}], "abc": [0.5, 0.5, 0.5]},
        ],
    }
    return {
        "fid": "example",
        "phase": "BCC",
        "composition": {"Co": 0.5, "Cr": 0.5},
        "NIONS": 2,
        "exact_initial_structure": structure,
    }


class TestPhase7Selection(unittest.TestCase):
    def test_atom_count_precedes_sro_range(self):
        rows = []
        for phase in ("FCC", "BCC"):
            rows.extend(
                [
                    {"fid": f"{phase}-small-low", "phase": phase, "chemical_system": "Co-Cr", "composition_fractions_json": '{"Co": 0.5, "Cr": 0.5}', "NIONS": 2, TARGET: 0.1},
                    {"fid": f"{phase}-small-high", "phase": phase, "chemical_system": "Co-Cr", "composition_fractions_json": '{"Co": 0.5, "Cr": 0.5}', "NIONS": 2, TARGET: 0.2},
                    {"fid": f"{phase}-large-low", "phase": phase, "chemical_system": "Al-Si", "composition_fractions_json": '{"Al": 0.5, "Si": 0.5}', "NIONS": 4, TARGET: 0.0},
                    {"fid": f"{phase}-large-high", "phase": phase, "chemical_system": "Al-Si", "composition_fractions_json": '{"Al": 0.5, "Si": 0.5}', "NIONS": 4, TARGET: 1.0},
                ]
            )
        selected = choose_phase_pairs(pd.DataFrame(rows))
        self.assertEqual(set(selected["chemical_system"]), {"Co-Cr"})
        self.assertEqual(set(selected["NIONS"]), {2})
        self.assertEqual(selected.groupby("phase").size().to_dict(), {"BCC": 2, "FCC": 2})

    def test_structure_validation_rejects_composition_mismatch(self):
        payload = structure_payload()
        validate_structure(payload["exact_initial_structure"], json.dumps(payload["composition"]), 2)
        with self.assertRaises(ValueError):
            validate_structure(payload["exact_initial_structure"], '{"Co": 1.0}', 2)


class TestQuantumEspressoUtilities(unittest.TestCase):
    def test_template_preserves_atom_order_and_enables_spin(self):
        config = {
            "pseudopotentials": {"Co": {"filename": None}, "Cr": {"filename": None}},
            "ecutwfc_ry": None,
            "ecutrho_ry": None,
            "kpoint_spacing_inv_angstrom": 0.25,
            "starting_magnetization": {"Co": 0.3, "Cr": -0.3},
        }
        text = build_qe_input(structure_payload(), config, template=True)
        self.assertIn("calculation = 'scf'", text)
        self.assertIn("input_dft = 'PBE'", text)
        self.assertIn("nspin = 2", text)
        self.assertIn("starting_magnetization(1) = 0.300000", text)
        self.assertIn("starting_magnetization(2) = -0.300000", text)
        self.assertIn("__ECUTWFC_RY__", text)
        positions = text.split("ATOMIC_POSITIONS crystal\n", 1)[1].split("CELL_PARAMETERS", 1)[0]
        self.assertLess(positions.index("Co "), positions.index("Cr "))

    def test_qe_output_parser_uses_last_total_energy(self):
        content = """
     convergence has been achieved in 12 iterations
!    total energy              =    -10.00000000 Ry
     total magnetization       =      1.25 Bohr mag/cell
!    total energy              =    -10.10000000 Ry
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scf.out"
            path.write_text(content, encoding="utf-8")
            parsed = parse_qe_output(path)
        self.assertTrue(parsed["converged"])
        self.assertAlmostEqual(parsed["total_energy_ry"], -10.1)
        self.assertAlmostEqual(parsed["magnetic_moment_muB"], 1.25)


class TestPhase7TrackedArtifacts(unittest.TestCase):
    def test_selected_structures_and_templates_are_complete(self):
        selection = pd.read_csv("results/tables/dft/selected_configurations.csv")
        self.assertEqual(len(selection), 4)
        self.assertEqual(selection.groupby("phase").size().to_dict(), {"BCC": 2, "FCC": 2})
        self.assertEqual(set(selection["low_high_label"]), {"low", "high"})
        self.assertLessEqual(int(selection["NIONS"].max()), 8)
        for row in selection.itertuples(index=False):
            structure_path = Path("dft_structures") / f"{row.fid}.json"
            template_path = Path("dft_inputs/templates") / f"{row.fid}.scf.in.template"
            payload = json.loads(structure_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["fid"], row.fid)
            self.assertEqual(len(payload["exact_initial_structure"]["sites"]), row.NIONS)
            template = template_path.read_text(encoding="utf-8")
            self.assertIn("calculation = 'scf'", template)
            self.assertNotIn("relax", template)
            self.assertIn("__ECUTWFC_RY__", template)


if __name__ == "__main__":
    unittest.main()
