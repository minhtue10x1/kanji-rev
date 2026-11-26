/**
 * IT Nihongo Studio — Tactile Motion, SVG Iconography & Keyboard-First Engine
 * Standalone module providing:
 *   1. Crisp 1.5px stroke Lucide-style SVG icons (zero emoji clutter)
 *   2. Linear-style mouse-tracking spotlight hover on cards
 *   3. Spring-physics sliding pill indicator for Nav, Chapter Pills, and Subtabs
 *   4. Lightweight micro-confetti canvas burst on correct answers
 *   5. Keyboard-first study shortcuts (1-4, Space, ArrowLeft/Right, Enter, S, Esc)
 */
(function (global) {
  'use strict';

  const ICON_PATHS = {
    book: '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    zap: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    layers: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    puzzle: '<path d="M19.439 7.85c-.049.322.059.648.289.878l1.568 1.568c.47.47.706 1.087.706 1.704s-.235 1.233-.706 1.704l-1.611 1.611a.98.98 0 0 1-.837.276c-.47-.07-.802-.48-.968-.925a2.501 2.501 0 1 0-3.214 3.214c.446.166.855.497.925.968a.979.979 0 0 1-.276.837l-1.61 1.61a2.404 2.404 0 0 1-1.705.707 2.402 2.402 0 0 1-1.704-.706l-1.568-1.568a1.026 1.026 0 0 0-.877-.29c-.493.074-.84.504-1.02.968a2.5 2.5 0 1 1-3.237-3.237c.464-.18.894-.527.967-1.02a1.026 1.026 0 0 0-.289-.877l-1.568-1.568A2.402 2.402 0 0 1 1.998 12c0-.617.236-1.234.706-1.704L4.23 8.77c.24-.24.581-.353.917-.303.515.077.877.528 1.073 1.01a2.5 2.5 0 1 0 3.259-3.259c-.482-.196-.933-.558-1.01-1.073-.05-.336.062-.676.303-.917l1.525-1.525A2.402 2.402 0 0 1 12 1.998c.617 0 1.234.236 1.704.706l1.568 1.568c.23.23.556.338.877.29.493-.074.84-.504 1.02-.968a2.5 2.5 0 1 1 3.237 3.237c-.464.18-.894.527-.967 1.02Z"/>',
    target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    fileText: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    briefcase: '<rect width="20" height="14" x="2" y="7" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    flame: '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    volume: '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>',
    check: '<polyline points="20 6 9 17 4 12"/>',
    clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    eye: '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    eyeOff: '<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/>',
    arrowLeft: '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    arrowRight: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    alertCircle: '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
    sparkles: '<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>',
    rotateCw: '<path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/>',
    messageSquare: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    lightbulb: '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>',
    terminal: '<polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/>',
    award: '<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>'
  };

  function icon(name, cls = '') {
    const path = ICON_PATHS[name] || '';
    return `<svg class="it-svg ${cls}" viewBox="0 0 24 24" aria-hidden="true">${path}</svg>`;
  }

  function syncSlider(container) {
    if (!container) return;
    const active = container.querySelector('.active');
    let bg = container.querySelector(':scope > .it-sliding-bg');
    if (!active) {
      if (bg) bg.style.opacity = '0';
      return;
    }
    if (!bg) {
      bg = document.createElement('span');
      bg.className = 'it-sliding-bg';
      bg.setAttribute('aria-hidden', 'true');
      container.prepend(bg);
    }
    const left = active.offsetLeft;
    const top = active.offsetTop;
    const width = active.offsetWidth;
    const height = active.offsetHeight;
    if (width === 0 || height === 0) return;
    bg.style.opacity = '1';
    bg.style.width = `${width}px`;
    bg.style.height = `${height}px`;
    bg.style.transform = `translate3d(${left}px, ${top}px, 0)`;
  }

  function syncAllSliders() {
    if (document.documentElement.getAttribute('data-workspace') !== 'it') return;
    requestAnimationFrame(() => {
      syncSlider(document.querySelector('nav.it-only'));
      syncSlider(document.getElementById('it-chapter-pills'));
    });
  }

  function initSpotlight() {
    const view = document.getElementById('view-it');
    if (!view || view._itSpotlightBound) return;
    view._itSpotlightBound = true;
    view.addEventListener('pointermove', (e) => {
      const card = e.target.closest('.it-unit-card, .it-practice-mode-card, .it-vocab-item');
      if (!card) return;
      const rect = card.getBoundingClientRect();
      card.style.setProperty('--mx', `${e.clientX - rect.left}px`);
      card.style.setProperty('--my', `${e.clientY - rect.top}px`);
    }, { passive: true });
  }

  function burstConfetti(originEl) {
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const rect = originEl ? originEl.getBoundingClientRect() : { left: window.innerWidth / 2, top: window.innerHeight / 2, width: 0, height: 0 };
    const cx = rect.left + rect.width * 0.5;
    const cy = rect.top + rect.height * 0.5;

    const canvas = document.createElement('canvas');
    canvas.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:9999;';
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    document.body.appendChild(canvas);
    const ctx = canvas.getContext('2d');

    const colors = ['#38BDF8', '#34D399', '#FBBF24', '#F2F0EA', '#818CF8'];
    const particles = Array.from({ length: 22 }, () => {
      const angle = Math.random() * Math.PI * 2;
      const speed = 2.4 + Math.random() * 4.8;
      return {
        x: cx,
        y: cy,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 2.4,
        size: 3 + Math.random() * 3.5,
        rot: Math.random() * Math.PI,
        vrot: (Math.random() - 0.5) * 0.28,
        color: colors[Math.floor(Math.random() * colors.length)],
        life: 1
      };
    });

    const start = performance.now();
    function frame(now) {
      const elapsed = now - start;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      let alive = false;
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.16;
        p.vx *= 0.985;
        p.rot += p.vrot;
        p.life = Math.max(0, 1 - elapsed / 620);
        if (p.life > 0) {
          alive = true;
          ctx.save();
          ctx.globalAlpha = p.life;
          ctx.translate(p.x, p.y);
          ctx.rotate(p.rot);
          ctx.fillStyle = p.color;
          ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.65);
          ctx.restore();
        }
      }
      if (alive && elapsed < 660) {
        requestAnimationFrame(frame);
      } else {
        canvas.remove();
      }
    }
    requestAnimationFrame(frame);
  }

  function initKeyboard() {
    if (window._itKeyboardBound) return;
    window._itKeyboardBound = true;
    document.addEventListener('keydown', (e) => {
      if (document.documentElement.getAttribute('data-workspace') !== 'it') return;
      const tag = (e.target && e.target.tagName || '').toUpperCase();
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      const it = global.app && global.app.itWorkspace;
      if (!it || !it.study) return;
      const studyPanel = document.getElementById('it-study-panel');
      if (!studyPanel || studyPanel.style.display === 'none') return;

      const st = it.study;
      if (e.key === 'Escape') {
        e.preventDefault();
        it.exitStudy();
        return;
      }
      if (st.index >= st.queue.length) {
        if (e.key === 'Enter') {
          e.preventDefault();
          it.exitStudy();
        }
        return;
      }
      const item = st.queue[st.index];
      if (e.key === 's' || e.key === 'S') {
        e.preventDefault();
        const text = (st.mode === 'cloze' && item.clozeSentence) ? item.clozeSentence.ja : item.word;
        if (global.app && text) global.app.speakText(text);
        return;
      }
      if (st.mode === 'flashcard') {
        if (e.code === 'Space') {
          e.preventDefault();
          it.flipFlashcard();
        } else if (e.key === 'ArrowLeft') {
          e.preventDefault();
          it.answerFlashcard(false);
        } else if (e.key === 'ArrowRight') {
          e.preventDefault();
          it.answerFlashcard(true);
        }
      } else {
        if (!st.answered && ['1', '2', '3', '4'].includes(e.key)) {
          e.preventDefault();
          const idx = Number(e.key) - 1;
          if (st.currentOptions && idx < st.currentOptions.length) {
            it.selectQuizOption(idx);
          }
        } else if (st.answered && (e.key === 'Enter' || e.key === 'ArrowRight')) {
          e.preventDefault();
          it.nextQuizStep();
        }
      }
    });
  }

  window.addEventListener('resize', syncAllSliders);

  global.ITMotion = {
    icon,
    syncSlider,
    syncAllSliders,
    initSpotlight,
    burstConfetti,
    initKeyboard
  };
})(window);
