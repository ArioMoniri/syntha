// Gaussian copula sampler in TypeScript — matches src/syntha/generator/copula.py.
// Steps:
//   1. Draw z ~ N(0, Σ) using Cholesky factor of the model correlation matrix.
//   2. Map to uniforms via the standard normal CDF, u = Φ(z).
//   3. Invert each marginal:
//        - binary  : x = 1 iff u ≥ 1 − p   (latent-threshold form, v0.3.2 fix)
//        - continuous: x = empirical-quantile-inverse(u) by linear interpolation
//   4. Apply per-column missingness as independent Bernoulli(p_missing).

export interface CopulaModel {
  // "syntha-copula-v1" (legacy) or "syntha-copula-v2" (current).
  format: string;
  cohort: string;
  columns: string[];
  binary_cols: string[];
  p_missing: Record<string, number>;
  binary_p: Record<string, number>;
  continuous_quantiles: Record<string, number[]>;
  correlation: number[][];
  n_train: number;
  // v2 additions — optional so v1 bundles still load.
  date_lo?: string; // ISO-8601 (YYYY-MM-DD) start of the source date window
  date_hi?: string; // ISO-8601 end of the source date window
  curation_columns?: string[]; // cohort/NLP metadata to drop from default CSV
}

// Fallback used when a v1 bundle is loaded (no date_lo / date_hi present).
// Three-year window ending today — keeps episode_date sensible without the
// source CSV.
function defaultDateWindow(): { lo: string; hi: string } {
  const now = new Date();
  const hi = now.toISOString().slice(0, 10);
  const past = new Date(now);
  past.setFullYear(now.getFullYear() - 3);
  const lo = past.toISOString().slice(0, 10);
  return { lo, hi };
}

// Default curation-column set for v1 bundles that don't ship the list.
// Mirrors src/syntha/schema.py:CURATION_COLUMNS — single source of truth on
// the Python side; this is the JS-side fallback.
const DEFAULT_CURATION_COLUMNS: string[] = [
  "pristine_strict", "pristine_tolerant",
  "tier_healthy_episode", "tier_healthy_patient",
  "is_cancer", "is_ex", "is_cancer_or_ex",
  "drug_safe", "has_rx_data", "has_blacklist_drug",
  "polypharmacy_flag", "high_risk_drug_flag",
  "max_ilac_onem", "mean_ilac_onem",
  "rule_clean", "keyword_clean", "berturk_clean", "berturk_similarity",
  "text_available", "nlp_filter_pass", "keyword_total_flags",
  "has_nontolerable_icd_30d", "any_worsening",
  "rf_kanser", "rf_kronik_hastalik", "rf_akut_ciddi",
  "rf_psikiyatri_ciddi", "rf_ilac_risk_metin", "rf_fonksiyon_kaybi",
];

export function curationColumns(model: CopulaModel): string[] {
  return model.curation_columns && model.curation_columns.length > 0
    ? model.curation_columns
    : DEFAULT_CURATION_COLUMNS;
}

// ── PRNG ──────────────────────────────────────────────────────────
// xoshiro128** — fast, well-tested, seedable. Returns uniform on [0,1).
export function makeRng(seed: number): () => number {
  let s0 = Math.imul(seed, 0x9e3779b9) >>> 0;
  let s1 = (s0 ^ 0x6a09e667) >>> 0;
  let s2 = (s1 ^ 0xbb67ae85) >>> 0;
  let s3 = (s2 ^ 0x3c6ef372) >>> 0;
  return () => {
    const result = (Math.imul((s1 + s3) | 0, 5) << 7) | 0;
    const r = Math.imul(result, 9) >>> 0;
    const t = s1 << 9;
    s2 ^= s0;
    s3 ^= s1;
    s1 ^= s2;
    s0 ^= s3;
    s2 ^= t;
    s3 = ((s3 << 11) | (s3 >>> 21)) >>> 0;
    return r / 4294967296;
  };
}

// Box–Muller transform: two uniforms → two standard normals.
export function randn(rng: () => number): number {
  // Avoid log(0).
  let u1 = rng();
  while (u1 === 0) u1 = rng();
  const u2 = rng();
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}

// ── Standard normal CDF (Abramowitz & Stegun 7.1.26) ─────────────
export function normCdf(x: number): number {
  // Φ(x) = ½ (1 + erf(x / √2))
  const sign = x < 0 ? -1 : 1;
  const ax = Math.abs(x) / Math.SQRT2;
  const t = 1 / (1 + 0.3275911 * ax);
  const y =
    1 -
    (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t +
      0.254829592) *
      t *
      Math.exp(-ax * ax);
  return 0.5 * (1 + sign * y);
}

// ── Cholesky decomposition (in-place lower triangular) ──────────
// Returns L such that L L^T = A. Assumes A is symmetric positive-definite.
export function cholesky(A: number[][]): number[][] {
  const n = A.length;
  const L: number[][] = Array.from({ length: n }, () => new Array<number>(n).fill(0));
  for (let i = 0; i < n; i++) {
    for (let j = 0; j <= i; j++) {
      let sum = A[i][j];
      for (let k = 0; k < j; k++) sum -= L[i][k] * L[j][k];
      if (i === j) {
        if (sum <= 0) sum = 1e-10; // jitter for near-PSD matrices
        L[i][j] = Math.sqrt(sum);
      } else {
        L[i][j] = sum / L[j][j];
      }
    }
  }
  return L;
}

// ── Empirical quantile inverse by linear interpolation ──────────
export function quantileInverse(sorted: number[], u: number): number {
  const m = sorted.length;
  if (m === 0) return 0;
  if (m === 1) return sorted[0];
  const idx = u * (m - 1);
  const lo = Math.floor(idx);
  const hi = Math.min(lo + 1, m - 1);
  const frac = idx - lo;
  return sorted[lo] * (1 - frac) + sorted[hi] * frac;
}

// ── Main sampling routine ───────────────────────────────────────
export interface SampleOptions {
  n: number;
  seed: number;
  applyMissingness: boolean;
}

// Row cells can be:
//   - number  → continuous / count / binary columns from the copula
//   - string  → identifier columns (HASTA_ID, episode_date)
//   - null    → missing
// The CSV writer handles all three; the model sampler itself only emits
// number | null. String cells appear after addIdentifiers / longitudinal
// expansion runs.
export interface SampleResult {
  columns: string[];
  rows: (number | string | null)[][];
}

export function sample(model: CopulaModel, opts: SampleOptions): SampleResult {
  // v2 is current; v1 still loads (the missing fields fall back to defaults
  // in defaultDateWindow / DEFAULT_CURATION_COLUMNS).
  if (model.format !== "syntha-copula-v1" && model.format !== "syntha-copula-v2") {
    throw new Error(`unknown model format: ${model.format}`);
  }
  const { n, seed, applyMissingness } = opts;
  const rng = makeRng(seed);
  const k = model.columns.length;
  const L = cholesky(model.correlation);
  const binarySet = new Set(model.binary_cols);

  const rows: (number | null)[][] = [];
  for (let r = 0; r < n; r++) {
    // standard-normal vector z₀ then z = L z₀
    const z0 = new Array<number>(k);
    for (let i = 0; i < k; i++) z0[i] = randn(rng);
    const z = new Array<number>(k);
    for (let i = 0; i < k; i++) {
      let s = 0;
      for (let j = 0; j <= i; j++) s += L[i][j] * z0[j];
      z[i] = s;
    }
    const row: (number | null)[] = new Array(k);
    for (let i = 0; i < k; i++) {
      const col = model.columns[i];
      const u = normCdf(z[i]);
      if (binarySet.has(col)) {
        const p = model.binary_p[col] ?? 0;
        row[i] = u >= 1 - p ? 1 : 0;
      } else {
        const q = model.continuous_quantiles[col];
        row[i] = q ? quantileInverse(q, u) : null;
      }
    }
    if (applyMissingness) {
      for (let i = 0; i < k; i++) {
        const pm = model.p_missing[model.columns[i]] ?? 0;
        if (pm > 0 && rng() < pm) row[i] = null;
      }
    }
    rows.push(row);
  }
  return { columns: [...model.columns], rows };
}

// ── Physiologic constraint filter (mirrors Python implementation) ──
export function applyPhysiologicConstraints(s: SampleResult): SampleResult {
  const idx = (c: string) => s.columns.indexOf(c);
  const sys = idx("bp_systolic");
  const dia = idx("bp_diastolic");
  const chol = idx("cholesterol_total_latest");
  const hdl = idx("hdl_latest");
  const ldl = idx("ldl_direct_latest");
  const tg = idx("triglycerides_latest");
  const egfr = idx("egfr_latest");
  const cre = idx("creatinine_latest");

  const keep: (number | string | null)[][] = [];
  for (const row of s.rows) {
    let ok = true;
    if (sys >= 0 && dia >= 0 && row[sys] != null && row[dia] != null) {
      if ((row[sys] as number) - (row[dia] as number) < 20) ok = false;
    }
    if (ok && chol >= 0 && hdl >= 0 && ldl >= 0 && tg >= 0
        && row[chol] != null && row[hdl] != null && row[ldl] != null && row[tg] != null) {
      const expected = (row[hdl] as number) + (row[ldl] as number) + (row[tg] as number) / 5;
      if (Math.abs((row[chol] as number) - expected) > 40) ok = false;
    }
    if (ok && egfr >= 0 && cre >= 0 && row[egfr] != null && row[cre] != null) {
      if ((row[cre] as number) > 2.0 && (row[egfr] as number) > 90) ok = false;
    }
    if (ok) keep.push(row);
  }
  return { columns: s.columns, rows: keep };
}

// ── Serialize to CSV ─────────────────────────────────────────────
export function toCsv(s: SampleResult, intCastCols: Set<string>): string {
  const parts: string[] = [s.columns.join(",")];
  for (const row of s.rows) {
    const cells = row.map((v, i) => {
      if (v === null || v === undefined) return "";
      // ID/date columns arrive as strings (HASTA_ID, episode_date).
      // Pass through verbatim — quoted if they contain a comma.
      if (typeof v === "string") {
        return v.includes(",") ? `"${v.replace(/"/g, '""')}"` : v;
      }
      const n = v as number;
      if (Number.isNaN(n)) return "";
      if (intCastCols.has(s.columns[i])) return String(Math.round(n));
      return Number.isInteger(n) ? String(n) : n.toFixed(4).replace(/\.?0+$/, "");
    });
    parts.push(cells.join(","));
  }
  return parts.join("\n") + "\n";
}

export const INT_CAST_COLUMNS = new Set([
  "age", "n_drugs", "n_medications", "drug_class_count",
  "charlson_cci", "comorbidity_count", "n_ep_labs_available_x",
  "keyword_total_flags", "platelets_latest",
]);

// ── Identifier columns (synthesized — never modeled) ─────────────
// Matches src/syntha/schema.py:ID_COLUMNS and pipeline._generate_ids_and_dates.
export const ID_COLUMNS = ["RF_EPISODE2", "HASTA_ID", "episode_date"] as const;

// 8-hex-char patient ID compatible with the Python side:
//   f"SYN_{uuid.uuid4().hex[:8].upper()}"
function makePatientId(rng: () => number): string {
  let s = "";
  for (let i = 0; i < 8; i++) {
    const nibble = Math.floor(rng() * 16);
    s += nibble.toString(16).toUpperCase();
  }
  return `SYN_${s}`;
}

function makeEpisodeId(rng: () => number): number {
  // 8-digit integer, matches Python's rng.integers(10_000_000, 99_999_999).
  return 10_000_000 + Math.floor(rng() * 90_000_000);
}

function randomDateBetween(lo: Date, hi: Date, rng: () => number): Date {
  const span = hi.getTime() - lo.getTime();
  return new Date(lo.getTime() + rng() * Math.max(span, 1));
}

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/** Prepend RF_EPISODE2, HASTA_ID, episode_date to every row.
 *  Mirrors pipeline._generate_ids_and_dates() on the Python side. */
export function addIdentifiers(
  s: SampleResult,
  model: CopulaModel,
  seed: number,
): SampleResult {
  const win = (model.date_lo && model.date_hi)
    ? { lo: model.date_lo, hi: model.date_hi }
    : defaultDateWindow();
  const lo = new Date(win.lo + "T00:00:00Z");
  const hi = new Date(win.hi + "T23:59:59Z");
  const rng = makeRng(seed);

  const newCols = [...ID_COLUMNS, ...s.columns];
  const newRows: (number | string | null)[][] = s.rows.map((row) => {
    const ids: (number | string)[] = [
      makeEpisodeId(rng),
      makePatientId(rng),
      isoDate(randomDateBetween(lo, hi, rng)),
    ];
    return [...ids, ...row];
  });
  return { columns: newCols, rows: newRows };
}

/** Drop curation-flag columns from a SampleResult.
 *  Returns a new SampleResult with surviving columns + rows. */
export function dropCurationFlags(
  s: SampleResult,
  curation: string[],
): SampleResult {
  const dropSet = new Set(curation);
  const keepIdx: number[] = [];
  const keepCols: string[] = [];
  for (let i = 0; i < s.columns.length; i++) {
    if (!dropSet.has(s.columns[i])) {
      keepIdx.push(i);
      keepCols.push(s.columns[i]);
    }
  }
  const rows = s.rows.map((row) => keepIdx.map((i) => row[i]));
  return { columns: keepCols, rows };
}

// ── Longitudinal trajectory expansion (TS port) ─────────────────
// Mirrors src/syntha/longitudinal.py:expand_to_trajectories.
// Each baseline becomes K episodes (K ~ Poisson(mean)). Comorbidity / flag
// columns are sticky across episodes; lab and vital values drift via
// independent multiplicative Gaussian noise around the baseline.
export interface TrajectoryOptions {
  encountersPerPatientMean: number; // Poisson mean
  yearsOfHistory: number;
  labDriftScale: number; // sd as fraction of baseline (≈0.05 = 5%)
  ageAdvance: boolean;
  seed: number;
}

// Mirrors schema.COMORBIDITY_COLUMNS + FLAG_COLUMNS (binary, "sticky").
const STICKY_COLUMNS = new Set<string>([
  // Comorbidities
  "Kanser", "Iskemik_Kalp", "Serebrovaskuler", "Kalp_Yetmezligi",
  "Pulmoner_Emboli", "Aort_Anevrizma", "Kronik_Bobrek", "Karaciger_Siroz",
  "Sepsis", "Atriyal_Fibrilasyon", "COPD", "DM_Komplikasyonlu", "DM_Tum",
  "Astim", "Hipertansiyon", "Hiperlipidemi", "Tiroid", "Obezite",
  "Depresyon", "Anksiyete",
  // Flags
  "pristine_strict", "pristine_tolerant", "tier_healthy_episode",
  "is_cancer", "is_ex", "is_cancer_or_ex", "drug_safe",
  "has_rx_data", "has_blacklist_drug", "rule_clean", "keyword_clean",
  "berturk_clean", "text_available", "nlp_filter_pass",
  "all_ep_labs_normal_x", "polypharmacy_flag", "high_risk_drug_flag",
  "has_nontolerable_icd_30d", "any_worsening",
  "rf_kanser", "rf_kronik_hastalik", "rf_akut_ciddi",
  "rf_psikiyatri_ciddi", "rf_ilac_risk_metin", "rf_fonksiyon_kaybi",
  "gender_is_male",
]);

// Lab + vital + count columns that drift episode-to-episode.
const DRIFT_COLUMNS = new Set<string>([
  "glucose_fasting_latest", "ldl_direct_latest", "hdl_latest",
  "cholesterol_total_latest", "triglycerides_latest", "egfr_latest",
  "creatinine_latest", "hemoglobin_latest", "wbc_latest", "platelets_latest",
  "alt_latest", "ast_latest", "ferritin_latest", "vitamin_b12_latest",
  "bp_systolic", "bp_diastolic",
  "n_drugs", "n_medications", "drug_class_count",
  "n_ep_labs_available_x", "lab_abnormal_pct",
]);

function poissonSample(rng: () => number, mean: number): number {
  // Knuth's algorithm — fine for the small means we use (≈4).
  const L = Math.exp(-mean);
  let k = 0;
  let p = 1;
  do {
    k += 1;
    p *= rng();
  } while (p > L);
  return Math.max(1, k - 1);
}

export function expandToTrajectories(
  baselines: SampleResult,
  model: CopulaModel,
  opts: TrajectoryOptions,
): SampleResult {
  const win = (model.date_lo && model.date_hi)
    ? { lo: model.date_lo, hi: model.date_hi }
    : defaultDateWindow();
  const dateLo = new Date(win.lo + "T00:00:00Z");
  const dateHi = new Date(win.hi + "T23:59:59Z");
  const windowMs = Math.max(dateHi.getTime() - dateLo.getTime(), 1);
  const spanMs = opts.yearsOfHistory * 365.25 * 86400 * 1000;
  const rng = makeRng(opts.seed);

  const idxOf = (c: string) => baselines.columns.indexOf(c);
  const ageIdx = idxOf("age");
  const episodeIdIdx = idxOf("RF_EPISODE2");
  const patientIdIdx = idxOf("HASTA_ID");
  const dateIdx = idxOf("episode_date");

  const out: (number | string | null)[][] = [];
  type Row = (number | string | null)[];
  for (const base of baselines.rows as Row[]) {
    const nEnc = poissonSample(rng, opts.encountersPerPatientMean);
    // Anchor uniformly inside the source window.
    const anchor = new Date(dateLo.getTime() + rng() * windowMs);
    // Encounter offsets within [0, yearsOfHistory] years, sorted ascending.
    const offsets = Array.from({ length: nEnc }, () => rng() * spanMs)
      .sort((a, b) => a - b);
    // Reuse one synthetic patient_id across all encounters for this person.
    const sharedPid = makePatientId(rng);

    for (const off of offsets) {
      const row: Row = [...base];
      const episodeDt = new Date(anchor.getTime() + off);
      if (episodeIdIdx >= 0) row[episodeIdIdx] = makeEpisodeId(rng);
      if (patientIdIdx >= 0) row[patientIdIdx] = sharedPid;
      if (dateIdx >= 0) row[dateIdx] = isoDate(episodeDt);
      // Drift continuous columns; keep sticky columns as-is.
      for (let i = 0; i < baselines.columns.length; i++) {
        const col = baselines.columns[i];
        if (STICKY_COLUMNS.has(col)) continue;
        if (!DRIFT_COLUMNS.has(col)) continue;
        const v = row[i];
        if (v === null || v === undefined || Number.isNaN(v as number)) continue;
        const drift = 1 + randn(rng) * opts.labDriftScale;
        row[i] = (v as number) * drift;
      }
      if (opts.ageAdvance && ageIdx >= 0) {
        const v = row[ageIdx];
        if (v !== null && v !== undefined && !Number.isNaN(v as number)) {
          const deltaYears = off / (365.25 * 86400 * 1000);
          row[ageIdx] = Math.round((v as number) + deltaYears);
        }
      }
      out.push(row);
    }
  }
  return { columns: baselines.columns, rows: out };
}
