# Submitting `syntha` to the Anthropic Connector Directory

This document walks you (Ariorad Moniri, signed in as your **Anthropic Organization** account) through every step from "git tag" to "live in the connector directory at claude.com/connectors".

> Note on uncertainty: Anthropic's connector-submission UI may have moved or
> been renamed since this document was written (effective 2026-06-28). If a
> specific URL below 404s, navigate from <https://www.claude.com/connectors>
> and look for **"Submit a connector"** / **"Become a partner"** /
> **"Developer"**. The substance below is stable even if the routing isn't.

---

## Prerequisites (one-time setup)

### 1. Anthropic Organization account

You said you want to submit via your **company / Organization** account. Make sure that account exists and you're an Owner or Admin on it:

1. Go to <https://console.anthropic.com> and sign in.
2. **Settings → Organization** — confirm the org exists with the right legal name (recommended: "Acibadem University School of Medicine" or whatever entity is authorised to publish on the institution's behalf; double-check with your institution before listing them).
3. Confirm you have the **Owner** role on that organization (you'll need it to accept marketplace terms).
4. **Billing tab** — confirm there's at least a payment method on file. The connector directory itself does not charge a listing fee for Apache 2.0 OSS connectors (verify at submission time), but Anthropic gates organization features on a populated billing profile.

### 2. Claude account for testing

Also sign in to <https://claude.com> with the same identity, or with a personal account that's a member of the organization. You'll use this to **install and test** the `.dxt` from Claude Desktop before submitting it.

### 3. Local tools

```bash
# Node.js + npx (you already have it).
node --version    # any recent LTS
npx --version

# Claude Desktop installed: https://claude.ai/download
# Python 3.10+ with syntha-ehr[mcp] installable.
python3 --version

# Make sure git remotes are clean and main is in sync.
cd /Users/ario/Downloads/syntha
git status
git pull --rebase origin main
```

---

## Step 1 — Lock the release tag

The connector directory expects a stable, versioned submission. Use the most recent tag (or cut a new one if there are unreleased changes on `main`).

```bash
cd /Users/ario/Downloads/syntha

# What tag is current?
git describe --tags --abbrev=0          # → expected: v0.5.x

# If you have unmerged work that should ship with this listing, cut a new
# release through release-please (already wired): merge release-please PR #N,
# then push the tag.

# Verify the bundled model JSONs are inside the Python package:
ls src/syntha/bundled_models/
# should show: strict.json  tolerant.json
```

If something's missing, fix it first — the listing is hard to update post-submission.

## Step 2 — Build the `.dxt`

Anthropic's official packaging tool is **`@anthropic-ai/dxt`** on npm (the DXT format is documented at <https://github.com/anthropics/dxt>).

```bash
cd /Users/ario/Downloads/syntha/mcp

# Validate the manifest against the schema:
npx @anthropic-ai/dxt validate manifest.json

# Pack into syntha-<version>.dxt (output goes to ./):
npx @anthropic-ai/dxt pack .
ls -lh *.dxt
```

You should see a file named something like `syntha-0.5.10.dxt` (a few hundred KB — most of it is the two bundled cohort JSONs).

If `@anthropic-ai/dxt` isn't yet a public npm package, the equivalent manual build is documented in `mcp/build.sh` (it's just a `zip` of `manifest.json` + the Python entry-point + bundled assets).

## Step 3 — Install the `.dxt` locally in Claude Desktop and test it

Anthropic's reviewer will install your DXT and try the sample prompts. You should reproduce that exactly before submitting.

1. Open **Claude Desktop**.
2. **Settings → Extensions** (or **Developer → Install Extension** depending on Claude Desktop version).
3. **Install from file → choose `mcp/syntha-0.5.10.dxt`**.
4. The first install will prompt you to allow the connector. Accept.
5. Open a new chat and run each sample prompt from `mcp/LISTING.md` section "Sample prompts":
   - "Using the syntha connector, give me 50 synthetic patients aged 60+ with hypertension and diabetes, as a CSV."
   - "Generate 10 FHIR R4 bundles from syntha's tolerant cohort and show me the LOINC codes in the first bundle."
   - "What's the prevalence of thyroid disorders in syntha's tolerant cohort? Then sample 20 patients with that condition."
6. Each should return real synthetic output. If any tool errors, **stop here** — fix the bug, rebuild, re-test. Submitting broken tools means a rejection cycle.

## Step 4 — Push the `.dxt` as a GitHub Release asset

Public, immutable URL is required by some marketplace forms.

```bash
cd /Users/ario/Downloads/syntha
gh release upload v0.5.10 mcp/syntha-0.5.10.dxt --clobber
# Then verify:
gh release view v0.5.10 --json assets -q '.assets[] | .name'
# should now list syntha-0.5.10.dxt alongside the .dmg / .exe / .AppImage
```

(The CI workflow at `.github/workflows/dxt.yml` does this automatically on every tag push — see Appendix A below.)

## Step 5 — Submit through claude.com/connectors

Navigate to <https://www.claude.com/connectors> while signed in with your organization account.

Look for one of:

- **"Submit a connector"** button on the directory page;
- **"Become a partner"** / **"Apply for the Anthropic Partner program"** link in the footer of the directory page;
- **"Developer → Connector submission"** under your organization settings;
- A direct form at <https://www.claude.com/connectors/submit> (URL may have moved — start from the directory page).

When you reach the submission form, the fields it will ask for are pre-written in **`mcp/LISTING.md`**:

| Form field | Paste from LISTING.md section |
|---|---|
| Display name | "Display name" |
| Tagline (≤ 80 chars) | "One-line tagline" |
| Short description (≤ 200 chars) | "Short description" |
| Long description (≈ 800 chars) | "Long description" |
| Tags / keywords | "Tags / keywords" |
| Category | "Category" (Healthcare & Life Sciences) |
| Tools list (one row per tool) | "Tool list" table |
| Sample prompts (≥ 3) | "Sample prompts" |
| Screenshots (≥ 1) | Upload the three PNGs under `docs/figures/` |
| Author name | Ariorad Moniri |
| Author affiliation | Acibadem University School of Medicine, Istanbul, Turkey |
| Author email | (your preferred public contact — defaults to `moniriario@gmail.com`) |
| Author ORCID | 0000-0002-5171-3532 |
| Homepage URL | https://github.com/ArioMoniri/syntha |
| Documentation URL | https://github.com/ArioMoniri/syntha/blob/main/docs/MCP.md |
| Source repository | https://github.com/ArioMoniri/syntha |
| License | Apache-2.0 |
| Privacy policy URL | https://github.com/ArioMoniri/syntha/blob/main/PRIVACY.md |
| Terms of use URL | https://github.com/ArioMoniri/syntha/blob/main/TERMS.md |
| Security policy URL | https://github.com/ArioMoniri/syntha/blob/main/SECURITY.md |
| Support URL | https://github.com/ArioMoniri/syntha/issues |
| Pricing | Free (Apache-2.0 OSS) |
| DXT asset | Upload `syntha-0.5.10.dxt` *or* paste the GitHub release URL |
| Compatibility | macOS · Windows · Linux · Python ≥ 3.10 |

Read every TOS / partner-agreement clickwrap **before** accepting. Items to particularly verify:

- **Trademark grant** — confirm "syntha" is OK to use (no existing trademark conflict on PyPI / npm in your jurisdiction).
- **Data-handling clauses** — Anthropic may ask you to confirm that the connector does not call out to a service you operate. The PRIVACY.md statement is the authoritative answer; tell them "no, fully local, no outbound calls".
- **Liability cap / indemnity** — typical of marketplace TOS; consult institutional legal if your university requires it.

## Step 6 — During review

Anthropic's typical review process for OSS connectors involves:

1. **Automated check** — manifest schema validation, signature check, virus scan of the DXT.
2. **Human review** — a reviewer installs the DXT in a sandboxed Claude Desktop and runs the sample prompts.
3. **Privacy / safety review** — they'll read PRIVACY.md, look at the privacy-audit workflow, and confirm no PHI exfiltration risk.
4. **Listing copy review** — they'll edit your description for tone / Anthropic style if needed and may ask you to adjust.

You'll be notified through the submission portal and via the email associated with the organization account. Expected turnaround per Anthropic's documented partner process is **5-15 business days** for first review.

If they request changes:

- Update the relevant file(s) in the repo;
- Bump the version (`release-please` PR → merge → tag);
- Rebuild the DXT and re-upload via the submission portal's "Update submission" button (don't open a new submission).

## Step 7 — Post-listing

Once live:

1. Add a "Listed on the Anthropic Connector directory" badge to README.
2. Tag a new release with a `featured: true` flag in the manifest if Anthropic promotes you to Featured.
3. Subsequent updates ship by uploading a new DXT version through the same portal.

---

## Appendix A — CI auto-build of the `.dxt`

`.github/workflows/dxt.yml` (added in this branch) runs on every `v*` tag push and:

1. Installs `@anthropic-ai/dxt` from npm;
2. Runs `dxt validate mcp/manifest.json` (build fails on schema errors);
3. Runs `dxt pack mcp/` → `syntha-<tag>.dxt`;
4. Uploads the file as a GitHub Release asset alongside the existing `.dmg` / `.exe` / `.AppImage` / `latest.json`.

So after the next tag, you can pull the DXT directly from
`https://github.com/ArioMoniri/syntha/releases/latest/download/syntha.dxt`
without rebuilding locally.

## Appendix B — Alternative path: Streamable HTTP custom connector

If you want syntha available to **Claude.com web** users (not just Claude Desktop), publish a hosted HTTP endpoint:

```bash
# On any always-on host (Fly.io free tier, Render, Railway, your own VM):
pip install "syntha-ehr[mcp]"
syntha-mcp --transport http --host 0.0.0.0 --port 8765
# Terminate TLS in front (Caddy / Cloudflare Tunnel / nginx).
```

Then users add the URL to *claude.com → Settings → Connectors → Add custom connector*. This path **does not require Anthropic's review** — anyone with the URL can self-add it. The directory submission and the custom-connector URL are independent; you can do either, both, or neither.

## Appendix C — What you legally need from your institution

If you list the connector under "Acibadem University School of Medicine":

- Confirm with your department head that you have permission to publish under the institution's name.
- The institutional letterhead is not required by Anthropic, but **is** required by KVKK / institutional policy in Türkiye if the listing implies institutional endorsement.
- If unsure, list yourself personally as the author and put the affiliation in a sub-line: "Ariorad Moniri (Acibadem University School of Medicine — affiliation, not endorsement)".

This is a *you decide* item — neither the connector nor this guide imposes it.

## Appendix D — Roll-back

If a published listing version has a problem:

1. **Yank the listing** via the submission portal's "Withdraw" action (does not delete; sets the listing to "unlisted").
2. Ship a fix on `main`, tag a patch release.
3. Upload the new DXT and request re-review.

---

## Checklist (print this section)

Before submitting:

- [ ] Anthropic Organization account exists, you are Owner/Admin
- [ ] All tests pass on `main` (`pytest -q` returns 100% green)
- [ ] Latest release tag exists with all expected assets (`.dmg`, `.exe`, `.AppImage`, `.dxt`)
- [ ] `mcp/manifest.json` validates with `npx @anthropic-ai/dxt validate`
- [ ] DXT installs cleanly in Claude Desktop and all sample prompts return synthetic output
- [ ] `PRIVACY.md`, `TERMS.md`, `SECURITY.md` exist at the repo root and have non-stale effective dates
- [ ] `docs/MCP.md` lists every tool the manifest claims
- [ ] You've decided on the institutional affiliation text
- [ ] You've read the Anthropic Partner / Developer TOS

After submitting:

- [ ] You received a submission confirmation email
- [ ] Submission ID is recorded in this repo (open an internal-tracking issue if helpful)
- [ ] You're monitoring the email associated with the organization account for reviewer questions
