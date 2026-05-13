// Gaussian copula sampler in TypeScript — matches src/syntha/generator/copula.py.
// Steps:
//   1. Draw z ~ N(0, Σ) using Cholesky factor of the model correlation matrix.
//   2. Map to uniforms via the standard normal CDF, u = Φ(z).
//   3. Invert each marginal:
//        - binary  : x = 1 iff u ≥ 1 − p   (latent-threshold form, v0.3.2 fix)
//        - continuous: x = empirical-quantile-inverse(u) by linear interpolation
//   4. Apply per-column missingness as independent Bernoulli(p_missing).

export interface CopulaModel {
  format: string;
  cohort: string;
  columns: string[];
  binary_cols: string[];
  p_missing: Record<string, number>;
  binary_p: Record<string, number>;
  continuous_quantiles: Record<string, number[]>;
  correlation: number[][];
  n_train: number;
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

export interface SampleResult {
  columns: string[];
  rows: (number | null)[][];
}

export function sample(model: CopulaModel, opts: SampleOptions): SampleResult {
  if (model.format !== "syntha-copula-v1") {
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

  const keep: (number | null)[][] = [];
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
      if (v === null || v === undefined || Number.isNaN(v as number)) return "";
      if (intCastCols.has(s.columns[i])) return String(Math.round(v as number));
      const n = v as number;
      // Compact representation: integers as-is, floats with 4 decimals max.
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
