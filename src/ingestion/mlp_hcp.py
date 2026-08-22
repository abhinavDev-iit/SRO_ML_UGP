"""Audit and provisionally reconstruct HCP WC-SRO from MLP-cSRO CFG files."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import numpy as np
import pandas as pd


TYPE_TO_ELEMENT = {0: "Cr", 1: "Co", 2: "Ni"}


def cfg_blocks(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return ["BEGIN_CFG" + block for block in text.split("BEGIN_CFG")[1:]]


def block_hash(block: str) -> str:
    return hashlib.sha256(block.encode("utf-8")).hexdigest()


def parse_cfg_block(block: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lines = block.splitlines()
    size_index = next(i for i, line in enumerate(lines) if line.strip() == "Size")
    size = int(lines[size_index + 1].strip())
    cell_index = next(i for i, line in enumerate(lines) if line.strip() == "Supercell")
    cell = np.array([[float(value) for value in lines[cell_index + j].split()] for j in range(1, 4)])
    atom_index = next(i for i, line in enumerate(lines) if line.strip().startswith("AtomData:"))
    atom_rows = [lines[atom_index + j].split() for j in range(1, size + 1)]
    types = np.array([int(row[1]) for row in atom_rows], dtype=int)
    positions = np.array([[float(value) for value in row[2:5]] for row in atom_rows], dtype=float)
    return cell, positions, types


def first_shell_neighbors(cell: np.ndarray, positions: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Find 12 HCP nearest neighbours using periodic images and report shell gap."""
    translations = np.array(
        [i * cell[0] + j * cell[1] + k * cell[2] for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)]
    )
    n = len(positions)
    distances = np.full((n, n), np.inf, dtype=float)
    for shift in translations:
        delta = positions[None, :, :] + shift - positions[:, None, :]
        trial = np.sqrt(np.sum(delta * delta, axis=2))
        distances = np.minimum(distances, trial)
    np.fill_diagonal(distances, np.inf)
    order = np.argsort(distances, axis=1)
    neighbors = order[:, :12]
    sorted_distances = np.take_along_axis(distances, order[:, :13], axis=1)
    ratios = sorted_distances[:, 12] / sorted_distances[:, 11]
    return neighbors, float(np.min(ratios)), float(np.median(ratios))


def warren_cowley(types: np.ndarray, neighbors: np.ndarray) -> dict[str, float]:
    fractions = {kind: float(np.mean(types == kind)) for kind in TYPE_TO_ELEMENT}
    result: dict[str, float] = {}
    for a in TYPE_TO_ELEMENT:
        centers = np.flatnonzero(types == a)
        for b in range(a, len(TYPE_TO_ELEMENT)):
            probability = float(np.mean(types[neighbors[centers]] == b))
            result[f"wc_{TYPE_TO_ELEMENT[a]}_{TYPE_TO_ELEMENT[b]}"] = 1.0 - probability / fractions[b]
    return result


def audit_mlp_hcp(ts4_path: Path, ts5_path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    ts4_hashes = {block_hash(block) for block in cfg_blocks(ts4_path)}
    additions = [(index, block) for index, block in enumerate(cfg_blocks(ts5_path)) if block_hash(block) not in ts4_hashes]
    rows: list[dict[str, object]] = []
    for source_index, block in additions:
        cell, positions, types = parse_cfg_block(block)
        neighbors, min_gap, median_gap = first_shell_neighbors(cell, positions)
        counts = {TYPE_TO_ELEMENT[kind]: int(np.sum(types == kind)) for kind in TYPE_TO_ELEMENT}
        row: dict[str, object] = {
            "configuration_id": f"mlp_csro_ts5_cfg_{source_index:04d}",
            "source_cfg_index": source_index,
            "phase": "HCP",
            "formula": "Cr48Co48Ni48",
            "chemical_system": "Co-Cr-Ni",
            "temperature_K": 500.0,
            "number_of_atoms": len(types),
            "count_Cr": counts["Cr"], "count_Co": counts["Co"], "count_Ni": counts["Ni"],
            "first_shell_coordination": 12,
            "minimum_d13_over_d12": min_gap,
            "median_d13_over_d12": median_gap,
            "wc_status": "reconstructed_unvalidated_against_author_reference",
            "block_sha256": block_hash(block),
        }
        row.update(warren_cowley(types, neighbors))
        rows.append(row)
    frame = pd.DataFrame(rows)
    summary = {
        "candidate_configurations": int(len(frame)),
        "all_144_atoms": bool((frame["number_of_atoms"] == 144).all()),
        "all_equiatomic": bool((frame[["count_Cr", "count_Co", "count_Ni"]] == 48).all().all()),
        "minimum_shell_gap_ratio": float(frame["minimum_d13_over_d12"].min()),
        "median_shell_gap_ratio": float(frame["median_d13_over_d12"].median()),
        "configurations_with_shell_gap_below_1_02": int((frame["minimum_d13_over_d12"] < 1.02).sum()),
        "validated_reference_arrays_available": False,
        "validated_hcp_observations": 0,
    }
    return frame, summary
