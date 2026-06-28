# syntha MCP Connector — Terms of Use

**Effective date:** 2026-06-28
**Maintainer:** Ariorad Moniri (Acibadem University School of Medicine, Istanbul, Turkey)
**License:** Apache-2.0 (see [LICENSE](LICENSE))

These terms govern use of the `syntha` Model Context Protocol (MCP) connector and the `syntha-ehr` Python package. They are intentionally short and defer to the Apache 2.0 license for substantive terms.

## 1. License

The connector and all source code are licensed under the **Apache License, Version 2.0** (see [LICENSE](LICENSE)). By using the connector, you accept the Apache 2.0 terms — including the patent grant, the redistribution requirements, and the disclaimer of warranties in Section 7.

## 2. Synthetic data, not medical advice

All output is **synthetic and computer-generated**. The connector does not provide medical advice, diagnosis, or treatment. Outputs **must not** be used as a substitute for the clinical judgment of a qualified healthcare professional, or for any direct patient-care decision.

## 3. Calibration required before deployment

Synthetic disease prevalences in the bundled cohorts are systematically lower than national population figures by construction (the source was data-quality-curated to clinically-pristine episodes). Risk-prediction models trained on synthetic data from this connector **must** be recalibrated against population marginals (TÜİK, TURDEP-II, etc.) before any downstream deployment. The user, not the maintainer, is responsible for downstream validation.

## 4. No warranty

The Apache 2.0 disclaimer applies in full: the connector is provided "AS IS", WITHOUT WARRANTY OF ANY KIND. See LICENSE Section 7.

## 5. Limitation of liability

The Apache 2.0 limitation of liability applies in full. See LICENSE Section 8.

## 6. Trademark notice

Per Apache 2.0 Section 6: these terms do not grant permission to use the name "syntha", the maintainer's name, or any associated marks except as required for reasonable and customary use in describing the origin of the work and reproducing the content of NOTICE files.

## 7. Third-party services

The connector itself makes no outbound network calls in normal operation. If you run it via Streamable-HTTP transport, **you** are responsible for the security and terms of whichever hosting/networking provider you use.

The connector is **not** a service operated by the maintainer. There is no service-level agreement, no uptime guarantee, and no commercial support obligation.

## 8. Acceptable use

You may not use the connector to:

- Generate output and pass it off as real patient data;
- Attempt to reverse-engineer any individual patient's identity from the bundled model summaries (this is empirically protected by the Stadler 2022 NN-MIA gate but you must not attempt it);
- Violate applicable healthcare-data, research-ethics, or data-protection law (including, where applicable, GDPR, HIPAA, KVKK, FDA/EMA/TİTCK regulations).

## 9. Reporting issues

Bugs: https://github.com/ArioMoniri/syntha/issues
Security: https://github.com/ArioMoniri/syntha/security/advisories

## 10. Changes

These terms are versioned in git. Material changes ship in a new release and update the effective date.
