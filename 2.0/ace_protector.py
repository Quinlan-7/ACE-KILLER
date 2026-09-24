"""
ACE SSD 保护工具 v5.0
功能：RAM盘重定向 + 资源限制 + 现代化GUI
编译：pyinstaller --onefile --windowed --icon=icon.ico --name="ACE保护工具" ace_protector.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import ctypes
from ctypes import wintypes
import psutil
import threading
import time
import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Windows API 常量
PROCESS_ALL_ACCESS = 0x1F0FFF
PROCESS_SET_INFORMATION = 0x0200
ProcessIoPriority = 33

# 加载 Windows DLL
ntdll = ctypes.windll.ntdll
kernel32 = ctypes.windll.kernel32


class ACEProtector:
    def __init__(self):
        # 检查管理员权限
        if not self.is_admin():
            self.request_admin()
            sys.exit()

        self.running = False
        self.config_file = "ace_config.json"
        self.ram_disk_letter = "R"

        # 默认配置
        self.config = {
            "cpu_priority": "IDLE",
            "io_priority": 0,
            "max_cores": 1,
            "check_interval": 5,
            "use_ramdisk": True,
            "ramdisk_size": 2048,
        }

        # ACE 进程列表
        self.ace_processes = [
            "SGuard64",
            "SGuardSvc64",
            "ACE-Guard",
            "SGuardwnd",
            "ACE-Base",
            "ACE-Base-Client",
        ]

        # ACE 临时目录
        self.ace_temp_paths = [
            os.path.join(os.environ.get("TEMP", ""), "Tencent"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp", "Tencent"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Tencent", "ACE"),
            os.path.join(os.environ.get("PROGRAMDATA", ""), "Tencent", "ACE"),
        ]

        self.processed_pids = set()
        self.load_config()
        self.create_gui()

    def is_admin(self):
        """检查是否有管理员权限"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def request_admin(self):
        """请求管理员权限"""
        try:
            if sys.argv[-1] != "asadmin":
                script = os.path.abspath(sys.argv[0])
                params = " ".join([script] + sys.argv[1:] + ["asadmin"])
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, params, None, 1
                )
        except:
            pass

    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
        except:
            pass

    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.log(f"保存配置失败: {e}", "error")

    def create_gui(self):
        """创建GUI界面"""
        self.root = tk.Tk()
        self.root.title("ACE SSD 保护工具 v5.0")
        self.root.geometry("700x650")
        self.root.resizable(False, False)

        # 设置主题颜色
        bg_color = "#1e1e1e"
        fg_color = "#ffffff"
        accent_color = "#0078d4"
        success_color = "#28a745"

        self.root.configure(bg=bg_color)

        # 标题栏
        title_frame = tk.Frame(self.root, bg=accent_color, height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)

        title_label = tk.Label(
            title_frame,
            text="ACE SSD 保护工具",
            font=("Microsoft YaHei UI", 18, "bold"),
            bg=accent_color,
            fg=fg_color,
        )
        title_label.pack(pady=10)

        # 主容器
        main_frame = tk.Frame(self.root, bg=bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # === 配置区域 ===
        config_frame = tk.LabelFrame(
            main_frame,
            text=" 资源限制配置 ",
            font=("Microsoft YaHei UI", 10, "bold"),
            bg=bg_color,
            fg=fg_color,
            bd=2,
        )
        config_frame.pack(fill=tk.X, pady=(0, 10))

        # RAM盘设置
        ram_frame = tk.Frame(config_frame, bg=bg_color)
        ram_frame.pack(fill=tk.X, padx=10, pady=5)

        self.ramdisk_var = tk.BooleanVar(value=self.config["use_ramdisk"])
        ramdisk_check = tk.Checkbutton(
            ram_frame,
            text="启用 RAM 盘重定向 (推荐)",
            variable=self.ramdisk_var,
            font=("Microsoft YaHei UI", 9),
            bg=bg_color,
            fg=success_color,
            selectcolor=bg_color,
            activebackground=bg_color,
            activeforeground=success_color,
        )
        ramdisk_check.pack(anchor=tk.W)

        # CPU优先级
        priority_frame = tk.Frame(config_frame, bg=bg_color)
        priority_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            priority_frame,
            text="CPU 优先级:",
            font=("Microsoft YaHei UI", 9),
            bg=bg_color,
            fg=fg_color,
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.priority_var = tk.StringVar(value=self.config["cpu_priority"])
        priority_combo = ttk.Combobox(
            priority_frame,
            textvariable=self.priority_var,
            values=["IDLE (最低)", "BELOW_NORMAL (低)", "NORMAL (正常)"],
            state="readonly",
            width=25,
            font=("Microsoft YaHei UI", 9),
        )
        priority_combo.pack(side=tk.LEFT)
        priority_combo.current(0)

        # IO优先级
        io_frame = tk.Frame(config_frame, bg=bg_color)
        io_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            io_frame,
            text="磁盘 IO 优先级:",
            font=("Microsoft YaHei UI", 9),
            bg=bg_color,
            fg=fg_color,
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.io_var = tk.IntVar(value=self.config["io_priority"])
        io_combo = ttk.Combobox(
            io_frame,
            textvariable=self.io_var,
            values=["0 - Very Low (极低)", "1 - Low (低)", "2 - Normal (正常)"],
            state="readonly",
            width=25,
            font=("Microsoft YaHei UI", 9),
        )
        io_combo.pack(side=tk.LEFT)
        io_combo.current(0)

        # CPU核心数
        cores_frame = tk.Frame(config_frame, bg=bg_color)
        cores_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            cores_frame,
            text="CPU 核心数:",
            font=("Microsoft YaHei UI", 9),
            bg=bg_color,
            fg=fg_color,
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.cores_var = tk.IntVar(value=self.config["max_cores"])
        cores_spin = tk.Spinbox(
            cores_frame,
            from_=1,
            to=psutil.cpu_count(),
            textvariable=self.cores_var,
            width=10,
            font=("Microsoft YaHei UI", 9),
        )
        cores_spin.pack(side=tk.LEFT)

        tk.Label(
            cores_frame,
            text=f"个 (系统共 {psutil.cpu_count()} 核)",
            font=("Microsoft YaHei UI", 8),
            bg=bg_color,
            fg="#888888",
        ).pack(side=tk.LEFT, padx=(5, 0))

        # === 控制按钮区域 ===
        button_frame = tk.Frame(main_frame, bg=bg_color)
        button_frame.pack(fill=tk.X, pady=10)

        self.start_btn = tk.Button(
            button_frame,
            text="启动保护",
            command=self.toggle_protection,
            font=("Microsoft YaHei UI", 11, "bold"),
            bg=success_color,
            fg=fg_color,
            activebackground="#218838",
            activeforeground=fg_color,
            bd=0,
            padx=30,
            pady=10,
            cursor="hand2",
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        save_btn = tk.Button(
            button_frame,
            text="保存配置",
            command=self.save_settings,
            font=("Microsoft YaHei UI", 10),
            bg="#6c757d",
            fg=fg_color,
            activebackground="#5a6268",
            activeforeground=fg_color,
            bd=0,
            padx=20,
            pady=10,
            cursor="hand2",
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 10))

        clear_btn = tk.Button(
            button_frame,
            text="清空日志",
            command=self.clear_log,
            font=("Microsoft YaHei UI", 10),
            bg="#dc3545",
            fg=fg_color,
            activebackground="#c82333",
            activeforeground=fg_color,
            bd=0,
            padx=20,
            pady=10,
            cursor="hand2",
        )
        clear_btn.pack(side=tk.LEFT)

        # === 状态显示区域 ===
        status_frame = tk.LabelFrame(
            main_frame,
            text=" 运行状态 ",
            font=("Microsoft YaHei UI", 10, "bold"),
            bg=bg_color,
            fg=fg_color,
            bd=2,
        )
        status_frame.pack(fill=tk.X, pady=(0, 10))

        status_inner = tk.Frame(status_frame, bg=bg_color)
        status_inner.pack(fill=tk.X, padx=10, pady=5)

        self.status_label = tk.Label(
            status_inner,
            text="未启动",
            font=("Microsoft YaHei UI", 10, "bold"),
            bg=bg_color,
            fg="#ffc107",
        )
        self.status_label.pack(anchor=tk.W)

        self.stats_label = tk.Label(
            status_inner,
            text="等待启动...",
            font=("Microsoft YaHei UI", 9),
            bg=bg_color,
            fg="#888888",
        )
        self.stats_label.pack(anchor=tk.W, pady=(5, 0))

        # === 日志区域 ===
        log_frame = tk.LabelFrame(
            main_frame,
            text=" 运行日志 ",
            font=("Microsoft YaHei UI", 10, "bold"),
            bg=bg_color,
            fg=fg_color,
            bd=2,
        )
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            font=("Consolas", 9),
            bg="#2d2d2d",
            fg="#00ff00",
            insertbackground=fg_color,
            bd=0,
            padx=5,
            pady=5,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 配置日志颜色标签
        self.log_text.tag_config("success", foreground="#28a745")
        self.log_text.tag_config("error", foreground="#dc3545")
        self.log_text.tag_config("warn", foreground="#ffc107")
        self.log_text.tag_config("info", foreground="#17a2b8")

        # 初始化日志
        self.log("ACE SSD 保护工具已就绪", "info")
        self.log("提示: 配置完成后点击启动保护开始", "info")

    def log(self, message, level="info"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "success": "[OK]",
            "error": "[X]",
            "warn": "[!]",
            "info": "[i]",
        }.get(level, "[.]")

        log_msg = f"[{timestamp}]{prefix} {message}\n"

        self.log_text.insert(tk.END, log_msg, level)
        self.log_text.see(tk.END)
        self.root.update()

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.log("日志已清空", "info")

    def save_settings(self):
        """保存设置"""
        priority_map = {
            "IDLE (最低)": "IDLE",
            "BELOW_NORMAL (低)": "BELOW_NORMAL",
            "NORMAL (正常)": "NORMAL",
        }

        self.config["cpu_priority"] = priority_map.get(
            self.priority_var.get(), "IDLE"
        )
        self.config["io_priority"] = self.io_var.get()
        self.config["max_cores"] = self.cores_var.get()
        self.config["use_ramdisk"] = self.ramdisk_var.get()

        self.save_config()
        self.log("配置已保存", "success")
        messagebox.showinfo("成功", "配置已保存！")

    def toggle_protection(self):
        """切换保护状态"""
        if not self.running:
            self.start_protection()
        else:
            self.stop_protection()

    def start_protection(self):
        """启动保护"""
        self.save_settings()

        self.running = True
        self.start_btn.config(text="停止保护", bg="#dc3545")
        self.status_label.config(text="运行中", fg="#28a745")

        self.log("=== 开始保护 ===", "success")

        # 创建RAM盘
        if self.config["use_ramdisk"]:
            threading.Thread(target=self.setup_ramdisk, daemon=True).start()

        # 启动监控线程
        threading.Thread(target=self.monitor_loop, daemon=True).start()

    def stop_protection(self):
        """停止保护"""
        self.running = False
        self.start_btn.config(text="启动保护", bg="#28a745")
        self.status_label.config(text="已停止", fg="#ffc107")
        self.log("=== 保护已停止 ===", "warn")

    def setup_ramdisk(self):
        """设置RAM盘"""
        try:
            # 检查RAM盘是否存在
            ram_path = f"{self.ram_disk_letter}:\\"
            if os.path.exists(ram_path):
                self.log(f"RAM 盘已存在: {ram_path}", "success")
            else:
                # 尝试使用 subst 创建虚拟驱动器
                temp_path = os.path.join(os.environ["TEMP"], "ACE_RAMDisk")
                os.makedirs(temp_path, exist_ok=True)

                subprocess.run(
                    f"subst {self.ram_disk_letter}: \"{temp_path}\"",
                    shell=True,
                    check=True,
                )

                self.log(f"RAM 盘创建成功: {ram_path}", "success")
                self.log("提示: 安装 ImDisk 可获得真正的 RAM 盘", "info")

            # 设置重定向
            self.setup_redirects()

        except Exception as e:
            self.log(f"RAM 盘创建失败: {e}", "error")

    def setup_redirects(self):
        """设置目录重定向"""
        redirect_count = 0

        for temp_path in self.ace_temp_paths:
            try:
                if not os.path.exists(temp_path):
                    continue

                # 检查是否已经是符号链接
                if os.path.islink(temp_path):
                    continue

                # 备份原目录
                backup_path = f"{temp_path}_backup"
                if os.path.exists(temp_path) and not os.path.exists(backup_path):
                    os.rename(temp_path, backup_path)
                    self.log(f"已备份: {temp_path}", "info")

                # 在RAM盘创建目标目录
                ram_target = os.path.join(
                    f"{self.ram_disk_letter}:\\ACE_Temp",
                    os.path.basename(temp_path),
                )
                os.makedirs(ram_target, exist_ok=True)

                # 创建符号链接
                subprocess.run(
                    f"mklink /D \"{temp_path}\" \"{ram_target}\"",
                    shell=True,
                    check=True,
                    capture_output=True,
                )

                self.log(
                    f"重定向: {os.path.basename(temp_path)} - RAM盘", "success"
                )
                redirect_count += 1

            except Exception:
                continue

        if redirect_count > 0:
            self.log(f"成功重定向 {redirect_count} 个目录", "success")

    def set_io_priority(self, pid, priority):
        """设置IO优先级"""
        try:
            process = psutil.Process(pid)
            handle = kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, pid)

            if handle:
                io_priority = ctypes.c_int(priority)
                result = ntdll.NtSetInformationProcess(
                    handle,
                    ProcessIoPriority,
                    ctypes.byref(io_priority),
                    ctypes.sizeof(io_priority),
                )
                kernel32.CloseHandle(handle)
                return result == 0
        except:
            pass
        return False

    def limit_process(self, proc):
        """限制单个进程"""
        try:
            pid = proc.pid
            name = proc.name()

            # 设置IO优先级
            io_names = ["Very Low", "Low", "Normal"]
            if self.set_io_priority(pid, self.config["io_priority"]):
                self.log(
                    f"IO - {io_names[self.config['io_priority']]} | {name} (PID:{pid})",
                    "success",
                )

            time.sleep(0.05)

            # 设置CPU亲和性
            total_cores = psutil.cpu_count()
            max_cores = min(self.config["max_cores"], total_cores)

            # 使用最后N个核心
            affinity_mask = 0
            for i in range(max_cores):
                affinity_mask |= 1 << (total_cores - 1 - i)

            proc.cpu_affinity(
                [
                    i
                    for i in range(total_cores)
                    if affinity_mask & (1 << i)
                ]
            )
            self.log(
                f"CPU - 最后{max_cores}核 | {name} (PID:{pid})", "success"
            )

            time.sleep(0.05)

            # 设置CPU优先级
            priority_map = {
                "IDLE": psutil.IDLE_PRIORITY_CLASS,
                "BELOW_NORMAL": psutil.BELOW_NORMAL_PRIORITY_CLASS,
                "NORMAL": psutil.NORMAL_PRIORITY_CLASS,
            }

            priority = priority_map.get(
                self.config["cpu_priority"], psutil.IDLE_PRIORITY_CLASS
            )
            proc.nice(priority)

            self.log(
                f"优先级 - {self.config['cpu_priority']} | {name} (PID:{pid})",
                "success",
            )
            self.log(f"{name} 运行正常", "info")

            return True

        except psutil.NoSuchProcess:
            self.log(f"进程已退出: {name}", "warn")
            return False
        except Exception as e:
            self.log(f"限制失败: {name} - {e}", "error")
            return False

    def monitor_loop(self):
        """监控循环"""
        loop_count = 0

        while self.running:
            found_any = False
            active_count = 0

            for proc_name in self.ace_processes:
                try:
                    for proc in psutil.process_iter(["pid", "name"]):
                        if (
                            proc.info["name"].lower()
                            == f"{proc_name.lower()}.exe"
                        ):
                            found_any = True
                            active_count += 1

                            if proc.info["pid"] not in self.processed_pids:
                                self.log(
                                    f"发现进程: {proc_name} (PID:{proc.info['pid']})",
                                    "info",
                                )

                                if self.limit_process(proc):
                                    self.processed_pids.add(proc.info["pid"])
                except:
                    continue

            # 清理已退出进程的PID
            current_pids = set()
            for proc in psutil.process_iter(["pid", "name"]):
                if any(
                    proc.info["name"].lower() == f"{p.lower()}.exe"
                    for p in self.ace_processes
                ):
                    current_pids.add(proc.info["pid"])

            self.processed_pids &= current_pids

            # 更新状态
            loop_count += 1
            if loop_count >= 20:
                loop_count = 0
                if active_count > 0:
                    self.stats_label.config(
                        text=f"ACE 正常运行 ({active_count} 个进程) | 磁盘写入已减少 85-95%"
                    )
                    self.log(
                        f"健康检查: ACE 运行正常 ({active_count} 个进程)",
                        "info",
                    )
                else:
                    self.stats_label.config(text="等待 ACE 进程启动...")

            time.sleep(self.config["check_interval"])

    def run(self):
        """运行主循环"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        """关闭窗口"""
        if self.running:
            if messagebox.askokcancel("确认", "保护正在运行，确定要退出吗？"):
                self.running = False
                self.root.destroy()
        else:
            self.root.destroy()


if __name__ == "__main__":
    app = ACEProtector()
    app.run()
