// Collaborate panel — surfaces GitHub Issues labeled help-wanted-clinician /
// help-wanted-dev / help-wanted-data inside the desktop app, and lets the
// user "claim" one with their GitHub handle. No backend of our own — GitHub
// IS the collaboration platform. We use the unauthenticated REST API
// (60 req/h per IP, plenty for our use) and cache the result locally so
// the panel stays functional offline.

import { t } from "./i18n";

const REPO_OWNER = "ArioMoniri";
const REPO_NAME = "syntha";

const HANDLE_STORAGE_KEY = "syntha.collab.handle";
const CACHE_STORAGE_KEY = "syntha.collab.cache.v1";
const CACHE_TTL_MS = 15 * 60 * 1000; // 15 min — cheap to over-fetch the unauth API

export type CollabCategory = "clinician" | "dev" | "data";

export interface CollabIssue {
  number: number;
  title: string;
  url: string;
  body: string;
  category: CollabCategory;
  labels: string[];
  updated_at: string;
  author: string;
}

interface CacheEntry {
  fetched_at: number;
  issues: CollabIssue[];
}

interface GhLabel { name: string; }
interface GhUser  { login: string; }
interface GhIssue {
  number: number;
  title: string;
  html_url: string;
  body: string | null;
  labels: GhLabel[];
  updated_at: string;
  user: GhUser | null;
  pull_request?: unknown; // filter these out
}

function categoryOf(labels: string[]): CollabCategory | null {
  if (labels.includes("help-wanted-clinician")) return "clinician";
  if (labels.includes("help-wanted-dev"))       return "dev";
  if (labels.includes("help-wanted-data"))      return "data";
  return null;
}

export async function fetchHelpWantedIssues(force = false): Promise<{
  issues: CollabIssue[];
  fromCache: boolean;
  fetchedAt: Date;
  error?: string;
}> {
  const now = Date.now();
  if (!force) {
    try {
      const raw = localStorage.getItem(CACHE_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as CacheEntry;
        if (now - parsed.fetched_at < CACHE_TTL_MS) {
          return { issues: parsed.issues, fromCache: true, fetchedAt: new Date(parsed.fetched_at) };
        }
      }
    } catch { /* fall through */ }
  }

  const labels = ["help-wanted-clinician", "help-wanted-dev", "help-wanted-data"];
  const url = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/issues`
    + `?state=open&labels=${labels.join(",")}&per_page=50`;

  try {
    const r = await fetch(url, { headers: { Accept: "application/vnd.github+json" } });
    if (!r.ok) {
      // On rate-limit or network error, fall back to whatever cache we have.
      const cached = readCacheUnchecked();
      return {
        issues: cached?.issues ?? [],
        fromCache: !!cached,
        fetchedAt: cached ? new Date(cached.fetched_at) : new Date(),
        error: `GitHub API ${r.status}`,
      };
    }
    // The labels= filter is **AND**-semantics on github.com, so we need to
    // query each label separately to get the union.
    const all: GhIssue[] = [];
    const seen = new Set<number>();
    for (const lbl of labels) {
      const r2 = await fetch(
        `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/issues`
          + `?state=open&labels=${lbl}&per_page=50`,
        { headers: { Accept: "application/vnd.github+json" } },
      );
      if (!r2.ok) continue;
      const batch = (await r2.json()) as GhIssue[];
      for (const it of batch) {
        if (it.pull_request) continue;          // skip PRs
        if (seen.has(it.number)) continue;
        seen.add(it.number);
        all.push(it);
      }
    }

    const issues: CollabIssue[] = all.map((i) => {
      const labelNames = i.labels.map((l) => l.name);
      const cat = categoryOf(labelNames);
      return {
        number: i.number,
        title: i.title,
        url: i.html_url,
        body: (i.body ?? "").slice(0, 600),
        category: cat ?? "dev",
        labels: labelNames,
        updated_at: i.updated_at,
        author: i.user?.login ?? "unknown",
      };
    }).filter((i) => categoryOf(i.labels) !== null);

    issues.sort((a, b) => b.updated_at.localeCompare(a.updated_at));
    const entry: CacheEntry = { fetched_at: now, issues };
    try { localStorage.setItem(CACHE_STORAGE_KEY, JSON.stringify(entry)); } catch { /* ignore */ }
    return { issues, fromCache: false, fetchedAt: new Date(now) };
  } catch (e) {
    const cached = readCacheUnchecked();
    return {
      issues: cached?.issues ?? [],
      fromCache: !!cached,
      fetchedAt: cached ? new Date(cached.fetched_at) : new Date(),
      error: (e as Error).message,
    };
  }
}

function readCacheUnchecked(): CacheEntry | null {
  try {
    const raw = localStorage.getItem(CACHE_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as CacheEntry) : null;
  } catch {
    return null;
  }
}

// ── Handle persistence ───────────────────────────────────────────
export function loadHandle(): string {
  try {
    return localStorage.getItem(HANDLE_STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

export function saveHandle(handle: string): void {
  const cleaned = handle.trim().replace(/^@+/, "");
  try { localStorage.setItem(HANDLE_STORAGE_KEY, cleaned); } catch { /* ignore */ }
}

// ── Claim flow ────────────────────────────────────────────────────
// Build a deep-link to the issue with a pre-filled claim comment in the
// `body` query parameter. GitHub doesn't natively support that for issue
// comments, so we drop the user on the issue page with the comment text
// copied to their clipboard *and* navigate to a `#issuecomment-new` anchor.
export function claimLink(issue: CollabIssue): string {
  // GitHub doesn't expose a stable deep-link for "scroll to the new-comment
  // textarea on an existing issue", so we just open the issue itself. The
  // claim flow in main.ts copies the pre-filled comment to the clipboard.
  return `${issue.url}#issuecomment-new`;
}

export function claimCommentText(_issue: CollabIssue, handle: string): string {
  const h = handle ? `@${handle.replace(/^@+/, "")}` : "(your GitHub handle)";
  return [
    `${h} is claiming this — ETA <when>.`,
    "",
    "I read the task. I'll follow CONTRIBUTING.md and COLLABORATE.md and open a draft PR linked to this issue.",
    "",
    "_Claimed via the syntha desktop app._",
  ].join("\n");
}

// ── HTML rendering ────────────────────────────────────────────────
function badgeFor(cat: CollabCategory): string {
  const map: Record<CollabCategory, { color: string; label: string }> = {
    clinician: { color: "#8b5cf6", label: t("collab_badge_clinician") },
    dev:       { color: "#16a34a", label: t("collab_badge_dev") },
    data:      { color: "#2563eb", label: t("collab_badge_data") },
  };
  const { color, label } = map[cat];
  return `<span class="collab-badge" style="background:${color}">${label}</span>`;
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"]/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] as string
  ));
}

export function renderCollabList(
  container: HTMLElement,
  issues: CollabIssue[],
  fromCache: boolean,
  fetchedAt: Date,
  error: string | undefined,
): void {
  if (issues.length === 0) {
    container.innerHTML = `
      <p class="muted">${t("collab_empty")}</p>
      <p class="muted">${error ? escapeHtml(error) : ""}</p>
      <p><a href="https://github.com/${REPO_OWNER}/${REPO_NAME}/labels/help-wanted-clinician" target="_blank" rel="noopener">${t("collab_browse_github")}</a></p>
    `;
    return;
  }

  const items = issues.map((i) => `
    <article class="collab-card" data-issue="${i.number}">
      <header>
        ${badgeFor(i.category)}
        <a class="collab-title" href="${escapeHtml(i.url)}" target="_blank" rel="noopener">#${i.number} — ${escapeHtml(i.title)}</a>
      </header>
      <p class="collab-body">${escapeHtml(i.body || t("collab_no_body"))}</p>
      <footer>
        <span class="muted">${t("collab_opened_by")} <code>@${escapeHtml(i.author)}</code> · ${new Date(i.updated_at).toLocaleDateString()}</span>
        <button class="collab-claim" data-issue="${i.number}">${t("collab_btn_claim")}</button>
      </footer>
    </article>
  `).join("");

  const banner = fromCache
    ? `<p class="muted">${t("collab_offline")} ${fetchedAt.toLocaleString()}</p>`
    : `<p class="muted">${t("collab_fresh")} ${fetchedAt.toLocaleTimeString()}</p>`;

  container.innerHTML = `${banner}<div class="collab-grid">${items}</div>`;
}
