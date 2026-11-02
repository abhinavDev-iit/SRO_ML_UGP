# Phase 7 targeted DFT preparation status

Phase 7 asks whether static DFT energy differs between low- and high-SRO initial configurations at fixed composition and phase. The response remains `target_mean_abs_sro_shell1`, the aggregate mean absolute first-shell Warren–Cowley coefficient over unlike-element pairs.

## Selected exact-source configurations

| Phase | Label | fid | Composition | Atoms | SRO |
|---|---|---|---|---:|---:|
| FCC | low | `gra62121526` | Co0.5Cr0.5 | 2 | 0.000000 |
| FCC | high | `gra62121527` | Co0.5Cr0.5 | 2 | 0.333333 |
| BCC | low | `gra64001864` | Co0.5Cr0.5 | 2 | 0.000000 |
| BCC | high | `gra62121595` | Co0.5Cr0.5 | 2 | 1.000000 |

The exact initial lattices, species, fractional coordinates and atom ordering were extracted from the immutable 84k source and validated against composition and `NIONS`. Compact copies are under `dft_structures/`; the selection is `results/tables/dft/selected_configurations.csv`.

## Runtime and calculation policy

- Engine: Quantum ESPRESSO 7.6 at `/home/aditya/miniconda3/envs/qe7/bin/pw.x`, invoked through WSL with the Conda environment `qe7`; `/usr/bin/pw.x` is not used.
- Pseudopotentials: SSSP PBE Efficiency v1.3.0, Co `Co_pbe_v1.2.uspp.F.UPF` and Cr `cr_pbe_v1.5.uspp.F.UPF`; local UPFs remain Git-ignored and their hashes are recorded in `dft_inputs/qe_config.json`.
- Production cutoffs: `ecutwfc = 55 Ry`, `ecutrho = 440 Ry`.
- Sampling: fixed `12 x 12 x 12` Monkhorst-Pack grid for every two-atom cell.
- Occupations: Marzari–Vanderbilt smearing, `degauss = 0.02 Ry`.
- Spin: enabled for all four inputs, with starting magnetizations Co `+0.3` and Cr `-0.3`.
- Electronic settings: `conv_thr = 1e-8`, `electron_maxstep = 200`, `mixing_beta = 0.3`.
- Geometry: static SCF only; no relaxation, DOS, bands, phonons or additional structures.

## Cutoff decision

The representative structure was FCC low-SRO `gra62121526`.

| Cutoff | Total energy (Ry) | Energy/atom (eV) | Difference from latest 65 Ry energy (meV/atom) | Status |
|---:|---:|---:|---:|---|
| 45 Ry | -473.95516783 | -3224.244283776049 | 9.388336 | Formally converged; `JOB DONE` |
| 55 Ry | -473.95628523 | -3224.251885276797 | 1.786836 | Formally converged; `JOB DONE` |
| 65 Ry | -473.95654789 | -3224.253672112475 | 0.000000 | Near-converged; manually stopped; no `JOB DONE` |

At 65 Ry the immediately preceding completed iteration was `-473.95654736 Ry` at approximately `7e-8 Ry` estimated SCF error. The final completed iteration reported `-473.95654789 Ry` after the residual rebounded to `8.8e-7 Ry`; these two energies differ by only `0.00361 meV/atom`. The latest 65 Ry energy is `1.78684 meV/atom` below the formally converged 55 Ry energy. This few-meV/atom change does not indicate a meaningful cutoff problem for the intended preliminary fixed-composition comparison, so 55/440 Ry was selected. The machine-readable audit is `results/tables/dft/cutoff_sanity_check.csv`.

## Production-input status

Four final static inputs are prepared and validated under `dft_inputs/production/<fid>/scf.in`. Each contains exactly one Co and one Cr site, the exact source cell/coordinates, the same 55/440 Ry cutoff, k-point grid, smearing, spin initialization and electronic settings. The sequential runner is `dft_runs/run_final_scfs.sh`.

The four production SCFs have **not** been executed by Codex. Consequently, no production `dft_results.csv`, SRO–energy plot or FCC/BCC energetic conclusion is reported yet. Parsing and plotting remain deferred until the user completes the manual run and returns.
