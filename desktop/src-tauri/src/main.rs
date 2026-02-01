// Kiroku Memory Desktop - Tauri v2
// Main entry point

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod config;
mod service;

use config::{keychain, keys, settings, AppSettings};
use service::{check_health_once, wait_for_health, PythonService, ServiceStatus};
use std::sync::Arc;
use std::time::Duration;
use tauri::{AppHandle, Emitter, Manager, State};

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
    service.restart(&app).await.map_err(|e| e.to_string())?;

    // Wait for health
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

/// Tauri command to stop service
#[tauri::command]
async fn stop_service(service: State<'_, Arc<PythonService>>) -> Result<(), String> {
    service.stop().await.map_err(|e| e.to_string())
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

/// Monitor service health and restart if needed
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

            if service.should_auto_restart() {
                println!("[Monitor] Attempting to restart service...");
                app.emit("service-restarting", ()).ok();

                if let Err(e) = service.start(&app).await {
                    eprintln!("[Monitor] Failed to restart service: {}", e);
                    service.mark_error(e.to_string()).await;
                    app.emit("service-error", e.to_string()).ok();
                    continue;
                }

                // Wait for health after restart
                match wait_for_health("http://127.0.0.1:8000/health", Duration::from_secs(30)).await
                {
                    Ok(_) => {
                        println!("[Monitor] Service restarted successfully");
                        service.mark_running().await;
                        app.emit("service-ready", ()).ok();
                        consecutive_failures = 0;
                    }
                    Err(e) => {
                        eprintln!("[Monitor] Service restart failed: {}", e);
                        service.mark_error(e.to_string()).await;
                        app.emit("service-error", e.to_string()).ok();
                    }
                }
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
                    service
                        .mark_error("Service unresponsive".to_string())
                        .await;
                    app.emit("service-error", "Service unresponsive").ok();
                }
            }
        }
    }
}

fn main() {
    let service = Arc::new(PythonService::new());

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(service.clone())
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let service_clone = service.clone();

            // Spawn service startup
            let startup_handle = app_handle.clone();
            let startup_service = service_clone.clone();
            tauri::async_runtime::spawn(async move {
                start_and_wait(startup_handle, startup_service).await;
            });

            // Spawn service monitor
            let monitor_handle = app_handle.clone();
            let monitor_svc = service_clone.clone();
            tauri::async_runtime::spawn(async move {
                // Wait a bit before starting monitor
                tokio::time::sleep(Duration::from_secs(5)).await;
                monitor_service(monitor_handle, monitor_svc).await;
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                println!("[Tauri] Window close requested, shutting down...");

                let service: State<Arc<PythonService>> = window.state();
                let service = service.inner().clone();

                // Stop service synchronously
                tauri::async_runtime::block_on(async {
                    if let Err(e) = service.stop().await {
                        eprintln!("[Tauri] Error stopping service: {}", e);
                    }
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
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
