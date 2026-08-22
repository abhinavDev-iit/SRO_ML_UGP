# Study limitations

- **Aggregate target:** `target_mean_abs_sro_shell1` averages absolute Warren–Cowley values across unique unlike pairs. It discards pair identity, sign and competing pair-specific ordering/segregation tendencies.
- **Theoretical-source dominance:** all 83,797 validated labels come from one 84k computational workflow. Source-held-out generalization cannot be measured.
- **No validated HCP:** the 255 CrCoNi HCP configurations lack author WC references/topology validation and remain excluded; conclusions apply only to FCC and BCC.
- **Dataset-specific descriptors:** initial space group and local structural fingerprints dominate prediction but may not be reproducible across experimental/tabular sources.
- **Configuration signatures:** cell size, symmetry, SQS/order generation and local topology may encode configuration identity as well as transferable physics.
- **Chemical domain:** represented elements are Al, Co, Cr, Cu, Fe, Mn and Ni. Performance should not be extrapolated to arbitrary metallic alloys.
- **Dependence:** rows share alloy systems, compositions and generation procedures. Alloy-system holdout is used, but it cannot remove all workflow-level dependence.
- **Temperature:** the 84k labels do not provide a genuine observation temperature; temperature-dependent SRO cannot be learned from this source.
- **Correlation versus causation:** correlations, partial dependence and ablations quantify statistical association or predictive information, not mechanisms.
- **Importance limitations:** permutation importance is affected by correlated substitutes; group ablations are non-additive; partial dependence averages across possibly unrealistic feature combinations.
- **Model selection:** BALANCED was informed by whole-dataset Phase 4 EDA, making Phase 5 exploratory rather than a pristine confirmatory study. Phase 6 compact ranking corrects this for size selection by using training partitions only, but it still starts from BALANCED.
- **Generalization:** five alloy-system allocations support robustness within the represented domain; BCC variability across seeds shows sensitivity to which systems are withheld.

The study supports accurate configuration-sensitive prediction of an aggregate FCC/BCC SRO magnitude within a controlled theoretical domain. It does not establish universal alloy physics or experimental transferability.
