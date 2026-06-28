# syntha as a Claude / MCP connector

`syntha-mcp` is a [Model Context Protocol](https://modelcontextprotocol.io) server that exposes syntha's synthetic-cohort generator as a set of tools any MCP-compatible client can call — Claude Desktop, the Claude.com custom-connector slot, [mcp-cli](https://github.com/modelcontextprotocol/mcp-cli), Cursor, Continue, and others.

No real patient data is ever returned. The server samples from the two compressed empirical-summary JSONs bundled with this package (`tolerant`, `strict`) — ≈200 quantiles per continuous column plus a correlation matrix, with no rows of the source EHR embedded.

## Install

```bash
pip install "syntha-ehr[mcp]"
```

This installs the [`mcp`](https://pypi.org/project/mcp) Python SDK alongside syntha and registers a `syntha-mcp` console script.

## Tools exposed (34)

The connector exposes 34 tools across three categories: **Generate** (produce synthetic data), **Inspect** (introspect cohorts, schemas, and registries), and **Validate** (check synthetic data against reference ranges, physiologic constraints, and privacy bounds).

### Generate — produce synthetic data

| Tool | What it does | Typical inputs |
|---|---|---|
| `generate_cohort_csv` | N synthetic patients as a CSV string; physiologic-validity filter on by default; curation flags dropped by default | `n`, `cohort` (`tolerant`/`strict`), `seed`, `apply_constraints`, `drop_curation_flags` |
| `generate_cohort_fhir` | N synthetic patients as **FHIR R4** transaction-Bundle NDJSON, with the 9 Synthea-style clinical modules running | `n`, `cohort`, `seed`, `modules` |
| `generate_longitudinal_cohort` | N synthetic patients each with a multi-visit longitudinal trajectory (lab drift, condition progression) as CSV | `n`, `cohort`, `n_visits`, `visit_interval_days`, `drift_profile`, `seed` |
| `generate_longitudinal_fhir` | Same longitudinal trajectories as a FHIR R4 transaction Bundle with Encounter + Observation resources per visit | `n`, `cohort`, `n_visits`, `visit_interval_days`, `drift_profile`, `seed` |
| `generate_cohort_with_lab_history` | N patients plus an attached lab-history table (LOINC-coded series per panel) | `n`, `cohort`, `panels`, `n_history_points`, `seed` |
| `generate_clinical_assessments` | Synthesize scored clinical-assessment instruments (PHQ-9, GAD-7, MMSE, etc.) consistent with the patient row | `n`, `cohort`, `instruments`, `seed` |
| `sample_conditional` | AST-validated rejection sampling against a pandas-style filter expression — e.g. `"Hipertansiyon == 1 & age > 60 & bp_systolic >= 140"` | `condition`, `n`, `cohort`, `max_attempts`, `seed` |
| `apply_physiologic_constraints` | Filter / repair a synthetic batch in-place against the bundled physiologic-validity rules | `rows` (CSV/JSON), `mode` (`filter`/`repair`) |

### Inspect — introspect cohorts, schemas, and registries

| Tool | What it does | Typical inputs |
|---|---|---|
| `syntha_version` | Library version + bundled-cohort fingerprints | (none) |
| `list_bundled_cohorts` | The cohorts shipped with the connector — `tolerant` (n_train ≈ 135,569) and `strict` (n_train ≈ 55,141) | (none) |
| `get_cohort_summary` | n_train, modeled columns, **comorbidity prevalences**, source date window | `cohort` |
| `get_model_card` | Returns the model-card JSON for a bundled cohort (training metadata, eval metrics, intended use) | `cohort` |
| `list_schema_columns` | The full set of modeled columns with dtype and role (demographic / vital / lab / condition) | `cohort` |
| `list_condition_codes` | The condition flag columns with their ICD-10-equivalent labels | (none) |
| `list_lab_loinc_codes` | The lab columns mapped to LOINC codes | (none) |
| `list_lab_panels` | The lab panels (CMP, CBC, lipid, thyroid, etc.) and their member analytes | (none) |
| `list_lab_drift_profiles` | The longitudinal lab-drift profiles available for `generate_longitudinal_*` | (none) |
| `list_rxnorm_medications` | The medications used by the prescribing modules, mapped to RxNorm | (none) |
| `list_clinical_modules` | The 9 modules and the source flag each one fires on | (none) |
| `list_modules_detail` | Full module manifest — code systems used, generated resource types, firing rules | (none) |
| `list_physiologic_constraints` | The 3 + 1 validity rules (pulse pressure ≥ 20, Friedewald coherence, eGFR ↔ creatinine consistency, DBP ≤ SBP) | (none) |
| `list_reference_ranges` | Adult reference ranges (low / high / units) for every modeled lab and vital | (none) |
| `list_locale_data` | Locale-bound name/address/identifier pools (Turkish locale) | (none) |
| `list_clinical_assessment_instruments` | The scored instruments available to `generate_clinical_assessments` (PHQ-9, GAD-7, MMSE…) | (none) |
| `list_pipeline_config_options` | The configurable knobs for the generation pipeline (defaults + valid ranges) | (none) |
| `get_correlation_pairs` | The top-k correlated column pairs from the bundled correlation matrix | `cohort`, `k` |
| `ckd_stage_for_egfr` | Returns the KDIGO CKD stage for a given eGFR value | `egfr` |
| `validate_condition_expression` | Statically validates a filter expression against the schema before sampling | `expression`, `cohort` |

### Validate — check synthetic data quality

| Tool | What it does | Typical inputs |
|---|---|---|
| `validate_synthetic_csv` | Validate a CSV the user generated elsewhere against syntha's schema + physiologic rules | `csv`, `cohort` |
| `validate_against_bundled_cohort` | Statistical comparison (marginals, KS, correlation drift) of a user CSV against a bundled cohort | `csv`, `cohort` |
| `fraction_within_reference` | For each lab/vital, fraction of rows inside the adult reference range | `csv` |
| `check_row_within_reference` | Per-row reference-range check; returns which analytes are flagged H/L | `row` (single record) |
| `privacy_audit` | Runs the Stadler-2022 nearest-synthetic-neighbor MIA on a user CSV against a bundled cohort | `csv`, `cohort` |
| `privacy_audit_bundled` | Same MIA run against the bundled `tolerant` / `strict` cohort itself (regression check) | `cohort` |

## Use with Claude Desktop

Open Claude Desktop → Settings → Developer → *Edit Config*, and add:

```json
{
  "mcpServers": {
    "syntha": {
      "command": "syntha-mcp",
      "args": []
    }
  }
}
```

If `syntha-mcp` isn't on your `$PATH` (e.g. installed in a virtualenv), point at it explicitly:

```json
{
  "mcpServers": {
    "syntha": {
      "command": "/absolute/path/to/.venv/bin/syntha-mcp"
    }
  }
}
```

Restart Claude Desktop. You'll see the syntha tools appear next to your prompt input.

### Example prompts

> *"Using the syntha connector, give me 50 synthetic patients aged 60+ with hypertension and diabetes, as a CSV."*

> *"Generate 10 FHIR R4 bundles from syntha's tolerant cohort and show me the LOINC codes in the first bundle."*

> *"What's the prevalence of thyroid disorders in syntha's tolerant cohort? Then sample 20 patients with that condition."*

## Use with Claude.com custom connector (Streamable HTTP)

Run the server in HTTP mode and point Claude.com at it:

```bash
syntha-mcp --transport http --host 127.0.0.1 --port 8765
```

Then in Claude.com → *Settings → Connectors → Add custom connector*, paste:

```
http://127.0.0.1:8765/mcp
```

If you want it reachable from the web, terminate TLS in front (Caddy, nginx, Cloudflare tunnel, etc.) so the URL becomes `https://syntha.your-domain.tld/mcp`.

## Use with mcp-cli (smoke test)

```bash
pip install mcp-cli
mcp-cli call syntha generate_cohort_csv n=10 cohort=tolerant
mcp-cli call syntha sample_conditional condition="age > 60 & Hipertansiyon == 1" n=5
```

## Marketplace publication

Submission to the Claude Connector directory at <https://claude.com/connectors> goes through one of two paths: the **MCPB / desktop-extension** form (what syntha is positioned for) or the **Streamable HTTP / remote-connector** form (requires hosted HTTPS + OAuth + a Team/Enterprise org). This section enumerates what is required for the MCPB path, what we already have, what still needs to be authored, and what must come from the maintainer.

### Already in the repo

| Item | Where | Notes |
|---|---|---|
| **Manifest (`manifest.json`)** | `/mcp/manifest.json` | Declares name, version, tools, entry point. Bump `0.5.9 → 0.5.10` on submission. The `$schema` currently points at `dxt-manifest.json` — swap to the MCPB schema URL once Anthropic publishes a stable one. |
| **Support contact** | `https://github.com/ArioMoniri/syntha/issues` | Already in the manifest. A monitored email is optional. |
| **Public documentation URL** | `https://github.com/ArioMoniri/syntha/blob/main/docs/MCP.md` | Already referenced in the manifest and present in the repo. |
| **Listing copy (short + long description)** | `manifest.json` `description` / `long_description` | Self-sufficient. Will shorten to a ~140-char tagline for the directory card. |

### To author before submission

| Item | Why | Plan |
|---|---|---|
| **Tool annotations (`title` + `readOnlyHint` / `destructiveHint`) on every tool** | Most common rejection reason per Anthropic and third-party reports (sunpeak.ai). All syntha tools are read-only or generate-only: every tool in `manifest.json` `tools[]` gets `readOnlyHint: true` plus a human-readable `title`. | Edit `/mcp/manifest.json`. |
| **Public icon (PNG, 512×512, transparent)** | Required field; spec is 512×512 (256×256 min), transparent PNG. Current manifest points at a GitHub avatar which is not square / not transparent. | Generate a dedicated `icon.png` at `/mcp/icon.png` and reference by relative path. Design needs maintainer approval. |
| **Privacy policy URL** | Anthropic flags missing privacy policies as immediate rejection. Required even though syntha never returns PHI — because the connector is software the user runs. | Add `/docs/PRIVACY.md` and serve via the existing GitHub Pages site. Must state: no telemetry, disk-only reads of bundled artifacts, no network egress, no user-data collection. Clinical no-PHI assertion needs maintainer sign-off. |
| **Terms of service URL** | Standard for directory listing alongside the privacy policy. | Add `/docs/TERMS.md` restating Apache-2.0 + the research-only / not-for-clinical-decisions disclaimer already in `MEDICAL_OFFICER_REVIEW_v0.5.md`. |
| **Runbook with realistic sample prompts** | Anthropic requires submissions include a runbook with a test account pre-populated with realistic data — not an empty account. | syntha ships bundled cohorts (tolerant 135,569 / strict 55,141) so output is realistic on first run with zero setup. Write a 1-page `RUNBOOK.md` with five canned prompts: list cohorts, generate 20 CSV patients, generate 5 FHIR bundles, sample 10 hypertensive patients over 60, list physiologic constraints. |
| **Screenshots / demo prompts for the listing** | Listing cards typically show screenshots, cropped to the response pane (not the full chat). | Generate 3–4 screenshots: `list_bundled_cohorts` output, `generate_cohort_csv` first 5 rows, `generate_cohort_fhir` Bundle preview, `sample_conditional` filter expression. |

### Required from the maintainer (Ariorad / Acibadem)

| Item | Why | Action |
|---|---|---|
| **Anthropic / Claude.ai account for submission** | Submission portal requires sign-in. | Sign in to Claude.ai with personal account. No API key is documented as required for the submission flow itself. |
| **Author identity / ORCID / institutional affiliation** | Acibadem affiliation strengthens trust for a clinical-data connector and may be checked during review. ORCID is not formally required but recommended. | Provide ORCID + Acibadem affiliation in the submission copy. Already present in `CITATION.cff`. |
| **IRB / ethics statement** | Not an Anthropic requirement, but reviewers handling a synthetic-EHR tool may ask. The repo already states source episodes are de-identified retrospective EHR. | Confirm in writing whether the underlying retrospective dataset was IRB-approved at Acibadem and whether that approval permits redistribution of trained copulas (not raw rows). This cannot be asserted on the maintainer's behalf. |
| **Claude Team or Enterprise organization** | Per Anthropic docs, required for the remote-connector portal. Plan-tier requirements for the MCPB / desktop-extension form are not publicly clarified. | If pursuing the MCPB path only, likely NOT needed — but verify with `mcp-review@anthropic.com` before subscribing. |
| **Hosted HTTPS endpoint + OAuth 2.0** | Only required for the Streamable HTTP / SSE submission path. | NOT NEEDED for the MCPB submission. Skip unless we pivot to the remote-connector path. |
| **Domain ownership proof** | Anthropic verifies domain ownership for remote connectors only. | Not needed for MCPB. If pursuing the remote path, maintainer / Acibadem must control a domain and pass DNS verification. |
| **Code signing for `.mcpb` / `.dxt`** | Not publicly required by Anthropic for directory acceptance. The repo's `WINDOWS_SIGNING.md` indicates interest in Authenticode for the bundled binary, useful for desktop trust prompts but not a documented submission requirement. | Verify with Anthropic. If later required, maintainer / Acibadem must provide an Authenticode certificate (paid, requires institutional identity verification). |

### Packaging the bundle

```bash
pip install dxt
cd mcp/
dxt pack .   # produces syntha-0.5.10.mcpb
```

Submit the resulting `.mcpb` file (or the public repo URL) via the form linked from <https://claude.com/connectors>. Optional secondary listings: Smithery and mcp.so both accept the same `syntha-mcp` console-script entry point.

Submission status will be tracked in [ROADMAP.md](../ROADMAP.md).

## Safety

- **No PHI ever returned.** The bundled JSONs contain only marginal quantiles and a correlation matrix — they cannot reconstruct any real patient's row.
- **Privacy audit.** Every release runs the Stadler 2022 nearest-synthetic-neighbor MIA in CI (gate AUROC ≤ 0.60). See `.github/workflows/privacy-audit.yml`.
- **Output caps.** `generate_cohort_csv` caps at 10,000 rows; `generate_cohort_fhir` at 500 bundles — keeps tool-result payloads within typical client size limits.
- **No write side-effects.** The MCP server never writes to disk; all output goes back through the tool-result channel.

## Implementation

- `src/syntha/mcp_server.py` — FastMCP-based server (stdio + Streamable HTTP).
- `src/syntha/bundled_models/{tolerant,strict}.json` — packaged via `[tool.setuptools.package-data]` so `pip install syntha-ehr` ships them.
- `src/syntha/export_model.py:load_generator_from_json` — reconstructs a `GaussianCopulaGenerator` directly from a v2 JSON, no registry required.
- `tests/test_mcp_server.py` — 12 tests covering tool registration, defaults, and end-to-end invocation.
