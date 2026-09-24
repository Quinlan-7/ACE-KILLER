const { invoke } = window.__TAURI__?.core || {};

// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
    });
});

// Init
async function init() {
    try {
        const status = await invoke('get_status');
        updateStatus(status);
        refreshProcesses();
        refreshMemory();
        refreshRamdisk();
        refreshRules();
        refreshProfiles();
        loadSettings();
    } catch (e) {
        console.error('Init failed:', e);
    }
}

// Status
function updateStatus(status) {
    const badge = document.getElementById('status-badge');
    const running = status?.running || false;
    badge.textContent = running ? '运行中' : '待机';
    badge.className = `badge ${running ? 'running' : 'idle'}`;
}

async function refreshStatus() {
    try {
        const status = await invoke('get_status');
        updateStatus(status);
        document.getElementById('s-monitor').textContent = status.monitor_enabled ? '已启用' : '已禁用';
        document.getElementById('s-memory').textContent = status.ramdisk_enabled ? '已启用' : '已禁用';
        const procs = await invoke('get_processes');
        document.getElementById('s-processes').textContent = `${procs.length} 个`;
    } catch (e) { console.error(e); }
}

// Processes
async function refreshProcesses() {
    try {
        const processes = await invoke('get_processes');
        const list = document.getElementById('process-list');
        const search = (document.getElementById('proc-search')?.value || '').toLowerCase();
        
        const filtered = processes.filter(p => p.name.toLowerCase().includes(search));
        list.innerHTML = filtered.slice(0, 100).map(p => `
            <div class="proc-item">
                <div>
                    <span class="proc-name">${escapeHtml(p.name)}</span>
                    <span class="proc-pid"> (PID: ${p.pid})</span>
                </div>
                <div>
                    <span class="proc-mem">${p.memory_mb.toFixed(1)} MB</span>
                    <button class="btn-sm" onclick="limitProcess(${p.pid}, '${escapeHtml(p.name)}')">限制</button>
                </div>
            </div>
        `).join('');
    } catch (e) { console.error(e); }
}

function filterProcesses() { refreshProcesses(); }

async function limitProcess(pid, name) {
    try {
        const config = JSON.stringify({
            io_priority: 0,
            cpu_priority: 'IDLE',
            max_cores: 1,
            power_throttling: true
        });
        const result = await invoke('limit_process', { pid, configJson: config });
        alert(`已限制 ${name} (PID:${pid})\n方法: ${result}`);
    } catch (e) {
        alert(`限制失败: ${e}`);
    }
}

// Memory
async function refreshMemory() {
    try {
        const info = await invoke('get_memory_info');
        const div = document.getElementById('memory-info');
        div.innerHTML = `
            <div class="mem-bar">
                <div class="mem-bar-fill" style="width: ${info.percent}%"></div>
            </div>
            <div class="status-grid">
                <div class="stat"><span class="stat-label">总计</span><span class="stat-value">${info.total_gb} GB</span></div>
                <div class="stat"><span class="stat-label">已用</span><span class="stat-value">${info.used_gb} GB (${info.percent}%)</span></div>
                <div class="stat"><span class="stat-label">可用</span><span class="stat-value">${info.available_gb} GB</span></div>
            </div>
        `;
    } catch (e) { console.error(e); }
}

async function cleanMemory() {
    try {
        const result = await invoke('clean_memory', { switches: [true, true, true, true, true, true] });
        alert(`内存清理完成: ${result}`);
        refreshMemory();
    } catch (e) {
        alert(`清理失败: ${e}`);
    }
}

// RAM Disk
async function refreshRamdisk() {
    try {
        const info = await invoke('get_ramdisk_info', { letter: 'R' });
        const div = document.getElementById('ramdisk-info');
        if (info.exists) {
            div.innerHTML = `
                <div class="status-grid">
                    <div class="stat"><span class="stat-label">状态</span><span class="stat-value" style="color:var(--success)">运行中</span></div>
                    <div class="stat"><span class="stat-label">总空间</span><span class="stat-value">${info.total_gb} GB</span></div>
                    <div class="stat"><span class="stat-label">已用</span><span class="stat-value">${info.used_gb} GB</span></div>
                    <div class="stat"><span class="stat-label">可用</span><span class="stat-value">${info.free_gb} GB</span></div>
                </div>
            `;
        } else {
            div.innerHTML = '<p style="color:var(--text2)">RAM盘未激活</p>';
        }
    } catch (e) { console.error(e); }
}

async function setupRamdisk() {
    try {
        const result = await invoke('setup_ramdisk', { letter: 'R', sizeMb: 2048 });
        alert(result);
        refreshRamdisk();
    } catch (e) {
        alert(`创建失败: ${e}`);
    }
}

async function cleanupRamdisk() {
    try {
        const result = await invoke('cleanup_ramdisk', { letter: 'R' });
        alert(result);
        refreshRamdisk();
    } catch (e) {
        alert(`清理失败: ${e}`);
    }
}

// Rules
async function refreshRules() {
    try {
        const rules = await invoke('get_rules');
        const list = document.getElementById('rules-list');
        list.innerHTML = rules.length === 0
            ? '<p style="color:var(--text2);padding:12px;">暂无规则，点击添加</p>'
            : rules.map(r => `
                <div class="rule-item">
                    <div>
                        <strong>${escapeHtml(r.name)}</strong>
                        <span style="color:var(--text2);font-size:12px;margin-left:8px">${escapeHtml(r.process_pattern)}</span>
                    </div>
                    <div>
                        <span style="color:${r.enabled ? 'var(--success)' : 'var(--text2)'}">${r.enabled ? '启用' : '禁用'}</span>
                        <button class="btn-sm" onclick="deleteRule('${escapeHtml(r.name)}')">删除</button>
                    </div>
                </div>
            `).join('');
    } catch (e) { console.error(e); }
}

function showAddRule() {
    const name = prompt('规则名称:');
    if (!name) return;
    const pattern = prompt('进程匹配模式 (如: SGuard64.exe):');
    if (!pattern) return;
    const rule = {
        name, process_pattern: pattern, match_type: 'exact',
        actions: [{ type: 'io_priority', value: 0 }, { type: 'cpu_priority', value: 'IDLE' }],
        enabled: true, description: '', created_at: new Date().toISOString()
    };
    invoke('add_rule', { ruleJson: JSON.stringify(rule) }).then(refreshRules);
}

async function deleteRule(name) {
    if (!confirm(`删除规则「${name}」?`)) return;
    await invoke('remove_rule', { name });
    refreshRules();
}

// Profiles
async function refreshProfiles() {
    try {
        const profiles = await invoke('get_profiles');
        const list = document.getElementById('profiles-list');
        list.innerHTML = profiles.length === 0
            ? '<p style="color:var(--text2);padding:12px;">暂无预设，点击添加</p>'
            : profiles.map(p => `
                <div class="profile-item">
                    <div>
                        <strong>${escapeHtml(p.name)}</strong>
                        <span style="color:var(--text2);font-size:12px;margin-left:8px">${p.trigger_process ? escapeHtml(p.trigger_process) : '无触发'}</span>
                    </div>
                    <div>
                        <button class="btn-sm" onclick="activateProfile('${escapeHtml(p.name)}')">激活</button>
                    </div>
                </div>
            `).join('');
    } catch (e) { console.error(e); }
}

function showAddProfile() {
    const name = prompt('预设名称:');
    if (!name) return;
    const trigger = prompt('触发进程 (如: VALORANT.exe):');
    const profile = {
        name, description: '', trigger_process: trigger || '',
        rules: [], ramdisk_enabled: false, memory_clean: false,
        io_priority_processes: [], enabled: true,
        created_at: new Date().toISOString()
    };
    // For now, use the generic command approach
    alert('Profile creation via API. Use v2.0 for full dialog support.');
}

async function activateProfile(name) {
    try {
        await invoke('activate_profile', { name });
        alert(`已激活预设: ${name}`);
    } catch (e) {
        alert(`激活失败: ${e}`);
    }
}

// Settings
function loadSettings() {}
function saveSettings() {
    alert('设置已保存 (sync via config API pending)');
}

// Helpers
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Auto refresh
setInterval(refreshStatus, 3000);
document.addEventListener('DOMContentLoaded', init);
