# Proposed normalized database schema

Status: proposal after raw-data inventory; no processed database has yet been created.

## Identity and provenance tables

### `sources`

Primary key `source_id`. Stores the source registry fields from `sources.yaml`, including source type, provenance, method, citation, license, and immutable raw-file references.

### `alloys`

Primary key `alloy_id`. One row per standardized alloy system/composition family, with `alloy_system`, `composition_original`, canonical composition JSON, `number_of_elements`, and `composition_id`. Exact atomic fractions belong in a child `composition_fractions(composition_id, element, atomic_fraction)` table to avoid an ever-widening schema.

## Physical-state tables

### `structures`

One row per physical/configurational state. Primary key `structure_id`; foreign keys `source_id`, `alloy_id`, `composition_id`. Core fields: source-native ID, phase, phase origin, temperature K, pressure GPa, method, trajectory/replica/step IDs, atom count, lattice parameters, volume, density, relaxed-state flag, energies, magnetism/charge summaries, and quality status. `structure_id` must identify a state, not merely an alloy.

### `structure_files`

Maps `structure_id` to immutable raw paths, hashes, formats, frame offsets, and whether a file contains initial, relaxed, MC, MD, accepted or rejected states. This prevents multi-frame and duplicate-file ambiguity.

### `sro_long`

One row per `structure_id × directed_pair × shell × metric × convention`. Primary key may be a deterministic hash. Fields: `pair_center`, `pair_neighbor`, canonical unordered pair for grouping, shell index/vector, coordination number, distance, `sro_metric`, `sro_value`, uncertainty, sign convention, origin, validation status, quality status. Directed WC terms must not be collapsed until symmetry/equivalence is established.

### `features_long` and `features_wide`

`features_long` records `structure_id`, feature name/value/unit/origin/calculation version/leakage class. A later `features_wide` Parquet table is a reproducible pivot for analysis. Features calculated from relaxed geometry or target-derived quantities receive explicit leakage flags.

## Derived ML view

`ml_dataset` is not a master table. It is a versioned view joining one SRO observation to state-safe predictors. It includes grouping keys (`source_id`, `alloy_id`, `composition_id`, `structure_id`, `trajectory_id`) and a declared prediction scenario. Separate views are required for initial-only versus post-relaxation scientific questions.

## Current source mapping and join keys

| Source | Native structure key | Secondary grouping keys | SRO join |
|---|---|---|---|
| 84k DFT | `fid` | `chemical_system`, formula, lattice, NIONS | exact one-to-one `fid` join between initial features and SRO (83,797 rows) |
| Rao–Curtin | path-derived simulation/run identity | phase, composition `c`, interaction parameter `x`, neighbour model, cell size | workbook/script/path decoding required; no safe global key yet |
| MLP-cSRO | CFG configuration order plus training-set identity | TS version, phase, MC run/step | nested training sets require content hashes and parent-set lineage |
| cSRO_lattice | filename/path plus frame | temperature, ramp/replica, MC/MD stage | WC arrays must be linked through plotting-code indexing |
| ColabFit CrCoNi | `configuration_id` | source name/index, atom count | no supplied SRO; calculated labels only after validation |
| CMS-EAM | generated data-file path | alloy, random/CSRO, anneal condition | consolidated WC output absent locally |

## Integrity constraints

- atomic fractions sum to 1 within a documented tolerance;
- `phase` belongs to FCC/BCC/HCP/OTHER/UNKNOWN and `phase_origin` is mandatory;
- temperature and units are never inferred silently;
- pair direction and WC convention are retained;
- raw paths and hashes are immutable;
- D-quality values remain stored but are excluded from primary ML by default;
- repeated frames, shells and pairs share their physical grouping IDs for leakage-safe splitting.
