# 🚀 syntha v0.4.2 — Tauri 2 auto-updater + signed & notarized macOS

This release closes the loop on desktop distribution:

- 🔄 **Auto-updater** — the app polls a signed `latest.json` manifest on launch, shows an in-app banner when a new version exists, and applies the update with one click. Every artifact is verified against a minisign public key embedded in the build.
- 🍎 **Signed + notarized macOS DMG** — Apple Developer ID signing, Hardened Runtime, `Entitlements.plist`, `notarytool` stapling. No more "syntha.app is damaged" Gatekeeper warning. (Pipeline stabilized in v0.4.1.)
- 🤖 **Three-OS release matrix** — macOS aarch64 / Windows x64 / Linux x86_64 all built, signed, attached.

This is the **first release where users on v0.4.x will be silently offered v0.4.x+1 going forward** — no need to re-download manually.

---

## 🆕 What's new since v0.4.0

### 🔄 Auto-updater (this release)

| Component | Detail |
|---|---|
| Minisign keypair | Private key in `TAURI_SIGNING_PRIVATE_KEY` secret · public key in `tauri.conf.json` |
| Rust plugins | `tauri-plugin-updater@2` + `tauri-plugin-process@2` |
| Endpoint | `https://github.com/ArioMoniri/syntha/releases/latest/download/latest.json` |
| TS module | [`app/src/updater.ts`](https://github.com/ArioMoniri/syntha/blob/v0.4.2/app/src/updater.ts) — silent startup check + footer "Check for updates" + in-page banner with download progress |
| Per-platform payload | `.app.tar.gz` (macOS) · `-setup.exe` (Windows) · `.AppImage` (Linux) — each with a separate `.sig` minisign signature |

How it works end-to-end on every release:
1. Each matrix job emits its installer + an extra `.tar.gz` (macOS) / signed `.exe` (Windows) / `.AppImage` (Linux), plus a minisign `.sig`
2. A new `manifest` job runs after the matrix; downloads each `.sig` from the just-uploaded release; assembles `latest.json` per the [Tauri updater static-JSON spec](https://v2.tauri.app/plugin/updater/#static-json-file); attaches it to the release
3. End-user installs poll that URL once on launch; if a newer `version` is present and the signature verifies, the in-app banner offers **Install & restart**

### 🍎 Signed + notarized macOS DMG (stabilized in v0.4.1)

```
Authority: Developer ID Application: Ariorad Moniri (FF68N39FU5)
Authority: Developer ID Certification Authority
Authority: Apple Root CA
Notarization Ticket = stapled
spctl --assess → accepted (source: Notarized Developer ID)
```

The macOS DMG installs without any Gatekeeper warning — no right-click bypass, no `xattr` workaround. Hardened Runtime is on with `Entitlements.plist` allowing only the entitlements WKWebView strictly needs (JIT + unsigned executable memory + user-selected file read/write).

---

## 📦 Downloads

| Platform | File | Size |
|---|---|---|
| 🍎 macOS Apple Silicon | [`syntha_aarch64.dmg`](https://github.com/ArioMoniri/syntha/releases/download/v0.4.2/syntha_aarch64.dmg) | 4.73 MB |
| 🪟 Windows x64 | [`syntha_x64-setup.exe`](https://github.com/ArioMoniri/syntha/releases/download/v0.4.2/syntha_x64-setup.exe) | 3.12 MB |
| 🐧 Linux x86_64 | [`syntha_amd64.AppImage`](https://github.com/ArioMoniri/syntha/releases/download/v0.4.2/syntha_amd64.AppImage) | 78.66 MB |

Plus updater payloads + minisign signatures + `latest.json` are attached for the auto-updater. End users do not need to download those manually.

```bash
# Quick verify of the latest.json manifest:
curl -sL https://github.com/ArioMoniri/syntha/releases/latest/download/latest.json | jq .version
# → "0.4.2"
```

---

## ⬆️ Upgrading

**From v0.4.1+ users**: launch the app — you'll see an "Update available — v0.4.2" banner in a moment. Click **Install & restart**. The app downloads the signed `.app.tar.gz` (~5 MB), verifies its minisign signature against the embedded pubkey, swaps the bundle, and relaunches. All in-app.

**From v0.4.0 users**: the v0.4.0 installer had no updater logic, so this one-time upgrade is manual. Download the macOS DMG and drag to Applications — it'll replace the older copy. From there onward the auto-updater takes over.

**Fresh installs**: just download from the install buttons in the [README](https://github.com/ArioMoniri/syntha#%EF%B8%8F-desktop-app--generate-synthetic-patients-without-code).

---

## 🛡️ Verification (paranoid mode)

If you want to validate the signatures locally:

```bash
# macOS — verify the signed DMG end-to-end
spctl --assess --type execute -v /Volumes/syntha/syntha.app
# → /Volumes/syntha/syntha.app: accepted
#   source=Notarized Developer ID

# Inspect the minisign manifest signatures
curl -sLO https://github.com/ArioMoniri/syntha/releases/download/v0.4.2/syntha_aarch64.app.tar.gz
curl -sLO https://github.com/ArioMoniri/syntha/releases/download/v0.4.2/syntha_aarch64.app.tar.gz.sig
# Verify with the public key from app/src-tauri/tauri.conf.json (plugins.updater.pubkey)
minisign -V -P RWThZvpQUNrVuRHflZG+WCI7ntPoRQ0GYB26T+iqTiSw8pKrcvIKKevt \
         -m syntha_aarch64.app.tar.gz -x syntha_aarch64.app.tar.gz.sig
```

---

## 🧠 What this release does *not* change

Everything below is byte-identical to v0.4.0/v0.4.1 — no behavioral changes to the science:

- 🧬 The **Gaussian copula** sampling code (with the v0.3.2 latent-threshold fix)
- 🩺 **9 Synthea-style clinical modules** (hypertension, diabetes, hyperlipidemia, thyroid, depression, anxiety, IHD, asthma, COPD)
- 📡 **FHIR R4 output** with dual SNOMED CT + ICD-10 Condition coding, LOINC labs, RxNorm meds
- 🇹🇷 **Turkish localization** — Patient.name + Address + `tr` communication
- 📦 **Bundled trained models** — same `app/src/model_{tolerant,strict}.json` (170 KB each, trained on the full 135 569 / 55 141 row source cohorts)
- 🧪 **37 Python tests** still passing on `ci.yml` matrix Py 3.10 → 3.13
- 💻 **`cross-platform.yml`** still smoke-tests the full Python pipeline + Tauri TS frontend build + `cargo check` on macOS / Windows / Linux

---

## 📜 Full changelog

| Tag | Highlight |
|---|---|
| **v0.4.2** ← this | Auto-updater + signed/notarized desktop pipeline stable |
| [v0.4.1](https://github.com/ArioMoniri/syntha/releases/tag/v0.4.1) | First Apple-Developer-ID-signed + notarized macOS DMG |
| [v0.4.0](https://github.com/ArioMoniri/syntha/releases/tag/v0.4.0) | First public release: Tauri desktop app + CI matrix + install buttons |

Detailed change log: [CHANGELOG.md](https://github.com/ArioMoniri/syntha/blob/v0.4.2/CHANGELOG.md)

---

## 🤝 Clinician curation

The v0.6 roadmap is still waiting on TR-specific first-line drug calibration, MAFLD/CKD/B12 modules, prevalence calibration to TÜİK, and ICD-10 specificity review.

Three ways to contribute (easiest first):
1. 💬 Reply to me in any chat session — paste guidance, code lands directly
2. 📝 [Open a Clinical curation issue](https://github.com/ArioMoniri/syntha/issues/new?template=clinical_curation.md&labels=clinical-curation&title=%5Bclinical-curation%5D%20) with the prefilled template
3. 🔧 Submit a PR — see [CONTRIBUTING.md](https://github.com/ArioMoniri/syntha/blob/v0.4.2/CONTRIBUTING.md)

📄 Apache 2.0 © 2026 **Ariorad Moniri**
