"""Leakage-controlled feature engineering for the 84k HEA collection."""

from __future__ import annotations

from itertools import combinations_with_replacement
from typing import Iterable

import numpy as np
import pandas as pd

from src.cleaning.standardize import parse_formula_fractions


ELEMENTS = ("Al", "Co", "Cr", "Cu", "Fe", "Mn", "Ni", "Si")
R_GAS = 8.31446261815324

# Recover these elemental values from the source table's own MagpieData means.
# This avoids silently mixing an external elemental-property convention into the
# supplied feature space.
PROPERTY_COLUMNS = {
    "atomic_number": "MagpieData mean Number",
    "atomic_mass": "MagpieData mean AtomicWeight",
    "atomic_radius_covalent": "MagpieData mean CovalentRadius",
    "electronegativity": "MagpieData mean Electronegativity",
    "vec": "MagpieData mean NValence",
    "melting_point": "MagpieData mean MeltingT",
}


def composition_matrix(formulas: Iterable[str]) -> pd.DataFrame:
    rows = [parse_formula_fractions(value) for value in formulas]
    return pd.DataFrame(rows, columns=ELEMENTS).fillna(0.0).astype("float64")


def recover_elemental_reference(
    compositions: pd.DataFrame, source: pd.DataFrame
) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    """Recover property values from supplied composition-weighted means.

    Returns the per-element reference and maximum absolute reconstruction error.
    The overdetermined least-squares solution must reproduce every supplied mean
    to tight numerical tolerance before engineered property features are used.
    """
    matrix = compositions.loc[:, ELEMENTS].to_numpy(dtype=float)
    reference: dict[str, dict[str, float]] = {}
    errors: dict[str, float] = {}
    for name, column in PROPERTY_COLUMNS.items():
        values = pd.to_numeric(source[column], errors="coerce").to_numpy(dtype=float)
        mask = np.isfinite(values)
        solved, *_ = np.linalg.lstsq(matrix[mask], values[mask], rcond=None)
        predicted = matrix[mask] @ solved
        error = float(np.max(np.abs(predicted - values[mask])))
        reference[name] = {element: float(value) for element, value in zip(ELEMENTS, solved)}
        errors[name] = error
    return reference, errors


def _weighted_property_features(
    compositions: pd.DataFrame, reference: dict[str, dict[str, float]]
) -> pd.DataFrame:
    c = compositions.loc[:, ELEMENTS].to_numpy(dtype=float)
    output: dict[str, np.ndarray] = {}
    for property_name, values_by_element in reference.items():
        values = np.array([values_by_element[element] for element in ELEMENTS], dtype=float)
        mean = c @ values
        variance = np.sum(c * (values[None, :] - mean[:, None]) ** 2, axis=1)
        output[f"derived_{property_name}_mean"] = mean
        output[f"derived_{property_name}_std"] = np.sqrt(np.maximum(variance, 0.0))

        pair_weight = np.zeros(len(c), dtype=float)
        pair_abs = np.zeros(len(c), dtype=float)
        pair_sq = np.zeros(len(c), dtype=float)
        for i in range(len(ELEMENTS)):
            for j in range(i + 1, len(ELEMENTS)):
                weight = 2.0 * c[:, i] * c[:, j]
                difference = abs(values[i] - values[j])
                pair_weight += weight
                pair_abs += weight * difference
                pair_sq += weight * difference * difference
        valid = pair_weight > 0
        mean_abs = np.zeros(len(c), dtype=float)
        rms = np.zeros(len(c), dtype=float)
        mean_abs[valid] = pair_abs[valid] / pair_weight[valid]
        rms[valid] = np.sqrt(pair_sq[valid] / pair_weight[valid])
        output[f"pair_{property_name}_mean_abs_diff"] = mean_abs
        output[f"pair_{property_name}_rms_diff"] = rms

    radius = np.array(
        [reference["atomic_radius_covalent"][element] for element in ELEMENTS], dtype=float
    )
    radius_mean = c @ radius
    output["atomic_size_mismatch_percent"] = 100.0 * np.sqrt(
        np.sum(c * (1.0 - radius[None, :] / radius_mean[:, None]) ** 2, axis=1)
    )
    return pd.DataFrame(output, index=compositions.index)


def engineer_features(
    source: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict[str, float]], dict[str, float]]:
    """Return wide candidate features, provenance, reference values and QA errors."""
    compositions = composition_matrix(source["formula"])
    compositions.index = source.index
    reference, errors = recover_elemental_reference(compositions, source)

    source_features: dict[str, pd.Series] = {}
    provenance: list[dict[str, object]] = []

    excluded_text = {"fid", "reduced_formula", "chemical_system", "lattice", "formula"}
    for column in source.columns:
        if column in excluded_text:
            continue
        values = pd.to_numeric(source[column], errors="coerce")
        if values.notna().sum() == 0:
            continue
        source_features[column] = values
        if column == "space_group_number_ini" or "CN_VoronoiNN" in column or "local difference" in column or column in {
            "mean absolute deviation in relative bond length", "max relative bond length",
            "min relative bond length", "minimum neighbor distance variation",
            "maximum neighbor distance variation", "range neighbor distance variation",
            "mean neighbor distance variation", "avg_dev neighbor distance variation",
            "mean absolute deviation in relative cell size", "max packing efficiency",
        }:
            origin = "structure-derived"
        elif column.startswith("MagpieData ") or "valence electrons" in column or "ionic char" in column:
            origin = "elemental-reference-derived"
        elif column.endswith("-norm") or column == "compound possible":
            origin = "composition-derived"
        else:
            origin = "direct source"
        provenance.append({"feature": column, "origin": origin, "source_field": column})

    engineered: dict[str, object] = {}
    for element in ELEMENTS:
        name = f"composition_fraction_{element}"
        engineered[name] = compositions[element]
        provenance.append({"feature": name, "origin": "composition-derived", "source_field": "formula"})

    c = compositions.to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = np.where(c > 0, c * np.log(c), 0.0)
    entropy_kb = -terms.sum(axis=1)
    n_elements = (c > 0).sum(axis=1)
    engineered["composition_number_of_elements"] = n_elements
    engineered["configurational_entropy_kb_per_atom"] = entropy_kb
    engineered["configurational_entropy_j_mol_k"] = entropy_kb * R_GAS
    engineered["configurational_entropy_normalized"] = entropy_kb / np.log(n_elements)
    for name in (
        "composition_number_of_elements", "configurational_entropy_kb_per_atom",
        "configurational_entropy_j_mol_k", "configurational_entropy_normalized",
    ):
        provenance.append({"feature": name, "origin": "composition-derived", "source_field": "formula"})

    for a, b in combinations_with_replacement(range(len(ELEMENTS)), 2):
        ea, eb = ELEMENTS[a], ELEMENTS[b]
        name = f"pair_fraction_{ea}_{eb}"
        engineered[name] = c[:, a] ** 2 if a == b else 2.0 * c[:, a] * c[:, b]
        provenance.append({"feature": name, "origin": "composition-derived", "source_field": "formula"})

    derived = _weighted_property_features(compositions, reference)
    for column in derived.columns:
        engineered[column] = derived[column]
        provenance.append({
            "feature": column,
            "origin": "elemental-reference-derived",
            "source_field": PROPERTY_COLUMNS.get(column.removeprefix("derived_").removesuffix("_mean"), "formula + reconstructed Magpie reference"),
        })

    engineered["phase_FCC"] = (source["lattice"].str.upper() == "FCC").astype("int8")
    engineered["phase_BCC"] = (source["lattice"].str.upper() == "BCC").astype("int8")
    for name in ("phase_FCC", "phase_BCC"):
        provenance.append({"feature": name, "origin": "direct source", "source_field": "lattice"})

    output = pd.concat(
        [pd.DataFrame(source_features, index=source.index), pd.DataFrame(engineered, index=source.index)],
        axis=1,
    )
    output.insert(0, "fid", source["fid"].astype(str))
    provenance_df = pd.DataFrame(provenance).drop_duplicates("feature").sort_values("feature")
    if len(provenance_df) != len(output.columns) - 1:
        raise ValueError("every candidate feature must have exactly one provenance record")
    return output, provenance_df, reference, errors
