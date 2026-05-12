"""Minimal in-memory FHIR R4 read-only server.

Boots a stdlib http.server that loads a transaction-Bundle NDJSON file and
serves the contained resources at canonical FHIR REST endpoints. Enough for
demos, ETL integration tests, and prototyping FHIR consumers — **not** a
compliant production FHIR server (no writes, no search parameters beyond
``_id``, no _include, no terminology validation).

Endpoints
---------
GET /metadata                   → CapabilityStatement
GET /<ResourceType>             → searchset Bundle of all resources of that type
GET /<ResourceType>/{id}        → single resource
GET /<ResourceType>?_id=<id>    → searchset Bundle with one or zero entries
GET /$export                    → original transaction-Bundle NDJSON
                                  (FHIR Bulk Data Access "Export" style)
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SUPPORTED_RESOURCES = (
    "Patient", "Observation", "Condition", "Encounter",
    "MedicationRequest", "Procedure", "CarePlan", "Bundle",
)


def _load_bundles(path: str | Path) -> list[dict]:
    bundles: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            bundles.append(json.loads(line))
    return bundles


def _index(bundles: Iterable[dict]) -> dict[str, dict[str, dict]]:
    """Flat index resource_type → {id → resource}."""
    idx: dict[str, dict[str, dict]] = {t: {} for t in SUPPORTED_RESOURCES}
    for bundle in bundles:
        idx["Bundle"][bundle["id"]] = bundle
        for entry in bundle.get("entry", []):
            r = entry.get("resource", {})
            t = r.get("resourceType")
            if t in idx and "id" in r:
                idx[t][r["id"]] = r
    return idx


def _searchset(resources: list[dict]) -> dict:
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(resources),
        "entry": [{"resource": r} for r in resources],
    }


def _capability_statement(base: str, counts: dict[str, int]) -> dict:
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "kind": "instance",
        "fhirVersion": "4.0.1",
        "format": ["application/fhir+json"],
        "software": {"name": "syntha", "version": "0.3.0"},
        "implementation": {"description": "syntha read-only demo FHIR server", "url": base},
        "rest": [{
            "mode": "server",
            "resource": [
                {
                    "type": t,
                    "interaction": [{"code": "read"}, {"code": "search-type"}],
                    "searchParam": [{"name": "_id", "type": "token"}],
                    "documentation": f"{counts.get(t, 0)} {t} resources loaded",
                }
                for t in SUPPORTED_RESOURCES
            ],
            "operation": [{"name": "export", "definition": "OperationDefinition/Bundle-export"}],
        }],
    }


class _Handler(BaseHTTPRequestHandler):
    server_version = "syntha-fhir/0.3"

    # Injected by `serve()` below.
    INDEX: dict[str, dict[str, dict]] = {}
    BUNDLES_PATH: Path = Path()

    def _send_json(self, status: int, payload) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/fhir+json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _operation_outcome(self, status: int, diagnostics: str) -> None:
        self._send_json(status, {
            "resourceType": "OperationOutcome",
            "issue": [{"severity": "error", "code": "not-found", "diagnostics": diagnostics}],
        })

    def log_message(self, fmt, *args):  # quieter access log
        pass

    def do_GET(self):  # noqa: N802
        url = urlparse(self.path)
        path_parts = [p for p in url.path.split("/") if p]
        query = parse_qs(url.query)
        base = f"http://{self.headers.get('Host', 'localhost')}"

        if not path_parts:
            return self._send_json(200, {
                "resourceType": "Parameters",
                "parameter": [{
                    "name": "message",
                    "valueString": "syntha FHIR demo server — try GET /metadata or GET /Patient",
                }],
            })

        if path_parts == ["metadata"]:
            counts = {t: len(self.INDEX.get(t, {})) for t in SUPPORTED_RESOURCES}
            return self._send_json(200, _capability_statement(base, counts))

        if path_parts == ["$export"]:
            try:
                data = self.BUNDLES_PATH.read_bytes()
            except OSError as e:
                return self._operation_outcome(500, str(e))
            self.send_response(200)
            self.send_header("Content-Type", "application/fhir+ndjson")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        rtype = path_parts[0]
        if rtype not in SUPPORTED_RESOURCES:
            return self._operation_outcome(404, f"Resource type {rtype} not supported")
        store = self.INDEX[rtype]

        # /Patient/{id}
        if len(path_parts) == 2:
            res = store.get(path_parts[1])
            if not res:
                return self._operation_outcome(404, f"{rtype}/{path_parts[1]} not found")
            return self._send_json(200, res)

        # /Patient and /Patient?_id=...
        if len(path_parts) == 1:
            ids = query.get("_id")
            results = (
                [store[i] for i in ids if i in store] if ids else list(store.values())
            )
            return self._send_json(200, _searchset(results))

        return self._operation_outcome(404, f"Unsupported path {url.path}")


def serve(bundles_ndjson: str | Path, host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    """Boot the server. Returns the server instance — caller is responsible
    for calling ``serve_forever()`` or ``shutdown()``."""
    bundles_path = Path(bundles_ndjson)
    bundles = _load_bundles(bundles_path)
    _Handler.INDEX = _index(bundles)
    _Handler.BUNDLES_PATH = bundles_path
    return ThreadingHTTPServer((host, port), _Handler)


def serve_forever(bundles_ndjson: str | Path, host: str = "127.0.0.1", port: int = 8080) -> None:
    srv = serve(bundles_ndjson, host, port)
    print(f"syntha FHIR demo server listening on http://{host}:{port}")
    print(f"  loaded {sum(len(s) for s in _Handler.INDEX.values())} resources from {bundles_ndjson}")
    print("  try GET /metadata, /Patient, /Observation?_id=<uuid>, /$export")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
