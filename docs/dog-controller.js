const DOG_LINES = {
  idle: ['汪，我幫你盯著市場～', '今天目前風平浪靜，先摸魚一下。'],
  excited: ['汪！這則新聞有點重要喔！', '今天外面的世界很熱鬧！'],
  worried: ['嗚，我先幫你守著這些異動。', '這條任務卡一下，但我還在盯。'],
  sleepy: ['晚安模式啟動，我抱著枕頭值班。', '夜深了，我會安靜幫你顧著。'],
  bone: ['耶，得到獎勵骨頭了！', '汪汪，這次做得不錯吧。'],
  work: ['工作眼鏡戴好了，準備上工。', '我正在很認真看資料喔。'],
  ok: ['全部看起來都順順的。', '今天的資料很乖，讚。'],
};

export function createDogController(options = {}) {
  const {
    mapStatus,
    taskBubbleText,
    dogGuideLine,
    onStateChange,
    getCurrentData,
    getCurrentState,
  } = options;

  let clickCount = 0;
  let clickTimer = null;

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

  function setDogState(state, bubbleText) {
    const el = document.getElementById('dog-sprite');
    if (!el) return;
    const allowed = ['idle', 'bone', 'excited', 'worried', 'sleepy', 'work', 'ok'];
    const next = allowed.includes(state) ? state : 'idle';
    el.dataset.dogState = next;
    if (bubbleText) setDogBubble(bubbleText);
    onStateChange?.(next);
  }

  function syncDog(data) {
    setDogState(resolveDogState(data));
  }

  function restoreDogScene() {
    const data = getCurrentData?.();
    if (!data) return;
    syncDog(data);
    setDogBubble(document.body.dataset.theme === 'night' ? pickDogLine('sleepy') : taskBubbleText(data, 0, 0));
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
      setDogBubble(pickDogLine(getCurrentState?.() || 'idle'));
      window.setTimeout(() => {
        el.classList.remove('dog-pet');
        busy = false;
      }, 320);
    };

    const handleClick = (part) => {
      clickCount += 1;
      clearTimeout(clickTimer);
      clickTimer = window.setTimeout(() => { clickCount = 0; }, 550);

      if (clickCount >= 3) {
        clickCount = 0;
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
      if (getCurrentState?.() !== 'sleepy') setDogState('work', '汪，我看向你了，有什麼想一起改的嗎？');
    });
    el.addEventListener('mouseleave', restoreDogScene);
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
        restoreDogScene();
      });
    });
  }

  return {
    bindDogPet,
    setDogBubble,
    setDogState,
    syncDog,
    restoreDogScene,
    pickDogLine,
  };
}
