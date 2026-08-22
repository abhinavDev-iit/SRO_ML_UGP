# Data dictionary - current standardized 84k stage

This dictionary covers fields created or explicitly governed by the current ingestion stage. The complete 292-column raw manifest is in `reports/data_inventory_metrics.json`.

| Column/group | Definition | Units | Origin | Missing meaning | ML safety |
|---|---|---|---|---|---|
| `fid` / `source_structure_id` | immutable source-native structure identifier | none | directly reported | invalid record | grouping key, not predictor |
| `source_id` | `hea_84k_dft_2023` | none | provenance registry | invalid record | grouping only |
| `chemical_system` | alphabetized element set supplied by source | none | directly reported | unknown chemistry | categorical/compositional use |
| `formula` | integer-count formula for the initial cell | none | directly reported | invalid composition | parse, do not use raw as numeric |
| `composition_fractions_json` | normalized element-to-atomic-fraction mapping derived from `formula` | fraction | mathematically derived | parse failure is fatal | safe pre-relaxation |
| `phase` | normalized FCC/BCC label from source `lattice` | none | source metadata | `UNKNOWN` | safe pre-relaxation |
| `NIONS` / `number_of_atoms` | atoms in periodic cell | count | directly reported | invalid structure | safe but may encode ordered/SQS regime |
| `nelements` | number of constituent elements | count | directly reported | invalid composition | safe pre-relaxation |
| `space_group_number_ini` | initial unrelaxed space-group number | none | directly reported/initial structure analysis | unresolved symmetry | pre-relaxation; assess redundancy |
| initial local/Matminer descriptors | descriptors calculated from `structure_ini` | descriptor-specific | calculated from initial structure | source calculation failure | provisionally allowed; arrangement-sensitive ablation required |
| `mean abs SRO1` | mean of absolute WC alpha over unique unlike pairs in first neighbour shell | dimensionless | calculated from initial structure | not missing in current source | recommended aggregate target; never predictor |
| `mean abs SRO2`–`4` | analogous mean magnitude for shells 2–4 | dimensionless | calculated from initial structure | not missing | secondary targets |
| `mean/max/min/std/range SROn` | signed WC-alpha statistics across unlike pairs | dimensionless | calculated from initial structure | not missing | target/analysis only |
| `mean/max/min/std/range abs SROn` | magnitude statistics across unlike-pair alpha | dimensionless | calculated from initial structure | not missing | target/analysis only |
| `mean ordering parameter shell 1`–`3` | Matminer ChemicalOrdering structure features; distinct from SRO CSV labels | dimensionless | calculated from initial structure | not missing | excluded by default as direct target-family leakage |
| `Ef_per_atom`, `e_above_hull`, `e_per_atom` | final relaxed DFT energy outcomes | eV/atom | directly reported after DFT | unavailable outcome | excluded from pre-relaxation ML |
| `volume_per_atom` | final relaxed atomic volume | A^3/atom | final relaxed structure | unavailable outcome | excluded from pre-relaxation ML |
| `space_group_number` | final relaxed symmetry | none | final relaxed structure | unresolved final symmetry | excluded from pre-relaxation ML |
| `magmom`, `max_FORCE`, `pressure` | final calculation outputs/diagnostics | source-specific | DFT output | unavailable outcome | excluded from pre-relaxation ML |
