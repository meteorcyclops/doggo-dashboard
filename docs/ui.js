import { createDogController } from './dog-controller.js';

function tickClock() {
  const el = document.getElementById('clock');
  if (!el) return;
  el.textContent = new Date().toLocaleTimeString('zh-TW', { hour12: false });
}

function formatShortDateTime(value) {
  if (!value) return '無紀錄';
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value);
    return d.toLocaleString('zh-TW', {
      hour12: false,
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Taipei',
    });
  } catch {
    return String(value);
  }
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

function freshnessLabel(iso) {
  if (!iso) return { text: '無紀錄', cls: 'warn' };
  const ts = new Date(iso).getTime();
  const diffMin = Math.max(0, Math.floor((Date.now() - ts) / 60000));
  if (diffMin <= 5) return { text: `${timeAgo(ts)} · 新鮮`, cls: 'ok' };
  if (diffMin <= 15) return { text: `${timeAgo(ts)} · 稍舊`, cls: 'warn' };
  return { text: `${timeAgo(ts)} · 可能過期`, cls: 'danger' };
}

function mapStatus(job) {
  const status = job.state?.lastStatus || 'unknown';
  if (status === 'ok') return { badge: 'OK', cls: 'ok', desc: job.desc || '狀態穩定' };
  if (status === 'error') return { badge: 'JAM', cls: 'danger', desc: job.desc || '需要注意' };
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

function battleModeLabel(data) {
  if (data?.trumpTruth?.items?.some((item) => item.important)) return 'ALERT MODE';
  if (data?.feed?.items?.length) return 'SCAN MODE';
  if (data?.quotes?.items?.length) return 'MARKET MODE';
  return 'IDLE MODE';
}

function battleRhythmLabel(session, prov) {
  return `${session} · ${String(prov || 'SNAPSHOT').replace(/^LIVE\s*/,'LIVE ')}`;
}

function battleBroadcastDetail(data, focus) {
  if (focus === '川普發言快訊') return '狗狗正在播報高波動政治訊號與翻譯摘要。';
  if (focus === '新聞雷達') return '狗狗正在整理外部新聞，幫你快速抓情緒背景。';
  if (focus === '台股快報') return '狗狗正在盯盤面變化與主要股票快照。';
  if (focus === '8-bit 留言板') return '狗狗正在翻看牆上的便條紙和大家留下的心情。';
  return data?.trumpTruth?.items?.some((item) => item.important)
    ? '狗狗正在優先播報最值得先看的重點快訊。'
    : '狗狗正在整理今天值得先看的線索。';
}

function dogGuideLine(target) {
  switch (target) {
    case 'quotes':
      return { state: 'work', text: '狗狗：先看台股快報，這裡是今天最像儀表板核心資訊的地方。', focus: '台股快報' };
    case 'feed':
      return { state: 'ok', text: '狗狗：新聞雷達適合拿來判斷今天外面世界的情緒背景。', focus: '新聞雷達' };
    case 'trump':
      return { state: 'worried', text: '狗狗：這區屬於高波動訊號，應該用警報感而不是一般 feed 感。', focus: '川普發言快訊' };
    case 'guestbook':
      return { state: 'bone', text: '狗狗：這裡像小屋牆上的留言角，適合慢慢看大家留下來的心情。', focus: '8-bit 留言板' };
    default:
      return { state: 'idle', text: '狗狗：主舞台正在整理今天最值得先看的內容。', focus: '狗狗主舞台' };
  }
}

function taskBubbleText(data, jammed, alerts) {
  const label = data.dog?.label || '今天';
  const st = data.dog?.state || 'idle';
  const topTrump = data?.trumpTruth?.items?.[0];
  const topFeed = data?.feed?.items?.[0];
  const topQuote = data?.quotes?.items?.[0];
  if (alerts) return `狗狗快報：${label}，有項目需要留意，我先幫你把警報掛在前面。`;
  if (jammed) return `狗狗快報：${label}，追蹤小記裡有項目卡住，但主要資料台還在運作。`;
  if (topTrump?.excerptZhTw) return `狗狗快報：川普區有新重點，${topTrump.excerptZhTw.slice(0, 52)}${topTrump.excerptZhTw.length > 52 ? '…' : ''}`;
  if (topFeed?.title) return `狗狗快報：新聞雷達剛抓到，${topFeed.title.slice(0, 44)}${topFeed.title.length > 44 ? '…' : ''}`;
  if (topQuote?.symbol) return `狗狗快報：${topQuote.symbol} ${formatChangePct(topQuote.changePct)}，目前是最前排的盤面訊號。`;
  const byState = {
    idle: `狗狗快報：${label}，我正在輪播台股、新聞和摘要。`,
    excited: `狗狗快報：${label}，今天資訊量滿滿，我會一條一條唸給你。`,
    worried: `狗狗快報：${label}，外面波動有點多，我先把重要的講前面。`,
    sleepy: `狗狗快報：${label}，夜班模式中，我會安靜更新重點。`,
    bone: `狗狗快報：${label}，今天的資料都順利咬回來了。`,
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
  if (feed?.error) return { text: `異常 · ${feed.error}`, cls: 'danger' };
  const n = feed?.items?.length || 0;
  if (n) return { text: `${n} 則`, cls: 'ok' };
  return { text: '無資料', cls: 'warn' };
}

function trumpSummaryRow(tt) {
  if (tt?.error) return { text: `異常 · ${tt.error}`, cls: 'danger' };
  const n = tt?.items?.length || 0;
  if (n) return { text: `${n} 則`, cls: 'ok' };
  return { text: '無資料', cls: 'warn' };
}

function cardStateFromData({ items, error, asOf }) {
  if (error) return { tone: 'danger', badge: 'ERROR', title: '資料暫時失敗', detail: error };
  if (!items || !items.length) return { tone: 'warn', badge: 'EMPTY', title: '目前沒有資料', detail: '這張卡暫時是空的。' };
  if (!asOf) return { tone: 'warn', badge: 'STALE', title: '缺少時間戳', detail: '資料存在，但更新時間不明。' };
  return null;
}

function renderStateCard(list, meta, state, fallbackMeta) {
  list.innerHTML = '';
  const li = document.createElement('li');
  li.className = `card-state card-state-${state.tone}`;
  li.innerHTML = `<span><strong>${state.title}</strong><br><small>${state.detail}</small></span><b class="${state.tone}">${state.badge}</b>`;
  list.appendChild(li);
  if (meta) meta.textContent = fallbackMeta || state.detail;
}

function patternLabel(pattern) {
  switch (pattern) {
    case 'uptrend': return '走勢偏強';
    case 'downtrend': return '走勢偏弱';
    case 'volatile': return '波動明顯';
    default: return '區間整理';
  }
}

function renderSparkline(series = []) {
  const vals = series.filter((v) => Number.isFinite(Number(v))).map(Number);
  if (vals.length < 2) return '<span class="mini-trend-empty">···</span>';
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = Math.max(max - min, 0.0001);
  return `<span class="mini-trend">${vals.map((v) => {
    const h = Math.max(2, Math.round(((v - min) / range) * 18) + 4);
    return `<i style="height:${h}px"></i>`;
  }).join('')}</span>`;
}

function summarizeQuotes(items) {
  if (!items?.length) return '今天盤面還沒有足夠資料，狗狗先守著觀察。';
  const valid = items.filter((item) => Number.isFinite(Number(item.changePct)));
  if (!valid.length) return '目前有股票名單，但漲跌資料還不夠完整。';
  const avg = valid.reduce((sum, item) => sum + Number(item.changePct), 0) / valid.length;
  const top = [...valid].sort((a, b) => Number(b.changePct) - Number(a.changePct)).slice(0, 8);
  const semis = top.filter((item) => /積體電路|半導體|電子|電腦|SEMICONDUCTOR|ELECTRON|ADVANCED/i.test(String(item.name || ''))).length;
  const finance = top.filter((item) => /金控|銀行|證券|保險|金融|FINANCIAL|BANK/i.test(String(item.name || ''))).length;
  if (semis >= 3) return `今天半導體和電子族群偏強，前段班平均 ${avg.toFixed(2)}%。`;
  if (finance >= 3) return `今天金融股相對撐盤，前段班平均 ${avg.toFixed(2)}%。`;
  if (avg > 0.8) return `今天盤面整體偏強，追蹤股平均上漲 ${avg.toFixed(2)}%。`;
  if (avg < -0.8) return `今天盤面偏弱，追蹤股平均下跌 ${Math.abs(avg).toFixed(2)}%。`;
  return `今天追蹤股多半在盤整，平均變動 ${avg.toFixed(2)}%。`;
}

function renderQuotes(quotes) {
  const list = document.getElementById('quote-list');
  const meta = document.getElementById('quote-meta');
  const summaryEl = document.getElementById('quote-summary');
  if (!list) return;
  list.innerHTML = '';
  const asOf = quotes?.asOf;
  if (meta) {
    meta.textContent = asOf
      ? `報價快照：${formatShortDateTime(asOf)}`
      : '尚無報價時間戳';
  }
  const state = cardStateFromData({ items: quotes?.items, error: quotes?.error, asOf });
  if (summaryEl) summaryEl.textContent = summarizeQuotes(quotes?.items || []);
  if (state) {
    renderStateCard(list, meta, state, '台股快報暫時沒有完整資料');
    return;
  }
  quotes.items.forEach((q) => {
    const li = document.createElement('li');
    const pct = Number(q.changePct);
    const cls = pct > 0 ? 'ok' : pct < 0 ? 'danger' : 'warn';
    li.innerHTML = `<span>${q.symbol} ${q.name || ''}<br><small><span class="quote-price-line">現價 <strong class="quote-price-value">${q.price != null ? q.price : '—'}</strong>　<span class="quote-change-label">漲跌</span> <strong class="quote-change-value ${cls}">${formatChangePct(q.changePct)}</strong></span><span class="quote-mini-pattern">${patternLabel(q.pattern)}</span></small></span><span class="quote-trend-wrap">${renderSparkline(q.series)}<b class="quote-change-badge ${cls}">${formatChangePct(q.changePct)}</b></span>`;
    list.appendChild(li);
  });
}

function formatTrumpTime(iso) {
  if (!iso || typeof iso !== 'string') return '';
  return formatShortDateTime(iso);
}

function renderTrumpTruth(trump) {
  const list = document.getElementById('trump-list');
  const meta = document.getElementById('trump-meta');
  if (!list) return;
  list.innerHTML = '';
  const src = trump?.source ? String(trump.source).slice(0, 140) : '';
  const asOf = trump?.asOf ? formatTrumpTime(trump.asOf) : '';
  if (meta) {
    if (trump?.error) {
      meta.textContent = src ? `${src} · ${trump.error}` : trump.error;
    } else if (asOf) {
      meta.textContent = src ? `來源：${src} · 更新 ${asOf}` : `更新 ${asOf}`;
    } else {
      meta.textContent = src ? `來源：${src}` : '第三方存檔摘要';
    }
  }
  const state = cardStateFromData({ items: trump?.items, error: trump?.error, asOf });
  if (state) {
    renderStateCard(list, meta, state, src || '川普快訊暫時沒有完整資料');
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
  const src = feed?.source ? String(feed.source).slice(0, 120) : '';
  if (meta) {
    meta.textContent = feed?.error
      ? `RSS：${src || '—'}（${feed.error}）`
      : src
        ? `來源：${src}`
        : 'RSS 未設定';
  }
  const state = cardStateFromData({ items: feed?.items, error: feed?.error, asOf: src || 'rss-source' });
  if (state) {
    renderStateCard(list, meta, state, src || '新聞雷達暫時沒有完整資料');
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
    small.textContent = formatShortDateTime(item.time);
    span.appendChild(small);
    const badge = document.createElement('b');
    badge.className = 'ok';
    badge.textContent = 'RSS';
    li.appendChild(span);
    li.appendChild(badge);
    list.appendChild(li);
  });
}

let currentDogState = 'idle';
let currentData = null;
let currentFocus = 'doggo';
let broadcastItems = [];
let broadcastIndex = 0;
let broadcastTimer = null;
let broadcastPausedUntil = 0;

function animateBattleHud() {
  if (typeof gsap === 'undefined') return;
  gsap.fromTo(['#battle-chip', '#battle-focus-title', '#battle-focus-subtitle', '#battle-broadcast-detail', '#task-bubble'],
    { opacity: 0.35, y: 4 },
    { opacity: 1, y: 0, duration: 0.28, stagger: 0.04, ease: 'power2.out' }
  );
}

function buildBroadcastItems(data) {
  const items = [];
  for (const q of data?.quotes?.items || []) {
    items.push({
      focus: '台股快報',
      mode: 'MARKET MODE',
      state: 'work',
      title: `${q.symbol} ${formatChangePct(q.changePct)}`,
      detail: `${q.name || '盤面快照'} · 收盤價附近觀察`,
      bubble: `狗狗快報：${q.symbol} ${formatChangePct(q.changePct)}，${q.name || '這檔'}現在在盤面前排。`,
    });
  }
  for (const item of data?.feed?.items || []) {
    items.push({
      focus: '新聞雷達',
      mode: 'SCAN MODE',
      state: 'ok',
      title: (item.title || '新聞更新').slice(0, 30),
      detail: item.time || '外部新聞更新',
      bubble: `狗狗快報：${(item.title || '新聞更新').slice(0, 52)}${(item.title || '').length > 52 ? '…' : ''}`,
    });
  }
  for (const item of data?.trumpTruth?.items || []) {
    const text = item.excerptZhTw || item.excerpt || '川普快訊';
    items.push({
      focus: '川普發言快訊',
      mode: item.important ? 'ALERT MODE' : 'SCAN MODE',
      state: item.important ? 'worried' : 'ok',
      title: item.important ? '川普重點快訊' : '川普摘要',
      detail: text.slice(0, 36) + (text.length > 36 ? '…' : ''),
      bubble: `狗狗快報：${text.slice(0, 56)}${text.length > 56 ? '…' : ''}`,
    });
  }
  if (!items.length) {
    items.push({
      focus: '狗狗主舞台',
      mode: 'IDLE MODE',
      state: 'idle',
      title: '今日資料整理中',
      detail: '等新資料進來後，狗狗會開始輪播。',
      bubble: '狗狗快報：我先守著主舞台，等資料一到就開始播報。',
    });
  }
  return items;
}

function applyBroadcastItem(item) {
  if (!item) return;
  currentFocus = item.focus;
  const battleKicker = document.getElementById('battle-kicker');
  const battleChip = document.getElementById('battle-chip');
  const battleFocusTitle = document.getElementById('battle-focus-title');
  const battleBroadcastDetailEl = document.getElementById('battle-broadcast-detail');
  if (battleKicker) battleKicker.textContent = item.mode;
  if (battleChip) battleChip.textContent = item.focus;
  if (battleFocusTitle) battleFocusTitle.textContent = item.title;
  if (battleBroadcastDetailEl) battleBroadcastDetailEl.textContent = item.detail;
  dogController.setDogState(item.state, item.bubble);
  animateBattleHud();
}

function startBroadcastRotation(data) {
  broadcastItems = buildBroadcastItems(data);
  broadcastIndex = 0;
  clearInterval(broadcastTimer);
  applyBroadcastItem(broadcastItems[0]);
  broadcastTimer = window.setInterval(() => {
    if (Date.now() < broadcastPausedUntil || !broadcastItems.length) return;
    broadcastIndex = (broadcastIndex + 1) % broadcastItems.length;
    applyBroadcastItem(broadcastItems[broadcastIndex]);
  }, 4800);
}

function syncBattleStageMode(data) {
  const stage = document.querySelector('.battle-stage');
  if (!stage) return;
  const mode = battleModeLabel(data).toLowerCase().replace(/\s+/g, '-');
  stage.dataset.battleMode = mode;
}

const dogController = createDogController({
  mapStatus,
  taskBubbleText,
  dogGuideLine,
  onStateChange: (state) => {
    currentDogState = state;
    const mood = document.getElementById('lobster-mood');
    if (mood && currentData) mood.textContent = dogMoodCN(state);
  },
  onGuideChange: (focus, options = {}) => {
    currentFocus = focus || 'doggo';
    if (options.pauseBroadcast) {
      broadcastPausedUntil = Date.now() + 8000;
    }
    if (currentData) renderSummary(currentData);
  },
  getCurrentData: () => currentData,
  getCurrentState: () => currentDogState,
});

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
  const mood = dogMoodCN(currentDogState || data.dog?.state || 'idle');
  const focus = heroFocusLabel(data);
  const prov = data.provenance || '—';

  const statusEl = document.getElementById('current-status');
  if (statusEl) {
    const core = `${session} · ${dogLabel} · ${mood}`;
    statusEl.textContent = jammed || alerts ? `追蹤小記有待留意 · ${core}` : core;
  }

  const battleFocusSubtitle = document.getElementById('battle-focus-subtitle');
  const liveFocus = currentFocus === 'doggo' ? focus : currentFocus;
  if (battleFocusSubtitle) battleFocusSubtitle.textContent = battleRhythmLabel(session, prov);
  syncBattleStageMode(data);

  const stuck = jobs.length - ready;
  document.getElementById('automation-count').textContent = `${jobs.length} 項追蹤 · ${ready} 項順利${
    stuck ? ` · ${stuck} 項待留意` : ''
  }`;

  document.getElementById('lobster-mood').textContent = mood;
  dogController.setDogBubble(taskBubbleText(data, jammed, alerts));

  document.getElementById('gateway-pill').textContent = pillGateway(!!data.gatewayOnline);
  document.getElementById('line-link').textContent = pillLineStatus(data.lineStatus);

  const provCls = provenanceClass(prov);
  const genAt = data.generatedAt
    ? `${formatShortDateTime(data.generatedAt)}（台北時間）`
    : '—';
  const freshness = freshnessLabel(data.generatedAt);
  const quoteAsOf = data.quotes?.asOf
    ? `${formatShortDateTime(data.quotes.asOf)}（台北時間）`
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
    <li><span>報價快照</span><b class="${data.quotes?.items?.length ? 'ok' : 'warn'}">${escHtml(quoteAsOf)}</b></li>
    <li><span>RSS 狀態</span><b class="${feedRow.cls}">${escHtml(feedRow.text)}</b></li>
    <li><span>川普摘要</span><b class="${trumpRow.cls}">${escHtml(trumpRow.text)}</b></li>
    <li><span>最後建置</span><b class="ok">${escHtml(genAt)}</b></li>
    <li><span>資料新鮮度</span><b class="${freshness.cls}">${escHtml(freshness.text)}</b></li>
  `;
}

const POLL_MS = 30_000;
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
    currentData = data;
    renderTasks(data.jobs || []);
    renderQuotes(data.quotes);
    renderHeadlines(data.feed);
    renderTrumpTruth(data.trumpTruth);
    dogController.syncDog(data);
    renderSummary(data);
    startBroadcastRotation(data);
    staggerFeedLists(silent);
    if (hint && !silent) {
      const localT = new Date().toLocaleTimeString('zh-TW', { hour12: false, hour: '2-digit', minute: '2-digit' });
      const fresh = freshnessLabel(data.generatedAt).text;
      hint.textContent = `已載入資料 · 本地 ${localT} · 最後建置 ${fresh}`;
    }
  } catch (err) {
    if (hint) hint.textContent = `資料讀取失敗：${err.message}`;
  }
}

function applyTheme(theme) {
  document.body.dataset.theme = theme;
  const label = document.getElementById('theme-label');
  const toggle = document.getElementById('theme-toggle');
  if (label) label.textContent = theme === 'night' ? 'NIGHT' : 'DAY';
  if (toggle) toggle.classList.add('theme-toggle-flash');
  try { localStorage.setItem('doggo-dream-theme', theme); } catch {}
  if (currentData) {
    dogController.syncDog(currentData);
    dogController.setDogBubble(theme === 'night' ? dogController.pickDogLine('sleepy') : taskBubbleText(currentData, 0, 0));
    renderSummary(currentData);
    animateBattleHud();
  }
  window.setTimeout(() => toggle?.classList.remove('theme-toggle-flash'), 320);
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
  document.getElementById('quote-expand-btn')?.addEventListener('click', () => {
    const shell = document.querySelector('.quote-list-shell');
    const btn = document.getElementById('quote-expand-btn');
    const expanded = shell?.classList.toggle('is-expanded');
    if (btn) btn.textContent = expanded ? '收起追蹤股清單' : '展開更多追蹤股';
  });
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

setInterval(tickClock, 1000);
tickClock();
initTheme();
bindActions();
dogController.bindDogPet();
loadData();
setInterval(() => loadData({ silent: true }), POLL_MS);
