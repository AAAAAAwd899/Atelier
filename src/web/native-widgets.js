/* Atelier-owned widgets, in the existing Anki home webview. No Onigiri dependency. */
(() => {
  'use strict';
  const builtin = [
    ['today', 'Today’s study', 'Your recorded Anki answers and study time.', 'chart'],
    ['focus', 'Active study groups', 'Choose lectures or remove a finished focus.', 'focus'],
    ['plans', 'Upcoming exams', 'Your existing plans, dates and practice routes.', 'calendar'],
    ['work', 'Continue your work', 'Saved practice, drafts and repairs that need attention.', 'edit'],
    ['recent', 'Recently opened', 'Return to the folders and lectures you visited.', 'clock'],
    ['saved', 'Saved collections', 'Your favorite decks and folders, without copies.', 'star'],
    ['notes', 'My note', 'A small plain-text note saved only in this profile.', 'book'],
    ['onigiri', 'Onigiri rewards', 'Keep the real rewards section on your Atelier Study desk.', 'addons']
  ];
  const defaults = () => ({items: ['today', 'focus', 'plans', 'work'].map(id => ({id, size: ['today', 'work'].includes(id) ? 'wide' : 'normal', home: false}))});
  function normalize(v) {
    if (!v || !Array.isArray(v.items)) return defaults();
    const seen = new Set();
    return {items: v.items.slice(0, 24).filter(x => x && typeof x.id === 'string' &&
      (builtin.some(b => b[0] === x.id) || /^addon\.[a-z0-9][a-z0-9_.-]{1,75}$/.test(x.id)) &&
      ['normal', 'wide'].includes(x.size) && typeof x.home === 'boolean' && !seen.has(x.id) && !!seen.add(x.id))
      .map(x => ({id: x.id, size: x.size, home: x.home}))};
  }
  function create(api) {
    const {esc, icon, btn, ib, state, shadow} = api;
    let history = null, historyKey = '', historyError = '', inflightKey = '', serial = 0, loadedAt = 0;
    const fmt = n => Number(n || 0).toLocaleString();
    const catalog = () => [...builtin.filter(x => x[0] !== 'onigiri' || api.onigiri()).map(([id, title, description, glyph]) => ({id, title, description, glyph})),
      ...(window.AtelierWidgets?.catalog() || []).map(x => ({...x, glyph: 'addons'}))];
    const layout = () => normalize(state.profile.native_widgets);
    const title = id => catalog().find(x => x.id === id)?.title || 'Unavailable add-on widget';
    function scopeInfo() {
      const f = api.scope();
      return {id: f.enabled ? state.profile.selected_study === 'all' ? 'active' : state.profile.selected_study : 'all',
        title: f.enabled ? f.selected.length === 1 ? f.selected[0].name : 'All active groups' : 'All decks'};
    }
    const key = () => JSON.stringify([scopeInfo().id, state.profile.studies, api.now().toDateString()]);
    function context() {
      const s = getComputedStyle(api.host);
      return {surface: state.page === 'widgets' ? 'widgets' : 'study-desk', owner: state.config.visual_owner, theme: state.config.visual_owner === 'atelier' ? state.config.theme : 'original',
        tokens: Object.fromEntries(['bg', 'panel', 'raised', 'text', 'muted', 'accent', 'line', 'scheme'].map(k => [k, s.getPropertyValue('--' + k).trim()]))};
    }
    function shell(id, content, subtitle = '') {
      return `<div class="nw-card-heading"><span class="nw-title-mark">${icon(catalog().find(x => x.id === id)?.glyph || 'addons', 18)}<h2>${esc(title(id))}</h2></span>${subtitle ? `<span class="nw-caption">${subtitle}</span>` : ''}</div>${content}`;
    }
    function todayContent() {
      const current = historyKey === key() ? history : null;
      if (historyError && historyKey === key()) return `<div class="nw-state" role="alert"><p>${esc(historyError)}</p>${btn('nw-reload', 'Try again', 'reload', 'secondary')}</div>`;
      if (!current) return '<p class="nw-state" role="status">Reading your study history…</p>';
      const day = current.daily?.at(-1);
      if (!day) return '<p class="nw-state">No study-day information is available.</p>';
      const vals = [[day.reviews, 'Answer events'], [day.cards, 'Distinct cards'], [day.minutes, 'Recorded minutes']];
      const max = Math.max(1, ...current.daily.map(d => d.reviews));
      return `<div class="nw-today-content"><div><div class="nw-metrics">${vals.map(([n, label]) => `<div><strong>${fmt(n)}</strong><span>${label}</span></div>`).join('')}</div><p class="nw-definitions">${day.reviews ? 'Recorded in the current Anki study day.' : 'No recorded answers in this scope today.'} Repeated answers count separately. Practice mocks stay separate.</p></div><div class="nw-week" role="img" aria-label="Last seven study days: ${esc(current.daily.map(d => d.label + ': ' + d.reviews + ' answer events').join('; '))}">${current.daily.map((d, i) => `<div class="nw-day ${i === current.daily.length - 1 ? 'is-today' : ''}" title="${esc(d.label)}: ${fmt(d.reviews)} answers"><span style="--level:${Math.max(3, d.reviews / max * 100)}%"></span><small>${esc(d.label.slice(8))}</small></div>`).join('')}</div></div><div class="nw-card-footer">${btn('nw-progress', 'Study progress', 'chart', 'quiet')}${btn('nw-reload', 'Refresh', 'reload', 'quiet')}${api.preview ? '<span class="nw-caption">Sample history</span>' : ''}</div>`;
    }
    function content(id) {
      if (id === 'today') return shell(id, `<div id="nw-today-content">${todayContent()}</div>`, esc(scopeInfo().title));
      if (id === 'focus') {
        const groups = state.profile.studies.filter(s => s.active);
        return shell(id, `<div class="nw-link-list">${groups.map(s => `<div class="nw-focus-row"><button type="button" class="nw-open" data-action="select-study" data-id="${esc(s.id)}"><span class="nw-dot"></span><span><strong>${esc(s.name)}</strong><small>Choose individual lectures${s.date ? ' · ' + esc(s.date) : ''}</small></span>${icon('chevron', 14)}</button>${ib('finish-study', 'Remove ' + s.name + ' from active studies', 'close', `data-id="${esc(s.id)}"`)}</div>`).join('') || '<p class="nw-state">Pin an exam folder from the Library. Its lectures stay separate.</p>'}</div><div class="nw-card-footer">${btn('page', 'Open Library', 'folder', 'quiet', 'data-page="library"')}${btn('studies', 'Manage groups', 'sliders', 'quiet')}</div>`, 'Scheduled review');
      }
      if (id === 'plans') {
        const plans = (state.suite?.plans || []).filter(p => !p.archived).slice().sort((a,b) => (a.due || '9999').localeCompare(b.due || '9999'));
        return shell(id, `<div class="nw-link-list">${plans.slice(0, 4).map(p => `<button type="button" class="nw-open nw-plan" data-action="suite-open" data-view="overview" data-id="${esc(p.id)}"><span class="nw-date">${icon('calendar', 21)}</span><span><strong>${esc(p.name)}</strong><small>${p.due ? esc(new Date(p.due).toLocaleDateString(undefined, {month: 'short', day: 'numeric', year: 'numeric'})) : 'No exam date'}${p.filtered ? ' · Search-filtered' : ''}</small></span>${icon('arrow', 15)}</button>`).join('') || '<p class="nw-state">No saved plans yet. Create a plan when you need a date, a routine or a mock exam.</p>'}</div><div class="nw-card-footer">${btn('suite-open', plans.length > 4 ? `All ${plans.length} plans` : 'Exam Studio', 'calendar', 'quiet', 'data-view="overview"')}${btn('suite-open', 'New exam', 'plus', 'quiet', 'data-view="new"')}</div>`, 'Saved plans');
      }
      if (id === 'work') {
        const a = state.authoring || {}, draft = state.suite?.draft;
        const name = (state.suite?.plans || []).find(p => p.id === draft?.exam_id)?.name || 'Saved practice';
        return shell(id, `<div class="nw-work-grid">${draft ? btn('suite-open', `<strong>Resume saved practice</strong><small>${esc(name)}${draft.questions ? ' · ' + esc(draft.at) + ' / ' + esc(draft.questions) : ''}</small>`, 'clock', 'nw-work-link', 'data-view="practice"') : '<div class="nw-work-empty"><strong>No saved practice</strong><small>Use Save & close during a session to return later.</small></div>'}${a.available ? btn('authoring-open', `<strong>${fmt(a.drafts)} ${Number(a.drafts) === 1 ? 'draft' : 'drafts'} to review</strong><small>Saved locally · not yet in Anki</small>`, 'edit', 'nw-work-link', 'data-view="drafts"') : ''}${a.available && a.repairs ? btn('authoring-open', `<strong>${fmt(a.repairs)} ${Number(a.repairs) === 1 ? 'repair' : 'repairs'} to check</strong><small>Review before applying</small>`, 'shield', 'nw-work-link', 'data-view="improve"') : ''}</div><div class="nw-card-footer">${btn('native-tool', 'Add cards', 'plus', 'quiet', 'data-command="add"')}${a.available ? btn('authoring-open', 'Import a source', 'import', 'quiet', 'data-view="import"') : ''}</div>`);
      }
      if (id === 'recent' || id === 'saved') {
        const ids = id === 'recent' ? state.profile.recent_locations : state.profile.favorites;
        const nodes = ids.map(x => state.map.get(x)).filter(Boolean).slice(0, 5);
        return shell(id, `<div class="nw-link-list">${nodes.map(n => `<button type="button" class="nw-open" data-action="navigate" data-id="${esc(n.id)}">${icon(n.children.length ? 'folder' : 'layers', 18)}<span><strong>${esc(n.name)}</strong><small>${esc(n.path.split('::').slice(0,-1).join(' › ') || 'Library')}</small></span>${icon('chevron', 14)}</button>`).join('') || `<p class="nw-state">${id === 'recent' ? 'Open a deck or folder to see it here.' : 'Star a deck or folder to keep a shortcut here.'}</p>`}</div><div class="nw-card-footer">${btn('page', 'See all', 'arrow', 'quiet', `data-page="${id === 'recent' ? 'recent' : 'favorites'}"`)}</div>`);
      }
      if (id === 'notes') return shell(id, `<p class="nw-note-text">${esc(state.profile.native_widget_note || 'Keep a reminder or a question for your next study session.')}</p><div class="nw-card-footer">${btn('nw-note', 'Edit note', 'edit', 'quiet')}<span class="nw-caption">Local to this profile · not synced</span></div>`);
      if (id === 'onigiri' && api.onigiri()) return shell(id, '<p class="nw-state">Your real Onigiri reward room is included on the Study desk while the add-on is enabled. Its artwork, controls, and progress remain owned by Onigiri.</p><div class="nw-card-footer">' + btn('page', 'Show on Study desk', 'arrow', 'secondary', 'data-page="desk"') + btn('external-layout', 'Onigiri settings', 'sliders', 'quiet') + '</div>', 'Live on Home');
      const provider = window.AtelierWidgets?.catalog().find(x => x.id === id);
      if (provider) return shell(id, `<div data-native-provider="${esc(id)}"></div>`, 'Installed add-on');
      return shell(id, '<p class="nw-state">This optional add-on is not loaded. Your saved placement is retained; enable its add-on or remove this widget.</p>' + btn('nw-arrange', 'Arrange widgets', 'sliders', 'quiet'));
    }
    function cards(home = false) {
      const items = layout().items.filter(x => !home || x.home);
      return `<div class="nw-grid ${home ? 'nw-home-grid' : ''}">${items.map(x => `<article class="nw-card ${x.size === 'wide' ? 'nw-wide' : ''}" data-native-widget="${esc(x.id)}">${content(x.id)}</article>`).join('') || `<div class="nw-empty"><h2>Make space for what helps.</h2><p>Add study progress, exam plans, saved work, or a note. Onigiri is not needed.</p>${btn('nw-arrange', 'Add a widget', 'plus', 'primary')}</div>`}</div>`;
    }
    function header() {
      return `<header class="topbar unified-topbar nw-header"><div class="nw-header-title">${ib('mobile', 'Open navigation', 'menu', '', 'mobile-button')}<span><small>Your space, your way</small><h1 tabindex="-1">Widgets</h1></span>${api.preview ? '<span class="sample-label">SAMPLE DATA</span>' : ''}</div><div class="nw-header-controls">${btn('nw-arrange', 'Arrange widgets', 'grid', 'secondary')}${ib('appearance', 'Appearance', 'palette')}</div></header>`;
    }
    function page() {
      return `<section class="native-widgets" aria-label="Your customizable Anki widgets"><div class="nw-toolbar">${btn('quick-session', 'Quick study', 'play', 'primary')}${btn('focus-practice', 'Practice exam', 'book', 'secondary')}${btn('nw-tools', 'More tools', 'more', 'quiet', 'aria-haspopup="dialog"')}</div><div class="nw-section-heading"><p>${esc(api.now().toLocaleDateString(undefined, {weekday:'long', month:'long', day:'numeric'}))}</p><span>Built into Atelier · Onigiri not required</span></div>${cards()}<p class="nw-bottom-note">Add, remove, or reorder widgets in Arrange widgets. Removing a widget does not remove your study data.</p></section>`;
    }
    function onHome() {
      return layout().items.some(x => x.home) ? `<section class="nw-on-home" aria-label="Pinned home widgets"><div class="nw-section-heading"><h2>Your widgets</h2>${btn('nw-arrange', 'Customize', 'sliders', 'quiet')}</div>${cards(true)}</section>` : '';
    }
    function arrangement(data) {
      const chosen = data.widgetDraft.items, ids = new Set(chosen.map(x => x.id));
      return `<p class="note">Changes save only when you choose Save layout. “Show on Study desk” also shows that widget on your main home. Removing a widget does not delete its data.</p><div class="nw-arranged-list">${chosen.map((x, i) => `<div class="nw-arranged" data-widget-setting="${esc(x.id)}"><div class="nw-arranged-label"><strong>${esc(title(x.id))}</strong><small>${x.id.startsWith('addon.') ? 'Installed add-on' : 'Built-in'}</small></div><div class="nw-arranged-options"><label><input type="checkbox" data-nw-home="${esc(x.id)}" ${x.home ? 'checked' : ''}>Show on Study desk</label><label>Size<select data-nw-size="${esc(x.id)}"><option value="normal" ${x.size === 'normal' ? 'selected' : ''}>Normal</option><option value="wide" ${x.size === 'wide' ? 'selected' : ''}>Wide</option></select></label></div><div class="nw-arranged-move">${ib('nw-up', 'Move ' + title(x.id) + ' up', 'up', `data-id="${esc(x.id)}" ${i === 0 ? 'disabled' : ''}`)}${ib('nw-down', 'Move ' + title(x.id) + ' down', 'down', `data-id="${esc(x.id)}" ${i === chosen.length - 1 ? 'disabled' : ''}`)}${ib('nw-remove', 'Remove ' + title(x.id), 'close', `data-id="${esc(x.id)}"`)}</div></div>`).join('') || '<p class="nw-state">No widgets selected. Add one below, or save an empty page.</p>'}</div><h3 class="nw-add-heading">Add a widget</h3><div class="nw-catalog">${catalog().filter(x => !ids.has(x.id)).map(x => `<button type="button" class="nw-catalog-item" data-action="nw-add" data-id="${esc(x.id)}" ${chosen.length >= 24 ? 'disabled' : ''}>${icon(x.glyph, 20)}<span><strong>${esc(x.title)}</strong><small>${esc(x.description)}</small></span>${icon('plus', 16)}</button>`).join('') || '<p class="note">All available widgets are on your page.</p>'}</div><details class="nw-provider-help"><summary>Widgets from other add-ons</summary><p>Built-in widgets work without extra add-ons. Compatible installed add-ons can offer more widgets here. For Onigiri’s own games, open More tools. Website embeds are not supported.</p></details>`;
    }
    function tools() {
      const entries = [
        ['nw-progress', 'Study progress', 'chart', ''], ['pip-groups', 'Pip Study', 'focus', ''],
        ['native-tool', 'Add cards', 'plus', 'data-command="add"'], ['native-tool', 'Browse', 'browse', 'data-command="browse"'],
        ['native-tool', 'Sync', 'sync', 'data-command="sync"'], ['export-picker', 'Export cards', 'export', ''],
        ['suite-open', 'Exam Studio', 'calendar', 'data-view="overview"'], ['nw-reload', 'Refresh widgets', 'reload', ''],
        [api.onigiri() ? 'external-layout' : 'nw-original', api.onigiri() ? 'Onigiri settings' : 'Other add-ons — original page', 'addons', ''],
        ...(api.onigiri() ? [['nw-original', 'Original Onigiri page · compatibility', 'external', '']] : []),
      ];
      return `<div class="nw-tools-list">${entries.map(([a, label, glyph, extra]) => btn(a, label, glyph, 'nw-tool', extra)).join('')}</div><p class="note">These tools are also available on your Study desk. Sync updates your Anki collection, not local widget notes or layouts.</p>`;
    }
    function initDialog(type, data) {
      if (type === 'native-widgets') data.widgetDraft = normalize(state.profile.native_widgets);
    }
    function dialog(type, data) {
      if (type === 'native-widgets') return {title: 'Arrange your widgets', desc: 'One home. Only what you find useful.', wide: true, body: arrangement(data), footer: btn('nw-reset', 'Restore defaults', 'reload', 'quiet') + btn('close-dialog', 'Cancel', '', 'secondary') + btn('nw-save', 'Save layout', 'check', 'primary')};
      if (type === 'widget-tools') return {title: 'More tools', desc: 'Study, create, and manage your collection.', body: tools(), footer: btn('close-dialog', 'Done', 'check', 'primary')};
      if (type === 'widget-note') return {title: 'My note', desc: 'Plain text, saved locally in this profile. Nothing is uploaded.', body: `<label class="nw-note-label" for="nw-note-input">Your note<textarea id="nw-note-input" maxlength="4000" rows="8">${esc(state.profile.native_widget_note || '')}</textarea></label><p class="note">Choose Save note before closing. Removing the widget does not erase your note.</p>`, footer: btn('close-dialog', 'Cancel', '', 'secondary') + btn('nw-note-save', 'Save note', 'check', 'primary')};
      return null;
    }
    async function handle(action, id) {
      const data = state.dialogData;
      if (action === 'nw-arrange') api.openDialog('native-widgets');
      else if (action === 'nw-tools') api.openDialog('widget-tools');
      else if (action === 'nw-note') api.openDialog('widget-note');
      else if (action === 'nw-progress') api.openDialog('study-progress', {progressScope: scopeInfo().id, progressDays: 7});
      else if (action === 'nw-original') { api.closeDialog(); await api.original(); }
      else if (action === 'nw-reload') { api.closeDialog(); await api.reload(); loadedAt = 0; await refresh(true); }
      else if (action === 'nw-reset') { data.widgetDraft = defaults(); api.renderDialog(true); }
      else if (['nw-up', 'nw-down', 'nw-remove', 'nw-add'].includes(action)) {
        if (state.dialog !== 'native-widgets') return;
        const items = data.widgetDraft.items, i = items.findIndex(x => x.id === id);
        if (action === 'nw-remove' && i >= 0) items.splice(i, 1);
        if (action === 'nw-add' && i < 0 && items.length < 24 && catalog().some(x => x.id === id)) items.push({id, size: 'normal', home: false});
        const j = i + (action === 'nw-up' ? -1 : 1);
        if (['nw-up','nw-down'].includes(action) && i >= 0 && j >= 0 && j < items.length) [items[i], items[j]] = [items[j], items[i]];
        api.renderDialog(true);
        requestAnimationFrame(() => {
          if(state.dialog !== 'native-widgets')return;
          const escaped = CSS.escape(id || '');
          const entry = shadow.querySelector(`[data-widget-setting="${escaped}"]`);
          const target = entry?.querySelector(`[data-action="${action}"]:not(:disabled)`) || entry?.querySelector('button:not(:disabled)') || shadow.querySelector(`[data-action="nw-add"][data-id="${escaped}"]`) || shadow.querySelector('[data-action="nw-save"]');
          target?.focus({preventScroll:true});
        });
      } else if (action === 'nw-save' || action === 'nw-note-save') {
        if (state.busy) return;
        if (action === 'nw-save' && state.dialog !== 'native-widgets' || action === 'nw-note-save' && state.dialog !== 'widget-note') return;
        const payload = action === 'nw-save' ? {key: 'native_widgets', value: normalize(data.widgetDraft)} : {key: 'native_widget_note', value: shadow.getElementById('nw-note-input').value};
        api.busy(true);
        const ok = await api.updatePref(payload, false);
        api.busy(false);
        if (ok) { api.closeDialog(); api.render(); api.announce(action === 'nw-save' ? 'Widget layout saved. Your study records are unchanged.' : 'Note saved locally.'); }
      }
    }
    function change(el) {
      const id = el.dataset.nwHome || el.dataset.nwSize;
      if (state.dialog !== 'native-widgets' || !id) return false;
      const item = state.dialogData.widgetDraft.items.find(x => x.id === id);
      if (item) { if (el.dataset.nwHome) item.home = el.checked; else item.size = el.value; }
      return true;
    }
    async function refresh(force = false) {
      if (!shadow.querySelector('[data-native-widget="today"]')) return;
      const wanted = key();
      if (!force && (inflightKey === wanted || historyKey === wanted && history && Date.now() - loadedAt < 30000)) return;
      const revision = ++serial; inflightKey = wanted; historyKey = wanted; historyError = ''; history = null;
      paintToday();
      try {
        const result = await api.progress(scopeInfo().id);
        if (revision !== serial || wanted !== key()) return;
        history = result; loadedAt = Date.now();
      } catch (e) { if (revision === serial) historyError = e.message || 'Study activity could not load. Your records are unchanged.'; }
      finally { if (revision === serial) { inflightKey = ''; paintToday(); } }
    }
    function updateWork() {
      const card = shadow.querySelector('[data-native-widget="work"]');
      if(card)card.innerHTML=content('work');
    }
    function paintToday() { const node = shadow.getElementById('nw-today-content'); if (node) node.innerHTML = todayContent(); }
    function mount() {
      if (state.config.mode === 'native') return;
      // Registering a late provider must not destroy another widget's input.
      for(const card of shadow.querySelectorAll('[data-native-widget^="addon."]')) {
        const id=card.dataset.nativeWidget, available=window.AtelierWidgets?.catalog().some(x=>x.id===id);
        if(available !== !!card.querySelector('[data-native-provider]'))card.innerHTML=content(id);
      }
      window.AtelierWidgets?.reconcile(frameRoot(), context()); refresh();
    }
    function frameRoot() { return shadow.querySelector('.frame'); }
    function beforeRender() { window.AtelierWidgets?.disposeAll(); }
    function theme() { window.AtelierWidgets?.theme(context()); }
    window.addEventListener('atelier:widgets-changed', () => {
      if (!state.loaded) return;
      // Never replace a provider or note while an unfinished owned dialog is open.
      if (!state.dialog && (state.page === 'widgets' || layout().items.some(x => x.home))) mount();
    });
    return {header, page, onHome, initDialog, dialog, handle, change, mount, beforeRender, theme, refresh, updateWork};
  }
  window.AtelierNativeWidgets = Object.freeze({create, normalize, defaults});
})();
