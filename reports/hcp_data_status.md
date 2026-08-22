# HCP data status

Inventory date: 2026-08-22.

## Current balance

| Source | HCP status | Usable HCP structures now | Temperature | SRO status | Main gap |
|---|---|---:|---|---|---|
| 84k DFT | absent | 0 | none | aggregated SRO only for FCC/BCC | no HCP configurations |
| Rao–Curtin | absent | 0 | reduced parameter sweeps | FCC/BCC only | method has no HCP branch |
| MLP-cSRO CrCoNi | present in TS-5/TS-f training CFGs | 255 exact HCP CFG blocks identified as the TS-5 additions | 500 K MC sampling plus thermal perturbations described in paper | HCP WC was calculated in the study, but raw six-component HCP trajectories/reference arrays are absent locally | obtain reference arrays, then calculate and validate WC from CFG occupations |
| cSRO_lattice | not established | 0 confirmed | 300–1900 K filenames | WC arrays exist, likely FCC-focused | verify cells before phase assignment |
| ColabFit CrCoNi | possible mixed configuration set | 0 confirmed | not explicit | no supplied SRO | classify cells and sampling provenance |
| CMS-EAM | HfTiZr HCP workflow documented | 0 usable HCP SRO rows | 300 K anneal documented | generated structures/WC table absent locally | obtain actual HfTiZr random/CSRO structures and WC output |

Confirmed usable HCP SRO observations: **0**. Candidate HCP configurations: **255 CrCoNi CFG blocks**. A byte-level nesting audit found 254 configurations in local TS-4 and all 254 reproduced inside TS-5, with 255 exact additional blocks. The source paper defines those TS-5 additions as HCP configurations. TS-f contains all 509 TS-5 blocks plus 1,021 additional local blocks. Full counts and exact block hashes are in `reports/mlp_csro_cfg_inventory.json`.

The paper describes the HCP additions as 144-atom equiatomic CrCoNi cells extracted every 100 atom-swap attempts from five independent 500 K MC simulations, up to 5,000 attempts. They are therefore correlated snapshots from one composition and five trajectories, not 255 independent alloy systems.

The repository proves that HCP WC-SRO reference calculations existed: its analysis allocates arrays with six CrCoNi pair components and reads five DFT HCP MC trajectories before averaging the final 100 steps. However, those scripts reference author-local absolute paths such as `.../37_DFT_MC_HCP_500K_144_atoms/.../LOP_*.npy`. The repository only preserves derived HCP error summaries (`Beta_HCP.npy`), not the raw HCP WC trajectories or pair-resolved DFT mean. Consequently the local material does **not** contain validated HCP WC labels.

WC values can be calculated from the 255 CFG chemical occupations because the cells are periodic HCP configurations and element mapping is documented (`0=Cr`, `1=Co`, `2=Ni`). Thermal displacements make naive distance cutoffs fragile; the reliable method is to map atoms to the known ideal HCP lattice/topology or use a shell algorithm validated against the missing/published six-component reference. Until that comparison succeeds, calculated HCP values are provisional and excluded from primary ML.

The verified 84k phase counts are FCC 40,425, BCC 43,372, HCP 0, UNKNOWN 227. Thus the present compact labelled database is completely imbalanced against HCP. No duplication or synthetic row oversampling is justified.

## Immediate HCP priorities

1. Extract the 255 TS-5-minus-TS-4 HCP configurations while preserving their source order; recover five trajectory and MC-step IDs from author metadata or supplementary material rather than guessing from CFG order.
2. Request/download the six-component HCP `LOP_*.npy` DFT reference arrays or an equivalent compact table, plus the shell/topology calculation code used by the authors.
3. Request/download the completed CMS-EAM HfTiZr `data.HfTiZr_random`, `data.HfTiZr_CSRO`, `cn.out`/WC output and run metadata, rather than rerunning a large workflow blindly.
4. Seek compact tabular or final-snapshot HCP Ti–Zr–Hf family datasets with pair-resolved WC values and temperatures. Thermodynamic-only HCP databases are useful for enrichment but are not SRO labels.

## Limitations to retain in thesis interpretation

HCP counts must be reported both as rows and independent alloy systems. The 255 candidate frames represent one equiatomic CrCoNi composition and five correlated MC histories. Phase-specific HCP ML should remain withheld until WC validation passes and a chemically independent HCP source (preferably Hf–Ti–Zr) is added.

## Recommended next HCP dataset

First obtain the **compact MLP-cSRO HCP DFT-MC WC reference arrays** because they make the 255 already-local CrCoNi configurations scientifically usable without a large download. For chemical diversity, the next new source should be a completed **HfTiZr HCP** bundle containing final random/ordered configurations, temperature/run metadata and pair-resolved WC values—preferably the missing outputs associated with the locally present CMS-EAM workflow. Do not substitute the large Ti/Zr/Hf thermodynamics archive, which has no chemical SRO labels.
