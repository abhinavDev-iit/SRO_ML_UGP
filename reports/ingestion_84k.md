# 84k standardized-ingestion stage

The ingestion adapter is implemented in `src/ingestion/hea84k.py` and exposed through `run_pipeline.py`. It performs no feature selection or model training.

## Validated input

- 83,797 unique initial-structure feature rows.
- 83,797 unique SRO rows with an identical `fid` set.
- FCC: 40,425; BCC: 43,372; no missing SRO targets.

## Default feature policy

The `initial_structure_only` policy selects 278 metadata/descriptors from `structure_ini_featurized.dat_all.csv`. It explicitly removes:

- final DFT outcomes: `Ef_per_atom`, `e_above_hull`, `e_per_atom`, `magmom`, `max_FORCE`, `pressure`;
- final relaxed geometry/symmetry: `volume_per_atom`, `space_group_number`, `structure`;
- raw structure/object columns unsuitable for tabular ML;
- Matminer `mean ordering parameter shell 1/2/3`, which are direct SRO-family proxies and scientifically confound target prediction.

`space_group_number_ini` remains available because it belongs to the initial state. The adapter derives normalized phase labels and JSON atomic fractions from the formula. It refuses to overwrite an existing processed output and fails if the two ID sets stop matching one-to-one.

The 278-column view is a broad initial feature library, not a claim that every column is safe for every scientific question. A stricter composition/elemental-only view should be the first baseline because local arrangement descriptors can encode the same occupations used to derive SRO.

## Usage

Validation only:

```text
python run_pipeline.py ingest-84k --dry-run
```

Create ignored local CSV outputs:

```text
python run_pipeline.py ingest-84k
```

The generated files live under `data/processed/hea_84k/`, which is excluded from Git. Parquet conversion is deferred until this standardized view has been reviewed and `pyarrow` is installed.

## Tests

Seven tests validate composition parsing, phase normalization, pair canonicalization, exact row/phase counts, one-to-one ID matching and the leakage exclusion policy. On 2026-08-22 all tests passed.
