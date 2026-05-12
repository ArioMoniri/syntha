# Architecture

## Why a Gaussian copula?

Episode rows are a *mixed* feature vector: ~15 continuous labs and ~30 binary flags, with substantial column-wise missingness. A Gaussian copula handles this combination natively:

1. Each marginal is modeled independently — Bernoulli for flags, empirical quantile function for labs. This preserves heavy tails, skew, and even multi-modality that a Gaussian mixture would smooth away.
2. Dependence is captured by a single correlation matrix in Gaussian-score space. Spearman rank correlation is invariant to monotonic transforms of the marginals, so the same matrix works regardless of how non-Normal each lab actually is.
3. Missingness is modeled as independent column-wise Bernoulli noise. This is the simplest defensible assumption; more elaborate MNAR modeling is left for v2.

## Spearman-to-Gaussian transform

For a Gaussian copula, the relationship between Spearman ρ_s and the Gaussian correlation parameter ρ is `ρ = 2 sin(π ρ_s / 6)`. We apply this exactly in `copula.py` so the recovered rank correlations match the source.

## PSD projection

Pairwise-complete Spearman on data with structured missingness frequently produces a near-PSD matrix that is not quite PSD. `_nearest_psd` clips negative eigenvalues to `1e-6` and rescales to a valid correlation matrix.

## Physiologic constraints

The copula does not "know" that systolic must exceed diastolic. We post-filter:

| Constraint | Rationale |
|---|---|
| `systolic ≥ diastolic + 20 mmHg` | Pulse pressure floor for living adults |
| `\|total − (HDL + LDL + TG/5)\| ≤ 40` | Friedewald coherence, loosened because this cohort uses direct LDL |
| Not `(creatinine > 2.0 AND eGFR > 90)` | Internal contradiction — high creatinine cannot coexist with preserved GFR |

Rows failing any enabled constraint are dropped; the pipeline oversamples by `oversample_factor` (default 1.5) and retries up to 5 rounds.

## FHIR R4 output

Each synthetic episode becomes a transaction Bundle containing:

* one `Patient` (gender, derived `birthDate`, Turkey as `birthPlace`);
* one `Observation` per non-null lab/vital, with the appropriate LOINC code and UCUM unit;
* one `Condition` per active comorbidity flag, with the appropriate SNOMED CT code.

Output formats: `bundles.ndjson` (one bundle per line — Synthea bulk-FHIR style) or individual JSON files in `fhir/bundles/`.

## Two cohorts, two models

`strict` and `tolerant` cohorts have different inclusion criteria and therefore different joint distributions. We train and persist separate copulas (`copula_strict.pkl`, `copula_tolerant.pkl`) so each can be sampled independently.
