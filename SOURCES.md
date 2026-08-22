# Dataset sources

Inventory date: 2026-08-22. Status values distinguish files that are locally present from sources that are only candidates. Unknown fields are deliberately left unresolved rather than inferred.

## `hea_84k_dft_2023`

- **Dataset:** DFT dataset for high entropy materials, version 2023-04-06
- **Paper:** *Efficient first principles based modeling via machine learning: from simple representations to high entropy materials*, DOI `10.1039/D4TA00982G`
- **Authors:** Kangming Li; Kamal Choudhary; Brian DeCost; Michael Greenwood; Jason Hattrick-Simpers
- **Year / archive:** 2024 deposit; Zenodo record 10854500
- **Repository/archive:** https://github.com/mathsphy/high-entropy-alloys-dataset-ML / https://zenodo.org/records/10854500
- **Source type / provenance:** `theoretical_DFT` / `direct_dataset`
- **Method:** DFT; exact code, functional and convergence settings require the associated paper
- **Coverage:** 84,024 structures; 40,425 FCC, 43,372 BCC, 227 without a lattice label; 253 chemical systems
- **Sizes:** ordered cells of at most 8 atoms and SQS cells of 27, 64 or 125 atoms, plus a small number of other sizes
- **SRO:** summary statistics over unique unlike-pair Warren–Cowley alpha values for initial-structure shells 1–4, available for 83,797 structures. Pair identities/values are not retained; the convention was independently reproduced in `reports/sro_definition_84k.md`.
- **Files used in this inventory:** all four CSV files and both Python scripts under `data/raw/dataset_84k_hea/`
- **Limitations:** no temperature; no HCP; SRO is aggregated across pairs; 227 records lack initial structures and SRO; energies and several metadata fields describe relaxed DFT outputs even in the initial-feature table.

## `rao_curtin_2021`

- **Dataset/paper:** Analytical models of short-range order in FCC and BCC alloys
- **Authors:** You Rao; William A. Curtin
- **Year / DOI:** 2021; dataset DOI `10.24435/materialscloud:qa-ba`
- **Archive:** https://archive.materialscloud.org/records/xc3bm-qc060
- **Source type / provenance:** `theoretical_MC` / `direct_dataset`
- **Method:** statistical-mechanics analytical models with reference Monte Carlo simulations
- **Coverage:** FCC and BCC; binary and ternary model alloys; composition and reduced interaction/temperature sweeps
- **SRO:** pair probabilities and derived SRO-related quantities for first and second neighbours; precise workbook/script conventions must be decoded before ingestion
- **Files used in this inventory:** extracted FCC/BCC trees, `sro_fcc.xlsx`, `sro_bcc.xlsx`, and `files_description.md`
- **Limitations:** 41,501-file simulation tree with extensive repeated scripts/results; element identities are often abstract species; workbook layout is presentation-oriented; no HCP.

## `mlp_csro_crconi_2024_2025`

- **Dataset/paper:** Capturing Short-Range Order in High-Entropy Alloys with Machine Learning Potentials
- **Authors:** Yifan Cao; Killian Sheriff; Rodrigo Freitas
- **Year / DOI:** 2025; `10.1038/s41524-025-01722-2`
- **Repository:** https://github.com/yifan-henry-cao/MachineLearningPotential plus the local MLP-cSRO snapshot
- **Source type / provenance:** `theoretical_MLIP` / `direct_dataset`
- **Method:** moment tensor potentials trained to DFT CrCoNi configurations
- **Coverage:** CrCoNi; FCC, HCP and liquid configurations in later training sets; no ready normalized SRO table identified
- **Files:** 10 CFG training datasets, 863 MTP files, plotting arrays/tables and scripts
- **SRO:** 255 HCP CFG additions support provisional first-shell WC reconstruction, but the six-component author HCP reference arrays are not public in the checked repositories. Ninety-eight candidates have an ambiguous 13th/12th shell-distance ratio below 1.02 and are excluded from validated ML.
- **Current compact upstream check:** the 5.68 MB `DFTMC_structures.tar.gz` contains five 108-atom cubic FCC trajectories and no HCP/WC reference arrays; no archive over 500 MB was downloaded.
- **Limitations:** many potential ensembles are model artifacts rather than independent observations; shared configurations across nested training sets create pseudo-replication risk; HCP configuration order is not a substitute for missing trajectory identifiers/reference labels.

## `csro_lattice_crconi_2025`

- **Dataset/paper:** On the nature of chemical short-range order evolution
- **Authors:** G. C. Stumpf; Y. Cao; V. P. Bacurau; D. Miracle; W. Wolf; E. D. Zanotto; R. Freitas; F. G. Coury
- **Year:** 2025
- **Repository:** local `cSRO_lattice` snapshot; upstream URL to be verified
- **Source type / provenance:** `theoretical_MLIP` / `direct_dataset`
- **Method:** Monte Carlo and molecular dynamics using a trained potential
- **Coverage:** equiatomic CrCoNi; repository documentation and file names indicate FCC-focused thermal ramps; phase must be verified from cells before assignment
- **Files:** 3,085 LAMMPS dump files, MC final structures, 7 CSVs, 16 NPY arrays, plotting scripts and supplementary material
- **SRO:** WC evolution arrays/plots are available; pair/shell convention needs extraction from plotting code
- **Limitations:** numerous correlated frames and replicas; temperatures encoded in filenames; not yet a normalized structure/SRO table.

## `crconi_colabfit_2024`

- **Dataset:** `CrCoNi_Cao_2022` / ColabFit `DS_z2mkok0egrm8_0`
- **Authors:** Yifan Cao; Killian Sheriff; Rodrigo Freitas
- **Year / DOI:** 2024; dataset DOI `10.60732/76208b62`; source paper `10.1073/pnas.2322962121`
- **Source type / provenance:** `theoretical_DFT` / `direct_dataset`
- **Method/software:** spin-polarized DFT-PBE, VASP 6.2.1
- **Coverage:** 1,257 configurations, 108,684 atoms, equiatomic CrCoNi; structures, energies, forces, stresses
- **SRO:** no explicit SRO labels; potentially usable for independent SRO calculation/validation after phase and sampling-state identification
- **License:** MIT (from `dataset.json`)
- **Limitations:** configurations are a potential-training collection, not automatically equilibrium SRO observations.

## `cms_eam_2025`

- **Dataset/paper:** Chemical short-range order and its influence on selected properties of non-dilute random alloys
- **Authors:** Subah Mubassira et al.
- **Year / DOI:** 2025; `10.1016/j.commatsci.2024.113587`
- **Source type / provenance:** `theoretical_EAM` / mostly method scripts; direct result coverage incomplete locally
- **Coverage:** CoCrNi (FCC), HfTiZr (HCP), MoNbTa and 18 additional nominally BCC ternaries; CSRO annealing at 300 K
- **Files:** EAM potential, LAMMPS inputs, a CoCrNi random structure, elemental structure scripts, random lattice-parameter and USFE summaries
- **SRO:** README describes generation and later WC calculation, but local repository does not contain a consolidated WC table or all generated CSRO structures
- **Limitations:** do not count planned simulations as present data; HfTiZr scripts alone are not usable HCP SRO observations.

## `hea_computational_toolkit_2024`

- **Resource:** High-Entropy-Alloys computational toolkit
- **Reference DOI:** `10.1016/j.commatsci.2024.113196`
- **Source type / provenance:** software resource, not a dataset
- **Coverage:** FCC/BCC/HCP-capable utilities including PM-SRO/WC-SRO scripts
- **License:** GPL-3.0
- **Use:** candidate implementation reference only; must be scientifically validated before derived SRO is admitted.
