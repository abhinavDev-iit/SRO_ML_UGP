# FCC versus BCC exploratory comparison

## Coverage and target

The validated database contains 40,425 FCC and 43,372 BCC configurations. BCC has a higher aggregate mean target (0.4002) than FCC (0.2640); the standardized difference is 0.525. Coverage imbalance and repeated compositions mean this must not be interpreted as an intrinsic phase-only effect.

## Leading FCC Spearman associations

- `space_group_number_ini`: 0.5520
- `range CN_VoronoiNN`: 0.3564
- `NIONS`: 0.3450
- `minimum CN_VoronoiNN`: 0.3101
- `2-norm`: 0.3066
- `5-norm`: 0.3014
- `3-norm`: 0.2989
- `configurational_entropy_kb_per_atom`: 0.2974
- `configurational_entropy_j_mol_k`: 0.2974
- `7-norm`: 0.2952

## Leading BCC Spearman associations

- `space_group_number_ini`: 0.6200
- `NIONS`: 0.3050
- `avg_dev local difference in NsUnfilled`: 0.3015
- `avg_dev local difference in NsValence`: 0.3015
- `mean neighbor distance variation`: 0.2955
- `2-norm`: 0.2886
- `configurational_entropy_j_mol_k`: 0.2820
- `configurational_entropy_kb_per_atom`: 0.2820
- `10-norm`: 0.2783
- `7-norm`: 0.2783

## Phase stability

Feature rankings differ materially between FCC and BCC (see `phase_association_comparison.csv` and the comparison figure). Phase 5 should therefore compare pooled models with phase indicators against phase-specific models, using the same grouped outer splits. Features whose association reverses sign should be treated as interaction candidates rather than universal mechanisms.
