const ADMIN_TOKEN = window.CHAT_ADMIN_MODE ? (window.CHAT_ADMIN_TOKEN || '') : '';

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
    hint.textContent = `匿名顯示，發言冷卻 ${data.rateLimitSeconds} 秒，單則最多 ${data.maxMessageLength} 字，圖片上限 ${data.maxUploadMb}MB。`;
  }
  root.innerHTML = '';
  for (const item of data.items || []) {
    const el = document.createElement('article');
    const hasImage = Boolean(item.image_url);
    el.className = hasImage ? 'msg msg-photo' : 'msg';
    const t = formatMessageTime(item.created_at);
    const textHtml = item.body ? `<div class="body-text">${escapeHtml(item.body).replace(/\n/g, '<br>')}</div>` : '';
    if (hasImage) {
      const deleteButton = ADMIN_TOKEN ? `<button class="msg-delete" type="button" aria-label="刪除圖片訊息" title="刪除圖片訊息" data-delete-id="${escapeAttribute(item.id)}">✕</button>` : '';
      el.innerHTML = `
        <div class="msg-photo-frame">
          <img class="msg-image" src="${escapeAttribute(item.image_url)}" alt="上傳圖片" loading="lazy" data-fullscreen-src="${escapeAttribute(item.image_url)}" />
          ${deleteButton}
        </div>
        <div class="msg-photo-caption">
          <div class="meta"><span>${escapeHtml(item.nickname)}</span><span>${t}</span></div>
          ${textHtml}
        </div>`;
    } else {
      el.innerHTML = `<div class="meta"><span>${escapeHtml(item.nickname)}</span><span>${t}</span></div>${textHtml}`;
    }
    root.appendChild(el);
  }
  root.querySelectorAll('[data-fullscreen-src]').forEach((img) => {
    img.addEventListener('click', () => openLightbox(img.dataset.fullscreenSrc));
  });
  root.querySelectorAll('[data-delete-id]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!confirm('要刪掉這張圖片訊息嗎？')) return;
      const id = btn.dataset.deleteId;
      const res = await fetch(`/api/messages/${id}`, {
        method: 'DELETE',
        headers: { 'X-Admin-Token': ADMIN_TOKEN },
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.error || '刪除失敗');
        return;
      }
      loadMessages();
    });
  });
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

function escapeAttribute(v) {
  return String(v).replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
}

function updatePreview(file) {
  const preview = document.getElementById('imagePreview');
  const fileName = document.getElementById('fileName');
  if (!preview || !fileName) return;
  if (!file) {
    preview.classList.add('hidden');
    preview.innerHTML = '';
    fileName.textContent = '尚未選擇照片';
    return;
  }
  fileName.textContent = file.name;
  const url = URL.createObjectURL(file);
  preview.classList.remove('hidden');
  preview.innerHTML = `<img src="${url}" alt="預覽圖片" />`;
}

function openLightbox(src) {
  const lightbox = document.getElementById('lightbox');
  const image = document.getElementById('lightboxImage');
  if (!lightbox || !image) return;
  image.src = src;
  lightbox.classList.remove('hidden');
}

function closeLightbox() {
  const lightbox = document.getElementById('lightbox');
  const image = document.getElementById('lightboxImage');
  if (!lightbox || !image) return;
  lightbox.classList.add('hidden');
  image.src = '';
}

document.getElementById('refreshBtn')?.addEventListener('click', loadMessages);
document.getElementById('lightboxClose')?.addEventListener('click', closeLightbox);
document.getElementById('lightbox')?.addEventListener('click', (e) => {
  if (e.target.id === 'lightbox') closeLightbox();
});

document.getElementById('imageInput')?.addEventListener('change', (e) => {
  const file = e.target.files?.[0];
  updatePreview(file);
});

document.getElementById('composer')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const body = document.getElementById('body');
  const imageInput = document.getElementById('imageInput');
  const form = new FormData();
  form.append('body', body.value);
  const file = imageInput?.files?.[0];
  if (file) form.append('image', file);

  const res = await fetch('/api/messages', {
    method: 'POST',
    body: form,
  });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || '送出失敗');
    return;
  }
  body.value = '';
  if (imageInput) imageInput.value = '';
  updatePreview(null);
  loadMessages();
});

loadMessages();
setInterval(loadMessages, 5000);
