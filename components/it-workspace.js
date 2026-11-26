/**
 * Standalone Workspace Switcher & IT Nihongo Studio Component
 * Encapsulates:
 *   1. WorkspaceController: Notion/Linear-style switcher between "kanji" and "it"
 *      workspaces with smooth morph animations, dynamic theming, and URL hash sync.
 *   2. ITWorkspace: Complete 3-tab IT Japanese learning studio (23 Units, 848-term
 *      IT Dictionary, and Flashcard/Quiz Practice Hub).
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

  class WorkspaceController {
    constructor(app) {
      this.app = app;
      this.current = 'kanji';
      this._toastTimer = null;
      this._bindOutsideClick();
    }

    initFromUrlOrStorage() {
      const hash = (window.location.hash || '').toLowerCase();
      let initial = 'kanji';
      if (hash.startsWith('#it')) {
        initial = 'it';
      } else if (hash.startsWith('#bjt')) {
        initial = 'bjt';
      } else if (hash.startsWith('#kanji')) {
        initial = 'kanji';
      } else {
        const saved = localStorage.getItem('kanji_active_workspace');
        if (saved === 'it' || saved === 'kanji' || saved === 'bjt') initial = saved;
      }
      this.switchTo(initial, { animate: false, updateHash: false });
      if (initial === 'it') {
        if (hash === '#it/dict') this.app.itWorkspace.navigateSubView('dict');
        else if (hash === '#it/practice') this.app.itWorkspace.navigateSubView('practice');
        else this.app.itWorkspace.navigateSubView('units');
      } else if (initial === 'bjt') {
        if (hash === '#bjt/vocab') this.app.bjtWorkspace.navigateSubView('vocab');
        else if (hash === '#bjt/email') this.app.bjtWorkspace.navigateSubView('email');
        else if (hash === '#bjt/dokkai') this.app.bjtWorkspace.navigateSubView('dokkai');
        else this.app.bjtWorkspace.navigateSubView('keigo');
      }
    }

    toggleMenu(event) {
      if (event) event.stopPropagation();
      const el = document.getElementById('workspace-switcher');
      if (el) el.classList.toggle('open');
    }

    closeMenu() {
      const el = document.getElementById('workspace-switcher');
      if (el) el.classList.remove('open');
    }

    _bindOutsideClick() {
      document.addEventListener('click', (e) => {
        const el = document.getElementById('workspace-switcher');
        if (el && el.classList.contains('open') && !el.contains(e.target)) {
          el.classList.remove('open');
        }
      });
    }

    switchTo(workspace, opts = {}) {
      const { animate = true, updateHash = true } = opts;
      if (workspace !== 'kanji' && workspace !== 'it' && workspace !== 'bjt') return;
      const changed = this.current !== workspace;
      this.current = workspace;
      this.closeMenu();

      document.documentElement.setAttribute('data-workspace', workspace);
      localStorage.setItem('kanji_active_workspace', workspace);

      const meta = {
        kanji: {
          icon: '漢',
          title: '漢字マスター',
          sub: 'JLPT Kanji N5–N1',
          docTitle: '漢字マスター (N5 - N1) — Kanji Study App',
          toastTitle: 'Kanji Master JLPT',
          toastSub: 'Luyện thi Kanji N5 – N1'
        },
        it: {
          icon: 'IT',
          title: 'IT Nihongo',
          sub: 'しごとの日本語 · 23 bài',
          docTitle: 'IT Nihongo — しごとの日本語 IT業務編',
          toastTitle: 'IT Nihongo Studio',
          toastSub: '23 bài · 848 thuật ngữ IT thực chiến'
        },
        bjt: {
          icon: 'BJT',
          title: 'BJT Prep',
          sub: 'Kính ngữ · Từ vựng · Email · Đọc hiểu',
          docTitle: 'BJT Prep — ビジネス日本語能力テスト',
          toastTitle: 'BJT Business Prep',
          toastSub: '50 Kính ngữ · 228 Từ vựng · 40 Email · 160 Đọc hiểu'
        }
      }[workspace];

      const iconEl = document.getElementById('ws-trigger-icon');
      const titleEl = document.getElementById('ws-trigger-title');
      const subEl = document.getElementById('ws-trigger-sub');
      if (iconEl) {
        iconEl.className = `ws-badge-icon ${workspace}`;
        iconEl.textContent = meta.icon;
      }
      if (titleEl) titleEl.textContent = meta.title;
      if (subEl) subEl.textContent = meta.sub;
      document.title = meta.docTitle;

      document.querySelectorAll('.ws-option').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.ws === workspace);
      });

      if (updateHash) {
        const targetHash = `#${workspace}`;
        if (window.location.hash !== targetHash) {
          history.replaceState(null, '', targetHash);
        }
      }

      if (animate && changed) {
        this._playSwitchAnimation(workspace, meta);
      }

      if (workspace === 'it') {
        this.app.navigate('it');
        this.app.itWorkspace.navigateSubView('units');
      } else if (workspace === 'bjt') {
        this.app.navigate('bjt');
        this.app.bjtWorkspace.navigateSubView('keigo');
      } else {
        this.app.navigate('home');
      }
    }

    _playSwitchAnimation(workspace, meta) {
      const mainEl = document.querySelector('main');
      if (mainEl) {
        mainEl.classList.remove('ws-animating');
        void mainEl.offsetWidth;
        mainEl.classList.add('ws-animating');
      }

      const toast = document.getElementById('ws-transition-toast');
      if (!toast) return;
      const icon = toast.querySelector('.ws-badge-icon');
      const label = toast.querySelector('#ws-transition-label');
      const sub = toast.querySelector('#ws-transition-sub');
      if (icon) {
        icon.className = `ws-badge-icon ${workspace}`;
        icon.textContent = meta.icon;
      }
      if (label) label.textContent = meta.toastTitle;
      if (sub) sub.textContent = meta.toastSub;

      toast.classList.add('show');
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => {
        toast.classList.remove('show');
      }, 650);
    }
  }

  class ITWorkspace {
    constructor(app) {
      this.app = app;
      this.data = null;
      this.subView = 'units'; // 'units' | 'dict' | 'practice'
      this.chapterFilter = 'all';
      this.dictChapterFilter = 'all';
      this.dictTierFilter = 'all';
      this.showVi = true;
      this.currentUnitIdx = 0;
      this.currentUnit = null;
      this.study = null;
      this._skimTimer = null;
    }

    getProgress() {
      try {
        const raw = localStorage.getItem('kanji_it_japanese_progress_v1');
        if (raw) {
          const p = JSON.parse(raw);
          return {
            completedUnits: Array.isArray(p.completedUnits) ? p.completedUnits : [],
            masteredVocab: Array.isArray(p.masteredVocab) ? p.masteredVocab : [],
            wrongVocab: Array.isArray(p.wrongVocab) ? p.wrongVocab : []
          };
        }
      } catch (e) {}
      return { completedUnits: [], masteredVocab: [], wrongVocab: [] };
    }

    saveProgress(prog) {
      localStorage.setItem('kanji_it_japanese_progress_v1', JSON.stringify(prog));
    }

    _recordMistake(vKey, isCorrect) {
      if (!vKey) return;
      const prog = this.getProgress();
      const idx = prog.wrongVocab.indexOf(vKey);
      if (!isCorrect) {
        if (idx === -1) {
          prog.wrongVocab.push(vKey);
          this.saveProgress(prog);
        }
      } else if (idx !== -1) {
        prog.wrongVocab.splice(idx, 1);
        this.saveProgress(prog);
        this.app.showToast('✓ Đã gỡ khỏi sổ từ hay sai!');
      }
    }

    _stopSkimTimer() {
      if (this._skimTimer) {
        clearInterval(this._skimTimer);
        this._skimTimer = null;
      }
    }

    async ensureDataLoaded() {
      if (this.data) return true;
      const grid = document.getElementById('it-units-grid');
      if (grid) {
        grid.innerHTML = '<div style="color:var(--text-muted); padding:2rem; text-align:center;">Đang tải 23 bài Tiếng Nhật IT...</div>';
      }
      try {
        const res = await fetch('/data/it-japanese.json?v=2');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        this.data = await res.json();
        return true;
      } catch (e) {
        if (grid) {
          grid.innerHTML = '<div style="color:var(--danger); padding:2rem; text-align:center;">Không thể tải dữ liệu Tiếng Nhật IT. Vui lòng thử lại.</div>';
        }
        return false;
      }
    }

    async navigateSubView(subView) {
      this.subView = subView;
      if (this.app.currentView !== 'it') {
        this.app.navigate('it');
      }

      // Sync IT desktop & mobile nav active states
      document.querySelectorAll('.it-nav-btn, .it-mobile-nav-item').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.itsub === subView);
      });

      const hashMap = { units: '#it', dict: '#it/dict', practice: '#it/practice' };
      if (hashMap[subView] && window.location.hash !== hashMap[subView]) {
        history.replaceState(null, '', hashMap[subView]);
      }

      // Hide all panels inside #view-it
      ['it-home-panel', 'it-unit-panel', 'it-dict-panel', 'it-practice-hub-panel', 'it-study-panel'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
      });

      const ok = await this.ensureDataLoaded();
      if (!ok) return;

      if (subView === 'units') {
        document.getElementById('it-home-panel').style.display = 'block';
        this.renderOverview();
      } else if (subView === 'dict') {
        document.getElementById('it-dict-panel').style.display = 'block';
        this.renderDictionary();
      } else if (subView === 'practice') {
        document.getElementById('it-practice-hub-panel').style.display = 'block';
        this.renderPracticeHub();
      }
    }

    setChapterFilter(ch) {
      this.chapterFilter = ch;
      document.querySelectorAll('#it-chapter-pills .it-pill-btn').forEach(btn => {
        btn.classList.toggle('active', String(btn.dataset.ch) === String(ch));
      });
      this.renderOverview();
    }

    getFilteredUnits(chapterOverride) {
      if (!this.data || !this.data.units) return [];
      const ch = chapterOverride !== undefined ? chapterOverride : this.chapterFilter;
      if (ch === 'all') return this.data.units;
      return this.data.units.filter(u => String(u.chapter) === String(ch));
    }

    renderOverview() {
      if (!this.data || !this.data.units) return;
      const prog = this.getProgress();
      const totalUnits = this.data.units.length;
      const allVocabCount = this.data.units.reduce((acc, u) => acc + (u.vocab ? u.vocab.length : 0), 0);
      const summaryEl = document.getElementById('it-progress-summary');
      if (summaryEl) {
        summaryEl.textContent = `Đã học ${prog.completedUnits.length}/${totalUnits} bài · Thuộc ${prog.masteredVocab.length}/${allVocabCount} từ IT`;
      }

      const units = this.getFilteredUnits();
      const grid = document.getElementById('it-units-grid');
      if (!grid) return;

      grid.innerHTML = units.map(u => {
        const isDone = prog.completedUnits.includes(u.id);
        const vCount = (u.vocab || []).length;
        const pCount = (u.practice || []).length;
        return `
          <div class="it-unit-card ${isDone ? 'done' : ''}" onclick="app.itWorkspace.openUnit('${escapeHtml(u.id)}')">
            <div class="it-unit-meta">
              <span>Chương ${u.chapter} · Unit ${u.unit}</span>
              ${isDone ? '<span class="it-badge done">✓ Đã học</span>' : ''}
            </div>
            <div class="it-unit-ja">${escapeHtml(u.titleJa)}</div>
            <div class="it-unit-vi">${escapeHtml(u.titleVi)}</div>
            <div class="it-unit-summary">${escapeHtml(u.summaryVi || '')}</div>
            <div class="it-unit-badges">
              <span class="it-badge">🃏 ${vCount} từ IT</span>
              ${pCount > 0 ? `<span class="it-badge">✏️ ${pCount} tình huống</span>` : ''}
            </div>
          </div>
        `;
      }).join('');
    }

    renderDictionary() {
      if (!this.data || !this.data.units) return;
      const prog = this.getProgress();
      const q = ((document.getElementById('it-dict-search') || {}).value || '').trim().toLowerCase();
      const ch = (document.getElementById('it-dict-ch-filter') || {}).value || 'all';
      const tier = (document.getElementById('it-dict-tier-filter') || {}).value || 'all';

      const items = [];
      this.data.units.forEach(u => {
        if (ch !== 'all' && String(u.chapter) !== String(ch)) return;
        (u.vocab || []).forEach(v => {
          const vKey = `${u.id}::${v.word}`;
          const isMastered = prog.masteredVocab.includes(vKey);
          if (tier === 'core' && v.tier === 'advanced') return;
          if (tier === 'advanced' && v.tier !== 'advanced') return;
          if (tier === 'mastered' && !isMastered) return;
          if (tier === 'unlearned' && isMastered) return;
          if (q) {
            const hay = `${v.word} ${v.reading} ${v.vi} ${v.en}`.toLowerCase();
            if (!hay.includes(q)) return;
          }
          items.push({ unit: u, vocab: v, vKey, isMastered });
        });
      });

      const countEl = document.getElementById('it-dict-count');
      if (countEl) countEl.textContent = `Hiển thị ${items.length} thuật ngữ IT`;

      const listEl = document.getElementById('it-dict-list');
      if (!listEl) return;
      if (items.length === 0) {
        listEl.innerHTML = '<div style="color:var(--text-muted); padding:2rem; text-align:center;">Không tìm thấy thuật ngữ nào khớp bộ lọc.</div>';
        return;
      }

      const slice = items.slice(0, 120);
      listEl.innerHTML = slice.map(m => {
        const v = m.vocab;
        const u = m.unit;
        const wordSafe = escapeHtml(v.word).replace(/'/g, "\\'");
        const keySafe = escapeHtml(m.vKey).replace(/'/g, "\\'");
        return `
          <div class="it-vocab-item ${m.isMastered ? 'mastered' : ''}">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:0.4rem;">
              <span style="font-family:var(--font-jp); font-size:1.05rem; font-weight:700; color:var(--text);">${escapeHtml(v.word)}</span>
              <div style="display:flex; gap:0.3rem;">
                <button class="icon-btn" title="Phát âm" onclick="app.speakText('${wordSafe}')" style="width:1.7rem;height:1.7rem;font-size:0.75rem;">🔊</button>
                <button class="icon-btn" title="${m.isMastered ? 'Đã thuộc' : 'Đánh dấu đã thuộc'}" onclick="app.itWorkspace.toggleVocabMastered('${keySafe}', true)" style="width:1.7rem;height:1.7rem;font-size:0.75rem; ${m.isMastered ? 'background:var(--success-soft);color:var(--success);border-color:var(--success);' : ''}">✓</button>
              </div>
            </div>
            <div style="font-family:var(--font-jp); font-size:0.82rem; color:var(--accent);">${escapeHtml(v.reading || '')}</div>
            <div style="font-size:0.87rem; color:var(--text); font-weight:500;">${escapeHtml(v.vi || '')}</div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.25rem; gap:0.4rem;">
              <span style="font-size:0.74rem; color:var(--text-subtle); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(v.en || '')}</span>
              <button class="btn btn-sm" style="padding:0.15rem 0.45rem; font-size:0.72rem; flex-shrink:0;" onclick="app.itWorkspace.openUnit('${escapeHtml(u.id)}')">Ch.${u.chapter} U${u.unit} →</button>
            </div>
          </div>
        `;
      }).join('') + (items.length > 120 ? `<div style="grid-column:1/-1; text-align:center; font-size:0.82rem; color:var(--text-muted); padding:0.5rem;">Đang hiển thị 120/${items.length} kết quả — hãy gõ từ khóa cụ thể hơn để lọc nhanh.</div>` : '');
    }

    renderPracticeHub() {
      if (!this.data || !this.data.units) return;
      const prog = this.getProgress();
      const allCount = this.data.units.reduce((acc, u) => acc + (u.vocab ? u.vocab.length : 0), 0);
      const unlearnedCount = Math.max(0, allCount - prog.masteredVocab.length);

      const hub = document.getElementById('it-practice-hub-grid');
      if (!hub) return;
      hub.innerHTML = `
        ${prog.wrongVocab.length > 0 ? `
          <div class="it-practice-mode-card" style="border-color:var(--danger);" onclick="app.itWorkspace.startStudy('quiz', 'mistakes')">
            <div style="font-size:1.6rem;">🔴</div>
            <div style="font-weight:700; font-size:1rem; color:var(--danger);">Ôn lại ${prog.wrongVocab.length} từ hay sai</div>
            <div style="font-size:0.82rem; color:var(--text-muted); line-height:1.45;">Tự động gom các thuật ngữ bạn từng chọn nhầm. Trả lời đúng sẽ tự gỡ khỏi danh sách.</div>
          </div>
        ` : ''}
        <div class="it-practice-mode-card" style="border-color:var(--accent);" onclick="app.itWorkspace.startStudy('cloze', 'all', 20)">
          <div style="font-size:1.6rem;">🧩</div>
          <div style="font-weight:700; font-size:1rem; color:var(--text);">Điền từ vào hội thoại IT (Cloze 20 câu)</div>
          <div style="font-size:0.82rem; color:var(--text-muted); line-height:1.45;">Đục lỗ trực tiếp trên câu hội thoại & mẫu câu thực tế trong sách — học theo ngữ cảnh thay vì học từ rời.</div>
        </div>
        <div class="it-practice-mode-card" onclick="app.itWorkspace.startStudy('quiz', 'ch2', 20)">
          <div style="font-size:1.6rem;">🔥</div>
          <div style="font-weight:700; font-size:1rem; color:var(--text);">Trắc nghiệm nhanh Dự án (Ch.2)</div>
          <div style="font-size:0.82rem; color:var(--text-muted); line-height:1.45;">20 câu ngẫu nhiên từ 15 bài thực chiến dự án (SRS, thiết kế, delay, test, demo).</div>
        </div>
        <div class="it-practice-mode-card" onclick="app.itWorkspace.startStudy('flashcard', 'unlearned')">
          <div style="font-size:1.6rem;">🃏</div>
          <div style="font-weight:700; font-size:1rem; color:var(--text);">Flashcard từ chưa thuộc (${unlearnedCount})</div>
          <div style="font-size:0.82rem; color:var(--text-muted); line-height:1.45;">Tập trung ôn các thuật ngữ IT bạn chưa đánh dấu thuộc, có lặp lại từ quên.</div>
        </div>
        <div class="it-practice-mode-card" onclick="app.itWorkspace.startStudy('quiz', 'all', 40)">
          <div style="font-size:1.6rem;">🎯</div>
          <div style="font-weight:700; font-size:1rem; color:var(--text);">Tổng ôn 40 câu Toàn sách</div>
          <div style="font-size:0.82rem; color:var(--text-muted); line-height:1.45;">Kiểm tra toàn diện cả 3 chương (Tìm việc · Dự án · Đọc Spec), xen kẽ Nhật→Việt & Việt→Nhật.</div>
        </div>
        <div class="it-practice-mode-card" onclick="app.itWorkspace.startStudy('flashcard', 'ch3')">
          <div style="font-size:1.6rem;">📄</div>
          <div style="font-weight:700; font-size:1rem; color:var(--text);">Flashcard Đọc Spec (Ch.3)</div>
          <div style="font-size:0.82rem; color:var(--text-muted); line-height:1.45;">Thuật ngữ bảng dữ liệu, tồn kho, đơn hàng, điều kiện lọc thường gặp trong Spec Nhật.</div>
        </div>
      `;
    }

    openUnit(unitId) {
      if (!this.data || !this.data.units) return;
      const idx = this.data.units.findIndex(u => u.id === unitId);
      if (idx === -1) return;
      this.currentUnitIdx = idx;
      this.currentUnit = this.data.units[idx];

      ['it-home-panel', 'it-dict-panel', 'it-practice-hub-panel', 'it-study-panel'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
      });
      document.getElementById('it-unit-panel').style.display = 'block';

      const u = this.currentUnit;
      document.getElementById('it-unit-detail-meta').textContent = `Chương ${u.chapter} · Unit ${u.unit}${u.reading ? ' · ' + u.reading : ''}`;
      document.getElementById('it-unit-detail-ja').textContent = u.titleJa;
      document.getElementById('it-unit-detail-vi').textContent = u.titleVi;
      document.getElementById('it-unit-detail-summary').textContent = u.summaryVi || '';

      const vBtn = document.getElementById('it-subtab-vocab-btn');
      if (vBtn) vBtn.textContent = `🃏 Từ vựng IT (${(u.vocab || []).length})`;
      const pBtn = document.getElementById('it-subtab-practice-btn');
      if (pBtn) pBtn.textContent = `✏️ Luyện tập (${(u.practice || []).length})`;

      const prevBtn = document.getElementById('it-btn-prev-unit');
      const nextBtn = document.getElementById('it-btn-next-unit');
      if (prevBtn) prevBtn.disabled = idx <= 0;
      if (nextBtn) nextBtn.disabled = idx >= this.data.units.length - 1;

      this.updateUnitDoneButton();
      this.renderUnitContext();
      this.renderUnitVocab();
      this.renderUnitPractice();
      this.switchUnitTab('context');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    closeUnit() {
      this.navigateSubView('units');
    }

    navigateUnit(delta) {
      if (!this.data || !this.data.units) return;
      const nextIdx = this.currentUnitIdx + delta;
      if (nextIdx >= 0 && nextIdx < this.data.units.length) {
        this.openUnit(this.data.units[nextIdx].id);
      }
    }

    updateUnitDoneButton() {
      const btn = document.getElementById('it-btn-toggle-done');
      if (!btn || !this.currentUnit) return;
      const prog = this.getProgress();
      const isDone = prog.completedUnits.includes(this.currentUnit.id);
      btn.textContent = isDone ? '✓ Đã hoàn thành bài này' : '○ Đánh dấu đã học';
      btn.style.background = isDone ? 'var(--success-soft)' : '';
      btn.style.borderColor = isDone ? 'var(--success)' : '';
      btn.style.color = isDone ? 'var(--success)' : '';
    }

    toggleUnitDone() {
      if (!this.currentUnit) return;
      const prog = this.getProgress();
      const id = this.currentUnit.id;
      const i = prog.completedUnits.indexOf(id);
      if (i === -1) {
        prog.completedUnits.push(id);
        this.app.showToast('Đã đánh dấu hoàn thành bài học IT!');
      } else {
        prog.completedUnits.splice(i, 1);
      }
      this.saveProgress(prog);
      this.updateUnitDoneButton();
    }

    switchUnitTab(tabName) {
      ['context', 'vocab', 'practice'].forEach(t => {
        const el = document.getElementById(`it-tab-${t}`);
        if (el) el.style.display = (t === tabName) ? 'block' : 'none';
      });
      document.querySelectorAll('#it-unit-panel .it-subtab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
      });
    }

    toggleTranslation() {
      this.showVi = !this.showVi;
      document.querySelectorAll('#it-tab-context .it-vi-line').forEach(el => {
        el.classList.toggle('hidden-vi', !this.showVi);
      });
      const btn = document.getElementById('it-toggle-vi-btn');
      if (btn) btn.textContent = this.showVi ? '👁️ Ẩn dịch Việt (Tự đọc hiểu)' : '👁️ Hiện dịch Việt';
    }

    renderUnitContext() {
      const u = this.currentUnit;
      const el = document.getElementById('it-tab-context');
      if (!el || !u) return;

      const dialogueHtml = (u.dialogue || []).map(line => {
        const jaSafe = escapeHtml(line.ja).replace(/'/g, "\\'");
        return `
          <div class="it-dialogue-row">
            <div style="flex:1;">
              <span class="it-speaker">${escapeHtml(line.speaker || 'Nội dung')}</span>
              <div class="it-ja-line">${escapeHtml(line.ja)}</div>
              <div class="it-vi-line ${this.showVi ? '' : 'hidden-vi'}">${escapeHtml(line.vi || '')}</div>
            </div>
            <button class="icon-btn" title="Nghe câu này" onclick="app.speakText('${jaSafe}')" style="width:1.9rem;height:1.9rem;font-size:0.8rem;flex-shrink:0;">🔊</button>
          </div>
        `;
      }).join('');

      const pointsHtml = (u.points || []).length > 0 ? `
        <div style="font-size:0.85rem; font-weight:700; color:var(--text); margin:1.25rem 0 0.6rem;">💡 Điểm lưu ý thực tế trong công ty Nhật (ポイント)</div>
        ${(u.points || []).map(pt => `
          <div class="it-tip-card">
            <div style="font-weight:700; font-size:0.88rem; color:var(--text); margin-bottom:0.2rem;">${escapeHtml(pt.title)}</div>
            <div style="font-size:0.84rem; color:var(--text-muted); line-height:1.5;">${escapeHtml(pt.detailVi)}</div>
          </div>
        `).join('')}
      ` : '';

      const exprHtml = (u.expressions || []).length > 0 ? `
        <div style="font-size:0.85rem; font-weight:700; color:var(--text); margin:1.25rem 0 0.6rem;">🗣️ Mẫu câu & Cách diễn đạt cốt lõi (表現の理解)</div>
        ${(u.expressions || []).map(ex => {
          const jaSafe = escapeHtml(ex.ja).replace(/'/g, "\\'");
          return `
            <div class="it-dialogue-row">
              <div style="flex:1;">
                <div class="it-ja-line">${escapeHtml(ex.ja)}</div>
                <div style="font-size:0.86rem; color:var(--accent); font-weight:600; margin-top:0.2rem;">${escapeHtml(ex.vi)}</div>
                ${ex.noteVi ? `<div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.2rem;">${escapeHtml(ex.noteVi)}</div>` : ''}
              </div>
              <button class="icon-btn" title="Nghe mẫu câu" onclick="app.speakText('${jaSafe}')" style="width:1.9rem;height:1.9rem;font-size:0.8rem;flex-shrink:0;">🔊</button>
            </div>
          `;
        }).join('')}
      ` : '';

      el.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.75rem;">
          <span style="font-size:0.85rem; font-weight:700; color:var(--text);">${u.chapter === 3 ? '📄 Nội dung đặc tả / Flowchart (仕様書)' : '💬 Hội thoại ngữ cảnh thực tế (モデル会話)'}</span>
          <div style="display:flex; gap:0.4rem; flex-wrap:wrap;">
            <button class="btn btn-sm" id="it-skim-btn" onclick="app.itWorkspace.startUnitSkim()" style="border-color:var(--accent); color:var(--accent);">⏱️ Đọc nhanh 30s</button>
            <button class="btn btn-sm" id="it-toggle-vi-btn" onclick="app.itWorkspace.toggleTranslation()">${this.showVi ? '👁️ Ẩn dịch Việt (Tự đọc hiểu)' : '👁️ Hiện dịch Việt'}</button>
          </div>
        </div>
        ${dialogueHtml || '<div style="color:var(--text-muted);">Bài này trong bản scan không có trang hội thoại — bạn chuyển sang tab Từ vựng IT để luyện tập nhé.</div>'}
        ${pointsHtml}
        ${exprHtml}
      `;
    }

    startUnitSkim() {
      this._stopSkimTimer();
      this.showVi = false;
      document.querySelectorAll('#it-tab-context .it-vi-line').forEach(el => el.classList.add('hidden-vi'));
      const toggleBtn = document.getElementById('it-toggle-vi-btn');
      if (toggleBtn) toggleBtn.textContent = '👁️ Hiện dịch Việt';

      let sec = 30;
      const btn = document.getElementById('it-skim-btn');
      if (btn) btn.textContent = `⏱️ Đang đọc... ${sec}s`;
      this._skimTimer = setInterval(() => {
        sec--;
        const b = document.getElementById('it-skim-btn');
        if (sec <= 0) {
          this._stopSkimTimer();
          this.showVi = true;
          document.querySelectorAll('#it-tab-context .it-vi-line').forEach(el => el.classList.remove('hidden-vi'));
          const tb = document.getElementById('it-toggle-vi-btn');
          if (tb) tb.textContent = '👁️ Ẩn dịch Việt (Tự đọc hiểu)';
          if (b) b.textContent = '⏱️ Đọc nhanh 30s';
          this.app.showToast('Hết 30s — Đã mở bản dịch để bạn đối chiếu!');
        } else if (b) {
          b.textContent = `⏱️ Đang đọc... ${sec}s`;
        }
      }, 1000);
    }

    toggleVocabMastered(vocabKey, fromDict = false) {
      const prog = this.getProgress();
      const i = prog.masteredVocab.indexOf(vocabKey);
      if (i === -1) prog.masteredVocab.push(vocabKey);
      else prog.masteredVocab.splice(i, 1);
      this.saveProgress(prog);
      if (fromDict) this.renderDictionary();
      else this.renderUnitVocab();
    }

    renderUnitVocab() {
      const u = this.currentUnit;
      const el = document.getElementById('it-tab-vocab');
      if (!el || !u) return;
      const prog = this.getProgress();
      const core = (u.vocab || []).filter(v => v.tier !== 'advanced');
      const adv = (u.vocab || []).filter(v => v.tier === 'advanced');

      const renderGroup = (items) => items.map(v => {
        const vKey = `${u.id}::${v.word}`;
        const isM = prog.masteredVocab.includes(vKey);
        const wordSafe = escapeHtml(v.word).replace(/'/g, "\\'");
        const keySafe = escapeHtml(vKey).replace(/'/g, "\\'");
        return `
          <div class="it-vocab-item ${isM ? 'mastered' : ''}">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:0.4rem;">
              <span style="font-family:var(--font-jp); font-size:1.05rem; font-weight:700; color:var(--text);">${escapeHtml(v.word)}</span>
              <div style="display:flex; gap:0.3rem;">
                <button class="icon-btn" title="Phát âm" onclick="app.speakText('${wordSafe}')" style="width:1.7rem;height:1.7rem;font-size:0.75rem;">🔊</button>
                <button class="icon-btn" title="${isM ? 'Đã thuộc' : 'Đánh dấu đã thuộc'}" onclick="app.itWorkspace.toggleVocabMastered('${keySafe}')" style="width:1.7rem;height:1.7rem;font-size:0.75rem; ${isM ? 'background:var(--success-soft);color:var(--success);border-color:var(--success);' : ''}">✓</button>
              </div>
            </div>
            <div style="font-family:var(--font-jp); font-size:0.82rem; color:var(--accent);">${escapeHtml(v.reading || '')}</div>
            <div style="font-size:0.87rem; color:var(--text); font-weight:500;">${escapeHtml(v.vi || '')}</div>
            ${v.en ? `<div style="font-size:0.75rem; color:var(--text-subtle);">${escapeHtml(v.en)}</div>` : ''}
          </div>
        `;
      }).join('');

      el.innerHTML = `
        <div style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-bottom:1rem;">
          <button class="btn btn-sm btn-primary" onclick="app.itWorkspace.startStudy('flashcard', 'unit')">🃏 Học Flashcard bài này</button>
          <button class="btn btn-sm" onclick="app.itWorkspace.startStudy('quiz', 'unit')" style="border-color:var(--accent); color:var(--accent); font-weight:600;">⚡ Trắc nghiệm bài này</button>
        </div>
        <div style="font-size:0.84rem; font-weight:700; color:var(--text); margin-bottom:0.55rem;">📌 Từ vựng cốt lõi trong bài — 語彙 (${core.length})</div>
        <div class="it-vocab-list">${renderGroup(core)}</div>
        ${adv.length > 0 ? `
          <div style="font-size:0.84rem; font-weight:700; color:var(--text); margin:0.8rem 0 0.55rem;">🚀 Thuật ngữ IT mở rộng — 発展語彙 (${adv.length})</div>
          <div class="it-vocab-list">${renderGroup(adv)}</div>
        ` : ''}
      `;
    }

    renderUnitPractice() {
      const u = this.currentUnit;
      const el = document.getElementById('it-tab-practice');
      if (!el || !u) return;
      const list = u.practice || [];
      if (list.length === 0) {
        el.innerHTML = '<div style="color:var(--text-muted); padding:1rem 0;">Bài này tập trung vào thực hành tự viết. Bạn có thể chuyển sang tab Từ vựng IT để luyện Flashcard/Trắc nghiệm!</div>';
        return;
      }
      el.innerHTML = list.map((q, qIdx) => `
        <div class="it-practice-card" id="it-prac-${qIdx}">
          <div style="font-size:0.75rem; font-weight:700; color:var(--accent); margin-bottom:0.35rem;">TÌNH HUỐNG ${qIdx + 1} · やってみよう！</div>
          <div class="it-ja-line" style="margin-bottom:0.85rem;">${escapeHtml(q.questionJa)}</div>
          <div>
            ${(q.options || []).map((opt, oIdx) => `
              <button class="it-practice-opt" data-q="${qIdx}" data-o="${oIdx}" onclick="app.itWorkspace.answerPractice(${qIdx}, ${oIdx})">${escapeHtml(opt)}</button>
            `).join('')}
          </div>
          <div id="it-prac-fb-${qIdx}" style="display:none; margin-top:0.75rem; padding:0.75rem; border-radius:8px; background:var(--surface-elevated); font-size:0.85rem; line-height:1.5;"></div>
        </div>
      `).join('');
    }

    answerPractice(qIdx, oIdx) {
      if (!this.currentUnit || !this.currentUnit.practice) return;
      const q = this.currentUnit.practice[qIdx];
      if (!q) return;
      const card = document.getElementById(`it-prac-${qIdx}`);
      if (!card) return;
      const buttons = card.querySelectorAll('.it-practice-opt');
      const ans = q.answerIndex;
      const isCorrect = Array.isArray(ans) ? ans.includes(oIdx) : (oIdx === ans);
      buttons.forEach((b, idx) => {
        const isRightOpt = Array.isArray(ans) ? ans.includes(idx) : (idx === ans);
        if (isRightOpt) b.classList.add('correct');
        else if (idx === oIdx && !isCorrect) b.classList.add('incorrect');
        b.disabled = true;
      });
      const fb = document.getElementById(`it-prac-fb-${qIdx}`);
      if (fb) {
        fb.style.display = 'block';
        fb.innerHTML = `
          <div style="font-weight:700; color:${isCorrect ? 'var(--success)' : 'var(--danger)'}; margin-bottom:0.25rem;">
            ${isCorrect ? '✓ Chính xác!' : '✗ Chưa chính xác'}
          </div>
          ${q.questionVi ? `<div style="font-size:0.82rem; color:var(--text-muted); margin-bottom:0.3rem; font-style:italic;">Dịch câu hỏi: ${escapeHtml(q.questionVi)}</div>` : ''}
          <div style="color:var(--text);">${escapeHtml(q.explanationVi || '')}</div>
        `;
      }
    }

    startStudy(mode, scope, limit = null) {
      if (!this.data || !this.data.units) return;
      const prog = this.getProgress();
      let sourceUnits = [];
      if (scope === 'unit' && this.currentUnit) {
        sourceUnits = [this.currentUnit];
      } else if (scope === 'ch2') {
        sourceUnits = this.getFilteredUnits(2);
      } else if (scope === 'ch3') {
        sourceUnits = this.getFilteredUnits(3);
      } else if (scope === 'all' || scope === 'unlearned' || scope === 'mistakes') {
        sourceUnits = this.data.units;
      } else {
        sourceUnits = this.getFilteredUnits();
      }

      const pool = [];
      sourceUnits.forEach(u => {
        const unitSentences = [
          ...(u.dialogue || []).map(d => ({ ja: d.ja, vi: d.vi || '' })),
          ...(u.expressions || []).map(e => ({ ja: e.ja, vi: e.vi || '' }))
        ];
        (u.vocab || []).forEach(v => {
          const vKey = `${u.id}::${v.word}`;
          if (scope === 'unlearned' && prog.masteredVocab.includes(vKey)) return;
          if (scope === 'mistakes' && !prog.wrongVocab.includes(vKey)) return;
          let clozeSentence = null;
          if (mode === 'cloze') {
            if (!v.word || v.word.length < 2) return;
            const match = unitSentences.find(s => s.ja && s.ja.includes(v.word));
            if (!match) return;
            clozeSentence = match;
          }
          pool.push({
            ...v,
            unitId: u.id,
            unitLabel: `Ch.${u.chapter} U${u.unit} · ${u.titleJa}`,
            vKey,
            clozeSentence
          });
        });
      });

      if (pool.length === 0) {
        this.app.showToast(scope === 'mistakes' ? 'Tuyệt vời! Không còn từ hay sai nào.' : 'Tuyệt vời! Không còn từ chưa thuộc trong phạm vi này.');
        return;
      }

      pool.sort(() => Math.random() - 0.5);
      const maxCount = limit || (((mode === 'quiz' || mode === 'cloze') && scope !== 'unit' && scope !== 'mistakes') ? 25 : (scope === 'unlearned' ? 30 : pool.length));
      const queue = pool.slice(0, maxCount);

      this.study = {
        mode,
        scope,
        returnSubView: scope === 'unit' ? 'unit' : this.subView,
        queue,
        allPool: this.data.units.flatMap(u => (u.vocab || []).map(v => ({ ...v, unitId: u.id }))),
        index: 0,
        flipped: false,
        correct: 0,
        answered: false
      };

      ['it-home-panel', 'it-unit-panel', 'it-dict-panel', 'it-practice-hub-panel'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
      });
      document.getElementById('it-study-panel').style.display = 'block';
      this.renderStudyStep();
    }

    exitStudy() {
      const ret = this.study ? this.study.returnSubView : 'units';
      this.study = null;
      document.getElementById('it-study-panel').style.display = 'none';
      if (ret === 'unit' && this.currentUnit) {
        document.getElementById('it-unit-panel').style.display = 'block';
        this.renderUnitVocab();
      } else {
        this.navigateSubView(ret === 'dict' || ret === 'practice' ? ret : 'units');
      }
    }

    renderStudyStep() {
      const st = this.study;
      if (!st) return;
      const body = document.getElementById('it-study-body');
      const progText = document.getElementById('it-study-progress-text');
      const progFill = document.getElementById('it-study-progress-fill');

      if (st.index >= st.queue.length) {
        if (progFill) progFill.style.width = '100%';
        if (progText) progText.textContent = `Hoàn thành ${st.queue.length}/${st.queue.length}`;
        body.innerHTML = `
          <div style="background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:2rem 1.5rem; text-align:center;">
            <div style="font-size:2.5rem; margin-bottom:0.5rem;">🎉</div>
            <div style="font-size:1.25rem; font-weight:700; color:var(--text); margin-bottom:0.4rem;">Hoàn thành phiên luyện tập IT!</div>
            <div style="font-size:0.95rem; color:var(--text-muted); margin-bottom:1.25rem;">
              ${st.mode === 'flashcard' ? `Bạn đã ôn xong <strong>${st.queue.length}</strong> thuật ngữ IT.` : `Bạn trả lời đúng <strong>${st.correct} / ${st.queue.length}</strong> câu.`}
            </div>
            <button class="btn btn-primary" onclick="app.itWorkspace.exitStudy()">Quay lại →</button>
          </div>
        `;
        return;
      }

      const item = st.queue[st.index];
      const pct = Math.round((st.index / st.queue.length) * 100);
      if (progFill) progFill.style.width = `${pct}%`;
      if (progText) progText.textContent = `${st.mode === 'flashcard' ? 'Thẻ' : 'Câu'} ${st.index + 1} / ${st.queue.length}`;

      if (st.mode === 'flashcard') {
        const wordSafe = escapeHtml(item.word).replace(/'/g, "\\'");
        body.innerHTML = `
          <div class="it-flashcard" onclick="app.itWorkspace.flipFlashcard()">
            <span class="it-badge" style="margin-bottom:0.85rem;">${escapeHtml(item.unitLabel)}</span>
            <div style="font-family:var(--font-jp); font-size:2.1rem; font-weight:700; color:var(--text); margin-bottom:0.4rem;">${escapeHtml(item.word)}</div>
            <button class="icon-btn" onclick="event.stopPropagation(); app.speakText('${wordSafe}')" style="margin-bottom:0.8rem;">🔊</button>
            ${st.flipped ? `
              <div style="font-family:var(--font-jp); font-size:1.15rem; color:var(--accent); font-weight:600; margin-bottom:0.4rem;">${escapeHtml(item.reading || '')}</div>
              <div style="font-size:1.15rem; font-weight:700; color:var(--text); margin-bottom:0.25rem;">${escapeHtml(item.vi || '')}</div>
              ${item.en ? `<div style="font-size:0.88rem; color:var(--text-muted);">${escapeHtml(item.en)}</div>` : ''}
            ` : '<div style="font-size:0.82rem; color:var(--text-subtle); margin-top:0.5rem;">Bấm vào thẻ để xem cách đọc & nghĩa IT</div>'}
          </div>
          <div style="display:flex; gap:0.75rem; justify-content:center; margin-top:1rem;">
            <button class="btn" onclick="app.itWorkspace.answerFlashcard(false)" style="flex:1; max-width:220px; justify-content:center; border-color:var(--danger); color:var(--danger); font-weight:600;">Chưa nhớ (Lặp lại)</button>
            <button class="btn btn-primary" onclick="app.itWorkspace.answerFlashcard(true)" style="flex:1; max-width:220px; justify-content:center; background:var(--success); border-color:var(--success); font-weight:600;">Đã thuộc ✓</button>
          </div>
        `;
      } else if (st.mode === 'cloze') {
        const sent = item.clozeSentence || { ja: item.word, vi: item.vi };
        const pos = sent.ja.indexOf(item.word);
        const clozeHtml = pos !== -1
          ? escapeHtml(sent.ja.slice(0, pos)) + '<span style="display:inline-block;padding:0.05rem 0.55rem;margin:0 0.15rem;border-radius:6px;background:var(--accent-soft);color:var(--accent);font-weight:700;border:1px dashed var(--accent);">＿＿＿</span>' + escapeHtml(sent.ja.slice(pos + item.word.length))
          : escapeHtml(sent.ja);

        const distractors = [];
        const used = new Set([item.word]);
        const shuffledPool = [...st.allPool].sort(() => Math.random() - 0.5);
        for (const cand of shuffledPool) {
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
        const sentSafe = escapeHtml(sent.ja).replace(/'/g, "\\'");

        body.innerHTML = `
          <div class="quiz-question-box">
            <div class="quiz-type-badge">🧩 ĐIỀN TỪ VÀO HỘI THOẠI IT · ${escapeHtml(item.unitLabel)}</div>
            <div style="font-family:var(--font-jp); font-size:1.28rem; font-weight:600; color:var(--text); line-height:1.75; margin:0.75rem 0;">
              ${clozeHtml}
            </div>
            <div style="font-size:0.84rem; color:var(--text-muted);">Chọn thuật ngữ IT phù hợp điền vào chỗ trống:</div>
          </div>
          <div style="display:flex; flex-direction:column; gap:0.55rem; margin-top:1rem;">
            ${options.map((opt, idx) => `
              <button class="it-practice-opt" id="it-qopt-${idx}" onclick="app.itWorkspace.selectQuizOption(${idx})">${idx + 1}. ${escapeHtml(opt.text)}</button>
            `).join('')}
          </div>
          <div id="it-qfb" style="display:none; margin-top:0.85rem; padding:0.9rem; border-radius:10px; background:var(--surface); border:1px solid var(--border);">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:0.5rem;">
              <span id="it-qfb-title" style="font-weight:700;"></span>
              <div style="display:flex; gap:0.4rem;">
                <button class="icon-btn" onclick="app.speakText('${sentSafe}')" style="width:1.9rem;height:1.9rem;">🔊</button>
                <button class="btn btn-sm btn-primary" onclick="app.itWorkspace.nextQuizStep()">Câu tiếp theo →</button>
              </div>
            </div>
            <div style="font-size:0.86rem; color:var(--text-muted); margin-top:0.35rem;">
              <strong style="color:var(--text);">${escapeHtml(item.word)}</strong>${item.reading ? ` (${escapeHtml(item.reading)})` : ''} — ${escapeHtml(item.vi || '')}${item.en ? ' · ' + escapeHtml(item.en) : ''}
            </div>
            <div style="font-size:0.83rem; color:var(--text); margin-top:0.3rem; font-family:var(--font-jp);">${escapeHtml(sent.ja)}</div>
            ${sent.vi ? `<div style="font-size:0.81rem; color:var(--text-muted); margin-top:0.15rem;">${escapeHtml(sent.vi)}</div>` : ''}
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
          ...distractors.map(d => ({
            text: qType === 'jp_to_vi' ? d.vi : d.word,
            correct: false
          }))
        ].sort(() => Math.random() - 0.5);

        st.currentOptions = options;
        st.answered = false;
        const wordSafe = escapeHtml(item.word).replace(/'/g, "\\'");

        body.innerHTML = `
          <div class="quiz-question-box">
            <div class="quiz-type-badge">${escapeHtml(item.unitLabel)}</div>
            <div style="font-family:var(--font-jp); font-size:${qType === 'jp_to_vi' ? '2rem' : '1.35rem'}; font-weight:700; color:${qType === 'jp_to_vi' ? 'var(--text)' : 'var(--accent)'}; margin:0.6rem 0;">
              ${escapeHtml(qType === 'jp_to_vi' ? item.word : item.vi)}
            </div>
            <div style="font-size:0.85rem; color:var(--text-muted);">
              ${qType === 'jp_to_vi' ? 'Chọn nghĩa IT tương ứng:' : 'Chọn thuật ngữ tiếng Nhật tương ứng:'}
            </div>
          </div>
          <div style="display:flex; flex-direction:column; gap:0.55rem; margin-top:1rem;">
            ${options.map((opt, idx) => `
              <button class="it-practice-opt" id="it-qopt-${idx}" onclick="app.itWorkspace.selectQuizOption(${idx})">${idx + 1}. ${escapeHtml(opt.text)}</button>
            `).join('')}
          </div>
          <div id="it-qfb" style="display:none; margin-top:0.85rem; padding:0.9rem; border-radius:10px; background:var(--surface); border:1px solid var(--border);">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:0.5rem;">
              <span id="it-qfb-title" style="font-weight:700;"></span>
              <div style="display:flex; gap:0.4rem;">
                <button class="icon-btn" onclick="app.speakText('${wordSafe}')" style="width:1.9rem;height:1.9rem;">🔊</button>
                <button class="btn btn-sm btn-primary" onclick="app.itWorkspace.nextQuizStep()">Câu tiếp theo →</button>
              </div>
            </div>
            <div style="font-size:0.85rem; color:var(--text-muted); margin-top:0.35rem;">
              <strong style="color:var(--text);">${escapeHtml(item.word)}</strong>${item.reading ? ` (${escapeHtml(item.reading)})` : ''} — ${escapeHtml(item.vi || '')}${item.en ? ' · ' + escapeHtml(item.en) : ''}
            </div>
          </div>
        `;
      }
    }

    flipFlashcard() {
      if (!this.study) return;
      this.study.flipped = !this.study.flipped;
      this.renderStudyStep();
    }

    answerFlashcard(known) {
      const st = this.study;
      if (!st) return;
      const item = st.queue[st.index];
      if (known) {
        const prog = this.getProgress();
        if (!prog.masteredVocab.includes(item.vKey)) {
          prog.masteredVocab.push(item.vKey);
          this.saveProgress(prog);
        }
      } else {
        st.queue.push(item);
      }
      st.index++;
      st.flipped = false;
      this.renderStudyStep();
    }

    selectQuizOption(idx) {
      const st = this.study;
      if (!st || st.answered) return;
      st.answered = true;
      const item = st.queue[st.index];
      const chosen = st.currentOptions[idx];
      const isCorrect = !!(chosen && chosen.correct);
      if (isCorrect) st.correct++;
      if (item && item.vKey) this._recordMistake(item.vKey, isCorrect);

      st.currentOptions.forEach((opt, i) => {
        const btn = document.getElementById(`it-qopt-${i}`);
        if (!btn) return;
        if (opt.correct) btn.classList.add('correct');
        else if (i === idx) btn.classList.add('incorrect');
        btn.disabled = true;
      });

      const fb = document.getElementById('it-qfb');
      const title = document.getElementById('it-qfb-title');
      if (title) {
        title.textContent = isCorrect ? '✓ Chính xác!' : '✗ Chưa chính xác';
        title.style.color = isCorrect ? 'var(--success)' : 'var(--danger)';
      }
      if (fb) fb.style.display = 'block';
    }

    nextQuizStep() {
      if (!this.study) return;
      this.study.index++;
      this.renderStudyStep();
    }
  }

  global.WorkspaceController = WorkspaceController;
  global.ITWorkspace = ITWorkspace;
})(window);
