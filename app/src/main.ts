import {
  addIdentifiers,
  applyPhysiologicConstraints,
  curationColumns,
  dropCurationFlags,
  expandToTrajectories,
  ID_COLUMNS,
  INT_CAST_COLUMNS,
  sample,
  toCsv,
  type CopulaModel,
  type SampleResult,
} from "./copula";
import { initI18n, t } from "./i18n";
import { checkOnDemand, checkOnStartup } from "./updater";

// Lazy-load the bundled model for the chosen cohort.
async function loadModel(cohort: "tolerant" | "strict"): Promise<CopulaModel> {
  const url = cohort === "strict"
    ? new URL("./model_strict.json", import.meta.url)
    : new URL("./model_tolerant.json", import.meta.url);
  const r = await fetch(url.toString());
  if (!r.ok) throw new Error(`model fetch failed: ${r.status}`);
  return (await r.json()) as CopulaModel;
}

function el<T extends HTMLElement>(id: string): T {
  const e = document.getElementById(id);
  if (!e) throw new Error(`missing element #${id}`);
  return e as T;
}

function setStatus(msg: string, kind: "info" | "success" | "error" = "info") {
  const s = el<HTMLParagraphElement>("status");
  s.textContent = msg;
  s.className = "status " + (kind === "info" ? "muted" : kind);
}

function readParams() {
  const cohort = (document.querySelector<HTMLInputElement>(
    "input[name=cohort]:checked",
  )?.value ?? "tolerant") as "tolerant" | "strict";
  return {
    cohort,
    n: Math.max(1, Math.min(1_000_000, parseInt(el<HTMLInputElement>("n").value || "1000"))),
    seed: parseInt(el<HTMLInputElement>("seed").value || "42") | 0,
    applyConstraints: el<HTMLInputElement>("apply-constraints").checked,
    applyMissingness: el<HTMLInputElement>("include-missingness").checked,
    clinicalOnly: el<HTMLInputElement>("clinical-only").checked,
    longitudinal: el<HTMLInputElement>("longitudinal").checked,
    encountersPerPatient: Math.max(1, parseFloat(
      el<HTMLInputElement>("encounters-per-patient").value || "4",
    )),
    yearsOfHistory: Math.max(0.25, parseFloat(
      el<HTMLInputElement>("years-of-history").value || "3",
    )),
  };
}

async function generate(): Promise<SampleResult | null> {
  const p = readParams();
  setStatus(`Loading ${p.cohort} model…`);
  let model: CopulaModel;
  try {
    model = await loadModel(p.cohort);
  } catch (e) {
    setStatus(`Could not load model: ${(e as Error).message}. Did you run scripts/refresh_app_model.sh?`, "error");
    return null;
  }

  // In longitudinal mode `n` is the target *total encounter* count; we draw
  // fewer baselines and expand each into ~encountersPerPatient encounters.
  const targetEncounters = p.n;
  const baselineTarget = p.longitudinal
    ? Math.max(1, Math.round(targetEncounters / p.encountersPerPatient))
    : targetEncounters;

  setStatus(
    p.longitudinal
      ? `Sampling ~${baselineTarget.toLocaleString()} baselines × ~${p.encountersPerPatient.toFixed(1)} encounters from ${p.cohort} cohort (n_train = ${model.n_train.toLocaleString()})…`
      : `Sampling ${p.n.toLocaleString()} episodes from ${p.cohort} cohort (n_train = ${model.n_train.toLocaleString()})…`,
  );

  // 1) Copula sample → physiologic constraint filter (oversample to recover).
  const factor = p.applyConstraints ? 1.5 : 1.0;
  let baselines = sample(model, {
    n: Math.ceil(baselineTarget * factor),
    seed: p.seed,
    applyMissingness: p.applyMissingness,
  });
  if (p.applyConstraints) {
    baselines = applyPhysiologicConstraints(baselines);
    if (baselines.rows.length < baselineTarget) {
      const extra = sample(model, {
        n: Math.ceil((baselineTarget - baselines.rows.length) * 2),
        seed: p.seed + 1,
        applyMissingness: p.applyMissingness,
      });
      const more = applyPhysiologicConstraints(extra);
      baselines = { columns: baselines.columns, rows: baselines.rows.concat(more.rows) };
    }
  }
  baselines = { columns: baselines.columns, rows: baselines.rows.slice(0, baselineTarget) };

  // 2) Synthesize identifiers (RF_EPISODE2, HASTA_ID, episode_date).
  baselines = addIdentifiers(baselines, model, p.seed + 2);

  // 3) Longitudinal expansion (one row per encounter).
  let result: SampleResult;
  if (p.longitudinal) {
    result = expandToTrajectories(baselines, model, {
      encountersPerPatientMean: p.encountersPerPatient,
      yearsOfHistory: p.yearsOfHistory,
      labDriftScale: 0.05,
      ageAdvance: true,
      seed: p.seed + 3,
    });
    if (p.applyConstraints) result = applyPhysiologicConstraints(result);
    // Trim to the user's target encounter count (Poisson can overshoot).
    result = { columns: result.columns, rows: result.rows.slice(0, targetEncounters) };
  } else {
    result = baselines;
  }

  // 4) Drop curation-flag columns from the CSV/preview output by default.
  if (p.clinicalOnly) {
    result = dropCurationFlags(result, curationColumns(model));
  }

  const status = p.longitudinal
    ? `✓ Generated ${result.rows.length.toLocaleString()} encounters across ~${baselineTarget.toLocaleString()} patients (${p.cohort}).`
    : `✓ Generated ${result.rows.length.toLocaleString()} rows from ${p.cohort} cohort.`;
  setStatus(status, "success");
  return result;
}

function downloadCsv(result: SampleResult, cohort: string) {
  const csv = toCsv(result, INT_CAST_COLUMNS);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  a.href = url;
  a.download = `syntha_${cohort}_${result.rows.length}_${ts}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

const ID_COLUMN_SET = new Set<string>(ID_COLUMNS);

function formatCell(col: string, v: number | string | null | undefined): string {
  if (v === null || v === undefined) {
    return "<td><span class='muted'>—</span></td>";
  }
  if (typeof v === "string") {
    return `<td>${escapeHtml(v)}</td>`;
  }
  if (Number.isNaN(v)) {
    return "<td><span class='muted'>—</span></td>";
  }
  if (INT_CAST_COLUMNS.has(col) || ID_COLUMN_SET.has(col)) {
    return `<td>${Math.round(v)}</td>`;
  }
  return `<td>${Number.isInteger(v) ? v : v.toFixed(2)}</td>`;
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"]/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] as string
  ));
}

function renderPreview(result: SampleResult) {
  const card = el<HTMLElement>("preview-card");
  const container = el<HTMLDivElement>("preview");
  const cols = result.columns;
  const head = "<thead><tr>" + cols.map((c) => `<th>${escapeHtml(c)}</th>`).join("") + "</tr></thead>";
  const body = result.rows.slice(0, 50).map((row) => {
    const cells = cols.map((c, i) => formatCell(c, row[i]));
    return "<tr>" + cells.join("") + "</tr>";
  }).join("");
  container.innerHTML = `<table>${head}<tbody>${body}</tbody></table>`;
  card.hidden = false;
}

el<HTMLButtonElement>("generate").addEventListener("click", async () => {
  el<HTMLButtonElement>("generate").disabled = true;
  el<HTMLButtonElement>("preview-btn").disabled = true;
  try {
    const result = await generate();
    if (result && result.rows.length > 0) {
      downloadCsv(result, readParams().cohort);
    }
  } finally {
    el<HTMLButtonElement>("generate").disabled = false;
    el<HTMLButtonElement>("preview-btn").disabled = false;
  }
});

el<HTMLButtonElement>("preview-btn").addEventListener("click", async () => {
  el<HTMLButtonElement>("generate").disabled = true;
  el<HTMLButtonElement>("preview-btn").disabled = true;
  try {
    const result = await generate();
    if (result && result.rows.length > 0) renderPreview(result);
  } finally {
    el<HTMLButtonElement>("generate").disabled = false;
    el<HTMLButtonElement>("preview-btn").disabled = false;
  }
});

// Toggle visibility of the longitudinal sub-parameters when the checkbox flips.
const longitudinalToggle = el<HTMLInputElement>("longitudinal");
const longitudinalParams = el<HTMLDivElement>("longitudinal-params");
function refreshLongitudinalParamsVisibility() {
  longitudinalParams.hidden = !longitudinalToggle.checked;
}
longitudinalToggle.addEventListener("change", refreshLongitudinalParamsVisibility);
refreshLongitudinalParamsVisibility();

// Initialize i18n before any user-facing strings are emitted. Sets
// document.documentElement.lang + walks [data-i18n-key] and substitutes
// translations for the detected locale (tr if browser locale starts with
// 'tr', else en). Saved preference in localStorage["syntha.locale"]
// overrides detection.
initI18n();

setStatus(t("status_idle"));

// Updater: silent check on launch + wire the footer button.
checkOnStartup();
document.getElementById("check-updates")?.addEventListener("click", checkOnDemand);
