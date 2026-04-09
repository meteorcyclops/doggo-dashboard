function tickClock() {
  const el = document.getElementById('clock');
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleTimeString('zh-TW', { hour12: false });
}

function timeAgo(ms) {
  if (!ms) return '尚無紀錄';
  const diff = Math.max(0, Date.now() - ms);
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '剛剛';
  if (mins < 60) return `${mins} 分鐘前`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} 小時前`;
  return `${Math.floor(hours / 24)} 天前`;
}

function mapStatus(job) {
  if (!job.enabled) return { text: 'DISABLED', cls: 'warn' };
  const status = job.state?.lastStatus || job.state?.lastRunStatus || 'unknown';
  if (status === 'ok') return { text: 'OK', cls: 'ok' };
  if (status === 'error') return { text: 'ERROR', cls: 'danger' };
  return { text: 'RUNNING', cls: 'warn' };
}

function renderTasks(jobs) {
  const el = document.getElementById('task-list');
  if (!el) return;
  el.innerHTML = '';
  jobs.forEach((job) => {
    const state = mapStatus(job);
    const li = document.createElement('li');
    li.innerHTML = `<span>${job.name}<br><small>${timeAgo(job.state?.lastRunAtMs)}</small></span><b class="${state.cls}">${state.text}</b>`;
    el.appendChild(li);
  });
}

function renderSummary(data) {
  const enabledJobs = data.jobs.filter((job) => job.enabled);
  const errorJobs = enabledJobs.filter((job) => mapStatus(job).cls === 'danger');
  const okJobs = enabledJobs.filter((job) => mapStatus(job).cls === 'ok');

  document.getElementById('current-status').textContent = errorJobs.length
    ? `有 ${errorJobs.length} 條提醒需要注意`
    : '待命中，可接新任務';
  document.getElementById('automation-count').textContent = `${enabledJobs.length} 條已啟用，${okJobs.length} 條最近正常`;
  document.getElementById('task-bubble').textContent = `監控中：${enabledJobs.map((job) => job.name.replace(/ monitor| alerts| digest| watch/gi, '')).join(' / ')}`;
  document.getElementById('lobster-label').textContent = errorJobs.length
    ? '龍蝦在線，發現部分提醒異常'
    : '龍蝦在線，待命中';

  const pill = document.getElementById('gateway-pill');
  pill.textContent = data.gatewayOnline ? '● ONLINE' : '● DEGRADED';
  pill.className = `status-pill ${data.gatewayOnline ? 'online' : 'danger'}`;

  const summary = document.getElementById('summary-list');
  summary.innerHTML = `
    <li><span>Gateway</span><b>${data.gatewayOnline ? 'ONLINE' : 'OFFLINE'}</b></li>
    <li><span>LINE</span><b>${data.lineStatus}</b></li>
    <li><span>資料更新</span><b>${new Date(data.generatedAt).toLocaleTimeString('zh-TW', { hour12: false })}</b></li>
  `;
}

async function loadData() {
  const hint = document.getElementById('action-hint');
  try {
    hint.textContent = '正在刷新 dashboard 資料...';
    const res = await fetch('./data.json?_=' + Date.now(), { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderTasks(data.jobs);
    renderSummary(data);
    hint.textContent = `已更新，來源：本機 dashboard/data.json，${new Date(data.generatedAt).toLocaleTimeString('zh-TW', { hour12: false })}`;
  } catch (err) {
    hint.textContent = `資料讀取失敗：${err.message}`;
  }
}

function bindActions() {
  document.getElementById('refresh-btn')?.addEventListener('click', loadData);
  document.querySelectorAll('[data-copy]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const text = btn.getAttribute('data-copy');
      const hint = document.getElementById('action-hint');
      try {
        await navigator.clipboard.writeText(text);
        hint.textContent = `已複製：${text}`;
      } catch {
        hint.textContent = `無法自動複製，請手動複製：${text}`;
      }
    });
  });
}

setInterval(tickClock, 1000);
tickClock();
bindActions();
loadData();
setInterval(loadData, 30000);
