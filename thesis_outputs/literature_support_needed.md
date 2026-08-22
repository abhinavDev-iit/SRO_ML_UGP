# Literature support map

No reference below has been assumed or fabricated. Each item is a targeted verification task for thesis citation work.

## Warren–Cowley as an SRO descriptor

- **Observed result:** the primary label is mean absolute first-shell Warren–Cowley SRO across unlike pairs.
- **Project evidence:** `reports/sro_definition_84k.md`; exact reconstruction tests.
- **Figure/table:** dataset/target tables and Phase 4 target distributions.
- **Claim needing verification:** standard interpretation, sign convention, shell dependence, and limitations of magnitude aggregation.
- **Search keywords:** Warren Cowley SRO definition multicomponent alloy pair probability shell.

## Configurational entropy and ordering

- **Observed result:** removing two entropy features lowers grouped-CV R² by 0.0220; entropy is second in held-out permutation importance.
- **Project evidence:** `feature_group_ablation.csv`; Phase 5 importance tables.
- **Figure/table:** feature-group ablation; focused partial dependence.
- **Claim needing verification:** how ideal mixing entropy relates to composition complexity versus chemical ordering tendency.
- **Search keywords:** configurational entropy chemical short range order multicomponent high entropy alloy.

## Atomic-size mismatch and chemical ordering

- **Observed result:** atomic-size features have small conditional group-ablation loss once correlated descriptors remain.
- **Project evidence:** group-ablation table; Phase 4 associations.
- **Figure/table:** correlation ranking; feature-group ablation.
- **Claim needing verification:** elastic/size-mismatch contributions to ordering in FCC/BCC transition-metal alloys.
- **Search keywords:** atomic size mismatch short range order FCC BCC alloy strain ordering.

## Electronegativity, valence and electronic differences

- **Observed result:** local electronegativity, NsValence and NsUnfilled differences rank highly; the broad electronic/VEC/periodic group gives ΔR² −0.0126.
- **Project evidence:** unified/FCC/BCC importance tables; ablation.
- **Figure/table:** feature importance and group ablation.
- **Claim needing verification:** electronic/chemical affinity links to pair ordering, without treating ML association as mechanism.
- **Search keywords:** valence electron concentration electronegativity difference SRO transition metal alloy.

## Structural topology and configuration sensitivity

- **Observed result:** removing symmetry lowers grouped-CV R² by 0.0666; removing initial structure as a broad set collapses Phase 5 performance relative to BALANCED.
- **Project evidence:** configuration sensitivity and Phase 5 feature-set comparison.
- **Figure/table:** configuration-descriptor sensitivity; feature-set comparison.
- **Claim needing verification:** local topology descriptors used for chemical-order prediction and risks of configuration-generation signatures.
- **Search keywords:** local structure descriptor chemical ordering SQS machine learning data leakage configuration.

## FCC versus BCC SRO

- **Observed result:** BCC mean magnitude 0.4002 versus FCC 0.2640 (d=0.5253), with confounded source distributions.
- **Project evidence:** Phase 4 phase comparison.
- **Figure/table:** target distribution; FCC/BCC final comparison.
- **Claim needing verification:** alloy-specific FCC/BCC coordination/topology effects; whether comparable studies find systematic differences after controlling chemistry.
- **Search keywords:** FCC BCC Warren Cowley short range order comparison transition metal alloys.

## ML prediction and grouped validation

- **Observed result:** random R² 0.9266, composition-held-out 0.9161 and alloy-system-held-out 0.8997; repeated alloy splits mean 0.8946±0.0187.
- **Project evidence:** Phase 5 grouped evaluation and Phase 6 robustness.
- **Figure/table:** split comparison; robustness summary.
- **Claim needing verification:** appropriate group/source splitting for materials informatics and risks of composition leakage.
- **Search keywords:** materials informatics grouped cross validation composition split alloy machine learning leakage.

## HCP SRO validation

- **Observed result:** 255 configurations but zero validated HCP WC labels.
- **Project evidence:** `reports/hcp_data_status.md` and topology-gap audit.
- **Figure/table:** phase-count figure/table.
- **Claim needing verification:** robust HCP shell/topology algorithms under thermal displacement and reference HCP CrCoNi/HfTiZr WC data.
- **Search keywords:** HCP Warren Cowley CrCoNi Monte Carlo HfTiZr short range order topology.
