/* Scoped countdown + additive Atelier adapter. No reviewer or collection access. */
(() => {
  'use strict';
  // Some home replacements re-run scripts without navigating. One listener set,
  // one timer and one owned slot must survive repeated mounts.
  if (window.ExamSproutCountdown?.revision === '0.9.4' && !window.ExamSproutCountdown.disposed) {
    window.ExamSproutCountdown.mount();
    return;
  }
  window.ExamSproutCountdown?.dispose?.();
  const SLOT = 'exam-sprout-countdowns';
  let timer = null, active = null, anchor = null, ownedSlot = null, disposed = false;
  const handlers = new WeakMap();
  function rgb(value) {
    const hex = value.trim().match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
    if (hex) {
      const s = hex[1].length === 3 ? [...hex[1]].map(c=>c+c).join('') : hex[1];
      return [0,2,4].map(i=>parseInt(s.slice(i,i+2),16));
    }
    const parts = value.match(/[\d.]+/g)?.map(Number);
    return parts && parts.length >= 3 && (parts.length < 4 || parts[3] > .9) ? parts : null;
  }
  const dark = c => c[0]*.2126+c[1]*.7152+c[2]*.0722 < 135;
  function hostIsDark(root) {
    const app = root.closest('#es-app');
    if (app) return app.dataset.dark === 'true' || app.dataset.theme === 'midnight';
    if (root.dataset.host === 'atelier') {
      const c = rgb(root.style.getPropertyValue('--es-host-bg'));
      if (c) return dark(c);
    }
    for (let el = root.parentElement; el; el = el.parentElement) {
      const c = rgb(getComputedStyle(el).backgroundColor);
      if (c) return dark(c);
    }
    return document.documentElement.classList.contains('night-mode') || document.body.classList.contains('nightMode') || window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  function clearHost(root) {
    delete root.dataset.host;
    delete root.dataset.motion;
    for (const key of ['bg','text','accent','panel','muted','line']) root.style.removeProperty(`--es-host-${key}`);
  }
  function restore(root) {
    ownedSlot?.remove(); ownedSlot = null;
    root.removeAttribute('slot');
    clearHost(root);
    if (anchor?.isConnected) anchor.after(root);
    // If another extension destroyed the original section, leave our component
    // in the document, not as an invisible, unslotted child of a shadow host.
    else if (root.parentElement?.id === 'atelier-root') root.parentElement.after(root);
  }
  function syncHost(root) {
    if (root.dataset.preview === 'true' || root.closest('#es-app')) return;
    const host = document.getElementById('atelier-root');
    const main = host?.shadowRoot?.querySelector('.main-inner');
    const enabled = document.body.classList.contains('atelier-home');
    if (!host || !main || !enabled) { restore(root); return; }
    // Move only our light-DOM node. It retains our scoped CSS and bridge.
    // The owned slot sits after Atelier's header and before its hero, and is
    // re-created on its documented theme-change notification after rerenders.
    let slot = main.querySelector(`slot[data-exam-sprout-slot="${SLOT}"]`);
    if (!slot) {
      ownedSlot?.remove();
      slot = document.createElement('slot');
      slot.name = SLOT;
      slot.dataset.examSproutSlot = SLOT;
      slot.style.cssText = 'display:block;min-width:0;';
      const header = main.querySelector('.topline');
      if (header) header.after(slot); else main.prepend(slot);
      slot.style.cssText = 'display:block;min-width:0;margin:0 0 16px;';
    }
    ownedSlot = slot;
    root.slot = SLOT;
    if (root.parentElement !== host) host.append(root);
    root.dataset.host = 'atelier';
    root.dataset.motion = host.dataset.motion || 'on';
    const style = getComputedStyle(host);
    for (const key of ['bg','text','accent','panel','muted','line']) {
      const value = style.getPropertyValue(`--${key}`).trim();
      if (value && CSS.supports('color', value)) root.style.setProperty(`--es-host-${key}`, value);
      else root.style.removeProperty(`--es-host-${key}`);
    }
  }
  function update(root) {
    root.dataset.dark = String(hostIsDark(root));
    root.querySelectorAll('[data-deadline]').forEach(el => {
      const raw = new Date(el.dataset.deadline).getTime();
      if (!Number.isFinite(raw)) { el.textContent = 'Check date'; return; }
      const m = Math.max(0, Math.floor((raw - Date.now()) / 60000));
      const a = m >= 1440 ? [Math.floor(m/1440),'d',Math.floor(m%1440/60),'h'] : m >= 60 ? [Math.floor(m/60),'h',m%60,'m'] : [m,'m',null,''];
      el.innerHTML = m ? `${a[0]}<small>${a[1]}</small>${a[2]===null?'':`<em>${a[2]}<small>${a[3]}</small></em>`}` : 'Exam time';
      const unit = (n,u) => `${n} ${u}${n===1?'':'s'}`;
      const spoken = m>=1440 ? `${unit(Math.floor(m/1440),'day')}, ${unit(Math.floor(m%1440/60),'hour')}` : m>=60 ? `${unit(Math.floor(m/60),'hour')}, ${unit(m%60,'minute')}` : unit(m,'minute');
      el.setAttribute('aria-label',m ? spoken+' remaining' : 'Exam time');
    });
  }
  function refresh() {
    if (!disposed && active?.isConnected) { syncHost(active); update(active); }
    else if (!disposed) mount();
  }
  function mount() {
    if (disposed) return;
    const root = document.getElementById('es-countdowns');
    if (timer !== null) { clearInterval(timer); timer = null; }
    if (active !== root) {
      if (active) { const fn=handlers.get(active); if(fn)active.removeEventListener('click',fn); handlers.delete(active); }
      ownedSlot?.remove(); ownedSlot=null;
      anchor?.remove(); anchor=null;
    }
    active = root;
    if (!root) return;
    if (!anchor && root.dataset.preview !== 'true' && !root.closest('#es-app')) {
      anchor = document.createComment('Exam Sprout: original home position');
      root.before(anchor);
    }
    if (!handlers.has(root)) {
      const click = e => {
        if (root.dataset.preview === 'true') return;
        const chip=e.target.closest?.('[data-exam-id]');
        if (chip && root.contains(chip) && typeof window.pycmd === 'function') {
          e.preventDefault(); e.stopPropagation();
          window.pycmd('exam-sprout:open:'+chip.dataset.examId);
        }
      };
      handlers.set(root,click);
      root.addEventListener('click',click);
    }
    syncHost(root); update(root);
    timer=setInterval(() => {
      if (!root.isConnected) { mount(); return; }
      if (!document.hidden) update(root);
    },30000);
  }
  function visible() { if (!document.hidden) refresh(); }
  function dispose() {
    disposed=true;
    if (timer!==null) clearInterval(timer);
    timer=null;
    window.removeEventListener('atelier:theme-change',refresh);
    window.removeEventListener('pagehide',dispose);
    document.removeEventListener('visibilitychange',visible);
    document.removeEventListener('DOMContentLoaded',mount);
    if(active) {
      const fn=handlers.get(active); if(fn)active.removeEventListener('click',fn);
      restore(active);
    }
    anchor?.remove(); anchor=null; active=null;
  }
  window.ExamSproutCountdown={revision:'0.9.4',mount,dispose,get disposed(){return disposed;}};
  window.addEventListener('atelier:theme-change',refresh);
  document.addEventListener('visibilitychange',visible);
  window.addEventListener('pagehide',dispose,{once:true});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
})();
