#![allow(unused_imports)]
use serde::Serialize;
use std::mem;
use windows::Win32::System::SystemInformation::*;
use windows::Win32::System::Threading::*;
use windows::Win32::System::LibraryLoader::*;

#[allow(dead_code)]
#[derive(Debug, Serialize)]
pub struct MemoryInfo {
    pub total_gb: f64,
    pub available_gb: f64,
    pub used_gb: f64,
    pub percent: f64,
    pub cache_mb: f64,
}

// Constants from winternl.h
const SYSTEM_MEMORY_LIST_INFORMATION: u32 = 0x50;
const MEMORY_EMPTY_WORKING_SETS: u32 = 0x2;
const MEMORY_FLUSH_MODIFIED_LIST: u32 = 0x3;
const MEMORY_PURGE_STANDBY_LIST: u32 = 0x4;
const MEMORY_PURGE_LOW_PRIORITY_STANDBY_LIST: u32 = 0x5;

pub fn get_memory_info() -> Result<serde_json::Value, String> {
    unsafe {
        let mut statex: MEMORYSTATUSEX = MEMORYSTATUSEX::default();
        statex.dwLength = mem::size_of::<MEMORYSTATUSEX>() as u32;

        GlobalMemoryStatusEx(&mut statex)
            .map_err(|e| format!("GlobalMemoryStatusEx failed: {}", e))?;

        let total = statex.ullTotalPhys as f64 / (1024.0 * 1024.0 * 1024.0);
        let avail = statex.ullAvailPhys as f64 / (1024.0 * 1024.0 * 1024.0);

        Ok(serde_json::json!({
            "total_gb": (total * 10.0).round() / 10.0,
            "available_gb": (avail * 10.0).round() / 10.0,
            "used_gb": ((total - avail) * 10.0).round() / 10.0,
            "percent": statex.dwMemoryLoad,
        }))
    }
}

pub fn clean_memory(switches: &[bool]) -> Result<String, String> {
    let mut methods = Vec::new();

    unsafe {
        let ntdll = GetModuleHandleA(
            windows::core::s!("ntdll.dll"),
        )
        .map_err(|e| format!("ntdll not found: {}", e))?;

        let nt_set_sys_info: extern "system" fn(u32, *const std::ffi::c_void, u32) -> i32 =
        {
            let raw_addr = GetProcAddress(
                ntdll,
                windows::core::s!("NtSetSystemInformation"),
            );
            let addr = match raw_addr {
                Some(a) => a,
                None => return Err("NtSetSystemInformation not found".to_string()),
            };
            std::mem::transmute(addr)
        };

        // Empty working sets (index 0)
        if switches.get(0).copied().unwrap_or(false) {
            let cmd = MEMORY_EMPTY_WORKING_SETS as i32;
            let result = nt_set_sys_info(
                SYSTEM_MEMORY_LIST_INFORMATION,
                &cmd as *const _ as *const std::ffi::c_void,
                4,
            );
            if result == 0 {
                methods.push("EmptyWorkingSets");
            }
        }

        // Flush modified list (index 1)
        if switches.get(1).copied().unwrap_or(false) {
            let cmd = MEMORY_FLUSH_MODIFIED_LIST as i32;
            let result = nt_set_sys_info(
                SYSTEM_MEMORY_LIST_INFORMATION,
                &cmd as *const _ as *const std::ffi::c_void,
                4,
            );
            if result == 0 {
                methods.push("FlushModifiedList");
            }
        }

        // Purge standby list (index 2)
        if switches.get(2).copied().unwrap_or(false) {
            let cmd = MEMORY_PURGE_STANDBY_LIST as i32;
            let result = nt_set_sys_info(
                SYSTEM_MEMORY_LIST_INFORMATION,
                &cmd as *const _ as *const std::ffi::c_void,
                4,
            );
            if result == 0 {
                methods.push("PurgeStandbyList");
            }
        }

        // Purge low priority standby (index 3)
        if switches.get(3).copied().unwrap_or(false) {
            let cmd = MEMORY_PURGE_LOW_PRIORITY_STANDBY_LIST as i32;
            let result = nt_set_sys_info(
                SYSTEM_MEMORY_LIST_INFORMATION,
                &cmd as *const _ as *const std::ffi::c_void,
                4,
            );
            if result == 0 {
                methods.push("PurgeLowPriorityStandby");
            }
        }

        // Set working set size (index 4)
        if switches.get(4).copied().unwrap_or(false) {
            methods.push("TrimWorkingSet(unavailable)");
        }

        // Flush system cache (index 5)
        if switches.get(5).copied().unwrap_or(false) {
            methods.push("FlushSystemCache(unavailable)");
        }
    }

    if methods.is_empty() {
        return Err("No cleanup actions selected".into());
    }

    Ok(methods.join("+"))
}


