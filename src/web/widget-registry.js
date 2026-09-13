/* Public, opt-in contract for trusted installed add-ons. No URL/HTML imports.
   Registration does not mount code until the user adds the widget. */
(() => {
  'use strict';
  if (window.AtelierWidgets) return;
  const records = new Map(), mounted = new Map();
  const emit = () => window.dispatchEvent(new CustomEvent('atelier:widgets-changed'));
  const safeId = id => typeof id === 'string' && /^addon\.[a-z0-9][a-z0-9_.-]{1,75}$/.test(id);
  const label = (v, n) => typeof v === 'string' ? v.trim().slice(0, n) : '';
  function dispose(id) {
    const m = mounted.get(id); if (!m) return;
    mounted.delete(id);
    try { m.dispose?.(); } catch (_) { /* Failure is confined to this widget. */ }
  }
  function failure(target) {
    target.replaceChildren();
    const p = document.createElement('p'); p.textContent = 'This add-on widget could not open. Reload widgets to retry, or remove it in Arrange widgets.';
    p.setAttribute('role', 'status'); target.append(p);
  }
  const api = {
    apiVersion: 1,
    register(spec) {
      if (!spec || !safeId(spec.id) || !label(spec.title, 80) || typeof spec.mount !== 'function')
        throw new TypeError('Use addon.<id>, a title, and a mount function.');
      if (records.has(spec.id)) throw new Error('A widget with that id is already registered.');
      if (records.size >= 32) throw new Error('The installed-widget registration limit is 32.');
      const record = Object.freeze({id: spec.id, title: label(spec.title, 80), description: label(spec.description, 180),
        mount: spec.mount, theme: typeof spec.theme === 'function' ? spec.theme : null});
      records.set(spec.id, record); emit();
      return () => { if (records.get(spec.id) === record) { dispose(spec.id); records.delete(spec.id); emit(); } };
    },
    catalog: () => [...records.values()].map(({id, title, description}) => ({id, title, description})),
    reconcile(root, context) {
      for (const [id, m] of mounted) if (!m.target.isConnected || !root.contains(m.host)) dispose(id);
      for (const host of root.querySelectorAll('[data-native-provider]')) {
        const id = host.dataset.nativeProvider, spec = records.get(id);
        if (!spec || mounted.has(id)) continue;
        const surface = host.shadowRoot || host.attachShadow({mode: 'open'});
        const style = document.createElement('style');
        style.textContent = ':host{display:block;font:14px/1.6 system-ui;color:inherit;min-width:0;overflow:auto;max-height:600px}*{box-sizing:border-box}button,input,textarea,select{font:inherit}button:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:3px}';
        const target = document.createElement('div'); target.className = 'provider-content'; surface.replaceChildren(style, target);
        const ctx = Object.freeze({...context, tokens: Object.freeze({...context.tokens})});
        const entry = {host, target, dispose: null, spec}; mounted.set(id, entry);
        try {
          const cleanup = spec.mount(target, ctx);
          if (cleanup && typeof cleanup.then === 'function') throw new TypeError('mount returns a cleanup function, not a Promise. Start async work inside mount.');
          if (typeof cleanup === 'function') entry.dispose = cleanup;
        } catch (_) { failure(target); }
      }
    },
    theme(context) {
      const ctx = Object.freeze({...context, tokens: Object.freeze({...context.tokens})});
      for (const m of mounted.values()) {
        try { m.spec.theme?.(m.target, ctx); } catch (_) { /* Preserve an already mounted widget. */ }
      }
    },
    disposeAll() { for (const id of [...mounted.keys()]) dispose(id); },
    diagnostics: () => ({registered: records.size, mounted: mounted.size, apiVersion: 1})
  };
  window.AtelierWidgets = Object.freeze(api);
  window.addEventListener('pagehide', api.disposeAll, {once: true});
  window.dispatchEvent(new CustomEvent('atelier:widgets-ready'));
})();
