# 🩺 Medical Officer Review — v0.5 Roadmap

**Reviewer perspective:** Acting as a chief medical officer / clinical informaticist responsible for signing off that synthetic data produced by this tool would be *clinically plausible* and *safe to share with downstream investigators*. Reviewing each v0.5 item for: (a) clinical plausibility, (b) downstream utility, (c) patient-safety risk if misused, (d) implementation priority.

**Bottom line:** All six items are logically sound. I rank-order them differently than the engineering team's order, flag one item that needs a clinical addition before shipping, and identify three "must-do" guardrails the roadmap is missing.

---

## ✅ Item-by-item clinical review

### 5.1 Polyserial + tetrachoric correlation — **APPROVED, HIGHEST PRIORITY**

**Clinical reasoning:** The 50% attenuation on continuous↔binary correlations is the single biggest reason this tool is currently *unsafe for downstream ML training*. A junior data scientist who trains a hypertension-prediction model on the current synthetic output will see the lab-pressure relationship as half as strong as it really is. They'll dismiss systolic BP as a "weak predictor" and tune their feature weights accordingly. When that model touches a real patient, BP will be drastically underweighted.

This is exactly the kind of subtle methodological error that makes synthetic data unsafe in clinical practice — *the model passes statistical sanity checks but fails downstream*. Fixing this is a **patient-safety prerequisite**, not just a fidelity improvement.

**Verdict:** Implement first. No clinical addition needed. The math has 40 years of psychometric and biostatistical backing (Olsson 1982, polycor R package in production use since 2003).

### 5.2 Joint missingness model — **APPROVED, but with one clinical clarification**

**Clinical reasoning:** Yes — in real EHR, missingness is panel-correlated, not column-independent. Lab panels are *ordered as units*: when a clinician orders a "lipid panel," all four constituent labs appear together. The current Swiss-cheese pattern doesn't pass clinical-data-scientist sniff test.

**Clinical addition needed:** Missingness is *also conditional on patient characteristics*. Specifically:
- A diabetic patient is much more likely to have an HbA1c on file than a healthy 30-year-old
- A patient with chronic kidney disease has more frequent creatinine measurements
- Patients with the depression flag have more frequent PHQ-9 measurements

So the missingness model should not just be "panel-co-missingness" but rather *missingness conditional on the comorbidity flags*. Without this conditional structure, the synthetic data will have unrealistic patterns like "fully complete lab panel on a 22-year-old healthy adult" or "missing creatinine on a CKD patient" — both are immediately suspicious to a clinician.

**Verdict:** Approved with the recommendation to **make missingness conditional on the binary comorbidity vector**, not just self-correlated.

### 5.3 Differential privacy wrapper — **APPROVED, with patient-safety caveat**

**Clinical reasoning:** Differential privacy is essential for any clinical synthetic-data tool that might be redistributed. The ε=1.0 baseline is reasonable for moderate cohorts (≥10k patients); for cohorts <1k, ε should be more like 0.5 or smaller.

**Patient-safety caveat:** At low ε (high privacy), the synthetic data's predictive utility *will* degrade. Users should be warned that DP-synthetic data is **not suitable for clinical-decision-support model training**, only for:
- Pipeline integration testing (where utility doesn't matter)
- Teaching / coursework (where small fidelity loss is OK)
- Pre-screening of larger studies

I recommend that:
1. The CLI display a clear warning when `--epsilon < 2.0` saying "Output suitable for technical-integration testing only, not for ML-model training intended for clinical use"
2. The validation report include a flag `intended_use: technical-integration-testing` when DP is on

**Verdict:** Approved with mandatory user-facing warnings about restricted use cases.

### 5.4 Lab-panel grouping → DiagnosticReport — **APPROVED**

**Clinical reasoning:** Every real-world FHIR consumer (HAPI, Aidbox, Microsoft FHIR Service, OMOP ETL) expects labs to be grouped into `DiagnosticReport` resources. The current per-Observation output is technically valid FHIR but pragmatically incomplete. This is a "must-have" for any downstream FHIR ETL pipeline.

**Two clinical refinements:**
1. The 5 panels you list are correct, but add a **DiagnosticReport "Routine outpatient visit"** that groups the panels themselves (i.e., a parent DiagnosticReport containing CBC + CMP + Lipid). This matches how real "annual physical" lab orders come in.
2. Set `DiagnosticReport.status = "final"` (you have this), but also set `category` to LOINC code matching the panel type (e.g., `LP7795-0` for "Laboratory" category).

**Verdict:** Approved with the two minor structural additions.

### 5.5 Lab time-series + intra-encounter BP — **APPROVED, but verify drift rates**

**Clinical reasoning:** Lab time-series generation is great, but the drift rates you propose need to be cohort-appropriate:

**For healthy adults (which this cohort is):**
- eGFR: declines ~0.5–1 mL/min/year (you have this right)
- HbA1c: σ ≈ 0.2% over 3 months in non-diabetics; σ ≈ 0.5% in diabetics
- LDL: substantial month-to-month variation (σ ≈ 15 mg/dL), reasonable
- Hemoglobin: very stable (σ ≈ 0.3 g/dL) — your `lab_drift_scale: 0.05` (5%) might be too much for Hb (which is ±2% biologically)

**Clinical addition:** Make the drift rates **column-specific** (`drift_scale_per_column`), not a single global value. Use literature-derived biological variation coefficients (Westgard QC database has these for every common analyte).

**For intra-encounter BP:**
- Two BP measurements 5 min apart typically differ by 5–10 mmHg (white-coat effect dissipates)
- Patient should consistently be lower on the second reading (clinical pattern)
- Don't just add random noise — model the systematic decline

**Verdict:** Approved with column-specific drift rates and clinical-pattern-aware BP modeling.

### 5.6 SynthEHRella TSTR benchmark — **APPROVED**

**Clinical reasoning:** This is the *only* item that provides external validation. Without it, all the other improvements are unverifiable claims. I'd insist on this before any v0.5 release goes out.

**Clinical refinement:** Use **three** target tasks, not just hypertension:
1. **Hypertension prediction** (continuous lab → binary outcome — tests Limitation #1 fix directly)
2. **Disease co-occurrence prediction** (e.g., given DM, predict hyperlipidemia — tests binary↔binary structure)
3. **Lab-value regression** (e.g., predict eGFR from age + creatinine + comorbidities — tests continuous joint structure)

Report TSTR ROC-AUC / RMSE for all three; include a *fairness slice* by gender + age decade.

**Verdict:** Approved with multi-task evaluation.

---

## 🚨 Three guardrails the roadmap is missing

These are non-negotiable for me to sign off on v0.5 being "scientifically usable":

### G1 — Source-attribution audit trail

Every synthetic patient needs to carry a **clear "this is synthetic" marker** in the FHIR output. The current `Patient.meta.profile` doesn't say so. I want to see:

```json
{
  "resourceType": "Patient",
  "meta": {
    "tag": [{
      "system": "http://terminology.hl7.org/CodeSystem/v3-ActReason",
      "code": "HTEST",
      "display": "Test Patient (synthetic, not real)"
    }],
    "profile": [...]
  }
}
```

This is the FHIR standard way to mark a resource as synthetic/test, and it's mandated by Synthea. Without it, there's a real risk of synthetic patients leaking into a real EHR and being treated as real patients. **This is a patient-safety hazard.**

### G2 — No-PHI guarantee, audited

The model card already says the source CSVs are anonymized. But for v0.5 I want a **statistical attack** included in CI:
- Membership inference attack on the published model
- Attribute inference attack on rare-comorbidity patients
- The CI fails if either succeeds above chance

Both can be borrowed from SynQP. ~100 LOC. Should run on every release.

### G3 — Clinically-validated reference ranges per lab

The current `PHYSIOLOGIC_BOUNDS` in `schema.py` has gross "alive-vs-dead" ranges (e.g., hemoglobin 4–22 g/dL). For *clinical* validity we need *abnormal-vs-normal* ranges:

- Adult male hemoglobin reference: 13.5–17.5 g/dL
- Adult female: 12.0–15.5 g/dL
- Pediatric: different
- Pregnancy: different

A synthetic male patient with Hb = 8 g/dL is anatomically possible but *clinically anemic*. The tool should be able to flag synthetic patients whose lab values would trigger automatic alerts in a real clinical lab.

**Implementation:** add `CLINICAL_NORMAL_RANGES` table with sex-specific reference intervals. Add a `--clinically-realistic-only` CLI flag that resamples until labs fall within reference range (for studies needing "definitely healthy" patients).

---

## 📋 Recommended implementation order (revised)

| # | Item | Why this order |
|---|---|---|
| 1 | **G1: Synthetic-marker FHIR tag** | Patient-safety prerequisite. ~5 LOC. Ship immediately. |
| 2 | **5.1: Polyserial + tetrachoric** | Biggest scientific win. Unblocks downstream ML use. ~150 LOC. |
| 3 | **5.4: DiagnosticReport panels** | FHIR-consumer must-have. Low effort. ~100 LOC. |
| 4 | **G3: Clinical reference ranges** | Patient-safety polish. ~50 LOC + table. |
| 5 | **5.2 + clinical refinement: Conditional missingness** | High fidelity gain. ~150 LOC. |
| 6 | **5.5: Lab time-series with column-specific drift** | Clinical realism. ~100 LOC. |
| 7 | **5.6: SynthEHRella TSTR benchmark** | External validation. ~200 LOC. |
| 8 | **G2: Privacy attack CI** | Privacy assurance. ~120 LOC. |
| 9 | **5.3: Differential privacy** | Optional for users who need it. ~80 LOC. |

Total: ~950 LOC across v0.5. Roughly 4–5 working days of focused effort.

---

## 🧭 Summary

The roadmap is **scientifically logical** and **clinically defensible**. The mathematical methods cited (polyserial, tetrachoric, latent-Gaussian copula, DP-SGD) are all in mainstream biostatistical use and have decades of supporting literature.

I sign off on v0.5 going to implementation, with the three guardrails (G1, G2, G3) added and the clinical refinements noted above included.

— Acting CMO review, 2026-05-13
