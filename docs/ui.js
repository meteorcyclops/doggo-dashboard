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

function formatChangePct(p) {
  if (p == null || Number.isNaN(Number(p))) return '—';
  const n = Number(p);
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}%`;
}

function safeHttpUrl(raw) {
  if (!raw || typeof raw !== 'string') return '';
  try {
    const u = new URL(raw);
    return u.protocol === 'http:' || u.protocol === 'https:' ? u.href : '';
  } catch {
    return '';
  }
}

function provenanceClass(text) {
  if (!text) return 'warn';
  if (String(text).startsWith('LIVE')) return 'ok';
  if (String(text).startsWith('PARTIAL')) return 'warn';
  return 'warn';
}

function renderQuotes(quotes) {
  const list = document.getElementById('quote-list');
  const meta = document.getElementById('quote-meta');
  if (!list) return;
  list.innerHTML = '';
  const asOf = quotes?.asOf;
  if (meta) {
    meta.textContent = asOf
      ? `報價快照（UTC）：${asOf}`
      : '尚無報價時間戳';
  }
  if (!quotes?.items?.length) {
    const li = document.createElement('li');
    const hint = quotes?.error ? `暫無報價 · ${quotes.error}` : '暫無報價';
    li.innerHTML = `<span>${hint}</span><b class="warn">NA</b>`;
    list.appendChild(li);
    return;
  }
  quotes.items.forEach((q) => {
    const li = document.createElement('li');
    const pct = Number(q.changePct);
    const cls = pct > 0 ? 'ok' : pct < 0 ? 'danger' : 'warn';
    li.innerHTML = `<span>${q.symbol} ${q.name || ''}<br><small>收盤價附近 · ${formatChangePct(q.changePct)}</small></span><b class="${cls}">${formatChangePct(q.changePct)}</b>`;
    list.appendChild(li);
  });
}

function formatTrumpTime(iso) {
  if (!iso || typeof iso !== 'string') return '';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString('zh-TW', { hour12: false });
  } catch {
    return iso;
  }
}

function renderTrumpTruth(trump) {
  const list = document.getElementById('trump-list');
  const meta = document.getElementById('trump-meta');
  if (!list) return;
  list.innerHTML = '';
  const src = trump?.source ? String(trump.source).slice(0, 140) : '';
  if (meta) {
    const asOf = trump?.asOf ? formatTrumpTime(trump.asOf) : '';
    if (trump?.error) {
      meta.textContent = src ? `${src} · ${trump.error}` : trump.error;
    } else if (asOf) {
      meta.textContent = src ? `來源：${src} · 更新 ${asOf}` : `更新 ${asOf}`;
    } else {
      meta.textContent = src ? `來源：${src}` : '第三方存檔摘要';
    }
  }
  const hasItems = trump?.items?.length;
  if (!hasItems) {
    const li = document.createElement('li');
    const span = document.createElement('span');
    span.appendChild(
      document.createTextNode(
        trump?.error ? '暫無資料（建置時抓取失敗，請稍後重試）' : '暫無資料',
      ),
    );
    if (trump?.error) {
      span.appendChild(document.createElement('br'));
      const small = document.createElement('small');
      small.className = 'trump-excerpt';
      small.textContent = trump.error;
      span.appendChild(small);
    }
    const badge = document.createElement('b');
    badge.className = 'warn';
    badge.textContent = '—';
    li.appendChild(span);
    li.appendChild(badge);
    list.appendChild(li);
    return;
  }
  trump.items.forEach((item) => {
    const li = document.createElement('li');
    const span = document.createElement('span');
    const url = safeHttpUrl(item.url);
    if (url) {
      const a = document.createElement('a');
      a.href = url;
      a.target = '_blank';
      a.rel = 'noreferrer';
      a.textContent = item.excerpt || '（無摘要）';
      span.appendChild(a);
    } else {
      span.appendChild(document.createTextNode(item.excerpt || '（無摘要）'));
    }
    span.appendChild(document.createElement('br'));
    const small = document.createElement('small');
    small.className = 'trump-excerpt';
    small.textContent = formatTrumpTime(item.postedAtTw) || '';
    span.appendChild(small);
    const badge = document.createElement('b');
    badge.className = item.important ? 'warn' : 'ok';
    badge.textContent = item.important ? '重點' : '帖';
    li.appendChild(span);
    li.appendChild(badge);
    list.appendChild(li);
  });
}

function renderHeadlines(feed) {
  const list = document.getElementById('headline-list');
  const meta = document.getElementById('feed-meta');
  if (!list) return;
  list.innerHTML = '';
  if (meta) {
    const src = feed?.source ? String(feed.source).slice(0, 120) : '';
    meta.textContent = feed?.error
      ? `RSS：${src || '—'}（${feed.error}）`
      : src
        ? `來源：${src}`
        : 'RSS 未設定';
  }
  if (!feed?.items?.length) {
    const li = document.createElement('li');
    li.innerHTML = `<span>${feed?.error ? '暫無新聞（請稍後重試）' : '暫無新聞'}</span><b class="warn">—</b>`;
    list.appendChild(li);
    return;
  }
  feed.items.forEach((item) => {
    const li = document.createElement('li');
    const span = document.createElement('span');
    const url = safeHttpUrl(item.url);
    if (url) {
      const a = document.createElement('a');
      a.href = url;
      a.target = '_blank';
      a.rel = 'noreferrer';
      a.textContent = item.title || '';
      span.appendChild(a);
    } else {
      span.appendChild(document.createTextNode(item.title || ''));
    }
    span.appendChild(document.createElement('br'));
    const small = document.createElement('small');
    small.textContent = item.time || '';
    span.appendChild(small);
    const badge = document.createElement('b');
    badge.className = 'ok';
    badge.textContent = 'RSS';
    li.appendChild(span);
    li.appendChild(badge);
    list.appendChild(li);
  });
}

function setDogSprite(data) {
  const el = document.getElementById('dog-sprite');
  if (!el) return;
  const state = data.dog?.state || 'idle';
  el.dataset.dogState = ['idle', 'bone', 'excited', 'worried', 'sleepy'].includes(state) ? state : 'idle';
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
  const jobs = (data.jobs || []).filter((j) => j.enabled);
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

  const prov = data.provenance || 'DEMO';
  const provCls = provenanceClass(prov);
  const genAt = data.generatedAt
    ? new Date(data.generatedAt).toLocaleString('zh-TW', { hour12: false })
    : '—';
  const quoteAsOf = data.quotes?.asOf
    ? new Date(data.quotes.asOf).toLocaleString('zh-TW', { hour12: false })
    : '—';

  const summary = document.getElementById('summary-list');
  summary.innerHTML = `
    <li><span>展示模式</span><b class="ok">PUBLIC DEMO</b></li>
    <li><span>資料來源</span><b class="${provCls}">${prov}</b></li>
    <li><span>報價快照（UTC）</span><b class="${data.quotes?.items?.length ? 'ok' : 'warn'}">${quoteAsOf}</b></li>
    <li><span>最後建置</span><b class="ok">${genAt}</b></li>
  `;
}

async function loadData() {
  const hint = document.getElementById('action-hint');
  try {
    hint.textContent = '正在刷新展示資料...';
    const res = await fetch('./data.json?_=' + Date.now(), { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderTasks(data.jobs || []);
    renderQuotes(data.quotes);
    renderHeadlines(data.feed);
    renderTrumpTruth(data.trumpTruth);
    renderSummary(data);
    setDogSprite(data);
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
