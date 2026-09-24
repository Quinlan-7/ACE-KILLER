# -*- mode: python ; coding: utf-8 -*-
# ACE-KILLER v2.2.0 PyInstaller 构建配置
# 用法: pyinstaller --noconfirm ACE-KILLER.spec

import os

from PySide6.QtCore import QLibraryInfo
from PyInstaller.utils.hooks import collect_submodules, collect_dynamic_libs, collect_data_files

project_root = os.path.abspath(SPECPATH)
icon_path = os.path.join(project_root, "assets", "icon", "favicon.ico")

# winrt 系列为 Windows 通知依赖（windows_toasts 惰性导入，需显式收集）
winrt_hidden = collect_submodules("winrt")
winrt_bins = collect_dynamic_libs("winrt")
toast_data = collect_data_files("windows_toasts")

hiddenimports = (
    ["windows_toasts"]
    + winrt_hidden
    + [
        "winrt",
        "winrt.runtime",
        "winrt.windows.foundation",
        "winrt.windows.foundation.collections",
        "winrt.windows.data.xml.dom",
        "winrt.windows.ui.notifications",
    ]
)

datas = [
    # 图标资源目录（custom_titlebar 以 __file__ 推导根目录，QSS 相对路径 assets/icon/*）
    (os.path.join(project_root, "assets", "icon"), "assets/icon"),
    # favicon.ico 同时放到 EXE 同目录（utils.notification.find_icon_path 打包分支）
    (os.path.join(project_root, "assets", "icon", "favicon.ico"), "."),
] + winrt_bins + toast_data

a = Analysis(
    [os.path.join(project_root, "main.py")],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PIL.ImageTk", "matplotlib", "numpy"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ACE-KILLER",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
    uac_admin=True,          # 管理员权限清单（对应上游 --windows-uac-admin）
    uac_uiaccess=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ACE-KILLER",
)
