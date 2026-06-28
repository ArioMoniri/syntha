# syntha MCP Connector — Privacy Policy

**Effective date:** 2026-06-28
**Maintainer:** Ariorad Moniri (Acibadem University School of Medicine, Istanbul, Turkey)
**Repository:** https://github.com/ArioMoniri/syntha
**License:** Apache-2.0

This document describes what the `syntha` MCP connector does and does not do with data. It is provided to satisfy the public-privacy-policy requirement of marketplace listings (the Anthropic Connector directory, Smithery, mcp.so, and similar registries).

## 1. What the connector does

The connector generates **fully synthetic** patient cohorts from two pre-trained Gaussian-copula models that are bundled inside the Python package. Outputs are delivered as CSV, FHIR R4 transaction Bundles, or JSON summaries. Every row returned is computer-generated; **no row of any real EHR is ever returned, embedded, or transmitted**.

## 2. What data the connector receives

The connector receives **only the MCP-tool arguments your Claude client (Claude Desktop, Claude.com custom connector, mcp-cli, Cursor, Continue, etc.) sends to its tools** — for example `n=100`, `cohort='tolerant'`, `seed=42`, `condition='Hipertansiyon == 1 & age > 60'`.

It does **not** receive, request, ingest, store, or transmit:

- Protected health information (PHI) of any kind;
- User personal data (name, email, organization, demographics);
- Real patient records;
- Your GitHub identity or any OAuth identity;
- Your conversations with Claude;
- Telemetry, usage analytics, or crash reports;
- Your local files (no current tool accepts file contents as an argument);
- Your IP address (in `stdio` transport mode the server is a local subprocess with no network identity).

## 3. What data the connector returns

Every output is computer-generated synthetic data:

- **CSV strings** with synthetic patient records (demographics, labs, vitals, comorbidity flags);
- **FHIR R4 NDJSON** transaction Bundles with synthetic Patient, Observation, Condition, Encounter, MedicationRequest, Procedure, CarePlan, DiagnosticReport, RiskAssessment, and FamilyMemberHistory resources;
- **JSON summaries** (cohort metadata, prevalences, reference-range coverage, etc.).

Every row is computer-generated; **no real-patient row is ever returned**.

## 4. What is bundled inside the connector

The Python package ships two trained copula summaries as JSON files inside the `syntha.bundled_models` package:

- `src/syntha/bundled_models/tolerant.json` — trained on **n = 135,569** de-identified episodes (~172 KB);
- `src/syntha/bundled_models/strict.json` — trained on **n = 55,141** de-identified episodes (~174 KB).

Each file contains **only** compressed marginal summaries:

- ~200 quantile values per continuous column (the empirical CDF, downsampled);
- Bernoulli probabilities per binary column;
- A Gaussian-copula correlation matrix;
- Column names and cohort metadata (cohort name, source date window).

These are **not raw EHR records**. They are statistical summaries from which no individual patient's row can be reconstructed.

## 5. Source-data provenance

The trained models were fitted on **anonymized retrospective EHR episodes**. The source data:

- Was **de-identified at source before release to the authors**;
- Is **never redistributed** by this connector or by the `syntha-ehr` Python package;
- Is not accessible through any tool the connector exposes;
- The link between the source records and the trained-model summaries was retained solely by the originating institution's data custodian and is not accessible to the connector authors.

## 6. Privacy audit gate

Every release of `syntha` runs the **Stadler 2022 nearest-synthetic-neighbor membership-inference attack (NN-MIA)** in CI. **The build fails at AUROC > 0.60** (the MIA-resistance threshold from the cited paper). The audit workflow lives at `.github/workflows/privacy-audit.yml`.

A logistic-regression attribute-inference attack (AIA) on sensitive comorbidity targets (hypertension, diabetes, hyperlipidemia) also runs, gated at AUROC ≤ 0.70.

These are **empirical privacy checks**, not formal differential-privacy guarantees. A (ε, δ)-DP wrapper on the sufficient statistics is planned (see `ROADMAP.md`).

## 7. Storage

The MCP server is **stateless**. It does **not**:

- Log tool invocations;
- Write to disk during normal operation;
- Persist any session, cohort, or user state across calls;
- Call any external service.

In `stdio` transport mode (the default, used by Claude Desktop), **no data leaves the user's machine** — the server runs as a local subprocess and has no network identity.

In `http` transport mode (e.g. Claude.com custom connector), **no data leaves the endpoint the user chooses** — the server binds to whatever host/port the operator configures. The operator is responsible for HTTPS termination, firewall rules, and access control in front of that endpoint.

## 8. Telemetry

**None.** The connector emits no telemetry, no usage pings, no crash reports, and no analytics events.

## 9. No analytics, no third-party SDKs

The only runtime dependencies (declared in `pyproject.toml`) are:

- `syntha-ehr` (this package);
- `mcp` ≥ 1.2 — Anthropic's official Python MCP SDK;
- `numpy`, `scipy`, `pandas` — computation;
- `scikit-learn` — used by the privacy audit;
- `click`, `pyyaml` — CLI / config plumbing.

None of these contact external services at runtime. There are no analytics SDKs, no telemetry SDKs, and no third-party tracking code.

## 10. Compliance posture

`syntha` is a **software tool for generating synthetic data**. It is:

- **NOT** a clinical decision-support system;
- **NOT** a regulated medical device (not FDA-regulated, not EU MDR/IVDR-regulated, not TİTCK-regulated);
- **NOT** intended for diagnosis, treatment, or any direct patient-care decision.

Outputs **must be recalibrated against population marginals** (TÜİK, TURDEP-II, or equivalent reference sources) before any downstream deployment; uncalibrated use will systematically misrepresent population disease prevalence. See `ROADMAP.md` for limitations.

Because no real-patient row is ever returned, the connector handles **no personal data** within the meaning of GDPR Article 4(1) or KVKK Article 3(1)(d).

## 11. License and contact

- **License:** Apache-2.0 (see `LICENSE`).
- **Support / questions / bug reports:** GitHub Issues — https://github.com/ArioMoniri/syntha/issues
- **Security disclosures:** private GitHub Security Advisory at https://github.com/ArioMoniri/syntha/security/advisories

## 12. Changes to this policy

This document is versioned in git. Material changes will be reflected in a new release with an updated effective date above.

---

This policy is published in good faith to satisfy marketplace publication requirements. It describes the connector's actual behavior as implemented in the linked git tag. If a downstream user observes behavior inconsistent with this policy, please open an issue.
