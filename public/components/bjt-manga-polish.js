/**
 * BJT Business Prep — Modern Manga SFX, Speedlines, Ink Icons & Keyboard Engine
 * Standalone module (no dependency on ITMotion):
 *   1. Crisp 2px-stroke ink SVG icons
 *   2. Katakana Manga SFX pop (ビシッ！ / ナイス！ / 完璧！ / ガーン…)
 *   3. Radial Manga Speedlines flash (集中線) on Combo streaks
 *   4. Keyboard-first shortcuts for BJT Dokkai, Role-play, Cloze, Quiz & Flashcards
 */
(function (global) {
  'use strict';

  const ICON_PATHS = {
    award: '<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>',
    briefcase: '<rect width="20" height="14" x="2" y="7" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    mail: '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
    fileText: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    layers: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    zap: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    puzzle: '<path d="M19.439 7.85c-.049.322.059.648.289.878l1.568 1.568c.47.47.706 1.087.706 1.704s-.235 1.233-.706 1.704l-1.611 1.611a.98.98 0 0 1-.837.276c-.47-.07-.802-.48-.968-.925a2.501 2.501 0 1 0-3.214 3.214c.446.166.855.497.925.968a.979.979 0 0 1-.276.837l-1.61 1.61a2.404 2.404 0 0 1-1.705.707 2.402 2.402 0 0 1-1.704-.706l-1.568-1.568a1.026 1.026 0 0 0-.877-.29c-.493.074-.84.504-1.02.968a2.5 2.5 0 1 1-3.237-3.237c.464-.18.894-.527.967-1.02a1.026 1.026 0 0 0-.289-.877l-1.568-1.568A2.402 2.402 0 0 1 1.998 12c0-.617.236-1.234.706-1.704L4.23 8.77c.24-.24.581-.353.917-.303.515.077.877.528 1.073 1.01a2.5 2.5 0 1 0 3.259-3.259c-.482-.196-.933-.558-1.01-1.073-.05-.336.062-.676.303-.917l1.525-1.525A2.402 2.402 0 0 1 12 1.998c.617 0 1.234.236 1.704.706l1.568 1.568c.23.23.556.338.877.29.493-.074.84-.504 1.02-.968a2.5 2.5 0 1 1 3.237 3.237c-.464.18-.894.527-.967 1.02Z"/>',
    clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    volume: '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>',
    copy: '<rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
    check: '<polyline points="20 6 9 17 4 12"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    alertCircle: '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
    rotateCw: '<path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/>',
    table: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/><path d="M9 3v18"/>',
    messageSquare: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'
  };

  const GOOD_SFX = ['ビシッ！', 'ナイス！', '完璧！', '正解！', '流石！'];
  const BAD_SFX = ['ガーン…', 'おっと…', 'ドンマイ！'];

  function icon(name, cls = '') {
    const path = ICON_PATHS[name] || '';
    return `<svg class="bjt-svg ${cls}" viewBox="0 0 24 24" aria-hidden="true">${path}</svg>`;
  }

  function spawnSFX(originEl, isCorrect, combo = 0) {
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const rect = originEl ? originEl.getBoundingClientRect() : { left: window.innerWidth / 2, top: window.innerHeight / 2, width: 0, height: 0 };
    const el = document.createElement('div');
    let text = '';
    let kind = isCorrect ? 'good' : 'bad';
    if (isCorrect && combo >= 3) {
      text = `${combo}連勝!! ビシッ！`;
      kind = 'combo';
    } else if (isCorrect) {
      text = GOOD_SFX[Math.floor(Math.random() * GOOD_SFX.length)];
    } else {
      text = BAD_SFX[Math.floor(Math.random() * BAD_SFX.length)];
    }
    el.className = `manga-sfx-pop ${kind}`;
    el.textContent = text;
    el.style.left = `${Math.min(window.innerWidth - 90, Math.max(90, rect.left + rect.width * 0.5))}px`;
    el.style.top = `${Math.max(70, rect.top + 8)}px`;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 700);
  }

  function flashSpeedlines(containerEl) {
    if (!containerEl) return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const ring = document.createElement('div');
    ring.className = 'manga-speedlines-ring';
    containerEl.appendChild(ring);
    setTimeout(() => ring.remove(), 450);
  }

  function initKeyboard() {
    if (window._bjtKeyboardBound) return;
    window._bjtKeyboardBound = true;
    document.addEventListener('keydown', (e) => {
      if (document.documentElement.getAttribute('data-workspace') !== 'bjt') return;
      const tag = (e.target && e.target.tagName || '').toUpperCase();
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      const bjt = global.app && global.app.bjtWorkspace;
      if (!bjt) return;

      // 1. Dokkai CBT runner
      if (bjt.subView === 'dokkai' && bjt.dokkaiRun) {
        const st = bjt.dokkaiRun;
        if (st.index >= st.queue.length) return;
        if (!st.answered && ['1', '2', '3', '4'].includes(e.key)) {
          e.preventDefault();
          bjt.selectDokkaiOption(Number(e.key) - 1);
        } else if (st.answered && (e.key === 'Enter' || e.key === 'ArrowRight')) {
          e.preventDefault();
          bjt.nextDokkaiStep();
        }
        return;
      }

      // 2. Keigo Role-play & Flashcard
      if (bjt.subView === 'keigo') {
        if (bjt.keigoMode === 'roleplay' && bjt.keigoRoleplay) {
          const st = bjt.keigoRoleplay;
          if (st.index >= st.queue.length) return;
          if (!st.answered && ['1', '2', '3', '4'].includes(e.key)) {
            e.preventDefault();
            bjt.selectKeigoRoleplayOption(Number(e.key) - 1);
          } else if (st.answered && (e.key === 'Enter' || e.key === 'ArrowRight')) {
            e.preventDefault();
            bjt.nextKeigoRoleplayStep();
          }
          return;
        }
        if (bjt.keigoMode === 'flashcard' && bjt.keigoFlash) {
          if (e.code === 'Space') { e.preventDefault(); bjt.flipKeigoFlash(); }
          else if (e.key === 'ArrowLeft') { e.preventDefault(); bjt.answerKeigoFlash(false); }
          else if (e.key === 'ArrowRight') { e.preventDefault(); bjt.answerKeigoFlash(true); }
          return;
        }
      }

      // 3. Vocab Flashcard / Quiz / Cloze
      if (bjt.subView === 'vocab' && bjt.vocabStudy) {
        const st = bjt.vocabStudy;
        if (st.index >= st.queue.length) return;
        if (st.mode === 'flashcard') {
          if (e.code === 'Space') { e.preventDefault(); bjt.flipVocabFlash(); }
          else if (e.key === 'ArrowLeft') { e.preventDefault(); bjt.answerVocabFlash(false); }
          else if (e.key === 'ArrowRight') { e.preventDefault(); bjt.answerVocabFlash(true); }
        } else {
          if (!st.answered && ['1', '2', '3', '4'].includes(e.key)) {
            e.preventDefault();
            bjt.selectVocabQuizOption(Number(e.key) - 1);
          } else if (st.answered && (e.key === 'Enter' || e.key === 'ArrowRight')) {
            e.preventDefault();
            bjt.nextVocabQuizStep();
          }
        }
      }
    });
  }

  global.BJTManga = {
    icon,
    spawnSFX,
    flashSpeedlines,
    initKeyboard
  };
})(window);
