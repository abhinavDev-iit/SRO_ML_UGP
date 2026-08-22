"""Profile nested MLP-cSRO CFG training sets without loading atom arrays."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path("data/raw/mlp_csro/MLP-cSRO-main/training_datasets")
OUT = Path("reports/mlp_csro_cfg_inventory.json")


def blocks(path: Path):
    current = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith("BEGIN_CFG") and current:
                yield "".join(current)
                current = []
            current.append(line)
        if current:
            yield "".join(current)


def profile(path: Path) -> dict:
    hashes, sizes = [], []
    for block in blocks(path):
        hashes.append(hashlib.sha256(block.encode()).hexdigest())
        match = re.search(r"\n Size\s*\n\s*(\d+)", block)
        sizes.append(int(match.group(1)) if match else None)
    return {
        "bytes": path.stat().st_size,
        "configurations": len(hashes),
        "atom_counts": {str(size): sizes.count(size) for size in sorted(set(sizes), key=lambda x: (-1 if x is None else x))},
        "sha256_blocks": hashes,
    }


def main() -> None:
    files = {p.name: profile(p) for p in sorted(ROOT.glob("*.cfg"))}
    sets = {name: set(info["sha256_blocks"]) for name, info in files.items()}
    comparisons = {}
    for left, right in [
        ("Training_TS-4_Cao.cfg", "Training_TS-5_Cao.cfg"),
        ("Training_TS-5_Cao.cfg", "Training_TS-f_Cao.cfg"),
    ]:
        comparisons[f"{left} -> {right}"] = {
            "shared_exact_blocks": len(sets[left] & sets[right]),
            "left_only": len(sets[left] - sets[right]),
            "right_only": len(sets[right] - sets[left]),
        }
    result = {"files": files, "nested_set_comparisons": comparisons}
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT),
        "configurations": {k: v["configurations"] for k, v in files.items()},
        "nested_set_comparisons": comparisons,
    }, indent=2))


if __name__ == "__main__":
    main()
