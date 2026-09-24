#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CI 构建日志抓取辅助工具（v2.2 清理版）
- 令牌改为从环境变量 GITHUB_TOKEN 读取，不再硬编码
- 仓库地址改为本仓库 Quinlan-7/ACE-KILLER
用法: python get_error_logs.py [RUN_ID]
"""
import json
import os
import re
import subprocess
import sys

TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not TOKEN:
    print("缺少 GITHUB_TOKEN 环境变量")
    sys.exit(1)

REPO = "Quinlan-7/ACE-KILLER"
RUN_ID = sys.argv[1] if len(sys.argv) > 1 else ""

# Get job ID
result = subprocess.run(
    ["curl.exe", "-s", f"https://api.github.com/repos/{REPO}/actions/runs/{RUN_ID}/jobs",
     "-H", f"Authorization: Bearer {TOKEN}"],
    capture_output=True
)
data = json.loads(result.stdout.decode("utf-8"))
jobs = data.get("jobs", [])
if not jobs:
    print("No jobs found")
    sys.exit(1)

job_id = jobs[0]["id"]
print(f"Job ID: {job_id}")

# Download logs
result = subprocess.run(
    ["curl.exe", "-sL", f"https://api.github.com/repos/{REPO}/actions/jobs/{job_id}/logs",
     "-H", f"Authorization: Bearer {TOKEN}"],
    capture_output=True
)
log_text = result.stdout.decode("utf-8", errors="replace")

# Find error lines WITH context
lines = log_text.split("\n")
for i, line in enumerate(lines):
    clean = re.sub(r'\x1b\[[0-9;]*m', '', line)
    if "error[" in clean:
        print(f"\n{'='*60}")
        print(clean)
        # Print next 8 lines for context
        for j in range(i+1, min(i+9, len(lines))):
            ctx_clean = re.sub(r'\x1b\[[0-9;]*m', '', lines[j])
            if ctx_clean.strip():
                print(ctx_clean)
    if "could not compile" in clean or "Error failed" in clean:
        print(f"\n{clean}")
