// Updater integration — Tauri 2 plugin-updater wrapper.
//
// On startup we silently `check()` once (network round-trip to the
// updater endpoint configured in tauri.conf.json). If a new version is
// available we surface a banner the user can click to download +
// install. A manual "Check for updates" button in the footer triggers
// the same flow on demand.
//
// All artifacts are verified against the minisign public key embedded
// in tauri.conf.json before the installer is run.

let plugin: typeof import("@tauri-apps/plugin-updater") | null = null;
let processPlugin: typeof import("@tauri-apps/plugin-process") | null = null;

async function loadPlugins() {
  if (plugin && processPlugin) return { plugin, processPlugin };
  try {
    plugin = await import("@tauri-apps/plugin-updater");
    processPlugin = await import("@tauri-apps/plugin-process");
    return { plugin, processPlugin };
  } catch {
    // Running in the Vite dev server (no Tauri runtime) — silently skip.
    return null;
  }
}

function setBanner(html: string, kind: "info" | "success" | "error" = "info"): void {
  let el = document.getElementById("update-banner");
  if (!el) {
    el = document.createElement("div");
    el.id = "update-banner";
    document.body.insertBefore(el, document.body.firstChild);
  }
  el.className = `update-banner update-banner--${kind}`;
  el.innerHTML = html;
}

function clearBanner(): void {
  document.getElementById("update-banner")?.remove();
}

export interface UpdateInfo {
  version: string;
  notes: string | null;
}

async function offerInstall(info: UpdateInfo, plugins: NonNullable<Awaited<ReturnType<typeof loadPlugins>>>): Promise<void> {
  const safeNotes = (info.notes || "").replace(/[<>&]/g, (c) =>
    ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" } as Record<string, string>)[c] || c,
  );
  setBanner(
    `<div class="update-banner__row">
       <div>
         <strong>Update available — v${info.version}</strong>
         <div class="update-banner__notes">${safeNotes.slice(0, 280)}${safeNotes.length > 280 ? "…" : ""}</div>
       </div>
       <div class="update-banner__actions">
         <button id="update-install" class="primary">Install &amp; restart</button>
         <button id="update-dismiss">Later</button>
       </div>
     </div>`,
    "info",
  );
  document.getElementById("update-dismiss")?.addEventListener("click", clearBanner);
  document.getElementById("update-install")?.addEventListener("click", async () => {
    const btn = document.getElementById("update-install") as HTMLButtonElement | null;
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Downloading…";
    }
    try {
      // Re-fetch the update object so we can call its install method.
      const upd = await plugins.plugin.check();
      if (!upd) {
        setBanner("No update available anymore.", "info");
        return;
      }
      let downloaded = 0;
      await upd.downloadAndInstall((progress) => {
        if (progress.event === "Started" && btn) {
          const total = progress.data.contentLength ?? 0;
          btn.textContent = `Downloading 0 / ${(total / 1_048_576).toFixed(1)} MB…`;
        } else if (progress.event === "Progress" && btn) {
          downloaded += progress.data.chunkLength;
          btn.textContent = `Downloading ${(downloaded / 1_048_576).toFixed(1)} MB…`;
        } else if (progress.event === "Finished" && btn) {
          btn.textContent = "Installing…";
        }
      });
      await plugins.processPlugin.relaunch();
    } catch (e) {
      setBanner(`Update failed: ${(e as Error).message}`, "error");
    }
  });
}

/** Background check on app launch. Silent if no update or running in dev. */
export async function checkOnStartup(): Promise<void> {
  const plugins = await loadPlugins();
  if (!plugins) return;
  try {
    const upd = await plugins.plugin.check();
    if (upd) await offerInstall({ version: upd.version, notes: upd.body ?? null }, plugins);
  } catch {
    // Network failure / no updater endpoint reachable — fail silent.
  }
}

/** Triggered by the "Check for updates" footer button. */
export async function checkOnDemand(): Promise<void> {
  const plugins = await loadPlugins();
  if (!plugins) {
    setBanner("Updater is only available in the installed desktop app.", "info");
    return;
  }
  setBanner("Checking for updates…", "info");
  try {
    const upd = await plugins.plugin.check();
    if (!upd) {
      setBanner("✓ You're on the latest version.", "success");
      setTimeout(clearBanner, 3000);
      return;
    }
    await offerInstall({ version: upd.version, notes: upd.body ?? null }, plugins);
  } catch (e) {
    setBanner(`Could not check: ${(e as Error).message}`, "error");
  }
}
