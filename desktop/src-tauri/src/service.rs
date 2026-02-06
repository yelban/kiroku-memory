// Kiroku Memory Desktop - Python Service Management
// Handles spawning, health checking, and lifecycle of the Python FastAPI service

use crate::config::{keychain, keys};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;
use tauri::{AppHandle, Manager};
use tokio::sync::Mutex;

/// Service status for frontend
#[derive(Clone, serde::Serialize, PartialEq)]
pub enum ServiceStatus {
    Starting,
    Running,
    Stopped,
    Error(String),
    Restarting,
}

/// Health check response from the API
#[derive(serde::Deserialize, serde::Serialize, Debug, Clone)]
pub struct HealthResponse {
    pub status: String,
    pub version: String,
}

/// Python service state
pub struct PythonService {
    child: Mutex<Option<Child>>,
    status: Mutex<ServiceStatus>,
    should_restart: AtomicBool,
    restart_in_progress: AtomicBool,
}

impl PythonService {
    pub fn new() -> Self {
        Self {
            child: Mutex::new(None),
            status: Mutex::new(ServiceStatus::Stopped),
            should_restart: AtomicBool::new(true),
            restart_in_progress: AtomicBool::new(false),
        }
    }

    /// Try to acquire the restart lock. Returns true if acquired, false if already in progress.
    pub fn try_start_restart(&self) -> bool {
        self.restart_in_progress
            .compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst)
            .is_ok()
    }

    /// Release the restart lock.
    pub fn finish_restart(&self) {
        self.restart_in_progress.store(false, Ordering::SeqCst);
    }

    /// Get current service status
    pub async fn get_status(&self) -> ServiceStatus {
        self.status.lock().await.clone()
    }

    /// Set service status
    async fn set_status(&self, status: ServiceStatus) {
        *self.status.lock().await = status;
    }

    /// Check if service process is still running
    pub async fn is_running(&self) -> bool {
        let mut guard = self.child.lock().await;
        if let Some(child) = guard.as_mut() {
            match child.try_wait() {
                Ok(None) => true,  // Still running
                Ok(Some(_)) => false,  // Exited
                Err(_) => false,  // Error checking
            }
        } else {
            false
        }
    }

    /// Stop the service
    pub async fn stop(&self) -> anyhow::Result<()> {
        self.should_restart.store(false, Ordering::SeqCst);

        let mut guard = self.child.lock().await;
        if let Some(mut child) = guard.take() {
            println!("[Service] Stopping Python service (PID: {})...", child.id());
            let _ = child.kill();
            let _ = child.wait();
            println!("[Service] Python service stopped.");
        }
        self.set_status(ServiceStatus::Stopped).await;
        Ok(())
    }

    /// Start the service
    pub async fn start(&self, app: &AppHandle) -> anyhow::Result<()> {
        self.should_restart.store(true, Ordering::SeqCst);
        self.set_status(ServiceStatus::Starting).await;

        let (python_bin, pythonpath) = get_python_paths(app)?;
        let data_dir = get_data_dir(app)?;
        let data_path = data_dir.to_string_lossy().replace('\\', "/");
        let surreal_url = format!("file://{}/surrealdb/kiroku", data_path);

        // Get OpenAI API key from Keychain
        let openai_key = keychain::get_secret(keys::OPENAI_API_KEY).unwrap_or(None);

        println!("[Service] Starting Python service...");
        println!("[Service] Python: {:?}", python_bin);
        println!("[Service] PYTHONPATH: {:?}", pythonpath);
        println!("[Service] Data dir: {:?}", data_dir);
        println!("[Service] SurrealDB URL: {}", surreal_url);
        println!(
            "[Service] OpenAI API Key: {}",
            if openai_key.is_some() {
                "configured"
            } else {
                "not set"
            }
        );

        let child = spawn_python_process(&python_bin, &pythonpath, &surreal_url, openai_key)?;
        println!("[Service] Python service started with PID: {}", child.id());

        *self.child.lock().await = Some(child);
        Ok(())
    }

    /// Restart the service
    pub async fn restart(&self, app: &AppHandle) -> anyhow::Result<()> {
        println!("[Service] Restarting service...");
        self.set_status(ServiceStatus::Restarting).await;
        self.stop().await?;
        tokio::time::sleep(Duration::from_millis(500)).await;
        self.should_restart.store(true, Ordering::SeqCst);
        self.start(app).await
    }

    /// Mark service as running (called after health check succeeds)
    pub async fn mark_running(&self) {
        self.set_status(ServiceStatus::Running).await;
    }

    /// Mark service as error
    pub async fn mark_error(&self, error: String) {
        self.set_status(ServiceStatus::Error(error)).await;
    }

    /// Check if auto-restart is enabled
    pub fn should_auto_restart(&self) -> bool {
        self.should_restart.load(Ordering::SeqCst)
    }
}

/// Get Python binary and PYTHONPATH based on environment (dev vs production)
pub fn get_python_paths(app: &AppHandle) -> anyhow::Result<(PathBuf, PathBuf)> {
    let resource_dir = app
        .path()
        .resource_dir()
        .expect("Failed to get resource dir");

    println!("[Service] Resource dir: {:?}", resource_dir);

    // Platform-specific Python binary path
    #[cfg(target_os = "windows")]
    let python_binary_name = "python.exe";
    #[cfg(not(target_os = "windows"))]
    let python_binary_name = "bin/python3";

    // Check if bundled resources exist (production mode)
    let bundled_python = resource_dir.join("python").join(python_binary_name);
    let bundled_app = resource_dir.join("app/kiroku_memory");

    if bundled_python.exists() && bundled_app.exists() {
        // Production: use bundled resources
        println!("[Service] Using bundled Python runtime");
        println!("[Service] Python bin: {:?}", bundled_python);
        let app_dir = resource_dir.join("app");
        Ok((bundled_python, app_dir))
    } else {
        // Development: use tools/packaging/dist Python
        println!("[Service] Using development Python runtime");

        let arch = if cfg!(target_arch = "aarch64") {
            "aarch64"
        } else {
            "x86_64"
        };

        #[cfg(target_os = "macos")]
        let platform = "darwin";
        #[cfg(target_os = "linux")]
        let platform = "linux";
        #[cfg(target_os = "windows")]
        let platform = "windows";

        // Navigate from resource_dir up to project root
        // In dev: resource_dir = .../desktop/src-tauri/target/debug/
        // project_root = .../kiroku-memory/
        let project_root = resource_dir
            .parent() // target
            .and_then(|p: &Path| p.parent()) // src-tauri
            .and_then(|p: &Path| p.parent()) // desktop
            .and_then(|p: &Path| p.parent()) // kiroku-memory
            .map(|p: &Path| p.to_path_buf())
            .unwrap_or_else(|| PathBuf::from("."));

        let python_bin = project_root
            .join("tools/packaging/dist")
            .join(format!("{}-{}", platform, arch))
            .join("python")
            .join(python_binary_name);

        println!("[Service] Project root: {:?}", project_root);
        println!("[Service] Python bin: {:?}", python_bin);

        Ok((python_bin, project_root))
    }
}

/// Get data directory for the app
pub fn get_data_dir(app: &AppHandle) -> anyhow::Result<PathBuf> {
    let data_dir = app
        .path()
        .app_data_dir()
        .expect("Failed to get app data dir");
    std::fs::create_dir_all(&data_dir)?;
    Ok(data_dir)
}

/// Spawn the Python process
fn spawn_python_process(
    python_bin: &PathBuf,
    pythonpath: &PathBuf,
    surreal_url: &str,
    openai_key: Option<String>,
) -> anyhow::Result<Child> {
    if !python_bin.exists() {
        anyhow::bail!(
            "Python binary not found at: {}. Ensure the app was installed correctly.",
            python_bin.display()
        );
    }

    let mut cmd = Command::new(python_bin);
    cmd.args([
        "-m",
        "uvicorn",
        "kiroku_memory.api:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ])
    .env("PYTHONPATH", pythonpath)
    .env("BACKEND", "surrealdb")
    .env("SURREAL_URL", surreal_url)
    .env("SURREAL_NAMESPACE", "kiroku")
    .env("SURREAL_DATABASE", "memory")
    .env("PYTHONUNBUFFERED", "1")
    .stdout(Stdio::inherit())
    .stderr(Stdio::inherit());

    // Pass OpenAI API key if available
    if let Some(key) = openai_key {
        cmd.env("OPENAI_API_KEY", key);
    }

    Ok(cmd.spawn()?)
}

/// Wait for the API to become healthy
pub async fn wait_for_health(url: &str, timeout: Duration) -> anyhow::Result<HealthResponse> {
    let client = reqwest::Client::new();
    let deadline = std::time::Instant::now() + timeout;

    println!("[Service] Waiting for API health at {}...", url);

    while std::time::Instant::now() < deadline {
        match client.get(url).send().await {
            Ok(resp) if resp.status().is_success() => {
                if let Ok(health) = resp.json::<HealthResponse>().await {
                    println!(
                        "[Service] API is healthy! Status: {}, Version: {}",
                        health.status, health.version
                    );
                    return Ok(health);
                }
            }
            Ok(resp) => {
                println!("[Service] API returned status: {}", resp.status());
            }
            Err(e) => {
                println!("[Service] Connection error (retrying): {}", e);
            }
        }
        tokio::time::sleep(Duration::from_millis(250)).await;
    }

    anyhow::bail!("Health check timed out after {:?}", timeout)
}

/// Check health once (non-blocking)
pub async fn check_health_once() -> Option<HealthResponse> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .ok()?;

    match client.get("http://127.0.0.1:8000/health").send().await {
        Ok(resp) if resp.status().is_success() => resp.json::<HealthResponse>().await.ok(),
        _ => None,
    }
}
