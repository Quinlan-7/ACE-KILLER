<div align="center">

# ACE-KILLER

<img src="https://socialify.git.ci/Quinlan-7/ACE-KILLER/image?font=Jost&forks=1&issues=1&name=1&pattern=Plus&stargazers=1&theme=Dark" alt="ACE-KILLER" width="640" height="320" />

✨ _游戏反作弊进程资源管理 / 游戏优化工具，专为无畏契约、三角洲行动等使用 ACE 反作弊的游戏设计_ ✨

<!-- 项目状态徽章 -->
<div>
    <img alt="platform" src="https://img.shields.io/badge/Platform-Windows-blue?style=flat-square&logo=windows">
    <img alt="python" src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python&logoColor=white">
    <img alt="license" src="https://img.shields.io/badge/License-GPL--3.0-green?style=flat-square&logo=gnu">
    <img alt="version" src="https://img.shields.io/badge/version-2.2.0-orange?style=flat-square&logo=github">
</div>
<br/>


<div align="left">

> ## ⚠️ 重要声明
> 🚨 本项目所有代码均通过**标准Windows API和脚本实现**  
> 🔒 不涉及**任何反作弊内核修改、注入或破解**，仅对进程资源进行合理管理  
> ⚖️ 所有功能基于Windows系统标准权限管理，**未使用任何第三方破解工具**  
> 🎯 本项目仅优化系统资源分配，**不干扰反作弊程序的正常检测逻辑，所有操作均合理合法**  
> **❗ 最后，如果您因使用本工具而遇到任何被检测的问题，请优先检查自己是否使用了其他可能导致封号的软件！**

</div>
</div>

**📦 v2.2.3 更新**：新增「启动自动创建 RAM 盘」——RAM 盘开关开启后，程序每次启动自动创建（ImDisk 优先，subst 回退），无需手动点击。

## ✅ 功能特性

- 🛡️ 自动关闭`ACE-Tray.exe`反作弊安装询问弹窗（可配置关闭）
- 🚀 自动优化`SGuard64.exe`扫盘进程，降低 CPU 占用
- 🧠 **拓扑感知效能核心绑定**（v2.2）：AMD 平台自动绑定最后一个物理核心，Intel 混合架构自动绑定能效核（E-core）
- 🎮 **一键游戏模式**（v2.2）：电源方案 / GameDVR / 内存清理 / ACE 进程优化一键完成，可随时还原
- 🔥 **AMD CPU/GPU 平台兼容优化**（v2.2）：自动识别 AMD 硬件并启用针对性优化
- 💪 **强制开机自启动**（v2.2）：启动快捷方式 + 最高权限计划任务双通道，登录即自动运行
- 🗑️ 支持一键启动/停止反作弊进程，卸载/删除 ACE 反作弊服务
- 🐻 支持自定义进程性能模式
- 🧹 内存清理根据作者`H3d9`编写的 [Memory Cleaner](https://github.com/H3d9/memory_cleaner) 进行重构
- 📱 支持 Windows 系统通知
- 🔄 支持开机静默自启
- 💻 系统托盘常驻运行
- 🌓 支持明暗主题切换

## 🚀 如何使用

1. [点击下载最新版本.zip压缩包](https://github.com/Quinlan-7/ACE-KILLER) 👈
2. 解压后运行`ACE-KILLER.exe`
3. 程序将在系统托盘显示图标
4. 右键点击托盘图标可以：
   - 👁️ 查看程序状态
   - 🎮 一键切换游戏模式
   - 🔔 启用/禁用 Windows 通知
   - 🔄 设置开机自启动
   - ⚙️ 配置游戏监控
   - 📁 打开配置目录
   - 🚪 退出程序

## 🎮 一键游戏模式（v2.2）

进入游戏模式自动完成以下优化，退出时一键还原：

| 优化项 | 说明 |
| ------ | ---- |
| 电源方案 | 优先启用「卓越性能」，否则「高性能」，退出时恢复原方案 |
| GameDVR | 关闭后台录制，减少磁盘与性能开销，退出时恢复 |
| 内存清理 | 清理一次工作集/系统缓存，释放可用内存 |
| ACE 进程优化 | 将反作弊相关进程切换为效能模式（低优先级 + 效能核绑定） |

## ⚙️ 强制开机自启动（v2.2）

- 默认开启，首次运行即自动生效
- 双通道保障：
  1. 启动文件夹快捷方式（`--minimized` 最小化启动）
  2. **计划任务**（最高权限，登录即运行，不易被清理）
- 可在「设置 → 启动设置」中切换普通/强制模式

## 😶‍🌫️ 进程模式策略

| 性能模式    | CPU 优先级             | 效能节流     | CPU 核心绑定   |
| ----------- | ---------------------- | ------------ | ------------ |
| 🌱 效能模式 | 低优先级(IDLE)         | 启用节流     | 效能核心（拓扑感知） |
| 🍉 正常模式 | **正常优先级(NORMAL)** | **禁用节流** | 所有核心     |
| 🚀 高性能   | 高优先级(HIGH)         | 禁用节流     | 所有核心     |
| 🔥 最大性能 | 实时优先级(REALTIME)   | 禁用节流     | 所有核心     |

> 💡 v2.2 起「效能模式」不再简单绑定“最后一个逻辑核”，而是：
> - **AMD CPU**：绑定最后一个物理核心的首个线程（SMT 场景下最大限度让出主核）
> - **Intel 混合架构**：绑定能效核（E-core）

## ⚙️ ACE Services 说明

- **AntiCheatExpert Service**：用户模式，由 `SvGuard64.exe` 控制的游戏交互的服务，也是在服务概览 (services.msc) 中看到的唯一服务
- **AntiCheatExpert Protection**：反作弊组件
- **ACE-BASE**：内核模式，加载系统驱动程序
- **ACE-GAME**：内核模式，加载系统驱动程序

## ⚠️ 注意事项

- 本程序需要管理员权限运行
- 使用过程中如遇到问题，日志文件位于 `%USERPROFILE%\.ace-killer\logs\` 目录

## 📢 免责声明

- **本项目仅供个人学习和研究使用，禁止用于任何商业或非法目的。**
- **开发者保留对本项目的最终解释权。**
- **使用者在使用本项目时，必须严格遵守 `中华人民共和国（含台湾省）` 以及使用者所在地区的法律法规。禁止将本项目用于任何违反相关法律法规的活动。**
- **使用者应自行承担因使用本项目所产生的任何风险和责任。开发者不对因使用本项目而导致的任何直接或间接损失承担责任。**
- **开发者不对本项目所提供的服务或内容的准确性、完整性或适用性作出任何明示或暗示的保证。使用者应自行评估使用本项目的风险。**
- **若使用者发现任何商家或第三方以本项目进行收费或从事其他商业行为，所产生的任何问题或后果与本项目及开发者无关。使用者应自行承担相关风险。**

## 📜 许可证

- **本项目采用 `GNU General Public License v3.0`** - 详见 [LICENSE](LICENSE) 文件

## 📬 联系 & 讨论

- 💬 **项目主页**: [https://github.com/Quinlan-7/ACE-KILLER](https://github.com/Quinlan-7/ACE-KILLER)
- 📧 邮箱: 704979478@qq.com
