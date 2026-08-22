# Project plan after initial inventory

## Gate decision

Do not start model training. The compact 84k tables can be joined safely, but the SRO definition is aggregated rather than pair-resolved, Rao–Curtin semantics still need decoding, and no validated HCP SRO observation exists.

## Validated findings from this inventory

- Raw data comprise seven source families, 46,123 files and about 10.12 GB.
- The 84k master and relaxed-feature tables each contain 84,024 unique `fid` values. The initial-feature and SRO tables contain the identical subset of 83,797 unique IDs; the other 227 records lack an initial structure and lattice label.
- The 84k source covers 253 chemical systems and only FCC/BCC. It provides shell-level summary statistics, not pair-resolved WC observations.
- `structure_featurized.dat_all.csv` is featurized from final relaxed structures; `structure_ini_featurized.dat_all.csv` is featurized from initial unrelaxed structures. Their metadata/energies are largely shared, but geometry-sensitive descriptors differ for nearly all matched rows.
- Relaxed geometry, final space group, relaxed volume, force/energy outputs, and ordering descriptors can leak post-relaxation information into an initial-design prediction task. The default pre-relaxation feature view must use initial/compositional features and explicitly exclude final DFT outcomes.
- Rao–Curtin contains valuable FCC/BCC Monte Carlo data but requires path/workbook normalization. cSRO_lattice and MLP-cSRO contain extensive correlated atomistic data. ColabFit contains 1,257 CrCoNi DFT configurations without direct SRO labels. CMS-EAM is presently more workflow than completed database.

## Sequential implementation

1. Freeze raw-file hashes and create source-specific manifests; ignore AppleDouble/DS_Store artifacts without deleting them.
2. Implement 84k ingestion keyed by `fid`; create separate initial-only and relaxed/post-DFT feature namespaces. Preserve 227 unlabeled structures.
3. Decode Rao–Curtin workbooks and representative scripts to establish whether stored `P_mc`, `x`, `c` and neighbour labels map to WC alpha, pair probability, temperature or reduced interaction. Validate equations on several runs before bulk parsing.
4. Index CFG, EXTXYZ and LAMMPS dump collections without loading all frames simultaneously. Generate content hashes and trajectory/replica IDs to expose nested/repeated configurations.
5. Implement the normalized schema in `reports/normalized_database_schema.md` and source-specific adapters.
6. Implement composition, phase, pair and unit standardizers with tests.
7. Implement/validate WC-SRO calculation for FCC/BCC/HCP using a random-alloy test and at least one published paired structure/value test.
8. Create processed Parquet tables only after source semantics pass the gates above.
9. Then proceed to quality control, EDA, correlations, feature selection and grouped ML in the sequence specified by the project brief.

## Leakage and pseudo-replication controls

- Prediction scenarios must be declared: pre-relaxation design, post-relaxation characterization, or trajectory-state prediction.
- All pair/shell rows from one structure stay in one fold.
- MC/MD frames from the same trajectory stay in one fold; nested MLP training sets cannot cross folds.
- Composition-, alloy-system- and source-held-out tests remain distinct.
- Final relaxed energies/features are not permissible predictors in a pre-relaxation SRO model merely because they occur in the initial-feature CSV.

## Exact next downloads/requests

No new copy of the 84k or Rao–Curtin archives is needed; the required files are already local. Obtain next, in order:

1. **84k associated paper, supplementary information and repository README/BibTeX** (small documents): needed for DFT settings, exact SRO formula, shell construction, units, licenses and citation. Do not download trajectories.
2. **MLP-cSRO paper supplementary information and the smallest published HCP WC numerical arrays/configuration index**: needed to map TS-5/TS-f HCP frames to MC runs and validate calculated WC values. Existing training CFGs/potentials need not be downloaded again.
3. **CMS-EAM completed HfTiZr result bundle**, specifically `data.HfTiZr_random`, `data.HfTiZr_CSRO`, WC/`cn.out` output, temperature/run metadata and any compact summary table. Request these from authors/upstream if absent; do not rerun or download full trajectories first.
4. **cSRO_lattice machine-readable metadata/index** mapping dump filenames to phase, ramp, replica, temperature, timestep and WC arrays. Prefer a small CSV/JSON or author-provided index over another repository clone.
5. **A compact, independent HCP alloy SRO dataset** with final snapshots and pair-resolved WC values for Hf–Ti–Zr or another HCP solid solution. Before accepting it, require phase, composition, temperature, shell convention, potential/DFT method and trajectory grouping metadata.

The 1.2 GB Ti/Zr/Hf thermodynamics archive identified during search is not an SRO dataset and exceeds the automatic-download threshold; it should not be downloaded at this stage.

## Unresolved questions

- Exact WC convention and pair aggregation behind the 84k `mean/max/min SRO` columns.
- Whether the 84k SRO values are directed-pair averages and how absent species/pairs are handled.
- Rao–Curtin mapping from reduced parameter `x` to physical temperature and interaction energy.
- Exact HCP structure counts after MLP-cSRO training-set deduplication.
- Licenses/upstream commit hashes for several local repository snapshots.
