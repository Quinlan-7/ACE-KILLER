use std::process::Command;

pub fn detect_imdisk() -> bool {
    // Check if imdisk.exe is available
    Command::new("where")
        .args(["imdisk.exe"])
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

pub fn setup_ramdisk(letter: &str, size_mb: u32) -> Result<String, String> {
    let ram_path = format!("{}:\\", letter);

    // Check if already exists
    if std::path::Path::new(&ram_path).exists() {
        return Ok(format!("RAM disk already exists: {}", ram_path));
    }

    // Try ImDisk first
    if detect_imdisk() {
        let output = Command::new("imdisk")
            .args([
                "-a",
                "-s",
                &format!("{}M", size_mb),
                "-m",
                &format!("{}:", letter),
                "-p",
                "/fs:ntfs /q /y /v:ACE_RAMDISK",
            ])
            .output()
            .map_err(|e| format!("ImDisk failed: {}", e))?;

        if output.status.success() {
            return Ok(format!("ImDisk RAM disk created: {}: ({}MB)", letter, size_mb));
        }
        log::warn!("ImDisk failed, falling back to subst");
    }

    // Fallback to subst
    let temp_path = format!(
        "{}\\ACE_RAMDisk",
        std::env::var("TEMP").unwrap_or_else(|_| "C:\\Temp".into())
    );
    std::fs::create_dir_all(&temp_path).map_err(|e| format!("create_dir failed: {}", e))?;

    let output = Command::new("cmd")
        .args(["/C", &format!("subst {}: \"{}\"", letter, temp_path)])
        .output()
        .map_err(|e| format!("subst failed: {}", e))?;

    if output.status.success() {
        Ok(format!("Virtual drive created: {}: -> {}", letter, temp_path))
    } else {
        Err("subst command failed".into())
    }
}

pub fn cleanup_ramdisk(letter: &str) -> Result<String, String> {
    // Remove subst drive
    Command::new("cmd")
        .args(["/C", &format!("subst {}: /D", letter)])
        .output()
        .ok();

    // If ImDisk was used, try to remove it
    if detect_imdisk() {
        Command::new("imdisk")
            .args(["-D", "-m", &format!("{}:", letter)])
            .output()
            .ok();
    }

    Ok(format!("RAM disk {}: cleaned up", letter))
}

pub fn get_ramdisk_info(letter: &str) -> Result<serde_json::Value, String> {
    let ram_path = format!("{}:\\", letter);
    let exists = std::path::Path::new(&ram_path).exists();

    if !exists {
        return Ok(serde_json::json!({
            "exists": false,
            "total_gb": 0,
            "free_gb": 0,
            "used_gb": 0,
        }));
    }

    unsafe {
        let path: Vec<u16> = ram_path.encode_utf16().collect();
        let mut free_bytes: u64 = 0;
        let mut total_bytes: u64 = 0;
        let mut total_free: u64 = 0;

        let result = windows::Win32::Storage::FileSystem::GetDiskFreeSpaceExW(
            windows::core::PCWSTR::from_raw(path.as_ptr()),
            Some(&mut free_bytes),
            Some(&mut total_bytes),
            Some(&mut total_free),
        );

        match result {
            Ok(_) => Ok(serde_json::json!({
                "exists": true,
                "total_gb": (total_bytes as f64 / (1024.0 * 1024.0 * 1024.0) * 10.0).round() / 10.0,
                "free_gb": (free_bytes as f64 / (1024.0 * 1024.0 * 1024.0) * 10.0).round() / 10.0,
                "used_gb": ((total_bytes - free_bytes) as f64 / (1024.0 * 1024.0 * 1024.0) * 10.0).round() / 10.0,
            })),
            Err(e) => Ok(serde_json::json!({
                "exists": true,
                "error": format!("{:?}", e),
            })),
        }
    }
}
