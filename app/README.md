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
