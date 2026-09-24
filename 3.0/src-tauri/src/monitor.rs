use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use log;

#[allow(dead_code)]
pub struct ProcessMonitor {
    running: Arc<Mutex<bool>>,
    watch_list: Vec<String>,
    thread: Option<thread::JoinHandle<()>>,
}

#[allow(dead_code)]
impl ProcessMonitor {
    pub fn new() -> Self {
        Self {
            running: Arc::new(Mutex::new(false)),
            watch_list: vec![
                "SGuard64.exe".into(),
                "ACE-Tray.exe".into(),
                "ACE-Guard.exe".into(),
                "SGuardSvc64.exe".into(),
                "ACE-Base.exe".into(),
                "ACE-Base-Client.exe".into(),
            ],
            thread: None,
        }
    }

    pub fn start(&mut self) {
        let running = self.running.clone();
        let watch_list = self.watch_list.clone();

        *running.lock().unwrap() = true;
        log::info!("Process monitor started");

        self.thread = Some(thread::spawn(move || {
            while *running.lock().unwrap() {
                // Poll process list
                if let Ok(processes) = crate::process::list_processes() {
                    for proc in &processes {
                        if watch_list.iter().any(|w| w.eq_ignore_ascii_case(&proc.name)) {
                            log::debug!("Watched process running: {} (PID:{})", proc.name, proc.pid);
                        }
                    }
                }
                thread::sleep(Duration::from_secs(5));
            }
        }));
    }

    pub fn stop(&mut self) {
        *self.running.lock().unwrap() = false;
        log::info!("Process monitor stopped");
    }

    pub fn add_watch(&mut self, name: &str) {
        if !self.watch_list.iter().any(|w| w.eq_ignore_ascii_case(name)) {
            self.watch_list.push(name.into());
        }
    }
}
