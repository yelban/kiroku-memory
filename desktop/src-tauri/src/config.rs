// Kiroku Memory Desktop - Configuration Management
// Handles secure credential storage using macOS Keychain

use serde::{Deserialize, Serialize};

/// Configuration keys
pub mod keys {
    pub const OPENAI_API_KEY: &str = "openai_api_key";
}

/// Application settings (non-sensitive, stored in app data)
#[derive(Clone, Debug, Serialize, Deserialize, Default)]
pub struct AppSettings {
    pub auto_start_service: bool,
    pub service_port: u16,
}

impl AppSettings {
    pub fn default_settings() -> Self {
        Self {
            auto_start_service: true,
            service_port: 8000,
        }
    }
}

/// Keychain operations for macOS
#[cfg(target_os = "macos")]
pub mod keychain {
    use security_framework::passwords::{delete_generic_password, get_generic_password, set_generic_password};

    /// Service name for Keychain storage
    const KEYCHAIN_SERVICE: &str = "com.kiroku.memory";

    /// Store a secret in macOS Keychain
    pub fn set_secret(key: &str, value: &str) -> anyhow::Result<()> {
        // Delete existing entry if present (set_generic_password doesn't update)
        let _ = delete_generic_password(KEYCHAIN_SERVICE, key);

        set_generic_password(KEYCHAIN_SERVICE, key, value.as_bytes())
            .map_err(|e| anyhow::anyhow!("Failed to store in Keychain: {}", e))?;

        Ok(())
    }

    /// Retrieve a secret from macOS Keychain
    pub fn get_secret(key: &str) -> anyhow::Result<Option<String>> {
        match get_generic_password(KEYCHAIN_SERVICE, key) {
            Ok(data) => {
                let value = String::from_utf8(data.to_vec())
                    .map_err(|e| anyhow::anyhow!("Invalid UTF-8 in Keychain data: {}", e))?;
                Ok(Some(value))
            }
            Err(e) => {
                // Item not found is not an error
                if e.code() == -25300 {
                    Ok(None)
                } else {
                    Err(anyhow::anyhow!("Failed to read from Keychain: {}", e))
                }
            }
        }
    }

    /// Delete a secret from macOS Keychain
    pub fn delete_secret(key: &str) -> anyhow::Result<()> {
        match delete_generic_password(KEYCHAIN_SERVICE, key) {
            Ok(()) => Ok(()),
            Err(e) => {
                // Item not found is not an error
                if e.code() == -25300 {
                    Ok(())
                } else {
                    Err(anyhow::anyhow!("Failed to delete from Keychain: {}", e))
                }
            }
        }
    }

    /// Check if a secret exists in Keychain (without revealing the value)
    pub fn has_secret(key: &str) -> bool {
        get_generic_password(KEYCHAIN_SERVICE, key).is_ok()
    }
}

/// Fallback for non-macOS platforms (stores in memory only - NOT secure)
#[cfg(not(target_os = "macos"))]
pub mod keychain {
    use std::collections::HashMap;
    use std::sync::Mutex;
    use once_cell::sync::Lazy;

    static SECRETS: Lazy<Mutex<HashMap<String, String>>> = Lazy::new(|| Mutex::new(HashMap::new()));

    pub fn set_secret(key: &str, value: &str) -> anyhow::Result<()> {
        let mut secrets = SECRETS.lock().unwrap();
        secrets.insert(key.to_string(), value.to_string());
        Ok(())
    }

    pub fn get_secret(key: &str) -> anyhow::Result<Option<String>> {
        let secrets = SECRETS.lock().unwrap();
        Ok(secrets.get(key).cloned())
    }

    pub fn delete_secret(key: &str) -> anyhow::Result<()> {
        let mut secrets = SECRETS.lock().unwrap();
        secrets.remove(key);
        Ok(())
    }

    pub fn has_secret(key: &str) -> bool {
        let secrets = SECRETS.lock().unwrap();
        secrets.contains_key(key)
    }
}

/// Settings file operations
pub mod settings {
    use super::*;
    use std::path::PathBuf;
    use tauri::{AppHandle, Manager};

    fn settings_path(app: &AppHandle) -> anyhow::Result<PathBuf> {
        let data_dir = app
            .path()
            .app_data_dir()
            .map_err(|e| anyhow::anyhow!("Failed to get app data dir: {}", e))?;
        std::fs::create_dir_all(&data_dir)?;
        Ok(data_dir.join("settings.json"))
    }

    /// Load settings from file
    pub fn load(app: &AppHandle) -> anyhow::Result<AppSettings> {
        let path = settings_path(app)?;
        if path.exists() {
            let content = std::fs::read_to_string(&path)?;
            let settings: AppSettings = serde_json::from_str(&content)?;
            Ok(settings)
        } else {
            Ok(AppSettings::default_settings())
        }
    }

    /// Save settings to file
    pub fn save(app: &AppHandle, settings: &AppSettings) -> anyhow::Result<()> {
        let path = settings_path(app)?;
        let content = serde_json::to_string_pretty(settings)?;
        std::fs::write(&path, content)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[cfg(target_os = "macos")]
    fn test_keychain_operations() {
        let test_key = "test_key_kiroku";
        let test_value = "test_value_123";

        // Clean up first
        let _ = keychain::delete_secret(test_key);

        // Test set
        keychain::set_secret(test_key, test_value).unwrap();

        // Test get
        let retrieved = keychain::get_secret(test_key).unwrap();
        assert_eq!(retrieved, Some(test_value.to_string()));

        // Test has
        assert!(keychain::has_secret(test_key));

        // Test delete
        keychain::delete_secret(test_key).unwrap();
        assert!(!keychain::has_secret(test_key));
    }
}
