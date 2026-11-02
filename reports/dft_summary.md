# Phase 7 targeted static-DFT comparison

Four exact-source initial structures were compared using static Quantum ESPRESSO SCF calculations. Energies are normalized per atom and referenced only within each fixed-composition phase pair.

## Calculation policy

- Engine: Quantum ESPRESSO 7.6 `pw.x` from the WSL Conda environment `qe7` (`/home/aditya/miniconda3/envs/qe7/bin/pw.x`), not `/usr/bin/pw.x`.
- Pseudopotentials: SSSP PBE Efficiency v1.3.0 (PBE); Co `Co_pbe_v1.2.uspp.F.UPF` and Cr `cr_pbe_v1.5.uspp.F.UPF`.
- Cutoffs: `ecutwfc = 55 Ry`, `ecutrho = 440 Ry`.
- Brillouin-zone sampling: `12 x 12 x 12` Monkhorst-Pack grid for every two-atom cell.
- Metallic occupations: Marzari-Vanderbilt smearing with `degauss = 0.02 Ry`; electronic threshold `conv_thr = 1e-08`.
- Spin treatment: spin polarized, with deterministic starting magnetizations Co `+0.3` and Cr `-0.3`.
- Geometry: static SCF on the exact source initial cells and fractional coordinates; no relaxation was performed.

## Cutoff sanity check

| ecutwfc (Ry) | ecutrho (Ry) | energy/atom (eV) | change vs 65 Ry (meV/atom) | status |
|---:|---:|---:|---:|---|
| 45 | 360 | -3224.24428378 | 9.3736 | formally_converged |
| 55 | 440 | -3224.25188528 | 1.7721 | formally_converged |
| 65 | 520 | -3224.25365742 | 0.0000 | formally_converged_after_checkpoint |

At the production-selection checkpoint, 55 Ry was formally converged and the 65 Ry calculation had been manually stopped near convergence; the checkpoint energy-difference magnitude was 1.78684 meV/atom. A pre-existing background process subsequently continued the 65 Ry job to formal convergence without a restart, giving a final 55-to-65 Ry difference of 1.77214 meV/atom. This does not change the selected 55/440 Ry production setting or the preliminary-study conclusion.

The cutoff decision and checkpoint are recorded in `dft_inputs/qe_config.json`; the machine-readable final audit is `results/tables/dft/cutoff_sanity_check.csv`.

## Converged results

| Phase | Label | fid | SRO | total energy (Ry) | energy/atom (Ry) | relative energy (meV/atom) | total magnetization (muB/cell) | absolute magnetization (muB/cell) | iterations | status |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| FCC | low | `gra62121526` | 0.000000 | -473.95628523 | -236.97814261 | 106.9544 | 0.2200 | 0.3900 | 35 | converged |
| FCC | high | `gra62121527` | 0.333333 | -473.97200724 | -236.98600362 | 0.0000 | -0.0000 | 0.0000 | 29 | converged |
| BCC | low | `gra64001864` | 0.000000 | -473.94434310 | -236.97217155 | 0.0000 | -0.0000 | 0.0000 | 32 | converged |
| BCC | high | `gra62121595` | 1.000000 | -473.92326720 | -236.96163360 | 143.3761 | 0.0000 | 0.0000 | 43 | converged |

All four calculations reached the electronic convergence criterion, printed a finite final total energy, and terminated normally with `JOB DONE`.

## FCC

Composition `{"Co": 0.5, "Cr": 0.5}`; 2 atoms; SRO 0.000000 (gra62121526) versus 0.333333 (gra62121527).

For the selected fixed-composition Co-Cr FCC configurations, increasing the aggregate first-shell SRO magnitude from 0.0000 to 0.3333 changed the static DFT energy by 106.954 meV/atom. The high-SRO configuration (`gra62121527`) was energetically lower.

## BCC

Composition `{"Co": 0.5, "Cr": 0.5}`; 2 atoms; SRO 0.000000 (gra64001864) versus 1.000000 (gra62121595).

For the selected fixed-composition Co-Cr BCC configurations, increasing the aggregate first-shell SRO magnitude from 0.0000 to 1.0000 changed the static DFT energy by 143.376 meV/atom. The low-SRO configuration (`gra64001864`) was energetically lower.

## Scope

These targeted calculations demonstrate that configurations with identical chemistry and atom count but different local ordering can exhibit different first-principles energies. The four-configuration study is a focused validation/extension of the larger SRO-ML analysis and should not be interpreted as establishing a universal causal SRO-energy relationship.

Machine-readable results: `results/tables/dft/dft_results.csv`. Figures: `figures/dft/dft_relative_energy.png`, `figures/dft/sro_vs_relative_energy.png`.
