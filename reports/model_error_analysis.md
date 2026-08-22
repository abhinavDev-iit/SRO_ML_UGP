# Model error and extrapolation analysis

Analysis uses the unified seed-42 alloy-system-held-out BALANCED predictions (12,680 rows). The 95th-percentile absolute-error threshold is 0.1682, defining 634 high-error rows.

BCC rows have MAE 0.0621 and a 6.51% high-error fraction; FCC rows have MAE 0.0438 and 3.27%. Error rises strongly at the high end of the target: MAE increases from 0.0359 in the lowest target decile to 0.0915 in the highest, where 15.54% of rows exceed the high-error threshold. Six-component alloys have MAE 0.0683, but this does not form a monotonic component-count trend.

The largest 250 errors are concentrated in several systems, especially BCC Fe–Mn–Ni (43 rows), Co–Mn–Ni (37), Co–Cr–Ni (32), and six-component Al–Co–Cr–Fe–Mn–Ni (25). This is not merely a small-sample effect: some of these held-out systems contain hundreds of observations. The Phase 5 system-level table shows the largest BCC MAE for Al–Co–Cr–Fe–Mn–Ni (0.0918), Co–Mn–Ni (0.0780) and Fe–Mn–Ni (0.0747).

For the ten compact features, no test row lies outside the literal training minimum/maximum. Between 0.16% and 1.98% of test rows lie outside individual training 1st–99th percentile intervals; neighbour-distance variation is highest. Absolute error has weak positive Spearman association with nearest-training distance (ρ=0.1184) and moderate association with target magnitude (ρ=0.2921). The dominant warning is therefore difficult/extreme response regions and held-out chemistry, not gross univariate range violation.

This screen cannot prove interpolation in the joint feature manifold. Models must be limited to the represented Al–Co–Cr–Cu–Fe–Mn–Ni chemistry, FCC/BCC structures, and the 84k theoretical configuration workflow. Tables: `highest_error_observations.csv`, `error_group_summary.csv`, and `feature_extrapolation_audit.csv` under `results/tables/phase6/`.
