# 🧑‍⚕️🤖 Final v0.5 review — CMO + ML engineer

Acting as two reviewer agents simultaneously. Each scores the v0.5 scope on what's shipped, what's missing, and what should block the v0.5.0 tag from going out.

---

## 🩺 Chief Medical Officer review

### What's solid

| Item | Verdict | Notes |
|---|---|---|
| **5.1 Polyserial + tetrachoric** | ✅ **Approve** | Patient-safety prerequisite met. Lab↔disease correlations now 94.2% of source (was 83.7%). A junior data scientist training a HTN-prediction model on this will see the correct signal strength. |
| **5.4 DiagnosticReport panels** | ✅ Approve | FHIR ETL consumers will accept this. Five panels covered. |
| **G1 HTEST marker** | ✅ Approve | Every Patient now carries the standard `terminology.hl7.org/CodeSystem/v3-ActReason#HTEST` tag. Synthetic patients can no longer be confused with real ones downstream. |
| **G3 Clinical reference ranges** | ✅ Approve | Sex-specific Hb / Cr ranges + sex-agnostic ranges for 14 other labs. Citations to Tietz 8th ed., Mayo Labs, KDIGO 2024. |

### What I would NOT sign off on without these additions

| Concern | Required before v0.5.0 ships? |
|---|---|
| **5.5 Lab time-series** — single `_latest` value per lab is clinically unrealistic | 🔴 **Yes** — without this, no real clinician would call this "EHR-like" |
| **5.2 Conditional missingness** — synthetic missing-data pattern is Swiss-cheese, doesn't match real EHR panel-ordering behavior | 🟡 Strongly recommended |
| **Charlson CCI surfaced as `RiskAssessment`** — already in the CSV, trivial to expose | 🟡 Low cost, high clinical signal |
| **PHQ-9 / GAD-7** — patients flagged with depression/anxiety should have the standard screening score on file | 🟡 Adds clinical realism in psych modules |

### Patient-safety guardrails — gating

- **G2 privacy CI** — must run before v0.5.0 ships. Without it, we have no formal evidence the model doesn't memorize rare patients. Membership inference + attribute inference attacks measure exactly that.

---

## 🤖 ML engineer review

### What's solid

| Item | Verdict | Notes |
|---|---|---|
| **Polyserial/tetrachoric math** | ✅ Approve | Olsson 1982 two-step and bisection-based tetrachoric are textbook implementations. 14 unit tests with toy bivariate-normal ground truth, all recovered within ±0.08. |
| **Spearman→Gaussian backward-compat** | ✅ Approve | `corr_method="spearman"` preserved for v0.4 model reproducibility. Smart. |
| **Empirical validation on real data** | ✅ Approve | +10.5 percentage point magnitude recovery on the strict cohort. |
| **AST-validated conditional sampling** | ✅ Approve | Rejection-sampling with whitelist AST walk is exactly the right pattern. No `eval()` exposure. |
| **Test discipline** | ✅ Approve | 70 tests, ruff clean, codecov reporting, CI matrix 4-Python × 3-OS. Solid engineering hygiene. |

### What's concerning from a generative-modeling standpoint

| Concern | Severity | Fix |
|---|---|---|
| **No held-out validation split** — `validate.py` compares synthetic vs the *whole* training set. Doesn't catch memorization. | 🔴 High | Add 80/20 split + report KS on both train and test halves; flag if train KS << test KS (= overfitting). |
| **No formal privacy audit** — no membership-inference attack run anywhere. We're shipping a generative model trained on PHI-adjacent data with zero quantitative privacy evidence. | 🔴 High | This is G2 from the MO review — must land before v0.5.0. |
| **No TSTR benchmark** — we claim synthetic data is useful for downstream ML, but no Train-on-Synthetic / Test-on-Real evidence anywhere. | 🟡 Medium — could wait for v0.5.6 | But the dashboard prominently advertises it as a planned card; users will look. |
| **Bundled JSON model size = 173 KB per cohort** — fine, but if we add 30 more columns the file balloons. | 🟢 Low | Keep an eye on this; quantize quantile grids further if it exceeds 500 KB. |
| **Independent column-wise missingness** — known limitation; ML engineer agrees with CMO this should land in v0.5. | 🟡 Medium | 5.2 in the roadmap. |

### Performance + scale

- The mixed-correlation matrix fit is **O(k²·n)** where k=75 columns, n=135k rows. Tetrachoric bisection is the slow part (~80 calls to scipy's `brentq`). Wall time on the strict cohort: ~3 seconds. Acceptable.
- DP-SGD wrapper (5.3) will add ~3× to fit time. Should expose `--no-dp` for the common case.

---

## 📋 Combined verdict

| Item | Must-ship-before-v0.5.0? |
|---|---|
| 5.1 Polyserial + tetrachoric | ✅ shipped |
| 5.4 DiagnosticReport panels | ✅ shipped |
| G1 HTEST tag | ✅ shipped |
| G3 reference ranges | ✅ shipped |
| **5.5 Lab time-series** | 🔴 must ship |
| **G2 Privacy CI** | 🔴 must ship |
| **5.2 Conditional missingness** | 🟡 should ship |
| 5.6 SynthEHRella TSTR | 🟢 defer to v0.5.1 (it's a tooling integration, not a behavior change) |
| 5.3 DP-SGD wrapper | 🟢 defer to v0.5.2 (optional feature, not a default) |

### Recommended action

1. Ship **5.5 + G2 + 5.2** in this commit batch.
2. Add **Charlson CCI RiskAssessment + PHQ-9/GAD-7** as clinical-realism bonuses (low cost, high signal).
3. Then tag **v0.5.0** with confidence.

— Joint sign-off, 2026-05-14
