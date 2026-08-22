# Minimal cross-dataset feature set

## Purpose

This is a **preliminary, non-final** set for future FCC/BCC/HCP comparison. It uses composition, elemental references, and an explicit phase indicator; it deliberately avoids initial-geometry descriptors that may be unavailable or inconsistently generated for an HCP source.

## MINIMAL_PRELIMINARY (19 features)

- `composition_number_of_elements`
- `configurational_entropy_j_mol_k`
- `atomic_size_mismatch_percent`
- `derived_atomic_number_mean`
- `derived_atomic_number_std`
- `derived_atomic_mass_mean`
- `derived_atomic_mass_std`
- `derived_atomic_radius_covalent_mean`
- `derived_atomic_radius_covalent_std`
- `pair_atomic_radius_covalent_mean_abs_diff`
- `derived_electronegativity_mean`
- `derived_electronegativity_std`
- `pair_electronegativity_mean_abs_diff`
- `derived_vec_mean`
- `derived_vec_std`
- `pair_vec_mean_abs_diff`
- `derived_melting_point_mean`
- `derived_melting_point_std`
- `phase_FCC`

All quantities are reproducible from composition plus the versioned elemental-reference table, except the phase label. `phase_FCC` is sufficient because BCC is its complement in the present two-phase database; future HCP integration must replace this binary coding with an explicitly fitted three-level phase representation. Temperature is excluded because it is not genuinely available in the 84k source.

## Phase 5 use

Compare FULL_CLEAN, BALANCED_PRELIMINARY, and MINIMAL_PRELIMINARY under identical group-aware validation. Do not select the winning set from the held-out test cohort. Structure-derived features should be evaluated separately to quantify portability versus configuration sensitivity.
