import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const cfg = window.DOGGO_GUESTBOOK_CONFIG || {};
const statusEl = document.getElementById('guestbook-status');
const listEl = document.getElementById('guestbook-list');
const formEl = document.getElementById('guestbook-form');
const nameEl = document.getElementById('guestbook-name');
const messageEl = document.getElementById('guestbook-message');

let supabase = null;
let pendingDeleteId = null;
let lastRenderedIds = [];

function setStatus(text) {
  if (statusEl) statusEl.textContent = text;
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleString('zh-TW', { hour12: false });
  } catch {
    return iso || '';
  }
}

function ensureModal() {
  let modal = document.getElementById('guestbook-modal');
  if (modal) return modal;
  modal = document.createElement('div');
  modal.id = 'guestbook-modal';
  modal.className = 'guestbook-modal';
  modal.hidden = true;
  modal.innerHTML = `
    <div class="guestbook-modal-card">
      <div class="guestbook-modal-title">刪除像素便條紙</div>
      <div class="guestbook-modal-copy">只有管理員知道密碼。輸入後就會把這張便條紙移除。</div>
      <input class="guestbook-password-input" id="guestbook-password-input" type="password" inputmode="numeric" placeholder="輸入刪除密碼" />
      <div class="guestbook-modal-actions">
        <button class="cmd-btn" id="guestbook-cancel-btn" type="button">取消</button>
        <button class="cmd-btn" id="guestbook-delete-btn" type="button">刪除</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  modal.querySelector('#guestbook-cancel-btn')?.addEventListener('click', () => {
    modal.hidden = true;
    pendingDeleteId = null;
  });
  modal.querySelector('#guestbook-delete-btn')?.addEventListener('click', submitDelete);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.hidden = true;
      pendingDeleteId = null;
    }
  });
  return modal;
}

function burstSticker(target, symbol = '❤') {
  if (!target) return;
  const sticker = document.createElement('div');
  sticker.textContent = symbol;
  sticker.style.position = 'absolute';
  sticker.style.right = '10px';
  sticker.style.top = '-4px';
  sticker.style.fontSize = '16px';
  sticker.style.pointerEvents = 'none';
  sticker.style.zIndex = '3';
  sticker.style.animation = 'sticker-burst 0.8s ease-out forwards';
  target.appendChild(sticker);
  window.setTimeout(() => sticker.remove(), 820);
}

function renderNotes(notes) {
  if (!listEl) return;
  const prevIds = lastRenderedIds;
  lastRenderedIds = notes.map((note) => note.id);
  if (!notes.length) {
    listEl.innerHTML = '<div class="guestbook-empty">還沒有便條紙，來貼第一張吧。</div>';
    return;
  }
  listEl.innerHTML = notes.map((note) => `
    <article class="guestbook-note" data-id="${escHtml(note.id)}">
      <div class="guestbook-note-head">
        <div class="guestbook-note-name">
          ${escHtml(note.nickname || '匿名訪客')}
          <span class="guestbook-note-time">${escHtml(formatTime(note.created_at))}</span>
        </div>
        <button class="guestbook-delete" type="button" data-delete-id="${escHtml(note.id)}">X</button>
      </div>
      <div class="guestbook-note-text">${escHtml(note.message || '')}</div>
    </article>
  `).join('');

  listEl.querySelectorAll('.guestbook-note').forEach((noteEl) => {
    const isNew = !prevIds.includes(noteEl.dataset.id);
    if (isNew) {
      noteEl.style.animation = 'note-pop-in 0.35s ease-out';
      burstSticker(noteEl, ['❤', '★', '✦'][Math.floor(Math.random() * 3)]);
    }
  });

  listEl.querySelectorAll('[data-delete-id]').forEach((btn) => {
    btn.addEventListener('click', () => {
      pendingDeleteId = btn.dataset.deleteId;
      const modal = ensureModal();
      modal.hidden = false;
      modal.querySelector('#guestbook-password-input')?.focus();
    });
  });
}

async function loadNotes() {
  if (!supabase) {
    setStatus('尚未接上 Supabase，先把 guestbook-config.js 填好。');
    renderNotes([]);
    return;
  }
  setStatus('正在讀取像素便條紙…');
  const { data, error } = await supabase
    .from('guestbook_notes')
    .select('id,nickname,message,created_at')
    .order('created_at', { ascending: false })
    .limit(50);
  if (error) {
    setStatus(`留言板讀取失敗：${error.message}`);
    renderNotes([]);
    return;
  }
  renderNotes(data || []);
  setStatus('留言板已同步。');
}

async function submitNote(e) {
  e?.preventDefault?.();
  if (!supabase) {
    setStatus('Supabase 尚未設定完成，所以目前不能送出留言。');
    return;
  }
  const nickname = (nameEl?.value || '').trim() || '匿名訪客';
  const message = (messageEl?.value || '').trim();
  if (!message) {
    setStatus('先寫點內容再貼上便條紙吧。');
    return;
  }
  setStatus('正在貼上便條紙…');
  const { error } = await supabase.from('guestbook_notes').insert({ nickname, message });
  if (error) {
    setStatus(`送出失敗：${error.message}`);
    return;
  }
  if (messageEl) messageEl.value = '';
  if (nameEl && !nameEl.value.trim()) nameEl.value = '';
  setStatus('便條紙貼上成功 ✦');
  await loadNotes();
}

async function submitDelete() {
  if (!pendingDeleteId) return;
  const modal = ensureModal();
  const password = modal.querySelector('#guestbook-password-input')?.value || '';
  if (!cfg.deleteFunctionUrl) {
    setStatus('刪除功能尚未接上後端函式。');
    return;
  }
  setStatus('正在驗證密碼並刪除…');
  const res = await fetch(cfg.deleteFunctionUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ noteId: pendingDeleteId, password }),
  });
  const text = await res.text();
  if (!res.ok) {
    setStatus(`刪除失敗：${text || res.status}`);
    return;
  }
  modal.hidden = true;
  modal.querySelector('#guestbook-password-input').value = '';
  pendingDeleteId = null;
  setStatus('便條紙已刪除。');
  await loadNotes();
}

function initGuestbook() {
  formEl?.addEventListener('submit', submitNote);
  if (cfg.supabaseUrl && cfg.supabaseAnonKey) {
    supabase = createClient(cfg.supabaseUrl, cfg.supabaseAnonKey);
    loadNotes();
    supabase
      .channel('guestbook-notes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'guestbook_notes' }, () => loadNotes())
      .subscribe();
  } else {
    setStatus('尚未接上 Supabase，先把 guestbook-config.js 填好。');
    renderNotes([]);
  }
}

initGuestbook();
