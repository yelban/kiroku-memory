// Kiroku Memory Desktop - Tauri v2
// Main entry point

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod config;
mod service;

use config::{keychain, keys, settings, AppSettings};
use serde::Deserialize;
use service::{check_health_once, wait_for_health, PythonService, ServiceStatus};
use std::fs::OpenOptions;
use std::io::Write;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, OnceLock};
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tauri::image::Image;
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{AppHandle, Emitter, Manager, State, Window};

/// Tauri command to get service status
#[tauri::command]
async fn get_service_status(
    service: State<'_, Arc<PythonService>>,
) -> Result<ServiceStatus, String> {
    Ok(service.get_status().await)
}

/// Tauri command to check health
#[tauri::command]
async fn check_health() -> Result<String, String> {
    match check_health_once().await {
        Some(health) => serde_json::to_string(&health).map_err(|e| e.to_string()),
        None => Err("Service not available".to_string()),
    }
}

/// Tauri command to get stats
#[tauri::command]
async fn get_stats() -> Result<String, String> {
    let client = reqwest::Client::new();
    match client.get("http://127.0.0.1:8000/v2/stats").send().await {
        Ok(resp) => {
            let text = resp.text().await.map_err(|e| e.to_string())?;
            Ok(text)
        }
        Err(e) => Err(format!("Service not available: {}", e)),
    }
}

/// Tauri command to restart service
#[tauri::command]
async fn restart_service(
    app: AppHandle,
    service: State<'_, Arc<PythonService>>,
) -> Result<(), String> {
    restart_service_and_wait(app, service.inner().clone()).await
}

/// Tauri command to stop service
#[tauri::command]
async fn stop_service(service: State<'_, Arc<PythonService>>) -> Result<(), String> {
    service.stop().await.map_err(|e| e.to_string())
}

async fn restart_service_and_wait(
    app: AppHandle,
    service: Arc<PythonService>,
) -> Result<(), String> {
    service.restart(&app).await.map_err(|e| e.to_string())?;

    match wait_for_health("http://127.0.0.1:8000/health", Duration::from_secs(30)).await {
        Ok(_) => {
            service.mark_running().await;
            app.emit("service-ready", ()).ok();
            Ok(())
        }
        Err(e) => {
            let error = e.to_string();
            service.mark_error(error.clone()).await;
            app.emit("service-error", &error).ok();
            Err(error)
        }
    }
}

// ============================================================================
// Config Commands
// ============================================================================

/// Tauri command to set OpenAI API key (stores in macOS Keychain)
#[tauri::command]
async fn set_openai_key(key: String) -> Result<(), String> {
    keychain::set_secret(keys::OPENAI_API_KEY, &key).map_err(|e| e.to_string())
}

/// Tauri command to check if OpenAI API key is set (doesn't expose the key)
#[tauri::command]
async fn has_openai_key() -> bool {
    keychain::has_secret(keys::OPENAI_API_KEY)
}

/// Tauri command to delete OpenAI API key
#[tauri::command]
async fn delete_openai_key() -> Result<(), String> {
    keychain::delete_secret(keys::OPENAI_API_KEY).map_err(|e| e.to_string())
}

/// Tauri command to get app settings
#[tauri::command]
async fn get_settings(app: AppHandle) -> Result<AppSettings, String> {
    settings::load(&app).map_err(|e| e.to_string())
}

/// Tauri command to save app settings
#[tauri::command]
async fn save_settings(app: AppHandle, new_settings: AppSettings) -> Result<(), String> {
    let current_settings = settings::load(&app).unwrap_or_default();
    if current_settings.launch_at_login != new_settings.launch_at_login {
        set_launch_at_login(&app, new_settings.launch_at_login)?;
    }
    settings::save(&app, &new_settings).map_err(|e| e.to_string())
}

/// Tauri command to get app data directory path
#[tauri::command]
async fn get_data_dir(app: AppHandle) -> Result<String, String> {
    app.path()
        .app_data_dir()
        .map(|p| p.to_string_lossy().to_string())
        .map_err(|e| e.to_string())
}

// ============================================================================
// Tray Helpers
// ============================================================================

const TRAY_ID: &str = "main";
const MENU_ID_STATUS: &str = "status";
const MENU_ID_TOGGLE_WINDOW: &str = "toggle_window";
const MENU_ID_RESTART_SERVICE: &str = "restart_service";
const MENU_ID_MEMORY_COUNT: &str = "memory_count";
const MENU_ID_QUIT: &str = "quit";
const TRAY_FALLBACK_TITLE: &str = "Kiroku";

const TRAY_ICON_PNG: &[u8] = include_bytes!("../icons/tray-icon.png");

type AppMenuItem = MenuItem<tauri::Wry>;

#[derive(Clone)]
struct TrayItems {
    status: AppMenuItem,
    toggle_window: AppMenuItem,
    restart_service: AppMenuItem,
    memory_count: AppMenuItem,
}

#[derive(Deserialize)]
struct StatsResponse {
    items: StatsItems,
}

#[derive(Deserialize)]
struct StatsItems {
    total: u64,
}

static LOG_PATH: OnceLock<PathBuf> = OnceLock::new();

fn build_tray_menu(app: &AppHandle) -> tauri::Result<(Menu<tauri::Wry>, TrayItems)> {
    let status_item = MenuItem::with_id(app, MENU_ID_STATUS, "Status: Starting", false, None::<&str>)?;
    let memory_count =
        MenuItem::with_id(app, MENU_ID_MEMORY_COUNT, "Memories: -", false, None::<&str>)?;
    let toggle_window = MenuItem::with_id(
        app,
        MENU_ID_TOGGLE_WINDOW,
        "Show Window",
        true,
        None::<&str>,
    )?;
    let restart_service = MenuItem::with_id(
        app,
        MENU_ID_RESTART_SERVICE,
        "Restart Service",
        true,
        None::<&str>,
    )?;

    let menu = Menu::with_items(
        app,
        &[
            &status_item,
            &memory_count,
            &PredefinedMenuItem::separator(app)?,
            &toggle_window,
            &restart_service,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(app, MENU_ID_QUIT, "Quit", true, None::<&str>)?,
        ],
    )?;

    Ok((
        menu,
        TrayItems {
            status: status_item,
            toggle_window,
            restart_service,
            memory_count,
        },
    ))
}

fn load_tray_icon(app: &AppHandle) -> Option<Image<'static>> {
    if let Some(icon) = app.default_window_icon() {
        return Some(icon.clone().to_owned());
    }

    Image::from_bytes(TRAY_ICON_PNG).ok().map(|img| img.to_owned())
}

fn ensure_log_path(app: &AppHandle) -> Option<&PathBuf> {
    if LOG_PATH.get().is_none() {
        if let Ok(dir) = app.path().app_data_dir() {
            let _ = std::fs::create_dir_all(&dir);
            let _ = LOG_PATH.set(dir.join("app.log"));
        }
    }
    LOG_PATH.get()
}

fn log_line(path: &PathBuf, line: &str) {
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(path) {
        let _ = writeln!(file, "{}", line);
    }
}

fn log_panic(message: &str) {
    let path = LOG_PATH
        .get()
        .cloned()
        .unwrap_or_else(|| std::env::temp_dir().join("kiroku-tauri.log"));
    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0);
    let line = format!("{:.3} {}", ts, message);
    log_line(&path, &line);
}

fn log_event(app: &AppHandle, message: &str) {
    let Some(path) = ensure_log_path(app) else {
        return;
    };
    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0);
    let line = format!("{:.3} {}", ts, message);
    log_line(path, &line);
}

fn update_tray_status(tray: &TrayItems, status: &ServiceStatus) {
    let label = match status {
        ServiceStatus::Starting => "Status: Starting",
        ServiceStatus::Running => "Status: Running",
        ServiceStatus::Stopped => "Status: Stopped",
        ServiceStatus::Restarting => "Status: Restarting",
        ServiceStatus::Error(_) => "Status: Error",
    };
    let _ = tray.status.set_text(label);
}

fn update_restart_label(tray: &TrayItems, status: &ServiceStatus) {
    let label = match status {
        ServiceStatus::Running | ServiceStatus::Starting | ServiceStatus::Restarting => {
            "Restart Service"
        }
        ServiceStatus::Stopped | ServiceStatus::Error(_) => "Start Service",
    };
    let _ = tray.restart_service.set_text(label);
}

fn update_memory_count(tray: &TrayItems, count: Option<u64>) {
    let label = match count {
        Some(v) => format!("Memories: {}", v),
        None => "Memories: -".to_string(),
    };
    let _ = tray.memory_count.set_text(label);
}

fn update_toggle_label(tray: &TrayItems, is_visible: bool) {
    let label = if is_visible { "Hide Window" } else { "Show Window" };
    let _ = tray.toggle_window.set_text(label);
}

fn refresh_toggle_label(app: &AppHandle, tray: &TrayItems, close_guard: &Arc<AtomicBool>) {
    if let Some(window) = app.get_webview_window("main") {
        let visible = window.is_visible().unwrap_or(false);
        close_guard.store(!visible, Ordering::SeqCst);
        update_toggle_label(tray, visible);
    }
}

fn toggle_main_window(app: &AppHandle, tray: &TrayItems, close_guard: &Arc<AtomicBool>) {
    if let Some(window) = app.get_webview_window("main") {
        let visible = window.is_visible().unwrap_or(false);
        if visible {
            let _ = window.hide();
            close_guard.store(true, Ordering::SeqCst);
        } else {
            let _ = window.show();
            let _ = window.set_focus();
            close_guard.store(false, Ordering::SeqCst);
        }
        update_toggle_label(tray, !visible);
    }
}

/// Animate window shrinking to menu bar area then hide
#[cfg(target_os = "macos")]
async fn animate_minimize_to_tray(window: Window) {
    use tauri::PhysicalPosition;

    // Get current window position and size
    let Ok(current_pos) = window.outer_position() else { return };
    let Ok(current_size) = window.outer_size() else { return };

    // Target position: top-right corner of screen (near menu bar)
    // Menu bar is typically at y=0, and tray icons are on the right
    let Ok(monitor) = window.current_monitor() else { return };
    let Some(monitor) = monitor else { return };
    let screen_size = monitor.size();

    let target_x = screen_size.width as i32 - 100;  // Near right edge
    let target_y = 25;  // Menu bar height

    // Animation parameters
    let steps = 12;
    let step_duration = Duration::from_millis(16);  // ~60fps

    for i in 1..=steps {
        let progress = i as f64 / steps as f64;
        // Ease-out curve for smoother animation
        let eased = 1.0 - (1.0 - progress).powi(3);

        // Interpolate position
        let new_x = current_pos.x + ((target_x - current_pos.x) as f64 * eased) as i32;
        let new_y = current_pos.y + ((target_y - current_pos.y) as f64 * eased) as i32;

        // Interpolate size (shrink to 10% of original)
        let scale = 1.0 - (eased * 0.9);
        let new_width = (current_size.width as f64 * scale) as u32;
        let new_height = (current_size.height as f64 * scale) as u32;

        let _ = window.set_position(PhysicalPosition::new(new_x, new_y));
        let _ = window.set_size(tauri::PhysicalSize::new(new_width.max(50), new_height.max(50)));

        tokio::time::sleep(step_duration).await;
    }

    // Hide window and restore original size for next show
    let _ = window.hide();
    let _ = window.set_position(current_pos);
    let _ = window.set_size(current_size);
}

#[cfg(not(target_os = "macos"))]
async fn animate_minimize_to_tray(window: Window) {
    let _ = window.hide();
}

fn handle_tray_menu_event(
    app: &AppHandle,
    event: tauri::menu::MenuEvent,
    tray: &TrayItems,
    is_quitting: &Arc<AtomicBool>,
    close_guard: &Arc<AtomicBool>,
) {
    log_event(
        app,
        &format!("tray menu event id={}", event.id().as_ref()),
    );
    match event.id().as_ref() {
        MENU_ID_TOGGLE_WINDOW => {
            toggle_main_window(app, tray, close_guard);
        }
        MENU_ID_RESTART_SERVICE => {
            let app_handle = app.clone();
            let service = app.state::<Arc<PythonService>>().inner().clone();
            tauri::async_runtime::spawn(async move {
                if let Err(e) = restart_service_and_wait(app_handle, service).await {
                    eprintln!("[Tray] Failed to restart service: {}", e);
                }
            });
        }
        MENU_ID_QUIT => {
            request_quit(app.clone(), is_quitting.clone());
        }
        _ => {}
    }
}

async fn fetch_memory_count() -> Option<u64> {
    let client = reqwest::Client::new();
    let resp = client
        .get("http://127.0.0.1:8000/v2/stats")
        .send()
        .await
        .ok()?;
    if !resp.status().is_success() {
        return None;
    }
    let stats: StatsResponse = resp.json().await.ok()?;
    Some(stats.items.total)
}

async fn tray_status_loop(
    app: AppHandle,
    service: Arc<PythonService>,
    tray: TrayItems,
    close_guard: Arc<AtomicBool>,
) {
    let mut status_interval = tokio::time::interval(Duration::from_secs(2));
    let mut stats_interval = tokio::time::interval(Duration::from_secs(30));
    let mut last_status: Option<ServiceStatus> = None;

    loop {
        tokio::select! {
            _ = status_interval.tick() => {
                let status = service.get_status().await;
                if last_status.as_ref() != Some(&status) {
                    update_tray_status(&tray, &status);
                    update_restart_label(&tray, &status);
                    last_status = Some(status);
                }
                refresh_toggle_label(&app, &tray, &close_guard);
            }
            _ = stats_interval.tick() => {
                let status = service.get_status().await;
                if matches!(status, ServiceStatus::Running) {
                    update_memory_count(&tray, fetch_memory_count().await);
                } else {
                    update_memory_count(&tray, None);
                }
            }
        }
    }
}

fn should_start_hidden(app: &AppHandle) -> bool {
    if cfg!(debug_assertions) && std::env::var("KIROKU_ALLOW_START_HIDDEN").is_err() {
        return false;
    }
    if std::env::args().any(|arg| arg == "--tray" || arg == "--hidden") {
        return true;
    }
    if std::env::var("KIROKU_TRAY_ONLY").is_ok() {
        return true;
    }
    if let Ok(app_settings) = settings::load(app) {
        return app_settings.start_hidden;
    }
    false
}

fn request_quit(app: AppHandle, is_quitting: Arc<AtomicBool>) {
    if is_quitting.swap(true, Ordering::SeqCst) {
        return;
    }

    log_event(&app, "request_quit");
    let service = app.state::<Arc<PythonService>>().inner().clone();
    tauri::async_runtime::spawn(async move {
        if let Err(e) = service.stop().await {
            eprintln!("[Tauri] Error stopping service: {}", e);
        }
        app.exit(0);
    });
}

#[cfg(target_os = "macos")]
fn set_launch_at_login(app: &AppHandle, enabled: bool) -> Result<(), String> {
    use std::fs;

    let home = app
        .path()
        .home_dir()
        .map_err(|e| format!("Failed to resolve home dir: {}", e))?;
    let agents_dir = home.join("Library/LaunchAgents");
    fs::create_dir_all(&agents_dir).map_err(|e| format!("Failed to create LaunchAgents dir: {}", e))?;

    let plist_path = agents_dir.join("com.kiroku.memory.plist");

    if !enabled {
        if plist_path.exists() {
            fs::remove_file(&plist_path)
                .map_err(|e| format!("Failed to remove LaunchAgent: {}", e))?;
        }
        return Ok(());
    }

    let exe_path = std::env::current_exe()
        .map_err(|e| format!("Failed to resolve current exe: {}", e))?;

    let plist_content = build_launch_agent_plist(&exe_path)?;
    write_atomic(&plist_path, plist_content.as_bytes())
        .map_err(|e| format!("Failed to write LaunchAgent: {}", e))?;

    Ok(())
}

#[cfg(target_os = "macos")]
fn build_launch_agent_plist(exe_path: &std::path::Path) -> Result<String, String> {
    let exe = exe_path
        .to_str()
        .ok_or_else(|| "Executable path is not valid UTF-8".to_string())?;

    Ok(format!(
        r#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.kiroku.memory</string>
  <key>ProgramArguments</key>
  <array>
    <string>{}</string>
    <string>--tray</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <false/>
  <key>EnvironmentVariables</key>
  <dict>
    <key>KIROKU_TRAY_ONLY</key>
    <string>1</string>
  </dict>
</dict>
</plist>
"#,
        exe
    ))
}

#[cfg(target_os = "macos")]
fn write_atomic(path: &std::path::Path, contents: &[u8]) -> std::io::Result<()> {
    use std::io::Write;
    let tmp_path = path.with_extension("tmp");
    {
        let mut tmp = std::fs::File::create(&tmp_path)?;
        tmp.write_all(contents)?;
        tmp.sync_all()?;
    }
    std::fs::rename(tmp_path, path)?;
    Ok(())
}

#[cfg(not(target_os = "macos"))]
fn set_launch_at_login(_app: &AppHandle, _enabled: bool) -> Result<(), String> {
    Err("Launch at login is only supported on macOS".to_string())
}

/// Start service and wait for health
async fn start_and_wait(app: AppHandle, service: Arc<PythonService>) {
    // Start service
    if let Err(e) = service.start(&app).await {
        eprintln!("[Tauri] Failed to spawn Python service: {}", e);
        service.mark_error(e.to_string()).await;
        app.emit("service-error", e.to_string()).ok();
        return;
    }

    // Wait for health
    match wait_for_health("http://127.0.0.1:8000/health", Duration::from_secs(30)).await {
        Ok(_) => {
            println!("[Tauri] Service is ready!");
            service.mark_running().await;
            app.emit("service-ready", ()).ok();
        }
        Err(e) => {
            eprintln!("[Tauri] Service failed to start: {}", e);
            service.mark_error(e.to_string()).await;
            app.emit("service-error", e.to_string()).ok();
        }
    }
}

/// Monitor service health and report failures
async fn monitor_service(app: AppHandle, service: Arc<PythonService>) {
    let mut consecutive_failures = 0;
    const MAX_FAILURES: u32 = 3;
    const CHECK_INTERVAL: Duration = Duration::from_secs(5);

    loop {
        tokio::time::sleep(CHECK_INTERVAL).await;

        // Skip monitoring if service is intentionally stopped
        if !service.should_auto_restart() {
            continue;
        }

        // Check if process is still running
        if !service.is_running().await {
            println!("[Monitor] Service process is not running");
            let status = service.get_status().await;
            if !matches!(status, ServiceStatus::Error(_)) {
                service
                    .mark_error("Service stopped".to_string())
                    .await;
                app.emit("service-error", "Service stopped").ok();
            }
            continue;
        }

        // Process is running, check health
        match check_health_once().await {
            Some(_) => {
                consecutive_failures = 0;
            }
            None => {
                consecutive_failures += 1;
                println!(
                    "[Monitor] Health check failed ({}/{})",
                    consecutive_failures, MAX_FAILURES
                );

                if consecutive_failures >= MAX_FAILURES {
                    println!("[Monitor] Too many health check failures, marking as error");
                    let status = service.get_status().await;
                    if !matches!(status, ServiceStatus::Error(_)) {
                        service
                            .mark_error("Service unresponsive".to_string())
                            .await;
                        app.emit("service-error", "Service unresponsive").ok();
                    }
                }
            }
        }
    }
}

fn main() {
    std::panic::set_hook(Box::new(|info| {
        log_panic(&format!("panic: {}", info));
    }));

    let service = Arc::new(PythonService::new());
    let is_quitting = Arc::new(AtomicBool::new(false));
    let close_to_tray = Arc::new(AtomicBool::new(false));
    let quit_guard_setup = is_quitting.clone();
    let close_guard_setup = close_to_tray.clone();
    let close_guard_window = close_to_tray.clone();

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(service.clone())
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let service_clone = service.clone();
            let quit_guard = quit_guard_setup.clone();
            let close_guard_setup = close_guard_setup.clone();

            log_event(&app_handle, "setup start");

            #[cfg(target_os = "macos")]
            {
                let force_dock = std::env::var("KIROKU_DOCK_VISIBLE").is_ok();
                if cfg!(debug_assertions) || force_dock {
                    let _ = app_handle.set_activation_policy(tauri::ActivationPolicy::Regular);
                    let _ = app_handle.set_dock_visibility(true);
                    log_event(&app_handle, "dock policy=regular visible=true");
                } else {
                    let _ = app_handle.set_activation_policy(tauri::ActivationPolicy::Accessory);
                    let _ = app_handle.set_dock_visibility(false);
                    log_event(&app_handle, "dock policy=accessory visible=false");
                }
            }

            let mut tray_items_opt = None;
            if let Ok((tray_menu, tray_items)) = build_tray_menu(&app_handle) {
                let tray_items_for_events = tray_items.clone();
                let quit_guard_for_events = quit_guard.clone();
                let close_guard_for_events = close_guard_setup.clone();
                let mut tray_builder = TrayIconBuilder::with_id(TRAY_ID)
                    .menu(&tray_menu)
                    .icon_as_template(false)
                    .tooltip("Kiroku Memory")
                    .on_menu_event(move |app, event| {
                        handle_tray_menu_event(
                            app,
                            event,
                            &tray_items_for_events,
                            &quit_guard_for_events,
                            &close_guard_for_events,
                        );
                    });

                if let Some(icon) = load_tray_icon(&app_handle) {
                    tray_builder = tray_builder.icon(icon);
                } else {
                    tray_builder = tray_builder.title(TRAY_FALLBACK_TITLE);
                }

                if let Ok(tray) = tray_builder.build(app) {
                    let _ = tray.set_tooltip(Some("Kiroku Memory"));
                    log_event(&app_handle, "tray build ok");
                    tray_items_opt = Some(tray_items);
                } else {
                    log_event(&app_handle, "tray build failed");
                }
            }

            if should_start_hidden(&app_handle) {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.hide();
                    close_guard_setup.store(true, Ordering::SeqCst);
                    log_event(&app_handle, "start hidden=true (window hidden)");
                }
            } else {
                close_guard_setup.store(false, Ordering::SeqCst);
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
                log_event(&app_handle, "start hidden=false (focus requested)");
            }
            if let Some(window) = app.get_webview_window("main") {
                let is_visible = window.is_visible().unwrap_or(false);
                let is_maximized = window.is_maximized().unwrap_or(false);
                let is_fullscreen = window.is_fullscreen().unwrap_or(false);
                log_event(
                    &app_handle,
                    &format!(
                        "window present visible={} maximized={} fullscreen={}",
                        is_visible, is_maximized, is_fullscreen
                    ),
                );
            } else {
                log_event(&app_handle, "window missing");
            }

            let keepalive_handle = app_handle.clone();
            tauri::async_runtime::spawn(async move {
                let checks = [1u64, 3, 5, 10, 20];
                for secs in checks {
                    tokio::time::sleep(Duration::from_secs(secs)).await;
                    if let Some(win) = keepalive_handle.get_webview_window("main") {
                        let visible = win.is_visible().unwrap_or(false);
                        log_event(
                            &keepalive_handle,
                            &format!("keepalive {}s visible={}", secs, visible),
                        );
                    }
                }
            });
            if let Some(tray_items) = tray_items_opt.as_ref() {
                refresh_toggle_label(&app_handle, tray_items, &close_guard_setup);
            }

            let app_settings = settings::load(&app_handle).unwrap_or_default();
            if app_settings.auto_start_service {
                let startup_handle = app_handle.clone();
                let startup_service = service_clone.clone();
                tauri::async_runtime::spawn(async move {
                    start_and_wait(startup_handle, startup_service).await;
                });
            } else {
                let svc = service_clone.clone();
                tauri::async_runtime::spawn(async move {
                    let _ = svc.stop().await;
                });
            }

            // Spawn service monitor
            let monitor_handle = app_handle.clone();
            let monitor_svc = service_clone.clone();
            tauri::async_runtime::spawn(async move {
                // Wait a bit before starting monitor
                tokio::time::sleep(Duration::from_secs(5)).await;
                monitor_service(monitor_handle, monitor_svc).await;
            });

            if let Some(tray_items) = tray_items_opt {
                let tray_handle = app_handle.clone();
                let tray_service = service_clone.clone();
                let tray_close_guard = close_guard_setup.clone();
                tauri::async_runtime::spawn(async move {
                    tray_status_loop(tray_handle, tray_service, tray_items, tray_close_guard).await;
                });
            }

            let heartbeat_handle = app_handle.clone();
            tauri::async_runtime::spawn(async move {
                tokio::time::sleep(Duration::from_secs(5)).await;
                log_event(&heartbeat_handle, "heartbeat 5s");
                tokio::time::sleep(Duration::from_secs(10)).await;
                log_event(&heartbeat_handle, "heartbeat 15s");
            });

            Ok(())
        })
        .on_window_event(move |window, event| {
            log_event(&window.app_handle(), &format!("window event {:?}", event));
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                let app_handle = window.app_handle().clone();
                let is_visible = window.is_visible().unwrap_or(false);
                let is_maximized = window.is_maximized().unwrap_or(false);
                let is_fullscreen = window.is_fullscreen().unwrap_or(false);
                log_event(
                    &app_handle,
                    &format!(
                        "close requested visible={} maximized={} fullscreen={}",
                        is_visible, is_maximized, is_fullscreen
                    ),
                );
                api.prevent_close();

                let close_guard = close_guard_window.clone();
                let win_clone = window.clone();
                tauri::async_runtime::spawn(async move {
                    let is_maximized = win_clone.is_maximized().unwrap_or(false);
                    let is_fullscreen = win_clone.is_fullscreen().unwrap_or(false);
                    if is_maximized || is_fullscreen {
                        log_event(&app_handle, "close deferred -> fullscreen/maximized");
                        return;
                    }
                    close_guard.store(true, Ordering::SeqCst);
                    log_event(&app_handle, "close deferred -> animate to tray");
                    animate_minimize_to_tray(win_clone).await;
                });
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_service_status,
            check_health,
            get_stats,
            restart_service,
            stop_service,
            // Config commands
            set_openai_key,
            has_openai_key,
            delete_openai_key,
            get_settings,
            save_settings,
            get_data_dir,
        ])
        .build(tauri::generate_context!())
        .expect("error while running tauri application");

    let quit_guard = is_quitting.clone();
    let close_guard = close_to_tray.clone();
    app.run(move |app_handle, event| match event {
        tauri::RunEvent::ExitRequested { api, code, .. } => {
            log_event(
                app_handle,
                &format!(
                    "exit requested code={:?} quit_guard={} close_guard={}",
                    code,
                    quit_guard.load(Ordering::SeqCst),
                    close_guard.load(Ordering::SeqCst)
                ),
            );
            if quit_guard.load(Ordering::SeqCst) {
                return;
            }
            api.prevent_exit();
            if close_guard.load(Ordering::SeqCst) {
                return;
            }
        }
        tauri::RunEvent::Exit => {
            log_event(app_handle, "run event exit");
        }
        _ => {}
    });
}
