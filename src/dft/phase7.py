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
import shlex
import shutil
import subprocess
import time
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


def _engine_status(config: dict[str, Any]) -> tuple[bool, str | None]:
    executable = str(config.get("executable") or config.get("pw_x") or "pw.x")
    if str(config.get("execution", "native")).lower() == "wsl":
        conda = config.get("conda_executable")
        environment = config.get("conda_environment")
        if conda and environment:
            command = f"{shlex.quote(str(conda))} run -n {shlex.quote(str(environment))} which {shlex.quote(executable)}"
            result = subprocess.run(["wsl", "bash", "-lc", command], capture_output=True, text=True, check=False)
            resolved = result.stdout.strip().splitlines()[-1] if result.returncode == 0 and result.stdout.strip() else None
            if resolved == "/usr/bin/pw.x":
                return False, resolved
            return bool(resolved), resolved
        result = subprocess.run(["wsl", "bash", "-lc", f"test -x {shlex.quote(executable)}"], capture_output=True, check=False)
        return result.returncode == 0, executable if result.returncode == 0 else None
    resolved = shutil.which(executable)
    return bool(resolved), resolved


def inspect_dft_environment(
    config_path: Path = DEFAULT_CONFIG,
    pseudo_dir: Path | None = None,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    directory = Path(pseudo_dir or config.get("pseudo_dir") or "dft_pseudos")
    available = sorted([*directory.glob("*.UPF"), *directory.glob("*.upf")]) if directory.exists() else []
    missing, _ = _pseudopotential_status(config, directory) if config else (["configuration"], {})
    available_engine, executable = _engine_status(config)
    return {
        "pw_x": executable,
        "execution": config.get("execution", "native"),
        "vasp_std": shutil.which("vasp_std"),
        "pseudo_dir": directory.as_posix(),
        "pseudopotential_files": [path.name for path in available],
        "missing_setup": missing + ([] if available_engine else ["Quantum ESPRESSO pw.x executable"]),
        "ready": bool(available_engine and not missing),
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
        elif record.get("md5"):
            md5 = hashlib.md5(path.read_bytes()).hexdigest()
            if md5.lower() != str(record["md5"]).lower():
                raise ValueError(f"pseudopotential MD5 mismatch: {path}")
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
    configured_grid = config.get("kpoint_grid")
    if configured_grid:
        if len(configured_grid) != 3 or any(int(value) <= 0 for value in configured_grid):
            raise ValueError("kpoint_grid must contain three positive integers")
        grid = tuple(int(value) for value in configured_grid)
    else:
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
    pseudo_dir: Path | None = None,
) -> dict[str, Any]:
    """Write tracked templates, or runnable local inputs when PP data are complete."""
    selection = pd.read_csv(selection_path)
    if len(selection) != 4 or set(selection["phase"]) != {"FCC", "BCC"}:
        raise ValueError("DFT selection must contain exactly four FCC/BCC rows")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    pp_dir = Path(pseudo_dir or config.get("pseudo_dir") or "dft_pseudos")
    missing, pseudo_paths = _pseudopotential_status(config, pp_dir)
    engine_available, engine = _engine_status(config)
    template_only = bool(missing or not engine_available)
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
            calculation_dir = input_dir / "production" / str(row.fid)
            calculation_dir.mkdir(parents=True, exist_ok=True)
            path = calculation_dir / "scf.in"
            path.write_text(text, encoding="utf-8")
            metadata = {
                "fid": row.fid,
                "phase": row.phase,
                "composition": row.composition,
                "SRO": float(row.SRO),
                "NIONS": int(row.NIONS),
                "engine": "Quantum ESPRESSO pw.x",
                "qe_version": config.get("qe_version"),
                "execution": config.get("execution", "native"),
                "executable": engine,
                "conda_environment": config.get("conda_environment"),
                "pseudo_family": config["pseudo_family"],
                "pseudopotentials": config["pseudopotentials"],
                "ecutwfc_ry": config["ecutwfc_ry"],
                "ecutrho_ry": config["ecutrho_ry"],
                "kpoint_grid": config.get("kpoint_grid"),
                "kpoint_policy": config.get("kpoint_policy"),
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
        "missing_setup": missing + ([] if engine_available else ["Quantum ESPRESSO pw.x executable"]),
        "generated_inputs": generated,
    }


def _copy_runtime_files(
    fid: str,
    config: dict[str, Any],
    input_dir: Path,
    run_dir: Path,
    pseudo_dir: Path,
) -> Path:
    calculation_dir = run_dir / fid
    calculation_dir.mkdir(parents=True, exist_ok=True)
    (calculation_dir / "scratch").mkdir(exist_ok=True)
    local_pseudo = calculation_dir / "pseudopotentials"
    local_pseudo.mkdir(exist_ok=True)
    source_input = input_dir / "production" / fid / "scf.in"
    if not source_input.is_file():
        raise FileNotFoundError(f"production input missing: {source_input}")
    shutil.copy2(source_input, calculation_dir / "scf.in")
    _, pseudo_paths = _pseudopotential_status(config, pseudo_dir)
    for pp_path in pseudo_paths.values():
        shutil.copy2(pp_path, local_pseudo / pp_path.name)
    return calculation_dir


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if len(drive) != 1 or not drive.isalpha():
        raise RuntimeError(f"could not convert Windows path for WSL: {path}")
    relative = resolved.relative_to(resolved.anchor).as_posix()
    return f"/mnt/{drive}/{relative}"


def _wait_for_qe_output(output_path: Path, timeout_seconds: int = 7200) -> int:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if output_path.is_file():
            text = output_path.read_text(encoding="utf-8", errors="replace")
            if "JOB DONE." in text:
                return 0
            if "Error in routine" in text or "MPI_ABORT was invoked" in text:
                return 1
        time.sleep(5)
    raise TimeoutError(f"QE output did not terminate within {timeout_seconds} s: {output_path}")


def _execute_qe(calculation_dir: Path, config: dict[str, Any]) -> int:
    executable = str(config.get("executable") or config.get("pw_x") or "pw.x")
    if str(config.get("execution", "native")).lower() == "wsl":
        wsl_directory = _wsl_path(calculation_dir)
        conda = config.get("conda_executable")
        environment = config.get("conda_environment")
        if conda and environment:
            launch = (
                f"{shlex.quote(str(conda))} run --no-capture-output "
                f"-n {shlex.quote(str(environment))} {shlex.quote(executable)} -in scf.in"
            )
        else:
            launch = f"{shlex.quote(executable)} -in scf.in"
        command = (
            f"cd {shlex.quote(wsl_directory)} && "
            f"{launch} > scf.out 2>&1"
        )
        result = subprocess.run(["wsl", "bash", "-lc", command], check=False)
        if result.returncode not in (0, 1):
            return result.returncode
        return _wait_for_qe_output(calculation_dir / "scf.out")
    with (calculation_dir / "scf.in").open("rb") as source, (calculation_dir / "scf.out").open("wb") as sink:
        return subprocess.run(
            [executable], stdin=source, stdout=sink, stderr=subprocess.STDOUT,
            cwd=calculation_dir, check=False,
        ).returncode


def run_dft(
    selection_path: Path = DEFAULT_SELECTION,
    config_path: Path = DEFAULT_CONFIG,
    input_dir: Path = DEFAULT_INPUTS,
    run_dir: Path = DEFAULT_RUNS,
) -> dict[str, Any]:
    """Run the four already-prepared single-point QE inputs sequentially."""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    engine_available, _ = _engine_status(config)
    if not engine_available:
        raise RuntimeError("configured Quantum ESPRESSO pw.x executable is unavailable")
    pseudo_dir = Path(config.get("pseudo_dir") or "dft_pseudos")
    missing, _ = _pseudopotential_status(config, pseudo_dir)
    if missing:
        raise RuntimeError(f"pseudopotential setup incomplete: {missing}")
    selection = pd.read_csv(selection_path)
    completed: list[str] = []
    for fid in selection["fid"].astype(str):
        calculation_dir = _copy_runtime_files(fid, config, input_dir, run_dir, pseudo_dir)
        output_path = calculation_dir / "scf.out"
        parsed = parse_qe_output(output_path) if output_path.is_file() else {"converged": False, "normal_termination": False}
        if parsed["converged"] and parsed["normal_termination"]:
            returncode = 0
        else:
            returncode = _execute_qe(calculation_dir, config)
            parsed = parse_qe_output(output_path)
        if returncode != 0:
            raise RuntimeError(f"pw.x failed for {fid}; inspect {output_path}")
        if not parsed["converged"] or not parsed["normal_termination"]:
            raise RuntimeError(f"SCF did not converge normally for {fid}; inspect {output_path}")
        metadata_path = input_dir / "production" / fid / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["runtime_result"] = parsed
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        completed.append(fid)
    return {"completed": completed, "run_dir": run_dir.as_posix()}


def run_cutoff_sanity_check(
    fid: str = "gra62121526",
    cutoffs_ry: tuple[float, ...] = (45.0, 55.0, 65.0),
    config_path: Path = DEFAULT_CONFIG,
    structure_dir: Path = DEFAULT_STRUCTURES,
    run_dir: Path = DEFAULT_RUNS / "cutoff_sanity",
    output_path: Path = Path("results/tables/dft/cutoff_sanity_check.csv"),
    figure_path: Path = Path("figures/dft/cutoff_sanity_check.png"),
    smoke_output: Path = DEFAULT_RUNS / "smoke_test" / "gra62121526" / "scf.out",
    smoke_cutoff_ry: float = 45.0,
    stopped_near_converged_cutoff_ry: float = 65.0,
) -> dict[str, Any]:
    """Run a three-point cutoff check on one exact selected structure."""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    engine_available, _ = _engine_status(config)
    if not engine_available:
        raise RuntimeError("configured Quantum ESPRESSO pw.x executable is unavailable")
    pseudo_dir = Path(config.get("pseudo_dir") or "dft_pseudos")
    missing, pseudo_paths = _pseudopotential_status(config, pseudo_dir)
    if missing:
        raise RuntimeError(f"pseudopotential setup incomplete: {missing}")
    payload = _load_structure_copy(structure_dir / f"{fid}.json")
    rows: list[dict[str, Any]] = []
    for cutoff in cutoffs_ry:
        trial = dict(config)
        trial["ecutwfc_ry"] = float(cutoff)
        trial["ecutrho_ry"] = float(cutoff) * 8.0
        if math.isclose(float(cutoff), float(smoke_cutoff_ry)) and smoke_output.is_file():
            parsed = parse_qe_output(smoke_output)
            returncode = 0 if parsed["converged"] and parsed["normal_termination"] else 1
        else:
            calculation_dir = run_dir / fid / f"{cutoff:g}Ry"
            calculation_dir.mkdir(parents=True, exist_ok=True)
            (calculation_dir / "scratch").mkdir(exist_ok=True)
            local_pseudo = calculation_dir / "pseudopotentials"
            local_pseudo.mkdir(exist_ok=True)
            for pp_path in pseudo_paths.values():
                shutil.copy2(pp_path, local_pseudo / pp_path.name)
            (calculation_dir / "scf.in").write_text(build_qe_input(payload, trial, template=False), encoding="utf-8")
            trial_output = calculation_dir / "scf.out"
            parsed = parse_qe_output(trial_output) if trial_output.is_file() else {
                "converged": False,
                "normal_termination": False,
                "latest_total_energy_eV": math.nan,
            }
            if parsed["converged"] and parsed["normal_termination"]:
                returncode = 0
            elif (
                math.isclose(float(cutoff), float(stopped_near_converged_cutoff_ry))
                and math.isfinite(parsed["latest_total_energy_eV"])
            ):
                # The user intentionally stopped this optional endpoint after its
                # energy stabilized close to, but above, the formal SCF threshold.
                # Preserve and label it; never restart it implicitly.
                returncode = 2
            else:
                returncode = _execute_qe(calculation_dir, trial)
                parsed = parse_qe_output(trial_output)
        converged = returncode == 0 and parsed["converged"] and parsed["normal_termination"]
        near_converged = (
            returncode == 2
            and not converged
            and math.isfinite(parsed["latest_total_energy_eV"])
        )
        energy_eV = parsed["total_energy_eV"] if converged else parsed.get("latest_total_energy_eV", math.nan)
        rows.append(
            {
                "fid": fid,
                "ecutwfc_ry": float(cutoff),
                "ecutrho_ry": float(cutoff) * 8.0,
                "total_energy_eV": energy_eV,
                "energy_per_atom_eV": energy_eV / int(payload["NIONS"]) if converged or near_converged else math.nan,
                "relative_energy_change_meV_atom": math.nan,
                "convergence_status": "formally_converged" if converged else "near_converged_not_formal" if near_converged else "failed",
                "normal_termination": bool(parsed["normal_termination"]),
                "latest_estimated_scf_error_ry": parsed.get("latest_estimated_scf_error_ry", math.nan),
            }
        )
        if not converged and not near_converged:
            raise RuntimeError(f"cutoff sanity calculation failed at {cutoff:g} Ry")
    results = pd.DataFrame(rows).sort_values("ecutwfc_ry")
    reference = results.iloc[-1]["energy_per_atom_eV"]
    results["relative_energy_change_meV_atom"] = (results["energy_per_atom_eV"] - reference) * 1000.0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path, index=False)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5.8, 4.0))
    ax.plot(results["ecutwfc_ry"], results["relative_energy_change_meV_atom"], marker="o", color="#2878B5")
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set(xlabel="Wavefunction cutoff (Ry)", ylabel="Energy change vs 65 Ry (meV/atom)", title="Cutoff sanity check: FCC low-SRO structure")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(figure_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return {"table": output_path.as_posix(), "figure": figure_path.as_posix(), "rows": len(results)}


def parse_qe_output(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    energies = re.findall(r"!\s+total energy\s+=\s+([-+0-9.Ee]+)\s+Ry", text)
    latest_energies = re.findall(r"^\s*!?\s*total energy\s+=\s+([-+0-9.Ee]+)\s+Ry", text, re.MULTILINE)
    estimated_errors = re.findall(r"estimated scf accuracy\s+<\s+([-+0-9.Ee]+)\s+Ry", text)
    moments = re.findall(r"total magnetization\s+=\s+([-+0-9.Ee]+)", text)
    absolute_moments = re.findall(r"absolute magnetization\s+=\s+([-+0-9.Ee]+)", text)
    iterations = re.findall(r"convergence has been achieved in\s+(\d+)\s+iterations", text)
    failure_markers = re.findall(
        r"Error in routine|MPI_ABORT|\bNaN\b|convergence NOT achieved|segmentation fault|SIGSEGV",
        text,
        flags=re.IGNORECASE,
    )
    converged = "convergence has been achieved" in text and bool(energies)
    energy_ry = float(energies[-1]) if energies else math.nan
    latest_energy_ry = float(latest_energies[-1]) if latest_energies else math.nan
    return {
        "converged": converged,
        "normal_termination": "JOB DONE." in text,
        "total_energy_ry": energy_ry,
        "total_energy_eV": energy_ry * RY_TO_EV if math.isfinite(energy_ry) else math.nan,
        "latest_total_energy_ry": latest_energy_ry,
        "latest_total_energy_eV": latest_energy_ry * RY_TO_EV if math.isfinite(latest_energy_ry) else math.nan,
        "latest_estimated_scf_error_ry": float(estimated_errors[-1]) if estimated_errors else math.nan,
        "magnetic_moment_muB": float(moments[-1]) if moments else math.nan,
        "absolute_magnetization_muB": float(absolute_moments[-1]) if absolute_moments else math.nan,
        "scf_iterations": int(iterations[-1]) if iterations else None,
        "failure_markers": failure_markers,
    }


def _save_dft_figures(results: pd.DataFrame, figure_dir: Path) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    figure_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    colors = {"FCC": "#2878B5", "BCC": "#D95319"}

    order_map = {("FCC", "low"): 0, ("FCC", "high"): 1, ("BCC", "low"): 2, ("BCC", "high"): 3}
    order = results.assign(
        _plot_order=[order_map[(row.phase, row.low_high_label)] for row in results.itertuples()]
    ).sort_values("_plot_order")
    labels = [f"{row.phase} {row.low_high_label}\nSRO={row.SRO:.3f}" for row in order.itertuples()]
    x_positions = np.asarray([0.0, 1.0, 2.8, 3.8])
    fig, ax = plt.subplots(figsize=(7.4, 4.5))
    bars = ax.bar(
        x_positions,
        order["relative_energy_meV_atom"],
        width=0.72,
        color=[colors[p] for p in order["phase"]],
    )
    ax.bar_label(bars, fmt="%.2f", padding=3)
    ax.set_xticks(x_positions, labels)
    ax.axvline(1.9, color="#777777", linewidth=0.8, linestyle="--")
    ax.set_ylabel("Relative static DFT energy (meV/atom)")
    ax.set_title("Static energy differences within FCC and BCC Co-Cr pairs")
    ax.legend(
        handles=[Patch(facecolor=colors["FCC"], label="FCC"), Patch(facecolor=colors["BCC"], label="BCC")],
        frameon=False,
    )
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
    ax.set(
        xlabel="Aggregate first-shell SRO magnitude",
        ylabel="Relative static DFT energy (meV/atom)",
        title="SRO magnitude and static energy within phase pairs",
    )
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = figure_dir / "sro_vs_relative_energy.png"
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
    config_path: Path = DEFAULT_CONFIG,
    cutoff_table_path: Path = Path("results/tables/dft/cutoff_sanity_check.csv"),
) -> dict[str, Any]:
    """Parse actual QE outputs and compare energy only within each phase pair."""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    selection = pd.read_csv(selection_path)
    rows: list[dict[str, Any]] = []
    for row in selection.itertuples(index=False):
        output_path = run_dir / str(row.fid) / "scf.out"
        if not output_path.is_file():
            raise FileNotFoundError(f"actual QE output missing: {output_path}")
        parsed = parse_qe_output(output_path)
        valid = (
            parsed["converged"]
            and parsed["normal_termination"]
            and math.isfinite(parsed["total_energy_ry"])
            and not parsed["failure_markers"]
        )
        energy_per_atom_ry = parsed["total_energy_ry"] / int(row.NIONS) if valid else math.nan
        energy_per_atom_eV = energy_per_atom_ry * RY_TO_EV if valid else math.nan
        rows.append(
            {
                "fid": row.fid,
                "phase": row.phase,
                "composition": row.composition,
                "NIONS": int(row.NIONS),
                "SRO": float(row.SRO),
                "low_high_label": row.low_high_label,
                "total_energy_ry": parsed["total_energy_ry"],
                "energy_per_atom_ry": energy_per_atom_ry,
                "total_energy_eV": parsed["total_energy_eV"],
                "energy_per_atom_eV": energy_per_atom_eV,
                "relative_energy_meV_atom": math.nan,
                "SCF_convergence_status": "converged" if valid else "not_converged",
                "normal_termination": parsed["normal_termination"],
                "scf_iterations": parsed["scf_iterations"],
                "total_magnetization_muB_cell": parsed["magnetic_moment_muB"],
                "absolute_magnetization_muB_cell": parsed["absolute_magnetization_muB"],
                "failure_marker_count": len(parsed["failure_markers"]),
            }
        )
    results = pd.DataFrame(rows)
    if len(results) != 4 or not results["SCF_convergence_status"].eq("converged").all():
        raise RuntimeError("all four actual SCF calculations must converge before Phase 7 analysis")
    for _, indices in results.groupby(["phase", "composition"], observed=True).groups.items():
        values = results.loc[indices, "energy_per_atom_ry"]
        results.loc[indices, "relative_energy_meV_atom"] = (values - values.min()) * RY_TO_EV * 1000.0
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(results_path, index=False)
    figures = _save_dft_figures(results, figure_dir)

    lines = [
        "# Phase 7 targeted static-DFT comparison",
        "",
        "Four exact-source initial structures were compared using static Quantum ESPRESSO SCF calculations. Energies are normalized per atom and referenced only within each fixed-composition phase pair.",
        "",
        "## Calculation policy",
        "",
        f"- Engine: Quantum ESPRESSO {config['qe_version']} `pw.x` from the WSL Conda environment `{config['conda_environment']}` (`{config['resolved_executable']}`), not `/usr/bin/pw.x`.",
        f"- Pseudopotentials: {config['pseudo_family']} ({config['exchange_correlation']}); Co `{config['pseudopotentials']['Co']['filename']}` and Cr `{config['pseudopotentials']['Cr']['filename']}`.",
        f"- Cutoffs: `ecutwfc = {config['ecutwfc_ry']:g} Ry`, `ecutrho = {config['ecutrho_ry']:g} Ry`.",
        f"- Brillouin-zone sampling: `{config['kpoint_grid'][0]} x {config['kpoint_grid'][1]} x {config['kpoint_grid'][2]}` Monkhorst-Pack grid for every two-atom cell.",
        f"- Metallic occupations: Marzari-Vanderbilt smearing with `degauss = {config['degauss_ry']:g} Ry`; electronic threshold `conv_thr = {config['conv_thr']:.0e}`.",
        f"- Spin treatment: spin polarized, with deterministic starting magnetizations Co `{config['starting_magnetization']['Co']:+g}` and Cr `{config['starting_magnetization']['Cr']:+g}`.",
        "- Geometry: static SCF on the exact source initial cells and fractional coordinates; no relaxation was performed.",
        "",
    ]
    if cutoff_table_path.is_file():
        cutoff = pd.read_csv(cutoff_table_path)
        cutoff_rows = [
            "| ecutwfc (Ry) | ecutrho (Ry) | energy/atom (eV) | change vs 65 Ry (meV/atom) | status |",
            "|---:|---:|---:|---:|---|",
        ]
        for row in cutoff.itertuples(index=False):
            cutoff_rows.append(
                f"| {row.ecutwfc_ry:.0f} | {row.ecutrho_ry:.0f} | {row.energy_per_atom_eV:.8f} | "
                f"{row.relative_energy_change_meV_atom:.4f} | {row.convergence_status} |"
            )
        lines.extend(
            [
                "## Cutoff sanity check",
                "",
                *cutoff_rows,
                "",
                "At the production-selection checkpoint, 55 Ry was formally converged and the 65 Ry calculation had been manually stopped near convergence; the checkpoint energy-difference magnitude was 1.78684 meV/atom. A pre-existing background process subsequently continued the 65 Ry job to formal convergence without a restart, giving a final 55-to-65 Ry difference of 1.77214 meV/atom. This does not change the selected 55/440 Ry production setting or the preliminary-study conclusion.",
                "",
                f"The cutoff decision and checkpoint are recorded in `{config_path.as_posix()}`; the machine-readable final audit is `{cutoff_table_path.as_posix()}`.",
                "",
            ]
        )
    result_rows = [
        "| Phase | Label | fid | SRO | total energy (Ry) | energy/atom (Ry) | relative energy (meV/atom) | total magnetization (muB/cell) | absolute magnetization (muB/cell) | iterations | status |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in results.itertuples(index=False):
        result_rows.append(
            f"| {row.phase} | {row.low_high_label} | `{row.fid}` | {row.SRO:.6f} | {row.total_energy_ry:.8f} | "
            f"{row.energy_per_atom_ry:.8f} | {row.relative_energy_meV_atom:.4f} | "
            f"{row.total_magnetization_muB_cell:.4f} | {row.absolute_magnetization_muB_cell:.4f} | "
            f"{row.scf_iterations} | {row.SCF_convergence_status} |"
        )
    lines.extend(
        [
            "## Converged results",
            "",
            *result_rows,
            "",
            "All four calculations reached the electronic convergence criterion, printed a finite final total energy, and terminated normally with `JOB DONE`.",
            "",
        ]
    )
    for phase in ("FCC", "BCC"):
        pair = results.loc[results["phase"].eq(phase)].sort_values("SRO")
        low, high = list(pair.itertuples(index=False))
        difference = abs(high.relative_energy_meV_atom - low.relative_energy_meV_atom)
        lower = pair.loc[pair["relative_energy_meV_atom"].idxmin()]
        lines.extend(
            [
                f"## {phase}",
                "",
                f"Composition `{low.composition}`; {low.NIONS} atoms; SRO {low.SRO:.6f} ({low.fid}) versus {high.SRO:.6f} ({high.fid}).",
                "",
                f"For the selected fixed-composition Co-Cr {phase} configurations, increasing the aggregate first-shell SRO magnitude from {low.SRO:.4f} to {high.SRO:.4f} changed the static DFT energy by {difference:.3f} meV/atom. The {lower.low_high_label}-SRO configuration (`{lower.fid}`) was energetically lower.",
                "",
            ]
        )
    lines.extend(
        [
            "## Scope",
            "",
            "These targeted calculations demonstrate that configurations with identical chemistry and atom count but different local ordering can exhibit different first-principles energies. The four-configuration study is a focused validation/extension of the larger SRO-ML analysis and should not be interpreted as establishing a universal causal SRO-energy relationship.",
            "",
            f"Machine-readable results: `{results_path.as_posix()}`. Figures: " + ", ".join(f"`{path}`" for path in figures) + ".",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"results": results_path.as_posix(), "figures": figures, "report": report_path.as_posix()}
