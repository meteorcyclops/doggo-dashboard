function tickClock() {
  const el = document.getElementById('clock');
  if (!el) return;
  el.textContent = new Date().toLocaleTimeString('zh-TW', { hour12: false });
}

function timeAgo(ms) {
  if (!ms) return 'NO RUN';
  const diff = Math.max(0, Date.now() - ms);
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'JUST NOW';
  if (mins < 60) return `${mins}M AGO`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}H AGO`;
  return `${Math.floor(hours / 24)}D AGO`;
}

function mapStatus(job) {
  if (!job.enabled) return { badge: 'OFF', cls: 'warn', desc: 'MISSION PAUSED' };
  if (job.state?.manualHealthy) return { badge: 'READY', cls: 'ok', desc: 'TESTED OK / NO NEW SIGNAL' };
  const status = job.state?.lastStatus || 'unknown';
  if (status === 'ok') return { badge: 'OK', cls: 'ok', desc: 'LAST RUN CLEAR' };
  if (status === 'error') {
    if (job.state?.lastErrorReason === 'rate_limit') return { badge: 'JAM', cls: 'warn', desc: 'LAST RUN HIT RATE LIMIT' };
    return { badge: 'ALERT', cls: 'danger', desc: 'LAST RUN FAILED' };
  }
  return { badge: 'WAIT', cls: 'warn', desc: 'WAITING NEXT CYCLE' };
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

  document.getElementById('enemy-hp').style.width = `${Math.max(18, 100 - jammed * 18 - alerts * 26)}%`;
  document.getElementById('player-hp').style.width = `${Math.max(62, 96 - alerts * 12)}%`;

  document.getElementById('current-status').textContent = alerts
    ? `${alerts} alert, need cuddle + fix`
    : jammed
      ? `${jammed} jammed, but still scheduled`
      : 'all missions calm and cute';

  document.getElementById('automation-count').textContent = `${jobs.length} live / ${ready} ready`;
  document.getElementById('lobster-mood').textContent = alerts ? 'WORRIED' : jammed ? 'BRAVE' : 'HAPPY';

  document.getElementById('task-bubble').textContent = alerts
    ? 'Doggo says: some missions need help right now!'
    : jammed
      ? 'Doggo says: last run got jammed, but the missions are still alive.'
      : 'Doggo says: everything is quiet, no new alerts for now.';

  document.getElementById('gateway-pill').textContent = data.gatewayOnline ? 'ONLINE' : 'OFFLINE';
  document.getElementById('line-link').textContent = data.lineStatus;

  const summary = document.getElementById('summary-list');
  summary.innerHTML = `
    <li><span>GATEWAY</span><b class="${data.gatewayOnline ? 'ok' : 'danger'}">${data.gatewayOnline ? 'ONLINE' : 'OFFLINE'}</b></li>
    <li><span>LINE LINK</span><b class="${data.lineStatus === 'OK' ? 'ok' : 'warn'}">${data.lineStatus}</b></li>
    <li><span>LAST SYNC</span><b class="ok">${new Date(data.generatedAt).toLocaleTimeString('zh-TW', { hour12: false })}</b></li>
  `;
}

async function loadData() {
  const hint = document.getElementById('action-hint');
  try {
    hint.textContent = 'SYNCING CUTE DATA...';
    const res = await fetch('./data.json?_=' + Date.now(), { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderTasks(data.jobs);
    renderSummary(data);
    hint.textContent = `SYNC OK @ ${new Date(data.generatedAt).toLocaleTimeString('zh-TW', { hour12: false })}`;
  } catch (err) {
    hint.textContent = `SYNC FAIL: ${err.message}`;
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
  try {
    theme = localStorage.getItem('doggo-dream-theme') || theme;
  } catch {}
  applyTheme(theme);
  document.getElementById('theme-toggle')?.addEventListener('click', () => {
    applyTheme(document.body.dataset.theme === 'night' ? 'day' : 'night');
  });
}

function bindActions() {
  document.getElementById('refresh-btn')?.addEventListener('click', loadData);
  document.querySelectorAll('[data-copy]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const text = btn.getAttribute('data-copy');
      const hint = document.getElementById('action-hint');
      try {
        await navigator.clipboard.writeText(text);
        hint.textContent = `COPIED: ${text}`;
      } catch {
        hint.textContent = `COPY FAILED, USE: ${text}`;
      }
    });
  });
}

setInterval(tickClock, 1000);
tickClock();
initTheme();
bindActions();
loadData();
setInterval(loadData, 30000);
