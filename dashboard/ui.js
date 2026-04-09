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
  if (!job.enabled) {
    return { badge: '已停用', cls: 'warn', human: '目前停用中' };
  }
  if (job.state?.manualHealthy) {
    return { badge: '待命', cls: 'ok', human: '剛手動測過，現在可正常執行，暫時沒有新通知' };
  }
  const status = job.state?.lastStatus || job.state?.lastRunStatus || 'unknown';
  if (status === 'ok') {
    return { badge: '正常', cls: 'ok', human: '最近一次執行正常' };
  }
  if (status === 'error') {
    const reason = job.state?.lastErrorReason === 'rate_limit'
      ? '上次被模型額度限制擋住'
      : '上次執行失敗，建議再檢查';
    return { badge: '注意', cls: 'warn', human: reason };
  }
  return { badge: '執行中', cls: 'warn', human: '等待下一次排程執行' };
}

function renderTasks(jobs) {
  const el = document.getElementById('task-list');
  if (!el) return;
  el.innerHTML = '';
  jobs.forEach((job) => {
    const state = mapStatus(job);
    const li = document.createElement('li');
    li.innerHTML = `<span>${job.name}<br><small>${timeAgo(job.state?.lastRunAtMs)}，${state.human}</small></span><b class="${state.cls}">${state.badge}</b>`;
    el.appendChild(li);
  });
}

function renderSummary(data) {
  const enabledJobs = data.jobs.filter((job) => job.enabled);
  const healthyJobs = enabledJobs.filter((job) => mapStatus(job).cls === 'ok');
  const attentionJobs = enabledJobs.filter((job) => mapStatus(job).cls !== 'ok');

  document.getElementById('current-status').textContent = attentionJobs.length
    ? `目前有 ${attentionJobs.length} 條提醒值得注意，但任務仍在排程中`
    : '全部提醒目前都安穩運作中';
  document.getElementById('automation-count').textContent = `${enabledJobs.length} 條已啟用，${healthyJobs.length} 條狀態穩定`;

  const bubbleText = attentionJobs.length
    ? '我有在工作喔，只是有些提醒上次被額度限制卡到，現在已經可以手動跑。'
    : '今天的提醒們都很乖，我在工位上顧著它們。';
  document.getElementById('task-bubble').textContent = bubbleText;

  document.getElementById('lobster-label').textContent = attentionJobs.length
    ? '小龍蝦正在盯著有風險的提醒'
    : '小龍蝦已上工，一切順順的';
  document.getElementById('lobster-mood').textContent = attentionJobs.length
    ? '盯盤中，但心情還行'
    : '專心工作中';

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
    hint.textContent = `已更新，${new Date(data.generatedAt).toLocaleTimeString('zh-TW', { hour12: false })}`;
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
