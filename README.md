<div align="center">

# ACE-KILLER

✨ _游戏反作弊进程资源管理 / 游戏优化工具 - ACE SSD 保护 | RAM 盘重定向 | 内存清理_ ✨

<div>
    <img alt="platform" src="https://img.shields.io/badge/Platform-Windows-blue?style=flat-square&logo=windows">
    <img alt="python" src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python&logoColor=white">
    <img alt="license" src="https://img.shields.io/badge/License-GPL--3.0-green?style=flat-square&logo=gnu">
    <img alt="version" src="https://img.shields.io/badge/Version-2.2.0-orange?style=flat-square">
</div>

<br/>

> 本项目用于管理 ACE 反作弊进程的**资源占用**（优先级 / 核心绑定 / 效能模式），
> 优化系统资源分配，减少 SSD 写入损伤，**不干扰反作弊检测逻辑**。

</div>

---

## 项目版本

| 版本 | 目录 | 说明 |
|------|------|------|
| **v2.2.2** | [2.0/](2.0/) | 最新版 - 精简界面（移除进程规则/场景预设/游戏模式）；默认不终止 ACE-Tray 修复游戏进不去；深色常驻；AMD 效能核绑定、强制开机自启 |
| **v2.2.1** | [2.0/](2.0/) | 一键游戏模式、拓扑感知效能核绑定、AMD 平台优化、强制开机自启；修复 SignalBus 崩溃、向导重复弹出、计划任务解码 BUG |
| **v2.1** | [2.0/](2.0/) | 线程安全修复、共享常量模块、单元测试 |
| **v1.0** | [1.0/](1.0/) | 稳定版 - 进程监控、内存清理、IO 优先级管理、RAM 盘重定向 |

## 编译产物

通过 [GitHub Actions](https://github.com/Quinlan-7/ACE-KILLER/actions) 构建，发布版本见 [GitHub Releases](https://github.com/Quinlan-7/ACE-KILLER/releases)。

## 功能特性

- 🛡️ 自动关闭 ACE-Tray.exe 反作弊安装弹窗（可配置）
- 🚀 自动优化 SGuard64.exe 扫盘进程，降低 CPU 占用
- 🧠 **拓扑感知效能核心绑定**：AMD 绑定最后一个物理核心，Intel 混合架构绑定能效核（E-core）
- 🎮 **一键游戏模式**：电源方案 / GameDVR / 内存清理 / ACE 进程优化，一键启用、一键还原
- 🔥 **AMD CPU/GPU 自动识别与平台兼容优化**
- 💪 **强制开机自启动**：启动快捷方式 + 最高权限计划任务双通道
- 💾 RAM 盘重定向减少 SSD 磁盘损伤
- 🧹 内存清理（工作集/系统缓存/备用列表）
- 🔧 进程 IO 优先级和性能模式管理
- 🌓 Ant Design 风格明暗主题切换
- 📱 Windows 系统通知
- 💻 系统托盘常驻运行

## 注意事项

- 本程序需要**管理员权限**运行
- 使用过程中如遇问题，日志文件位于 `%USERPROFILE%\.ace-killer\logs\`

## 联系 & 讨论

- 💬 **项目主页**: [https://github.com/Quinlan-7/ACE-KILLER](https://github.com/Quinlan-7/ACE-KILLER)
- 📧 邮箱: 704979478@qq.com

## 许可证

- **GNU General Public License v3.0** - 详见 [LICENSE](LICENSE)
