/* Only this independent Previewer document. Never installs main-review shortcuts. */
(() => {
  'use strict';
  if (window.AtelierReviewKeys) return;
  let state = {token: '', actions: {}};
  const interactive = el => el instanceof Element && (
    el.matches('input, textarea, select, button, a[href], audio, video, [role="textbox"], [role="combobox"], [role="slider"], [data-atelier-keys="off"]') ||
    el.isContentEditable || el.closest('[contenteditable="true"], [data-atelier-keys="off"]')
  );
  function keydown(e) {
    // Composition, selections, interactive card controls and existing handlers
    // win. Holding Space cannot cycle through answers or award a rating.
    if (e.defaultPrevented || e.isComposing || e.repeat || e.altKey || e.metaKey ||
        (e.ctrlKey && e.key !== 'Enter') || e.composedPath().some(interactive) ||
        interactive(document.activeElement) || document.visibilityState === 'hidden') return;
    if (window.getSelection()?.toString()) return;
    const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
    if (!state.token || !Object.hasOwn(state.actions, key)) return;
    if (typeof window.pycmd !== 'function') return;
    e.preventDefault();
    window.pycmd('atelier-review-key:' + JSON.stringify({token: state.token, key}));
  }
  window.addEventListener('keydown', keydown);
  window.AtelierReviewKeys = {
    update(next) {
      state = next && typeof next.token === 'string' && next.actions && typeof next.actions === 'object'
        ? {token: next.token, actions: {...next.actions}} : {token:'', actions:{}};
    },
    dispose() { window.removeEventListener('keydown', keydown); state={token:'', actions:{}}; delete window.AtelierReviewKeys; }
  };
})();
