# Configuration-descriptor sensitivity

Held-out permutation importance ranks `space_group_number_ini` first in the unified, FCC and BCC models (MAE increases 0.1278, 0.1039 and 0.1635). Removing it lowers outer R² by 0.0830 unified, 0.0751 FCC and 0.0805 BCC. Removing all 11 symmetry-group predictors lowers R² by 0.0950, 0.0725 and 0.1000, respectively.

Removing the six coarse structural-geometry predictors lowers R² by 0.0341 unified, 0.0174 FCC and 0.0079 BCC. `max packing efficiency` has a larger unified effect (ΔR² −0.0186) than within FCC (−0.0018) or BCC (−0.0042), suggesting some of its unified importance separates phase/configuration regimes. Removing `range neighbor distance variation` changes R² by only −0.0006 unified, −0.0031 FCC and −0.0041 BCC, despite its permutation rank; correlation and interactions make single-feature measures non-additive.

These results show that configuration-sensitive information is predictive even within phase. They do **not** distinguish transferable structural physics from signatures of cell size, SQS/order generation, or dataset preprocessing. No causal mechanism is claimed. A decisive test requires new sources with independently generated structures and consistently recomputed descriptors.

Exact results and the figure are in `results/tables/phase6/configuration_descriptor_sensitivity.csv` and `thesis_outputs/figures/configuration_descriptor_sensitivity.png`.
