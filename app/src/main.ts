import {
  applyPhysiologicConstraints,
  INT_CAST_COLUMNS,
  sample,
  toCsv,
  type CopulaModel,
  type SampleResult,
} from "./copula";

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
  setStatus(`Sampling ${p.n.toLocaleString()} episodes from ${p.cohort} cohort (n_train = ${model.n_train.toLocaleString()})…`);

  // Oversample to make up for constraint rejection.
  const target = p.n;
  const factor = p.applyConstraints ? 1.5 : 1.0;
  let result = sample(model, {
    n: Math.ceil(target * factor),
    seed: p.seed,
    applyMissingness: p.applyMissingness,
  });
  if (p.applyConstraints) {
    result = applyPhysiologicConstraints(result);
    if (result.rows.length < target) {
      const extra = sample(model, {
        n: Math.ceil((target - result.rows.length) * 2),
        seed: p.seed + 1,
        applyMissingness: p.applyMissingness,
      });
      const more = applyPhysiologicConstraints(extra);
      result = { columns: result.columns, rows: result.rows.concat(more.rows) };
    }
  }
  result = { columns: result.columns, rows: result.rows.slice(0, target) };
  setStatus(`✓ Generated ${result.rows.length.toLocaleString()} rows from ${p.cohort} cohort.`, "success");
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

function renderPreview(result: SampleResult) {
  const card = el<HTMLElement>("preview-card");
  const container = el<HTMLDivElement>("preview");
  const previewCols = [
    "HASTA_ID", "age", "gender_is_male",
    "bp_systolic", "bp_diastolic",
    "glucose_fasting_latest", "hdl_latest", "ldl_direct_latest",
    "hemoglobin_latest", "egfr_latest",
    "Hipertansiyon", "DM_Tum", "Hiperlipidemi",
  ];
  // HASTA_ID isn't in model columns; generate one on the fly for preview.
  const colIdx = previewCols.map((c) => ({ c, i: result.columns.indexOf(c) }));
  const head = "<thead><tr>" + previewCols.map((c) => `<th>${c}</th>`).join("") + "</tr></thead>";
  const body = result.rows.slice(0, 10).map((row, r) => {
    const cells = colIdx.map(({ c, i }) => {
      if (c === "HASTA_ID") return `<td>SYN_${(r + 1).toString().padStart(6, "0")}</td>`;
      const v = i >= 0 ? row[i] : null;
      if (v === null || v === undefined) return "<td><span class='muted'>—</span></td>";
      const cast = INT_CAST_COLUMNS.has(c) ? Math.round(v as number) : (v as number);
      return `<td>${typeof cast === "number" && !Number.isInteger(cast) ? cast.toFixed(2) : cast}</td>`;
    });
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

setStatus("Idle. Pick a cohort and parameters, then click Generate.");
