// Prevents opening an extra console window on Windows in release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        // The updater plugin lets the JS side call `check()` to look for a
        // new release and `downloadAndInstall()` to apply it. The plugin
        // verifies every downloaded artifact against the minisign public
        // key embedded in tauri.conf.json -> plugins.updater.pubkey.
        .plugin(tauri_plugin_updater::Builder::new().build())
        // process::restart() is used after the updater has installed.
        .plugin(tauri_plugin_process::init())
        .run(tauri::generate_context!())
        .expect("error while running syntha tauri application");
}
