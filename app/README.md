# syntha desktop app

A Tauri 2 desktop GUI that runs the syntha Gaussian copula sampler entirely client-side (TypeScript) and lets the user generate synthetic patient CSVs without installing Python.

## Architecture

```
┌──────────────┐    ┌────────────────────────────────────────────────┐
│ Rust backend │    │ TypeScript frontend                            │
│ (Tauri 2)    │◄──►│ • copula.ts — Gaussian copula sampler          │
│              │    │ • main.ts   — UI wiring, download              │
│ tiny shell   │    │ • model_{tolerant,strict}.json (~100 KB each)  │
└──────────────┘    └────────────────────────────────────────────────┘
```

The Rust side is intentionally minimal (just hosts the webview + dialog/fs plugins). All sampling math lives in TypeScript so the same code runs in dev (`vite`) and in the bundled installer.

## Refreshing the bundled model

The bundled `src/model_tolerant.json` and `src/model_strict.json` are exported from the Python side. Refresh them with:

```bash
bash ../scripts/refresh_app_model.sh
```

This runs the Python `syntha export-model` CLI against the fitted copulas in `output/` and writes the JSON files into `app/src/`.

## Local development

```bash
npm install
npm run tauri-dev      # opens the desktop window
```

## Building installers locally

```bash
npm install
npm run tauri-build
# artifacts land under src-tauri/target/release/bundle/
```

## CI release builds

`.github/workflows/release.yml` runs on `v*` tag pushes — builds `.dmg` (macOS aarch64), `-setup.exe` (Windows x64) and `.AppImage` (Linux x86_64), then uploads them to the release with these stable names:

- `syntha_aarch64.dmg`
- `syntha_x64-setup.exe`
- `syntha_amd64.AppImage`

That's what the install buttons in the top-level README link to.

## macOS code signing & notarization

Without signing, macOS shows the `"syntha.app" is damaged` error (Gatekeeper's misleading message for unsigned apps). The release workflow signs **and** notarizes the macOS DMG automatically — once these six GitHub repository secrets are set:

| Secret name | What it is | How to get it |
|---|---|---|
| `APPLE_CERTIFICATE` | Base64-encoded **Developer ID Application** `.p12` | `base64 -i Cert.p12 -o Cert.p12.b64 && pbcopy < Cert.p12.b64` |
| `APPLE_CERTIFICATE_PASSWORD` | The password you set during the `.p12` export | — |
| `APPLE_SIGNING_IDENTITY` | Full identity string, e.g. `Developer ID Application: Ariorad Moniri (FF68N39FU5)` | `security find-identity -v -p codesigning` after importing into Keychain |
| `APPLE_ID` | Your Apple ID **email** | — |
| `APPLE_PASSWORD` | App-specific password (NOT your Apple ID password) | https://appleid.apple.com → Sign-In and Security → App-Specific Passwords |
| `APPLE_TEAM_ID` | Your 10-character team identifier | https://developer.apple.com/account → Membership → Team ID |
| `KEYCHAIN_PASSWORD` | Any random string for the throwaway CI keychain | `openssl rand -base64 24` |

How the workflow uses them
- Imports the `.p12` into a fresh keychain in `$RUNNER_TEMP` (gone at job end).
- Sets `APPLE_*` env vars on the `tauri build` step; Tauri 2 then calls `codesign` with the hardened runtime + `Entitlements.plist`, runs `xcrun notarytool submit --wait`, and **staples** the notarization ticket to the resulting `.dmg`.

If any secret is absent the workflow skips signing — the build still succeeds, but the DMG ships unsigned and users will see the Gatekeeper "damaged" warning.

### Local user workaround for unsigned builds

Until signed installers are available, end users can run an unsigned `syntha.app` with one terminal command after dragging it to `/Applications/`:

```bash
xattr -dr com.apple.quarantine /Applications/syntha.app
open /Applications/syntha.app
```
