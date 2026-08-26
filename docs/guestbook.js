import { guestbookCfg as cfg, supabase } from './supabase-client.js?v=75';

const statusEl = document.getElementById('guestbook-status');
const listEl = document.getElementById('guestbook-list');
const formEl = document.getElementById('guestbook-form');
const nameEl = document.getElementById('guestbook-name');
const messageEl = document.getElementById('guestbook-message');
const websiteEl = document.getElementById('guestbook-website');
const moreBtn = document.getElementById('guestbook-more');

let pendingDeleteId = null;
let lastRenderedIds = [];
let allNotes = [];
let visibleNoteCount = 3;
let deleteTriggerEl = null;
let submitting = false;
const SUBMIT_COOLDOWN_MS = 30_000;
const LAST_SUBMIT_KEY = 'doggo-guestbook-last-submit-v1';

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
    return new Date(iso).toLocaleString('zh-TW', {
      hour12: false,
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Taipei',
    });
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
    <div class="guestbook-modal-card" role="dialog" aria-modal="true" aria-labelledby="guestbook-modal-title">
      <div class="guestbook-modal-title" id="guestbook-modal-title">管理像素便條紙</div>
      <div class="guestbook-modal-copy">只有管理員知道密碼。輸入後就會把這張便條紙移除。</div>
      <label for="guestbook-password-input">管理員密碼</label>
      <input class="guestbook-password-input" id="guestbook-password-input" type="password" inputmode="numeric" autocomplete="current-password" placeholder="輸入刪除密碼" />
      <div class="guestbook-modal-status" id="guestbook-modal-status" role="status" aria-live="polite"></div>
      <div class="guestbook-modal-actions">
        <button class="cmd-btn" id="guestbook-cancel-btn" type="button">取消</button>
        <button class="cmd-btn" id="guestbook-delete-btn" type="button">刪除</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  modal.querySelector('#guestbook-cancel-btn')?.addEventListener('click', closeDeleteModal);
  modal.querySelector('#guestbook-delete-btn')?.addEventListener('click', submitDelete);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      closeDeleteModal();
    }
  });
  modal.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeDeleteModal();
    if (e.key !== 'Tab') return;
    const focusable = [...modal.querySelectorAll('input, button')].filter((el) => !el.disabled);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });
  return modal;
}

function closeDeleteModal() {
  const modal = document.getElementById('guestbook-modal');
  if (modal) {
    modal.hidden = true;
    const modalStatus = modal.querySelector('#guestbook-modal-status');
    if (modalStatus) modalStatus.textContent = '';
  }
  const page = document.querySelector('.dream-shell');
  if (page) page.inert = false;
  pendingDeleteId = null;
  deleteTriggerEl?.focus();
  deleteTriggerEl = null;
}

function burstSticker(target, symbol = '❤') {
  if (!target) return;
  target.classList.remove('note-wall-pulse');
  void target.offsetWidth;
  target.classList.add('note-wall-pulse');
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
  window.setTimeout(() => {
    sticker.remove();
    target.classList.remove('note-wall-pulse');
  }, 820);
}

function noteLabel(note, index) {
  const text = `${note.nickname || ''} ${note.message || ''}`.toLowerCase();
  if (/愛|喜歡|可愛|抱抱|讚|❤️|❤|♥|love/.test(text)) return 'LOVE';
  if (/急|救|壞|bug|錯|error|不行|有問題|help|求救|緊急/.test(text)) return 'ALERT';
  if (/嗨|hello|hi|哈囉|你好|晚安|早安|安安|路過/.test(text)) return 'MAIL';
  if (/汪|狗|骨頭|散步|尾巴|罐罐/.test(text)) return 'WOOF';
  const fallback = ['QUEST', 'MAIL', 'LOVE', 'WOOF'];
  return fallback[index % fallback.length];
}

function renderNotes(notes) {
  if (!listEl) return;
  const prevIds = lastRenderedIds;
  allNotes = notes;
  const visibleNotes = notes.slice(0, visibleNoteCount);
  lastRenderedIds = visibleNotes.map((note) => note.id);
  if (!notes.length) {
    listEl.innerHTML = '<div class="guestbook-empty">牆上還沒有便條紙，來替狗狗貼第一張吧。</div>';
    if (moreBtn) moreBtn.hidden = true;
    return;
  }
  listEl.innerHTML = visibleNotes.map((note, index) => `
    <article class="guestbook-note" data-id="${escHtml(note.id)}" data-label="${escHtml(noteLabel(note, index))}">
      <div class="guestbook-note-head">
        <div class="guestbook-note-name">
          ${escHtml(note.nickname || '匿名訪客')}
          <span class="guestbook-note-time">${escHtml(formatTime(note.created_at))}</span>
        </div>
        <button class="guestbook-delete" type="button" data-delete-id="${escHtml(note.id)}" aria-label="管理 ${escHtml(note.nickname || '匿名訪客')} 的留言">管理</button>
      </div>
      <div class="guestbook-note-text">${escHtml(note.message || '')}</div>
    </article>
  `).join('');
  if (moreBtn) {
    moreBtn.hidden = notes.length <= visibleNoteCount;
    moreBtn.textContent = `顯示更多留言（還有 ${Math.max(notes.length - visibleNoteCount, 0)} 則）`;
  }

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
      deleteTriggerEl = btn;
      const modal = ensureModal();
      const page = document.querySelector('.dream-shell');
      if (page) page.inert = true;
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
    console.warn('guestbook load failed', error);
    setStatus('留言板暫時無法連線，狗狗會稍後再試。');
    renderNotes([]);
    return;
  }
  renderNotes(data || []);
  setStatus('留言板已同步。');
}

async function submitNote(e) {
  e?.preventDefault?.();
  if (submitting) return;
  if (!supabase || !cfg.submitFunctionUrl) {
    setStatus('留言功能尚未設定完成，所以目前不能送出留言。');
    return;
  }
  const nickname = (nameEl?.value || '').trim() || '匿名訪客';
  const message = (messageEl?.value || '').trim();
  if (websiteEl?.value) {
    setStatus('便條紙貼上成功 ✦');
    return;
  }
  if (!message) {
    setStatus('先寫點內容再貼上便條紙吧。');
    return;
  }
  let lastSubmitAt = 0;
  try { lastSubmitAt = Number(localStorage.getItem(LAST_SUBMIT_KEY) || 0); } catch {}
  const remaining = SUBMIT_COOLDOWN_MS - (Date.now() - lastSubmitAt);
  if (remaining > 0) {
    setStatus(`請再等 ${Math.ceil(remaining / 1000)} 秒，讓狗狗把上一張便條紙貼好。`);
    return;
  }
  setStatus('正在貼上便條紙…');
  submitting = true;
  const submitBtn = formEl?.querySelector('button[type="submit"]');
  if (submitBtn) submitBtn.disabled = true;
  const releaseSubmit = () => {
    submitting = false;
    if (submitBtn) submitBtn.disabled = false;
  };
  const createdAt = new Date().toISOString();
  let submitRes;
  try {
    submitRes = await fetch(cfg.submitFunctionUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        apikey: cfg.supabaseAnonKey,
        Authorization: `Bearer ${cfg.supabaseAnonKey}`,
      },
      body: JSON.stringify({ nickname, message, createdAt }),
    });
  } catch (error) {
    console.warn('guestbook submit unavailable', error);
    setStatus('留言暫時無法送出，請稍後再試。');
    releaseSubmit();
    return;
  }
  if (!submitRes.ok) {
    console.warn('guestbook submit failed', submitRes.status);
    setStatus(submitRes.status === 429 ? '留言送得有點快，請稍後再試。' : '留言暫時無法送出，請稍後再試。');
    releaseSubmit();
    return;
  }
  try { localStorage.setItem(LAST_SUBMIT_KEY, String(Date.now())); } catch {}
  if (messageEl) messageEl.value = '';
  if (nameEl && !nameEl.value.trim()) nameEl.value = '';
  setStatus('便條紙貼上成功 ✦');
  try {
    await loadNotes();
  } finally {
    releaseSubmit();
  }
}

async function submitDelete() {
  if (!pendingDeleteId) return;
  const modal = ensureModal();
  const password = modal.querySelector('#guestbook-password-input')?.value || '';
  const modalStatus = modal.querySelector('#guestbook-modal-status');
  if (!cfg.deleteFunctionUrl) {
    setStatus('刪除功能尚未接上後端函式。');
    return;
  }
  setStatus('正在驗證密碼並刪除…');
  if (modalStatus) modalStatus.textContent = '正在驗證管理員密碼…';
  try {
    const res = await fetch(cfg.deleteFunctionUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ noteId: pendingDeleteId, password }),
    });
    const text = await res.text();
    if (!res.ok) {
      console.warn('guestbook delete failed', res.status, text);
      setStatus('管理驗證失敗，便條紙沒有被刪除。');
      if (modalStatus) modalStatus.textContent = res.status === 429 ? '嘗試次數太快，請稍後再試。' : '密碼不正確，便條紙沒有被刪除。';
      modal.querySelector('#guestbook-password-input')?.focus();
      return;
    }
    modal.querySelector('#guestbook-password-input').value = '';
    closeDeleteModal();
    setStatus('便條紙已刪除。');
    await loadNotes();
  } catch (error) {
    console.warn('guestbook delete unavailable', error);
    setStatus('管理功能暫時無法連線，便條紙沒有被刪除。');
    if (modalStatus) modalStatus.textContent = '管理功能暫時無法連線，請稍後再試。';
    modal.querySelector('#guestbook-password-input')?.focus();
  }
}

function initGuestbook() {
  formEl?.addEventListener('submit', submitNote);
  moreBtn?.addEventListener('click', () => {
    visibleNoteCount += 6;
    renderNotes(allNotes);
  });
  if (supabase) {
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
window.__DOGGO_GUESTBOOK_READY__ = true;
