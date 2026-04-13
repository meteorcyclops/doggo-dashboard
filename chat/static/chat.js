const ADMIN_TOKEN = window.CHAT_ADMIN_MODE ? (window.CHAT_ADMIN_TOKEN || '') : '';
let lastMessagesSignature = '';
let isLoadingMessages = false;

function buildMessageHtml(item) {
  const hasImage = Boolean(item.image_url);
  const t = formatMessageTime(item.created_at);
  const textHtml = item.body ? `<div class="body-text">${escapeHtml(item.body).replace(/\n/g, '<br>')}</div>` : '';
  if (hasImage) {
    const deleteButton = ADMIN_TOKEN ? `<button class="msg-delete" type="button" aria-label="刪除圖片訊息" title="刪除圖片訊息" data-delete-id="${escapeAttribute(item.id)}">✕</button>` : '';
    return {
      className: 'msg msg-photo',
      html: `
        <div class="msg-photo-frame">
          <img class="msg-image" src="${escapeAttribute(item.image_url)}" alt="上傳圖片" loading="lazy" data-fullscreen-src="${escapeAttribute(item.image_url)}" />
          ${deleteButton}
        </div>
        <div class="msg-photo-caption">
          <div class="meta"><span>${escapeHtml(item.nickname)}</span><span>${t}</span></div>
          ${textHtml}
        </div>`,
    };
  }
  return {
    className: 'msg',
    html: `<div class="meta"><span>${escapeHtml(item.nickname)}</span><span>${t}</span></div>${textHtml}`,
  };
}

function bindMessageEvents(root) {
  root.querySelectorAll('[data-fullscreen-src]').forEach((img) => {
    if (img.dataset.boundLightbox === 'true') return;
    img.dataset.boundLightbox = 'true';
    img.addEventListener('click', () => openLightbox(img.dataset.fullscreenSrc));
  });
  root.querySelectorAll('[data-delete-id]').forEach((btn) => {
    if (btn.dataset.boundDelete === 'true') return;
    btn.dataset.boundDelete = 'true';
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
      lastMessagesSignature = '';
      loadMessages({ forceRender: true });
    });
  });
}

function renderMessages(root, items) {
  const fragment = document.createDocumentFragment();
  for (const item of items || []) {
    const el = document.createElement('article');
    const rendered = buildMessageHtml(item);
    el.className = rendered.className;
    el.dataset.messageId = item.id;
    el.innerHTML = rendered.html;
    fragment.appendChild(el);
  }
  root.replaceChildren(fragment);
  bindMessageEvents(root);
}

async function loadMessages(options = {}) {
  if (isLoadingMessages) return;
  isLoadingMessages = true;
  try {
    const res = await fetch('/api/messages', { cache: 'no-store' });
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
    const items = data.items || [];
    const signature = JSON.stringify(items.map((item) => [item.id, item.body || '', item.image_url || '', item.created_at || '']));
    if (!options.forceRender && signature === lastMessagesSignature) {
      bindMessageEvents(root);
      return;
    }
    renderMessages(root, items);
    lastMessagesSignature = signature;
  } finally {
    isLoadingMessages = false;
  }
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
  lastMessagesSignature = '';
  loadMessages({ forceRender: true });
});

loadMessages({ forceRender: true });
setInterval(() => loadMessages(), 5000);
