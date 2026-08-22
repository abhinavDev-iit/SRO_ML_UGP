# HCP data status

Inventory date: 2026-08-22.

## Phase 6 final status

Validated HCP observations remain **0**. The **255 provisional CrCoNi HCP configurations** were not integrated and no HCP model was trained. They are equiatomic 144-atom frames from five reported 500 K MC trajectories, but the author-local six-component HCP Warren–Cowley `LOP_*.npy` reference arrays and the exact ideal-HCP neighbour/topology mapping remain unavailable. Distance-ranked reconstruction is not accepted because 98/255 frames have a 13th/12th-neighbour distance ratio below 1.02, making the first-shell boundary ambiguous under displacement.

The best immediate candidate is still the compact author HCP DFT-MC WC reference array/topology bundle, which would validate the already-local structures. The best chemically independent next dataset is a completed HfTiZr HCP bundle with configurations, pair-resolved WC outputs, genuine temperature/run metadata and trajectory grouping. The present study therefore makes conclusions for validated FCC and BCC data only.

## Phase 5 update

No HCP model was trained. All Phase 5 split, model, prediction, residual, importance, and alloy-error tables assert a validated HCP count of **0** and contain only the **40,425 FCC** and **43,372 BCC** observations. The 255 MLP-cSRO HCP configurations remain provisional and excluded because the author WC reference arrays/topology validation are unavailable. This prevents any claim of FCC/BCC/HCP model parity and remains the principal data limitation before HCP inference.

## Phase 4 update

The exploratory/correlation database remains FCC/BCC-only: **40,425 FCC**, **43,372 BCC**, and **0 validated HCP** observations. All **255 provisional MLP-cSRO HCP CrCoNi configurations** were excluded by an explicit pipeline assertion and output test. No new HCP archive was downloaded during Phase 4, and no file above 500 MB was requested. The missing author HCP `LOP_*.npy` Warren–Cowley reference arrays still prevent validation of the reconstructed values.

The next compact priority is unchanged: obtain the MLP-cSRO HCP reference arrays/topology mapping to validate the already-local 255 configurations. If unavailable, add a completed HfTiZr HCP bundle containing configurations, pair-resolved WC output, and genuine run-temperature metadata. Phase 4's `MINIMAL_PRELIMINARY` composition/elemental feature set is designed for this future cross-source comparison, but its binary phase representation must be expanded after HCP validation.

## Phase 3 update

The validated HCP count remains **0**. The 255 TS-5-minus-TS-4 HCP CFG additions were parsed as 144-atom equiatomic CrCoNi configurations at the study's documented 500 K. First-shell WC values were provisionally reconstructed using 12 periodic nearest neighbours, but 98/255 configurations have a minimum 13th/12th-neighbour distance ratio below 1.02 (minimum `1.0000008`). This makes distance-ranked topology ambiguous for a substantial subset. Because the author-reference `LOP_*.npy` HCP arrays and exact topology mapping are still absent, these values are stored only in ignored `data/processed/hcp_candidates_provisional.parquet` and are excluded from the validated ML database.

The current upstream `MachineLearningPotential` repository was rechecked on 2026-08-22. It now lists compact simulation archives. Only the 5.68 MB `DFTMC_structures.tar.gz` was downloaded and inspected. It contains five `structures_1`–`structures_5` trajectories with 108-atom cubic FCC cells (`Cr36Co36Ni36`) and MC logs; it provides neither HCP configurations nor WC reference arrays. Thus it does not close the HCP gap. Repository: https://github.com/yifan-henry-cao/MachineLearningPotential

No larger archive was downloaded. The next credible compact source remains a completed HfTiZr HCP random/CSRO bundle from the CMS-EAM workflow (configurations plus WC output and 300 K run metadata). A paper figure or a workflow script alone will not be counted as observations.

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
