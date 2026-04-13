async function loadMessages() {
  const res = await fetch('/api/messages');
  if (res.status === 403) {
    location.href = '/enter';
    return;
  }
  const data = await res.json();
  const root = document.getElementById('messages');
  const hint = document.getElementById('hint');
  if (hint && data.rateLimitSeconds) {
    hint.textContent = `匿名顯示，發言冷卻 ${data.rateLimitSeconds} 秒，單則最多 ${data.maxMessageLength} 字。`;
  }
  root.innerHTML = '';
  for (const item of data.items || []) {
    const el = document.createElement('article');
    el.className = 'msg';
    const t = formatMessageTime(item.created_at);
    el.innerHTML = `<div class="meta">${escapeHtml(item.nickname)} · ${t}</div><div>${escapeHtml(item.body).replace(/\n/g, '<br>')}</div>`;
    root.appendChild(el);
  }
  root.scrollTop = root.scrollHeight;
}

function formatMessageTime(value) {
  if (!value) return '時間未知';
  const date = typeof value === 'number' ? new Date(value * 1000) : new Date(value);
  if (Number.isNaN(date.getTime())) return '時間未知';
  return date.toLocaleString('zh-TW', { hour12: false });
}

function escapeHtml(v) {
  return String(v).replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
}

document.getElementById('refreshBtn')?.addEventListener('click', loadMessages);

document.getElementById('composer')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const body = document.getElementById('body');
  const res = await fetch('/api/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ body: body.value }),
  });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || '送出失敗');
    return;
  }
  body.value = '';
  loadMessages();
});

loadMessages();
setInterval(loadMessages, 5000);
