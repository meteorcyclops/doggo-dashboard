function tickClock() {
  const el = document.getElementById('clock');
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleTimeString('zh-TW', { hour12: false });
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
  if (job.state?.manualHealthy) {
    return { badge: 'READY', cls: 'ok', desc: 'MANUAL TEST PASS / NO NEW SIGNAL' };
  }
  const status = job.state?.lastStatus || 'unknown';
  if (status === 'ok') return { badge: 'OK', cls: 'ok', desc: 'LAST RUN CLEAR' };
  if (status === 'error') {
    if (job.state?.lastErrorReason === 'rate_limit') {
      return { badge: 'JAM', cls: 'warn', desc: 'LAST RUN HIT RATE LIMIT' };
    }
    return { badge: 'ALERT', cls: 'danger', desc: 'LAST RUN FAILED' };
  }
  return { badge: 'WAIT', cls: 'warn', desc: 'WAITING NEXT CYCLE' };
}

function renderTasks(jobs) {
  const el = document.getElementById('task-list');
  el.innerHTML = '';
  jobs.forEach((job) => {
    const state = mapStatus(job);
    const li = document.createElement('li');
    li.innerHTML = `<span>${job.name}<br><small>${timeAgo(job.state?.lastRunAtMs)} · ${state.desc}</small></span><b class="${state.cls}">${state.badge}</b>`;
    el.appendChild(li);
  });
}

function renderSummary(data) {
  const jobs = data.jobs.filter((j) => j.enabled);
  const ready = jobs.filter((j) => mapStatus(j).cls === 'ok').length;
  const jammed = jobs.filter((j) => mapStatus(j).badge === 'JAM').length;
  const alerts = jobs.filter((j) => mapStatus(j).cls === 'danger').length;

  const enemyHp = document.getElementById('enemy-hp');
  const playerHp = document.getElementById('player-hp');
  enemyHp.style.width = `${Math.max(12, 100 - jammed * 18 - alerts * 28)}%`;
  playerHp.style.width = `${Math.max(55, 96 - alerts * 12)}%`;

  document.getElementById('current-status').textContent = alerts
    ? `${alerts} ALERT / CHECK NOW`
    : jammed
      ? `${jammed} JAMMED / STILL RUNNING`
      : 'ALL MISSIONS STABLE';
  document.getElementById('automation-count').textContent = `${jobs.length} LIVE / ${ready} READY`;
  document.getElementById('lobster-mood').textContent = alerts ? 'GUARD MODE' : jammed ? 'BRAVE' : 'HAPPY';

  document.getElementById('task-bubble').textContent = alerts
    ? 'Woof! Some missions need repair right now.'
    : jammed
      ? 'Woof. Last run got jammed, but the missions are still active.'
      : 'Woof! Quiet shift, no new alerts for now.';

  document.getElementById('refresh-state').textContent = `SYNC ${new Date(data.generatedAt).toLocaleTimeString('zh-TW', { hour12: false })}`;
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
    hint.textContent = 'SYNCING LOCAL DATA...';
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
bindActions();
loadData();
setInterval(loadData, 30000);
