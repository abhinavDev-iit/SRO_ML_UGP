# Phase 7 targeted DFT preparation status

Phase 7 asks whether static DFT energy differs between low- and high-SRO initial configurations at fixed composition and phase. The source response remains `target_mean_abs_sro_shell1`, the aggregate mean absolute first-shell Warren–Cowley coefficient over unlike-element pairs.

## Selected exact-source configurations

| Phase | Label | fid | Composition | Atoms | SRO |
|---|---|---|---|---:|---:|
| FCC | low | `gra62121526` | Co0.5Cr0.5 | 2 | 0.000000 |
| FCC | high | `gra62121527` | Co0.5Cr0.5 | 2 | 0.333333 |
| BCC | low | `gra64001864` | Co0.5Cr0.5 | 2 | 0.000000 |
| BCC | high | `gra62121595` | Co0.5Cr0.5 | 2 | 1.000000 |

The search covered all 83,797 validated rows and ranked fixed phase/composition/atom-count groups by atom count, SRO range, group size, and deterministic chemical-system order. These four rows are the two-atom top-ranked groups. Their exact initial lattices, species, fractional coordinates, and atom ordering were extracted from `data/raw/dataset_84k_hea/hea.2023-04-06.csv`, column `structure_ini_as_dict`, and validated against the processed composition and `NIONS` fields. The compact copies are under `dft_structures/`; the selection is `results/tables/dft/selected_configurations.csv`.

## Prepared calculation policy

The tracked inputs under `dft_inputs/templates/` are static Quantum ESPRESSO `pw.x` SCF templates only: no ionic/cell relaxation, DOS, bands, phonons, or dynamics. They specify PBE, metallic Marzari–Vanderbilt smearing (`degauss = 0.02 Ry`), an automatic reciprocal-spacing policy of 0.25 Å⁻¹, `conv_thr = 1e-8`, and spin polarization. Co starts at `+0.3` and Cr at `-0.3`; the same deterministic initialization is used for every configuration. This initialization is a reproducible starting condition, not a claim that the magnetic ground state is established.

## Execution status

No DFT calculation, cutoff sanity check, energy result, or DFT figure has been produced. `pw.x` is not installed or available on `PATH`, and no local Quantum ESPRESSO UPF files were found. Plane-wave and charge-density cutoffs remain explicit template placeholders because they must follow the chosen pseudopotential recommendations.

Required setup before execution:

- an accessible Quantum ESPRESSO `pw.x` executable;
- one consistent PBE-compatible Quantum ESPRESSO pseudopotential family containing Co and Cr UPF files;
- the family/source, filenames, SHA-256 checksums, and recommended `ecutwfc`/`ecutrho` values entered in `dft_inputs/qe_config.json`.

Until that setup is supplied, `dft_results.csv`, energy figures, and an SRO–energy conclusion must not be created.
