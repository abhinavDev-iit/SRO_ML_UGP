# Phase 5 split strategy

The primary outer test holds out entire **alloy systems**. Model and feature-set selection uses three-fold shuffled `GroupKFold` on the remaining alloy systems. Only after selection is the frozen pipeline evaluated on the outer test. The same outer alloy systems are used for unified and phase-specific comparisons.

- **random_configuration**: 67,037 train / 16,760 test; group column `none`; overlap not_applicable; test FCC/BCC 8,085/8,675.
- **composition_grouped**: 68,318 train / 15,479 test; group column `composition_fractions_json`; overlap 0; test FCC/BCC 7,504/7,975.
- **alloy_system_grouped**: 71,117 train / 12,680 test; group column `chemical_system`; overlap 0; test FCC/BCC 5,905/6,775.

Random/configuration splitting is retained only as the easiest baseline. Composition grouping tests transfer to unseen stoichiometries; alloy-system grouping is strongest because no elemental combination is shared across train/test. Configuration IDs are unique and cannot provide a stronger grouping than composition/system. All split seeds are fixed at 42.
