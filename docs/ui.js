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

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function twSessionLabel(iso) {
  const d = iso ? new Date(iso) : new Date();
  if (Number.isNaN(d.getTime())) return '台股時段';
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Taipei',
    weekday: 'short',
    hour: 'numeric',
    minute: 'numeric',
    hour12: false,
  }).formatToParts(d);
  const m = {};
  for (const p of parts) {
    if (p.type !== 'literal') m[p.type] = p.value;
  }
  const wd = m.weekday;
  if (wd === 'Sat' || wd === 'Sun') return '台股休市';
  let hour = Number(m.hour);
  let minute = Number(m.minute);
  if (Number.isNaN(hour)) hour = 0;
  if (Number.isNaN(minute)) minute = 0;
  const mins = hour * 60 + minute;
  if (mins < 9 * 60) return '台股盤前';
  if (mins >= 13 * 60 + 30) return '台股盤後';
  return '台股盤中';
}

function dogMoodCN(state) {
  switch (state) {
    case 'excited':
      return '超嗨';
    case 'worried':
      return '緊張';
    case 'sleepy':
      return '休息中';
    case 'bone':
      return '很滿足';
    case 'work':
      return '上工中';
    case 'ok':
      return '穩穩的';
    default:
      return '放鬆';
  }
}

function heroFocusLabel(data) {
  if (data?.trumpTruth?.items?.some((item) => item.important)) return '川普發言快訊';
  if (data?.feed?.items?.length) return '新聞雷達';
  if (data?.quotes?.items?.length) return '台股快報';
  return '狗狗主舞台';
}

function dogGuideLine(target) {
  switch (target) {
    case 'quotes':
      return { state: 'work', text: '狗狗：先看台股快報，這裡是今天最像儀表板核心資訊的地方。' };
    case 'feed':
      return { state: 'ok', text: '狗狗：新聞雷達適合拿來判斷今天外面世界的情緒背景。' };
    case 'trump':
      return { state: 'worried', text: '狗狗：這區屬於高波動訊號，應該用警報感而不是一般 feed 感。' };
    default:
      return { state: currentDogState, text: taskBubbleText(currentData || {}, 0, 0) };
  }
}

function taskBubbleText(data, jammed, alerts) {
  const label = data.dog?.label || '今天';
  const st = data.dog?.state || 'idle';
  if (alerts) return `狗狗：${label}——小劇場有項目要留意，一起看一下好嗎？`;
  if (jammed) return `狗狗：${label}，追蹤小記裡有項目卡住；那是種子進度條，不是真實服務狀態。`;
  const byState = {
    idle: `狗狗：${label}，陪你看台股快照、新聞與摘要。`,
    excited: `狗狗：${label}，今天資訊量滿滿！`,
    worried: `狗狗：${label}，市面消息多，慢慢看沒關係。`,
    sleepy: `狗狗：${label}，盤後了，慢慢整理資訊吧。`,
    bone: `狗狗：${label}，今天的資料都咬回來了。`,
  };
  return byState[st] || byState.idle;
}

function pillLineStatus(raw) {
  const s = String(raw || '').trim().toUpperCase();
  if (!s || s === 'DEMO') return '資料 OK';
  return String(raw || '資料 OK');
}

function pillGateway(online) {
  return online ? '儀表板' : '離線';
}

function feedSummaryRow(feed) {
  if (feed?.error) return { text: `異常 · ${feed.error}`, cls: 'warn' };
  const n = feed?.items?.length || 0;
  if (n) return { text: `${n} 則`, cls: 'ok' };
  return { text: '無資料', cls: 'warn' };
}

function trumpSummaryRow(tt) {
  if (tt?.error) return { text: `異常 · ${tt.error}`, cls: 'warn' };
  const n = tt?.items?.length || 0;
  if (n) return { text: `${n} 則`, cls: 'ok' };
  return { text: '無資料', cls: 'warn' };
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
    if (item.excerptZhTw) {
      span.appendChild(document.createElement('br'));
      const zh = document.createElement('small');
      zh.className = 'trump-translation';
      zh.textContent = `繁中：${item.excerptZhTw}`;
      span.appendChild(zh);
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
    li.innerHTML = `<span>${feed?.error ? `暫無新聞（請稍後重試）` : '暫無新聞'}</span><b class="warn">—</b>`;
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

const DOG_LINES = {
  idle: ['汪，我幫你盯著市場～', '今天目前風平浪靜，先摸魚一下。'],
  excited: ['汪！這則新聞有點重要喔！', '今天外面的世界很熱鬧！'],
  worried: ['嗚，我先幫你守著這些異動。', '這條任務卡一下，但我還在盯。'],
  sleepy: ['晚安模式啟動，我抱著枕頭值班。', '夜深了，我會安靜幫你顧著。'],
  bone: ['耶，得到獎勵骨頭了！', '汪汪，這次做得不錯吧。'],
  work: ['工作眼鏡戴好了，準備上工。', '我正在很認真看資料喔。'],
  ok: ['全部看起來都順順的。', '今天的資料很乖，讚。'],
};

let currentDogState = 'idle';
let currentData = null;
let dogClickCount = 0;
let dogClickTimer = null;

function pickDogLine(state) {
  const pool = DOG_LINES[state] || DOG_LINES.idle;
  return pool[Math.floor(Math.random() * pool.length)];
}

function setDogBubble(text) {
  const bubble = document.getElementById('task-bubble');
  if (bubble) bubble.textContent = text;
}

function spawnDogParticles(kind = 'heart', count = 3) {
  const root = document.getElementById('dog-particles');
  const dog = document.getElementById('dog-sprite');
  if (!root || !dog) return;
  const rect = dog.getBoundingClientRect();
  const stage = root.getBoundingClientRect();
  for (let i = 0; i < count; i += 1) {
    const node = document.createElement('div');
    node.className = `dog-particle ${kind}`;
    node.style.left = `${rect.left - stage.left + 90 + i * 10}px`;
    node.style.top = `${rect.top - stage.top + 20 - i * 6}px`;
    root.appendChild(node);
    if (typeof gsap !== 'undefined') {
      gsap.fromTo(node, { opacity: 1, y: 0, scale: 0.8 }, {
        opacity: 0,
        y: -30 - i * 6,
        x: (i - 1) * 10,
        scale: 1.1,
        duration: 0.6,
        ease: 'power2.out',
        onComplete: () => node.remove(),
      });
    } else {
      setTimeout(() => node.remove(), 700);
    }
  }
}

function setDogState(state, bubbleText) {
  const el = document.getElementById('dog-sprite');
  if (!el) return;
  const allowed = ['idle', 'bone', 'excited', 'worried', 'sleepy', 'work', 'ok'];
  currentDogState = allowed.includes(state) ? state : 'idle';
  el.dataset.dogState = currentDogState;
  if (bubbleText) setDogBubble(bubbleText);
}

function resolveDogState(data) {
  const base = data?.dog?.state || 'idle';
  if (document.body?.dataset?.theme === 'night') return 'sleepy';
  const jobs = (data?.jobs || []).filter((j) => j.enabled);
  const jammed = jobs.some((j) => mapStatus(j).badge === 'JAM');
  if (jammed) return 'worried';
  if (data?.feed?.items?.length || data?.trumpTruth?.items?.some((item) => item.important)) return 'excited';
  if (base === 'bone') return 'bone';
  return jobs.length ? 'ok' : 'idle';
}

function setDogSprite(data) {
  currentData = data;
  setDogState(resolveDogState(data));
}

function renderTasks(jobs) {
  const list = document.getElementById('task-list');
  list.innerHTML = '';
  jobs.forEach((job) => {
    const state = mapStatus(job);
    const li = document.createElement('li');
    li.innerHTML = `<span>${escHtml(job.name)}<br><small>${timeAgo(job.state?.lastRunAtMs)} · ${escHtml(state.desc)}</small></span><b class="${state.cls}">${state.badge}</b>`;
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

  const session = twSessionLabel(data.generatedAt);
  const dogLabel = data.dog?.label || '今日';
  const dogState = data.dog?.state || 'idle';
  const mood = dogMoodCN(dogState);
  const focus = heroFocusLabel(data);

  const statusEl = document.getElementById('current-status');
  if (statusEl) {
    const core = `${session} · ${dogLabel} · ${mood}`;
    statusEl.textContent = jammed || alerts ? `追蹤小記有待留意 · ${core}` : core;
  }

  const stuck = jobs.length - ready;
  document.getElementById('automation-count').textContent = `${jobs.length} 項追蹤 · ${ready} 項順利${
    stuck ? ` · ${stuck} 項待留意` : ''
  }`;

  document.getElementById('lobster-mood').textContent = mood;
  setDogBubble(taskBubbleText(data, jammed, alerts));

  document.getElementById('gateway-pill').textContent = pillGateway(!!data.gatewayOnline);
  document.getElementById('line-link').textContent = pillLineStatus(data.lineStatus);

  const prov = data.provenance || '—';
  const provCls = provenanceClass(prov);
  const genAt = data.generatedAt
    ? new Date(data.generatedAt).toLocaleString('zh-TW', { hour12: false })
    : '—';
  const quoteAsOf = data.quotes?.asOf
    ? new Date(data.quotes.asOf).toLocaleString('zh-TW', { hour12: false })
    : '—';

  const feedRow = feedSummaryRow(data.feed);
  const trumpRow = trumpSummaryRow(data.trumpTruth);

  document.getElementById('hero-session').textContent = session;
  document.getElementById('hero-dog-state').textContent = `${dogLabel} · ${mood}`;
  document.getElementById('hero-provenance').textContent = prov;
  document.getElementById('hero-focus').textContent = focus;

  const quoteBadge = document.getElementById('quote-badge');
  const feedBadge = document.getElementById('feed-badge');
  const trumpBadge = document.getElementById('trump-badge');
  if (quoteBadge) quoteBadge.textContent = data.quotes?.items?.length ? 'LIVE' : 'WAIT';
  if (feedBadge) feedBadge.textContent = data.feed?.items?.length ? 'SCAN' : 'WAIT';
  if (trumpBadge) trumpBadge.textContent = data.trumpTruth?.items?.some((item) => item.important) ? 'HOT' : 'WATCH';

  const summary = document.getElementById('summary-list');
  summary.innerHTML = `
    <li><span>頁面類型</span><b class="ok">靜態儀表板</b></li>
    <li><span>資料來源</span><b class="${provCls}">${escHtml(prov)}</b></li>
    <li><span>報價快照（UTC）</span><b class="${data.quotes?.items?.length ? 'ok' : 'warn'}">${escHtml(quoteAsOf)}</b></li>
    <li><span>RSS 狀態</span><b class="${feedRow.cls}">${escHtml(feedRow.text)}</b></li>
    <li><span>川普摘要</span><b class="${trumpRow.cls}">${escHtml(trumpRow.text)}</b></li>
    <li><span>最後建置</span><b class="ok">${escHtml(genAt)}</b></li>
  `;
}

const POLL_MS = 60_000;

const STAGGER_LIST_SELECTORS = ['#quote-list', '#headline-list', '#trump-list', '#task-list', '#summary-list'];

function staggerFeedLists(silent) {
  if (silent || typeof gsap === 'undefined') return;
  for (const sel of STAGGER_LIST_SELECTORS) {
    const root = document.querySelector(sel);
    if (!root) continue;
    const items = root.querySelectorAll(':scope > li');
    if (!items.length) continue;
    gsap.from(items, {
      opacity: 0,
      y: 4,
      duration: 0.16,
      stagger: 0.022,
      ease: 'power2.out',
      clearProps: 'opacity,transform',
    });
  }
}

async function loadData(opts = {}) {
  const silent = !!opts.silent;
  const hint = document.getElementById('action-hint');
  try {
    if (!silent && hint) hint.textContent = '正在更新資料…';
    const res = await fetch('./data.json?_=' + Date.now(), { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderTasks(data.jobs || []);
    renderQuotes(data.quotes);
    renderHeadlines(data.feed);
    renderTrumpTruth(data.trumpTruth);
    renderSummary(data);
    setDogSprite(data);
    staggerFeedLists(silent);
    if (hint && !silent) {
      const localT = new Date().toLocaleTimeString('zh-TW', { hour12: false });
      hint.textContent = `已載入資料 · 本地 ${localT} · 報價與摘要於建置時更新`;
    }
  } catch (err) {
    if (hint) hint.textContent = `資料讀取失敗：${err.message}`;
  }
}

function applyTheme(theme) {
  document.body.dataset.theme = theme;
  const label = document.getElementById('theme-label');
  if (label) label.textContent = theme === 'night' ? 'NIGHT' : 'DAY';
  try { localStorage.setItem('doggo-dream-theme', theme); } catch {}
  if (currentData) {
    setDogSprite(currentData);
    setDogBubble(theme === 'night' ? pickDogLine('sleepy') : taskBubbleText(currentData, 0, 0));
  }
  syncCommentsTheme(theme);
}

function syncCommentsTheme(theme) {
  const frame = document.querySelector('iframe.utterances-frame');
  if (!frame?.contentWindow) return;
  frame.contentWindow.postMessage({ type: 'set-theme', theme: theme === 'night' ? 'github-dark' : 'github-light' }, 'https://utteranc.es');
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
      hint.textContent = '已複製頁面網址';
    } catch {
      hint.textContent = '複製失敗，請手動複製網址列';
    }
  });
}

function bindDogPet() {
  const el = document.getElementById('dog-sprite');
  if (!el) return;
  let busy = false;
  const triggerPet = () => {
    if (busy) return;
    busy = true;
    el.classList.add('dog-pet');
    spawnDogParticles('heart', 3);
    setDogBubble(pickDogLine(currentDogState));
    window.setTimeout(() => {
      el.classList.remove('dog-pet');
      busy = false;
    }, 320);
  };

  const handleClick = (part) => {
    dogClickCount += 1;
    clearTimeout(dogClickTimer);
    dogClickTimer = window.setTimeout(() => { dogClickCount = 0; }, 550);

    if (dogClickCount >= 3) {
      dogClickCount = 0;
      el.classList.add('dog-super');
      setDogState('bone', '汪！你連點三下，我開啟隱藏歡樂模式！');
      spawnDogParticles('star', 5);
      window.setTimeout(() => el.classList.remove('dog-super'), 1500);
      return;
    }

    if (part === 'nose') {
      setDogState('excited', '汪！鼻子被戳到了，好癢好開心！');
      spawnDogParticles('heart', 2);
    } else if (part === 'ear') {
      setDogState('worried', '耳朵抖一下，我有在聽你說話喔。');
      spawnDogParticles('star', 2);
    } else if (part === 'tail') {
      setDogState('ok', '尾巴搖搖，今天看起來一切都不錯。');
      spawnDogParticles('heart', 2);
    } else {
      triggerPet();
    }
  };

  el.addEventListener('mouseenter', () => {
    if (currentDogState !== 'sleepy') setDogState('work', '汪，我看向你了，有什麼想一起改的嗎？');
  });
  el.addEventListener('mouseleave', () => {
    if (!currentData) return;
    setDogSprite(currentData);
    setDogBubble(document.body.dataset.theme === 'night' ? pickDogLine('sleepy') : taskBubbleText(currentData, 0, 0));
  });
  el.addEventListener('click', (e) => {
    e.preventDefault();
    handleClick(e.target?.dataset?.part || 'body');
  });
  el.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      triggerPet();
    }
  });

  document.querySelectorAll('[data-dog-target]').forEach((panel) => {
    panel.addEventListener('mouseenter', () => {
      const target = panel.getAttribute('data-dog-target');
      const guide = dogGuideLine(target);
      document.querySelectorAll('.intel-panel').forEach((node) => node.classList.remove('is-focus'));
      panel.classList.add('is-focus');
      setDogState(guide.state, guide.text);
    });
    panel.addEventListener('mouseleave', () => {
      panel.classList.remove('is-focus');
      if (!currentData) return;
      setDogSprite(currentData);
      setDogBubble(document.body.dataset.theme === 'night' ? pickDogLine('sleepy') : taskBubbleText(currentData, 0, 0));
    });
  });
}

setInterval(tickClock, 1000);
tickClock();
initTheme();
bindActions();
bindDogPet();
loadData();
setInterval(() => loadData({ silent: true }), POLL_MS);
