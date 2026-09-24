use serde::{Deserialize, Serialize};
use crate::config::Config;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GameProfile {
    pub name: String,
    pub description: String,
    pub trigger_process: String,
    pub rules: Vec<String>,
    pub ramdisk_enabled: bool,
    pub memory_clean: bool,
    pub io_priority_processes: Vec<serde_json::Value>,
    pub enabled: bool,
    pub created_at: String,
}

pub struct ProfileManager {
    pub profiles: Vec<GameProfile>,
    pub active: Option<String>,
}

impl ProfileManager {
    pub fn new(config: &Config) -> Self {
        let profiles: Vec<GameProfile> = config
            .profiles
            .iter()
            .filter_map(|p| serde_json::from_value(p.clone()).ok())
            .collect();
        Self {
            profiles,
            active: None,
        }
    }

    pub fn list_profiles(&self) -> Vec<GameProfile> {
        self.profiles.clone()
    }

    pub fn activate(&mut self, name: &str) -> Result<(), String> {
        let profile = self.profiles.iter().find(|p| p.name == name);
        match profile {
            Some(p) => {
                log::info!("Activating profile: {}", p.name);

                // Apply RAM disk if enabled
                if p.ramdisk_enabled {
                    log::info!("Profile: enabling RAM disk");
                }

                // Trigger memory clean if enabled
                if p.memory_clean {
                    log::info!("Profile: triggering memory clean");
                    let _ = crate::memory::clean_memory(&[true, true, true, true, true, true]);
                }

                self.active = Some(name.into());
                Ok(())
            }
            None => Err(format!("Profile not found: {}", name)),
        }
    }

    pub fn deactivate(&mut self) -> Result<(), String> {
        if let Some(ref name) = self.active {
            log::info!("Deactivating profile: {}", name);
            self.active = None;
            Ok(())
        } else {
            Err("No active profile".into())
        }
    }

    pub fn check_trigger(&self, process_name: &str) -> Option<String> {
        for profile in &self.profiles {
            if profile.enabled
                && !profile.trigger_process.is_empty()
                && profile.trigger_process.eq_ignore_ascii_case(process_name)
            {
                return Some(profile.name.clone());
            }
        }
        None
    }
}
