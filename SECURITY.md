# Security Policy

## Supported versions

| Version line | Supported |
|---|---|
| 0.5.x | ✅ |
| < 0.5 | ❌ (please upgrade) |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security reports.** Instead:

1. Open a **private GitHub Security Advisory** at
   https://github.com/ArioMoniri/syntha/security/advisories — this is the
   preferred channel.
2. Or open a public issue tagged `security` *only* if the vulnerability is
   already public.

We will acknowledge within 5 working days and aim to ship a fix within 30
days of acknowledgement, faster for high-severity issues.

## Scope

In scope:

- Code execution / data-exfiltration vulnerabilities in the `syntha-ehr`
  package or the `syntha-mcp` connector.
- Privacy regressions — anything that allows reconstructing a row of the
  source EHR from the bundled model summaries (the Stadler 2022 NN-MIA gate
  is the empirical defence; an MIA AUROC > 0.60 result on the released model
  is in scope).
- Supply-chain risks in the published PyPI / Docker / DMG / EXE / AppImage
  artifacts.

Out of scope:

- Bugs that affect only research-grade output quality (open a normal issue).
- Vulnerabilities in your own deployment of `syntha-mcp --transport http`
  if you have failed to terminate TLS, restrict access, or otherwise harden
  the endpoint. The connector ships with no built-in authentication; it is
  your responsibility to gate the HTTP endpoint.
- Anything in third-party dependencies; please report those upstream and
  CC us.

## Privacy gate

Every tagged release runs the Stadler 2022 nearest-synthetic-neighbor MIA
in CI (`.github/workflows/privacy-audit.yml`); the build fails at AUROC
> 0.60. If a release ships with a passing CI gate but you can demonstrate
a higher AUROC against the bundled model, that is a privacy regression and
should be reported via the channels above.

## Coordinated disclosure

We follow a 90-day coordinated-disclosure window from the date of
acknowledgement, extensible by mutual agreement.
