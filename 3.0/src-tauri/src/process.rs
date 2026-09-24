use serde::{Deserialize, Serialize};
use windows::Win32::Foundation::*;
use windows::Win32::System::Threading::*;
use windows::Win32::System::ProcessStatus::*;
use windows::Win32::System::LibraryLoader::*;


#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessInfo {
    pub pid: u32,
    pub name: String,
    pub cpu_percent: f64,
    pub memory_mb: f64,
    pub thread_count: u32,
    pub priority: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessLimitConfig {
    pub io_priority: Option<u32>,
    pub cpu_priority: Option<String>,
    pub max_cores: Option<u32>,
    pub power_throttling: Option<bool>,
}

pub fn list_processes() -> Result<Vec<ProcessInfo>, String> {
    let mut process_ids = [0u32; 1024];
    let mut bytes_returned: u32 = 0;

    unsafe {
        let _ = EnumProcesses(
            process_ids.as_mut_ptr(),
            std::mem::size_of_val(&process_ids) as u32,
            &mut bytes_returned,
        );
    }

    let count = (bytes_returned / 4) as usize;
    let mut processes = Vec::new();

    for i in 0..count {
        let pid = process_ids[i];
        if pid == 0 {
            continue;
        }

        let info = get_process_info(pid).unwrap_or(ProcessInfo {
            pid,
            name: format!("PID-{}", pid),
            cpu_percent: 0.0,
            memory_mb: 0.0,
            thread_count: 0,
            priority: "unknown".into(),
        });
        processes.push(info);
    }

    Ok(processes)
}

fn get_process_info(pid: u32) -> Option<ProcessInfo> {
    unsafe {
        let handle = OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
            false,
            pid,
        )
        .ok()?;

        let mut exe_name = [0u16; 260];
        let mut size = exe_name.len() as u32;

        QueryFullProcessImageNameW(
            handle,
            windows::Win32::System::Threading::PROCESS_NAME_WIN32,
            windows::core::PWSTR(exe_name.as_mut_ptr()),
            &mut size,
        )
        .ok()?;

        let name = String::from_utf16_lossy(&exe_name[..size as usize]);
        let file_name = std::path::Path::new(&name)
            .file_name()
            .unwrap_or_default()
            .to_string_lossy()
            .to_string();

        // Memory info
        let mut pmc: PROCESS_MEMORY_COUNTERS = Default::default();
        GetProcessMemoryInfo(
            handle,
            &mut pmc,
            std::mem::size_of::<PROCESS_MEMORY_COUNTERS>() as u32,
        )
        .ok()?;

        let memory_mb = pmc.WorkingSetSize as f64 / (1024.0 * 1024.0);

        // Thread count & priority
        let priority = "normal".to_string();
        let _tc: u32 = 0;

        let _ = CloseHandle(handle);

        Some(ProcessInfo {
            pid,
            name: file_name,
            cpu_percent: 0.0,
            memory_mb,
            thread_count: 0,
            priority,
        })
    }
}

pub fn limit_process(pid: u32, config: &ProcessLimitConfig) -> Result<String, String> {
    let mut methods = Vec::new();

    unsafe {
        let handle = OpenProcess(
            PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION | PROCESS_TERMINATE,
            false,
            pid,
        )
        .map_err(|e| format!("OpenProcess failed: {}", e))?;

        // IO Priority
        if let Some(io_prio) = config.io_priority {
            let ntdll = GetModuleHandleA(
                windows::core::s!("ntdll.dll"),
            )
            .map_err(|e| format!("GetModuleHandle failed: {}", e))?;

            let nt_set_info: extern "system" fn(
                HANDLE, u32, *const std::ffi::c_void, u32,
            ) -> i32 = {
                let raw_addr = GetProcAddress(
                    ntdll,
                    windows::core::s!("NtSetInformationProcess"),
                );
                let addr = match raw_addr {
                    Some(a) => a,
                    None => return Err("NtSetInformationProcess not found".to_string()),
                };
                std::mem::transmute(addr)
            };

            let priority_val = io_prio as i32;
            let result = nt_set_info(
                handle,
                33, // ProcessIoPriority
                &priority_val as *const _ as *const std::ffi::c_void,
                4,  // sizeof(i32)
            );

            if result == 0 {
                methods.push("IO_Priority");
            } else {
                log::warn!("NtSetInformationProcess IO priority failed: {}", result);
                // Fallback: SetPriorityClass
                let _ = SetPriorityClass(handle, IDLE_PRIORITY_CLASS);
                methods.push("IO_Priority(fallback)");
            }
        }

        // CPU Priority
        if let Some(ref cpu_prio) = config.cpu_priority {
            let prio_class = match cpu_prio.as_str() {
                "IDLE" => IDLE_PRIORITY_CLASS,
                "BELOW_NORMAL" => BELOW_NORMAL_PRIORITY_CLASS,
                "NORMAL" => NORMAL_PRIORITY_CLASS,
                "HIGH" => HIGH_PRIORITY_CLASS,
                "REALTIME" => REALTIME_PRIORITY_CLASS,
                _ => NORMAL_PRIORITY_CLASS,
            };
            let _ = SetPriorityClass(handle, prio_class);
            methods.push("CPU_Priority");
        }

        // CPU Affinity (via SetPriorityClass fallback)
        // SetProcessAffinityMask not directly available, using priority class only
        if let Some(_cores) = config.max_cores {
            let _ = SetPriorityClass(handle, IDLE_PRIORITY_CLASS);
            methods.push("CPU_Affinity(fallback)");
        }

        let _ = CloseHandle(handle);
    }

    if methods.is_empty() {
        return Err("No actions configured".into());
    }

    Ok(methods.join("+"))
}
