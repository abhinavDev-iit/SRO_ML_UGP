# Feature-group interpretation

One physical group at a time was removed from the 198-feature BALANCED model and evaluated by three-fold alloy-system-grouped CV within the outer training partition. The baseline was R² 0.8803 and MAE 0.0640.

| Removed group | Features removed | ΔR² | ΔMAE |
|---|---:|---:|---:|
| Symmetry | 11 | −0.0666 | +0.0172 |
| Structural geometry | 6 | −0.0246 | +0.0086 |
| Configurational entropy | 2 | −0.0220 | +0.0074 |
| Electronic/VEC/periodic | 80 | −0.0126 | +0.0032 |
| Elemental thermophysical | 25 | −0.0043 | +0.0007 |
| Electronegativity | 12 | −0.0034 | +0.0007 |
| Composition | 46 | −0.0022 | +0.0008 |
| Atomic size | 16 | −0.0011 | +0.0003 |

Symmetry has the largest conditional contribution, followed by structural geometry and configurational entropy. The small conditional loss for composition does not mean composition is physically irrelevant: it is redundant with entropy, elemental statistics, local-difference and phase/configuration descriptors. Group ablations are also non-additive because HistGradientBoosting can substitute correlated features.

The results quantify predictive information conditional on the remaining 198-feature representation. They do not establish causality. The exact table is `thesis_outputs/tables/feature_group_ablation.csv`; the figure is `thesis_outputs/figures/feature_group_ablation.png`.

Phase-resolved ablations preserve symmetry as the largest group: ΔR² is −0.0901 FCC and −0.0574 BCC. FCC next depends on configurational entropy (−0.0213), electronic/VEC/periodic features (−0.0184) and structural geometry (−0.0104). BCC next depends on electronic/VEC/periodic features (−0.0153), configurational entropy (−0.0151), composition (−0.0094) and structural geometry (−0.0042). Small positive deltas for a few removals are within model/CV variability and indicate redundancy rather than a beneficial physical absence.
