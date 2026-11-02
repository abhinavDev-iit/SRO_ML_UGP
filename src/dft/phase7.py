"""Small, reproducible Phase 7 static-DFT comparison.

The module deliberately selects only one low/high-SRO pair per phase, extracts
the exact source initial structures, and prepares Quantum ESPRESSO inputs.  It
does not install a DFT engine or invent pseudopotential settings/results.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


TARGET = "target_mean_abs_sro_shell1"
DEFAULT_DATASET = Path("data/processed/ml_dataset.parquet")
DEFAULT_MASTER = Path("data/raw/dataset_84k_hea/hea.2023-04-06.csv")
DEFAULT_SELECTION = Path("results/tables/dft/selected_configurations.csv")
DEFAULT_STRUCTURES = Path("dft_structures")
DEFAULT_CONFIG = Path("dft_inputs/qe_config.json")
DEFAULT_INPUTS = Path("dft_inputs")
DEFAULT_RUNS = Path("dft_runs")
DEFAULT_RESULTS = Path("results/tables/dft/dft_results.csv")
DEFAULT_FIGURES = Path("figures/dft")
DEFAULT_REPORT = Path("reports/dft_summary.md")
RY_TO_EV = 13.605693122994

# Dataset elements only; values are conventional standard atomic weights used
# by QE to label species, not fitted scientific descriptors.
ATOMIC_MASSES = {
    "Al": 26.9815385,
    "Co": 58.933194,
    "Cr": 51.9961,
    "Cu": 63.546,
    "Fe": 55.845,
    "Mn": 54.938044,
    "Ni": 58.6934,
    "Si": 28.085,
}
MAGNETIC_ELEMENTS = {"Cr", "Mn", "Fe", "Co", "Ni"}


def _phase(value: str) -> str:
    return str(value).strip().upper()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rank_candidate_groups(frame: pd.DataFrame, max_nions: int = 16) -> pd.DataFrame:
    """Rank fixed phase/composition/atom-count groups deterministically."""
    required = {
        "fid",
        "phase",
        "chemical_system",
        "composition_fractions_json",
        "NIONS",
        TARGET,
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"candidate table missing columns: {sorted(missing)}")
    eligible = frame.loc[
        frame["phase"].map(_phase).isin({"FCC", "BCC"})
        & frame["NIONS"].le(max_nions)
    ].copy()
    eligible["phase"] = eligible["phase"].map(_phase)
    keys = ["phase", "chemical_system", "composition_fractions_json", "NIONS"]
    ranked = (
        eligible.groupby(keys, dropna=False)[TARGET]
        .agg(configuration_count="size", sro_min="min", sro_max="max")
        .reset_index()
    )
    ranked["sro_range"] = ranked["sro_max"] - ranked["sro_min"]
    ranked = ranked.loc[
        ranked["configuration_count"].ge(2) & ranked["sro_range"].gt(0)
    ].copy()
    return ranked.sort_values(
        ["phase", "NIONS", "sro_range", "configuration_count", "chemical_system", "composition_fractions_json"],
        ascending=[True, True, False, False, True, True],
        kind="stable",
    ).reset_index(drop=True)


def choose_phase_pairs(frame: pd.DataFrame, max_nions: int = 16) -> pd.DataFrame:
    """Choose one lowest/highest-SRO row from the best group in each phase."""
    normalized = frame.copy()
    normalized["phase"] = normalized["phase"].map(_phase)
    ranked = rank_candidate_groups(normalized, max_nions=max_nions)
    rows: list[pd.DataFrame] = []
    keys = ["phase", "chemical_system", "composition_fractions_json", "NIONS"]
    for phase in ("FCC", "BCC"):
        phase_groups = ranked.loc[ranked["phase"].eq(phase)]
        if phase_groups.empty:
            raise ValueError(f"no eligible {phase} fixed-composition pair found")
        best = phase_groups.iloc[0]
        mask = pd.Series(True, index=normalized.index)
        for key in keys:
            mask &= normalized[key].eq(best[key])
        candidates = normalized.loc[mask].sort_values([TARGET, "fid"], kind="stable")
        selected = candidates.iloc[[0, -1]].copy()
        selected["sro_label"] = ["low", "high"]
        rows.append(selected)
    return pd.concat(rows, ignore_index=True)


def _read_master_records(master_path: Path, fids: set[str]) -> pd.DataFrame:
    columns = [
        "fid",
        "reduced_formula",
        "chemical_system",
        "lattice",
        "NIONS",
        "structure_ini_as_dict",
    ]
    matches: list[pd.DataFrame] = []
    for chunk in pd.read_csv(master_path, usecols=columns, chunksize=5000):
        found = chunk.loc[chunk["fid"].astype(str).isin(fids)]
        if not found.empty:
            matches.append(found)
    if not matches:
        raise ValueError("none of the selected fids were found in the raw master table")
    records = pd.concat(matches, ignore_index=True)
    if set(records["fid"].astype(str)) != fids or records["fid"].duplicated().any():
        raise ValueError("selected fids are missing or duplicated in the raw master table")
    return records


def _parse_structure(value: str) -> dict[str, Any]:
    try:
        structure = ast.literal_eval(value)
    except (SyntaxError, ValueError) as exc:
        raise ValueError("invalid source structure_ini_as_dict") from exc
    if not isinstance(structure, dict) or "lattice" not in structure or "sites" not in structure:
        raise ValueError("source structure lacks lattice or sites")
    return structure


def _site_element(site: dict[str, Any]) -> str:
    species = site.get("species", [])
    if len(species) != 1 or float(species[0].get("occu", 0)) != 1.0:
        raise ValueError("only fully occupied single-species sites are supported")
    return str(species[0]["element"])


def validate_structure(structure: dict[str, Any], composition_json: str, nions: int) -> None:
    sites = structure["sites"]
    matrix = np.asarray(structure["lattice"]["matrix"], dtype=float)
    if matrix.shape != (3, 3) or not np.isfinite(matrix).all() or abs(np.linalg.det(matrix)) <= 1e-10:
        raise ValueError("invalid 3x3 source lattice")
    if len(sites) != int(nions):
        raise ValueError(f"source site count {len(sites)} does not match NIONS {nions}")
    counts: dict[str, int] = {}
    for site in sites:
        element = _site_element(site)
        abc = np.asarray(site.get("abc"), dtype=float)
        if abc.shape != (3,) or not np.isfinite(abc).all():
            raise ValueError("source site lacks finite fractional coordinates")
        counts[element] = counts.get(element, 0) + 1
    expected = json.loads(composition_json)
    observed = {key: value / len(sites) for key, value in counts.items()}
    if set(expected) != set(observed) or any(
        not math.isclose(float(expected[key]), observed[key], abs_tol=1e-12)
        for key in expected
    ):
        raise ValueError(f"source composition mismatch: expected {expected}, observed {observed}")


def select_dft_configurations(
    data_path: Path = DEFAULT_DATASET,
    master_path: Path = DEFAULT_MASTER,
    output_path: Path = DEFAULT_SELECTION,
    structure_dir: Path = DEFAULT_STRUCTURES,
    max_nions: int = 16,
) -> dict[str, Any]:
    """Select four rows and extract exact source initial-structure copies."""
    columns = [
        "fid",
        "phase",
        "chemical_system",
        "composition_fractions_json",
        "NIONS",
        TARGET,
    ]
    frame = pd.read_parquet(data_path, columns=columns)
    selected = choose_phase_pairs(frame, max_nions=max_nions)
    fids = set(selected["fid"].astype(str))
    raw = _read_master_records(master_path, fids).set_index("fid")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    structure_dir.mkdir(parents=True, exist_ok=True)

    output_rows: list[dict[str, Any]] = []
    structure_paths: list[str] = []
    for row in selected.itertuples(index=False):
        fid = str(row.fid)
        source = raw.loc[fid]
        if _phase(source["lattice"]) != row.phase:
            raise ValueError(f"phase mismatch for {fid}")
        if int(source["NIONS"]) != int(row.NIONS):
            raise ValueError(f"atom-count mismatch for {fid}")
        structure = _parse_structure(str(source["structure_ini_as_dict"]))
        validate_structure(structure, row.composition_fractions_json, int(row.NIONS))
        source_locator = f"{master_path.as_posix()}#fid={fid};column=structure_ini_as_dict"
        structure_path = structure_dir / f"{fid}.json"
        payload = {
            "schema_version": 1,
            "fid": fid,
            "phase": row.phase,
            "chemical_system": row.chemical_system,
            "composition": json.loads(row.composition_fractions_json),
            "NIONS": int(row.NIONS),
            TARGET: float(getattr(row, TARGET)),
            "sro_label": row.sro_label,
            "source_structure_path": source_locator,
            "exact_initial_structure": structure,
        }
        structure_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        structure_paths.append(structure_path.as_posix())
        output_rows.append(
            {
                "fid": fid,
                "phase": row.phase,
                "chemical_system": row.chemical_system,
                "composition": json.dumps(json.loads(row.composition_fractions_json), sort_keys=True),
                "NIONS": int(row.NIONS),
                "SRO": float(getattr(row, TARGET)),
                "low_high_label": row.sro_label,
                "source_structure_path": source_locator,
            }
        )
    output = pd.DataFrame(output_rows)
    output.to_csv(output_path, index=False)
    return {
        "selected_configurations": len(output),
        "selection_path": output_path.as_posix(),
        "structure_paths": structure_paths,
        "max_nions": int(output["NIONS"].max()),
        "fids": output["fid"].tolist(),
    }


def _load_structure_copy(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_structure(
        payload["exact_initial_structure"],
        json.dumps(payload["composition"]),
        int(payload["NIONS"]),
    )
    return payload


def _kpoint_grid(matrix: np.ndarray, spacing_inv_angstrom: float) -> tuple[int, int, int]:
    if spacing_inv_angstrom <= 0:
        raise ValueError("k-point spacing must be positive")
    reciprocal = 2.0 * np.pi * np.linalg.inv(matrix).T
    return tuple(max(1, int(math.ceil(np.linalg.norm(vector) / spacing_inv_angstrom))) for vector in reciprocal)


def inspect_dft_environment(
    config_path: Path = DEFAULT_CONFIG,
    pseudo_dir: Path | None = None,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    directory = Path(pseudo_dir or config.get("pseudo_dir") or "dft_pseudopotentials")
    available = sorted([*directory.glob("*.UPF"), *directory.glob("*.upf")]) if directory.exists() else []
    missing, _ = _pseudopotential_status(config, directory) if config else (["configuration"], {})
    pw_x = shutil.which(str(config.get("pw_x") or "pw.x"))
    return {
        "pw_x": pw_x,
        "vasp_std": shutil.which("vasp_std"),
        "pseudo_dir": directory.as_posix(),
        "pseudopotential_files": [path.name for path in available],
        "missing_setup": missing + ([] if pw_x else ["Quantum ESPRESSO pw.x executable"]),
        "ready": bool(pw_x and not missing),
    }


def _pseudopotential_status(config: dict[str, Any], pseudo_dir: Path) -> tuple[list[str], dict[str, Path]]:
    missing: list[str] = []
    paths: dict[str, Path] = {}
    if not config.get("pseudo_family"):
        missing.append("pseudo_family")
    if not config.get("pseudo_source"):
        missing.append("pseudo_source")
    for key in ("ecutwfc_ry", "ecutrho_ry"):
        if not isinstance(config.get(key), (int, float)) or float(config[key]) <= 0:
            missing.append(key)
    for element, record in config.get("pseudopotentials", {}).items():
        filename = record.get("filename")
        checksum = record.get("sha256")
        if not filename:
            missing.append(f"pseudopotentials.{element}.filename")
            continue
        path = pseudo_dir / filename
        paths[element] = path
        if not path.is_file():
            missing.append(f"pseudopotential file {path.as_posix()}")
        elif not checksum:
            missing.append(f"pseudopotentials.{element}.sha256")
        elif _sha256(path).lower() != str(checksum).lower():
            raise ValueError(f"pseudopotential checksum mismatch: {path}")
    return missing, paths


def build_qe_input(payload: dict[str, Any], config: dict[str, Any], template: bool) -> str:
    structure = payload["exact_initial_structure"]
    matrix = np.asarray(structure["lattice"]["matrix"], dtype=float)
    sites = structure["sites"]
    elements = sorted({_site_element(site) for site in sites})
    for element in elements:
        if element not in ATOMIC_MASSES:
            raise ValueError(f"atomic mass not configured for {element}")
    pseudos = config.get("pseudopotentials", {})
    ecutwfc = config.get("ecutwfc_ry")
    ecutrho = config.get("ecutrho_ry")
    if template:
        ecutwfc_text = str(ecutwfc) if ecutwfc else "__ECUTWFC_RY__"
        ecutrho_text = str(ecutrho) if ecutrho else "__ECUTRHO_RY__"
    else:
        if not ecutwfc or not ecutrho:
            raise ValueError("runnable QE inputs require positive cutoffs")
        ecutwfc_text, ecutrho_text = str(ecutwfc), str(ecutrho)

    magnetic = any(element in MAGNETIC_ELEMENTS for element in elements)
    system_lines = [
        "  ibrav = 0,",
        f"  nat = {len(sites)},",
        f"  ntyp = {len(elements)},",
        f"  ecutwfc = {ecutwfc_text},",
        f"  ecutrho = {ecutrho_text},",
        "  occupations = 'smearing',",
        f"  input_dft = '{config.get('exchange_correlation', 'PBE')}',",
        f"  smearing = '{config.get('smearing', 'mv')}',",
        f"  degauss = {float(config.get('degauss_ry', 0.02)):.8f},",
    ]
    if magnetic:
        system_lines.append("  nspin = 2,")
        starts = config.get("starting_magnetization", {})
        for index, element in enumerate(elements, start=1):
            if element in MAGNETIC_ELEMENTS and element not in starts:
                raise ValueError(f"starting magnetization missing for {element}")
            value = float(starts.get(element, 0.0))
            system_lines.append(f"  starting_magnetization({index}) = {value:.6f},")

    species_lines = []
    for element in elements:
        filename = pseudos.get(element, {}).get("filename")
        if not filename:
            filename = f"__{element.upper()}_PSEUDOPOTENTIAL_UPF__"
        species_lines.append(f"{element} {ATOMIC_MASSES[element]:.8f} {filename}")
    position_lines = [
        f"{_site_element(site)} " + " ".join(f"{float(value):.12f}" for value in site["abc"])
        for site in sites
    ]
    cell_lines = [" ".join(f"{float(value):.12f}" for value in vector) for vector in matrix]
    grid = _kpoint_grid(matrix, float(config.get("kpoint_spacing_inv_angstrom", 0.25)))
    fid = payload["fid"]
    return "\n".join(
        [
            "&CONTROL",
            "  calculation = 'scf',",
            "  restart_mode = 'from_scratch',",
            f"  prefix = '{fid}',",
            "  outdir = './scratch',",
            "  pseudo_dir = './pseudopotentials',",
            "  disk_io = 'low',",
            "  tstress = .true.,",
            "  tprnfor = .false.,",
            "/",
            "&SYSTEM",
            *system_lines,
            "/",
            "&ELECTRONS",
            f"  conv_thr = {float(config.get('conv_thr', 1e-8)):.3e},",
            f"  electron_maxstep = {int(config.get('electron_maxstep', 200))},",
            f"  mixing_beta = {float(config.get('mixing_beta', 0.3)):.6f},",
            "/",
            "ATOMIC_SPECIES",
            *species_lines,
            "ATOMIC_POSITIONS crystal",
            *position_lines,
            "CELL_PARAMETERS angstrom",
            *cell_lines,
            "K_POINTS automatic",
            f"{grid[0]} {grid[1]} {grid[2]} 0 0 0",
            "",
        ]
    )


def prepare_dft_inputs(
    selection_path: Path = DEFAULT_SELECTION,
    structure_dir: Path = DEFAULT_STRUCTURES,
    config_path: Path = DEFAULT_CONFIG,
    input_dir: Path = DEFAULT_INPUTS,
    run_dir: Path = DEFAULT_RUNS,
    pseudo_dir: Path | None = None,
) -> dict[str, Any]:
    """Write tracked templates, or runnable local inputs when PP data are complete."""
    selection = pd.read_csv(selection_path)
    if len(selection) != 4 or set(selection["phase"]) != {"FCC", "BCC"}:
        raise ValueError("DFT selection must contain exactly four FCC/BCC rows")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    pp_dir = Path(pseudo_dir or config.get("pseudo_dir") or "dft_pseudopotentials")
    missing, pseudo_paths = _pseudopotential_status(config, pp_dir)
    engine = shutil.which(str(config.get("pw_x") or "pw.x"))
    template_only = bool(missing or not engine)
    template_root = input_dir / "templates"
    template_root.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []

    for row in selection.itertuples(index=False):
        payload = _load_structure_copy(structure_dir / f"{row.fid}.json")
        text = build_qe_input(payload, config, template=template_only)
        if template_only:
            path = template_root / f"{row.fid}.scf.in.template"
            path.write_text(text, encoding="utf-8")
        else:
            calculation_dir = run_dir / str(row.fid)
            calculation_dir.mkdir(parents=True, exist_ok=True)
            path = calculation_dir / "scf.in"
            path.write_text(text, encoding="utf-8")
            local_pseudo = calculation_dir / "pseudopotentials"
            local_pseudo.mkdir(exist_ok=True)
            for pp_path in pseudo_paths.values():
                destination = local_pseudo / pp_path.name
                if not destination.exists():
                    shutil.copy2(pp_path, destination)
            metadata = {
                "fid": row.fid,
                "phase": row.phase,
                "composition": row.composition,
                "SRO": float(row.SRO),
                "NIONS": int(row.NIONS),
                "engine": "Quantum ESPRESSO pw.x",
                "pseudo_family": config["pseudo_family"],
                "pseudopotentials": config["pseudopotentials"],
                "ecutwfc_ry": config["ecutwfc_ry"],
                "ecutrho_ry": config["ecutrho_ry"],
                "kpoint_spacing_inv_angstrom": config["kpoint_spacing_inv_angstrom"],
                "smearing": config["smearing"],
                "degauss_ry": config["degauss_ry"],
                "spin_polarized": True,
                "starting_magnetization": config["starting_magnetization"],
            }
            (calculation_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        generated.append(path.as_posix())

    return {
        "mode": "template_only" if template_only else "runnable",
        "pw_x": engine,
        "pseudo_dir": pp_dir.as_posix(),
        "missing_setup": missing + ([] if engine else ["Quantum ESPRESSO pw.x executable"]),
        "generated_inputs": generated,
    }


def run_dft(
    selection_path: Path = DEFAULT_SELECTION,
    config_path: Path = DEFAULT_CONFIG,
    run_dir: Path = DEFAULT_RUNS,
) -> dict[str, Any]:
    """Run the four already-prepared single-point QE inputs sequentially."""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    executable = shutil.which(str(config.get("pw_x") or "pw.x"))
    if not executable:
        raise RuntimeError("Quantum ESPRESSO pw.x executable is not available on PATH")
    selection = pd.read_csv(selection_path)
    completed: list[str] = []
    for fid in selection["fid"].astype(str):
        calculation_dir = run_dir / fid
        input_path = calculation_dir / "scf.in"
        if not input_path.is_file():
            raise FileNotFoundError(f"runnable input missing: {input_path}")
        output_path = calculation_dir / "scf.out"
        with input_path.open("rb") as source, output_path.open("wb") as sink:
            result = subprocess.run(
                [executable],
                stdin=source,
                stdout=sink,
                stderr=subprocess.STDOUT,
                cwd=calculation_dir,
                check=False,
            )
        completed.append(fid)
        if result.returncode != 0:
            raise RuntimeError(f"pw.x failed for {fid}; inspect {output_path}")
    return {"completed": completed, "run_dir": run_dir.as_posix()}


def parse_qe_output(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    energies = re.findall(r"!\s+total energy\s+=\s+([-+0-9.Ee]+)\s+Ry", text)
    moments = re.findall(r"total magnetization\s+=\s+([-+0-9.Ee]+)", text)
    converged = "convergence has been achieved" in text and bool(energies)
    energy_ry = float(energies[-1]) if energies else math.nan
    return {
        "converged": converged,
        "total_energy_ry": energy_ry,
        "total_energy_eV": energy_ry * RY_TO_EV if math.isfinite(energy_ry) else math.nan,
        "magnetic_moment_muB": float(moments[-1]) if moments else math.nan,
    }


def _save_dft_figures(results: pd.DataFrame, figure_dir: Path) -> list[str]:
    import matplotlib.pyplot as plt

    figure_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    colors = {"FCC": "#2878B5", "BCC": "#D95319"}

    order = results.sort_values(["phase", "low_high_label"], ascending=[True, False])
    labels = [f"{row.phase} {row.low_high_label}\nSRO={row.SRO:.3f}" for row in order.itertuples()]
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    bars = ax.bar(labels, order["relative_energy_meV_atom"], color=[colors[p] for p in order["phase"]])
    ax.bar_label(bars, fmt="%.2f", padding=3)
    ax.set_ylabel("Relative DFT energy (meV/atom)")
    ax.set_title("Static energy within fixed-composition phase pairs")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = figure_dir / "dft_relative_energy.png"
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    outputs.append(path.as_posix())

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    for phase, group in results.groupby("phase", observed=True):
        ax.scatter(group["SRO"], group["relative_energy_meV_atom"], s=70, color=colors[phase], label=phase)
        for row in group.itertuples():
            ax.annotate(row.low_high_label, (row.SRO, row.relative_energy_meV_atom), xytext=(5, 5), textcoords="offset points")
    ax.set(xlabel=TARGET, ylabel="Relative DFT energy (meV/atom)", title="Selected SRO-energy comparisons")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = figure_dir / "sro_vs_relative_energy.png"
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    outputs.append(path.as_posix())

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    bars = ax.bar(labels, order["SRO"], color=[colors[p] for p in order["phase"]])
    ax.bar_label(bars, fmt="%.3f", padding=3)
    ax.set(ylabel="Aggregate first-shell SRO magnitude", title="Four selected exact-source configurations")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = figure_dir / "selected_configurations.png"
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    outputs.append(path.as_posix())
    return outputs


def analyze_dft_results(
    selection_path: Path = DEFAULT_SELECTION,
    run_dir: Path = DEFAULT_RUNS,
    results_path: Path = DEFAULT_RESULTS,
    figure_dir: Path = DEFAULT_FIGURES,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Parse actual QE outputs and compare energy only within each phase pair."""
    selection = pd.read_csv(selection_path)
    rows: list[dict[str, Any]] = []
    for row in selection.itertuples(index=False):
        output_path = run_dir / str(row.fid) / "scf.out"
        if not output_path.is_file():
            raise FileNotFoundError(f"actual QE output missing: {output_path}")
        parsed = parse_qe_output(output_path)
        energy_per_atom = parsed["total_energy_eV"] / int(row.NIONS) if parsed["converged"] else math.nan
        rows.append(
            {
                "fid": row.fid,
                "phase": row.phase,
                "composition": row.composition,
                "NIONS": int(row.NIONS),
                "SRO": float(row.SRO),
                "low_high_label": row.low_high_label,
                "total_DFT_energy_eV": parsed["total_energy_eV"],
                "energy_per_atom_eV": energy_per_atom,
                "relative_energy_meV_atom": math.nan,
                "SCF_convergence_status": "converged" if parsed["converged"] else "not_converged",
                "magnetic_moment_muB": parsed["magnetic_moment_muB"],
            }
        )
    results = pd.DataFrame(rows)
    if len(results) != 4 or not results["SCF_convergence_status"].eq("converged").all():
        raise RuntimeError("all four actual SCF calculations must converge before Phase 7 analysis")
    for _, indices in results.groupby(["phase", "composition"], observed=True).groups.items():
        values = results.loc[indices, "energy_per_atom_eV"]
        results.loc[indices, "relative_energy_meV_atom"] = (values - values.min()) * 1000.0
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(results_path, index=False)
    figures = _save_dft_figures(results, figure_dir)

    lines = [
        "# Phase 7 targeted static-DFT comparison",
        "",
        "Four exact-source initial structures were compared using static Quantum ESPRESSO SCF calculations. Energies are normalized per atom and referenced only within each fixed-composition phase pair.",
        "",
    ]
    for phase in ("FCC", "BCC"):
        pair = results.loc[results["phase"].eq(phase)].sort_values("SRO")
        low, high = list(pair.itertuples(index=False))
        difference = abs(high.relative_energy_meV_atom - low.relative_energy_meV_atom)
        lower = pair.loc[pair["relative_energy_meV_atom"].idxmin()]
        trend = "increasing" if high.SRO > low.SRO else "decreasing"
        lines.extend(
            [
                f"## {phase}",
                "",
                f"Composition `{low.composition}`; {low.NIONS} atoms; SRO {low.SRO:.6f} ({low.fid}) versus {high.SRO:.6f} ({high.fid}).",
                "",
                f"For the selected fixed-composition {phase} configurations, {trend} SRO from {low.SRO:.6f} to {high.SRO:.6f} corresponded to an energy difference of {difference:.3f} meV/atom, with configuration `{lower.fid}` being lower in static DFT energy.",
                "",
            ]
        )
    lines.extend(
        [
            "## Scope",
            "",
            "These four selected configurations provide a targeted first-principles comparison and do not establish a universal causal SRO-energy relationship.",
            "",
            f"Machine-readable results: `{results_path.as_posix()}`. Figures: " + ", ".join(f"`{path}`" for path in figures) + ".",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"results": results_path.as_posix(), "figures": figures, "report": report_path.as_posix()}
