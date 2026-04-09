function tickClock() {
  const el = document.getElementById('clock');
  if (!el) return;
  el.textContent = new Date().toLocaleTimeString('zh-TW', { hour12: false });
}

function timeAgo(ms) {
  if (!ms) return '無紀錄';
  const diff = Math.max(0, Date.now() - ms);
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '剛剛';
  if (mins < 60) return `${mins} 分鐘前`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} 小時前`;
  return `${Math.floor(hours / 24)} 天前`;
}

function mapStatus(job) {
  const status = job.state?.lastStatus || 'unknown';
  if (status === 'ok') return { badge: 'OK', cls: 'ok', desc: job.desc || '狀態穩定' };
  if (status === 'error') return { badge: 'JAM', cls: 'warn', desc: job.desc || '需要注意' };
  return { badge: 'WAIT', cls: 'warn', desc: job.desc || '等待中' };
}

function renderTasks(jobs) {
  const list = document.getElementById('task-list');
  list.innerHTML = '';
  jobs.forEach((job) => {
    const state = mapStatus(job);
    const li = document.createElement('li');
    li.innerHTML = `<span>${job.name}<br><small>${timeAgo(job.state?.lastRunAtMs)} · ${state.desc}</small></span><b class="${state.cls}">${state.badge}</b>`;
    list.appendChild(li);
  });
}

function renderSummary(data) {
  const jobs = data.jobs.filter((j) => j.enabled);
  const ready = jobs.filter((j) => mapStatus(j).cls === 'ok').length;
  const jammed = jobs.filter((j) => mapStatus(j).badge === 'JAM').length;
  const alerts = jobs.filter((j) => mapStatus(j).cls === 'danger').length;

  document.getElementById('enemy-hp').style.width = `${Math.max(24, 100 - jammed * 16 - alerts * 24)}%`;
  document.getElementById('player-hp').style.width = `${Math.max(70, 96 - alerts * 10)}%`;

  document.getElementById('current-status').textContent = alerts
    ? '有一些展示任務需要關注'
    : jammed
      ? '部分任務卡住，但整體正常'
      : '全部展示任務都很平穩';

  document.getElementById('automation-count').textContent = `${jobs.length} 條展示中 / ${ready} 條穩定`;
  document.getElementById('lobster-mood').textContent = alerts ? 'WORRIED' : jammed ? 'BRAVE' : 'HAPPY';
  document.getElementById('task-bubble').textContent = alerts
    ? '狗狗說：今天有幾個展示任務要再看一下！'
    : jammed
      ? '狗狗說：有些任務暫時卡住，但只是展示資料喔。'
      : '狗狗說：今天一切安穩，歡迎參觀這個可愛儀表板。';

  document.getElementById('gateway-pill').textContent = data.gatewayOnline ? 'DEMO' : 'OFFLINE';
  document.getElementById('line-link').textContent = data.lineStatus;

  const summary = document.getElementById('summary-list');
  summary.innerHTML = `
    <li><span>展示模式</span><b class="ok">PUBLIC DEMO</b></li>
    <li><span>資料來源</span><b class="ok">FAKE DATA</b></li>
    <li><span>最後更新</span><b class="ok">${new Date(data.generatedAt).toLocaleTimeString('zh-TW', { hour12: false })}</b></li>
  `;
}

async function loadData() {
  const hint = document.getElementById('action-hint');
  try {
    hint.textContent = '正在刷新展示資料...';
    const res = await fetch('./data.json?_=' + Date.now(), { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderTasks(data.jobs);
    renderSummary(data);
    hint.textContent = `公開展示版，已更新於 ${new Date(data.generatedAt).toLocaleTimeString('zh-TW', { hour12: false })}`;
  } catch (err) {
    hint.textContent = `資料讀取失敗：${err.message}`;
  }
}

function applyTheme(theme) {
  document.body.dataset.theme = theme;
  const label = document.getElementById('theme-label');
  if (label) label.textContent = theme === 'night' ? 'NIGHT' : 'DAY';
  try { localStorage.setItem('doggo-dream-theme', theme); } catch {}
}

function initTheme() {
  let theme = 'day';
  try { theme = localStorage.getItem('doggo-dream-theme') || theme; } catch {}
  applyTheme(theme);
  document.getElementById('theme-toggle')?.addEventListener('click', () => {
    applyTheme(document.body.dataset.theme === 'night' ? 'day' : 'night');
  });
}

function bindActions() {
  document.getElementById('refresh-btn')?.addEventListener('click', loadData);
  document.getElementById('theme-copy-btn')?.addEventListener('click', async () => {
    const hint = document.getElementById('action-hint');
    try {
      await navigator.clipboard.writeText(window.location.href);
      hint.textContent = '已複製這個展示頁網址';
    } catch {
      hint.textContent = '複製失敗，請手動複製網址列';
    }
  });
}

setInterval(tickClock, 1000);
tickClock();
initTheme();
bindActions();
loadData();
setInterval(loadData, 30000);
