# Final model interpretation

## Statistical and predictive evidence

Held-out permutation importance identifies `space_group_number_ini`, configurational entropy, packing efficiency, atom count, normalized entropy, neighbour-distance variation and local electronic/symmetry differences as the leading unified predictors. Initial space group and entropy lead both FCC and BCC. Group ablation gives the largest conditional losses for symmetry (ΔR² −0.0666), structural geometry (−0.0246), configurational entropy (−0.0220) and electronic/VEC/periodic descriptors (−0.0126).

Targeted removal confirms that initial space group supplies information not easily replaced by the other BALANCED features: outer ΔR² is −0.0830 unified, −0.0751 FCC and −0.0805 BCC. Conversely, neighbour-distance variation has high permutation importance but small single-feature removal loss, consistent with correlated substitutes and interactions.

## Possible physical interpretation

Composition entropy summarizes mixture complexity; valence/electronegativity differences may reflect chemical affinities; geometry/symmetry may summarize local topology and ordering constraints. These are plausible hypotheses requiring literature and controlled calculations. The focused partial-dependence curves are descriptive averages from the fitted model and are not causal response functions.

## Confounding and scope

Space group, atom count, packing and local fingerprints may encode how the 84k SQS/ordered cells were generated. Permutation importance can inflate or suppress correlated variables, and ablation measures contribution conditional on remaining groups. The strongest defensible conclusion is that composition plus initial-configuration descriptors predict the present aggregate SRO target well within the represented theoretical domain. Cross-source mechanism claims require independently generated data, consistently recomputed descriptors and source-held-out evaluation.

Evidence: Phase 5 feature-importance tables; `feature_group_ablation.csv`; `configuration_descriptor_sensitivity.csv`; `focused_partial_dependence.png`.
