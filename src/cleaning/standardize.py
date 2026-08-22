"""Small, dependency-free standardizers used by ingestion stages."""

from __future__ import annotations

import re


_FORMULA_TOKEN = re.compile(r"([A-Z][a-z]?)(\d*\.?\d*)")


def parse_formula_fractions(formula: str) -> dict[str, float]:
    """Convert a compact formula such as ``Cr1Co1Ni1`` to atomic fractions."""
    if not formula or not isinstance(formula, str):
        raise ValueError("formula must be a non-empty string")
    position = 0
    amounts: dict[str, float] = {}
    for match in _FORMULA_TOKEN.finditer(formula):
        if match.start() != position:
            raise ValueError(f"unparsed formula segment in {formula!r}")
        element, raw_amount = match.groups()
        amount = float(raw_amount) if raw_amount else 1.0
        if amount <= 0:
            raise ValueError(f"non-positive amount for {element}")
        amounts[element] = amounts.get(element, 0.0) + amount
        position = match.end()
    if position != len(formula) or not amounts:
        raise ValueError(f"cannot parse formula {formula!r}")
    total = sum(amounts.values())
    return {element: amount / total for element, amount in sorted(amounts.items())}


def normalize_phase(value: str | None) -> str:
    normalized = (value or "").strip().upper()
    return normalized if normalized in {"FCC", "BCC", "HCP"} else "UNKNOWN"


def canonical_pair(element_a: str, element_b: str) -> tuple[str, str]:
    if not element_a or not element_b:
        raise ValueError("both pair elements are required")
    return tuple(sorted((element_a.strip(), element_b.strip())))
