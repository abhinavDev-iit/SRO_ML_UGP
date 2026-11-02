import json
import hashlib
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.dft.phase7 import (
    TARGET,
    analyze_dft_results,
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
     absolute magnetization    =      1.50 Bohr mag/cell
!    total energy              =    -10.10000000 Ry
   JOB DONE.
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scf.out"
            path.write_text(content, encoding="utf-8")
            parsed = parse_qe_output(path)
        self.assertTrue(parsed["converged"])
        self.assertTrue(parsed["normal_termination"])
        self.assertAlmostEqual(parsed["total_energy_ry"], -10.1)
        self.assertAlmostEqual(parsed["latest_total_energy_ry"], -10.1)
        self.assertAlmostEqual(parsed["magnetic_moment_muB"], 1.25)
        self.assertAlmostEqual(parsed["absolute_magnetization_muB"], 1.5)
        self.assertEqual(parsed["scf_iterations"], 12)

    def test_analysis_requires_normal_outputs_and_writes_pairwise_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selection_path = root / "selection.csv"
            rows = [
                {"fid": "fcc-low", "phase": "FCC", "composition": "Co0.5Cr0.5", "NIONS": 2, "SRO": 0.0, "low_high_label": "low"},
                {"fid": "fcc-high", "phase": "FCC", "composition": "Co0.5Cr0.5", "NIONS": 2, "SRO": 1 / 3, "low_high_label": "high"},
                {"fid": "bcc-low", "phase": "BCC", "composition": "Co0.5Cr0.5", "NIONS": 2, "SRO": 0.0, "low_high_label": "low"},
                {"fid": "bcc-high", "phase": "BCC", "composition": "Co0.5Cr0.5", "NIONS": 2, "SRO": 1.0, "low_high_label": "high"},
            ]
            pd.DataFrame(rows).to_csv(selection_path, index=False)
            run_dir = root / "runs"
            energies = {"fcc-low": -10.00, "fcc-high": -10.02, "bcc-low": -11.00, "bcc-high": -10.98}
            for fid, energy in energies.items():
                output = run_dir / fid / "scf.out"
                output.parent.mkdir(parents=True)
                output.write_text(
                    "convergence has been achieved in 8 iterations\n"
                    f"!    total energy = {energy:.8f} Ry\n"
                    "total magnetization = 0.20 Bohr mag/cell\n"
                    "absolute magnetization = 0.40 Bohr mag/cell\n"
                    "JOB DONE.\n",
                    encoding="utf-8",
                )
            config = json.loads(Path("dft_inputs/qe_config.json").read_text(encoding="utf-8"))
            config_path = root / "qe_config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            cutoff_path = root / "cutoff.csv"
            pd.DataFrame(
                [
                    {"ecutwfc_ry": 45, "ecutrho_ry": 360, "energy_per_atom_eV": -68.0, "relative_energy_change_meV_atom": 1.0, "convergence_status": "converged"},
                    {"ecutwfc_ry": 55, "ecutrho_ry": 440, "energy_per_atom_eV": -68.001, "relative_energy_change_meV_atom": 0.0, "convergence_status": "converged"},
                ]
            ).to_csv(cutoff_path, index=False)
            results_path = root / "dft_results.csv"
            report_path = root / "dft_summary.md"
            figure_dir = root / "figures"
            analyze_dft_results(
                selection_path=selection_path,
                run_dir=run_dir,
                results_path=results_path,
                figure_dir=figure_dir,
                report_path=report_path,
                config_path=config_path,
                cutoff_table_path=cutoff_path,
            )
            results = pd.read_csv(results_path)
            self.assertEqual(len(results), 4)
            self.assertTrue(results["normal_termination"].all())
            self.assertIn("absolute_magnetization_muB", results.columns)
            self.assertEqual(results.groupby("phase")["relative_energy_meV_atom"].min().to_dict(), {"BCC": 0.0, "FCC": 0.0})
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("should not be interpreted as establishing a universal causal relationship", report)
            self.assertTrue((figure_dir / "dft_relative_energy.png").is_file())
            self.assertTrue((figure_dir / "sro_vs_relative_energy.png").is_file())


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

    def test_qe7_production_inputs_and_pseudopotential_metadata(self):
        config = json.loads(Path("dft_inputs/qe_config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["qe_version"], "7.6")
        self.assertEqual(config["conda_environment"], "qe7")
        self.assertNotEqual(config["resolved_executable"], "/usr/bin/pw.x")
        self.assertEqual(config["kpoint_grid"], [12, 12, 12])
        self.assertEqual(config["ecutwfc_ry"], 55.0)
        self.assertEqual(config["ecutrho_ry"], 440.0)
        self.assertEqual(config["pseudo_family"], "SSSP PBE Efficiency v1.3.0")
        for element, expected_sha256 in {
            "Co": "a5f392a0d35fc78cc9e2ac1636bb1cd02e9b80a063ea368e85be83b0e4523c45",
            "Cr": "c7449bbfea358d76832cf2f7b43dc89101ead6891806773121bfaa93a140f6de",
        }.items():
            record = config["pseudopotentials"][element]
            self.assertEqual(record["sha256"], expected_sha256)
            path = Path(config["pseudo_dir"]) / record["filename"]
            if path.is_file():
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected_sha256)
        selection = pd.read_csv("results/tables/dft/selected_configurations.csv")
        for fid in selection["fid"].astype(str):
            production = Path("dft_inputs/production") / fid / "scf.in"
            text = production.read_text(encoding="utf-8")
            self.assertIn("calculation = 'scf'", text)
            self.assertIn("nspin = 2", text)
            self.assertIn("ecutwfc = 55.0", text)
            self.assertIn("ecutrho = 440.0", text)
            self.assertIn("K_POINTS automatic\n12 12 12 0 0 0", text)
            self.assertNotIn("__ECUTWFC_RY__", text)
            self.assertNotIn("relax", text)
            positions = text.split("ATOMIC_POSITIONS crystal\n", 1)[1].split("CELL_PARAMETERS", 1)[0]
            species = [line.split()[0] for line in positions.splitlines() if line.strip()]
            self.assertEqual(species, ["Co", "Cr"])
            metadata = json.loads((production.parent / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["NIONS"], 2)
            self.assertEqual(metadata["ecutwfc_ry"], 55.0)
            self.assertEqual(metadata["ecutrho_ry"], 440.0)

    def test_manual_runner_is_sequential_and_preserves_outputs(self):
        script = Path("dft_runs/run_final_scfs.sh").read_text(encoding="utf-8")
        self.assertIn('CONDA_ENV="qe7"', script)
        self.assertIn("gra62121526 gra62121527 gra64001864 gra62121595", script)
        self.assertIn("grep -q 'JOB DONE", script)
        self.assertIn("scf.previous.", script)
        self.assertNotIn("rm ", script)

    def test_cutoff_audit_distinguishes_formal_and_near_convergence(self):
        cutoff = pd.read_csv("results/tables/dft/cutoff_sanity_check.csv")
        self.assertEqual(cutoff["ecutwfc_ry"].tolist(), [45.0, 55.0, 65.0])
        row55 = cutoff.loc[cutoff["ecutwfc_ry"].eq(55.0)].iloc[0]
        row65 = cutoff.loc[cutoff["ecutwfc_ry"].eq(65.0)].iloc[0]
        self.assertEqual(row55["convergence_status"], "formally_converged")
        self.assertTrue(bool(row55["normal_termination"]))
        self.assertEqual(row65["convergence_status"], "near_converged_not_formal")
        self.assertFalse(bool(row65["normal_termination"]))
        self.assertAlmostEqual(row55["total_energy_ry"], -473.95628523)
        self.assertAlmostEqual(row65["total_energy_ry"], -473.95654789)
        self.assertAlmostEqual(row55["relative_energy_change_meV_atom"], 1.786835678)


if __name__ == "__main__":
    unittest.main()
