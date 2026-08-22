# Scientific definition of the 84k SRO labels

Status: resolved for the supplied 40 columns by source review and independent numerical reproduction. Date: 2026-08-22.

## Sources inspected

- Dataset record: https://doi.org/10.5281/zenodo.10854500
- Source publication: K. Li, K. Choudhary, B. DeCost, M. Greenwood and J. Hattrick-Simpers, *Efficient first principles based modeling via machine learning: from simple representations to high entropy materials*, Journal of Materials Chemistry A 12 (2024) 12412–12422, https://doi.org/10.1039/D4TA00982G
- Official repository: https://github.com/mathsphy/high-entropy-alloys-dataset-ML, inspected at commit `dc62220ff35a31f75742201c3edac9a29b9c2c97`
- Local `explore_data.py`, `demo_ML_training.py`, all supplied CSV headers and selected initial structures.
- Matminer documentation for the separate `ChemicalOrdering` descriptor: https://hackingmaterials.lbl.gov/matminer/matminer.featurizers.structure.html

The publication, repository and Zenodo record call these quantities SRO and plot `mean abs SRO1`/`SRO2`, but they do not publish the script that generated `SROs_structure_ini.csv` or spell out its pair-level equation. Therefore, the exact convention below was established by independently calculating conventional Warren–Cowley coefficients from the supplied initial cells and reproducing the file values.

## Exact underlying quantity

For each structure, coordination shell `s`, and each **unique unlike-element pair** A–B present in the structure, the underlying value is the Warren–Cowley coefficient

`alpha_AB(s) = 1 - P_s(B | A) / c_B`,

where `c_B` is the global atomic fraction of B and `P_s(B | A)` is the fraction of shell-`s` neighbours around A sites that are B. Periodicity and pair-count balance make the corresponding A-around-B value equivalent for these fixed-coordination ideal cells, so the file retains one value per unordered unlike pair.

Interpretation under this convention:

- `alpha_AB = 0`: pair occurrence is random for that shell;
- `alpha_AB < 0`: unlike A–B neighbours occur more often than random, an ordering tendency;
- `alpha_AB > 0`: unlike A–B neighbours occur less often than random, consistent with like-species clustering or A–B avoidance.

The sign is therefore the conventional WC sign and must not be reversed.

## Pair resolution and aggregation

The CSV is **not pair-resolved**. For a structure with `k` elements, the calculation produces `k(k-1)/2` unlike-pair WC values for each shell, then stores summary statistics across that pair set. Pair identities and individual coefficients were discarded and cannot be recovered from the 40 summary columns alone.

For each shell `n = 1, 2, 3, 4`, the columns mean:

| Column pattern | Exact meaning across the unique unlike-pair alpha values in shell n |
|---|---|
| `mean SROn` | arithmetic mean of signed alpha |
| `max SROn` | largest signed alpha |
| `min SROn` | smallest signed alpha |
| `std SROn` | standard deviation of signed alpha values, using the dataset implementation's NumPy/Pandas convention; binary rows have zero |
| `range SROn` | `max SROn - min SROn` |
| `mean abs SROn` | arithmetic mean of `abs(alpha)` |
| `max abs SROn` | largest `abs(alpha)` |
| `min abs SROn` | smallest `abs(alpha)` |
| `std abs SROn` | standard deviation across `abs(alpha)` |
| `range abs SROn` | `max abs SROn - min abs SROn` |

For binary structures only one unlike pair exists, which explains why mean, maximum and minimum are identical and both ranges/standard deviations are zero.

## Neighbour shells

`SRO1` through `SRO4` are the first four distinct geometric neighbour-distance shells of the ideal **initial, unrelaxed** periodic cell. They are not temperatures, time indices or powers of a scalar descriptor.

For ideal lattices the expected coordination counts and distances are:

| Phase | Shell 1 | Shell 2 | Shell 3 | Shell 4 |
|---|---|---|---|---|
| FCC | 12 at `a/sqrt(2)` | 6 at `a` | 24 at `a*sqrt(3/2)` | 12 at `a*sqrt(2)` |
| BCC | 8 at `a*sqrt(3)/2` | 6 at `a` | 12 at `a*sqrt(2)` | 24 at `a*sqrt(11)/2` |

The labels describe the deliberately constructed ordered/SQS initial configurations. They are not equilibrium temperature-dependent SRO from DFT or Monte Carlo.

## Independent reproduction check

An independent periodic-neighbour calculation was applied to supplied binary and ternary initial structures. It grouped neighbours by the first four distinct distances, calculated unique unlike-pair WC alpha values, and recomputed the four principal summary statistics. Values matched the supplied file to displayed floating-point precision for every tested shell.

Example: ternary FCC `AlCr6Co` (`fid=ced41336001`) has first-shell pair coefficients `[-1/3, -1/9, -1/9]`. Their mean is `-0.185185...`, maximum `-0.111111...`, minimum `-0.333333...`, and mean absolute value `0.185185...`; all match the supplied SRO1 row. The same test matched shells 2–4 and multiple binary/ternary cells.

The separately supplied Matminer columns `mean ordering parameter shell 1/2/3` are **not** the same values: across all 83,797 rows, exact equality with `mean abs SRO1` occurs for only about 0.75% and the first-shell correlation is about 0.717. Those columns must not be substituted for the SRO file and are excluded as direct target-family proxies from default ingestion.

## ML-target decision

For the 84k source alone, the recommended primary scalar target is:

**`mean abs SRO1` — mean magnitude of first-neighbour Warren–Cowley alpha across all unique unlike-element pairs.**

It is the target emphasized by the authors' exploratory script, is non-negative, does not suffer cancellation between positive and negative pair coefficients, and measures overall first-shell departure from random mixing.

It must be described as an **aggregate first-shell ordering magnitude**, not “the Warren–Cowley parameter” for a specific chemical pair. Separate secondary targets may use `mean abs SRO2` through `mean abs SRO4`. Signed `mean SROn` is interpretable but can hide strong opposing pair tendencies by cancellation.

## Scientific readiness and limitations

The dataset is ready for leakage-controlled ML of aggregate initial-configuration ordering magnitude across FCC/BCC cells. It is not sufficient for the project's eventual pair-resolved thermodynamic target because:

- individual pair alpha values and pair identities are absent;
- temperature is absent;
- labels are deterministic descriptors of the input initial arrangement, not relaxed or equilibrium SRO;
- exact structure descriptors can encode the same neighbour occupations used to calculate the label, creating a near-tautological prediction task;
- rows from the same composition/alloy family are not fully independent.

Primary models should therefore begin with composition/elemental descriptors and clearly state the prediction scenario. Any use of arrangement-sensitive initial descriptors requires a separate ablation and leakage discussion. Pair-resolved WC alpha requires recalculation from the stored initial structures into `sro_long` and validation before it becomes the project's final scientific target.
