// Dashboard renderer. Pulls benchmark data from /benchmarks/*.json
// committed in the repo (proxied via the GH Pages static-asset path)
// and renders 4 Chart.js charts + a release-timeline table.

const BENCHMARKS_URL = "../../benchmarks/dashboard.json";

const CHART_OPTS = {
  responsive: true,
  plugins: {
    legend: { position: "bottom", labels: { padding: 12, boxWidth: 12 } },
    tooltip: { mode: "index", intersect: false },
  },
  scales: {
    y: { beginAtZero: true, grid: { color: "rgba(127,127,127,0.15)" } },
    x: { grid: { display: false } },
  },
};

function bar(canvasId, labels, datasets, yMax = 1.0, threshold = null) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const opts = JSON.parse(JSON.stringify(CHART_OPTS));
  opts.scales.y.max = yMax;
  if (threshold !== null) {
    opts.plugins.annotation = {
      annotations: {
        line1: {
          type: "line",
          yMin: threshold,
          yMax: threshold,
          borderColor: "#999",
          borderDash: [6, 4],
          borderWidth: 1,
        },
      },
    };
  }
  new Chart(ctx, { type: "bar", data: { labels, datasets }, options: opts });
}

async function load() {
  let data;
  try {
    const r = await fetch(BENCHMARKS_URL);
    data = await r.json();
  } catch {
    // Fall back to placeholder shape so the dashboard still renders
    // before the first benchmark run lands.
    data = {
      releases: [
        { version: "v0.4.2", date: "2026-05-13", scope: "Auto-updater, signed/notarized macOS", tests: 51 },
        { version: "v0.5.0-dev", date: "2026-05-13", scope: "Polyserial+tetrachoric, HTEST tag, DiagnosticReport panels", tests: 61 },
      ],
      ks: {
        // Mean + max KS per release across continuous columns.
        labels: ["v0.4.0", "v0.4.2", "v0.5.0-dev"],
        mean:   [0.07, 0.07, 0.07],
        max:    [0.14, 0.14, 0.14],
      },
      correlation_magnitude: {
        labels: ["cont↔cont", "cont↔binary", "binary↔binary"],
        v04: [0.99, 0.84, 0.39],
        v05: [0.99, 0.94, 0.90],
      },
      tstr: null,       // placeholder until v0.5.6
      privacy: null,    // placeholder until v0.5 G2
    };
  }

  // ─ KS chart
  bar("ks-chart",
    data.ks.labels,
    [
      { label: "mean KS", data: data.ks.mean, backgroundColor: "#2563eb" },
      { label: "max KS",  data: data.ks.max,  backgroundColor: "#93c5fd" },
    ],
    0.25,
    0.05,
  );

  // ─ Correlation magnitude
  bar("corr-chart",
    data.correlation_magnitude.labels,
    [
      { label: "v0.4 (Spearman pipeline)", data: data.correlation_magnitude.v04, backgroundColor: "#94a3b8" },
      { label: "v0.5 (polyserial+tetrachoric)", data: data.correlation_magnitude.v05, backgroundColor: "#16a34a" },
    ],
    1.0,
    0.9,
  );

  // ─ TSTR placeholder
  const tstrCtx = document.getElementById("tstr-chart");
  if (tstrCtx && !data.tstr) {
    tstrCtx.replaceWith(makePlaceholder("Pending v0.5.6 — SynthEHRella TSTR benchmark integration"));
  }

  // ─ Privacy placeholder
  const privCtx = document.getElementById("privacy-chart");
  if (privCtx && !data.privacy) {
    privCtx.replaceWith(makePlaceholder("Pending v0.5 G2 — membership + attribute inference CI"));
  }

  // ─ Release table
  const tbody = document.querySelector("#release-table tbody");
  if (tbody && data.releases) {
    tbody.innerHTML = data.releases
      .map((r) => `<tr>
        <td><code>${r.version}</code></td>
        <td>${r.date}</td>
        <td>${r.scope}</td>
        <td>${r.tests}</td>
      </tr>`)
      .join("");
  }
}

function makePlaceholder(message) {
  const div = document.createElement("div");
  div.className = "placeholder";
  div.style.cssText = "padding:48px; text-align:center; color:var(--muted); font-style:italic;";
  div.textContent = message;
  return div;
}

load();
