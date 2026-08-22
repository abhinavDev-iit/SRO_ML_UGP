# Initial space-group sensitivity

Phase 4 correlations for `space_group_number_ini` were 0.4753/0.5931 (Pearson/Spearman) combined, 0.4812/0.5520 within FCC, and 0.4877/0.6200 within BCC. The association therefore persists within each phase and is not merely a binary FCC/BCC discriminator.

Using each cohort's selected algorithm with FULL_CLEAN descriptors, removing initial space group changed alloy-held-out R² by:

- ALL: with 0.8973, without 0.8179, delta 0.0794.
- BCC: with 0.9128, without 0.8351, delta 0.0777.
- FCC: with 0.9067, without 0.8256, delta 0.0811.

This remains predictive sensitivity, not evidence that space-group number physically controls SRO. It can encode initial cell construction, symmetry breaking, or configuration-generation regimes and requires structure-feature ablation and external support.
