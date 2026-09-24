mod config;
mod memory;
mod monitor;
mod process;
mod profiles;
mod ramdisk;
mod rules;

use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri::State;

pub struct AppState {
    pub running: Mutex<bool>,
    pub config: Mutex<config::Config>,
    pub rule_engine: Mutex<rules::RuleEngine>,
    pub profile_manager: Mutex<profiles::ProfileManager>,
}

#[derive(Serialize, Deserialize)]
pub struct AppInfo {
    pub version: String,
    pub status: String,
    pub process_count: usize,
}

#[tauri::command]
fn get_app_info(state: State<AppInfo>) -> Result<AppInfo, String> {
    let inner = state.inner();
    Ok(AppInfo {
        version: inner.version.clone(),
        status: inner.status.clone(),
        process_count: inner.process_count,
    })
}

#[tauri::command]
fn get_status(state: State<AppState>) -> Result<serde_json::Value, String> {
    let config_guard = state.config.lock().map_err(|e| e.to_string())?;
    let config = &*config_guard;
    let running = *state.running.lock().map_err(|e| e.to_string())?;

    Ok(serde_json::json!({
        "running": running,
        "monitor_enabled": config.monitor.enabled,
        "use_wmi": config.monitor.use_wmi,
        "ramdisk_enabled": config.ramdisk.enabled,
        "version": "3.0.0"
    }))
}

#[tauri::command]
fn get_processes() -> Result<Vec<process::ProcessInfo>, String> {
    process::list_processes().map_err(|e| e.to_string())
}

#[tauri::command]
fn limit_process(pid: u32, config_json: String) -> Result<String, String> {
    let cfg: process::ProcessLimitConfig =
        serde_json::from_str(&config_json).map_err(|e| e.to_string())?;
    let result = process::limit_process(pid, &cfg)?;
    Ok(result)
}

#[tauri::command]
fn get_memory_info() -> Result<serde_json::Value, String> {
    memory::get_memory_info().map_err(|e| e.to_string())
}

#[tauri::command]
fn clean_memory(switches: Vec<bool>) -> Result<String, String> {
    memory::clean_memory(&switches).map_err(|e| e.to_string())
}

#[tauri::command]
fn setup_ramdisk(letter: String, size_mb: u32) -> Result<String, String> {
    ramdisk::setup_ramdisk(&letter, size_mb).map_err(|e| e.to_string())
}

#[tauri::command]
fn cleanup_ramdisk(letter: String) -> Result<String, String> {
    ramdisk::cleanup_ramdisk(&letter).map_err(|e| e.to_string())
}

#[tauri::command]
fn get_ramdisk_info(letter: String) -> Result<serde_json::Value, String> {
    ramdisk::get_ramdisk_info(&letter).map_err(|e| e.to_string())
}

#[tauri::command]
fn get_rules(state: State<AppState>) -> Result<Vec<rules::ProcessRule>, String> {
    let engine = state.rule_engine.lock().map_err(|e| e.to_string())?;
    Ok(engine.list_rules())
}

#[tauri::command]
fn add_rule(state: State<AppState>, rule_json: String) -> Result<(), String> {
    let rule: rules::ProcessRule =
        serde_json::from_str(&rule_json).map_err(|e| e.to_string())?;
    let mut engine = state.rule_engine.lock().map_err(|e| e.to_string())?;
    engine.add_rule(rule);
    let config = state.config.lock().map_err(|e| e.to_string())?;
    engine.save(&*config)?;
    Ok(())
}

#[tauri::command]
fn remove_rule(state: State<AppState>, name: String) -> Result<(), String> {
    let mut engine = state.rule_engine.lock().map_err(|e| e.to_string())?;
    engine.remove_rule(&name);
    let config = state.config.lock().map_err(|e| e.to_string())?;
    engine.save(&*config)?;
    Ok(())
}

#[tauri::command]
fn get_profiles(state: State<AppState>) -> Result<Vec<profiles::GameProfile>, String> {
    let pm = state.profile_manager.lock().map_err(|e| e.to_string())?;
    Ok(pm.list_profiles())
}

#[tauri::command]
fn activate_profile(state: State<AppState>, name: String) -> Result<(), String> {
    let mut pm = state.profile_manager.lock().map_err(|e| e.to_string())?;
    pm.activate(&name)
}

#[tauri::command]
fn deactivate_profile(state: State<AppState>) -> Result<(), String> {
    let mut pm = state.profile_manager.lock().map_err(|e| e.to_string())?;
    pm.deactivate()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    simple_logger::SimpleLogger::new()
        .with_level(log::LevelFilter::Info)
        .init()
        .ok();

    let init_config = config::Config::load().unwrap_or_default();
    let rule_engine = rules::RuleEngine::new(&init_config);
    let profile_manager = profiles::ProfileManager::new(&init_config);

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(AppInfo {
            version: "3.0.0".to_string(),
            status: "ready".to_string(),
            process_count: 0,
        })
        .manage(AppState {
            running: Mutex::new(false),
            config: Mutex::new(init_config),
            rule_engine: Mutex::new(rule_engine),
            profile_manager: Mutex::new(profile_manager),
        })
        .invoke_handler(tauri::generate_handler![
            get_app_info,
            get_status,
            get_processes,
            limit_process,
            get_memory_info,
            clean_memory,
            setup_ramdisk,
            cleanup_ramdisk,
            get_ramdisk_info,
            get_rules,
            add_rule,
            remove_rule,
            get_profiles,
            activate_profile,
            deactivate_profile,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
