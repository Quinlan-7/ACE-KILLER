use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub config_version: u32,
    pub notifications: NotificationsConfig,
    pub logging: LoggingConfig,
    pub application: ApplicationConfig,
    pub monitor: MonitorConfig,
    pub memory_cleaner: MemoryCleanerConfig,
    pub io_priority: IoPriorityConfig,
    pub ramdisk: RamdiskConfig,
    pub rules: Vec<serde_json::Value>,
    pub profiles: Vec<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NotificationsConfig {
    pub enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoggingConfig {
    pub retention_days: u32,
    pub rotation: String,
    pub debug_mode: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApplicationConfig {
    pub auto_start: bool,
    pub close_to_tray: bool,
    pub theme: String,
    pub startup_delay: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MonitorConfig {
    pub enabled: bool,
    pub use_wmi: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryCleanerConfig {
    pub enabled: bool,
    pub brute_mode: bool,
    pub switches: Vec<bool>,
    pub interval: u32,
    pub threshold: f64,
    pub cooldown: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IoPriorityConfig {
    pub processes: Vec<IoPriorityProcess>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IoPriorityProcess {
    pub name: String,
    pub priority: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RamdiskConfig {
    pub enabled: bool,
    pub auto_cleanup: bool,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            config_version: 2,
            notifications: NotificationsConfig { enabled: true },
            logging: LoggingConfig {
                retention_days: 7,
                rotation: "1 day".into(),
                debug_mode: false,
            },
            application: ApplicationConfig {
                auto_start: false,
                close_to_tray: true,
                theme: "light".into(),
                startup_delay: 30,
            },
            monitor: MonitorConfig {
                enabled: true,
                use_wmi: true,
            },
            memory_cleaner: MemoryCleanerConfig {
                enabled: false,
                brute_mode: true,
                switches: vec![true, true, false, false, false, false],
                interval: 300,
                threshold: 80.0,
                cooldown: 60,
            },
            io_priority: IoPriorityConfig {
                processes: vec![
                    IoPriorityProcess { name: "SGuard64.exe".into(), priority: 0 },
                    IoPriorityProcess { name: "ACE-Tray.exe".into(), priority: 0 },
                ],
            },
            ramdisk: RamdiskConfig {
                enabled: false,
                auto_cleanup: true,
            },
            rules: vec![],
            profiles: vec![],
        }
    }
}

impl Config {
    pub fn config_path() -> PathBuf {
        let home = std::env::var("USERPROFILE")
            .unwrap_or_else(|_| "C:\\Users\\Default".into());
        PathBuf::from(home).join(".ace-killer").join("config.yaml")
    }

    pub fn ensure_dir() -> std::io::Result<()> {
        let config_path = Self::config_path();
        let dir = config_path.parent().unwrap();
        std::fs::create_dir_all(dir)
    }

    pub fn load() -> Option<Self> {
        let path = Self::config_path();
        if !path.exists() {
            let config = Self::default();
            config.save().ok();
            return Some(config);
        }
        match std::fs::read_to_string(&path) {
            Ok(content) => {
                serde_yaml::from_str(&content).ok().or_else(|| {
                    log::warn!("Config parse failed, using defaults");
                    Some(Self::default())
                })
            }
            Err(e) => {
                log::error!("Config load error: {}", e);
                Some(Self::default())
            }
        }
    }

    pub fn save(&self) -> Result<(), String> {
        Self::ensure_dir().map_err(|e| e.to_string())?;
        let content = serde_yaml::to_string(self).map_err(|e| e.to_string())?;
        std::fs::write(Self::config_path(), content).map_err(|e| e.to_string())
    }
}
