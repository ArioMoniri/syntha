# 🪟 Windows Authenticode signing setup

Without an Authenticode-signed `.exe`, Windows SmartScreen shows end users a
"Microsoft Defender SmartScreen prevented an unrecognized app from starting"
dialog the first time they run the syntha installer. This document explains
how to get the signed-installer pipeline live.

## Why it's not automatic

Unlike macOS (where Apple issues Developer ID certificates to any
member of the $99/year Apple Developer Program) Windows requires a
code-signing certificate from a **commercial Certificate Authority** —
Sectigo, DigiCert, SSL.com, GlobalSign. Prices range roughly $200–700/year
for standard validation, $400–1500/year for EV (which gives instant
SmartScreen reputation, no warning even on first install).

There is no way to get a *trusted* Authenticode cert for free. The
hardware-token requirement for OV/EV certs as of June 2023 means you also
need either a USB token or an HSM-as-a-service subscription.

## The repo is already wired — you just add 2 secrets

The release workflow `.github/workflows/release.yml` has a
**conditional step** ("Import Windows code-signing certificate") that
fires only when `WINDOWS_CERTIFICATE` is set. The Tauri config at
`app/src-tauri/tauri.conf.json` already declares the `windows`
signing block (SHA-256 digest, Sectigo timestamp server).

Once you have a cert, do these one-time steps:

### 1. Export the certificate as a password-protected .pfx

If your CA delivered a `.cer` + private key in your local cert store:

```powershell
# In PowerShell, on the Windows machine where the cert was issued
$pwd = ConvertTo-SecureString -String "your-export-password" -Force -AsPlainText
Export-PfxCertificate `
    -Cert "Cert:\CurrentUser\My\<THUMBPRINT>" `
    -FilePath "$env:USERPROFILE\Desktop\syntha-codesign.pfx" `
    -Password $pwd
```

### 2. Base64-encode + push as GitHub secrets

```powershell
$bytes = [System.IO.File]::ReadAllBytes("$env:USERPROFILE\Desktop\syntha-codesign.pfx")
$b64 = [System.Convert]::ToBase64String($bytes)
Set-Clipboard -Value $b64
# (paste into GitHub repo settings → Secrets → New repository secret
# with name WINDOWS_CERTIFICATE)
```

Add:
- `WINDOWS_CERTIFICATE` ← the base64 string
- `WINDOWS_CERTIFICATE_PASSWORD` ← the password you used in step 1

### 3. Tag a new release

The next `v*` tag will pick up the secrets, import the .pfx into a fresh
keychain in `$RUNNER_TEMP`, sign the `.exe` with signtool through Tauri
2's bundle pipeline, timestamp via Sectigo, and ship the signed installer
to the release. End users no longer see SmartScreen.

## EV certs and the SmartScreen reputation curve

Standard (OV) certs **still trigger SmartScreen for the first ~3000
downloads** of a new app. After that threshold, SmartScreen learns the
publisher is legit and starts auto-approving. EV certs skip this curve
entirely — they're auto-trusted on day one. For a new project the cost
delta usually isn't worth it unless you expect heavy first-week downloads.

## Hardware token vs HSM-as-a-service

OV/EV certs issued after June 2023 require the private key live in a
hardware token (Yubikey FIPS, SafeNet, Sectigo USB) OR a cloud HSM
service like Azure Key Vault. The token approach **does not work with
GitHub Actions** — there's no USB on a cloud runner. You need an HSM
service. Sectigo's "Code Signing in the Cloud" + DigiCert KeyLocker
both work with GitHub Actions; they cost an extra ~$300/year on top of
the cert.

## Cheapest viable path (May 2026 prices)

1. SSL.com OV Code Signing: $129/year (3-year deal $389)
2. + SSL.com Cloud Signing: $99/year
3. Total: ~$228/year for everything

The repo's signing pipeline works with any of the above — once the .pfx
+ password land in the secrets, the next tag publishes a signed installer.
