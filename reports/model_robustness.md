# Model robustness

Five deterministic alloy-system-held-out allocations (seeds 7, 19, 42, 73 and 101) were evaluated with the fixed Phase 5 HistGradientBoosting specification and the 198-feature BALANCED set. No hyperparameter search was repeated. Each allocation has zero alloy-system overlap between training and test data.

| Cohort | Mean R² | SD R² | Range R² | Mean MAE | Mean RMSE |
|---|---:|---:|---:|---:|---:|
| Unified | 0.8946 | 0.0187 | 0.8671–0.9154 | 0.0569 | 0.0824 |
| FCC | 0.9046 | 0.0128 | 0.8907–0.9193 | 0.0375 | 0.0576 |
| BCC | 0.9042 | 0.0287 | 0.8620–0.9335 | 0.0615 | 0.0892 |

The seed-42 results are therefore not isolated favorable outcomes. FCC has the smallest split-to-split R² variation; BCC has the largest, indicating greater sensitivity to which alloy systems are withheld. The stable conclusion is that initial configuration-sensitive descriptors support strong within-domain prediction under complete alloy-system holdout. This does not establish universal performance outside the represented chemistry or source workflow.

Machine-readable results are in `thesis_outputs/tables/model_robustness_summary.csv` and `results/tables/phase6/model_robustness_detail.csv`; the thesis figure is `thesis_outputs/figures/model_robustness.png`.
