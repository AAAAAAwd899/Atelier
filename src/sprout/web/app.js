/* Exam Sprout: shared production UI. No external dependencies or network calls. */
(() => {
  'use strict';
  const E = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const assetBase = window.AtelierSuiteAssets || '/_addons/exam_sprout/web';
  const sprout = `<img class="es-pip-logo" src="${E(assetBase)}/pip/stage1.png" alt="Pip" draggable="false">`;
  const cardsIcon = '<svg viewBox="0 0 36 40" fill="none" class="es-callout-icon" aria-hidden="true"><rect x="9" y="4" width="23" height="29" rx="4" stroke="currentColor" stroke-width="1.3"/><rect x="3" y="10" width="23" height="27" rx="4" fill="var(--es-soft)" stroke="currentColor" stroke-width="1.3"/><path d="M9 20h11M9 25h8M9 30h5" stroke="currentColor" stroke-linecap="round"/></svg>';
  const lock = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="6" y="10" width="12" height="10" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M9 10V6a3 3 0 0 1 6 0v4" stroke="currentColor" stroke-width="1.5"/></svg>';
  const icon = name => `<svg data-icon="${E(name)}" viewBox="0 0 24 24" fill="none" aria-hidden="true"><g stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${({browse:"<rect x=\"3\" y=\"3\" width=\"14\" height=\"17\" rx=\"2\"/><path d=\"M7 7h6M7 11h4\"/><circle cx=\"16\" cy=\"16\" r=\"4\"/><path d=\"m19 19 3 3\"/>",sync:"<path d=\"M7 3 3 7l4 4M3 7h13a4 4 0 0 1 4 4M17 21l4-4-4-4M21 17H8a4 4 0 0 1-4-4\"/>",calendar:'<rect x="4" y="5" width="16" height="16" rx="3"/><path d="M8 3v4m8-4v4M4 11h16m-11 5h2m3 0h1"/>',clock:'<circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/>',layers:'<rect x="7" y="3" width="13" height="16" rx="3"/><path d="M16 22H6a3 3 0 0 1-3-3V8"/>',plan:'<rect x="4" y="4" width="16" height="17" rx="3"/><path d="m8 10 1.5 1.5L12 9m2 1h2m-8 6h8"/>',plus:'<path d="M12 4v16M4 12h16"/>',settings:'<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="2.5" fill="var(--es-surface)"/><circle cx="15" cy="17" r="2.5" fill="var(--es-surface)"/>',arrow:'<path d="M4 12h15m-5-5 5 5-5 5"/>',check:'<path d="m5 12 4 4L19 6"/>',spark:'<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"/>'})[name]||''}</g></svg>`;
  function acceptState(result) { S.data.state=result.state; if(typeof result.countdown_html==='string') S.data.countdown_html=result.countdown_html; }
  let root, sequence = 0, toastTimer;
  const pending = new Map();
  const S = {data:null, selected:null, view:'overview', plan:null, planToken:0, draft:null, step:1, deckSearch:'', suggestions:[], past:false, allRows:false, practice:{size:50,minutes:0,kind:'exam',weighting:'emphasis',weights:{},strategy:'representative',cold_only:false,one_per_note:true,ensure_coverage:true,include_new:true,include_suspended:false,include_buried:false}};
  let modalCallback = null, deferredRender = false, railOpen = false;
  let lastRenderLocation = '', focusNextStep = false, activeActionElement = null;
  const summaryExpanded = {setup:null,practice:null};
  const exam = () => S.data?.state.exams.find(e => e.id === S.selected);
  const localDate = iso => new Date(iso).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'});
  const examDate = iso => new Date(iso).toLocaleString(undefined,{weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});
  const daysLeft = e => Math.max(0, Math.ceil((new Date(e.due).getTime()-Date.now())/86400000));
  const isPast = e => new Date(e.due).getTime() <= Date.now();
  const selectedAttr = (x,y) => x === y ? ' selected' : '';
  const checked = x => x ? ' checked' : '';
  const activeClass = x => x ? ' selected' : '';
  function request(action, payload={}) {
    return new Promise((resolve,reject) => {
      const id = String(++sequence);
      const timer = setTimeout(() => {pending.delete(id); reject(new Error('Anki has not responded yet. Close and reopen this window before retrying.'));}, 120000);
      pending.set(id,{resolve,reject,timer});
      const msg = 'exam-sprout:' + JSON.stringify({id,action,payload});
      let tries = 0;
      const send = () => {
        if (typeof window.pycmd === 'function') window.pycmd(msg);
        else if (++tries < 100) setTimeout(send,50);
        else { clearTimeout(timer); pending.delete(id); reject(new Error('This window is not connected to Anki. Open Exam Studio from Atelier and try again.')); }
      };
      send();
    });
  }
  window.ExamSprout = {
    suiteReady(){return !!S.data;},
    suiteRequest(action,payload={}){if(!S.data?.suite||!["suite_theme","suite_focus","suite_native"].includes(action))return Promise.reject(new Error("Unavailable suite action"));return request(action,payload);},
    suiteWorld(theme){if(!S.data)return;S.data.state.settings.theme=String(theme||'');updateCompanionWorld(theme);},
    receive(message) {
      const p = pending.get(message.id);
      if (!p) return;
      clearTimeout(p.timer); pending.delete(message.id);
      if (message.error) p.reject(new Error(message.error)); else p.resolve(message.data);
    },
    event(name, payload) {
      if (name === 'suite-navigate') {
        if (!S.data) return;
        const go = () => {
          if (payload.id && S.data.state.exams.some(e=>e.id===payload.id)) {S.selected=payload.id;S.plan=null;S.practice.weights={};fetchPlan();}
          if (payload.view==='new') {newExam(); if(payload.setup && S.draft){S.draft.name=String(payload.setup.name||'').slice(0,120);if(payload.setup.query)S.draft.query=String(payload.setup.query);S.draft.scopes=(payload.setup.deck_ids||[]).map(id=>S.data.decks.find(d=>String(d.id)===String(id))).filter(Boolean).map(d=>({deck_id:d.id,name:d.name,weight:1,confidence:3}));render();} return;}
          navigate(['overview','practice','settings'].includes(payload.view)?payload.view:'overview');
          if(payload.view==='pip')action({dataset:{action:'pip-study'}}).catch(e=>toast(e.message));
        };
        if(S.draft){confirmModal('Leave unsaved changes?','Your saved exams and results stay unchanged.',()=>{S.draft=null;markDirty(false);go();});}else go();
      }
      if (name === 'error') toast(payload.message);
      if (name === 'select' && !S.draft) selectExam(payload.id);
      if (name === 'draft_saved') {S.data.draft=payload.draft;S.view='practice';render();}
      if (name === 'result') {
        S.data.draft=null;
        S.data.state = payload.state; S.view = 'overview'; S.draft = null;
        S.plan = null; fetchPlan(); render(); resultModal(payload.result);
      }
    }
  };
  function toast(message) {
    if (!root) return;
    root.querySelector('.es-toast')?.remove();
    const node = document.createElement('div'); node.className='es-toast'; node.setAttribute('role','alert'); node.textContent=message;
    (root.querySelector('#es-modal[open] .suite-modal-alerts')||root).appendChild(node); clearTimeout(toastTimer); toastTimer=setTimeout(() => node.remove(),8000);
  }
  function markDirty(value=true) { request('dirty',{value}).catch(() => {}); }
  function applyTheme() {
    root.dataset.theme = S.data?.state.settings.theme || 'inherit';
    root.dataset.dark = String(Boolean(S.data?.night));
  }
  function pipWorld(theme) {
    const id = String(theme || '').toLowerCase();
    if (['rose','bloom','peach','castle','lavender','sky'].includes(id)) return {kind:'cutesy', label:'Pip · soft cat companion'};
    if (['forest','matcha','cabin','sage'].includes(id)) return {kind:'green', label:'Pip · grove companion'};
    if (['tidal','glacier','sunset-beach'].includes(id)) return {kind:'water', label:'Pip · tide companion'};
    if (['midnight','obsidian','celestial','mythic'].includes(id)) return {kind:'orbit', label:'Pip · night companion'};
    if (['ember','underworld'].includes(id)) return {kind:'ember', label:'Pip · ember companion'};
    return {kind:'linen', label:'Pip · paper companion'};
  }
  function pipStages(kind) {
    return ({
      cutesy:['Curious','Cozy','Confident','Radiant'],
      green:['Sprout','Rooted','Flourishing','Canopy'],
      water:['Ripple','Current','Tide','Horizon'],
      orbit:['Spark','Orbit','Constellation','Zenith'],
      ember:['Coal','Glow','Flame','Hearth'],
      linen:['Fold','Page','Chapter','Archive']
    })[kind] || ['Start','Steady','Growing','Flourishing'];
  }
  function pipActions(kind) {
    return ({
      cutesy:['Pet','Treat'], green:['Pet','Water'], water:['Wave','Splash'],
      orbit:['Greet','Stargaze'], ember:['Pet','Warm'], linen:['Greet','Read']
    })[kind] || ['Greet','Encourage'];
  }
  function pipStageLabel(kind, stage) {
    const stages=pipStages(kind),index=Math.max(0,Math.min(stages.length-1,Number(stage||1)-1));
    return `${stages[index]} stage`;
  }
  function updateCompanionWorld(theme) {
    const card=root?.querySelector('.pip-card');if(!card)return;
    const world=pipWorld(theme),base=card.dataset.pipBase,portrait=`${base}/companion-${world.kind}-1.0.3.png`;
    [...card.classList].filter(name=>name.startsWith('pip-world-')).forEach(name=>card.classList.remove(name));
    card.classList.add(`pip-world-${world.kind}`);card.dataset.pipWorld=world.kind;card.dataset.pipWorldLabel=world.label;card.dataset.pipPortrait=portrait;
    const image=card.querySelector('.pip-image');if(image){image.src=portrait;image.alt=world.label;}
    card.querySelector('.pip-world-label')?.replaceChildren(world.label);
    card.querySelector('.pip-touch')?.setAttribute('aria-label',`Greet ${world.label}`);
    const actions=pipActions(world.kind),buttons=card.querySelectorAll('.pip-actions button');if(buttons[0])buttons[0].textContent=actions[0];if(buttons[1])buttons[1].textContent=actions[1];
    const stages=pipStages(world.kind);card.closest('.es-companion-panel')?.querySelectorAll('.es-growth-steps span').forEach((node,index)=>{node.textContent=stages[index]||'';});
    const progressLabel=card.closest('.es-companion-panel')?.querySelector('.es-pip-stage-label');if(progressLabel)progressLabel.textContent=pipStageLabel(world.kind,card.dataset.pipStage);
    card.querySelector('.pip-speech')?.replaceChildren('Quiet company. No distractions.');
    window.PipCompanion?.mount?.();
  }
  function pipWorldMark(kind) {
    const marks = {
      cutesy:'<svg viewBox="0 0 180 180" aria-hidden="true"><defs><linearGradient id="pip-cat" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fff7fb"/><stop offset="1" stop-color="#f2bdd2"/></linearGradient></defs><circle cx="90" cy="90" r="72" fill="url(#pip-cat)" opacity=".46"/><path d="M47 73 55 37l29 22c4-1 8-2 12-2s8 1 12 2l29-22 8 36c4 8 6 17 6 27 0 32-27 48-61 48S29 132 29 100c0-10 2-19 6-27Z" fill="none" stroke="#fff9fc" stroke-width="3" opacity=".88"/><circle cx="67" cy="101" r="3" fill="#fff9fc"/><circle cx="113" cy="101" r="3" fill="#fff9fc"/><path d="M82 119q8 7 16 0" fill="none" stroke="#fff9fc" stroke-width="3" stroke-linecap="round"/></svg>',
      green:'<svg viewBox="0 0 180 180" aria-hidden="true"><circle cx="90" cy="90" r="72" fill="#bde29c" opacity=".24"/><path d="M90 143V45" stroke="#dff4c4" stroke-width="3" stroke-linecap="round"/><path d="M88 92C54 89 36 69 39 43c27 0 48 17 49 45Z" fill="#dff4c4" opacity=".52" stroke="#b6db96" stroke-width="2"/><path d="M92 75c4-30 25-47 52-46 1 28-17 48-49 53Z" fill="#dff4c4" opacity=".52" stroke="#b6db96" stroke-width="2"/><path d="M90 113c-22 0-37 11-44 29 25 8 43-2 47-24Z" fill="#dff4c4" opacity=".42" stroke="#b6db96" stroke-width="2"/></svg>',
      water:'<svg viewBox="0 0 180 180" aria-hidden="true"><circle cx="90" cy="90" r="72" fill="#9ce2e4" opacity=".2"/><path d="M25 94c19-21 38-21 57 0s38 21 57 0 38-21 57 0" fill="none" stroke="#d5f6f0" stroke-width="4" stroke-linecap="round" opacity=".9"/><path d="M32 119c16-15 32-15 48 0s32 15 48 0 32-15 48 0" fill="none" stroke="#b4ece8" stroke-width="2" stroke-linecap="round" opacity=".75"/></svg>',
      orbit:'<svg viewBox="0 0 180 180" aria-hidden="true"><circle cx="90" cy="90" r="72" fill="#aeb6f3" opacity=".16"/><ellipse cx="90" cy="90" rx="68" ry="29" fill="none" stroke="#d8dcff" stroke-width="2" opacity=".9" transform="rotate(-18 90 90)"/><ellipse cx="90" cy="90" rx="47" ry="68" fill="none" stroke="#b8c0ff" stroke-width="1.5" opacity=".65" transform="rotate(26 90 90)"/><circle cx="133" cy="51" r="4" fill="#f5e8a8"/><path d="m133 41 2.5 7.5L143 51l-7.5 2.5L133 61l-2.5-7.5L123 51l7.5-2.5Z" fill="#f5e8a8" opacity=".85"/></svg>',
      ember:'<svg viewBox="0 0 180 180" aria-hidden="true"><circle cx="90" cy="90" r="72" fill="#ef9a5e" opacity=".18"/><path d="M90 146c-29 0-48-17-48-42 0-20 13-30 27-45 0 17 8 24 15 29-2-21 9-37 21-50 1 18 25 32 31 55 8 29-10 53-46 53Z" fill="none" stroke="#ffd29a" stroke-width="3" opacity=".9"/></svg>',
      linen:'<svg viewBox="0 0 180 180" aria-hidden="true"><circle cx="90" cy="90" r="72" fill="#f1dcae" opacity=".18"/><circle cx="90" cy="90" r="61" fill="none" stroke="#f6e6bc" stroke-width="2" opacity=".8"/><path d="M43 72h94M43 90h94M43 108h94M72 43v94M90 43v94M108 43v94" stroke="#f6e6bc" stroke-width="1" opacity=".38"/></svg>'
    };
    return marks[kind] || marks.linen;
  }
  function chooseInitial() {
    const all = S.data.state.exams;
    S.selected = all.some(e=>e.id===S.data.initial_exam) ? S.data.initial_exam : [...all].filter(e=>!e.archived&&!isPast(e)).sort((a,b)=>a.due.localeCompare(b.due))[0]?.id || all.find(e=>!e.archived)?.id || null;
  }
  async function fetchPlan() {
    const e = exam(); if (!e) return;
    const token = ++S.planToken;
    try {
      const result = await request('plan',{id:e.id});
      if (token !== S.planToken || S.selected !== e.id) return;
      S.plan = result; if('draft' in result)S.data.draft=result.draft; if(S.view==='overview') renderAfterModal();
    } catch(error) { if(token===S.planToken) {S.plan={error:error.message}; if(S.view==='overview')renderAfterModal();} }
  }
  function renderAfterModal() {
    if (root.querySelector('#es-modal')?.open) deferredRender = true;
    else render();
  }
  function selectExam(id) {
    if (S.draft) {confirmModal('Leave this exam?','Unsaved changes will be discarded.',()=>{S.draft=null;markDirty(false);selectExam(id);});return;}
    railOpen=false; S.selected=id; S.plan=null; S.view='overview'; S.practice.weights={}; render(); fetchPlan();
  }
  function navigate(view) {
    if (S.draft) {confirmModal('Discard unsaved changes?','Your saved exams will not be changed.',()=>{S.draft=null;markDirty(false);navigate(view);}); return;}
    railOpen=false; S.view=view; render();
  }
  function render() {
    if (!S.data) return;
    applyTheme();
    const previousSummary=root.querySelector('.suite-setup-summary[data-summary-mode]');
    if(previousSummary)summaryExpanded[previousSummary.dataset.summaryMode]=previousSummary.open;
    root.dataset.suite=String(Boolean(S.data.suite));
    root.dataset.page=S.draft?'setup':S.view;
    root.dataset.railOpen=String(railOpen);
    const all = [...S.data.state.exams].sort((a,b)=>a.due.localeCompare(b.due));
    const visible = all.filter(e => S.past || (!e.archived&&!isPast(e)) || e.id===S.selected);
    const historyCount = all.filter(e=>e.archived||isPast(e)).length;
    const retainedPip=root.querySelector('.pip-card');
    const location=[S.view,S.selected||'',S.draft?'setup-'+S.step:''].join(':');
    const scrollHost=root.querySelector('.suite-setup-scroll')||root.querySelector('.es-main');
    const retainedScroll=location===lastRenderLocation?(scrollHost?.scrollTop||0):0;
    const focused=activeActionElement||document.activeElement;
    let retainedFocus='';
    if(location===lastRenderLocation&&root.contains(focused)&&focused?.matches('button[data-action],select[data-practice],select[data-setting]')){
      retainedFocus=focused.tagName.toLowerCase();
      for(const key of ['action','practice','setting','value','day','size','id','kind'])if(focused.dataset[key]!==undefined)retainedFocus+='[data-'+key+'="'+CSS.escape(focused.dataset[key])+'"]';
    }
    lastRenderLocation=location;
    root.innerHTML = `
      <header class="es-app-header"><div class="es-brand"><span class="es-brand-mark">${sprout}</span><span class="suite-brand-copy"><strong>${S.data.suite?'Atelier':'Exam Sprout'}</strong><span class="es-header-note">${S.data.suite?'Exam Studio':'A calmer way to prepare.'}</span></span></div>
      ${S.data.suite?`<div class="suite-tool-links" aria-label="Anki tools"><button data-action="suite-native" data-command="add">${icon('plus')} Add cards</button><button data-action="suite-native" data-command="browse">${icon('browse')} Browse</button><button data-action="suite-native" data-command="sync">${icon('sync')} Sync</button></div>`:''}<nav class="es-top-nav" aria-label="Exam Studio pages">${['overview','practice','settings'].map(v=>`<button data-action="nav" data-view="${v}" aria-current="${S.view===v?'page':'false'}">${icon(v==='overview'?'plan':v==='practice'?'layers':'settings')}<span>${v==='overview'?'My plan':v==='practice'?'Practice':'Settings'}</span></button>`).join('')}<button class="suite-home-link" data-action="back-to-anki" title="Return to Anki study desk">${icon('arrow')}<span>${S.data.suite?'Study desk':'Back to Anki'}</span></button></nav></header>
      <div class="es-layout">${S.data.suite?`<button class="suite-exams-toggle" data-action="toggle-exams" aria-controls="suite-exams-rail" aria-expanded="${railOpen}">${icon('calendar')}<span>Your exams</span><span>${all.filter(e=>!e.archived&&!isPast(e)).length}</span><b aria-hidden="true">${railOpen?'−':'+'}</b></button>`:''}<aside id="suite-exams-rail" class="es-sidebar" aria-label="Your exams"><div class="es-sidebar-label"><span class="es-label">Your exams</span><span class="es-muted">${all.filter(e=>!e.archived&&!isPast(e)).length}</span></div>
      <div class="es-exam-list">${visible.map(e=>`<button class="es-exam-link" data-action="select-exam" data-id="${E(e.id)}" aria-current="${e.id===S.selected}"><span class="es-exam-stamp" aria-hidden="true">${new Date(e.due).getDate()}<small>${new Date(e.due).toLocaleDateString(undefined,{month:'short'})}</small></span><span class="es-exam-link-copy"><strong>${E(e.name)}</strong><span>${e.archived?'Archived':isPast(e)?'Exam time passed':`${daysLeft(e)} ${daysLeft(e)===1?'day':'days'} to go`} · ${E(localDate(e.due).replace(/, \d{4}$/, ''))}</span></span></button>`).join('')}</div>
      <button class="es-sidebar-add" data-action="new" ${S.data.read_only?'disabled':''}>+ New exam</button>
      ${historyCount?`<button class="es-quiet es-small" data-action="toggle-past">${S.past?'Hide':'Show'} past & archived (${historyCount})</button>`:''}
      <div class="es-sidebar-footer"><details class="suite-companion-note"><summary><span class="es-sidebar-sprout">${sprout}</span><span>A little today.<small>A calmer tomorrow.</small></span></summary><p>A plan is a starting point, not a score. Work through one manageable session at a time.</p></details><p class="suite-privacy-label">${lock} Local & private</p><span>Practice is separate. Normal study uses your schedule.</span></div></aside>
      <section class="es-main" aria-label="Exam details">${S.data.warning?notice(S.data.warning):''}${S.draft?renderForm():S.view==='settings'?renderSettings():S.view==='practice'?renderPractice():renderOverview()}</section></div>
      <dialog id="es-modal" class="es-modal" aria-label="Exam Sprout dialog"></dialog>`;
    const newPip=root.querySelector('.pip-card');
    if(retainedPip&&newPip&&retainedPip.dataset.pipKey===newPip.dataset.pipKey&&retainedPip.dataset.pipStage===newPip.dataset.pipStage){retainedPip.dataset.pipAnimate=newPip.dataset.pipAnimate;newPip.replaceWith(retainedPip);}
    const dialog = root.querySelector('#es-modal');
    dialog.addEventListener('cancel',()=>{modalCallback=null;});
    dialog.addEventListener('close',()=>{
      // A queued close event from a replaced or reopened dialog must not tear
      // down a newer result dialog while its plan query is completing.
      if(!dialog.isConnected || root.querySelector('#es-modal')!==dialog || dialog.open)return;
      if(deferredRender){deferredRender=false;render();}
    });
    if (S.draft?.step===2) renderDeckList();
    updateSetupSummary(); updatePracticeSummary();
    const nextScroll=root.querySelector('.suite-setup-scroll')||root.querySelector('.es-main');
    if(nextScroll)nextScroll.scrollTop=retainedScroll;
    if(retainedFocus&&!focusNextStep)root.querySelector(retainedFocus)?.focus({preventScroll:true});
    // New pages/steps start at their heading; input edits never reset the page.
    if(focusNextStep){focusNextStep=false;root.querySelector('.suite-form-heading h1')?.focus({preventScroll:true});} 
    window.ExamSproutCountdown?.mount();
    window.PipCompanion?.mount();
  }
  function notice(t) {return `<div class="es-notice">${E(t)}</div>`;}
  function readinessData(plan) {
    return plan?.growth || S.data?.pip_growth || {score:0,stage:1,label:'Just planted',points:0,kind:'effort'};
  }
  function readinessPanel(r) {
    if(!r)return '';
    return `<section class="es-readiness" aria-label="Experimental exam readiness"><div class="es-readiness-top"><div><div class="es-label">Projected exam readiness</div><h2>Know what still needs work.</h2><p>${E(r.evidence)} evidence · ${r.observed_notes} of ${r.eligible_notes} notes checked</p></div><div class="es-readiness-grade" aria-label="Estimated readiness grade ${E(r.grade)}"><strong>${E(r.grade)}</strong><span>${r.score==null?'Not enough evidence':`${r.score}/100 index`}</span></div></div><div class="es-readiness-stats"><span><b>${r.coverage}%</b> recent topic coverage</span><span><b>${r.delayed_coverage}%</b> delayed retrieval</span><span><b>${r.cold_mocks}</b> cold mock checks</span></div><p class="es-readiness-disclaimer">${E(r.disclaimer)}</p><div class="es-readiness-actions"><button class="es-small" data-action="readiness-method">How this estimate works</button><button class="es-primary" data-action="pip-study">Study with Pip ${icon('arrow')}</button></div>${r.limits?.length?`<details><summary>Evidence gaps & next steps</summary>${r.limits.map(x=>`<p>${E(x)}</p>`).join('')}<div class="es-readiness-topics">${r.rows.map(row=>`<div><span title="${E(row.name)}">${E(shortName(row.name))}</span><b>${row.observed?'Checked':'Unmeasured'}</b><small>${row.coverage}% recent coverage · ${E(row.status)}${row.confident_misses?' · '+row.confident_misses+' confident misses':''}</small></div>`).join('')}</div></details>`:''}</section>`;
  }
  function readinessMethod() {
    const r=S.plan?.plan.readiness;if(!r)return;
    modal('A readiness estimate, not a promised grade.',`<p>${E(r.disclaimer)}</p><p style="margin-top:14px">${E(r.method)}</p><p style="margin-top:14px"><strong>Evidence: ${E(r.evidence)}</strong> · ${r.observed_notes} distinct notes over ${r.days} UTC days. Your confidence ratings help find blind spots but do not earn readiness points.</p>${r.sensitivity?`<p style="margin-top:14px">${r.sensitivity[0]}–${r.sensitivity[1]}: ${E(r.sensitivity_label)}</p>`:''}<p style="margin-top:14px">F− through A+ and S are app-specific readiness tiers, not your school's grading scale. S is the exceptional evidence tier. There is no fitted or validated exam-grade model.</p><div class="es-grade-bands">${r.bands.map(x=>`<span><strong>${E(x.grade)}</strong> ${x.minimum}+</span>`).join('')}</div>`,`<button class="es-primary" data-action="close-modal">Back to my plan</button>`,null);
  }
  function draftBanner() {
    const d=S.data.draft;if(!d)return '';
    return `<section class="es-draft-banner suite-resume-card" aria-label="Saved practice session"><div class="suite-resume-symbol">${icon('clock')}</div><div><span class="es-label">Saved on this computer</span><h3>${E(S.data.state.exams.find(e=>e.id===d.exam_id)?.name||'Unfinished exam')}</h3><p>${d.error?E(d.error):`Question ${d.at} of ${d.questions} · ${d.phase==='grading'?'Self-marking':d.timed?'Timer continues while closed':'Untimed'} · Written responses are stored locally.`}</p><small>Resume the existing session; do not start over. Discard removes this saved copy, not your decks or finished results.</small></div><div class="es-flex">${!d.error?'<button class="es-primary" data-action="resume-exam">Resume</button>':''}<button class="es-quiet" data-action="discard-draft">Discard</button></div></section>`;
  }

  function groupHistory(){
    const rows=(S.data.state.history||[]).filter(r=>r.exam_id.startsWith('atelier_group_')).slice(-8).reverse();
    if(!rows.length)return '';
    return `<section class="es-history"><div class="es-section-head"><div><h3>Study-group sessions</h3><p class="es-muted">Pip practice using your focus folders · self-marked, not predicted exam grades</p></div></div>${rows.map(r=>`<div class="es-history-row"><span class="es-score">${r.percent}%</span><div><strong>Pip · study group</strong><p>${r.graded}/${r.total} self-marked · ${E(localDate(r.finished_at))}</p></div><button class="es-small" data-action="result" data-id="${E(r.id)}">Details</button></div>`).join('')}</section>`;
  }
  function pipPanel(growth) {
    const base=E((S.data.asset_base||'/_addons/exam_sprout/web')+'/pip');
    const animate=S.data.state.settings.animate_pip!==false;
    const world=pipWorld(S.data?.state?.settings?.theme);
    const portrait=`${base}/companion-${world.kind}-1.0.3.png`, actions=pipActions(world.kind), stages=pipStages(world.kind);
    return `<aside class="es-companion-panel" aria-label="Pip companion"><section class="pip-card pip-world-${world.kind}" data-pip-world="${world.kind}" data-pip-world-label="${E(world.label)}" data-pip-base="${base}" data-pip-portrait="${portrait}" data-pip-key="profile-companion" data-pip-stage="${growth.stage}" data-pip-animate="${animate}"><span class="pip-kicker">A LITTLE LIFE BESIDE YOUR STUDY</span><button class="pip-touch" data-pip-action="greet" aria-label="Greet ${E(world.label)}"><span class="pip-world-aura" aria-hidden="true"><span class="pip-world-emblem">${pipWorldMark(world.kind)}</span></span><img class="pip-image" src="${portrait}" alt="${E(world.label)}" draggable="false"><canvas class="pip-canvas" aria-hidden="true" hidden></canvas></button><strong class="pip-name">Meet Pip</strong><span class="pip-world-label">${E(world.label)}</span><span class="pip-speech" aria-live="polite">Quiet company. No distractions.</span><div class="pip-actions"><button data-pip-action="pet">${actions[0]}</button><button data-pip-action="water">${actions[1]}</button></div><button class="pip-pause" data-pip-action="pause">Pause motion</button><span class="pip-mode">Loading your companion…</span></section><div class="es-pip-progress"><span class="es-pip-stage-label">${E(pipStageLabel(world.kind,growth.stage))}</span><strong>${growth.score}<small>%</small></strong><div class="es-growth-bar" role="meter" aria-label="Effort progress toward Pip’s next stage, not readiness" aria-valuenow="${growth.score}" aria-valuemin="0" aria-valuemax="100"><span style="width:${growth.score}%"></span></div><div class="es-growth-steps" aria-label="Pip growth">${stages.map((name,i)=>`<span aria-current="${i+1===growth.stage?'step':'false'}">${name}</span>`).join('')}</div><p><strong>${growth.points||0} effort points</strong>${growth.next?` · ${growth.next} for the next stage`:" · Lifetime growth"}. One point per studied note per day, across exams. Incorrect effort counts too. Exam readiness is separate; companion interactions add no points.</p><button class="es-small es-full-width" data-action="pip-study">Study with Pip</button></div></aside>`;
  }

  function renderFocusRow(r,i){
    const eligible=r.total>0&&!r.missing;
    return `<article class="es-focus-row ${i===0&&r.minutes?'es-first':''}"><div class="es-focus-heading"><span class="es-rank">${String(i+1).padStart(2,'0')}</span><span class="es-deck-name" title="${E(r.name)}"><small>${E(parentName(r.name))}</small><strong>${E(leafName(r.name))}</strong></span><span class="es-focus-time">${r.minutes} <small>min</small></span></div><div class="es-focus-description">${E(r.reason)}</div><div class="es-focus-detail"><p>${r.total} cards in scope</p><div class="es-focus-actions"><button class="${i===0?'es-primary':'es-small'}" data-action="study" data-deck="${r.deck_id}" data-size="${Math.max(1,Math.min(100,r.card_target||20))}" ${eligible?'':'disabled'} title="Open normal Anki review; a filtered scope opens independent focus practice">${i===0?'Start here':'Study'} ${icon('arrow')}</button><button class="es-small" data-action="focus" data-deck="${r.deck_id}" data-size="${Math.max(1,Math.min(100,r.card_target||20))}" ${eligible?'':'disabled'}>Focus practice</button><button class="es-text-button" data-action="browse" data-deck="${r.deck_id}" ${r.missing?'disabled':''}>View cards</button></div></div><div class="es-meter" aria-label="${r.share}% of study focus"><span style="width:${r.share}%"></span></div></article>`;
  }

  function focusRows(plan) {
    return (plan?.rows || []).filter(r => !r.covered_elsewhere);
  }

  function renderOverview() {
    const e=exam();
    if (!e) return `<div class="es-empty">${sprout}<h1>One exam. One clear next step.</h1><p>Add an exam, choose the decks it covers, and tell us where you feel least confident. We’ll turn that into a small, realistic study plan.</p><button class="es-primary" data-action="new">Add your first exam</button><p style="font-size:11px">No account. No AI subscription. Practice stays separate from scheduled reviews.</p></div>`;
    const p=S.plan?.plan;
    const days=daysLeft(e), hours=Math.max(0,Math.floor((new Date(e.due).getTime()-Date.now())/3600000));
    let content=`<div class="es-page-top"><span class="es-label">Your next exam, a little clearer</span><div class="es-flex"><button class="es-quiet es-small" data-action="refresh">Refresh</button><button class="es-small" data-action="edit">Edit exam</button></div></div>
      <div class="es-hero"><div class="es-hero-copy"><div class="es-hero-kicker">${sprout}<span>Small steps. More breathing room.</span></div><h1>${E(e.name)}</h1><p class="es-hero-date">${icon('calendar')}${E(examDate(e.due))}<span>Local time</span></p>${e.topics?`<p class="es-topic-line">${E(e.topics)}</p>`:''}</div><div class="es-count"><span class="es-count-caption">${isPast(e)?'LOOKING BACK':'COUNTING DOWN'}</span><strong>${isPast(e)?'—':days>1?days:hours}</strong><span class="es-count-unit">${isPast(e)?'Exam time passed':days>1?'days to go':'hours to go'}</span><span class="es-count-date">${E(new Date(e.due).toLocaleDateString(undefined,{month:'short',day:'numeric'}))}</span></div></div>`;
    if(S.plan?.error) return content+notice(S.plan.error)+`<button data-action="refresh">Try again</button>`;
    if(!p) return content+`<div class="es-loading">Reading your deck history…</div><div class="es-skeleton"></div><div class="es-skeleton"></div>`;
    const growth=readinessData(p), rows=focusRows(p);
    content+=`<div class="es-study-workspace ${S.data.state.settings.show_pip===false?'es-without-pip':''}"><div class="es-study-main"><div class="es-metrics"><div class="es-metric"><div class="es-metric-icon">${icon('clock')}</div><div><strong>${p.budget_minutes}<small>min</small></strong><span>${p.today_is_study_day?'Today’s time budget':'Next study-day budget'}</span></div></div><div class="es-metric"><div class="es-metric-icon">${icon('calendar')}</div><div><strong>${p.study_days_left}<small>${p.study_days_left===1?'day':'days'}</small></strong><span>Study days left</span></div></div><div class="es-metric"><div class="es-metric-icon">${icon('layers')}</div><div><strong>${e.scopes.length}<small>${e.scopes.length===1?'deck':'decks'}</small></strong><span>Included in this exam</span></div></div></div>
      ${readinessPanel(p.readiness)}
      <div class="es-section-head"><div><h2>${p.today_is_study_day?'A good place to start.':'Your next study session'}</h2><p class="es-section-sub">Your focus, in order. One deck at a time.</p></div><span class="es-pill">${p.mode==='cram'?'Cram mode':'Steady study'}</span></div>
      ${(S.allRows?rows:rows.slice(0,5)).map(renderFocusRow).join('')}
      ${rows.length>5?`<button class="es-quiet es-small es-expand" data-action="toggle-rows">${S.allRows?'Show fewer priorities':`Show all ${rows.length} deck groups`}</button>`:''}
      <p class="es-plan-footnote">${p.focus_minutes} minutes of focus + ${p.break_minutes} minutes for breaks. Time allocations are estimates, not Anki scheduling instructions.</p>
      ${[...(p.warnings||[]),...(S.plan.warnings||[])].length?`<details class="es-coverage-notes"><summary>Coverage & time notes (${new Set([...(p.warnings||[]),...(S.plan.warnings||[])]).size})</summary>${[...new Set([...(p.warnings||[]),...(S.plan.warnings||[])])].map(notice).join('')}</details>`:''}
      ${S.data.suite&&!e.query?`<div class="suite-plan-controls"><button data-action="suite-focus">Pin these folders to the study desk</button><span>Normal review stays separate from practice.</span></div>`:''}<div class="es-practice-callout">${cardsIcon}<div><h3>Make the real thing feel familiar.</h3><p>A mixed practice exam, from your own decks. No rescheduling.</p></div><button class="es-primary" data-action="nav" data-view="practice">Build an exam ${icon('arrow')}</button></div>
      <details><summary>How this plan works & what to do next</summary><p>${E(p.guidance)}</p><div class="es-phases">${p.phases.map((x,i)=>`<div><span class="es-phase-num">0${i+1}</span><h3>${E(x.title)}</h3><p>${E(x.body)}</p></div>`).join('')}</div><p>${E(p.method)}</p><p>Topics are your planning brief. Deck-name suggestions are only hints; confirm the decks and use an Anki search filter to narrow the actual card scope.</p></details>
      ${renderHistory(e)}
      <div style="margin-top:26px;display:flex;gap:12px"><button class="es-quiet es-small" data-action="archive">${e.archived?'Unarchive':'Archive'} exam</button><button class="es-quiet es-small es-danger" data-action="delete">Delete exam</button></div></div>${S.data.state.settings.show_pip===false?'':pipPanel(growth)}</div>`;
    return content;
  }
  function leafName(name) { return String(name).split('::').at(-1); }
  function parentName(name) { const p=String(name).split('::'); return p.length>1?p.slice(Math.max(0,p.length-3),-1).join(' / '):'Selected deck'; }
  function shortName(name) { const parts=String(name).split('::');return parts.length>1?parts.slice(-2).join(' / '):name; }
  function renderHistory(e) {
    const all=S.data.state.history.filter(r=>r.exam_id===e.id).slice().reverse();
    if(!all.length)return '';
    const history=historyExpanded?all:all.slice(0,5);
    return `<div class="es-history"><div class="es-section-head"><div><h3>Recent practice</h3><p class="es-muted">Self-marked, not a predicted score · ${all.length} stored sessions</p></div>${all.length>5?`<button class="es-small" data-action="history-expand">${historyExpanded?'Show recent five':'Show all stored sessions'}</button>`:''}</div>${history.map(r=>`<div class="es-history-row"><span class="es-score">${r.percent}%</span><div><strong>${r.pip_study?'Pip Study':r.kind==='exam'?'Mock exam':'Focus practice'}${r.interrupted?' · Partial session':''}</strong><p>${r.graded}/${r.total} self-marked · ${r.ungraded} ungraded</p><p class="es-muted">${E(localDate(r.finished_at))}</p></div><button class="es-small" data-action="result" data-id="${E(r.id)}">Details</button></div>`).join('')}</div>`;
  }
  function newExam() {
    if(S.draft){confirmModal('Discard unsaved changes?','A new exam will start with a blank form.',()=>{S.draft=null;newExam();});return;}
    const due=new Date(); due.setDate(due.getDate()+7); due.setHours(9,0,0,0);
    const local=new Date(due.getTime()-due.getTimezoneOffset()*60000).toISOString().slice(0,16);
    S.draft={name:'',due:local,topics:'',exam_format:'mixed',mode:'auto',daily_minutes:60,weekdays:[0,1,2,3,4,5,6],scopes:[],query:'',step:1};
    railOpen=false;focusNextStep=true;S.step=1;S.deckSearch='';S.suggestions=[];S.view='overview';render();
  }
  function editExam() {if(!exam())return;S.draft=JSON.parse(JSON.stringify(exam()));S.draft.step=1;S.step=1;S.deckSearch='';S.suggestions=[];railOpen=false;focusNextStep=true;render();}
  function renderForm() {
    const d=S.draft; d.step=S.step;
    const stepTitles=['The essentials','Choose your decks · combine parents','Find your rhythm'];
    const stepHelp=['Name the exam and choose its date. You can refine the rest later.',
      'Choose the material you actually need. Each deck keeps its own confidence and emphasis.',
      'Set a realistic budget. Your existing Anki schedule stays unchanged.'];
    let html=`<div class="es-form suite-exam-editor"><div class="suite-form-heading"><div><span class="es-label">${d.id?'Edit exam':'Create an exam'} · Step ${S.step} of 3</span><h1 tabindex="-1">${stepTitles[S.step-1]}</h1><p>${stepHelp[S.step-1]}</p></div><span class="suite-unsaved-state">Not saved yet</span></div>
      <nav class="es-stepper" aria-label="Exam setup progress">${['The exam','Your decks','Your routine'].map((x,i)=>`<button type="button" class="es-step ${S.step===i+1?'active':i+1<S.step?'complete':''}" data-action="setup-step" data-step="${i+1}" ${i+1>=S.step?'disabled':''} ${S.step===i+1?'aria-current="step"':''}><b>${i+1<S.step?icon('check'):i+1}</b><span>${x}</span></button>`).join('')}</nav>
      <div class="suite-setup-scroll"><div class="suite-setup-grid"><section class="suite-editor-fields" aria-label="Exam setup fields">`;

    if(S.step===1) html+=`
      <label class="es-field">What’s the exam called?<input data-field="name" value="${E(d.name)}" maxlength="120" placeholder="e.g. Pharmacotherapy · Exam 3" required></label>
      <div class="es-form-grid"><label class="es-field">When is it?<input type="datetime-local" data-field="due" value="${E(d.due.slice(0,16))}" required><small>Uses this computer’s local time. Update it when travelling.</small></label>
      <label class="es-field">What kind of questions?<select data-field="exam_format"><option value="mixed"${selectedAttr(d.exam_format,'mixed')}>A mix of recall and application</option><option value="recall"${selectedAttr(d.exam_format,'recall')}>Mostly facts and recall</option><option value="application"${selectedAttr(d.exam_format,'application')}>Cases, reasoning, and application</option></select></label></div>
      <label class="es-field">What does the exam cover?<textarea data-field="topics" maxlength="3000" placeholder="List the topics, lectures, or chapters you need to know.">${E(d.topics)}</textarea><small>We can suggest matching deck names. You’ll confirm which decks actually cover these topics.</small></label>`;
    if(S.step===2) html+=`<h2>Choose one or more parent folders or decks.</h2><p class="es-intro">Combine separate courses or parent folders in this one exam. Confidence runs from unfamiliar to confident. Emphasis is relative exam importance: 2 means twice as important as 1. Subdecks are included automatically; overlapping selections never duplicate cards.</p>
      <div class="es-flex" style="margin-bottom:12px"><input data-special="deck-search" value="${E(S.deckSearch)}" aria-label="Filter decks" placeholder="Find a deck…"><button class="es-small" data-action="suggest">Suggest by topic</button></div>
      <div class="es-bulk-bar"><strong>Quick apply to selected decks</strong><div class="es-bulk-controls"><label>Confidence <select data-bulk="confidence">${[1,2,3,4,5].map(n=>`<option value="${n}">${n}</option>`).join('')}</select><button class="es-small" type="button" data-action="apply-bulk" data-kind="confidence">Set all</button></label><label>Emphasis <input type="number" data-bulk="emphasis" value="1" min="0" max="1000" step="0.5"><button class="es-small" type="button" data-action="apply-bulk" data-kind="emphasis">Set all</button></label></div></div>
      <div class="es-deck-picker-head"><span>Parent folder or deck</span><span>Confidence</span><span>Emphasis</span></div><div id="es-deck-options"></div><p class="es-picker-summary" id="es-picker-summary">${d.scopes.length} parent folders / decks selected</p>`;
    if(S.step===3) html+=`<h2>Choose a pace you can actually keep.</h2><p class="es-intro">Auto switches to cram mode in the final 72 hours. No mode changes your Anki scheduling.</p>
      <div class="es-choice-grid">${[['auto','Find my pace','Steady now, focused near exam day.'],['steady','Steady study','Build, revisit, then rehearse.'],['cram','I’m cramming','Triage the most important weak areas.']].map(([value,title,desc])=>`<button class="es-choice${activeClass(d.mode===value)}" data-action="study-mode" data-value="${value}" aria-pressed="${d.mode===value}"><strong>${title}</strong><span>${desc}</span></button>`).join('')}</div>
      <label class="es-field">How much time per selected day?<input type="number" data-field="daily_minutes" value="${E(d.daily_minutes)}" min="5" max="480" step="5"><small>5–480 minutes. Break time is included, and this budget applies to this exam only.</small></label>
      <p style="font-size:12px;margin:0 0 10px">Which days can you study?</p><div class="es-weekdays">${['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map((x,i)=>`<button class="es-weekday${activeClass(d.weekdays.includes(i))}" data-action="weekday" data-day="${i}" aria-pressed="${d.weekdays.includes(i)}">${x}</button>`).join('')}</div>
      <details><summary>Advanced: narrow the material with an Anki search</summary><label class="es-field" style="margin-top:15px">Optional search filter<input data-field="query" value="${E(d.query)}" maxlength="2000" placeholder="e.g. tag:exam3 or (tag:cardiology or tag:renal)"><small>This is applied inside the selected decks. Suspended and buried cards are excluded from study planning.</small></label></details>`;
    return html+`</section><aside class="suite-editor-aside" aria-label="Live exam summary"><details class="suite-setup-summary" data-summary-mode="setup" ${summaryExpanded.setup??innerWidth>=1180?'open':''}><summary>${icon('plan')} Your exam at a glance <span aria-hidden="true">⌄</span></summary><div class="suite-summary-scenery" aria-hidden="true"></div><div class="suite-summary-content"></div></details></aside></div></div><div class="es-form-actions"><button class="es-quiet" data-action="cancel-form">Cancel</button><span class="suite-save-hint">${S.step===3?'Review your summary, then save.':'Saved only when you finish step 3.'}</span><div class="es-flex">${S.step>1?'<button data-action="back-step">Back</button>':''}<button class="es-primary" data-action="${S.step===3?'save':'next-step'}">${S.step===3?'Save my exam':'Continue →'}</button></div></div></div>`;
  }
  function updateSetupSummary() {
    const dest=root?.querySelector('.suite-summary-content'),d=S.draft;
    if(!dest||!d)return;
    const validDate=d.due&&Number.isFinite(new Date(d.due).getTime());
    const minutes=Number(d.daily_minutes),weekdays=Array.isArray(d.weekdays)?d.weekdays:[];
    const selected=d.scopes||[],format={mixed:'Recall & application',recall:'Facts & recall',application:'Cases & reasoning'}[d.exam_format]||'Not chosen';
    const routine={auto:'Automatic pace',steady:'Steady study',cram:'Focused cram'}[d.mode]||'Not chosen';
    dest.innerHTML=`<span class="es-label">Your plan, in progress</span><h2 data-summary="name">${E(d.name.trim()||'Your next exam')}</h2><dl class="suite-summary-facts"><div><dt>${icon('calendar')} Exam date</dt><dd data-summary="date">${validDate?E(examDate(d.due)):'Choose a date'}<small>Computer’s local time</small></dd></div><div><dt>${icon('plan')} Questions</dt><dd>${format}</dd></div><div><dt>${icon('layers')} Material</dt><dd data-summary="decks">${selected.length} selected ${selected.length===1?'deck':'decks'}<small>Includes subdecks without counting cards twice.</small></dd></div><div><dt>${icon('clock')} Study rhythm</dt><dd data-summary="routine">${routine}<small>${Number.isFinite(minutes)?E(minutes):'—'} min / study day · ${weekdays.length} ${weekdays.length===1?'day':'days'} / week</small></dd></div></dl>${selected.length?`<div class="suite-scope-preview"><span class="es-label">Selected material</span>${selected.slice(0,4).map(s=>`<span>${E(shortName(s.name))}</span>`).join('')}${selected.length>4?`<small>+ ${selected.length-4} more selections</small>`:''}</div>`:''}${d.query?.trim()?'<p class="suite-summary-filter">An Anki search further narrows this material.</p>':''}<p class="suite-summary-note">${lock} Planning does not move cards or change their schedule.</p>`;
  }
  function updatePracticeSummary() {
    const dest=root?.querySelector('.suite-practice-summary-content'),e=exam(),p=S.practice;
    if(!dest||!e)return;
    // Manually typing a size must not leave the previous preset selected.
    for(const button of root.querySelectorAll('[data-action="question-preset"]'))button.setAttribute('aria-pressed',String(Number(button.dataset.size)===Number(p.size)));
    const formats={emphasis:'Exam emphasis',equal:'Equal across decks',size:'Eligible card counts',custom:'Custom weights'};
    dest.innerHTML=`<span class="es-label">${p.kind==='exam'?'Simulated exam':'Quick practice'}</span><h2>${E(e.name)}</h2><div class="suite-session-size"><strong data-summary="size">${E(p.size)}</strong><span>requested questions</span></div><dl class="suite-summary-facts"><div><dt>${icon('clock')} Answering time</dt><dd>${p.minutes?E(p.minutes)+' minutes':'Untimed'}</dd></div><div><dt>${icon('layers')} Material</dt><dd>${e.scopes.length} selected ${e.scopes.length===1?'deck':'decks'}<small>Actual eligible counts appear in the preview.</small></dd></div><div><dt>${icon('plan')} Allocation</dt><dd>${formats[p.weighting]||'Custom'}<small>${p.strategy==='adaptive'?'Targeted toward gaps; not representative.':'Representative of the selected scope.'}</small></dd></div></dl><div class="suite-session-tags"><span>${p.cold_only?'Cold retrieval only':'Warm & cold retrieval'}</span><span>${p.include_new?'New cards allowed':'Learned cards only'}</span>${p.one_per_note?'<span>One card per note</span>':''}</div><p class="suite-summary-note">${lock} Practice only. No recorded Anki reviews or scheduling changes.</p><p class="suite-summary-footnote">${p.kind==='exam'?'Answers stay hidden until submission.':'Reveal and self-mark one card at a time.'} Your next screen confirms the actual sample before you start.</p>`;
  }
  function renderDeckList() {
    const container=root.querySelector('#es-deck-options'); if(!container||!S.draft)return;
    const active=document.activeElement;
    const focusTarget=container.contains(active)&&active?.dataset.special&&active?.dataset.id
      ? '[data-special="'+CSS.escape(active.dataset.special)+'"][data-id="'+CSS.escape(active.dataset.id)+'"]':null;
    const selected=new Map(S.draft.scopes.map(s=>[s.deck_id,s]));
    const all=[...S.data.decks];
    // Keep missing selections visible so they can be removed before saving.
    for(const s of S.draft.scopes) if(!all.some(d=>d.id===s.deck_id))all.push({id:s.deck_id,name:s.name+' (missing)'});
    const list=all.filter(d=>d.name.toLowerCase().includes(S.deckSearch.toLowerCase())).sort((a,b)=>Number(selected.has(b.id))-Number(selected.has(a.id))||Number(S.suggestions.includes(b.id))-Number(S.suggestions.includes(a.id))||a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'}));
    container.innerHTML=list.slice(0,100).map(d=>{const s=selected.get(d.id);return `<div class="es-deck-option"><input type="checkbox" data-special="choose-deck" data-id="${d.id}" id="deck-${d.id}"${checked(s)}><label for="deck-${d.id}">${E(d.name)}${S.suggestions.includes(d.id)?'<span class="es-hint">Name match</span>':''}</label><select data-special="confidence" data-id="${d.id}" aria-label="Confidence for ${E(d.name)}"${s?'':' disabled'}>${['1 · Unfamiliar','2 · Shaky','3 · Some gaps','4 · Mostly good','5 · Confident'].map((x,i)=>`<option value="${i+1}"${selectedAttr(s?.confidence||3,i+1)}>${x}</option>`).join('')}</select><input type="number" data-special="emphasis" data-id="${d.id}" value="${s?.weight??1}" min="0" max="1000" step="0.5" aria-label="Exam emphasis for ${E(d.name)}"${s?'':' disabled'}></div>`;}).join('') || '<p class="es-intro">No matching decks. Try a shorter search.</p>';
    if(focusTarget)container.querySelector(focusTarget)?.focus({preventScroll:true});
    updateSetupSummary();
    root.querySelector('#es-picker-summary').textContent=`${selected.size} parent folders / decks selected${list.length>100?' · Showing the first 100 matches; narrow your search.':''}`;
  }
  function validateStep() {
    const d=S.draft;
    if(S.step===1) {
      if(!d.name.trim())throw new Error('Give your exam a name.');
      if(!d.due||!Number.isFinite(new Date(d.due).getTime()))throw new Error('Choose a valid exam date and time.');
      if(!d.id&&new Date(d.due)<=new Date())throw new Error('Choose a future date for a new exam.');
    }
    if(S.step===2) {
      if(!d.scopes.length)throw new Error('Choose at least one deck.');
      if(!d.scopes.some(s=>Number(s.weight)>0))throw new Error('At least one selected deck needs positive exam emphasis.');
    }
    if(S.step===3) {
      if(!d.weekdays.length)throw new Error('Choose at least one study day.');
      if(!Number.isInteger(Number(d.daily_minutes))||d.daily_minutes<5||d.daily_minutes>480)throw new Error('Enter a daily budget from 5 to 480 minutes.');
    }
  }
  function renderPractice() {
    const e=exam(); if(!e)return `${draftBanner()}<div class="es-empty">${cardsIcon}<h1>Choose what to practice.</h1><p>Use an active study group with Pip, or create a complete exam plan.</p>${S.data.suite?'<button class="es-primary" data-action="pip-study">Study an active group with Pip</button>':''}<button class="es-small" data-action="new">Create exam plan</button></div>${groupHistory()}`;
    const p=S.practice;
    return `${draftBanner()}${groupHistory()}<div class="suite-practice-heading"><div class="es-label">Practice, without the side effects</div><h1 style="margin-top:8px">Your exam rehearsal, your rules.</h1><p class="es-intro">For ${E(e.name)} · Random cards from ${e.scopes.length} selected decks and their subdecks. New and not-yet-due cards can be included.</p><span class="suite-schedule-safe">${lock} Practice only · does not change scheduling</span></div>
      <div class="suite-practice-grid"><div class="es-practice-card"><div class="es-mode-switch">${[['exam','Simulated exam','Answer all questions first. Reveal and self-mark after submission.'],['practice','Quick practice','Reveal and self-mark each card as you go.']].map(([value,title,desc])=>`<button class="${p.kind===value?'selected':''}" data-action="practice-kind" data-value="${value}" aria-pressed="${p.kind===value}"><strong>${title}</strong><span>${desc}</span></button>`).join('')}</div>
      <div class="es-form-grid"><label class="es-field">How many cards?<input type="number" data-practice="size" value="${p.size}" min="1" max="500" step="1"><small>1–500 unique cards. We never repeat cards to fill a shortfall.</small></label><label class="es-field">Time limit (minutes)<input type="number" data-practice="minutes" value="${p.minutes}" min="0" max="720" step="1"><small>0 = untimed. The timer ends the answering pass, not self-marking.</small></label></div>
      <div class="es-session-presets" aria-label="Question count presets">${[25,50,100,200,500].map(n=>`<button class="es-small" data-action="question-preset" data-size="${n}" aria-pressed="${p.size===n}">${n} questions</button>`).join('')}</div>
      <label class="es-field">What is this session for?<select data-practice="strategy"><option value="representative"${selectedAttr(p.strategy,'representative')}>Representative mock · check broad readiness</option><option value="adaptive"${selectedAttr(p.strategy,'adaptive')}>Targeted rehearsal · weak spots and confident mistakes</option></select><small>Mock questions are fixed before you start. Targeted practice is intentionally biased toward gaps; it is not treated as a representative mock.</small></label>
      ${checkOption('cold_only','Cold retrieval only','Exclude new notes, unknown exposure dates, and any note studied in the last 24 hours. A shorter pool is disclosed, never silently filled with warm repeats.',p.cold_only)}
      <label class="es-field">How should decks be represented?<select data-practice="weighting">${[['emphasis','Use my exam emphasis'],['equal','About equally across selected decks'],['size','Proportional to eligible card counts'],['custom','Custom practice weights']].map(([v,t])=>`<option value="${v}"${selectedAttr(p.weighting,v)}>${t}</option>`).join('')}</select><small>Weights set relative proportions, not exact card counts. The next screen shows the actual allocation.</small></label>
      ${p.weighting==='custom'?`<div>${e.scopes.map(s=>`<div class="es-weight-row"><label for="weight-${s.deck_id}">${E(shortName(s.name))}</label><input id="weight-${s.deck_id}" data-weight="${s.deck_id}" type="number" min="0" max="1000" step="1" value="${E(p.weights[s.deck_id]??s.weight)}"></div>`).join('')}<p class="es-plan-footnote">For example, 50 / 30 / 20. Zero excludes a deck from this session. Weights do not have to total 100.</p></div>`:''}
      <details><summary>Advanced settings & card inclusion</summary>
      ${checkOption('one_per_note','One card per note','Avoid answer leakage between reversed cards or cloze siblings.',p.one_per_note)}
      ${checkOption('ensure_coverage','Include each positive-weight deck when possible','Reserves at least one card per nonempty eligible deck if the session is large enough.',p.ensure_coverage)}
      ${checkOption('include_new','Include cards I haven’t learned yet','Useful for a diagnostic exam or broad rehearsal.',p.include_new)}
      ${checkOption('include_suspended','Include suspended cards in this practice only','Does not unsuspend them or change their schedule.',p.include_suspended)}
      ${checkOption('include_buried','Include buried cards in this practice only','Does not unbury them or change their schedule.',p.include_buried)}
      <p>Selected child decks take precedence over selected parents. Every sampled card appears only once, and the final order is shuffled.</p></details>
      <button class="es-primary es-full-width" style="margin-top:25px" data-action="prepare">Preview my exam →</button>
      <p class="es-plan-footnote" style="text-align:center;margin:13px 0 0">${lock} No filtered decks. No rescheduling. No recorded Anki reviews.</p></div><aside class="suite-practice-aside"><details class="suite-setup-summary" data-summary-mode="practice" ${summaryExpanded.practice??innerWidth>=1180?'open':''}><summary>${icon('plan')} Session summary <span aria-hidden="true">⌄</span></summary><div class="suite-summary-scenery" aria-hidden="true"></div><div class="suite-practice-summary-content"></div></details></aside></div>
      <p class="es-intro" style="margin-top:20px">Uses your actual templates, not generated exam questions. Mark mental or written answers before submitting; add confidence to spot guessing and confident mistakes. Flags, a question navigator, early submission, Save & close, and original-answer review are available. Timed mock exams keep counting while closed. Save & close explicitly stores answers locally; otherwise written responses stay in memory unless local retention is enabled.</p>`;
  }
  function checkOption(key,title,desc,value){return `<label class="es-check-row"><input type="checkbox" data-practice="${key}"${checked(value)}><span>${title}<small>${desc}</small></span></label>`;}
  function renderSettings() {
    const s=S.data.state.settings;
    const themes=[['inherit','Match Anki','#eef0eb','#6a7c6e'],['sage','Sage','#e9f0e4','#557554'],['lavender','Lavender','#f0eafa','#805c9e'],['peach','Peach','#fff0e2','#a86b49'],['rose','Rose','#fbe8f1','#aa507b'],['sky','Sky','#e8f2fc','#467aa3'],['midnight','Midnight','#28293c','#c3c5f0']];
    return `<div class="es-label">Make yourself at home</div><h1 style="margin-top:8px">Find your kind of calm.</h1><p class="es-intro">${S.data.suite?'Choose how your planner and companion work. Use World above to change the appearance throughout Atelier.':'Keep the countdown in the background. Choose a color, or let it settle into your Anki theme.'}</p>
      <div class="es-preview-stage"><div class="es-label">Live countdown preview</div><div class="es-preview-widget">${S.data.countdown_html||''}</div><p>${s.show_countdown?'This is how your countdown will look on the Decks screen.':'Your home countdown is hidden. This preview still shows your chosen style.'}</p></div><h2>A little more you.</h2><div class="es-theme-grid">${themes.map(([value,title,bg,fg])=>`<button class="es-theme-card${activeClass(s.theme===value)}" data-action="theme" data-value="${value}" aria-pressed="${s.theme===value}"><span class="es-swatch" style="--preview-bg:${bg};--preview-fg:${fg}"><span class="es-swatch-mini">${sprout}<i></i><b>12d</b></span><span class="es-swatch-check">${icon('check')}</span></span><strong>${title}</strong></button>`).join('')}</div>
      <p class="es-intro">${S.data.suite?'These colors apply when you keep another add-on’s theme or turn off Match Exam Studio. Otherwise, the World selector controls Atelier’s appearance.':'Match Anki inherits available theme colors and keeps the home widget transparent. Presets only style Exam Sprout—not your decks, card templates, or reviewer. Theme add-ons that completely replace the deck screen may require integration.'}</p>
      ${[['show_countdown','Show the home-screen countdown','A clickable reminder on your Anki home.'],['compact','Keep it extra compact','A small single-line tile. Turn off for the date and study-plan hint.'],['show_toolbar','Show “Exams” in the top navigation',S.data.suite?'Exam Studio stays available from Tools → Atelier.':'Exam Sprout stays available from Anki’s Tools menu.'],['show_pip','Show Pip','A growing companion in your planner, with a tiny version in card sessions.'],['reviewer_pip','Tiny Pip while reviewing','A small companion beside your review controls. Click to pet; right-click to water, pause, or hide.'],['animate_pip','Animate Pip','Gentle idle, petting and watering animations. Reduced-motion preferences take priority.'],['remember_answers','Save written practice answers locally','Off by default. Retains the last 10 sessions on this computer. Turning off deletes the saved response file.']].map(([key,title,desc])=>`<label class="es-setting-row"><div><h3>${title}</h3><p>${desc}</p></div><input type="checkbox" role="switch" data-setting="${key}"${checked(s[key])}></label>`).join('')}
      <label class="es-setting-row"><div><h3>Visible countdowns</h3><p>The closest upcoming exams come first.</p></div><select data-setting="max_countdowns">${[1,2,3].map(n=>`<option${selectedAttr(s.max_countdowns,n)}>${n}</option>`).join('')}</select></label>
      <div class="es-setting-row"><div><h3>Your plans belong to you</h3><p>Plans and results stay in this Anki profile. No account is needed. Anki Sync does not include this data; keep a separate backup.</p></div><button class="es-small" data-action="export">Export data</button></div>
      <div class="es-about"><p>${S.data.suite?'Exam Studio · included with Atelier':'Exam Sprout '+E(S.data.version)}</p><p>By <a href="https://daedalusworks.net/" target="_blank" rel="noopener noreferrer">Daedalus Works</a></p><p style="margin-top:12px">Your original Anki cards, formatting, and media are used in practice. Specialized card templates and other add-ons may need their own settings.</p></div>`;
  }
  let activeResult=null, resultFilter='all', resultPage=0, historyExpanded=false;
  function modal(title,body,buttons,callback,kind='') {
    const d=root.querySelector('#es-modal');if(!d)return;
    modalCallback=callback;
    d.dataset.view=kind;
    d.setAttribute('aria-labelledby','suite-modal-title');
    d.innerHTML=`<div class="es-modal-inner"><header class="suite-modal-heading"><h2 id="suite-modal-title">${E(title)}</h2><button type="button" class="es-quiet suite-modal-close" data-action="dismiss-dialog" aria-label="Close dialog">×</button></header><div class="suite-modal-alerts"></div><div class="suite-modal-scroll">${body}</div><div class="es-modal-actions">${buttons}</div></div>`;
    d.showModal();
  }
  function closeModal(){const d=root.querySelector('#es-modal');if(d?.open)d.close();modalCallback=null;}
  function confirmModal(title,body,fn){modal(title,`<p>${E(body)}</p>`,`<button data-action="close-modal">Keep editing</button><button class="es-primary" data-action="confirm-modal">Continue</button>`,fn);}
  function sampleModal(sample) {
    modal(`${sample.actual} cards, ready when you are.`, `<p>${sample.kind==='exam'?'Answers stay hidden until you submit the exam.':'Reveal and self-mark each card as you go.'} ${sample.minutes?`${sample.minutes}-minute time limit.`:'No timer.'}</p><div style="margin-top:17px">${sample.counts.map(row=>`<div class="es-allocation-row"><span>${E(shortName(row.name))}</span><strong>${row.count}</strong></div>`).join('')}</div>${sample.warnings.map(notice).join('')}${sample.coverage?.length?`<details><summary>Deck coverage details</summary>${sample.coverage.map(r=>`<div class="es-coverage-row"><strong>${E(shortName(r.name))}</strong><span>${r.drawn} drawn · ${r.available} available</span><small>${E(r.status)}</small></div>`).join('')}</details>`:''}<p style="margin-top:17px">${lock} Nothing in your Anki schedule will be changed.</p>`, `<button data-action="close-modal">Adjust settings</button><button class="es-primary" data-action="confirm-modal">Start ${sample.kind==='exam'?'exam':'practice'} →</button>`, async()=>{await request('start',{token:sample.token});});
  }
  function legacyResultModal(r) {
    const names=new Map((exam()?.scopes||[]).map(s=>[s.deck_id,s.name]));
    const items=r.items||[],blind=items.filter(x=>x.confidence===3&&x.grade!=null&&x.grade<1).length;
    const types={};items.forEach(x=>{if(x.error_type&&x.error_type!=='none')types[x.error_type]=(types[x.error_type]||0)+1;});
    const diagnostics=`<section class="es-result-diagnostics"><strong>${blind} confident mistake${blind===1?'':'s'}</strong><p>${r.sampling==='adaptive'?'Targeted sample: use this to find gaps, not as a representative mock score.':'First-pass mock result. Compare topic coverage as well as total points.'}</p>${Object.keys(types).length?`<p>Error categories: ${Object.entries(types).map(([k,v])=>E(k)+' '+v).join(' · ')}</p>`:''}</section>`;
    modal(r.interrupted?'A little practice still counts.':'A rehearsal, in the books.',`${diagnostics}<div class="es-big-score">${r.percent}%</div><p>Self-marked points across all ${r.total} selected cards. This is not a predicted exam score.</p><p style="margin-top:9px">${r.graded} graded · ${r.ungraded} ungraded · ${Math.floor(r.elapsed_seconds/60)}m ${r.elapsed_seconds%60}s answering${r.timed_out?' · Time limit reached':''}</p><div style="margin-top:20px">${r.breakdown.map(row=>`<div class="es-allocation-row"><span>${E(shortName(names.get(row.deck_id)||String(row.deck_id)))}</span><strong>${row.points}/${row.total}</strong></div>`).join('')}</div><p style="margin-top:18px">Missed = 0 · Partly right = ½ · Correct = 1. Unanswered items in a completed exam receive no credit. Render failures, unfinished sessions and answered-but-unmarked items are excluded from the readiness evidence.</p>`, `<button data-action="close-modal">Back to my plan</button><button class="es-small" data-action="export-result" data-id="${E(r.id)}">Export result</button><button class="es-small" data-action="review-all" data-id="${E(r.id)}">Review all</button><button class="es-primary" data-action="review-misses" data-id="${E(r.id)}">Review misses & unanswered →</button>`,null);
  }
  function resultModal(r) {
    if(!S.data.suite||!window.AtelierSessionModel)return legacyResultModal(r);
    activeResult=r;resultFilter='all';resultPage=0;
    const d=window.AtelierSessionModel.inspect(r);
    const plan=S.data.state.exams.find(e=>e.id===r.exam_id);
    const names=new Map((plan?.scopes||[]).map(s=>[String(s.deck_id),s.name]));
    const elapsed=Number.isFinite(r.elapsed_seconds)?Math.max(0,Math.floor(r.elapsed_seconds)):0;
    const breakdown=(r.breakdown||[]).map(row=>`<div class="suite-result-deck"><span>${E(shortName(names.get(String(row.deck_id))||String(row.deck_id)))}</span><b>${E(row.points)} / ${E(row.total)}</b><small>${E(row.graded)} self-marked</small></div>`).join('');
    const actions=`<button data-action="close-modal">Back to my plan</button><button class="es-small" data-action="export-result" data-id="${E(r.id)}">Export result</button><button class="es-small" data-action="review-all" data-id="${E(r.id)}" data-exam="${E(r.exam_id)}">Review all</button><button class="es-primary" data-action="review-misses" data-id="${E(r.id)}" data-exam="${E(r.exam_id)}">Review misses & unanswered →</button>`;
    modal(d.partial?'Your partial session':'Your session, in perspective',`
      <div class="suite-session-heading"><span class="suite-session-kicker">${E(d.label)}${d.targeted?' · targeted sample':''}${d.partial?' · partial result':''}</span><span>${E(localDate(r.finished_at))}</span></div>
      <section class="suite-result-hero"><div><span class="es-label">Self-marked points</span><div class="es-big-score">${d.percent===null?'—':E(d.percent)+'<small>%</small>'}</div><p>${E(d.points)} points across all ${E(d.total)} selected cards.<br><b>This is not a predicted exam score.</b></p></div><div class="suite-result-metrics"><div><b>${E(r.graded??0)} / ${E(d.total)}</b><span>Self-marked</span></div><div><b>${E(r.ungraded??0)}</b><span>Not graded</span></div><div><b>${Math.floor(elapsed/60)}m ${elapsed%60}s</b><span>Answering time${r.timed_out?' · limit reached':''}</span></div><div><b>${d.confident}</b><span>Confident misses</span></div></div></section>
      <div class="suite-session-safety" data-kind="${d.scheduled?'learning':'rehearsal'}">${lock}<span>${E(d.scheduleLabel)}. Reviewing this result is read-only.</span></div>
      <section class="es-result-diagnostics"><h3>${d.partial?'Use what you completed.':'Turn the result into a next step.'}</h3><p>${d.partial?'This is an unfinished session, not a complete mock. Ungraded cards are not proof of a knowledge gap.':d.targeted?'Targeted sample: use this to find gaps, not as a representative mock score.':r.kind==='exam'?'Compare topic coverage as well as the total points. Your marks reflect this first pass, not a predicted grade.':'This was reveal-and-self-mark practice, not an answer-locked mock.'} ${d.confident?'Start by revisiting confident misses, then compare your recorded reasoning with the original answers.':'Use Review misses & unanswered to revisit the original cards without changing marks or due dates.'}</p></section>
      <section class="suite-result-breakdown"><h3>By deck</h3>${breakdown||'<p>No deck breakdown was retained for this older result.</p>'}</section>
      <section class="suite-result-questions" aria-label="Question results"><div class="suite-result-title"><h3>Question-by-question</h3><label>Show <select id="suite-result-filter" aria-label="Filter question results">${window.AtelierSessionModel.filters.map(x=>`<option value="${x.id}">${E(x.label)}</option>`).join('')}</select></label></div><p class="suite-result-detail-note">Read-only details. Filters do not change marks or the original review actions.</p><div id="suite-result-rows"></div><div class="suite-result-pagination"><span id="suite-result-range" aria-live="polite"></span><div><button class="es-small" data-action="result-page" data-delta="-1">Previous</button><button class="es-small" data-action="result-page" data-delta="1">Next</button></div></div></section>
      <details class="suite-result-method"><summary>How to read these marks and what is kept</summary><p>Missed = 0 · Partly right = ½ · Correct = 1. The percentage uses all selected cards, not only the ones marked. Unanswered items in a completed mock receive no credit. Render failures, unfinished sessions and answered-but-unmarked items are excluded from readiness evidence.</p><p>Written answers are not included in this table or result exports. Original-card review uses any responses still in memory or retained under your local privacy setting. It does not change stored grades.</p></details>`,actions,null,'results');
    paintResultRows();
  }
  function paintResultRows() {
    if(!activeResult||!root.querySelector('#es-modal[open][data-view="results"]'))return;
    const model=window.AtelierSessionModel, data=model.inspect(activeResult),page=model.page(activeResult,resultFilter,resultPage);resultPage=page.page;
    const holder=root.querySelector('#suite-result-rows');
    holder.innerHTML=!data.hasItemDetail?'<p class="suite-session-empty">This older result has no question-level details. Its summary is preserved.</p>':!page.total?'<p class="suite-session-empty">No questions match this filter.</p>':`<div class="suite-result-table" role="table" aria-label="Recorded question outcomes"><div role="row" class="suite-result-table-head"><span role="columnheader">Question</span><span role="columnheader">Outcome</span><span role="columnheader">Before reveal</span><span role="columnheader">Review notes</span></div>${page.rows.map(x=>`<div role="row" data-result-question="${x.number}"><b role="cell">${String(x.number).padStart(2,'0')}${x.flagged?'<small>Flagged</small>':''}</b><span role="cell">${E(x.status)}</span><span role="cell">${E(x.confidence)}${x.seconds!==null?`<small>${E(x.seconds)}s answering</small>`:''}</span><span role="cell">${x.error?E(x.error):'—'}${x.scheduled?'<small>Explicit Anki rating</small>':''}${x.confident?'<small>Confident miss</small>':''}</span></div>`).join('')}</div>`;
    root.querySelector('#suite-result-range').textContent=`${page.from}–${page.to} of ${page.total} · Page ${page.page+1} of ${page.pages}`;
    root.querySelector('[data-action="result-page"][data-delta="-1"]').disabled=resultPage===0;
    root.querySelector('[data-action="result-page"][data-delta="1"]').disabled=resultPage+1>=page.pages;
  }
  function updatePipMode() {
    const toggle=root.querySelector('#es-teach-new'),status=root.querySelector('#suite-pip-mode');if(!toggle||!status)return;
    status.dataset.kind=toggle.checked?'learning':'rehearsal';
    status.querySelector('strong').textContent=toggle.checked?'New-card learning is enabled':'Rehearsal only';
    status.querySelector('p').textContent=toggle.checked?'Only currently NEW cards can receive a real Anki rating, after you reveal. Existing learned cards remain rehearsal.':'All selected cards stay in independent practice. No Anki ratings or scheduling writes from this session.';
  }

  let settingsQueue = Promise.resolve();
  function saveSettings(changes) {
    // Serialize fast theme/toggle changes so a slow response cannot revert another choice.
    const task = settingsQueue.then(async () => {
      const result=await request('settings',{...S.data.state.settings,...changes});
      acceptState(result);
      if(S.view!=='settings'||S.draft)return;
      const focused=document.activeElement;
      const setting=focused?.dataset.setting;
      const theme=focused?.dataset.action==='theme'?focused.dataset.value:null;
      const scrollY=window.scrollY;
      render();
      const next=setting?root.querySelector(`[data-setting="${CSS.escape(setting)}"]`):theme?root.querySelector(`[data-action="theme"][data-value="${CSS.escape(theme)}"]`):null;
      next?.focus({preventScroll:true});
      window.scrollTo(0,scrollY);
    });
    settingsQueue=task.catch(()=>{});
    return task;
  }
  async function action(button) {
    const a=button.dataset.action;
    if(a==='result-page'){resultPage=Math.max(0,resultPage+Number(button.dataset.delta));paintResultRows();return;}
    if(a==='history-expand'){historyExpanded=!historyExpanded;render();return;}
    if(a==='toggle-exams'){railOpen=!railOpen;root.dataset.railOpen=String(railOpen);button.setAttribute('aria-expanded',String(railOpen));button.querySelector('b').textContent=railOpen?'−':'+';return;}
    if(a==='setup-step'){const n=Number(button.dataset.step);if(S.draft&&Number.isInteger(n)&&n>=1&&n<S.step){S.step=n;S.draft.step=n;focusNextStep=true;render();}return;}
    if(a==='nav')return navigate(button.dataset.view);
    if(a==='select-exam')return selectExam(button.dataset.id);
    if(a==='readiness-method')return readinessMethod();
    if(a==='question-preset'){S.practice.size=Number(button.dataset.size);render();return;}
    if(a==='resume-exam')return request('resume_exam');
    if(a==='discard-draft'){confirmModal('Discard this saved exam?','The local saved session and its written responses will be removed. Your finished results and Anki cards stay unchanged.',async()=>{await request('discard_draft');S.data.draft=null;render();});return;}
    if(a==='export-result'){const r=await request('export_result',{result_id:button.dataset.id});if(r.saved)toast('Result exported without written answers.');return;}
    if(a==='review-all'){const r=await request('review_misses',{id:button.dataset.exam||S.selected,result_id:button.dataset.id,filter:'all'});if(r.empty)toast(r.message);else closeModal();return;}
    if(a==='pip-study'){
      let groups=[];if(S.data.suite)groups=await request('suite_groups');
      const plans=S.data.state.exams.filter(e=>!e.archived);
      if(!groups.some(g=>g.available)&&!plans.length){toast('Pin a study group on the study desk or create an exam plan first.');return;}
      const chosen=plans.some(e=>e.id===S.selected)?S.selected:groups.find(g=>g.available)?'group:'+groups.find(g=>g.available).id:plans[0]?.id;
      const material=`<label class="es-field suite-pip-material">Study material<select id="suite-pip-material">${groups.length?'<optgroup label="Active study groups">'+groups.map(g=>`<option value="group:${E(g.id)}" ${chosen==='group:'+g.id?'selected':''} ${g.available?'':'disabled'}>${E(g.name)}${g.available?'':' · unavailable'}</option>`).join('')+'</optgroup>':''}${plans.length?'<optgroup label="Saved exam plans">'+plans.map(e=>`<option value="${E(e.id)}" ${chosen===e.id?'selected':''}>${E(e.name)}</option>`).join('')+'</optgroup>':''}</select><small>Groups use their existing folders and subdecks. No duplicate exam plan is created. Practice remains separate from scheduled reviews.</small></label>`;
      modal('A focused session with Pip' ,`<div class="suite-pip-intro"><div class="suite-pip-avatar">${sprout}</div><div><span class="es-label">Study with your existing material</span><h3>Recall first. Then take the next step.</h3><p>Learned cards get targeted retrieval: explain, contrast or apply. Recent successes are deprioritized.</p></div></div>${material}<label class="es-field suite-pip-count">Questions in this session<input id="es-pip-count" type="number" value="30" min="1" max="500"><small>Request 1–500. The existing engine selects eligible cards from this exam’s scope.</small></label><label class="es-check-row suite-pip-choice"><input id="es-teach-new" type="checkbox" checked><span>Introduce new cards into Anki<small>After reveal, choose Again / Hard / Good / Easy. This changes the normal learning schedule for currently NEW cards only. Learned-card rehearsal, mocks and pet interactions never reschedule.</small></span></label><div id="suite-pip-mode" class="suite-session-safety" data-kind="learning" role="status">${lock}<div><strong>New-card learning is enabled</strong><p>Only currently NEW cards can receive a real Anki rating, after you reveal. Existing learned cards remain rehearsal.</p></div></div><details class="suite-result-method"><summary>Learning, limits and saving a session</summary><p>Explicit new learning may exceed today's new-card quota without changing the deck's limits. Remaining learning steps are completed in normal Anki review. Uncheck to make the entire session rehearsal-only.</p><p>Save & close in the session stores your unfinished work locally. Timed exams continue counting while closed. Petting and watering do not change readiness or effort points.</p></details>`,`<button data-action="close-modal">Cancel</button><button class="es-primary" data-action="begin-pip-study">Start Pip Study →</button>`,null,'pip');return;
    }
    if(a==='begin-pip-study'){
      const size=Number(root.querySelector('#es-pip-count')?.value),teach_new=root.querySelector('#es-teach-new')?.checked===true;
      if(!Number.isInteger(size)||size<1||size>500)throw new Error('Choose 1–500 questions.');
      const selected=root.querySelector('#suite-pip-material')?.value||S.selected;
      await request('pip_study',{...(selected?.startsWith('group:')?{group_id:selected.slice(6)}:{id:selected}),size,teach_new});closeModal();return;
    }
    if(a==='new')return newExam();
    if(a==='edit')return editExam();
    if(a==='refresh')return fetchPlan();
    if(a==='toggle-past'){S.past=!S.past;return render();}
    if(a==='cancel-form'){if(S.draft)confirmModal('Leave this exam?','Your unsaved changes will be discarded.',()=>{S.draft=null;markDirty(false);render();});return;}
    if(a==='next-step'){validateStep();S.step++;S.draft.step=S.step;focusNextStep=true;render();return;}
    if(a==='back-step'){S.step--;S.draft.step=S.step;focusNextStep=true;render();return;}
    if(a==='study-mode'){S.draft.mode=button.dataset.value;markDirty();render();return;}
    if(a==='weekday'){const n=Number(button.dataset.day);S.draft.weekdays=S.draft.weekdays.includes(n)?S.draft.weekdays.filter(d=>d!==n):[...S.draft.weekdays,n].sort();markDirty();render();return;}
    if(a==='suggest'){const result=await request('suggest',{topics:S.draft.topics});S.suggestions=result.ids;renderDeckList();toast(result.ids.length?'Matching deck names are marked. Confirm their actual coverage before selecting.':'No deck names matched. Select the correct decks yourself.');return;}
    if(a==='apply-bulk'&&S.draft){
      const kind=button.dataset.kind, control=root.querySelector(`[data-bulk="${kind}"]`);
      const raw=control?.value?.trim(), value=Number(raw);
      if(!S.draft.scopes.length)throw new Error('Select at least one deck first.');
      if(!raw||!Number.isFinite(value))throw new Error('Enter a valid number before applying it.');
      if(kind==='confidence'&&(!Number.isInteger(value)||value<1||value>5))throw new Error('Confidence must be a whole number from 1 to 5.');
      if(kind==='emphasis'&&(value<0||value>1000))throw new Error('Emphasis must be from 0 to 1000.');
      for(const scope of S.draft.scopes)scope[kind==='confidence'?'confidence':'weight']=value;
      markDirty();renderDeckList();toast(`Applied ${kind==='confidence'?'confidence':'emphasis'} to all selected decks.`);return;
    }
    if(a==='save'){
      validateStep();const data={...S.draft};delete data.step;
      const result=await request('save_exam',data);acceptState(result);S.selected=result.exam_id;S.plan={plan:result.plan,warnings:result.warnings||[]};S.draft=null;markDirty(false);S.view='overview';render();toast('Your exam is saved. One step at a time.');return;
    }
    if(a==='archive'){
      const e=exam();const result=await request('archive_exam',{id:e.id,archived:!e.archived});acceptState(result);S.past=true;render();return;
    }
    if(a==='delete'){const e=exam();confirmModal('Delete this exam?',`“${e.name}” and its local practice history will be removed. Your Anki decks and cards will not change.`,async()=>{const result=await request('delete_exam',{id:e.id});acceptState(result);S.selected=null;S.plan=null;chooseInitial();render();fetchPlan();});return;}
    if(a==='practice-kind'){S.practice.kind=button.dataset.value;render();return;}
    if(a==='prepare'){
      const p=S.practice;
      if(!Number.isInteger(Number(p.size))||p.size<1||p.size>500)throw new Error('Choose 1–500 practice cards.');
      if(!Number.isInteger(Number(p.minutes))||p.minutes<0||p.minutes>720)throw new Error('Use a time limit from 0 to 720 minutes.');
      const result=await request('prepare',{id:S.selected,...p});sampleModal(result);return;
    }
    if(a==='toggle-rows'){S.allRows=!S.allRows;render();return;}
    if(a==='back-to-anki')return request('back_to_anki');
    if(a==='suite-focus'){const e=exam();if(e){await request('suite_focus',{id:e.id});toast('Exam folders are now available on the study desk.');}return;}
    if(a==='suite-native'){await request('suite_native',{command:button.dataset.command});return;}
    if(a==='study'||a==='focus')return request(a,{id:S.selected,deck_id:Number(button.dataset.deck),size:Number(button.dataset.size)||20});
    if(a==='browse')return request('browse',{id:S.selected,deck_id:Number(button.dataset.deck)});
    if(a==='review-misses'){const r=await request('review_misses',{id:button.dataset.exam||S.selected,result_id:button.dataset.id});if(r.empty)toast(r.message);else closeModal();return;}
    if(a==='result'){const r=S.data.state.history.find(x=>x.id===button.dataset.id);if(r)resultModal(r);return;}
    if(a==='theme')return saveSettings({theme:button.dataset.value});
    if(a==='export'){const result=await request('export');if(result.saved)toast('Exam plans and local results exported.');return;}
    if(a==='close-modal'||a==='dismiss-dialog'){closeModal();return;}
    if(a==='confirm-modal'){const callback=modalCallback;closeModal();if(callback)return callback();return;}
  }
  function handleField(target) {
    if(target.id==='suite-result-filter'){resultFilter=target.value;resultPage=0;paintResultRows();return;}
    if(target.id==='es-teach-new'){updatePipMode();return;}
    if(target.dataset.field&&S.draft){S.draft[target.dataset.field]=target.type==='number'?Number(target.value):target.value;markDirty();}
    if(target.dataset.special==='deck-search'){S.deckSearch=target.value;renderDeckList();}
    if(target.dataset.special==='choose-deck'&&S.draft){
      const id=Number(target.dataset.id),d=S.data.decks.find(x=>x.id===id);
      if(target.checked&&d&&!S.draft.scopes.some(s=>s.deck_id===id)){
        if(S.draft.scopes.length>=100){target.checked=false;toast('An exam can contain up to 100 deck selections.');return;}
        S.draft.scopes.push({deck_id:id,name:d.name,confidence:3,weight:1});
      }else if(!target.checked)S.draft.scopes=S.draft.scopes.filter(s=>s.deck_id!==id);
      markDirty();renderDeckList();
    }
    if(['confidence','emphasis'].includes(target.dataset.special)&&S.draft){const s=S.draft.scopes.find(s=>s.deck_id===Number(target.dataset.id));if(s)s[target.dataset.special==='confidence'?'confidence':'weight']=Number(target.value);markDirty();}
    if(target.dataset.practice){S.practice[target.dataset.practice]=target.type==='checkbox'?target.checked:target.type==='number'?Number(target.value):target.value;if(target.dataset.practice==='weighting')render();}
    if(target.dataset.weight)S.practice.weights[target.dataset.weight]=Number(target.value);
    updateSetupSummary();updatePracticeSummary();
    if(target.dataset.setting){saveSettings({[target.dataset.setting]:target.type==='checkbox'?target.checked:Number(target.value)}).catch(e=>{toast(e.message);render();});}
  }
  async function init() {
    root=document.getElementById('es-app');if(!root)return;
    document.documentElement.classList.add('es-host');
    root.addEventListener('keydown',e=>{if(e.key==='Escape'&&railOpen&&!root.querySelector('#es-modal')?.open){railOpen=false;root.dataset.railOpen='false';const b=root.querySelector('.suite-exams-toggle');b?.setAttribute('aria-expanded','false');if(b)b.querySelector('b').textContent='+';b?.focus({preventScroll:true});e.preventDefault();}});
    root.addEventListener('pip-preference',e=>{const animate=e.detail?.animate;if(typeof animate==='boolean')saveSettings({animate_pip:animate}).catch(err=>toast(err.message));});
    root.addEventListener('click',async e=>{
      const b=e.target.closest('button[data-action]');if(!b||!root.contains(b)||b.disabled)return;
      const hadFocus=document.activeElement===b||b.contains(document.activeElement);
      activeActionElement=hadFocus?b:null;b.disabled=true;
      try{await action(b);}catch(error){toast(error.message);}finally{
        if(b.isConnected){b.disabled=false;if(hadFocus&&document.activeElement===document.body)b.focus({preventScroll:true});}
        if(activeActionElement===b)activeActionElement=null;
        if(b.dataset.action==='result-page')paintResultRows();
      }
    });
    // Text/number edits use input; selects and checkboxes use change, avoiding
    // duplicate bridge writes and preserving keyboard focus while typing.
    root.addEventListener('input',e=>{if(e.target.matches('input:not([type="checkbox"]),textarea'))handleField(e.target);});
    root.addEventListener('change',e=>{if(e.target.matches('select,input[type="checkbox"]'))handleField(e.target);});
    try{S.data=await request('load');chooseInitial();render();fetchPlan();}
    catch(error){root.innerHTML=`<div class="es-empty">${sprout}<h1>Couldn’t open your exam space.</h1><p>${E(error.message)}</p><p>Close this window and reopen the planner from Anki’s Tools menu.</p></div>`;}
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
