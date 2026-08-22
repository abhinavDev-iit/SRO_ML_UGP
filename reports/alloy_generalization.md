# Alloy-system generalization

The primary test contains entire alloy systems unseen during training. System-wise counts, MAE and RMSE are in `alloy_system_error.csv`. The ten largest unified-system MAEs are:

- `Co-Mn`: n=342, MAE=0.0739, RMSE=0.0966.
- `Co-Mn-Ni`: n=1428, MAE=0.0709, RMSE=0.0957.
- `Fe-Mn-Ni`: n=1427, MAE=0.0696, RMSE=0.0943.
- `Al-Co-Cr-Fe-Mn-Ni`: n=567, MAE=0.0695, RMSE=0.0965.
- `Al-Cu-Mn`: n=382, MAE=0.0637, RMSE=0.0852.
- `Co-Cr-Ni`: n=1431, MAE=0.0622, RMSE=0.0862.
- `Al-Cu-Fe`: n=355, MAE=0.0606, RMSE=0.0826.
- `Al-Mn`: n=79, MAE=0.0606, RMSE=0.0831.
- `Fe-Si`: n=80, MAE=0.0603, RMSE=0.0841.
- `Cu-Fe-Mn`: n=298, MAE=0.0601, RMSE=0.0779.

The ten lowest MAEs among systems with at least 20 test rows are:

- `Cr-Fe-Si`: n=181, MAE=0.0249, RMSE=0.0354.
- `Cr-Ni-Si`: n=180, MAE=0.0277, RMSE=0.0398.
- `Co-Fe-Si`: n=182, MAE=0.0280, RMSE=0.0413.
- `Co-Cr-Ni-Si`: n=171, MAE=0.0295, RMSE=0.0392.
- `Cr-Mn-Ni-Si`: n=172, MAE=0.0300, RMSE=0.0407.
- `Al-Cr-Fe-Ni-Si`: n=279, MAE=0.0300, RMSE=0.0399.
- `Al-Fe-Mn`: n=181, MAE=0.0304, RMSE=0.0440.
- `Al-Co-Ni`: n=182, MAE=0.0304, RMSE=0.0443.
- `Al-Co-Cr-Fe-Si`: n=280, MAE=0.0309, RMSE=0.0401.
- `Al-Co-Cr-Ni-Si`: n=278, MAE=0.0310, RMSE=0.0403.

The Spearman association between held-out system size and MAE is 0.774. Every test system is absent from training, so bias toward a specific heavily represented training system is structurally prevented; representation effects can still enter through chemically related training systems. Small systems have noisier error estimates and poor performance must not automatically be attributed to chemistry.
