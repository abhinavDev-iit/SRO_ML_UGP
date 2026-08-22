"""Read-only, streaming inventory profiler for the raw SRO sources."""

from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path("data/raw")
OUT = Path("reports/data_inventory_metrics.json")
TRACK_UNIQUES = {
    "fid", "reduced_formula", "chemical_system", "lattice", "nelements",
    "NIONS", "space_group_number", "space_group_number_ini",
}


def tree_summary() -> dict:
    datasets = {}
    extensions = Counter()
    for dataset in sorted(p for p in ROOT.iterdir() if p.is_dir()):
        files = [p for p in dataset.rglob("*") if p.is_file()]
        ext = Counter((p.suffix.lower() or "[no extension]") for p in files)
        extensions.update(ext)
        sizes = [p.stat().st_size for p in files]
        datasets[dataset.name] = {
            "file_count": len(files),
            "total_bytes": sum(sizes),
            "largest_file_bytes": max(sizes, default=0),
            "extensions": dict(ext.most_common()),
        }
    return {"datasets": datasets, "extensions": dict(extensions.most_common())}


def profile_csv(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        missing = [0] * len(header)
        uniques = {name: set() for name in header if name in TRACK_UNIQUES}
        duplicate_first_key = 0
        seen_key = set()
        malformed = 0
        rows = 0
        for row in reader:
            rows += 1
            if len(row) != len(header):
                malformed += 1
                if len(row) < len(header):
                    row += [""] * (len(header) - len(row))
                else:
                    row = row[: len(header)]
            for i, value in enumerate(row):
                if value.strip() == "" or value.strip().lower() in {"nan", "none", "null"}:
                    missing[i] += 1
            if row:
                key = row[0]
                if key in seen_key:
                    duplicate_first_key += 1
                else:
                    seen_key.add(key)
            for name, values in uniques.items():
                values.add(row[header.index(name)])
    return {
        "bytes": path.stat().st_size,
        "rows": rows,
        "columns": len(header),
        "column_names": header,
        "missing_by_column": dict(zip(header, missing)),
        "unique_counts": {k: len(v) for k, v in uniques.items()},
        "unique_values_small": {k: sorted(v) for k, v in uniques.items() if len(v) <= 30},
        "duplicate_first_column_keys": duplicate_first_key,
        "malformed_rows": malformed,
    }


def main() -> None:
    result = {"tree": tree_summary(), "csv": {}}
    for path in sorted(ROOT.rglob("*.csv")):
        rel = path.as_posix()
        result["csv"][rel] = profile_csv(path)
    hea_dir = ROOT / "dataset_84k_hea"
    key_sets = {}
    distributions = {}
    for name in ("hea.2023-04-06.csv", "SROs_structure_ini.csv", "structure_featurized.dat_all.csv", "structure_ini_featurized.dat_all.csv"):
        with (hea_dir / name).open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            key = reader.fieldnames[0]
            keys, lattice, nions, chemical_systems = set(), Counter(), Counter(), set()
            for row in reader:
                keys.add(row[key])
                lattice[row.get("lattice", "")] += 1
                nions[row.get("NIONS", "")] += 1
                chemical_systems.add(row.get("chemical_system", ""))
        key_sets[name] = keys
        distributions[name] = {
            "key": key, "lattice": dict(lattice), "NIONS": dict(nions),
            "chemical_system_count": len(chemical_systems - {""}),
        }
    overlaps = {}
    names = list(key_sets)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            overlaps[f"{a} <> {b}"] = {
                "intersection": len(key_sets[a] & key_sets[b]),
                "left_only": len(key_sets[a] - key_sets[b]),
                "right_only": len(key_sets[b] - key_sets[a]),
            }
    result["hea_84k_relationships"] = {"distributions": distributions, "key_overlaps": overlaps}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT),
        "csv_files_profiled": len(result["csv"]),
        "datasets": result["tree"]["datasets"],
        "csv_summary": {k: {x: v[x] for x in ("rows", "columns", "duplicate_first_column_keys", "malformed_rows")} for k, v in result["csv"].items()},
    }, indent=2))


if __name__ == "__main__":
    main()
