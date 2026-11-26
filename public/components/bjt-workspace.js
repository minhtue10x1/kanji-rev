/**
 * Standalone BJT Prep Workspace Component
 * 3 Core Non-Listening Modules:
 *   1. Keigo (敬語): Conversion table (Plain -> Sonkeigo / Kenjougo), Keigo Flashcards,
 *      and 9 workplace Keigo situations with Bad vs Good examples & mini-quizzes.
 *   2. Business Email (ビジネスメール): Ready-to-use Internal / External / General
 *      Japanese business email templates with 1-click copy, TTS, and Keigo notes.
 *   3. BJT Reading CBT (読解): Real BJT Part 3 Reading Comprehension questions
 *      with section filtering, optional CBT timer, and Vietnamese explanations.
 */
(function (global) {
  'use strict';

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function bjtIcon(name, cls = '') {
    return (global.BJTManga && typeof global.BJTManga.icon === 'function')
      ? global.BJTManga.icon(name, cls)
      : '';
  }

  class BJTWorkspace {
    constructor(app) {
      this.app = app;
      this.data = null;
      this.subView = 'keigo'; // 'keigo' | 'vocab' | 'email' | 'dokkai'
      this.keigoMode = 'table'; // 'table' | 'situations' | 'flashcard' | 'roleplay'
      this.keigoRoleplay = null;
      this.vocabCategory = 'all';
      this.vocabStudy = null;
      this.emailCategory = 'all';
      this.emailSkim = null;
      this.dokkaiSection = 'all';
      this.dokkaiSource = 'all';
      this.dokkaiRun = null;
      this.keigoFlash = null;
      this._timerInterval = null;
    }

    getProgress() {
      try {
        const raw = localStorage.getItem('kanji_bjt_progress_v1');
        if (raw) {
          const p = JSON.parse(raw);
          return {
            solvedDokkai: Array.isArray(p.solvedDokkai) ? p.solvedDokkai : [],
            masteredKeigo: Array.isArray(p.masteredKeigo) ? p.masteredKeigo : [],
            masteredVocab: Array.isArray(p.masteredVocab) ? p.masteredVocab : [],
            wrongDokkai: Array.isArray(p.wrongDokkai) ? p.wrongDokkai : [],
            wrongVocab: Array.isArray(p.wrongVocab) ? p.wrongVocab : [],
            wrongKeigo: Array.isArray(p.wrongKeigo) ? p.wrongKeigo : []
          };
        }
      } catch (e) {}
      return { solvedDokkai: [], masteredKeigo: [], masteredVocab: [], wrongDokkai: [], wrongVocab: [], wrongKeigo: [] };
    }

    saveProgress(prog) {
      localStorage.setItem('kanji_bjt_progress_v1', JSON.stringify(prog));
    }

    _recordMistake(bucket, id, isCorrect) {
      if (!id) return;
      const prog = this.getProgress();
      const list = prog[bucket] || [];
      const idx = list.indexOf(id);
      if (!isCorrect) {
        if (idx === -1) {
          list.push(id);
          prog[bucket] = list;
          this.saveProgress(prog);
        }
      } else if (idx !== -1) {
        list.splice(idx, 1);
        prog[bucket] = list;
        this.saveProgress(prog);
        this.app.showToast('✓ Đã gỡ khỏi sổ câu hay sai!');
      }
    }

    async ensureDataLoaded() {
      if (this.data) return true;
      const target = document.getElementById('bjt-keigo-body') || document.getElementById('bjt-vocab-body') || document.getElementById('bjt-dokkai-body');
      if (target) {
        target.innerHTML = '<div style="color:var(--text-muted); padding:2rem; text-align:center;">Đang tải dữ liệu BJT Prep...</div>';
      }
      try {
        const res = await fetch('/data/bjt-prep.json?v=3');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        this.data = await res.json();
        return true;
      } catch (e) {
        if (target) {
          target.innerHTML = '<div style="color:var(--danger); padding:2rem; text-align:center;">Không thể tải dữ liệu BJT. Vui lòng thử lại.</div>';
        }
        return false;
      }
    }

    _stopTimer() {
      if (this._timerInterval) {
        clearInterval(this._timerInterval);
        this._timerInterval = null;
      }
    }

    async navigateSubView(subView) {
      this.subView = subView;
      this._stopTimer();
      this.vocabStudy = null;
      this.emailSkim = null;
      if (this.app.currentView !== 'bjt') {
        this.app.navigate('bjt');
      }

      document.querySelectorAll('.bjt-nav-btn, .bjt-mobile-nav-item').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.bjtsub === subView);
      });

      const hashMap = { keigo: '#bjt', vocab: '#bjt/vocab', email: '#bjt/email', dokkai: '#bjt/dokkai' };
      if (hashMap[subView] && window.location.hash !== hashMap[subView]) {
        history.replaceState(null, '', hashMap[subView]);
      }

      ['bjt-keigo-panel', 'bjt-vocab-panel', 'bjt-email-panel', 'bjt-dokkai-panel'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
      });

      const ok = await this.ensureDataLoaded();
      if (!ok) return;

      if (subView === 'keigo') {
        document.getElementById('bjt-keigo-panel').style.display = 'block';
        this.renderKeigo();
      } else if (subView === 'vocab') {
        document.getElementById('bjt-vocab-panel').style.display = 'block';
        this.renderVocab();
      } else if (subView === 'email') {
        document.getElementById('bjt-email-panel').style.display = 'block';
        this.renderEmails();
      } else if (subView === 'dokkai') {
        document.getElementById('bjt-dokkai-panel').style.display = 'block';
        this.renderDokkaiHome();
      }

      if (global.BJTManga) global.BJTManga.initKeyboard();
    }

    // ==================== TAB 1: KEIGO ====================

    setKeigoMode(mode) {
      this.keigoMode = mode;
      document.querySelectorAll('#bjt-keigo-pills .it-pill-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.kmode === mode);
      });
      if (mode === 'flashcard') {
        this.startKeigoFlashcards();
      } else if (mode === 'roleplay') {
        this.startKeigoRoleplay(false);
      } else {
        this.renderKeigo();
      }
    }

    renderKeigo() {
      if (!this.data) return;
      const body = document.getElementById('bjt-keigo-body');
      if (!body) return;
      const prog = this.getProgress();

      const statsEl = document.getElementById('bjt-keigo-stats');
      if (statsEl) {
        const wrongNote = prog.wrongKeigo.length > 0 ? ` · 🔴 ${prog.wrongKeigo.length} câu hay sai` : '';
        statsEl.textContent = `Thuộc ${prog.masteredKeigo.length}/${(this.data.keigoTable || []).length} động từ Kính ngữ · ${(this.data.keigoSituations || []).length} tình huống${wrongNote}`;
      }
      const mistakeBtn = document.getElementById('bjt-keigo-mistake-btn');
      if (mistakeBtn) {
        mistakeBtn.style.display = prog.wrongKeigo.length > 0 ? 'inline-flex' : 'none';
        mistakeBtn.textContent = `🔴 Ôn ${prog.wrongKeigo.length} câu hay sai`;
      }

      if (this.keigoMode === 'flashcard') {
        this.renderKeigoFlashcardStep();
        return;
      }
      if (this.keigoMode === 'roleplay') {
        this.renderKeigoRoleplayStep();
        return;
      }

      if (this.keigoMode === 'table') {
        const q = ((document.getElementById('bjt-keigo-search') || {}).value || '').trim().toLowerCase();
        const rows = (this.data.keigoTable || []).filter(k => {
          if (!q) return true;
          return `${k.plain} ${k.reading} ${k.sonkeigo} ${k.kenjougo} ${k.vi}`.toLowerCase().includes(q);
        });

        body.innerHTML = `
          <div style="margin-bottom:0.9rem;">
            <input type="text" class="search-input" id="bjt-keigo-search" value="${escapeHtml(q)}" placeholder="Tìm động từ (VD: 行く, 見る, 確認, đi, xem)..." oninput="app.bjtWorkspace.renderKeigo()" style="width:100%;">
          </div>
          <div class="bjt-keigo-grid">
            ${rows.map((k, idx) => {
              const isM = prog.masteredKeigo.includes(k.id);
              const exSafe = escapeHtml(k.exampleJa || k.sonkeigo).replace(/'/g, "\\'");
              return `
                <div class="bjt-keigo-card bjt-stagger ${isM ? 'mastered' : ''}" style="--i:${Math.min(idx, 18)};">
                  ${isM ? '<span class="bjt-hanko-stamp" aria-label="Đã thuộc">済</span>' : ''}
                  <div style="display:flex; justify-content:space-between; align-items:center; gap:0.5rem;">
                    <div>
                      <span style="font-family:var(--font-manga-jp, var(--font-jp)); font-size:1.15rem; font-weight:700; color:var(--text);">${escapeHtml(k.plain)}</span>
                      <span style="font-family:var(--font-jp); font-size:0.82rem; color:var(--text-muted); margin-left:0.35rem;">(${escapeHtml(k.reading || '')})</span>
                      <span style="font-size:0.86rem; font-weight:600; color:var(--accent); margin-left:0.4rem;">${escapeHtml(k.vi)}</span>
                    </div>
                    <div style="display:flex; gap:0.3rem;">
                      <button class="icon-btn" title="Nghe ví dụ" onclick="app.speakText('${exSafe}')" style="width:1.75rem;height:1.75rem;">${bjtIcon('volume', 'bjt-svg-sm')}</button>
                      <button class="icon-btn" title="${isM ? 'Đã thuộc' : 'Đánh dấu đã thuộc'}" onclick="app.bjtWorkspace.toggleKeigoMastered('${escapeHtml(k.id)}')" style="width:1.75rem;height:1.75rem; ${isM ? 'background:var(--success-soft);color:var(--success);border-color:var(--success);' : ''}">${bjtIcon('check', 'bjt-svg-sm')}</button>
                    </div>
                  </div>
                  <div class="bjt-keigo-rows">
                    <div class="bjt-keigo-row"><span class="bjt-tag sonkei">尊敬語 (Tôn kính)</span> <strong style="font-family:var(--font-jp);">${escapeHtml(k.sonkeigo)}</strong></div>
                    <div class="bjt-keigo-row"><span class="bjt-tag kenjou">謙譲語 (Khiêm nhường)</span> <strong style="font-family:var(--font-jp);">${escapeHtml(k.kenjougo)}</strong></div>
                  </div>
                  ${k.exampleJa ? `
                    <div style="font-size:0.82rem; color:var(--text-muted); border-top:1px dashed var(--border); padding-top:0.45rem; margin-top:0.35rem;">
                      <div style="font-family:var(--font-jp); color:var(--text);">${escapeHtml(k.exampleJa)}</div>
                      <div>${escapeHtml(k.exampleVi || '')}</div>
                    </div>
                  ` : ''}
                </div>
              `;
            }).join('')}
          </div>
        `;
      } else {
        // Situations mode
        const sits = this.data.keigoSituations || [];
        body.innerHTML = sits.map((s, idx) => `
          <div class="bjt-situation-card" id="bjt-sit-${idx}">
            <div style="font-size:0.76rem; font-weight:700; color:var(--accent); margin-bottom:0.2rem;">TÌNH HUỐNG ${idx + 1} · 敬語トレーニング</div>
            <div style="font-family:var(--font-jp); font-size:1.12rem; font-weight:700; color:var(--text);">${escapeHtml(s.titleJa)} — <span style="font-family:var(--font-ui); font-weight:600; color:var(--text-muted);">${escapeHtml(s.titleVi)}</span></div>

            <div class="bjt-compare-grid">
              <div class="bjt-compare-box bad">
                <div style="font-size:0.74rem; font-weight:700; color:var(--danger); margin-bottom:0.25rem;">✗ NÊN TRÁNH (Thẳng thừng / Sai vai vế)</div>
                <div style="font-family:var(--font-jp); font-size:0.94rem; color:var(--text);">${escapeHtml(s.badJa)}</div>
              </div>
              <div class="bjt-compare-box good">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.25rem;">
                  <span style="font-size:0.74rem; font-weight:700; color:var(--success);">✓ CHUẨN CÔNG SỞ NHẬT</span>
                  <button class="icon-btn" onclick="app.speakText('${escapeHtml(s.goodJa).replace(/'/g, "\\'")}')" style="width:1.6rem;height:1.6rem;font-size:0.72rem;">🔊</button>
                </div>
                <div style="font-family:var(--font-jp); font-size:0.95rem; font-weight:600; color:var(--text);">${escapeHtml(s.goodJa)}</div>
                <div style="font-size:0.82rem; color:var(--text-muted); margin-top:0.25rem;">${escapeHtml(s.vi || '')}</div>
              </div>
            </div>

            <div class="it-tip-card" style="margin:0.75rem 0;">
              <div style="font-size:0.83rem; color:var(--text-muted); line-height:1.5;">💡 ${escapeHtml(s.tipVi || '')}</div>
            </div>

            ${s.quiz ? `
              <div style="margin-top:0.75rem; padding-top:0.75rem; border-top:1px solid var(--border);">
                <div style="font-size:0.86rem; font-weight:600; color:var(--text); margin-bottom:0.55rem;">🎯 Mini-Quiz: ${escapeHtml(s.quiz.questionJa)}</div>
                ${(s.quiz.options || []).map((opt, oIdx) => `
                  <button class="it-practice-opt" onclick="app.bjtWorkspace.answerSituationQuiz(${idx}, ${oIdx})">${escapeHtml(opt)}</button>
                `).join('')}
                <div id="bjt-sit-fb-${idx}" style="display:none; margin-top:0.5rem; padding:0.7rem; border-radius:8px; background:var(--surface-elevated); font-size:0.84rem;"></div>
              </div>
            ` : ''}
          </div>
        `).join('');
      }
    }

    toggleKeigoMastered(id) {
      const prog = this.getProgress();
      const i = prog.masteredKeigo.indexOf(id);
      if (i === -1) prog.masteredKeigo.push(id);
      else prog.masteredKeigo.splice(i, 1);
      this.saveProgress(prog);
      this.renderKeigo();
    }

    answerSituationQuiz(sIdx, oIdx) {
      const s = (this.data.keigoSituations || [])[sIdx];
      if (!s || !s.quiz) return;
      const card = document.getElementById(`bjt-sit-${sIdx}`);
      if (!card) return;
      const isCorrect = oIdx === s.quiz.answerIndex;
      const btns = card.querySelectorAll('.it-practice-opt');
      btns.forEach((btn, idx) => {
        if (idx === s.quiz.answerIndex) btn.classList.add('correct');
        else if (idx === oIdx && !isCorrect) btn.classList.add('incorrect');
        btn.disabled = true;
      });
      if (global.BJTManga) {
        global.BJTManga.spawnSFX(btns[oIdx], isCorrect, 0);
        if (isCorrect) global.BJTManga.flashSpeedlines(card);
      }
      const fb = document.getElementById(`bjt-sit-fb-${sIdx}`);
      if (fb) {
        fb.style.display = 'block';
        fb.innerHTML = `<strong style="color:${isCorrect ? 'var(--success)' : 'var(--danger)'};">${isCorrect ? '✓ Chính xác!' : '✗ Chưa chính xác'}</strong> — ${escapeHtml(s.quiz.explanationVi || '')}`;
      }
    }

    startKeigoFlashcards() {
      if (!this.data || !this.data.keigoTable) return;
      const queue = [...this.data.keigoTable].sort(() => Math.random() - 0.5);
      this.keigoFlash = { queue, index: 0, flipped: false };
      this.renderKeigoFlashcardStep();
    }

    renderKeigoFlashcardStep() {
      const body = document.getElementById('bjt-keigo-body');
      const st = this.keigoFlash;
      if (!body || !st) return;

      if (st.index >= st.queue.length) {
        body.innerHTML = `
          <div style="background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:2rem; text-align:center;">
            <div style="font-size:2.4rem; margin-bottom:0.5rem;">🎉</div>
            <div style="font-size:1.2rem; font-weight:700; color:var(--text); margin-bottom:0.4rem;">Hoàn thành ôn Flashcard Kính ngữ!</div>
            <button class="btn btn-primary" onclick="app.bjtWorkspace.startKeigoFlashcards()">Ôn lại từ đầu →</button>
          </div>
        `;
        return;
      }

      const k = st.queue[st.index];
      const exSafe = escapeHtml(k.exampleJa || k.sonkeigo).replace(/'/g, "\\'");
      body.innerHTML = `
        <div style="text-align:center; font-family:var(--font-mono); font-size:0.82rem; font-weight:700; color:var(--text-muted); margin-bottom:0.65rem;">Thẻ ${st.index + 1} / ${st.queue.length}</div>
        <div class="bjt-fc-scene">
          <div class="bjt-fc-card ${st.flipped ? 'is-flipped' : ''}" id="bjt-kfc-card" onclick="app.bjtWorkspace.flipKeigoFlash()">
            <div class="bjt-fc-face">
              <span class="it-badge" style="margin-bottom:0.85rem;">尊敬語・謙譲語</span>
              <div style="font-family:var(--font-manga-jp, var(--font-jp)); font-size:2.35rem; font-weight:700; color:var(--text);">${escapeHtml(k.plain)}</div>
              <div style="font-size:0.95rem; color:var(--text-muted); margin-top:0.35rem;">(${escapeHtml(k.reading || '')}) — ${escapeHtml(k.vi)}</div>
              <div style="position:absolute; bottom:0.9rem; font-size:0.74rem; color:var(--text-subtle); display:inline-flex; align-items:center; gap:0.35rem;">${bjtIcon('rotateCw', 'bjt-svg-sm')} <span>Bấm thẻ hoặc Space để lật</span></div>
            </div>
            <div class="bjt-fc-face bjt-fc-back">
              <div style="width:100%; max-width:440px; text-align:left; display:flex; flex-direction:column; gap:0.5rem;">
                <div style="font-family:var(--font-manga-jp, var(--font-jp)); font-size:1.15rem; font-weight:700; color:var(--text); margin-bottom:0.15rem;">${escapeHtml(k.plain)} <span style="font-size:0.85rem; color:var(--text-muted); font-weight:500;">— ${escapeHtml(k.vi)}</span></div>
                <div class="bjt-keigo-row"><span class="bjt-tag sonkei">尊敬語</span> <strong style="font-family:var(--font-jp); font-size:1.05rem;">${escapeHtml(k.sonkeigo)}</strong></div>
                <div class="bjt-keigo-row"><span class="bjt-tag kenjou">謙譲語</span> <strong style="font-family:var(--font-jp); font-size:1.05rem;">${escapeHtml(k.kenjougo)}</strong></div>
                ${k.exampleJa ? `
                  <div style="font-size:0.84rem; color:var(--text-muted); margin-top:0.35rem; border-top:1.5px dashed var(--border); padding-top:0.45rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; gap:0.4rem;">
                      <span style="font-family:var(--font-jp); color:var(--text);">${escapeHtml(k.exampleJa)}</span>
                      <button class="icon-btn" onclick="event.stopPropagation(); app.speakText('${exSafe}')" style="width:1.75rem;height:1.75rem;">${bjtIcon('volume', 'bjt-svg-sm')}</button>
                    </div>
                    <div>${escapeHtml(k.exampleVi || '')}</div>
                  </div>
                ` : ''}
              </div>
            </div>
          </div>
        </div>
        <div style="display:flex; gap:0.75rem; justify-content:center; margin-top:1.15rem;">
          <button class="btn" onclick="app.bjtWorkspace.answerKeigoFlash(false)" style="flex:1; max-width:210px; justify-content:center; border-color:var(--danger); color:var(--danger);">← Chưa nhớ</button>
          <button class="btn btn-primary" onclick="app.bjtWorkspace.answerKeigoFlash(true)" style="flex:1; max-width:210px; justify-content:center; background:var(--success); border-color:var(--manga-ink);">Đã thuộc 済 →</button>
        </div>
      `;
    }

    flipKeigoFlash() {
      if (!this.keigoFlash || this.keigoFlash._swiping) return;
      this.keigoFlash.flipped = !this.keigoFlash.flipped;
      const card = document.getElementById('bjt-kfc-card');
      if (card) card.classList.toggle('is-flipped', this.keigoFlash.flipped);
      else this.renderKeigoFlashcardStep();
    }

    answerKeigoFlash(known) {
      const st = this.keigoFlash;
      if (!st || st._swiping) return;
      st._swiping = true;
      const item = st.queue[st.index];
      if (known) {
        const prog = this.getProgress();
        if (!prog.masteredKeigo.includes(item.id)) {
          prog.masteredKeigo.push(item.id);
          this.saveProgress(prog);
        }
      } else {
        st.queue.push(item);
      }
      const card = document.getElementById('bjt-kfc-card');
      if (card) {
        card.classList.add(known ? 'swipe-right' : 'swipe-left');
        setTimeout(() => {
          if (!this.keigoFlash) return;
          this.keigoFlash._swiping = false;
          this.keigoFlash.index++;
          this.keigoFlash.flipped = false;
          this.renderKeigoFlashcardStep();
        }, 220);
      } else {
        st._swiping = false;
        st.index++;
        st.flipped = false;
        this.renderKeigoFlashcardStep();
      }
    }

    startKeigoRoleplay(mistakesOnly = false) {
      if (!this.data || !this.data.keigoTable) return;
      this.keigoMode = 'roleplay';
      document.querySelectorAll('#bjt-keigo-pills .it-pill-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.kmode === 'roleplay');
      });
      const prog = this.getProgress();
      let pool = [...this.data.keigoTable];
      if (mistakesOnly) {
        pool = pool.filter(k => prog.wrongKeigo.includes(k.id));
        if (pool.length === 0) {
          this.app.showToast('Không còn câu Kính ngữ sai nào!');
          return;
        }
      }
      pool.sort(() => Math.random() - 0.5);
      const queue = mistakesOnly ? pool : pool.slice(0, Math.min(20, pool.length));
      this.keigoRoleplay = {
        queue,
        index: 0,
        correct: 0,
        answered: false,
        currentOptions: [],
        targetType: 'sonkeigo'
      };
      this.renderKeigoRoleplayStep();
    }

    renderKeigoRoleplayStep() {
      const body = document.getElementById('bjt-keigo-body');
      const st = this.keigoRoleplay;
      if (!body || !st) return;

      if (st.index >= st.queue.length) {
        const pct = Math.round((st.correct / st.queue.length) * 100);
        body.innerHTML = `
          <div style="background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:2rem 1.5rem; text-align:center; max-width:520px; margin:0 auto;">
            <div style="font-size:2.4rem; margin-bottom:0.5rem;">🎭</div>
            <div style="font-size:1.25rem; font-weight:700; color:var(--text); margin-bottom:0.4rem;">Hoàn thành Phản xạ Vai vế Kính ngữ!</div>
            <div style="font-size:0.95rem; color:var(--text-muted); margin-bottom:1.25rem;">
              Đúng <strong>${st.correct} / ${st.queue.length}</strong> câu (<strong>${pct}%</strong>)
            </div>
            <button class="btn btn-primary" onclick="app.bjtWorkspace.startKeigoRoleplay(false)">Luyện lượt mới →</button>
          </div>
        `;
        return;
      }

      const item = st.queue[st.index];
      const hasValidKenjou = item.kenjougo && !item.kenjougo.startsWith('—');
      const targetType = hasValidKenjou ? (Math.random() < 0.5 ? 'sonkeigo' : 'kenjougo') : 'sonkeigo';
      const oppositeType = targetType === 'sonkeigo' ? 'kenjougo' : 'sonkeigo';
      st.targetType = targetType;
      st.answered = false;

      const correctText = item[targetType];
      const distractors = [];
      const used = new Set([correctText]);
      // Trap #1: Always include the opposite form of the SAME verb when valid!
      if (item[oppositeType] && !item[oppositeType].startsWith('—') && !used.has(item[oppositeType])) {
        used.add(item[oppositeType]);
        distractors.push(item[oppositeType]);
      }
      const others = [...(this.data.keigoTable || [])].sort(() => Math.random() - 0.5);
      for (const cand of others) {
        if (distractors.length >= 3) break;
        const pick = Math.random() < 0.5 ? cand.sonkeigo : cand.kenjougo;
        if (pick && !pick.startsWith('—') && !used.has(pick)) {
          used.add(pick);
          distractors.push(pick);
        }
      }

      const options = [
        { text: correctText, correct: true },
        ...distractors.map(t => ({ text: t, correct: false }))
      ].sort(() => Math.random() - 0.5);
      st.currentOptions = options;

      const pct = Math.round((st.index / st.queue.length) * 100);
      const isSonkei = targetType === 'sonkeigo';
      const exSafe = escapeHtml(item.exampleJa || correctText).replace(/'/g, "\\'");

      body.innerHTML = `
        <div style="max-width:680px; margin:0 auto;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.55rem;">
            <span style="font-size:0.82rem; font-weight:700; color:var(--accent);">🎭 Phản xạ vai vế (Tránh bẫy 尊敬語 / 謙譲語)</span>
            <span style="font-size:0.84rem; font-weight:600; color:var(--text-muted);">Câu ${st.index + 1} / ${st.queue.length}</span>
          </div>
          <div class="progress-bar" style="margin-bottom:1rem;"><div class="progress-fill" style="width:${pct}%;"></div></div>

          <div class="quiz-question-box">
            <div class="quiz-type-badge" style="${isSonkei ? 'background:rgba(59,130,246,0.14);color:#60a5fa;' : 'background:rgba(16,185,129,0.14);color:#34d399;'}">
              ${isSonkei ? '👔 HÀNH ĐỘNG CỦA KHÁCH HÀNG / CẤP TRÊN' : '🙋 HÀNH ĐỘNG CỦA BẢN THÂN / CÔNG TY MÌNH'}
            </div>
            <div style="font-family:var(--font-jp); font-size:2.1rem; font-weight:700; color:var(--text); margin:0.65rem 0 0.35rem;">
              ${escapeHtml(item.plain)}
            </div>
            <div style="font-size:0.86rem; color:var(--text-muted);">
              ${isSonkei ? 'Chọn 尊敬語 (Tôn kính ngữ) phù hợp:' : 'Chọn 謙譲語 (Khiêm nhường ngữ) phù hợp:'}
            </div>
          </div>

          <div style="display:flex; flex-direction:column; gap:0.55rem; margin-top:1rem;">
            ${options.map((opt, idx) => `
              <button class="it-practice-opt" id="bjt-krp-${idx}" onclick="app.bjtWorkspace.selectKeigoRoleplayOption(${idx})"><span class="bjt-keycap">${idx + 1}</span><span>${escapeHtml(opt.text)}</span></button>
            `).join('')}
          </div>

          <div id="bjt-krp-fb" style="display:none; margin-top:0.85rem; padding:0.9rem; border-radius:10px; background:var(--surface); border:1px solid var(--border);">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:0.5rem; margin-bottom:0.45rem;">
              <span id="bjt-krp-fb-title" style="font-weight:700;"></span>
              <div style="display:flex; gap:0.4rem;">
                <button class="icon-btn" onclick="app.speakText('${exSafe}')" style="width:1.9rem;height:1.9rem;">🔊</button>
                <button class="btn btn-sm btn-primary" onclick="app.bjtWorkspace.nextKeigoRoleplayStep()">Câu tiếp theo →</button>
              </div>
            </div>
            <div style="font-size:0.84rem; color:var(--text-muted); display:flex; flex-direction:column; gap:0.25rem;">
              <div><strong style="color:var(--text);">${escapeHtml(item.plain)}</strong> (${escapeHtml(item.reading || '')}) — ${escapeHtml(item.vi)}</div>
              <div><span class="bjt-tag sonkei">尊敬語</span> <strong style="font-family:var(--font-jp); color:var(--text);">${escapeHtml(item.sonkeigo)}</strong></div>
              <div><span class="bjt-tag kenjou">謙譲語</span> <strong style="font-family:var(--font-jp); color:var(--text);">${escapeHtml(item.kenjougo)}</strong></div>
              ${item.exampleJa ? `<div style="margin-top:0.25rem; font-family:var(--font-jp); color:var(--text);">${escapeHtml(item.exampleJa)}</div><div>${escapeHtml(item.exampleVi || '')}</div>` : ''}
            </div>
          </div>
        </div>
      `;
    }

    selectKeigoRoleplayOption(idx) {
      const st = this.keigoRoleplay;
      if (!st || st.answered) return;
      st.answered = true;
      const item = st.queue[st.index];
      const chosen = st.currentOptions[idx];
      const isCorrect = !!(chosen && chosen.correct);
      if (isCorrect) {
        st.correct++;
        st.combo = (st.combo || 0) + 1;
      } else {
        st.combo = 0;
      }
      this._recordMistake('wrongKeigo', item.id, isCorrect);

      st.currentOptions.forEach((opt, i) => {
        const btn = document.getElementById(`bjt-krp-${i}`);
        if (!btn) return;
        if (opt.correct) btn.classList.add('correct');
        else if (i === idx) btn.classList.add('incorrect');
        btn.disabled = true;
      });

      if (global.BJTManga) {
        global.BJTManga.spawnSFX(document.getElementById(`bjt-krp-${idx}`), isCorrect, st.combo);
        if (isCorrect && st.combo >= 2) {
          global.BJTManga.flashSpeedlines(document.querySelector('#bjt-keigo-body .quiz-question-box'));
        }
      }

      const fb = document.getElementById('bjt-krp-fb');
      const title = document.getElementById('bjt-krp-fb-title');
      if (title) {
        title.textContent = isCorrect ? '✓ Chính xác!' : '✗ Chưa đúng vai vế';
        title.style.color = isCorrect ? 'var(--success)' : 'var(--danger)';
      }
      if (fb) fb.style.display = 'block';
    }

    nextKeigoRoleplayStep() {
      if (!this.keigoRoleplay) return;
      this.keigoRoleplay.index++;
      this.renderKeigoRoleplayStep();
    }

    // ==================== TAB 4: BUSINESS VOCAB & PHRASES ====================

    setVocabCategory(cat) {
      this.vocabCategory = cat;
      this.vocabStudy = null;
      document.querySelectorAll('#bjt-vocab-cat-pills .it-pill-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.vcat === cat);
      });
      this.renderVocab();
    }

    getFilteredVocab() {
      const allV = (this.data && this.data.businessVocab) || [];
      const q = ((document.getElementById('bjt-vocab-search') || {}).value || '').trim().toLowerCase();
      return allV.filter(v => {
        if (this.vocabCategory !== 'all' && v.category !== this.vocabCategory) return false;
        if (q) {
          return `${v.word} ${v.reading || ''} ${v.vi || ''} ${v.source || ''} ${v.exampleJa || ''}`.toLowerCase().includes(q);
        }
        return true;
      });
    }

    toggleVocabMastered(id) {
      const prog = this.getProgress();
      const i = prog.masteredVocab.indexOf(id);
      if (i === -1) prog.masteredVocab.push(id);
      else prog.masteredVocab.splice(i, 1);
      this.saveProgress(prog);
      this.renderVocab();
    }

    renderVocab() {
      if (!this.data) return;
      const body = document.getElementById('bjt-vocab-body');
      const searchWrap = document.getElementById('bjt-vocab-search-wrap');
      if (!body) return;

      const allV = this.data.businessVocab || [];
      const prog = this.getProgress();
      const statsEl = document.getElementById('bjt-vocab-stats');
      if (statsEl) {
        const wrongNote = prog.wrongVocab.length > 0 ? ` · 🔴 ${prog.wrongVocab.length} từ hay sai` : '';
        statsEl.textContent = `Đã thuộc ${prog.masteredVocab.length}/${allV.length} từ vựng & cụm câu thương mại${wrongNote}`;
      }
      const vMistakeBtn = document.getElementById('bjt-vocab-mistake-btn');
      if (vMistakeBtn) {
        vMistakeBtn.style.display = prog.wrongVocab.length > 0 ? 'inline-flex' : 'none';
        vMistakeBtn.textContent = `🔴 Ôn ${prog.wrongVocab.length} từ hay sai`;
      }

      if (this.vocabStudy) {
        if (searchWrap) searchWrap.style.display = 'none';
        this.renderVocabStudyStep();
        return;
      }

      if (searchWrap) searchWrap.style.display = 'block';
      const list = this.getFilteredVocab();

      if (list.length === 0) {
        body.innerHTML = '<div style="color:var(--text-muted); padding:2rem; text-align:center;">Không tìm thấy từ vựng phù hợp.</div>';
        return;
      }

      body.innerHTML = `
        <div style="font-size:0.82rem; color:var(--text-muted); margin-bottom:0.65rem;">Hiển thị <strong>${list.length}</strong> / ${allV.length} mục</div>
        <div class="it-vocab-list">
          ${list.map((v, idx) => {
            const isM = prog.masteredVocab.includes(v.id);
            const speakSafe = escapeHtml(v.word).replace(/'/g, "\\'");
            return `
              <div class="it-vocab-item bjt-stagger ${isM ? 'mastered' : ''}" style="--i:${Math.min(idx, 18)};">
                ${isM ? '<span class="bjt-hanko-stamp" aria-label="Đã thuộc">済</span>' : ''}
                <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:0.4rem;">
                  <span style="font-family:var(--font-manga-jp, var(--font-jp)); font-size:1.08rem; font-weight:700; color:var(--text);">${escapeHtml(v.word)}</span>
                  <div style="display:flex; gap:0.3rem; flex-shrink:0;">
                    <button class="icon-btn" title="Phát âm" onclick="app.speakText('${speakSafe}')" style="width:1.75rem;height:1.75rem;">${bjtIcon('volume', 'bjt-svg-sm')}</button>
                    <button class="icon-btn" title="${isM ? 'Đã thuộc' : 'Đánh dấu đã thuộc'}" onclick="app.bjtWorkspace.toggleVocabMastered('${escapeHtml(v.id)}')" style="width:1.75rem;height:1.75rem; ${isM ? 'background:var(--success-soft);color:var(--success);border-color:var(--success);' : ''}">${bjtIcon('check', 'bjt-svg-sm')}</button>
                  </div>
                </div>
                ${v.reading ? `<div style="font-family:var(--font-jp); font-size:0.82rem; color:var(--accent);">${escapeHtml(v.reading)}</div>` : ''}
                <div style="font-size:0.88rem; color:var(--text); font-weight:500;">${escapeHtml(v.vi || '')}</div>
                <div style="display:flex; gap:0.35rem; flex-wrap:wrap; margin-top:0.2rem;">
                  <span class="it-badge" style="font-size:0.7rem;">${escapeHtml(v.categoryLabel || v.category)}</span>
                  ${v.source ? `<span class="it-badge" style="font-size:0.7rem; opacity:0.85;">${escapeHtml(v.source)}</span>` : ''}
                </div>
                ${v.exampleJa ? `
                  <div style="font-size:0.79rem; color:var(--text-muted); border-top:1px dashed var(--border); padding-top:0.35rem; margin-top:0.3rem; line-height:1.45;">
                    <div style="font-family:var(--font-jp); color:var(--text);">${escapeHtml(v.exampleJa)}</div>
                    <div>${escapeHtml(v.exampleVi || '')}</div>
                  </div>
                ` : ''}
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    _makeClozeSentence(item) {
      const ex = item.exampleJa || '';
      const w = item.word || '';
      if (!ex || !w) return null;
      let target = null;
      if (ex.includes(w)) target = w;
      else if (w.length >= 3 && ex.includes(w.slice(0, -1))) target = w.slice(0, -1);
      else if (w.length >= 4 && ex.includes(w.slice(0, -2))) target = w.slice(0, -2);
      if (!target) return null;
      const idx = ex.indexOf(target);
      return escapeHtml(ex.slice(0, idx)) + '<span style="display:inline-block;padding:0.05rem 0.55rem;margin:0 0.15rem;border-radius:6px;background:var(--accent-soft);color:var(--accent);font-weight:700;border:1px dashed var(--accent);">＿＿＿</span>' + escapeHtml(ex.slice(idx + target.length));
    }

    startVocabStudy(mode, mistakesOnly = false) {
      if (!this.data || !this.data.businessVocab) return;
      const prog = this.getProgress();
      let pool = mistakesOnly
        ? this.data.businessVocab.filter(v => prog.wrongVocab.includes(v.id))
        : this.getFilteredVocab();

      if (mode === 'cloze') {
        pool = pool.filter(v => this._makeClozeSentence(v) !== null);
      }

      if (pool.length === 0 || (!mistakesOnly && pool.length < 4)) {
        this.app.showToast(mistakesOnly ? 'Không còn từ hay sai nào!' : 'Cần ít nhất 4 từ trong bộ lọc để bắt đầu luyện tập.');
        return;
      }
      const shuffled = [...pool].sort(() => Math.random() - 0.5);
      const queue = (mode === 'quiz' || mode === 'cloze') && !mistakesOnly
        ? shuffled.slice(0, Math.min(25, shuffled.length))
        : shuffled;
      this.vocabStudy = {
        mode,
        queue,
        allPool: this.data.businessVocab,
        index: 0,
        flipped: false,
        correct: 0,
        answered: false,
        currentOptions: []
      };
      this.renderVocab();
    }

    exitVocabStudy() {
      this.vocabStudy = null;
      this.renderVocab();
    }

    renderVocabStudyStep() {
      const st = this.vocabStudy;
      const body = document.getElementById('bjt-vocab-body');
      if (!st || !body) return;

      if (st.index >= st.queue.length) {
        body.innerHTML = `
          <div style="background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:2rem 1.5rem; text-align:center; max-width:520px; margin:0 auto;">
            <div style="font-size:2.5rem; margin-bottom:0.5rem;">🎉</div>
            <div style="font-size:1.25rem; font-weight:700; color:var(--text); margin-bottom:0.4rem;">Hoàn thành phiên ôn Từ vựng BJT!</div>
            <div style="font-size:0.95rem; color:var(--text-muted); margin-bottom:1.25rem;">
              ${st.mode === 'flashcard' ? `Bạn đã ôn xong <strong>${st.queue.length}</strong> từ vựng thương mại.` : `Bạn trả lời đúng <strong>${st.correct} / ${st.queue.length}</strong> câu.`}
            </div>
            <button class="btn btn-primary" onclick="app.bjtWorkspace.exitVocabStudy()">Quay lại danh sách →</button>
          </div>
        `;
        return;
      }

      const item = st.queue[st.index];
      const pct = Math.round((st.index / st.queue.length) * 100);
      const wordSafe = escapeHtml(item.word).replace(/'/g, "\\'");

      const headerBar = `
        <div style="max-width:680px; margin:0 auto;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem;">
            <button class="btn btn-sm" onclick="app.bjtWorkspace.exitVocabStudy()">← Quay lại</button>
            <span style="font-size:0.85rem; font-weight:600; color:var(--text-muted);">${st.mode === 'flashcard' ? 'Thẻ' : 'Câu'} ${st.index + 1} / ${st.queue.length}</span>
          </div>
          <div class="progress-bar" style="margin-bottom:1rem;"><div class="progress-fill" style="width:${pct}%;"></div></div>
      `;

      if (st.mode === 'flashcard') {
        body.innerHTML = `
          ${headerBar}
            <div class="bjt-fc-scene">
              <div class="bjt-fc-card ${st.flipped ? 'is-flipped' : ''}" id="bjt-vfc-card" onclick="app.bjtWorkspace.flipVocabFlash()">
                <div class="bjt-fc-face">
                  <span class="it-badge" style="margin-bottom:0.85rem;">${escapeHtml(item.categoryLabel || item.category)}</span>
                  <div style="font-family:var(--font-manga-jp, var(--font-jp)); font-size:2.15rem; font-weight:700; color:var(--text); margin-bottom:0.45rem;">${escapeHtml(item.word)}</div>
                  <button class="icon-btn" onclick="event.stopPropagation(); app.speakText('${wordSafe}')" style="margin-top:0.35rem;">${bjtIcon('volume')}</button>
                  <div style="position:absolute; bottom:0.9rem; font-size:0.74rem; color:var(--text-subtle); display:inline-flex; align-items:center; gap:0.35rem;">${bjtIcon('rotateCw', 'bjt-svg-sm')} <span>Bấm thẻ hoặc Space để lật</span></div>
                </div>
                <div class="bjt-fc-face bjt-fc-back">
                  <span class="it-badge" style="margin-bottom:0.55rem;">${escapeHtml(item.categoryLabel || item.category)}</span>
                  <div style="font-family:var(--font-manga-jp, var(--font-jp)); font-size:1.5rem; font-weight:700; color:var(--text);">${escapeHtml(item.word)}</div>
                  ${item.reading ? `<div style="font-family:var(--font-jp); font-size:1.05rem; color:var(--accent); font-weight:600; margin:0.25rem 0;">${escapeHtml(item.reading)}</div>` : ''}
                  <div style="font-size:1.1rem; font-weight:700; color:var(--text); margin:0.25rem 0 0.45rem;">${escapeHtml(item.vi || '')}</div>
                  ${item.exampleJa ? `
                    <div style="font-size:0.82rem; color:var(--text-muted); max-width:460px; border-top:1.5px dashed var(--border); padding-top:0.45rem; margin-top:0.25rem;">
                      <div style="font-family:var(--font-jp); color:var(--text);">${escapeHtml(item.exampleJa)}</div>
                      <div>${escapeHtml(item.exampleVi || '')}</div>
                    </div>
                  ` : ''}
                </div>
              </div>
            </div>
            <div style="display:flex; gap:0.75rem; justify-content:center; margin-top:1.15rem;">
              <button class="btn" onclick="app.bjtWorkspace.answerVocabFlash(false)" style="flex:1; max-width:210px; justify-content:center; border-color:var(--danger); color:var(--danger);">← Chưa nhớ</button>
              <button class="btn btn-primary" onclick="app.bjtWorkspace.answerVocabFlash(true)" style="flex:1; max-width:210px; justify-content:center; background:var(--success); border-color:var(--manga-ink);">Đã thuộc 済 →</button>
            </div>
          </div>
        `;
      } else if (st.mode === 'cloze') {
        const clozeHtml = this._makeClozeSentence(item) || escapeHtml(item.exampleJa || item.word);
        const distractors = [];
        const used = new Set([item.word]);
        const sameCat = st.allPool.filter(c => c.category === item.category).sort(() => Math.random() - 0.5);
        const otherCat = st.allPool.filter(c => c.category !== item.category).sort(() => Math.random() - 0.5);
        for (const cand of [...sameCat, ...otherCat]) {
          if (!used.has(cand.word)) {
            used.add(cand.word);
            distractors.push(cand);
            if (distractors.length >= 3) break;
          }
        }
        const options = [
          { text: item.word, correct: true },
          ...distractors.map(d => ({ text: d.word, correct: false }))
        ].sort(() => Math.random() - 0.5);

        st.currentOptions = options;
        st.answered = false;
        const exSafe = escapeHtml(item.exampleJa || item.word).replace(/'/g, "\\'");

        body.innerHTML = `
          ${headerBar}
            <div class="quiz-question-box">
              <div class="quiz-type-badge">🧩 ĐIỀN TỪ VÀO NGỮ CẢNH · ${escapeHtml(item.categoryLabel || item.category)}</div>
              <div style="font-family:var(--font-jp); font-size:1.3rem; font-weight:600; color:var(--text); line-height:1.75; margin:0.75rem 0;">
                ${clozeHtml}
              </div>
              <div style="font-size:0.84rem; color:var(--text-muted);">Chọn từ / cụm từ điền vào chỗ trống:</div>
            </div>
            <div style="display:flex; flex-direction:column; gap:0.55rem; margin-top:1rem;">
              ${options.map((opt, idx) => `
                <button class="it-practice-opt" id="bjt-vqopt-${idx}" onclick="app.bjtWorkspace.selectVocabQuizOption(${idx})">${idx + 1}. ${escapeHtml(opt.text)}</button>
              `).join('')}
            </div>
            <div id="bjt-vqfb" style="display:none; margin-top:0.85rem; padding:0.9rem; border-radius:10px; background:var(--surface); border:1px solid var(--border);">
              <div style="display:flex; justify-content:space-between; align-items:center; gap:0.5rem;">
                <span id="bjt-vqfb-title" style="font-weight:700;"></span>
                <div style="display:flex; gap:0.4rem;">
                  <button class="icon-btn" onclick="app.speakText('${exSafe}')" style="width:1.9rem;height:1.9rem;">🔊</button>
                  <button class="btn btn-sm btn-primary" onclick="app.bjtWorkspace.nextVocabQuizStep()">Câu tiếp theo →</button>
                </div>
              </div>
              <div style="font-size:0.86rem; color:var(--text-muted); margin-top:0.35rem;">
                <strong style="color:var(--text);">${escapeHtml(item.word)}</strong>${item.reading ? ` (${escapeHtml(item.reading)})` : ''} — ${escapeHtml(item.vi || '')}
              </div>
              <div style="font-size:0.84rem; color:var(--text); margin-top:0.3rem; font-family:var(--font-jp);">${escapeHtml(item.exampleJa || '')}</div>
              ${item.exampleVi ? `<div style="font-size:0.82rem; color:var(--text-muted); margin-top:0.15rem;">${escapeHtml(item.exampleVi)}</div>` : ''}
            </div>
          </div>
        `;
      } else {
        const qType = st.index % 2 === 0 ? 'jp_to_vi' : 'vi_to_jp';
        const distractors = [];
        const used = new Set([item.word]);
        const shuffledPool = [...st.allPool].sort(() => Math.random() - 0.5);
        for (const cand of shuffledPool) {
          if (!used.has(cand.word) && cand.vi !== item.vi) {
            used.add(cand.word);
            distractors.push(cand);
            if (distractors.length >= 3) break;
          }
        }
        const options = [
          { text: qType === 'jp_to_vi' ? item.vi : item.word, correct: true },
          ...distractors.map(d => ({ text: qType === 'jp_to_vi' ? d.vi : d.word, correct: false }))
        ].sort(() => Math.random() - 0.5);

        st.currentOptions = options;
        st.answered = false;

        body.innerHTML = `
          ${headerBar}
            <div class="quiz-question-box">
              <div class="quiz-type-badge">${escapeHtml(item.categoryLabel || item.category)}</div>
              <div style="font-family:var(--font-jp); font-size:${qType === 'jp_to_vi' ? '2rem' : '1.3rem'}; font-weight:700; color:${qType === 'jp_to_vi' ? 'var(--text)' : 'var(--accent)'}; margin:0.6rem 0;">
                ${escapeHtml(qType === 'jp_to_vi' ? item.word : item.vi)}
              </div>
              <div style="font-size:0.85rem; color:var(--text-muted);">
                ${qType === 'jp_to_vi' ? 'Chọn nghĩa thương mại tương ứng:' : 'Chọn từ / cụm tiếng Nhật tương ứng:'}
              </div>
            </div>
            <div style="display:flex; flex-direction:column; gap:0.55rem; margin-top:1rem;">
              ${options.map((opt, idx) => `
                <button class="it-practice-opt" id="bjt-vqopt-${idx}" onclick="app.bjtWorkspace.selectVocabQuizOption(${idx})">${idx + 1}. ${escapeHtml(opt.text)}</button>
              `).join('')}
            </div>
            <div id="bjt-vqfb" style="display:none; margin-top:0.85rem; padding:0.9rem; border-radius:10px; background:var(--surface); border:1px solid var(--border);">
              <div style="display:flex; justify-content:space-between; align-items:center; gap:0.5rem;">
                <span id="bjt-vqfb-title" style="font-weight:700;"></span>
                <div style="display:flex; gap:0.4rem;">
                  <button class="icon-btn" onclick="app.speakText('${wordSafe}')" style="width:1.9rem;height:1.9rem;">🔊</button>
                  <button class="btn btn-sm btn-primary" onclick="app.bjtWorkspace.nextVocabQuizStep()">Câu tiếp theo →</button>
                </div>
              </div>
              <div style="font-size:0.85rem; color:var(--text-muted); margin-top:0.35rem;">
                <strong style="color:var(--text);">${escapeHtml(item.word)}</strong>${item.reading ? ` (${escapeHtml(item.reading)})` : ''} — ${escapeHtml(item.vi || '')}
              </div>
              ${item.exampleJa ? `<div style="font-size:0.82rem; color:var(--text-muted); margin-top:0.3rem; font-family:var(--font-jp);">${escapeHtml(item.exampleJa)}</div>` : ''}
            </div>
          </div>
        `;
      }
    }

    flipVocabFlash() {
      if (!this.vocabStudy || this.vocabStudy._swiping) return;
      this.vocabStudy.flipped = !this.vocabStudy.flipped;
      const card = document.getElementById('bjt-vfc-card');
      if (card) card.classList.toggle('is-flipped', this.vocabStudy.flipped);
      else this.renderVocabStudyStep();
    }

    answerVocabFlash(known) {
      const st = this.vocabStudy;
      if (!st || st._swiping) return;
      st._swiping = true;
      const item = st.queue[st.index];
      if (known) {
        const prog = this.getProgress();
        if (!prog.masteredVocab.includes(item.id)) {
          prog.masteredVocab.push(item.id);
          this.saveProgress(prog);
        }
      } else {
        st.queue.push(item);
      }
      const card = document.getElementById('bjt-vfc-card');
      if (card) {
        card.classList.add(known ? 'swipe-right' : 'swipe-left');
        setTimeout(() => {
          if (!this.vocabStudy) return;
          this.vocabStudy._swiping = false;
          this.vocabStudy.index++;
          this.vocabStudy.flipped = false;
          this.renderVocabStudyStep();
        }, 220);
      } else {
        st._swiping = false;
        st.index++;
        st.flipped = false;
        this.renderVocabStudyStep();
      }
    }

    selectVocabQuizOption(idx) {
      const st = this.vocabStudy;
      if (!st || st.answered) return;
      st.answered = true;
      const item = st.queue[st.index];
      const chosen = st.currentOptions[idx];
      const isCorrect = !!(chosen && chosen.correct);
      if (isCorrect) {
        st.correct++;
        st.combo = (st.combo || 0) + 1;
      } else {
        st.combo = 0;
      }
      this._recordMistake('wrongVocab', item.id, isCorrect);

      st.currentOptions.forEach((opt, i) => {
        const btn = document.getElementById(`bjt-vqopt-${i}`);
        if (!btn) return;
        if (opt.correct) btn.classList.add('correct');
        else if (i === idx) btn.classList.add('incorrect');
        btn.disabled = true;
      });

      if (global.BJTManga) {
        global.BJTManga.spawnSFX(document.getElementById(`bjt-vqopt-${idx}`), isCorrect, st.combo);
        if (isCorrect && st.combo >= 2) {
          global.BJTManga.flashSpeedlines(document.querySelector('#bjt-vocab-body .quiz-question-box'));
        }
      }

      const fb = document.getElementById('bjt-vqfb');
      const title = document.getElementById('bjt-vqfb-title');
      if (title) {
        title.textContent = isCorrect ? '✓ Chính xác!' : '✗ Chưa chính xác';
        title.style.color = isCorrect ? 'var(--success)' : 'var(--danger)';
      }
      if (fb) fb.style.display = 'block';
    }

    nextVocabQuizStep() {
      if (!this.vocabStudy) return;
      this.vocabStudy.index++;
      this.renderVocabStudyStep();
    }

    // ==================== TAB 2: BUSINESS EMAILS ====================

    setEmailCategory(cat) {
      this.emailCategory = cat;
      this.exitEmailSkim(false);
      document.querySelectorAll('#bjt-email-pills .it-pill-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.ecat === cat);
      });
      this.renderEmails();
    }

    startEmailSkim() {
      if (!this.data || !this.data.emails) return;
      const pool = (this.data.emails || []).filter(em => this.emailCategory === 'all' || em.category === this.emailCategory);
      if (pool.length === 0) {
        this.app.showToast('Không có mẫu Email nào trong nhóm này.');
        return;
      }
      this._stopTimer();
      this.emailSkim = {
        queue: [...pool].sort(() => Math.random() - 0.5),
        index: 0,
        secondsLeft: 30,
        revealed: false
      };
      this.renderEmailSkimStep();
    }

    exitEmailSkim(shouldRender = true) {
      this._stopTimer();
      this.emailSkim = null;
      if (shouldRender) this.renderEmails();
    }

    renderEmailSkimStep() {
      const st = this.emailSkim;
      const body = document.getElementById('bjt-email-body');
      if (!st || !body) return;
      this._stopTimer();

      if (st.index >= st.queue.length) {
        this.emailSkim = null;
        body.innerHTML = `
          <div style="background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:2rem; text-align:center; max-width:520px; margin:0 auto;">
            <div style="font-size:2.4rem; margin-bottom:0.5rem;">⚡</div>
            <div style="font-size:1.2rem; font-weight:700; color:var(--text); margin-bottom:0.4rem;">Hoàn thành luyện đọc lướt Email!</div>
            <button class="btn btn-primary" onclick="app.bjtWorkspace.renderEmails()">Quay lại thư viện Email →</button>
          </div>
        `;
        return;
      }

      const em = st.queue[st.index];
      const speakSafe = escapeHtml(em.bodyJa.replace(/\n+/g, ' ')).replace(/'/g, "\\'");

      if (!st.revealed) {
        st.secondsLeft = 30;
        this._timerInterval = setInterval(() => {
          if (!this.emailSkim || this.emailSkim.revealed) return this._stopTimer();
          this.emailSkim.secondsLeft = Math.max(0, this.emailSkim.secondsLeft - 1);
          const badge = document.getElementById('bjt-skim-timer');
          if (badge) {
            badge.textContent = `⏱️ ${this._fmtTime(this.emailSkim.secondsLeft)}`;
            if (this.emailSkim.secondsLeft <= 5) badge.style.color = 'var(--danger)';
          }
          if (this.emailSkim.secondsLeft === 0) {
            this.revealEmailSkim();
          }
        }, 1000);
      }

      body.innerHTML = `
        <div class="bjt-email-card" style="max-width:820px; margin:0 auto;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.75rem;">
            <button class="btn btn-sm" onclick="app.bjtWorkspace.exitEmailSkim(true)">← Thoát đọc lướt</button>
            <div style="display:flex; align-items:center; gap:0.5rem;">
              <span class="it-badge" id="bjt-skim-timer" style="background:var(--accent-soft); color:var(--accent); font-weight:700;">⏱️ ${this._fmtTime(st.secondsLeft)}</span>
              <span style="font-size:0.84rem; color:var(--text-muted); font-weight:600;">Email ${st.index + 1} / ${st.queue.length}</span>
            </div>
          </div>

          <div class="it-tip-card" style="margin-bottom:0.85rem;">
            <div style="font-size:0.8rem; font-weight:700; color:var(--accent); margin-bottom:0.2rem;">🎯 Mục tiêu đọc lướt 30 giây (tự nhẩm nhanh 3 ý):</div>
            <div style="font-size:0.82rem; color:var(--text-muted);">1) Ai gửi & mục đích chính? · 2) Yêu cầu hành động / thời hạn? · 3) Cụm kính ngữ quan trọng?</div>
          </div>

          <div class="bjt-email-subject">
            <strong>件名:</strong> <span style="font-family:var(--font-jp);">${escapeHtml(em.subjectJa)}</span>
            ${st.revealed ? `<span style="color:var(--text-muted); font-size:0.82rem; margin-left:0.4rem;">— ${escapeHtml(em.subjectVi || '')}</span>` : ''}
          </div>

          <div class="${st.revealed ? 'bjt-email-columns' : ''}">
            <pre class="bjt-email-pre jp">${escapeHtml(em.bodyJa)}</pre>
            ${st.revealed ? `<pre class="bjt-email-pre vi">${escapeHtml(em.bodyVi || '')}</pre>` : ''}
          </div>

          ${st.revealed ? `
            ${(em.keigoNotes || []).length > 0 ? `
              <div class="it-tip-card" style="margin-top:0.75rem;">
                <div style="font-size:0.76rem; font-weight:700; color:var(--accent); margin-bottom:0.25rem;">💡 Phân tích kính ngữ & cấu trúc (${escapeHtml(em.titleVi)})</div>
                <ul style="margin:0; padding-left:1.1rem; font-size:0.82rem; color:var(--text-muted); line-height:1.5;">
                  ${em.keigoNotes.map(n => `<li>${escapeHtml(n)}</li>`).join('')}
                </ul>
              </div>
            ` : ''}
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem; margin-top:0.9rem;">
              <div style="display:flex; gap:0.4rem;">
                <button class="btn btn-sm" onclick="app.speakText('${speakSafe}')">🔊 Nghe Shadowing</button>
                <button class="btn btn-sm" onclick="app.bjtWorkspace.copyEmailText('${escapeHtml(em.id)}')">📋 Copy JP</button>
              </div>
              <button class="btn btn-primary" onclick="app.bjtWorkspace.nextEmailSkim()">Email tiếp theo →</button>
            </div>
          ` : `
            <div style="display:flex; justify-content:center; gap:0.6rem; margin-top:1rem;">
              <button class="btn btn-primary" onclick="app.bjtWorkspace.revealEmailSkim()">👁️ Hiện bản dịch & Phân tích</button>
              <button class="btn" onclick="app.speakText('${speakSafe}')">🔊 Nghe đọc</button>
            </div>
          `}
        </div>
      `;
    }

    revealEmailSkim() {
      if (!this.emailSkim) return;
      this._stopTimer();
      this.emailSkim.revealed = true;
      this.renderEmailSkimStep();
    }

    nextEmailSkim() {
      if (!this.emailSkim) return;
      this.emailSkim.index++;
      this.emailSkim.revealed = false;
      this.emailSkim.secondsLeft = 30;
      this.renderEmailSkimStep();
    }

    copyEmailText(emailId) {
      const em = (this.data && this.data.emails || []).find(e => e.id === emailId);
      if (!em) return;
      const full = `件名: ${em.subjectJa}\n\n${em.bodyJa}`;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(full).then(() => {
          this.app.showToast('Đã copy mẫu Email tiếng Nhật!');
        }).catch(() => {});
      }
    }

    renderEmails() {
      if (!this.data) return;
      const body = document.getElementById('bjt-email-body');
      if (!body) return;
      const q = ((document.getElementById('bjt-email-search') || {}).value || '').trim().toLowerCase();

      const list = (this.data.emails || []).filter(em => {
        if (this.emailCategory !== 'all' && em.category !== this.emailCategory) return false;
        if (q) {
          return `${em.titleVi} ${em.subjectJa} ${em.bodyJa} ${em.bodyVi}`.toLowerCase().includes(q);
        }
        return true;
      });

      if (list.length === 0) {
        body.innerHTML = '<div style="color:var(--text-muted); padding:2rem; text-align:center;">Không tìm thấy mẫu Email phù hợp.</div>';
        return;
      }

      body.innerHTML = list.map(em => {
        const speakSafe = escapeHtml(em.bodyJa.replace(/\n+/g, ' ')).replace(/'/g, "\\'");
        return `
          <div class="bjt-email-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.65rem;">
              <div>
                <span class="it-badge" style="background:var(--accent-soft); color:var(--accent); font-weight:700;">${escapeHtml(em.categoryLabel || em.category)}</span>
                <div style="font-size:1.05rem; font-weight:700; color:var(--text); margin-top:0.3rem;">${escapeHtml(em.titleVi)}</div>
              </div>
              <div style="display:flex; gap:0.4rem;">
                <button class="btn btn-sm" onclick="app.speakText('${speakSafe}')">🔊 Nghe</button>
                <button class="btn btn-sm btn-primary" onclick="app.bjtWorkspace.copyEmailText('${escapeHtml(em.id)}')">📋 Copy JP</button>
              </div>
            </div>

            <div class="bjt-email-subject">
              <strong>件名 (Tiêu đề):</strong> <span style="font-family:var(--font-jp);">${escapeHtml(em.subjectJa)}</span>
              <span style="color:var(--text-muted); font-size:0.8rem; margin-left:0.4rem;">— ${escapeHtml(em.subjectVi || '')}</span>
            </div>

            <div class="bjt-email-columns">
              <pre class="bjt-email-pre jp">${escapeHtml(em.bodyJa)}</pre>
              <pre class="bjt-email-pre vi">${escapeHtml(em.bodyVi || '')}</pre>
            </div>

            ${(em.keigoNotes || []).length > 0 ? `
              <div class="it-tip-card" style="margin-top:0.75rem; margin-bottom:0;">
                <div style="font-size:0.76rem; font-weight:700; color:var(--accent); margin-bottom:0.25rem;">💡 Chú thích kính ngữ & cấu trúc Email</div>
                <ul style="margin:0; padding-left:1.1rem; font-size:0.82rem; color:var(--text-muted); line-height:1.5;">
                  ${em.keigoNotes.map(n => `<li>${escapeHtml(n)}</li>`).join('')}
                </ul>
              </div>
            ` : ''}
          </div>
        `;
      }).join('');
    }

    // ==================== TAB 3: BJT READING CBT (読解) ====================

    setDokkaiSource(src) {
      this.dokkaiSource = src;
      document.querySelectorAll('#bjt-dokkai-source-pills .it-pill-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.dsrc === src);
      });
      this.renderDokkaiHome();
    }

    setDokkaiSection(sec) {
      this.dokkaiSection = sec;
      document.querySelectorAll('#bjt-dokkai-pills .it-pill-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.dsec === sec);
      });
      this.renderDokkaiHome();
    }

    getFilteredDokkai(sectionOverride) {
      const allQ = (this.data && this.data.dokkai) || [];
      const sec = sectionOverride !== undefined ? sectionOverride : this.dokkaiSection;
      return allQ.filter(q => {
        const qSrc = q.source || 'mcbooks';
        if (this.dokkaiSource !== 'all' && qSrc !== this.dokkaiSource) return false;
        if (sec !== 'all' && q.section !== sec) return false;
        return true;
      });
    }

    renderDokkaiHome() {
      this._stopTimer();
      this.dokkaiRun = null;
      if (!this.data) return;
      const body = document.getElementById('bjt-dokkai-body');
      if (!body) return;

      const allQ = this.data.dokkai || [];
      const prog = this.getProgress();
      const sourcePool = this.getFilteredDokkai('all');
      const filtered = this.getFilteredDokkai();

      const cntVocab = sourcePool.filter(q => q.section === 'vocab').length;
      const cntExpr = sourcePool.filter(q => q.section === 'expression').length;
      const cntDoc = sourcePool.filter(q => q.section === 'document').length;

      // Update source pill labels with live counts
      const srcCounts = {
        all: allQ.length,
        mcbooks: allQ.filter(q => (q.source || 'mcbooks') === 'mcbooks').length,
        jitsuryoku: allQ.filter(q => q.source === 'jitsuryoku').length,
        redbook: allQ.filter(q => q.source === 'redbook').length
      };
      const labels = {
        all: `Tất cả (${srcCounts.all})`,
        mcbooks: `📘 Đề 1: MCBooks (${srcCounts.mcbooks})`,
        jitsuryoku: `📗 実力養成 (${srcCounts.jitsuryoku})`,
        redbook: `📕 Quyển đỏ (${srcCounts.redbook})`
      };
      document.querySelectorAll('#bjt-dokkai-source-pills .it-pill-btn').forEach(b => {
        const key = b.dataset.dsrc;
        if (labels[key]) b.textContent = labels[key];
      });

      body.innerHTML = `
        <div class="it-hero" style="margin-bottom:1rem;">
          <span class="bjt-manga-ribbon" aria-hidden="true">読解試験</span>
          <div>
            <div class="it-hero-title">Kho Đọc hiểu BJT — 第3部 読解テスト</div>
            <div class="it-hero-sub">Tổng hợp từ 3 bộ sách chuẩn BJT (MCBooks · 実力養成問題集 · Quyển đỏ) kèm giải thích tiếng Việt.</div>
            <div class="it-progress-pill">Đã làm đúng ${prog.solvedDokkai.length}/${allQ.length} câu · Đang lọc: ${filtered.length} câu${prog.wrongDokkai.length > 0 ? ` · 🔴 ${prog.wrongDokkai.length} câu hay sai` : ''}</div>
          </div>
          <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
            <button class="btn btn-primary" onclick="app.bjtWorkspace.startDokkai(false, 20)">Luyện nhanh 20 câu</button>
            <button class="btn" onclick="app.bjtWorkspace.startDokkai(false, null)">Làm hết (${filtered.length} câu)</button>
            <button class="btn" onclick="app.bjtWorkspace.startDokkai(true, 35)" style="border-color:var(--accent); color:var(--accent);">Thi thử CBT (35 câu)</button>
            ${prog.wrongDokkai.length > 0 ? `<button class="btn" onclick="app.bjtWorkspace.startDokkaiMistakes()" style="border-color:var(--danger); color:var(--danger);">Ôn ${prog.wrongDokkai.length} câu hay sai</button>` : ''}
          </div>
        </div>

        <div class="it-practice-hub-grid">
          <div class="it-practice-mode-card" onclick="app.bjtWorkspace.setDokkaiSection('vocab'); app.bjtWorkspace.startDokkai(false, null)">
            <div style="font-size:1.5rem;">🔤</div>
            <div style="font-weight:700; color:var(--text);">Dạng 1: 語彙・表現 (${cntVocab} câu)</div>
            <div style="font-size:0.82rem; color:var(--text-muted);">Chọn từ vựng thương mại và cụm từ diễn đạt chuẩn ngữ cảnh công ty Nhật.</div>
          </div>
          <div class="it-practice-mode-card" onclick="app.bjtWorkspace.setDokkaiSection('expression'); app.bjtWorkspace.startDokkai(false, null)">
            <div style="font-size:1.5rem;">🙇</div>
            <div style="font-weight:700; color:var(--text);">Dạng 2: 表現・敬語 (${cntExpr} câu)</div>
            <div style="font-size:0.82rem; color:var(--text-muted);">Diễn đạt lại câu & chọn kính ngữ đúng vai vế trong văn bản kinh doanh.</div>
          </div>
          <div class="it-practice-mode-card" onclick="app.bjtWorkspace.setDokkaiSection('document'); app.bjtWorkspace.startDokkai(false, null)">
            <div style="font-size:1.5rem;">📄</div>
            <div style="font-weight:700; color:var(--text);">Dạng 3: 文書・メール読解 (${cntDoc} câu)</div>
            <div style="font-size:0.82rem; color:var(--text-muted);">Đọc Email, thông báo nội bộ, báo cáo doanh nghiệp và nắm ý chính nhanh.</div>
          </div>
        </div>
      `;
    }

    startDokkaiMistakes() {
      if (!this.data || !this.data.dokkai) return;
      const prog = this.getProgress();
      const pool = this.data.dokkai.filter(q => prog.wrongDokkai.includes(q.id));
      if (pool.length === 0) {
        this.app.showToast('Tuyệt vời! Không còn câu Đọc hiểu sai nào.');
        return;
      }
      this._stopTimer();
      this.dokkaiRun = {
        queue: pool.sort(() => Math.random() - 0.5),
        index: 0,
        correct: 0,
        answered: false,
        timed: false,
        secondsLeft: pool.length * 60
      };
      this.renderDokkaiStep();
    }

    startDokkai(timed, limit = null) {
      if (!this.data || !this.data.dokkai) return;
      let pool = this.getFilteredDokkai();
      if (pool.length === 0) {
        this.app.showToast('Không có câu hỏi nào trong bộ lọc này.');
        return;
      }
      if (limit && limit < pool.length) {
        // Prioritize unsolved questions first when slicing a random batch
        const prog = this.getProgress();
        const unsolved = pool.filter(q => !prog.solvedDokkai.includes(q.id)).sort(() => Math.random() - 0.5);
        const solved = pool.filter(q => prog.solvedDokkai.includes(q.id)).sort(() => Math.random() - 0.5);
        pool = [...unsolved, ...solved].slice(0, limit);
      }

      this._stopTimer();
      this.dokkaiRun = {
        queue: pool,
        index: 0,
        correct: 0,
        answered: false,
        timed,
        secondsLeft: pool.length * 60 // 1 min per BJT reading question standard pace
      };

      if (timed) {
        this._timerInterval = setInterval(() => {
          if (!this.dokkaiRun) return this._stopTimer();
          this.dokkaiRun.secondsLeft = Math.max(0, this.dokkaiRun.secondsLeft - 1);
          const el = document.getElementById('bjt-timer-badge');
          if (el) el.textContent = `⏱️ ${this._fmtTime(this.dokkaiRun.secondsLeft)}`;
          if (this.dokkaiRun.secondsLeft === 0) {
            this._stopTimer();
            this.app.showToast('Hết giờ làm bài CBT!');
          }
        }, 1000);
      }

      this.renderDokkaiStep();
    }

    _fmtTime(sec) {
      const m = Math.floor(sec / 60);
      const s = sec % 60;
      return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    renderDokkaiStep() {
      const st = this.dokkaiRun;
      const body = document.getElementById('bjt-dokkai-body');
      if (!st || !body) return;

      if (st.index >= st.queue.length) {
        this._stopTimer();
        const pct = Math.round((st.correct / st.queue.length) * 100);
        body.innerHTML = `
          <div style="background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:2rem 1.5rem; text-align:center; max-width:540px; margin:0 auto;">
            <div style="font-size:2.6rem; margin-bottom:0.5rem;">🏆</div>
            <div style="font-size:1.3rem; font-weight:700; color:var(--text); margin-bottom:0.4rem;">Hoàn thành bài Đọc hiểu BJT!</div>
            <div style="font-size:1rem; color:var(--text-muted); margin-bottom:1.25rem;">
              Đúng <strong>${st.correct} / ${st.queue.length}</strong> câu (<strong>${pct}%</strong>)
            </div>
            <button class="btn btn-primary" onclick="app.bjtWorkspace.renderDokkaiHome()">Quay lại chọn dạng đề →</button>
          </div>
        `;
        return;
      }

      const q = st.queue[st.index];
      st.answered = false;
      const pct = Math.round((st.index / st.queue.length) * 100);

      body.innerHTML = `
        <div style="max-width:780px; margin:0 auto;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.75rem;">
            <button class="btn btn-sm" onclick="app.bjtWorkspace.renderDokkaiHome()">← Thoát bài</button>
            <div style="display:flex; align-items:center; gap:0.6rem;">
              ${st.timed ? `<span class="it-badge" id="bjt-timer-badge" style="background:var(--accent-soft); color:var(--accent); font-weight:700;">⏱️ ${this._fmtTime(st.secondsLeft)}</span>` : ''}
              <span style="font-size:0.85rem; font-weight:600; color:var(--text-muted);">Câu ${st.index + 1} / ${st.queue.length}</span>
            </div>
          </div>

          <div class="progress-bar" style="margin-bottom:1.1rem;">
            <div class="progress-fill" style="width:${pct}%;"></div>
          </div>

          <div class="bjt-dokkai-card">
            <div style="font-size:0.76rem; font-weight:700; color:var(--accent); margin-bottom:0.5rem;">${escapeHtml(q.sourceLabel || 'Đề 1: MCBooks')} · ${escapeHtml(q.sectionLabel || 'BJT 読解')} · Câu ${q.number || (st.index + 1)}</div>
            ${q.passageJa ? `<pre class="bjt-passage-box">${escapeHtml(q.passageJa)}</pre>` : ''}
            <div class="it-ja-line" style="font-weight:700; margin-bottom:0.85rem;">${escapeHtml(q.questionJa)}</div>

            <div>
              ${(q.options || []).map((opt, oIdx) => `
                <button class="it-practice-opt" id="bjt-dopt-${oIdx}" onclick="app.bjtWorkspace.selectDokkaiOption(${oIdx})">${escapeHtml(opt)}</button>
              `).join('')}
            </div>

            <div id="bjt-dfb" style="display:none; margin-top:0.9rem; padding:0.9rem 1rem; border-radius:10px; background:var(--surface-elevated); border:1px solid var(--border);">
              <div style="display:flex; justify-content:space-between; align-items:center; gap:0.5rem; margin-bottom:0.45rem;">
                <span id="bjt-dfb-title" style="font-weight:700;"></span>
                <button class="btn btn-sm btn-primary" onclick="app.bjtWorkspace.nextDokkaiStep()">Câu tiếp theo →</button>
              </div>
              ${q.questionVi ? `<div style="font-size:0.82rem; color:var(--text-muted); margin-bottom:0.35rem; font-style:italic;">Dịch câu hỏi: ${escapeHtml(q.questionVi)}</div>` : ''}
              <div style="font-size:0.86rem; color:var(--text); line-height:1.6;">${escapeHtml(q.explanationVi || '')}</div>
            </div>
          </div>
        </div>
      `;
    }

    selectDokkaiOption(oIdx) {
      const st = this.dokkaiRun;
      if (!st || st.answered) return;
      st.answered = true;
      const q = st.queue[st.index];
      const isCorrect = oIdx === q.answerIndex;
      if (isCorrect) {
        st.correct++;
        st.combo = (st.combo || 0) + 1;
        const prog = this.getProgress();
        if (!prog.solvedDokkai.includes(q.id)) {
          prog.solvedDokkai.push(q.id);
          this.saveProgress(prog);
        }
      } else {
        st.combo = 0;
      }
      this._recordMistake('wrongDokkai', q.id, isCorrect);

      (q.options || []).forEach((_, idx) => {
        const btn = document.getElementById(`bjt-dopt-${idx}`);
        if (!btn) return;
        if (idx === q.answerIndex) btn.classList.add('correct');
        else if (idx === oIdx && !isCorrect) btn.classList.add('incorrect');
        btn.disabled = true;
      });

      if (global.BJTManga) {
        global.BJTManga.spawnSFX(document.getElementById(`bjt-dopt-${oIdx}`), isCorrect, st.combo);
        if (isCorrect && st.combo >= 2) {
          global.BJTManga.flashSpeedlines(document.querySelector('#bjt-dokkai-body .bjt-dokkai-card'));
        }
      }

      const fb = document.getElementById('bjt-dfb');
      const title = document.getElementById('bjt-dfb-title');
      if (title) {
        title.textContent = isCorrect ? '✓ Chính xác!' : `✗ Chưa chính xác (Đáp án đúng: ${q.answerIndex + 1})`;
        title.style.color = isCorrect ? 'var(--success)' : 'var(--danger)';
      }
      if (fb) fb.style.display = 'block';
    }

    nextDokkaiStep() {
      if (!this.dokkaiRun) return;
      this.dokkaiRun.index++;
      this.renderDokkaiStep();
    }
  }

  global.BJTWorkspace = BJTWorkspace;
})(window);
