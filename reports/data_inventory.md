# Raw-data inventory

Inventory date: 2026-08-22. Raw files were read only. Machine-readable per-file metrics, full CSV column manifests and missing counts are in `reports/data_inventory_metrics.json` and can be regenerated with `python scripts/profile_raw_inventory.py`.

## Repository summary

The repository initially contained only `data/raw/`. Seven source families contain 46,123 files and 10,124,534,739 bytes (~10.12 GB decimal). No Parquet files were present. The tree includes CSV, JSON, EXTXYZ, CFG, LAMMPS dump/data/results, POSCAR/VASP, XLSX, MAT/NPY, compressed TAR/ZIP archives, Python/MATLAB/shell code, images, PDFs and documentation.

| Source directory | Files | Bytes | Largest file | Inventory interpretation |
|---|---:|---:|---:|---|
| `dataset_84k_hea` | 6 | 1,280,699,969 | 452,858,376 B | compact primary DFT/SRO tables and scripts |
| `rao_curtin` | 41,501 | 7,919,328,221 | 243,005,440 B | extracted FCC/BCC MC simulation trees and summaries |
| `csro_lattice` | 3,192 | 711,678,701 | 44,936,170 B | CrCoNi MC/MD structures, arrays and plotting code |
| `mlp_csro` | 1,290 | 170,385,765 | 15,439,740 B | CrCoNi CFG training sets, MTP ensembles and plots |
| `crconi_colabfit` | 2 | 12,305,385 | 12,303,340 B | 1,257-configuration DFT EXTXYZ plus metadata |
| `cms_eam` | 32 | 6,655,127 | 4,058,261 B | EAM potential/workflow and small result summaries |
| `hea_computational_toolkit` | 100 | 23,481,571 | 22,524,988 B | software utilities, not primary observations |

Thousands of extensionless Rao–Curtin files are named `POSCAR`, `Results`, `Rejected`, `runjob`, etc.; extension counts alone therefore understate structure and simulation-output formats. AppleDouble `._*` and `.DS_Store` files are obvious packaging duplicates/metadata, retained in raw but excluded from future ingestion.

## 84k DFT dataset

| File | Size | Rows × columns | Key | Missing / parsing |
|---|---:|---:|---|---|
| `hea.2023-04-06.csv` | 452,858,376 B | 84,024 × 18 | unique `fid` | 227 missing `lattice` and `structure_ini_as_dict`; no malformed rows |
| `SROs_structure_ini.csv` | 42,983,861 B | 83,797 × 41 | unnamed unique first column (`fid`) | no empty fields; no malformed rows |
| `structure_featurized.dat_all.csv` | 394,478,280 B | 84,024 × 292 | unique `fid` | 227 missing initial structure/lattice/initial space group |
| `structure_ini_featurized.dat_all.csv` | 390,356,975 B | 83,797 × 292 | unique `fid` | no empty fields |

Master columns: `fid`, `reduced_formula`, `chemical_system`, `lattice`, `nelements`, `NIONS`, `space_group_number`, `volume_per_atom`, `pressure`, `stress`, `e_per_atom`, `Ef_per_atom`, `e_above_hull`, `magmom`, `charge`, `structure_ini_as_dict`, `structure_as_dict`, `kpt`.

SRO columns comprise, for each shell 1–4, `mean`, `max`, `min`, `std`, `range`, `mean abs`, `max abs`, `min abs`, `std abs`, and `range abs` SRO. These are one-row-per-structure aggregate descriptors, not the requested pair-resolved `sro_long` granularity.

Both feature files share 292 column names: 19 metadata/structure columns plus local-environment differences, bond/packing/order descriptors and 273 composition/Matminer descriptors. The complete exact ordered list and per-column missing counts are stored in the metrics JSON to avoid silently abbreviating the schema here.

Phase counts are FCC 40,425, BCC 43,372, UNKNOWN 227, HCP 0. There are 253 chemical systems in the master/relaxed table and 246 among initial/SRO rows. Dominant atom counts are 6 (36,052 master; 36,042 initial), 8 (18,275; 18,240), 27 (9,928), 4 (7,826; 7,772), 5 (6,174; 6,165), 64 (3,697; 3,696), 7 (854), 125 (598), and 3 (469; 462).

### Relationships and leakage conclusion

The master and relaxed-feature ID sets are identical (84,024). The SRO and initial-feature ID sets are identical (83,797) and are strict subsets missing the same 227 master rows. Thus the validated SRO join is exact `fid` one-to-one with `structure_ini_featurized.dat_all.csv`.

Zenodo documentation confirms that `structure_featurized` describes final relaxed structures and `structure_ini_featurized` initial unrelaxed structures. A matched-row audit shows shared final outcome metadata (`Ef_per_atom`, `e_above_hull`, `volume_per_atom`, final space group) but substantial changes in geometry-sensitive features: only 2.30% of relative-bond-length MAD values, 0.43% of packing-efficiency values and 0.57–0.86% of shell ordering descriptors are identical. Relaxed features are therefore post-outcome information for an initial-design prediction task. Even the initial-feature table must be filtered because it retains final energy/volume/space-group metadata.

## Rao–Curtin FCC/BCC

The extracted archive has 41,501 files (~7.92 GB): repeated POSCARs, accepted/rejected MC histories, results, scripts, plots, MATLAB arrays and two primary summary workbooks (plus duplicate extracted copies). `sro_fcc.xlsx` contains 4 sheets; `sro_bcc.xlsx` contains 3. Example sheets store cell size, composition `c`, reduced parameter `x`, Monte Carlo pair probability `P_mc`, theoretical values and fluctuations for first/second-neighbour cases. Rows are not normalized observations and formulas exist in secondary sheets. Paths encode phase, cell size, neighbour model, composition and interaction settings, making a path parser necessary. Obvious duplicates include AppleDouble files, copied scripts per run and plots derived from numerical results.

## MLP-cSRO CrCoNi

The repository contains 10 CFG training sets, 863 MTP files, 80 NPY arrays, 63 DAT files, 58 Python scripts, plots and PDFs. It represents equiatomic CrCoNi. The paper/repository describes nested TS-0…TS-5/TS-f datasets; TS-5 and TS-f include HCP configurations. Granularity is configuration/frame, but nesting means the same configuration may appear in several sets. No ready pair-resolved SRO table was identified. Energies/forces and phase/temperature provenance are potentially available through CFGs and code.

## cSRO_lattice CrCoNi

This source contains 3,085 LAMMPS dump files plus MC final structures, 7 CSVs (170–3,005 rows), 16 NPY arrays, JSON metadata, scripts and supplementary PDFs. File names encode replica and temperatures from 300 to 1,900 K in 100 K increments. CSVs include lattice-parameter series (`LP_aged`, `LP_quenched`) and volume-versus-temperature histories; duplicate first-column values occur in several volume tables and must be interpreted as trajectory records, not immediately removed. WC evolution is used by plotting scripts, but its pair/shell axes and links to structures remain to be decoded.

## ColabFit CrCoNi

`dataset.json` reports 1,257 DFT-PBE/VASP configurations, 108,684 sites, energies, forces and stresses for equiatomic CrCoNi, MIT licensed. The 12.3 MB EXTXYZ has per-frame `configuration_id`, `property_id`, lattice, energy, forces and stress. It supplies no SRO label or explicit temperature in the sampled header. Phase and equilibrium status must be established per cell; metadata explicitly marks the collection non-equilibrium.

## CMS-EAM

The local snapshot contains a multi-element EAM potential, LAMMPS inputs, a CoCrNi random structure, HfTiZr/MoNbTa preparation scripts, random lattice-parameter/USFE summaries and documentation. It describes 21 equiatomic ternaries (CoCrNi FCC, HfTiZr HCP, 19 BCC) and 300 K CSRO construction, but most generated CSRO structures and WC outputs are absent. Planned simulations are not counted as observations.

## HEA computational toolkit

This is a 100-file software collection, not a data source. Relevant scripts calculate PM/WC-SRO, create FCC/BCC/HCP SQS lattices, and calculate composition/entropy. It also includes unrelated ML, VASP and defect utilities and a 22.5 MB bundled ZIP. Its SRO routines are candidate references only and require independent validation.

## Immediate parsing and quality risks

- No local source yet supplies a clean common `structure × pair × shell × metric` table.
- 84k SRO convention and pair aggregation are unresolved; temperature is absent.
- Rao–Curtin uses abstract species and reduced parameters; units/physical mapping cannot be guessed.
- Atomistic collections contain strong trajectory, replica and nested-training-set dependence.
- Phase must come from cells/publication metadata, never alloy names alone.
- Calculated SRO from structures remains quality B only after random-alloy and published-value validation; until then it is excluded from final ML.
