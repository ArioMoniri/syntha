# syntha as a Claude / MCP connector

`syntha-mcp` is a [Model Context Protocol](https://modelcontextprotocol.io) server that exposes syntha's synthetic-cohort generator as a set of tools any MCP-compatible client can call — Claude Desktop, the Claude.com custom-connector slot, [mcp-cli](https://github.com/modelcontextprotocol/mcp-cli), Cursor, Continue, and others.

No real patient data is ever returned. The server samples from the two compressed empirical-summary JSONs bundled with this package (`tolerant`, `strict`) — ≈200 quantiles per continuous column plus a correlation matrix, with no rows of the source EHR embedded.

## Install

```bash
pip install "syntha-ehr[mcp]"
```

This installs the [`mcp`](https://pypi.org/project/mcp) Python SDK alongside syntha and registers a `syntha-mcp` console script.

## Tools exposed (8)

| Tool | What it does |
|---|---|
| `syntha_version` | Library version + bundled-cohort fingerprints |
| `list_bundled_cohorts` | The cohorts shipped with the connector — `tolerant` (n_train ≈ 135,569) and `strict` (n_train ≈ 55,141) |
| `get_cohort_summary` | n_train, modeled columns, **comorbidity prevalences**, source date window |
| `generate_cohort_csv` | N synthetic patients as a CSV string; physiologic-validity filter on by default; curation flags dropped by default |
| `generate_cohort_fhir` | N synthetic patients as **FHIR R4** transaction-Bundle NDJSON, with the 9 Synthea-style clinical modules running |
| `sample_conditional` | AST-validated rejection sampling against a pandas-style filter expression — e.g. `"Hipertansiyon == 1 & age > 60 & bp_systolic >= 140"` |
| `list_clinical_modules` | The 9 modules and the source flag each one fires on |
| `list_physiologic_constraints` | The 3 + 1 validity rules (pulse pressure ≥ 20, Friedewald coherence, eGFR ↔ creatinine consistency, DBP ≤ SBP) |

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

## Submitting to the Claude Connector directory

Anthropic curates a directory at <https://www.claude.com/connectors> and an open ecosystem of [Desktop Extensions](https://github.com/anthropics/dxt) (`.dxt` packages).

1. **DXT package** — `mcp/manifest.json` in this repo follows the [dxt-manifest schema](https://json.schemastore.org/dxt-manifest.json). To produce a `.dxt` file ready for upload:
   ```bash
   pip install dxt
   cd mcp/
   dxt pack .   # produces syntha-0.5.9.dxt
   ```
2. **Claim the connector listing** — submit the `.dxt` file (or the public repo URL) via the form linked from <https://www.claude.com/connectors>.
3. **Smithery / mcp.so** — optional secondary listing on community registries; both accept the same Python entry point (`syntha-mcp` console script).

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
