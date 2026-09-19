/* Atelier 1.0.3 — isolated study desk. No framework or external requests. */
(() => {
  'use strict';
  const ready = fn => document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', fn, {once:true}) : fn();
  ready(() => {
    const host = document.getElementById('atelier-root'), bootstrap = document.getElementById('atelier-bootstrap');
    if (!host || !bootstrap || host.shadowRoot) return;
    let boot;
    try { boot = JSON.parse(bootstrap.textContent); } catch (_) { return; }
    const template = document.getElementById('atelier-style');
    if (!template || !window.AtelierModel) return;
    const Model = window.AtelierModel;
    if(boot.integrations && boot.integrations.onigiri===false && boot.integrations.metadata_checked!==false && !(boot.integrations.makeovers||[]).length && boot.settings.visual_owner==='ask'){
      boot.settings={...boot.settings,visual_owner:'atelier',mode:'workspace'};
      if(boot.demo)boot.demo.settings={...boot.settings};
    }

    // Place only OUR host outside the body. This avoids third-party body
    // transforms, flex/grid, overflow locks, zoom inheritance and positioning.
    // No native or Onigiri nodes are moved, cloned or deleted.
    document.documentElement.appendChild(host);
    const shadow = host.attachShadow({mode:'open'});
    shadow.append(template.content.cloneNode(true));
    const app = document.createElement('div'); app.className = 'app'; shadow.append(app);
    const frame = document.createElement('div'); frame.className = 'frame'; app.append(frame);
    const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const icons = {
      controls:'<rect x="6" y="2" width="12" height="20" rx="4"/><path d="M9 8h6m-3-3v6"/><circle cx="10" cy="15" r="1"/><circle cx="14" cy="18" r="1"/>',
      grid:'<rect x="3" y="3" width="7" height="7" rx="1.4"/><rect x="14" y="3" width="7" height="7" rx="1.4"/><rect x="3" y="14" width="7" height="7" rx="1.4"/><rect x="14" y="14" width="7" height="7" rx="1.4"/>',
      folder:'<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
      layers:'<path d="m12 3 9 5-9 5-9-5zM3 12l9 5 9-5M3 16l9 5 9-5"/>',
      star:'<path d="m12 3 2.8 5.7 6.3.9-4.6 4.5 1.1 6.3-5.6-3-5.6 3 1.1-6.3L3 9.6l6.2-.9z"/>',
      clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
      plus:'<path d="M12 5v14M5 12h14"/>',
      search:'<circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/>',
      arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
      chevron:'<path d="m9 5 7 7-7 7"/>',
      down:'<path d="m5 9 7 7 7-7"/>',
      more:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
      check:'<path d="m5 12 4 4L19 6"/>',
      close:'<path d="m6 6 12 12M6 18 18 6"/>',
      list:'<path d="M8 6h13M8 12h13M8 18h13M3 6h.1M3 12h.1M3 18h.1"/>',
      palette:'<path d="M12 3a9 9 0 1 0 0 18h1.5a2 2 0 0 0 1-3.7 1.5 1.5 0 0 1 .8-2.8H17a4 4 0 0 0 4-4c0-4.2-4-7.5-9-7.5Z"/><circle cx="7" cy="10" r=".6"/><circle cx="10" cy="6.5" r=".6"/><circle cx="15" cy="7" r=".6"/>',
      move:'<path d="M12 3v18M3 12h18m-12-6 3-3 3 3m-6 12 3 3 3-3M6 9l-3 3 3 3m12-6 3 3-3 3"/>',
      edit:'<path d="m15 4 5 5M4 20l5-1L21 7a2.1 2.1 0 0 0-5-4L4 15z"/>',
      info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
      play:'<path d="m8 5 11 7-11 7z"/>',
      import:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
      menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
      chart:'<path d="M4 20h17M7 16V9M12 16V4M17 16v-5"/>',
      shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8 12 3 3 5-6"/>',
      refresh:'<path d="M20 8a8 8 0 0 0-14-3L3 8m0-5v5h5M4 16a8 8 0 0 0 14 3l3-3m0 5v-5h-5"/>',
      home:'<path d="m3 11 9-8 9 8M5 10v11h5v-7h4v7h5V10"/>',
      external:'<path d="M14 3h7v7m0-7L10 14M10 5H4v15h15v-6"/>',
      book:'<path d="M12 6c-3-2-6-2-9-1v14c3-1 6-1 9 1 3-2 6-2 9-1V5c-3-1-6-1-9 1zm0 0v14"/>'
    };
    Object.assign(icons, {"browse": "<rect x=\"3\" y=\"3\" width=\"14\" height=\"17\" rx=\"2\"/><path d=\"M7 7h6M7 11h4\"/><circle cx=\"16\" cy=\"16\" r=\"4\"/><path d=\"m19 19 3 3\"/>", "sync": "<path d=\"M7 3 3 7l4 4M3 7h13a4 4 0 0 1 4 4M17 21l4-4-4-4M21 17H8a4 4 0 0 1-4-4\"/>", "reload": "<path d=\"M20 6v6h-6M20 12a8 8 0 1 0-2 5\"/>", "export": "<path d=\"M12 15V3m-5 5 5-5 5 5M4 15v6h16v-6\"/>", "sliders": "<path d=\"M4 6h4m6 0h6M4 12h10m6 0h0M4 18h4m6 0h6\"/><circle cx=\"11\" cy=\"6\" r=\"3\"/><circle cx=\"17\" cy=\"12\" r=\"3\"/><circle cx=\"11\" cy=\"18\" r=\"3\"/>", "filter": "<path d=\"M3 4h18l-7 8v7l-4 2v-9z\"/>", "profiles": "<circle cx=\"9\" cy=\"7\" r=\"3\"/><path d=\"M3 21v-3a6 6 0 0 1 12 0v3M16 4a3 3 0 0 1 0 6m2 5a5 5 0 0 1 3 5\"/>", "undo": "<path d=\"M9 4 3 10l6 6M3 10h12a6 6 0 0 1 0 12\"/>", "redo": "<path d=\"m15 4 6 6-6 6m6-6H9a6 6 0 0 0 0 12\"/>", "fullscreen": "<path d=\"M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5\"/>", "media": "<rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\"/><circle cx=\"8\" cy=\"8\" r=\"1.5\"/><path d=\"m3 17 5-5 4 4 4-6 5 7\"/>", "database": "<ellipse cx=\"12\" cy=\"5\" rx=\"8\" ry=\"3\"/><path d=\"M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0\"/>", "blank": "<rect x=\"4\" y=\"3\" width=\"16\" height=\"18\" rx=\"2\"/><path d=\"M8 16h8\"/>", "updates": "<path d=\"M12 16V3m-5 5 5-5 5 5M3 16v5h18v-5\"/><path d=\"m7 17 2 2 3-3\"/>", "note-types": "<rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\"/><path d=\"M3 9h18M9 9v12M13 13h4M13 17h4\"/>", "addons": "<path d=\"M9 3H4v6H2a2 2 0 0 0 0 4h2v7h7v-2a2 2 0 0 1 4 0v2h6v-7h-2a2 2 0 0 1 0-4h2V3h-6v2a3 3 0 0 1-6 0z\"/>"});
    const icon = (name, size=16, fill=false) => `<svg class="icon" data-icon="${esc(name)}" width="${size}" height="${size}" viewBox="0 0 24 24" fill="${fill?'currentColor':'none'}" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.layers}</svg>`;
    const assetBase=String(boot.assetBase||boot.suiteAssets?.replace(/\/sprout\/web\/?$/,'/web')||'/_addons/daedalus_atelier/web').replace(/\/$/,'');
    const brand = `<img class="brand-mark" src="${esc(assetBase+'/atelier-mark-1.0.3.png')}" alt="" aria-hidden="true" draggable="false">`;
    const folderArt = isFolder => isFolder ? `<svg viewBox="0 0 54 46" fill="none" aria-hidden="true"><path d="M5 8a4 4 0 0 1 4-4h12l5 5h20a4 4 0 0 1 4 4v23a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4Z" fill="currentColor" opacity=".32"/><path d="M10 12h35v21H10z" fill="currentColor" opacity=".32"/><path d="M4 18a4 4 0 0 1 4-4h39a4 4 0 0 1 4 4l-3 20a4 4 0 0 1-4 4H10a4 4 0 0 1-4-4Z" fill="currentColor" opacity=".84"/><path d="M9 14h37a4 4 0 0 1 4 3" stroke="white" opacity=".45"/><path d="M17 29h20" stroke="var(--panel)" stroke-width="1.4" opacity=".5"/></svg>` : `<svg viewBox="0 0 54 46" fill="none" aria-hidden="true"><rect x="11" y="3" width="30" height="36" rx="4" transform="rotate(12 26 21)" fill="currentColor" opacity=".28"/><rect x="10" y="6" width="31" height="36" rx="4" transform="rotate(-7 25 24)" fill="currentColor" opacity=".8"/><path d="m17 18 17-2m-16 8 13-2m-12 8 8-1" stroke="var(--panel)" stroke-width="1.5" opacity=".7"/><path d="m12 9 24-3" stroke="white" opacity=".4"/></svg>`;
    icons.back = '<path d="M20 12H4m6-6-6 6 6 6"/>';
    icons.up = '<path d="M12 20V4m-6 6 6-6 6 6"/>';
    icons.calendar = '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4M17 3v4M3 10h18M7 14h3M14 14h3M7 17h3"/>';
    icons.focus = '<path d="M8 3H5a2 2 0 0 0-2 2v3m13-5h3a2 2 0 0 1 2 2v3M3 16v3a2 2 0 0 0 2 2h3m8 0h3a2 2 0 0 0 2-2v-3"/><path d="m8 12 3 3 5-6"/>';
    const THEMES = Array.isArray(boot.worlds)&&boot.worlds.length ? boot.worlds.map(w=>[w.id,w.name,w.description]) : [["obsidian", "Obsidian", "Prismatic stone. Quiet violet light."], ["glacier", "Glacier", "Glacial facets. Polar light."], ["rose", "Rose Quartz", "Rose-gold arches. A garden in bloom."], ["bloom", "Bloom", "Botanical ink. Lilac conservatory glass."], ["linen", "Linen", "Bookcloth. Library light. Brass rules."], ["matcha", "Matcha", "Bamboo. Shoji light. Glazed ceramic."], ["midnight", "Midnight", "Precise geometry. Teal city lights."], ["peach", "Peach", "Sun-warmed plaster. Soft desert contours."], ["forest", "Forest", "Layered pines. Moss. Filtered daylight."], ["tidal", "Tidal", "Sea-glass surfaces. Flowing ocean contours."], ["ember", "Ember", "Basalt strata. Copper seams. Warm light."], ["celestial", "Celestial", "A silver horizon. Deep orbital night."]];
    const defaults = {native_surfaces:true,theme:'obsidian',mode:'workspace',density:'comfortable',motion:true,chrome:false,view:'grid',sort:'name',review_style:'adaptive',review_width:'standard',surface_revision:1,shared_theme:true,match_sprout:true,visual_owner:'ask',ambience:true,review_context:'compact',companion_shortcuts:false,acknowledged_makeovers:[]};
    const examKey = s => [...new Set(s.deck_ids)].sort().join(',');
    const normalizeProfile = p => {
      const out={favorites:[],folders:[],colors:{},last_location:'0',last_studied:'0',studies:[],focus_enabled:false,selected_study:'all',recent_locations:[],recent_added:[],home_layout:{enabled:false,columns:3,items:[]},...p};
      out.native_widgets=window.AtelierNativeWidgets?.normalize(out.native_widgets)||{items:[]};
      out.native_widget_note=typeof out.native_widget_note==='string'?out.native_widget_note:'';
      const seen=new Set();out.studies=out.studies.map(s=>{const key=examKey(s);const active=!!s.active&&!seen.has(key);if(active)seen.add(key);return {...s,active};});
      if(!out.studies.some(s=>s.active&&s.id===out.selected_study))out.selected_study='all';
      return out;
    };
    const state = {config:{...defaults,...boot.settings},profile:normalizeProfile(boot.profile),nodes:[],map:new Map(),childMap:new Map(),
      toolsGroup:'all',page:boot.ui?.page || 'desk',location:boot.ui?.location || '0',filter:'all',query:'',limit:60,treeLimit:240,
      expanded:new Set(),mobile:false,loaded:false,dialog:null,dialogData:{},busy:false,current:'0',studied:'',
      authoring:boot.authoring||{available:false},suite:boot.suite||{available:false,plans:[]},history:[],forward:[],recentTab:'viewed',saveStatus:'Saved',failure:'',peek:new Set(),collapsedLectures:new Set(),boardLimit:100,menu:null};
    if (state.config.mode === 'hybrid') state.config.mode = 'workspace';
    const pending = new Map(); let sequence = 0, toastTimer, uiTimer, lastKeyCapture = false;
    let configQueue = Promise.resolve(), configRevision = 0, configSaved = {...state.config}, configPending = 0;
    let prefQueue = Promise.resolve(), prefRevision = 0, loadRevision = 0, focusBeforeDialog = null, surfaceNavigation = 0;
    const now = () => boot.preview && boot.demoNow ? new Date(boot.demoNow) : new Date();
    const request = (action, data = {}) => {
      if (boot.preview) return demoRequest(action, data);
      return new Promise((resolve,reject) => {
        const id = `r${++sequence}`;
        const timeout = setTimeout(() => {pending.delete(id); reject(new Error('Anki has not responded yet. Try Refresh after its current operation finishes.'));},20000);
        pending.set(id,{resolve,reject,timeout});
        const send = retries => {
          if (!pending.has(id)) return;
          if (typeof window.pycmd === 'function') window.pycmd(`atelier:v1:${boot.token}:`+JSON.stringify({id,action,data}));
          else if (retries < 60) setTimeout(() => send(retries+1),50);
          else {clearTimeout(timeout);pending.delete(id);reject(new Error('The Anki bridge is unavailable. Your original home is still available.'));}
        }; send(0);
      });
    };
    function receive(payload) {
      if (payload.token !== boot.token) return;
      const p = pending.get(payload.id); if (!p) return;
      pending.delete(payload.id); clearTimeout(p.timeout);
      payload.error ? p.reject(new Error(payload.error)) : p.resolve(payload.result);
    }
    const sproutAvailable = () => !!(boot.integrations?.exam_sprout || window.ExamSproutCountdown || document.getElementById('es-countdowns'));
    const due = n => n ? n.review + n.learn : 0;
    const fmt = n => Number(n || 0).toLocaleString();
    const favorite = n => state.profile.favorites.includes(n.id);
    const isFolder = n => !!(n?.children?.length || state.profile.folders.includes(n?.id));
    const nicePath = p => String(p || '').split('::').join(' › ');
    const byName = Model.compareNames;
    const children = id => state.childMap.get(id) || [];
    const hash = str => {let h=0;for(const c of str) h=((h<<5)-h+c.charCodeAt(0))|0;return h;};
    const tone = n => ['violet','blue','rose','green','amber','cyan'].includes(state.profile.colors[n.id]) ? state.profile.colors[n.id] : ['violet','blue','green','amber','rose','cyan'][Math.abs(hash(n.path))%6];
    const scope = () => Model.scope(state.nodes,state.profile);
    const btn = (a,label,ico,cls='secondary',extra='') => `<button type="button" class="${cls}" data-action="${a}" ${extra}>${ico?icon(ico,16):''}<span>${label}</span></button>`;
    const ib = (a,label,ico,extra='',cls='') => `<button type="button" class="icon-button ${cls}" data-action="${a}" title="${esc(label)}" aria-label="${esc(label)}" ${extra}>${icon(ico,17)}</button>`;
    const getScroll = () => ({main:shadow.querySelector('.main')?.scrollTop||0,side:shadow.querySelector('.side-scroll')?.scrollTop||0});
    let companionSent='';
    let home=null, nativeWidgets=null; let bodyState = null, undoStudy = null; const quickPending=new Set();
    const exactExams=n=>state.profile.studies.filter(s=>s.active&&s.deck_ids.length===1&&s.deck_ids[0]===n.id);
    const inExam=n=>Model.belongs(state.nodes,Model.roots(state.nodes,state.profile.studies.filter(s=>s.active).flatMap(s=>s.deck_ids)),n.id);
    const examButton=n=>btn('quick-exam',exactExams(n).length?'Exam active':inExam(n)?'Pin as own exam':'Set as exam',exactExams(n).length?'check':'focus',`exam-pin ${exactExams(n).length?'is-active':''}`,`data-id="${n.id}" aria-pressed="${!!exactExams(n).length}" title="${exactExams(n).length?'Remove this exam from active studies':'Add this folder as an upcoming exam in one click'}"`);
    function setHost() {
      host.dataset.owner=state.config.visual_owner||'ask';
      host.dataset.theme=state.config.theme;host.dataset.ambience=String(state.config.ambience!==false);host.dataset.density=state.config.density;host.dataset.motion=state.config.motion?'on':'off';
      const workspace = state.config.mode !== 'native' || state.config.visual_owner==='ask';
      host.dataset.workspace = workspace ? 'true' : 'false';
      let sheet = document.getElementById('atelier-host-style');
      if (!sheet) {sheet=document.createElement('style');sheet.id='atelier-host-style';document.head.append(sheet);}
      // This sheet targets only our host. Never tint body/html or game typography.
      const css = '#atelier-root{all:initial!important;display:block!important;position:fixed!important;z-index:2147483000!important;box-sizing:border-box!important;isolation:isolate!important;transform:none!important;direction:ltr!important;}' +
        (workspace ? '#atelier-root{inset:0!important;left:0!important;right:0!important;top:0!important;bottom:0!important;width:auto!important;height:auto!important;inline-size:auto!important;block-size:auto!important;max-width:none!important;max-height:none!important;}' : '#atelier-root{inset:auto 20px 20px auto!important;width:min(430px,calc(100vw - 32px))!important;height:auto!important;}');
      if (sheet.textContent !== css) sheet.textContent=css;
      if (workspace && !bodyState) {
        bodyState = {inert:document.body.hasAttribute('inert'),hidden:document.body.getAttribute('aria-hidden')};
        document.body.setAttribute('inert','');document.body.setAttribute('aria-hidden','true');
      } else if (!workspace && bodyState) {
        if (!bodyState.inert) document.body.removeAttribute('inert');
        bodyState.hidden === null ? document.body.removeAttribute('aria-hidden') : document.body.setAttribute('aria-hidden',bodyState.hidden);
        bodyState=null;
      }
      window.AtelierCohesion?.sync({host,config:state.config,layoutEnabled:!!state.profile.home_layout?.enabled});
      window.AtelierPaint?.ready(state.config.mode);
      home?.sync();
      const companion=window.AtelierOwnership?.get();if(companion&&state.config.visual_owner==='onigiri'){const key=JSON.stringify(companion);if(key!==companionSent){companionSent=key;request('companion_palette',companion).catch(()=>{companionSent='';});}}
      nativeWidgets?.theme();
      frame.inert=!!(state.dialog || state.mobile);
      if (state.mobile) frame.inert=false; // Drawer focus is trapped below; main is inert separately.
      const computed=getComputedStyle(host);
      window.dispatchEvent(new CustomEvent('atelier:theme-change',{detail:{theme:state.config.theme,active:workspace&&state.config.visual_owner==='atelier',tokens:Object.fromEntries(['bg','text','accent','panel','muted','line'].map(k=>[k,computed.getPropertyValue('--'+k).trim()]))}}));
    }
    function updateThemeControls() {
      for (const tile of shadow.querySelectorAll('[data-theme-choice]')) {
        const selected=tile.dataset.themeChoice===state.config.theme;tile.classList.toggle('selected',selected);tile.setAttribute('aria-pressed',String(selected));
        const check=tile.querySelector('.theme-check');if(check)check.hidden=!selected;
      }
      for (const toggle of shadow.querySelectorAll('[data-setting]')) toggle.setAttribute('aria-checked',String(!!state.config[toggle.dataset.setting]));
      if(state.dialog==='appearance')filterWorlds(state.dialogData.worldFilter||'all');
      const status=shadow.getElementById('save-state');if(status)status.textContent=state.saveStatus;
      const current=THEMES.find(t=>t[0]===state.config.theme);
      const world=(boot.worlds||[]).find(w=>w.id===state.config.theme);
      const name=current?.[1]||'Your world',title=world?.title||'A place to focus';
      const text=(el,value)=>{if(el&&el.textContent!==value)el.textContent=value;};
      text(shadow.querySelector('.appearance-link small'),name+' · '+THEMES.length+' worlds');
      // The page remains mounted during a theme change. Update semantic copy
      // alongside CSS tokens, on optimistic changes, saved state AND rollback.
      for(const preview of shadow.querySelectorAll('.world-window')){
        preview.dataset.world=state.config.theme;
        preview.setAttribute('aria-label',name+' — '+title+'. Change study world');
        preview.title=name+' — '+title;
        text(preview.querySelector('.world-window-label small'),name);
        text(preview.querySelector('.world-window-label strong'),title);
      }
      for(const [id,key] of Object.entries({'setting-density':'density','setting-review-style':'review_style','setting-review-width':'review_width','setting-review-context':'review_context','atelier-sort':'sort'})){
        const select=shadow.getElementById(id);if(select&&select.value!==String(state.config[key]))select.value=state.config[key];
      }
    }
    function updateConfig(patch, redraw=false) {
      const revision=++configRevision;configPending++;
      state.config={...state.config,...patch};state.saveStatus='Saving…';setHost();updateThemeControls();
      if(redraw)render();
      const operation=configQueue.then(()=>request('settings',patch)).then(saved=>{
        configSaved={...defaults,...saved};
        if(revision===configRevision){state.config={...configSaved};state.saveStatus='Saved';setHost();updateThemeControls();}
        return true;
      }).catch(e=>{
        if(revision===configRevision){state.config={...configSaved};state.saveStatus='Not saved — try again';setHost();updateThemeControls();if(redraw)render();}
        announce(e.message,true);return false;
      }).finally(()=>{configPending--;});
      configQueue=operation.then(()=>{});return operation;
    }
    function updatePref(data, redraw=true) {
      prefRevision++;
      const op=prefQueue.then(()=>request('preference',data)).then(p=>{
        state.profile=normalizeProfile(p);if(redraw)render();return true;
      }).catch(e=>{announce(e.message,true);return false;});
      prefQueue=op.then(()=>{});return op;
    }
    function remember() {
      clearTimeout(uiTimer);uiTimer=setTimeout(()=>request('ui',{page:state.page,location:state.location,filter:state.filter,query:state.query}).catch(()=>{}),150);
    }
    async function openWidgets() {
      const ticket = ++surfaceNavigation;
      if (!nativeWidgets) {
        announce('Atelier widgets could not load. Restart Anki, then use Tools → Atelier → Open Atelier widgets. The original provider page has not been substituted.', true);
        return false;
      }
      closeDialog();state.mobile=false;
      if (state.config.mode === 'native') {
        const saved=await updateConfig({mode:'workspace'},true);
        if (!saved || ticket!==surfaceNavigation) return false;
      }
      if (ticket!==surfaceNavigation) return false;
      go('widgets');
      // Keyboard focus lands at the destination, not a removed provider button.
      requestAnimationFrame(()=>shadow.querySelector('.nw-header h1')?.focus({preventScroll:true}));
      return true;
    }
    async function openProvider() {
      const ticket=++surfaceNavigation;
      closeDialog();state.mobile=false;
      const saved=await updateConfig({mode:'native'},true);
      return saved && ticket===surfaceNavigation;
    }
    function stateLocation(){return {page:state.page,location:state.location,query:state.query,filter:state.filter};}
    function go(page,location='0',history=true) {
      surfaceNavigation++;
      closeMenu(false);
      if(location!=='0'&&!state.map.has(location))return;
      if(history && (state.page!==page || state.location!==location || state.query)){state.history.push(stateLocation());state.history=state.history.slice(-80);state.forward=[];}
      state.page=page;state.location=location;state.query='';state.filter='all';state.limit=60;state.mobile=false;
      let n=state.map.get(location);const seen=new Set();while(n&&!seen.has(n.id)){seen.add(n.id);state.expanded.add(n.id);n=state.map.get(n.parent);}
      render({resetMain:true});remember();
      if(location!=='0')updatePref({key:'last_location',value:location},false);
    }
    function travel(back) {
      const source=back?state.history:state.forward,target=back?state.forward:state.history;
      if(!source.length)return;
      let item=source.pop();while(item&&item.location!=='0'&&!state.map.has(item.location))item=source.pop();if(!item)return;target.push(stateLocation());Object.assign(state,item);state.mobile=false;render({resetMain:true});remember();
    }
    function sidebarTree() {
      const stack=sortedNodes(children('0')).reverse().map(n=>({n,depth:0})),output=[];let count=0;
      while(stack.length && count<state.treeLimit){
        const {n,depth}=stack.pop();count++;
        const nested=children(n.id),expanded=state.expanded.has(n.id),selected=state.page==='library'&&state.location===n.id;
        output.push(`<div class="tree-row ${selected?'selected':''}" style="--depth:${Math.min(depth,8)}" data-node="${n.id}" data-drop="${n.filtered?'':n.id}">
          ${nested.length?`<button type="button" class="tree-toggle" data-action="expand" data-id="${n.id}" aria-label="${expanded?'Collapse':'Expand'} ${esc(n.name)}" aria-expanded="${expanded}">${icon(expanded?'down':'chevron',12)}</button>`:'<span class="tree-spacer"></span>'}
          <button type="button" class="tree-open" data-action="navigate" data-id="${n.id}" title="${esc(nicePath(n.path))}" ${selected?'aria-current="page"':''}><span class="tree-art tone-${tone(n)}">${folderArt(isFolder(n))}</span><span class="tree-name">${esc(n.name)}</span>${nested.length?`<small>${nested.length}</small>`:''}</button>${ib('quick-exam',exactExams(n).length?'Remove '+n.name+' from active exams':'Set '+n.name+' as active exam',exactExams(n).length?'check':'plus',`data-id="${n.id}" aria-pressed="${!!exactExams(n).length}"`,exactExams(n).length?'tree-active':'tree-pin')}</div>`);
        if(expanded)for(const child of sortedNodes(nested).reverse())stack.push({n:child,depth:depth+1});
      }
      return output.join('')+(stack.length?btn('tree-more','Show more folders','down','quiet'):'' );
    }
    function sidebar() {
      const f=scope(),recent=state.profile.recent_locations.map(id=>state.map.get(id)).filter(Boolean).slice(0,3);
      const badge=f.enabled?fmt(due(f.totals)):'',chosen=f.active.find(s=>s.id===state.profile.selected_study),scopeName=chosen?.name||(f.active.length?'All active studies':'All folders'),scopeCount=f.selected.length;
      return `<aside class="sidebar ${state.mobile?'mobile-open':''}" aria-label="Folder navigation">
        <div class="brand-row"><button type="button" class="brand" data-action="home" aria-label="Atelier study desk">${brand}<span><strong>atelier</strong><small>Your space to learn · ${esc(boot.version)}</small></span></button>${ib('close-nav','Close navigation','close','','drawer-close')}</div>
        <p class="brand-promise">Create, organize and study in one calm workspace.</p>
        <nav class="nav-group" aria-label="Main navigation">
          <span class="nav-section-label">LEARN</span>
          ${btn('home','Study desk','home',`nav-row ${state.page==='desk'?'active':''}`)}
          ${btn('page','Library & study scope','folder',`nav-row ${state.page==='library'?'active':''}`,'data-page="library"')}
          <span class="nav-section-label">CREATE & PREPARE</span>
          ${state.authoring.available?btn('authoring-open','Card Studio','edit','nav-row','data-view="studio"'):''}
          ${btn('suite-open','Exam Studio','calendar','nav-row','data-view="overview"')}
          ${btn('suite-open','Practice & mocks','book','nav-row','data-view="practice"')}
          <span class="nav-section-label">TRACK & MANAGE</span>
          ${btn('suite-open','Pip Study','focus','nav-row','data-view="pip"')}
          ${btn('study-progress','Study progress','chart','nav-row')}
          ${btn('page','Anki tools','layers',`nav-row ${state.page==='tools'?'active':''}`,'data-page="tools"')}
        </nav>
        <div class="side-scroll" tabindex="0" aria-label="Scrollable folders and shortcuts">
          <div class="side-utility-card"><span class="side-card-label">TODAY</span><div class="side-utility-links">${btn('page','Due'+(badge?` <b>${badge}</b>`:''),'clock','recent-link','data-page="due"')}${btn('page','Recent','refresh','recent-link','data-page="recent"')}${btn('page','Saved','star','recent-link','data-page="favorites"')}</div></div>
          <section class="side-scope-card" aria-label="Current study scope"><header><span>${icon('focus',14)}STUDY SCOPE</span>${btn('studies','Edit','edit','side-scope-edit')}</header><strong>${esc(scopeName)}</strong><small>${scopeCount?`${scopeCount} selected ${scopeCount===1?'folder':'folders'} · ${fmt(f.totals.review)} review · ${fmt(f.totals.learn)} learning`:'Choose the exact folders you want included.'}</small><div class="side-scope-actions">${scopeCount?btn('quick-session','Study this scope','play','side-scope-study'):btn('studies','Choose folders','plus','side-scope-study')}${btn('page','Browse','folder','side-scope-browse','data-page="library"')}</div></section>
          ${state.page!=='library'&&f.enabled&&f.active.length?`<div class="side-label active-label">FOCUS FOLDERS</div><div class="side-studies">${f.active.map(s=>`<div class="side-exam"><button type="button" class="side-study" data-action="select-study" data-id="${s.id}" title="Choose lectures in ${esc(s.name)}"><span class="study-indicator"></span><span>${esc(s.name)}</span>${icon('chevron',12)}</button>${ib('finish-study','Remove '+s.name+' from active exams','close',`data-id="${s.id}"`,'side-remove')}</div>`).join('')}</div>`:''}
          <div class="side-label"><span>${state.page==='library'?'BROWSE FOLDERS':'FOLDERS'}</span><span>${ib('collapse-all','Collapse all folders','layers')}${ib('create','New folder','plus','data-kind="folder" data-parent="0"')}</span></div>
          <div class="tree" role="navigation" aria-label="Deck and folder tree">${sidebarTree()||'<p class="side-note">Your existing folders will appear here.</p>'}</div>
          ${recent.length?`<div class="side-label recent-label">PICK UP WHERE YOU LEFT OFF</div><div class="recent-links">${recent.map(n=>btn('navigate',`<span class="truncate">${esc(n.name)}</span>`,'clock','recent-link',`data-id="${n.id}" title="${esc(nicePath(n.path))}"`)).join('')}</div>`:''}
        </div>
        <div class="side-bottom">${btn('appearance',`<strong>Change the atmosphere</strong><small>${THEMES.find(t=>t[0]===state.config.theme)?.[1]||'Appearance'} · ${THEMES.length} worlds</small>`,'palette','appearance-link')}
          ${btn('widget-page','Widgets','grid','native-link',`aria-current="${state.page==='widgets'?'page':'false'}"`)}
          <button type="button" class="credit" data-action="website">DAEDALUS WORKS<small>daedalusworks.net</small></button>
        </div>
      </aside>`;
    }
    function nativeBtn(command,label,ico='layers',cls='secondary',extra='') {
      const supported=boot.nativeTools?.[command]!==false;
      return btn('native-tool',label,ico,cls,`data-command="${command}" ${!supported?'disabled title="Use Anki’s File or Tools menu for this version"':''} ${extra}`);
    }
    function topbar(){
      if(state.page==='widgets'&&nativeWidgets)return nativeWidgets.header();
      return `<header class="topbar unified-topbar"><div class="topbar-left">${ib('mobile','Open navigation','menu','','mobile-button')}<button class="owner-badge" data-action="owner-settings" title="Choose which add-on controls appearance" aria-label="Choose appearance owner">${state.config.visual_owner==='onigiri'?'Onigiri companion':state.config.visual_owner==='external'?'Original-theme companion':'Atelier · '+(state.page==='tools'?'Anki tools':state.page==='library'?'Library':state.page==='recent'?'Recent':state.page==='favorites'?'Saved':'Study desk')} ${icon('chevron',12)}</button>${boot.preview?'<b class="sample-label">SAMPLE DATA</b>':''}</div><div class="top-actions"><label class="search">${icon('search',16)}<input id="atelier-search" type="search" placeholder="${state.page==='tools'?'Find an Anki tool…':'Find a folder or deck…'}" aria-label="${state.page==='tools'?'Search Anki tools':'Find a folder or deck across your library'}" maxlength="200" value="${esc(state.query)}" autocomplete="off"><kbd>/</kbd></label>${nativeBtn('add','Add cards','plus','primary add-cards-top')}${nativeBtn('browse','Browse','browse','secondary browse-top')}${nativeBtn('sync','Sync','sync','secondary sync-top')}${ib('refresh','Refresh library · not sync','reload','', 'refresh-library')}${ib('appearance','Worlds and appearance','palette')}</div></header>`;
    }
    function toolsPage(){
      const found=Model.findTools(state.query,state.toolsGroup),remoteQuery=/remote|controller|bluetooth|gamepad/i.test(state.query),count=found.length+(remoteQuery?1:0);
      return `<section class="tools-page" aria-label="Anki tools directory"><div class="tools-heading"><div class="eyebrow">EVERYTHING WITHIN REACH</div><h1>Your Anki toolkit.</h1><p>The full native tools. Grouped by what you need to do.</p></div><div class="tools-spotlight">${btn('create','New folder','folder','secondary','data-kind="folder" data-parent="0"')}${btn('create','New deck','plus','secondary','data-kind="deck" data-parent="0"')}${btn('suite-open','New exam plan','calendar','secondary','data-view="new"')}${btn('remote-open','Remote controls','controls','secondary')}${btn('appearance','Appearance & compatibility','palette','quiet')}</div><div class="tools-filter-bar"><nav class="tool-categories" aria-label="Tool categories">${[{id:'all',name:'All tools'},...Model.TOOL_GROUPS].map(g=>`<button type="button" data-action="tool-category" data-category="${g.id}" aria-pressed="${state.toolsGroup===g.id}" class="tool-category ${state.toolsGroup===g.id?'selected':''}">${esc(g.name)}</button>`).join('')}</nav><span class="tool-result-count" role="status">${count} ${count===1?'tool':'tools'}${state.query?' matching your search':''}</span></div>${count?(remoteQuery?`<section class="tools-group"><h2>Remote controls</h2><p>Connect a keyboard-mode remote, test its buttons safely, and choose optional review mappings.</p>${btn('remote-open','Set up remote controls','controls','secondary')}</section>`:'')+Model.TOOL_GROUPS.map(g=>{const items=found.filter(x=>x.group===g.id);return items.length?`<section class="tools-group"><div class="tools-group-heading"><h2>${esc(g.name)}</h2><p>${esc(g.description)}</p></div><div class="tools-grid">${items.map(x=>`<div class="tool-entry"><button type="button" class="tool-tile" data-action="native-tool" data-command="${x.id}" ${boot.nativeTools?.[x.id]===false?'disabled aria-describedby="tool-unavailable-'+x.id+'"':''}><span class="tool-symbol">${icon(x.icon,22)}</span><span><strong>${esc(x.label)}</strong><small>${esc(x.description)}</small>${x.note?`<span class="tool-note">${icon(x.group==='maintenance'?'shield':'info',12)}${esc(x.note)}</span>`:''}</span>${icon('external',14)}</button>${boot.nativeTools?.[x.id]===false?`<small class="tool-unavailable" id="tool-unavailable-${x.id}">Use Anki’s original menus for this tool on your version.</small>`:''}</div>`).join('')}</div></section>`:'';}).join(''):`<div class="empty tools-empty">${icon('search',28)}<h3>No tools match that search.</h3><p>Try “import”, “media”, “templates” or “preferences”. This search finds tools, not cards.</p>${btn('reset-tools','Clear search & filters','reload','secondary')}</div>`}<aside class="tool-safety"><span>${icon('shield',19)}</span><div><strong>Your original Anki controls stay in charge.</strong><p>Collection changes keep their native dialogs and confirmations. Sync does not include local exam plans, saved practice or Pip effort. Keep those folders backed up separately.</p></div></aside></section>`;
    }

    function suitePlans(){
      const data=state.suite||{},plans=(data.plans||[]).filter(x=>!x.archived);
      return `<section class="suite-exams" aria-label="Saved exam plans"><div class="suite-exams-head"><div><h2 class="suite-section-title">Exam Studio</h2><p>One planner. Your existing exams, practice and progress.</p></div>${btn('suite-open','New exam','plus','secondary','data-view="new"')}</div>${data.warning?`<p role="status" class="suite-warning">${esc(data.warning)}</p>`:''}${data.draft?`<div class="suite-draft"><span>Saved unfinished session · resume through the practice page</span>${btn('suite-open','Open practice','arrow','quiet','data-view="practice"')}</div>`:''}${plans.length?`<div class="suite-plan-list">${plans.slice(0,6).map((e,i)=>`<article class="suite-plan"><div class="suite-plan-top"><span class="suite-plan-index">${String(i+1).padStart(2,'0')}</span><div><h3>${esc(e.name)}</h3><small>${e.due?esc(new Date(e.due).toLocaleDateString(undefined,{month:'short',day:'numeric'}))+' · ':''}${e.deck_ids?.length||0} parent ${(e.deck_ids?.length||0)===1?'folder':'folders'} / decks${e.filtered?' · Search-filtered':''}</small></div></div><div class="suite-plan-actions">${btn('suite-open','Plan','calendar','',`data-view="overview" data-id="${esc(e.id)}"`)}${btn('suite-open','Practice','book','',`data-view="practice" data-id="${esc(e.id)}"`)}${btn('suite-open','Pip Study','focus','',`data-view="pip" data-id="${esc(e.id)}"`)}${!e.filtered?btn('suite-focus','Focus folders','layers','',`data-id="${esc(e.id)}" title="Pin these folders for normal Anki review; does not create another exam plan"`):''}</div></article>`).join('')}</div>${plans.length>6?btn('suite-open',`All ${plans.length} exam plans`,'arrow','quiet','data-view="overview"'):''}`:`<div class="suite-hub-empty"><div><strong>Plan it once. Prepare in one place.</strong><p>Create an exam, choose its decks and emphasis, then build a mock or a targeted practice session. Your existing focus folders stay available below.</p></div>${btn('suite-open','Create first exam','plus','primary','data-view="new"')}</div>`}</section>`;
    }
    function authoringHub(){const a=state.authoring;return a?.available?`<section class="authoring-hub" aria-label="Card Studio workspace"><div><span class="eyebrow">FROM MATERIAL TO MEMORY</span><h2>Shape your next useful card.</h2><p>Keep the source. Refine the question. Add only what you approve.</p></div><div class="authoring-hub-actions">${btn('authoring-open','Create cards','plus','primary','data-view="studio"')}${btn('authoring-open','Find cards & sources','search','secondary','data-view="find"')}${btn('authoring-open',`${fmt(a.projects)} source projects`,'book','secondary','data-view="library"')}${btn('authoring-open',`${fmt(a.drafts)} drafts`,'edit','quiet','data-view="drafts"')}${btn('authoring-open',`${fmt(a.repairs)} need attention`,'shield','quiet','data-view="improve"')}</div></section>`:'';}
    function workflowInbox(){
      const a=state.authoring||{},draft=state.suite?.draft,plans=state.suite?.plans||[];
      if(!a.available&&!draft)return '';
      const savedName=plans.find(p=>p.id===draft?.exam_id)?.name||'Unfinished practice';
      const cards=[];
      if(draft)cards.push(`<button type="button" class="workflow-item saved-work" data-action="suite-open" data-view="practice"><span class="workflow-glyph">${icon('clock',18)}</span><span><strong>${draft.error?'Check saved practice':'Saved practice'}</strong><small>${esc(savedName)}${!draft.error&&draft.questions?' · '+esc(draft.at)+' / '+esc(draft.questions):''}</small></span>${icon('arrow',15)}</button>`);
      if(a.available&&a.drafts>0)cards.push(`<button type="button" class="workflow-item" data-action="authoring-open" data-view="drafts"><span class="workflow-glyph">${icon('edit',18)}</span><span><strong>${fmt(a.drafts)} drafts to review</strong><small>Saved locally · not yet in Anki</small></span>${icon('arrow',15)}</button>`);
      if(a.available&&a.repairs>0)cards.push(`<button type="button" class="workflow-item" data-action="authoring-open" data-view="improve"><span class="workflow-glyph">${icon('shield',18)}</span><span><strong>${fmt(a.repairs)} ${a.repairs===1?'repair':'repairs'} to check</strong><small>Review suggestions before applying</small></span>${icon('arrow',15)}</button>`);
      if(!cards.length)return '';
      return `<section class="workflow-inbox" aria-label="Continue unfinished work"><div class="workflow-heading"><strong>${cards.length?'Continue your work':'Create from your material'}</strong>${a.available?btn('authoring-open','Import a source','import','quiet','data-view="import" title="PDF, slides, documents or images — not an Anki deck package"'):''}</div>${cards.length?`<div class="workflow-items">${cards.join('')}</div>`:'<p>Turn a document, image or passage into reviewed cards. Your files stay in Sources & projects.</p>'}</section>`;
    }
    async function focusedPip(){
      const plans=(state.suite?.plans||[]).filter(p=>!p.archived),f=scope();
      const roots=f.enabled&&!f.missing.length?f.roots:[];
      const signature=ids=>Model.roots(state.nodes,ids||[]).map(n=>n.id).sort().join('|');
      const selected=signature(roots.map(n=>n.id));
      if(!selected){openDialog('studies');return;}
      const matches=plans.filter(p=>p.deck_ids?.length&&p.deck_ids.every(id=>state.map.has(id))&&signature(p.deck_ids)===selected);
      if(matches.length===1){await request('suite_open',{view:'pip',id:matches[0].id});return;}
      const chosen=f.selected.find(s=>s.id===state.profile.selected_study);
      const label=chosen?.name || (roots.length===1 ? roots[0].name : 'Focused study');
      await request('suite_open',{view:'new',setup:{name:label+' · Pip study',deck_ids:roots.map(n=>n.id)}});
    }
    async function focusedPractice(){
      const plans=(state.suite?.plans||[]).filter(p=>!p.archived),f=scope();
      const signature=ids=>Model.roots(state.nodes,ids||[]).map(n=>n.id).sort().join('|');
      const selected=f.enabled&&!f.missing.length?signature(f.roots.map(n=>n.id)):'';
      const matches=selected?plans.filter(p=>p.deck_ids?.length&&p.deck_ids.every(id=>state.map.has(id))&&signature(p.deck_ids)===selected):[];
      if(matches.length===1){await request('suite_open',{view:'practice',id:matches[0].id});return;}
      // Folder shortcuts are not exam records. Never silently use the last open plan.
      const choices=matches.length?matches:plans;
      openDialog('practice-picker',{plans:choices,matched:matches.length>0});
    }
    function deskTools(){return `<nav class="desk-tools" aria-label="Study desk actions">${nativeBtn('add','Create cards','plus','desk-tool')}${nativeBtn('import','Import a deck','import','desk-tool')}${btn('quick-session','Scheduled review','play','desk-tool')}${btn('suite-open','Practice exam','book','desk-tool','data-view="practice"')}${nativeBtn('stats','Statistics','chart','desk-tool')}${btn('page','All Anki tools','arrow','desk-tool','data-page="tools"')}</nav>`;}
    function dateBadge(study){
      const days=Model.dayState(study.date,now());
      if(days===null)return '<span class="date-label">No exam date</span>';
      return `<span class="date-label ${days<0?'past':''}">${icon('calendar',13)}${days===0?'Today':days===1?'Tomorrow':days<0?'Date passed · still active':`${days} days to go`}</span>`;
    }
    function dateTile(study){
      if(!study.date)return `<span class="date-tile">${icon('book',22)}</span>`;
      const d=new Date(study.date+'T12:00:00');
      return `<span class="date-tile"><small>${esc(d.toLocaleDateString(undefined,{month:'short'}))}</small><strong>${d.getDate()}</strong></span>`;
    }
    function focusPanel(){
      const f=scope(),count=f.selected.length,tot=f.totals,last=Model.continueDeck(state.nodes,state.profile);
      const title=last?'Welcome back.':count&&f.enabled?(count===1?f.selected[0].name:'A little progress, in focus.'):f.enabled?'Choose your next chapter.':'A good place to begin.';
      const subtitle=last?(f.enabled?'Within your active study focus.':'Your last lecture. Your normal Anki schedule.'):count&&f.enabled?'Choose one lecture at a time. Your existing folders stay separate.':f.enabled?'No active folders. Old exams stay in the library, not in today’s headline.':'Add cards, import a deck, or choose a folder you already have.';
      return `<section class="focus-panel quiet-focus task-focus ${!f.enabled?'onboarding':''}" aria-label="Active study overview"><div class="focus-intro"><div class="eyebrow"><span class="status-dot"></span>${last?'BACK TO YOUR STUDY':count&&f.enabled?'YOUR CURRENT FOCUS':'YOUR STUDY DESK'}</div><h1>${esc(title)}</h1><p>${esc(subtitle)}</p>${last?`<div class="resume-lecture"><span class="resume-glyph tone-${tone(last)}">${icon('book',20)}</span><div><strong>${esc(last.name)}</strong><small>${esc(nicePath(state.map.get(last.parent)?.path||'Library'))}</small></div><span class="resume-available">${fmt(due(last))} review / learning</span></div>`:''}<div class="focus-actions">${last?btn('study-now','Continue lecture','play','primary',`data-id="${last.id}" title="Open normal Anki review for ${esc(last.name)}"`):count&&f.enabled?btn('quick-session','Quick study','play','primary'):btn('studies','Set your focus','focus','primary','title="Choose the class or folders you want to study"')}${btn(last?'quick-session':'focus-practice',last?'Choose another':'Practice exam',last?'layers':'book','secondary')}${last?btn('focus-practice','Practice exam','book','secondary'):''}${count&&f.enabled?btn('focus-pip','Study with Pip','focus','secondary','title="Open Pip Study for these focused folders"'):''}${!last?btn('page','Browse library','folder','secondary','data-page="library"'):''}${btn('choose-lectures','Browse lectures','arrow','quiet')}</div>${f.enabled&&f.missing.length?`<button type="button" class="missing-note" data-action="studies">${icon('info',14)}${f.missing.length} selected decks are missing. Check the setup.</button>`:''}</div><div class="focus-agenda"><button type="button" class="world-window" data-action="appearance" aria-label="Explore study worlds"><span class="world-window-label"><small>${esc(THEMES.find(t=>t[0]===state.config.theme)?.[1]||'Your world')}</small><strong>${esc((boot.worlds||[]).find(w=>w.id===state.config.theme)?.title||'A place to focus')}</strong></span></button><div class="focus-quiet-note">${icon('shield',13)}Normal study uses your Anki schedule.</div></div>${f.enabled&&count?`<div class="focus-footer"><div class="focus-metric review"><strong>${fmt(tot.review)}</strong><span>Review available</span></div><div class="focus-metric learn"><strong>${fmt(tot.learn)}</strong><span>Learning</span></div><div class="focus-metric new"><strong>${fmt(tot.new)}</strong><span>New available</span></div><span class="scope-note">${icon('focus',15)}Selected folders only · Anki’s limits apply</span></div>`:''}</section>`;
    }
    function revisitPanel(){
      const recent=state.profile.recent_locations.map(id=>state.map.get(id)).filter(Boolean).slice(0,4);
      const saved=state.profile.favorites.map(id=>state.map.get(id)).filter(Boolean).slice(0,4);
      const column=(title,items,page,empty)=>`<section class="revisit-column"><header><h2>${title}</h2>${btn('page','See all','arrow','quiet',`data-page="${page}"`)}</header>${items.length?items.map(n=>`<div class="revisit-row"><button type="button" data-action="navigate" data-id="${n.id}" title="${esc(nicePath(n.path))}"><span class="revisit-glyph tone-${tone(n)}">${icon(isFolder(n)?'folder':'layers',18)}</span><span><strong>${esc(n.name)}</strong><small>${esc(nicePath(state.map.get(n.parent)?.path||'Library'))}</small></span></button>${!children(n.id).length?ib('study','Study '+n.name,'play',`data-id="${n.id}"`):ib('navigate','Open '+n.name,'arrow',`data-id="${n.id}"`)}</div>`).join(''):`<p class="revisit-empty">${empty}</p>`}</section>`;
      return `<section class="desk-revisit" aria-label="Recent and saved material">${column('Recently opened',recent,'recent','Open a folder or deck and its shortcut will appear here.')}${column('Saved for later',saved,'favorites','Star a folder or deck to keep it here. It stays in its original location.')}</section>`;
    }

    function scopeBar(){
      const f=scope();
      if(!f.enabled)return '';
      return `<div class="scope-bar"><span>${icon('focus',14)}Active focus</span><select id="active-study-selector" aria-label="Active study"><option value="all">All active studies${f.active.length?' ('+f.active.length+')':''}</option>${f.active.map(s=>`<option value="${s.id}" ${state.profile.selected_study===s.id?'selected':''}>${esc(s.name)}</option>`).join('')}</select>${btn('new-study','Add study','plus','quiet')}<span class="scope-spacer"></span>${btn('page','See all folders','arrow','quiet','data-page="library"')}</div>`;
    }
    function breadcrumb(){
      const path=[];let n=state.map.get(state.location);const seen=new Set();
      while(n&&!seen.has(n.id)){seen.add(n.id);path.unshift(n);n=state.map.get(n.parent);}
      const parent=state.map.get(state.location)?.parent||'0';
      return `<div class="location-bar"><div class="history-buttons">${ib('back','Back to previous location','back',!state.history.length?'disabled':'')}${ib('forward','Forward','arrow',!state.forward.length?'disabled':'')}${ib('up','Up to parent folder','up',state.location==='0'?'disabled':'')}</div><nav class="breadcrumbs" aria-label="Current folder path">${btn('page','All folders','home','crumb','data-page="library" data-drop="0"')}${path.map((n,i)=>`${icon('chevron',12)}<button type="button" class="crumb ${i===path.length-1?'current':''}" data-action="navigate" data-id="${n.id}" ${i===path.length-1?'aria-current="page"':''} title="${esc(n.name)}">${esc(n.name)}</button>`).join('')}</nav>${state.location!=='0'?btn('navigate','Parent folder','up','parent-link',`data-id="${parent}"`):''}</div>`;
    }
    function peekRows(n){
      const nested=children(n.id),shown=state.peek.has(n.id),limit=shown?32:3;
      if(!nested.length)return '';
      return `<div class="card-shortcuts card-peek"><div class="peek-label">INSIDE THIS FOLDER</div>${nested.slice(0,limit).map(c=>`<div class="peek-row"><button type="button" data-action="navigate" data-id="${c.id}" title="Open ${esc(nicePath(c.path))}">${icon(isFolder(c)?'folder':'layers',14)}<span>${esc(c.name)}</span>${icon('chevron',11)}</button>${!children(c.id).length?ib('study','Study only '+c.name,'play',`data-id="${c.id}"`,'peek-study'):''}</div>${children(c.id).length===1?`<button type="button" class="peek-grandchild" data-action="navigate" data-id="${children(c.id)[0].id}">${icon('chevron',10)}<span>${esc(children(c.id)[0].name)}</span></button>`:''}`).join('')}${nested.length>3?btn('peek',shown?'Show less':`Show ${Math.min(nested.length,32)-3} more`,shown?'up':'down','peek-more',`data-id="${n.id}" aria-expanded="${shown}"`):''}${shown&&nested.length>32?btn('navigate',`Open all ${nested.length} items`,'arrow','peek-more',`data-id="${n.id}"`):''}</div>`;
    }
    function deckCard(n){
      const folder=isFolder(n),nested=children(n.id),path=nicePath(n.path);
      return `<article class="deck-card tone-${tone(n)} ${folder?'folder-card':'stack-card'}" data-node="${n.id}" data-drop="${n.filtered?'':n.id}" draggable="${!n.filtered}" aria-label="${esc(n.name)} ${folder?'folder':'deck'}">
        <div class="card-head"><button type="button" class="card-art" data-action="navigate" data-id="${n.id}" aria-label="Open ${esc(n.name)}">${folderArt(folder)}</button><div class="card-controls">${ib('favorite',`${favorite(n)?'Unpin':'Pin'} ${n.name}`,'star',`data-id="${n.id}" aria-pressed="${favorite(n)}"`,favorite(n)?'starred':'')}${ib('organize','Organize '+n.name,'more',`data-id="${n.id}"`)}</div></div>
        <div class="card-type">${n.filtered?'FILTERED DECK':folder?'FOLDER':'DECK'}</div><button type="button" class="card-title" data-action="navigate" data-id="${n.id}" title="${esc(path)}">${esc(n.name)}</button>
        <p class="card-description">${folder?nested.length+(nested.length===1?' item':' items')+' · nothing combined':n.filtered?'Managed by Anki':'Individual lecture deck'}</p>
        ${examButton(n)}
        ${state.query||state.page==='recent'||state.page==='favorites'?`<p class="card-path" title="${esc(path)}">${esc(n.parent==='0'?'All folders':nicePath(state.map.get(n.parent)?.path||''))}</p>`:''}
        ${peekRows(n)}
        <div class="countline"><span class="review">${fmt(n.review)} review</span><span class="learn">${fmt(n.learn)} learn</span><span class="new">${fmt(n.new)} new</span></div>
        <div class="card-bottom">${btn('navigate',folder?'Browse contents':'Open deck','arrow','open-card',`data-id="${n.id}"`)}${ib('study',folder?'Study whole folder':'Study only '+n.name,'play',`data-id="${n.id}"`,'quick-study')}</div></article>`;
    }
    function deckListRow(n){
      const folder=isFolder(n),nested=children(n.id),open=state.peek.has(n.id),path=nicePath(n.path);
      return `<article class="deck-card library-row tone-${tone(n)}" data-node="${n.id}" data-drop="${n.filtered?'':n.id}" draggable="${!n.filtered}" aria-label="${esc(n.name)} ${folder?'folder':'deck'}"><div class="library-row-main"><div class="library-row-name">${nested.length?ib('peek',(open?'Hide':'Preview')+' contents of '+n.name,open?'down':'chevron',`data-id="${n.id}" aria-expanded="${open}"`,'list-preview-toggle'):'<span class="list-preview-spacer"></span>'}<span class="list-glyph">${folderArt(folder)}</span><div><button type="button" class="card-title" data-action="navigate" data-id="${n.id}" title="${esc(path)}">${esc(n.name)}</button><div class="list-meta"><span>${n.filtered?'Filtered deck':folder?'Folder':'Deck'}</span>${folder?`<span>${nested.length} inside</span>`:''}${exactExams(n).length?'<span class="focus-badge">In focus</span>':''}</div>${state.query||state.page==='recent'||state.page==='favorites'?`<p class="card-path" title="${esc(path)}">${esc(nicePath(state.map.get(n.parent)?.path||'Library'))}</p>`:''}</div></div><div class="row-counts" aria-label="Available counts"><span class="review">${fmt(n.review)}<small>review</small></span><span class="learn">${fmt(n.learn)}<small>learn</small></span><span class="new">${fmt(n.new)}<small>new</small></span></div><div class="library-row-actions">${btn('navigate',folder?'Open folder':'Open deck',folder?'folder':'layers','quiet row-open',`data-id="${n.id}"`)}${ib('study',folder?'Study whole folder':'Study only '+n.name,'play',`data-id="${n.id}"`)}${ib('favorite',`${favorite(n)?'Unpin':'Pin'} ${n.name}`,'star',`data-id="${n.id}" aria-pressed="${favorite(n)}"`,favorite(n)?'starred':'')}${ib('organize','Organize '+n.name,'more',`data-id="${n.id}"`)}</div></div>${open&&nested.length?`<div class="library-row-preview">${peekRows(n)}</div>`:''}</article>`;
    }
    function lectureRows(study){
      const roots=Model.roots(state.nodes,study.deck_ids),start=roots.length===1&&children(roots[0].id).length?children(roots[0].id):roots;
      const stack=sortedNodes(start).reverse().map(n=>({n,depth:0})),rows=[];const seen=new Set();let total=0;
      while(stack.length&&rows.length<state.boardLimit){
        const {n,depth}=stack.pop();if(seen.has(n.id))continue;seen.add(n.id);total++;
        const nested=children(n.id),key=study.id+':'+n.id,closed=state.collapsedLectures.has(key);
        if(state.page!=='due'||due(n)>0||nested.length){
          rows.push(`<div class="lecture-row ${nested.length?'lecture-branch':''} tone-${tone(n)}" data-node="${n.id}" style="--level:${Math.min(depth,8)}"><div class="lecture-ident">${nested.length?ib('lecture-expand',closed?'Expand lectures':'Collapse lectures',closed?'chevron':'down',`data-id="${key}" aria-expanded="${!closed}"`,'lecture-toggle'):`<span class="lecture-leaf-icon">${icon('layers',16)}</span>`}<button type="button" class="lecture-name" data-action="navigate" data-id="${n.id}" title="${esc(nicePath(n.path))}"><strong>${esc(n.name)}</strong><small>${nested.length?nested.length+(nested.length===1?' item':' items')+' · expand or open':esc(nicePath(state.map.get(n.parent)?.path||'Individual deck'))}</small></button></div><div class="lecture-counts"><span class="review">${fmt(n.review)}<small>review</small></span><span class="learn">${fmt(n.learn)}<small>learn</small></span><span class="new">${fmt(n.new)}<small>new</small></span></div><div class="lecture-actions">${nested.length?btn('navigate','Open','folder','quiet',`data-id="${n.id}"`):btn('study','Study','play','lecture-study',`data-id="${n.id}" title="Study only ${esc(n.name)}"`)}${ib('organize','Options for '+n.name,'more',`data-id="${n.id}"`)}</div></div>`);
        }
        if(!closed)for(const child of sortedNodes(nested).reverse())stack.push({n:child,depth:depth+1});
      }
      return rows.join('')+(stack.length?btn('board-more','Show more lectures','down','quiet board-more'):'') || `<div class="empty small"><p>No available reviews in these lectures right now.</p></div>`;
    }
    function studyBoard(){
      const f=scope();
      if(!f.selected.length)return emptyState();
      return `<div class="exam-board" id="lecture-board" tabindex="-1">${f.selected.map(study=>{
        const roots=Model.roots(state.nodes,study.deck_ids);
        return `<section class="exam-section" aria-label="Lectures in ${esc(study.name)}"><header class="exam-section-head"><span class="exam-section-symbol">${icon('folder',20)}</span><div><h3>${esc(study.name)}</h3><p>${roots.length===1?esc(nicePath(roots[0].path)):roots.length+' selected folders and decks'}</p></div><div class="exam-section-actions">${roots.length===1?btn('navigate','Browse folder','arrow','quiet',`data-id="${roots[0].id}"`):''}${ib('edit-study','Edit '+study.name,'edit',`data-id="${study.id}"`)}${ib('finish-study','Remove '+study.name+' from active exams','close',`data-id="${study.id}"`)}</div></header><div class="lecture-table">${lectureRows(study)}</div>${roots.length===1&&children(roots[0].id).length?`<footer class="exam-section-foot"><span>Study buttons open individual decks. Nothing is merged.</span>${btn('study','Study entire folder','play','quiet',`data-id="${roots[0].id}"`)}</footer>`:''}</section>`;
      }).join('')}</div>`;
    }
    function sortedNodes(items){return Model.sortNodes(items,{sort:state.config.sort,recent:state.profile.recent_locations,folderIds:state.profile.folders});}
    function visibleNodes(){
      let items;
      if(state.query){const q=state.query.toLocaleLowerCase();items=state.nodes.filter(n=>nicePath(n.path).toLocaleLowerCase().includes(q));}
      else if(state.page==='favorites')items=state.nodes.filter(favorite);
      else if(state.page==='recent')items=(state.recentTab==='added'?state.profile.recent_added.map(x=>x.id):state.profile.recent_locations).map(id=>state.map.get(id)).filter(Boolean);
      else if(state.page==='desk'||state.page==='due')items=scope().roots;
      else items=children(state.location);
      if(state.page==='due'&&!state.query||state.filter==='due')items=items.filter(n=>due(n)>0);
      if(state.filter==='folders')items=items.filter(isFolder);
      if(state.filter==='decks')items=items.filter(n=>!isFolder(n));
      if(state.page==='recent'&&!state.query)return [...items];
      return sortedNodes(items);
    }
    function emptyState(){
      if(state.page==='library'&&state.location==='0'&&!state.query&&state.filter==='all'&&!state.nodes.length){
        const source=state.authoring?.available?`<article class="empty-guide-item"><span class="empty-guide-icon">${icon('import',20)}</span><div><h4>I have notes or study material</h4><p>Bring in a PDF, slide deck, document, or image. Card Studio keeps the source beside the cards you approve.</p>${btn('authoring-open','Import source','import','secondary','data-view="import"')}</div></article>`:'';
        return `<div class="empty library-first-run"><span class="eyebrow">YOUR FIRST STEP</span><h3>Bring your learning into one calm library.</h3><p>Choose the path that matches what you already have. You can reorganize anything later; nothing moves until you choose it.</p><div class="empty-guide-grid"><article class="empty-guide-item"><span class="empty-guide-icon">${icon('updates',20)}</span><div><h4>I already use Anki</h4><p>Import a shared deck or collection file, then keep studying with Anki’s normal schedule.</p>${nativeBtn('import','Import an Anki deck','import','secondary')}</div></article>${source}<article class="empty-guide-item"><span class="empty-guide-icon">${icon('folder',20)}</span><div><h4>I want a clear structure</h4><p>Create a subject folder first, then add decks inside it so classes and chapters stay easy to find.</p>${btn('create','Create a folder','plus','secondary','data-kind="folder"')}</div></article></div><div class="empty-guide-footer">${btn('help','Show navigation tips','info','quiet')}</div></div>`;
      }
      let title='A clear place to start.',body='Create a folder for a subject, then add a deck inside it.',action=btn('create','New folder','plus','primary','data-kind="folder"');
      if(state.query){title='No matching folders or decks.';body='Search looks through the whole library, including old exams and nested folders.';action=btn('clear-search','Clear search','search');}
      else if(state.page==='desk'&&scope().enabled){title='Nothing selected for today.';body='Choose the folders that belong to your next exam. Existing cards stay exactly where they are.';action=btn('studies','Choose active studies','focus','primary');}
      else if(state.page==='due'){title='No available reviews in this view.';body=scope().enabled?'This only reflects your selected studies. Anki’s daily limits still apply; this is not a measure of exam readiness.':'Anki is not listing review or learning cards for these decks right now.';action=btn('home','Back to study desk','back');}
      else if(state.page==='recent'){title=state.recentTab==='added'?'New decks will appear here.':'Your next visit is one click away.';body=state.recentTab==='added'?'Atelier tracks decks first seen after this version starts. Your entire existing collection is not mislabeled as new.':'Open a folder or deck and it will appear here. These are shortcuts, not copies.';action=btn('page','Browse your folders','folder','primary','data-page="library"');}
      else if(state.page==='favorites'){title='Keep your go-to decks close.';body='Star any folder or deck to pin a shortcut here, without moving it.';action=btn('page','Browse folders','folder','primary','data-page="library"');}
      else if(state.filter!=='all'){title='Nothing matches this view.';body='Your folder contents are still here. Choose All items to see them.';action=btn('filter','Show all items','layers','secondary','data-filter="all"');}
      else if(state.location!=='0'){title='You’re inside '+state.map.get(state.location)?.name+'.';body='This deck has no subfolders. Study its cards, or create something inside it.';action=btn('study','Study this deck','play','primary',`data-id="${state.location}"`)+btn('create','New deck inside','plus','secondary','data-kind="deck"');}
      return `<div class="empty">${icon('folder',30)}<h3>${esc(title)}</h3><p>${esc(body)}</p><div>${action}</div></div>`;
    }
    function deckDetail(n){
      return `<section class="deck-detail tone-${tone(n)}" aria-label="Current deck actions"><div class="deck-detail-head"><span class="detail-glyph">${folderArt(false)}</span><div><h3>Ready when you are.</h3><p>This is an individual deck. Open its cards, review it, or use it in an exam plan.</p></div></div><div class="deck-detail-counts"><div class="review"><strong>${fmt(n.review)}</strong><span>Review available</span></div><div class="learn"><strong>${fmt(n.learn)}</strong><span>Learning</span></div><div class="new"><strong>${fmt(n.new)}</strong><span>New available</span></div></div><div class="deck-detail-actions">${btn('study','Study this deck','play','primary',`data-id="${n.id}"`)}${btn('browse','Browse its cards','browse','secondary',`data-id="${n.id}"`)}${btn('options','Deck options','sliders','quiet',`data-id="${n.id}"`)}${state.authoring.available?btn('authoring-open','Add cards here','plus','secondary',`data-view="studio" data-deck="${n.id}"`):''}${btn('plan-folder','Use in an exam plan','calendar','quiet',`data-id="${n.id}"`)}</div><p class="detail-note">${icon('info',14)}These are Anki’s available counts, not total cards or a readiness score. Study opens Anki’s normal deck overview.</p></section>`;
    }
    function results(){const leaf=state.map.get(state.location);if(!state.query&&state.page==='library'&&leaf&&!isFolder(leaf)&&state.filter!=='folders')return deckDetail(leaf);if(!state.query&&['desk','due'].includes(state.page)&&scope().enabled)return studyBoard();const items=visibleNodes();return `<div class="cards ${state.page==='desk'?'focus-cards':''} ${state.config.view==='list'?'list':''}" id="card-list">${items.length?items.slice(0,state.limit).map(state.config.view==='list'?deckListRow:deckCard).join(''):emptyState()}</div>${items.length>state.limit?btn('more-results',`Show ${Math.min(60,items.length-state.limit)} more`,'down','secondary show-more'):''}<div class="library-foot"><span>${items.length} ${items.length===1?'item':'items'}${state.query?' · Search across all folders':''}${state.page==='recent'&&state.recentTab==='added'?' · First observed by Atelier; not original card creation dates':''}</span>${btn('help','Navigation tips','info','quiet')}</div>`;}
    function librarySection(){
      const here=state.map.get(state.location),f=scope();
      const last=Model.lastFolder(state.nodes,state.profile,state.location);
      const heading=state.query?'Search results':state.page==='desk'?(f.enabled?'Choose a lecture':'Your folders'):state.page==='recent'?'Pick up where you left off':state.page==='favorites'?'Within reach':state.page==='due'?(f.enabled?'Reviews in your active studies':'Available reviews'):here?here.name:'All folders';
      return `<section class="library" aria-label="Folders and decks">${state.page==='library'&&!state.query?breadcrumb():''}${state.page==='library'?`<div class="library-orientation"><span>${icon('folder',14)}${state.location==='0'?'Your complete library':'Inside a folder'} · Focus never hides your other material</span>${last?btn('navigate','Last folder','clock','quiet',`data-id="${last.id}" title="Return to ${esc(nicePath(last.path))}"`):''}</div>`:''}
        <div class="section-heading"><div><h2>${esc(heading)}</h2>${state.page==='library'?'<p>Open a folder to navigate. Study starts review. Pinning creates a shortcut, not a copy.</p>':state.page==='desk'&&f.enabled?'<p>Open a branch, or study one lecture at a time.</p>':''}</div><div class="library-actions">${state.page==='library'&&!here?nativeBtn('import','Import','import','quiet'):''}${here?examButton(here):''}${here?btn('study',children(here.id).length?'Study entire folder':'Study deck','play','secondary',`data-id="${here.id}"`):''}${btn('create','New deck','plus','quiet','data-kind="deck"')}${btn('create','New folder','folder','secondary','data-kind="folder"')}</div></div>
        <div class="library-controls ${!state.query&&['desk','due'].includes(state.page)&&f.enabled?'board-controls':''}"><div class="tabs" role="group" aria-label="Filter folders">${(state.page==='recent'?[['viewed','Recently opened'],['added','Recently added']]:[['all','All items'],['folders','Folders'],['decks','Decks']]).map(([id,label])=>`<button type="button" class="tab ${(state.page==='recent'?state.recentTab:state.filter)===id?'active':''}" data-action="filter" data-filter="${id}" aria-pressed="${(state.page==='recent'?state.recentTab:state.filter)===id}">${label}</button>`).join('')}</div><div class="view-tools">${state.page==='recent'&&!state.query?'<span class="recent-order" aria-label="Sort order">Newest first</span>':`<select id="atelier-sort" aria-label="Sort folders" title="Sort siblings only; folder hierarchy is preserved"><option value="name" ${state.config.sort==='name'?'selected':''}>Name · folders first</option><option value="due" ${state.config.sort==='due'?'selected':''}>Review + learning</option><option value="recent" ${state.config.sort==='recent'?'selected':''}>Recently opened</option></select>`}<div class="view-switch">${ib('view','Grid view','grid',`data-view="grid" aria-pressed="${state.config.view==='grid'}"`,state.config.view==='grid'?'active':'')}${ib('view','List view','list',`data-view="list" aria-pressed="${state.config.view==='list'}"`,state.config.view==='list'?'active':'')}</div></div></div><div id="library-results" aria-live="polite">${results()}</div></section>`;
    }

    function ownershipChoices(){
      const report=boot.integrations||{},hasOnigiri=report.onigiri===true,others=report.makeovers||[];
      return `<div class="owner-choices"><button class="owner-choice atelier-choice" data-action="choose-owner" data-owner="atelier"><div class="owner-preview"><i></i><i></i><i></i><span>atelier</span></div><span class="owner-label">ATELIER STUDIO</span><h3>A designed space.<br>Your familiar tools.</h3><p>Use Atelier's home and review design. Onigiri keeps its rewards and widgets.${others.length?' Other detected makeovers are not disabled; use Companion for the safest separation.':''}</p><b>Use Atelier ${icon('arrow',16)}</b></button>${hasOnigiri?`<button class="owner-choice onigiri-choice" data-action="choose-owner" data-owner="onigiri"><div class="owner-preview"><i></i><i></i><i></i><span>Onigiri</span></div><span class="owner-label">ORIGINAL ONIGIRI</span><h3>Your original home.<br>No mixed theme.</h3><p>Keep Onigiri's page, reviewer, fonts and widget layout. Atelier adds only a compact launcher; open its organizer when you need it.</p><b>Keep Onigiri ${icon('arrow',16)}</b></button>`:''}</div><div class="owner-other"><div><strong>Another makeover or theme is installed?</strong><p>${boot.integrations?.metadata_checked===false?'The installed-add-on check could not finish. Keep the original appearance until you rescan. ':''}${others.length?'Possibly changing colors: '+others.map(x=>esc(x.name)).join(', ')+'.':'Renamed or custom themes may not be detected.'} Keep its design, with Atelier available as a separate organizer.</p></div>${btn('choose-owner','Keep original / other theme','shield','secondary','data-owner="external"')}</div>`;
    }
    function ownerScreen(){const names=(boot.integrations?.makeovers||[]).map(x=>esc(x.name));return `<main class="owner-screen"><div class="owner-intro"><span class="owner-kicker">ATELIER / COMPATIBILITY / ${esc(boot.version)}</span><h1>One visual owner.<br><em>Your tools, together.</em></h1><p>${names.length?'Another possible makeover was detected: '+names.join(', ')+'.<br>':'Onigiri is enabled.<br>'}Choose which design stays in control. No add-on is disabled.</p></div>${ownershipChoices()}<p class="owner-footnote">This only changes presentation. Decks, schedules, game progress and saved exam records are preserved.</p></main>`;}

    function quickChoices(){
      const f=scope();
      const roots=f.enabled?f.roots:[];
      const nodes=state.nodes.filter(n=>!n.children.length&&(!f.enabled||Model.belongs(state.nodes,roots,n.id)));
      const ranked=nodes.sort((a,b)=>(b.id===state.profile.last_studied)-(a.id===state.profile.last_studied)||due(b)-due(a)||byName(a,b));
      return ranked.slice(0,60).map(n=>`<div class="quick-lecture"><span class="quick-glyph tone-${tone(n)}">${icon('book',22)}</span><div><small>${esc(nicePath(n.path.split('::').slice(0,-1).join('::')))}</small><strong>${esc(n.name)}</strong><span>${fmt(n.review)} review · ${fmt(n.learn)} learning · ${fmt(n.new)} new${n.id===state.profile.last_studied?' · Last studied':''}</span></div>${btn('study-now','Start','play','secondary',`data-id="${n.id}"`)}</div>`).join('')||'<p class="note">No lecture decks in this focus yet. Open All folders to choose one or pin an exam.</p>';
    }
    function render(options={}) {
      nativeWidgets?.beforeRender();
      const pos=getScroll(),active=shadow.activeElement;
      const focus=active&&frame.contains(active)?{action:active.dataset.action,id:active.dataset.id,field:active.id,view:active.dataset.view,category:active.dataset.category,filter:active.dataset.filter,page:active.dataset.page}:null;
      setHost();
      if(state.config.visual_owner==='ask'){frame.style.display='';frame.innerHTML=ownerScreen();}
      else if(state.config.mode==='native'){
        frame.innerHTML=`<div class="native-launcher"><span class="launcher-icon">${icon('focus',20)}</span><span><strong>atelier · ${state.failure?'Recovery':state.loaded?'Study desk':'Loading'}</strong><small>${state.failure?'The original home is available.':state.loaded?'Your folders and active studies, one click away.':'Reading your deck library…'}</small></span>${btn(state.failure?'refresh':'workspace',state.failure?'Retry':'Open','arrow','primary')}</div>`;
        frame.style.display=state.loaded&&home?.hasRail()?'none':'';
      }else if(!state.loaded){
        frame.style.display='';
        frame.innerHTML=`<main class="workspace-loading"><div class="loading-mark">${brand}</div><h1>${state.failure?'Your study desk is taking longer to open.':'Opening your study desk…'}</h1><p>${state.failure?esc(state.failure):'Your folders and active exams will appear here.'}</p><div>${state.failure?btn('refresh','Try again','refresh','primary'):''}${btn('native','Other add-ons / original home','external','secondary')}</div></main>`;
      }else{
        frame.style.display='';
        frame.innerHTML=`<div class="layout" data-page="${esc(state.page)}">${sidebar()}<button type="button" class="side-scrim ${state.mobile?'open':''}" data-action="close-nav" aria-label="Dismiss navigation"></button><main class="main" tabindex="-1" ${state.mobile?'inert':''}>${topbar()}<div class="main-inner">${state.page==='widgets'?nativeWidgets.page():state.page==='tools'?toolsPage():state.page==='desk'&&!state.query?`<div class="desk-heading"><span>${esc(now().toLocaleDateString(undefined,{weekday:'long',month:'long',day:'numeric'}))}</span><span class="desk-status">${icon('check',13)}Your library, preserved</span></div><div id="atelier-workflow-inbox">${workflowInbox()}</div>${nativeWidgets?.onHome()||''}${focusPanel()}${scopeBar()}`:state.page==='due'?scopeBar():''}${['tools','widgets'].includes(state.page)?'':librarySection()}${state.page==='desk'&&!state.query?revisitPanel()+suitePlans()+deskTools()+'<div id="atelier-authoring-hub">'+authoringHub()+'</div>':''}<div class="extension-slot"><slot name="atelier-widgets"></slot></div><footer class="help-strip"><span>${icon('shield',14)}${scope().enabled?'Focus changes what you see, not when cards are due.':esc(state.studied||'Your decks stay in Anki’s native structure.')}</span><div>${btn('import','Import',null,'quiet')}${btn('study-progress','Study progress','chart','quiet')}${btn('stats','Statistics',null,'quiet')}${btn('widget-page','Widgets','grid','quiet')}${btn('nw-arrange','Customize home','grid','quiet')}</div></footer></div></main></div>`;
        const main=shadow.querySelector('.main'),side=shadow.querySelector('.side-scroll');
        main.scrollTop=options.resetMain?0:pos.main;side.scrollTop=pos.side;
        if(focus&&!options.resetMain&&!state.dialog){const target=focus.field?shadow.getElementById(focus.field):[...frame.querySelectorAll('[data-action]')].find(el=>el.dataset.action===focus.action&&el.dataset.id===focus.id&&el.dataset.view===focus.view&&el.dataset.category===focus.category&&el.dataset.filter===focus.filter&&el.dataset.page===focus.page);target?.focus({preventScroll:true});}
      }
      setHost();updateThemeControls();syncCapture();nativeWidgets?.mount();
    }
    async function load(){
      const rev=++loadRevision;
      try{
        await prefQueue;
        const loadedPrefRevision=prefRevision,loadedConfigRevision=configRevision;
        const data=await request('load');if(rev!==loadRevision)return;state.suite=data.suite||state.suite;state.authoring=data.authoring||state.authoring;
        state.nodes=Array.isArray(data.nodes)?data.nodes:[];state.map=new Map(state.nodes.map(n=>[n.id,n]));state.childMap=new Map();
        for(const n of state.nodes){if(!state.childMap.has(n.parent))state.childMap.set(n.parent,[]);state.childMap.get(n.parent).push(n);}
        for(const kids of state.childMap.values())kids.sort(byName);
        if(loadedPrefRevision===prefRevision)state.profile=normalizeProfile(data.profile);state.current=data.current;state.studied=data.studied;
        if(!configPending&&loadedConfigRevision===configRevision){state.config={...defaults,...data.settings};if(state.config.mode==='hybrid')state.config.mode='workspace';configSaved={...state.config};}
        if(state.location!=='0'&&!state.map.has(state.location))state.location='0';
        state.loaded=true;state.failure='';render();
        if(data.notice)announce(data.notice,true);
        if(boot.openSettings){boot.openSettings=false;openDialog('appearance');}
      }catch(e){if(rev!==loadRevision)return;state.loaded=false;state.failure=e.message;closeDialog(true);render();announce(e.message,true);}
    }
    function announce(text,error=false){
      shadow.querySelector('.toast')?.remove();clearTimeout(toastTimer);
      const el=document.createElement('div');el.className='toast';el.dataset.duration='6500';el.setAttribute('role',error?'alert':'status');el.innerHTML=icon(error?'info':'check',17)+`<span>${esc(text)}</span>`;
      const dismiss=document.createElement('button');dismiss.type='button';dismiss.className='toast-dismiss';dismiss.setAttribute('aria-label','Dismiss notification');dismiss.title='Dismiss notification';dismiss.innerHTML=icon('close',14);
      dismiss.addEventListener('click',()=>{clearTimeout(toastTimer);el.remove();});el.append(dismiss);
      const expire=()=>{clearTimeout(toastTimer);toastTimer=setTimeout(()=>{if(!el.matches(':hover,:focus-within'))el.remove();},Number(el.dataset.duration));};
      el.addEventListener('pointerenter',()=>clearTimeout(toastTimer));el.addEventListener('pointerleave',expire);
      el.addEventListener('focusin',()=>clearTimeout(toastTimer));el.addEventListener('focusout',()=>queueMicrotask(()=>{if(!el.contains(shadow.activeElement))expire();}));
      (shadow.querySelector('.dialog-alerts')||app).append(el);expire();
    }
    function themeTiles(){
      return THEMES.map(([id,name,desc])=>{
        const world=(boot.worlds||[]).find(w=>w.id===id)||{};
        const lighting=world.lighting||(['rose','bloom','linen','matcha','peach','tidal'].includes(id)?'light':'dark');
        return `<button type="button" class="theme-tile ${state.config.theme===id?'selected':''}" data-action="theme" data-theme-choice="${id}" data-lighting="${lighting}" aria-label="${esc(name+': '+desc)}" aria-pressed="${state.config.theme===id}"><span class="mini-screen" data-theme="${id}" aria-hidden="true"><span class="theme-light">${lighting==='light'?'Light':'Dark'}</span><span class="theme-material-sample"><i></i><i></i><i></i></span></span><span class="tile-label"><strong>${esc(name)}</strong><b class="theme-check" aria-hidden="true" ${state.config.theme===id?'':'hidden'}>${icon('check',16)}</b></span><span class="theme-title">${esc(world.title||name)}</span><small>${esc(world.material||desc)}</small></button>`;
      }).join('');
    }
    function filterWorlds(filter='all'){
      if(!['all','light','dark'].includes(filter))return;
      state.dialogData.worldFilter=filter;let count=0;
      for(const tile of shadow.querySelectorAll('[data-theme-choice]')){
        const visible=filter==='all'||tile.dataset.lighting===filter;tile.hidden=!visible;if(visible)count++;
      }
      for(const button of shadow.querySelectorAll('[data-action="world-filter"]'))button.setAttribute('aria-pressed',String(button.dataset.filter===filter));
      const countNode=shadow.getElementById('world-filter-count');if(countNode)countNode.textContent=count+' worlds · '+(THEMES.find(t=>t[0]===state.config.theme)?.[1]||'Current world')+' selected';
    }
    function parentOptions(selected,exclude=''){
      const source=state.map.get(exclude);
      return `<option value="0" ${selected==='0'?'selected':''}>All folders (top level)</option>`+state.nodes.filter(n=>!n.filtered&&n.id!==exclude&&(!source||!n.path.startsWith(source.path+'::'))).sort((a,b)=>Model.compareNames({...a,name:a.path},{...b,name:b.path})).map(n=>`<option value="${n.id}" ${selected===n.id?'selected':''}>${esc(nicePath(n.path))}</option>`).join('');
    }
    function studyPicker(){
      const q=String(state.dialogData.search||'').toLocaleLowerCase(),selected=new Set(state.dialogData.draft.deck_ids);
      const rows=state.nodes.filter(n=>!q||nicePath(n.path).toLocaleLowerCase().includes(q));
      const shown=rows.slice(0,state.dialogData.limit||80);
      return `${shown.map(n=>`<label class="picker-row ${selected.has(n.id)?'checked':''}"><input type="checkbox" data-pick-deck="${n.id}" ${selected.has(n.id)?'checked':''}><span class="picker-art tone-${tone(n)}">${folderArt(isFolder(n))}</span><span><strong>${esc(n.name)}</strong><small>${esc(n.parent==='0'?'All folders':nicePath(state.map.get(n.parent)?.path||''))}</small></span>${n.children.length?`<small>${n.children.length} inside</small>`:''}</label>`).join('')||'<p class="note">No matching folders.</p>'}${rows.length>shown.length?btn('picker-more','Show more matches','down','quiet'):''}`;
    }
    function pickerSummary(){
      const draft=state.dialogData.draft,roots=Model.roots(state.nodes,draft.deck_ids),missing=draft.deck_ids.filter(id=>!state.map.has(id));
      return `${roots.length} ${roots.length===1?'parent folder / deck':'parent folders / decks'} selected for this study. Subfolders are included automatically; overlapping branches count once.${missing.length?` ${missing.length} selection(s) are no longer in the library.`:''}`;
    }
    function studyRows(){
      const studies=[...state.profile.studies].sort((a,b)=>Number(b.active)-Number(a.active)||(a.date||'9999').localeCompare(b.date||'9999'));
      return studies.length?studies.map(s=>{
        const roots=Model.roots(state.nodes,s.deck_ids),tot=Model.totals(roots),missing=s.deck_ids.filter(id=>!state.map.has(id)).length;
        return `<article class="study-row ${s.active?'':'finished'}">${dateTile(s)}<div class="study-row-text"><strong>${esc(s.name)}</strong><small>${s.active?'Active':'Finished'} · ${roots.length} parent folders / decks${s.active?' · '+fmt(due(tot))+' available reviews':''}${missing?' · '+missing+' missing':''}</small>${s.active?dateBadge(s):''}</div><div class="study-row-actions">${ib('edit-study','Edit '+s.name,'edit',`data-id="${s.id}"`)}${btn('toggle-study',s.active?'Finish':'Reactivate',s.active?'check':'refresh','secondary',`data-id="${s.id}"`)}${ib('remove-study','Remove study shortcut '+s.name,'close',`data-id="${s.id}"`)}</div></article>`;
      }).join(''):'<div class="empty small"><h3>Your next exam starts here.</h3><p>Choose decks you already have. Nothing gets copied, moved, suspended or rescheduled.</p></div>';
    }
    function openDialog(type,data={}){
      if(state.busy)return;
      if(!state.dialog)focusBeforeDialog=shadow.activeElement;
      state.mobile=false;state.dialog=type;state.dialogData={...data};
      if(type==='study-edit'){
        const saved=state.profile.studies.find(s=>s.id===data.id);
        state.dialogData.draft=saved?JSON.parse(JSON.stringify(saved)):{id:'study_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,7),name:'',date:'',deck_ids:data.deck?[data.deck]:[],active:true};
        state.dialogData.limit=80;state.dialogData.search='';
      }
      if(type==='home-edit'){
        const prefs=state.profile.home_layout||{enabled:false,columns:3,items:[]};
        const widgets=home?.list()||[], live=new Map(widgets.map(w=>[w.id,w]));
        const ordered=[...prefs.items.map(x=>({...x,...(live.get(x.id)||{}),title:live.get(x.id)?.title||'Widget not currently loaded',available:live.has(x.id)})),...widgets.filter(w=>!prefs.items.some(x=>x.id===w.id)).map(w=>({...w,available:true}))];
        state.dialogData.widgets=ordered;state.dialogData.layout={enabled:prefs.enabled,columns:prefs.columns,items:ordered.map(w=>({id:w.id,visible:w.visible,size:w.size,height:w.height}))};
      }
      nativeWidgets?.initDialog(type,state.dialogData);
      renderDialog();setHost();
    }
    function closeDialog(force=false){
      if(state.busy&&!force)return;
      const activeNotice=shadow.querySelector('.dialog-alerts .toast');if(activeNotice)app.append(activeNotice);
      state.dialog=null;state.dialogData={};shadow.querySelector('.overlay')?.remove();frame.inert=false;
      if(focusBeforeDialog?.isConnected)focusBeforeDialog.focus({preventScroll:true});else shadow.querySelector('[data-action="appearance"]')?.focus({preventScroll:true});
      syncCapture();nativeWidgets?.mount();
    }
    let progressSerial=0;
    function exportRows(){
      const data=state.dialogData,q=(data.exportQuery||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase();
      const items=state.nodes.filter(n=>nicePath(n.path).normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase().includes(q));
      // Resolve the active ancestry once per search, not once for every sort comparison.
      const roots=[...new Set(state.profile.studies.filter(s=>s.active).flatMap(s=>s.deck_ids).map(id=>state.map.get(String(id))?.path).filter(Boolean))];
      const active=new Set(items.filter(n=>roots.some(r=>n.path===r||n.path.startsWith(r+'::'))).map(n=>n.id));
      items.sort((a,b)=>(data.exportSort==='name'?0:Number(active.has(b.id))-Number(active.has(a.id)))||Model.compareNames({name:a.path},{name:b.path}));
      return `<p class="note">${items.length} matching folders or decks · ${data.exportSort==='name'?'Natural name order':'Active classes first'}</p><div class="export-list">${items.slice(0,data.exportLimit||50).map(n=>`<button type="button" data-action="export-select" data-id="${esc(n.id)}" class="export-row"><span class="export-icon">${icon(n.children.length?'folder':'layers',20)}</span><span><strong>${esc(n.name)}</strong><small>${esc(nicePath(n.path))}</small><small>${n.children.length?'Includes subdecks':'This deck'}${active.has(n.id)?' · Active class':''}</small></span>${icon('arrow',16)}</button>`).join('')||'<p class="note">No folder or deck matches that search. Your selection has not changed.</p>'}</div>${items.length>(data.exportLimit||50)?btn('export-more','Show more','down','secondary'):''}`;
    }
    function progressContent(d){
      const max=Math.max(1,...d.daily.map(x=>x.reviews));
      return `<div class="progress-summary"><div><strong>${fmt(d.reviews)}</strong><span>Answer events</span></div><div><strong>${fmt(d.cards)}</strong><span>Distinct cards</span></div><div><strong>${fmt(d.minutes)}</strong><span>Recorded minutes</span></div><div><strong>${d.days_studied} / ${d.days}</strong><span>Study days</span></div></div><section class="progress-chart" aria-label="Daily answer events"><div class="progress-bars">${d.daily.map(x=>`<div class="progress-day" title="${esc(x.label)}: ${x.reviews} answer events; ${x.minutes} minutes"><div style="--bar-height:${Math.max(1,x.reviews/max*100)}%"></div><small>${esc(x.label.slice(5))}</small></div>`).join('')}</div></section><p class="note">${d.again} Again answers (${d.reviews?Math.round(d.again/d.reviews*100):0}% of recorded answers). This is not a retention or mastery score. ${d.deck_count} current decks in scope.</p><details class="progress-detail"><summary>Daily numbers and definitions</summary><table><thead><tr><th>Study day</th><th>Answers</th><th>Cards</th><th>Again</th><th>Minutes</th></tr></thead><tbody>${d.daily.map(x=>`<tr><td>${esc(x.label)}</td><td>${x.reviews}</td><td>${x.cards}</td><td>${x.again}</td><td>${x.minutes}</td></tr>`).join('')}</tbody></table><p>Days follow Anki’s day rollover. Card counts across days cannot be added to get distinct cards for the whole period.</p></details><h3 class="progress-deck-title">Where you spent time</h3><div class="progress-decks">${d.decks.map(x=>`<div><span>${esc(nicePath(x.name))}</span><strong>${fmt(x.reviews)} answers</strong><small>${x.minutes} min</small></div>`).join('')||'<p>No recorded answers in this scope and period. Choose All decks to look outside your active classes.</p>'}</div><p class="note">${esc(d.attribution)} Recorded time follows Anki’s per-answer time cap. Independent practice is separate.</p>`;
    }
    async function fetchProgress(){
      const serial=++progressSerial,data=state.dialogData,scopeId=data.progressScope||'active',days=data.progressDays||7;
      const out=shadow.getElementById('progress-results');if(out)out.innerHTML='<p class="note" role="status">Reading study history…</p>';
      try{const result=boot.preview?demoProgress(scopeId,days):await request('study_progress',{scope:scopeId,days});if(serial!==progressSerial||state.dialog!=='study-progress')return;const el=shadow.getElementById('progress-results');if(el)el.innerHTML=progressContent(result);}
      catch(e){if(serial===progressSerial&&state.dialog==='study-progress'){const el=shadow.getElementById('progress-results');if(el)el.innerHTML=`<p class="note" role="alert">${esc(e.message)}</p>${btn('progress-refresh','Try again','refresh','secondary')}`;}}
    }
    function demoProgress(scope,days){const daily=Array.from({length:days},(_,i)=>({label:new Date(Date.UTC(2026,8,12-days+i+1)).toISOString().slice(0,10),reviews:(i*17+23)%71,cards:20,again:i%4,minutes:Math.round(((i*17+23)%71)/3)}));return {scope,days,daily,deck_count:9,reviews:daily.reduce((a,x)=>a+x.reviews,0),cards:126,again:daily.reduce((a,x)=>a+x.again,0),minutes:daily.reduce((a,x)=>a+x.minutes,0),days_studied:daily.filter(x=>x.reviews).length,decks:[{id:'221',name:'Sample Cardiology::Lecture 1',reviews:142,minutes:36},{id:'241',name:'Sample Endocrine::Lecture 2',reviews:82,minutes:22}],attribution:'Illustrative preview data only. Native history is queried read-only in Anki.'};}
    function renderDialog(preserve=false){
      const activeNotice=shadow.querySelector('.toast');if(activeNotice)app.append(activeNotice);
      const scroll=shadow.querySelector('.dialog-body')?.scrollTop||0;
      shadow.querySelector('.overlay')?.remove();frame.inert=true;
      const type=state.dialog,data=state.dialogData,n=state.map.get(data.id);
      let title='',desc='',body='',footer='',wide=false;
      const nativeDialog=nativeWidgets?.dialog(type,data);
      if(nativeDialog){({title,desc,body,footer}=nativeDialog);wide=!!nativeDialog.wide;}
      else if(type==='owner'){title='Choose your appearance';desc='Choose which add-on styles Anki. Your cards and other features stay available. The home page reloads after saving.';wide=true;body=ownershipChoices();footer=btn('close-dialog','Keep current choice',null,'secondary');}
      else if(type==='practice-picker'){title='Choose the exam to practice';desc=data.matched?'Several saved plans use these focus folders. Choose the plan whose date, weights and filters you intend to use.':'Focus folders and exam plans are separate. Choose a saved exam explicitly; nothing starts or gets saved automatically.';wide=true;body=`<div class="practice-plan-picker">${(data.plans||[]).map(p=>`<button type="button" data-action="practice-pick" data-id="${esc(p.id)}"><span>${icon('calendar',20)}</span><span><strong>${esc(p.name)}</strong><small>${esc(p.due?new Date(p.due).toLocaleDateString():'No date')} · ${(p.deck_ids||[]).length} folders${p.filtered?' · Search-filtered':''}</small></span>${icon('arrow',15)}</button>`).join('')||'<p>No saved exam plans yet. Create a plan with the folders, date and practice settings you need.</p>'}</div>`;footer=btn('close-dialog','Back',null,'secondary')+btn('practice-plans','Exam Studio','calendar','secondary','data-view="overview"');}
      else if(type==='export-picker'){title='Export or share cards';desc='Find the folder or deck you want, then choose Anki’s normal format and destination options. Nothing is exported until you confirm it there.';wide=true;
        body=`<div class="export-controls"><label>Find a folder or deck<input id="export-search" type="search" value="${esc(data.exportQuery||'')}" placeholder="Search the full folder path" aria-describedby="export-help"></label><label>Sort<select id="export-sort"><option value="active">Active classes first</option><option value="name">Name A–Z</option></select></label></div><p id="export-help" class="note export-help">Choose a parent folder to include its subdecks, or choose one deck for a focused share. Anki opens the familiar export dialog so you keep control of file type, media, and destination.</p><div id="export-results">${exportRows()}</div>`;
        footer=btn('export-all','All decks & export options','export','secondary')+btn('close-dialog','Cancel',null,'quiet');}
      else if(type==='study-progress'){title='Study progress';desc='See your Anki review activity for the classes you choose. Practice results stay separate.';wide=true;
        body=`<div class="progress-controls"><label>Material<select id="progress-scope"><option value="active">All active classes</option>${state.profile.studies.filter(s=>s.active).map(g=>`<option value="${esc(g.id)}">${esc(g.name)}</option>`).join('')}<option value="all">All decks</option></select></label><label>Period<select id="progress-days"><option value="7">7 study days</option><option value="30">30 study days</option></select></label>${btn('progress-refresh','Refresh','refresh','quiet')}</div><div id="progress-results" aria-live="polite"><p class="note">Reading study history…</p></div>`;
        footer=btn('progress-native','All Anki statistics','chart','secondary')+btn('close-dialog','Done','check','primary');setTimeout(fetchProgress,0);}
      else if(type==='quick-session'){title='Choose a lecture';desc='Study one lecture with your usual Anki schedule.';wide=true;body='<div class=quick-lectures>'+quickChoices()+'</div><p class=note>Counts show what Anki can offer now. When nothing is available, Anki shows when you can study again.</p>';footer=btn('close-dialog','Back to desk','back','secondary');}
      else if(type==='home-edit'){
        title='Arrange widgets';desc='Choose a starting layout or customize the live widgets below. Their original controls remain in place.';wide=true;
        const prefs=data.layout, metadata=new Map(data.widgets.map(w=>[w.id,w]));
        body=`${state.config.visual_owner==='atelier'?`<div class="widget-presets"><div><strong>Page layout</strong><small>Balanced fits the reward and statistics together. Original keeps the other add-on’s saved positions.</small></div><div>${btn('home-balanced','Balanced layout','grid','secondary',`aria-pressed="${state.config.widget_mode!=='original'&&!state.profile.home_layout?.enabled}"`)}${btn('home-original','Original positions','back','secondary',`aria-pressed="${state.config.widget_mode==='original'&&!state.profile.home_layout?.enabled}"`)}</div></div>`:''}<div class="home-editor-intro"><span class="build-label">ATELIER ${esc(boot.version)}</span><p>Show, hide, reorder, and resize widgets from your installed add-ons. Their original controls stay available.</p></div><div class="setting-row"><div><strong>Columns</strong><small>Automatically reduces to fit a narrow window.</small></div><select id="home-columns" aria-label="Widget columns">${[1,2,3,4].map(n=>`<option value="${n}" ${prefs.columns===n?'selected':''}>${n}</option>`).join('')}</select></div><div class="home-widget-list">${prefs.items.map((w,i)=>{const m=metadata.get(w.id);return `<div class="home-widget-row ${w.visible?'':'is-hidden'}" data-widget-row="${esc(w.id)}"><label class="home-widget-name"><input type="checkbox" data-home-visible="${esc(w.id)}" ${w.visible?'checked':''} ${m.available?'':'disabled'}><span><strong>${esc(m.title)}</strong><small>${m.available?esc(m.source)+(m.reflow?' · Live grid widget':' · Original position retained'):'Not loaded on this page; saved choice is retained'}</small></span></label><div class="home-widget-tools">${w.id==='widget.exam-sprout-countdowns'?'<label>Width<select disabled aria-label="Exam Sprout width"><option>Full width</option></select></label><label>Height<select disabled aria-label="Exam Sprout height"><option>Fit countdowns</option></select></label>':`<label>Width<select data-home-size="${esc(w.id)}" aria-label="Width of ${esc(m.title)}">${[['small','One column'],['wide','Two columns'],['full','Full width']].map(([v,l])=>`<option value="${v}" ${w.size===v?'selected':''}>${l}</option>`).join('')}</select></label><label>Height<select data-home-height="${esc(w.id)}" aria-label="Height of ${esc(m.title)}">${[['auto','Original height'],['short','Compact'],['tall','Tall']].map(([v,l])=>`<option value="${v}" ${w.height===v?'selected':''}>${l}</option>`).join('')}</select></label>`}<div class="widget-order">${ib('home-up','Move '+m.title+' earlier','up',`data-id="${esc(w.id)}" ${i===0?'disabled':''}`)}${ib('home-down','Move '+m.title+' later','down',`data-id="${esc(w.id)}" ${i===prefs.items.length-1?'disabled':''}`)}</div></div></div>`;}).join('')||'<p class="note">No supported widgets are currently loaded. Enable them in the add-on that provides them, then return and rescan.</p>'}</div><div class="home-editor-actions">${btn('external-layout','Open Onigiri settings','external','secondary')}${btn('home-rescan','Rescan widgets','refresh','quiet')}${btn('home-reset','Restore original layout','back','quiet')}</div><p class="note">Arrange widgets already provided by your installed add-ons. Some widgets keep their own layout. Hiding a widget here does not disable its add-on.</p><p class="note">This changes only the shared home. The full Atelier folder organizer is still one click away. Your exam selections and card scheduling are unchanged.</p>`;
        footer=btn('close-dialog','Cancel',null)+btn('home-apply','Save layout','check','primary');
      }else if(type==='appearance'){
        title='Find your place to focus.';desc=`${THEMES.length} distinct worlds. Familiar controls. Choose the light and materials that suit you.`;wide=true;
        const owns=state.config.visual_owner==='atelier';
        body=`<div class="owner-setting"><span><strong>${owns?'Atelier owns appearance':state.config.visual_owner==='onigiri'?'Onigiri owns appearance':'Your original theme owns appearance'}</strong><small>One visual owner. Switching reloads the home screen safely.</small></span>${btn('owner-settings','Change owner','palette','secondary')}</div>${owns?'<div class="world-browser-head"><p>Same study space. A different atmosphere.</p><div class="world-lighting" role="group" aria-label="World lighting">'+[['all','All worlds'],['dark','Dark'],['light','Light']].map(([id,label])=>'<button type="button" data-action="world-filter" data-filter="'+id+'" aria-pressed="'+(id==='all')+'">'+label+'</button>').join('')+'</div></div><p class="world-count" id="world-filter-count" role="status"></p><div class="themes">'+themeTiles()+'</div>':'<p class="note">Your chosen add-on keeps control of the home page and reviewer. Atelier adds an optional organizer without changing that add-on’s saved theme.</p>'}<div class="settings-label">COMFORT & MOVEMENT</div><div class="setting-row"><div><strong>Layout spacing</strong><small>Comfortable cards or a closer view for a larger library.</small></div><select id="setting-density" aria-label="Layout spacing"><option value="comfortable" ${state.config.density==='comfortable'?'selected':''}>Comfortable</option><option value="compact" ${state.config.density==='compact'?'selected':''}>Compact</option></select></div><div class="setting-row"><div><strong>Gentle motion</strong><small>Short hover and press responses. System reduced motion takes priority.</small></div><button type="button" class="switch" data-action="toggle-setting" data-setting="motion" role="switch" aria-label="Gentle motion" aria-checked="${state.config.motion}"></button></div>${owns?`<div class="setting-row"><div><strong>Ambient surfaces</strong><small>Preset-specific gradients. No moving light behind card text.</small></div><button type="button" class="switch" data-action="toggle-setting" data-setting="ambience" role="switch" aria-label="Ambient surfaces" aria-checked="${state.config.ambience!==false}"></button></div><div class="settings-label">REVIEW EXPERIENCE</div><div class="setting-row"><div><strong>Reviewer theme</strong><small>Match ordinary text cards to your world. Custom interactive cards keep their own design.</small></div><select id="setting-review-style" aria-label="Reviewer theme"><option value="adaptive" ${state.config.review_style==='adaptive'?'selected':''}>Adaptive</option><option value="controls" ${state.config.review_style==='controls'?'selected':''}>Controls only</option><option value="off" ${state.config.review_style==='off'?'selected':''}>Original Anki</option></select></div><div class="setting-row"><div><strong>Reading width</strong><small>Adjust text-card width. Images and occlusion masks keep their alignment.</small></div><select id="setting-review-width" aria-label="Reading width"><option value="standard" ${state.config.review_width==='standard'?'selected':''}>Focused</option><option value="wide" ${state.config.review_width==='wide'?'selected':''}>Wide</option></select></div><div class="setting-row"><div><strong>Review context</strong><small>Compact shows just the lecture. Full path appears on demand.</small></div><select id="setting-review-context" aria-label="Review context"><option value="compact" ${state.config.review_context==='compact'?'selected':''}>Compact · lecture only</option><option value="full" ${state.config.review_context==='full'?'selected':''}>Full · title and folder path</option><option value="hidden" ${state.config.review_context==='hidden'?'selected':''}>None · card only</option></select></div>`:'<p class="note">Your original theme controls the reviewer. Atelier’s card, toolbar and shared-home styles are inactive in this mode.</p>'}${owns?`<div class="setting-row"><div><strong>Match native Anki tools</strong><small>Match supported Anki tool windows without removing their controls.</small></div><button type="button" class="switch" data-action="toggle-setting" data-setting="native_surfaces" role="switch" aria-label="Match native Anki tools" aria-checked="${state.config.native_surfaces!==false}"></button></div>`:''}<div class="settings-label">COMPATIBILITY</div>${!owns?`<div class="setting-row"><div><strong>Exam buttons on original deck rows</strong><small>Optional + / ✓ controls and exam context menu. Off leaves the original sidebar untouched.</small></div><button type="button" class="switch" data-action="toggle-setting" data-setting="companion_shortcuts" role="switch" aria-label="Exam buttons on original deck rows" aria-checked="${state.config.companion_shortcuts}"></button></div>`:''}<div class="compatibility-actions">${btn('rescan-makeovers','Check installed makeovers','refresh','secondary')}</div><div class="setting-row"><div><strong>Match Exam Studio</strong><small>One world across library, planning and practice. Companion mode keeps the planner’s own design.</small></div><button type="button" class="switch" data-action="toggle-setting" data-setting="match_sprout" role="switch" aria-label="Match Exam Studio" aria-checked="${state.config.match_sprout}"></button></div><p class="note">Exam Studio is included. Plans and results stay in this Anki profile. Focus folders are shortcuts to your decks, not copies of your exam plans.</p>`;
        footer=`<span id="save-state" class="save-state" role="status">${state.saveStatus}</span>`+btn('close-dialog','Done','check','primary');
      }else if(type==='studies'){
        title='Make room for what’s next.';desc='Keep one or several exams active. Finished studies leave the desk, not your collection.';wide=true;
        body=`<div class="setting-row focus-setting"><div><strong>Focus on active studies</strong><small>Dashboard totals and study shortcuts use only the studies selected below.</small></div><button type="button" class="switch" role="switch" aria-label="Focus on active studies" aria-checked="${state.profile.focus_enabled}" data-action="focus-toggle"></button></div><div class="study-rows">${studyRows()}</div><p class="note">Selecting a parent and its child does not count the branch twice. Exam dates are reminders, not readiness scores. Finishing a study does not suspend cards; outside Atelier, their due dates are unchanged.</p>`;
        footer=btn('new-study','Add active study','plus','primary')+btn('close-dialog','Done','check');
      }else if(type==='study-edit'){
        const draft=data.draft;title=data.id?'Edit your study.':'Set an active study.';desc='An exam, a course, or anything you want to keep in focus.';wide=true;
        body=`<form id="study-form"><div class="study-fields"><label class="field">Study name<input id="study-name" required maxlength="100" placeholder="e.g. Cardiology · Exam 3" value="${esc(draft.name)}" autocomplete="off"></label><label class="field date-field">Exam date <span class="optional">optional</span><input id="study-date" type="date" value="${esc(draft.date)}"></label></div><div class="picker-heading"><strong>Choose folders or decks — combine parents for one exam</strong><span>Each parent includes its subdecks; overlaps are counted once.</span></div><label class="picker-search">${icon('search',16)}<input id="picker-search" type="search" placeholder="Find a course, exam or deck…" value="${esc(data.search)}" autocomplete="off"></label><div class="deck-picker" id="deck-picker">${studyPicker()}</div><div id="picker-summary" class="picker-summary">${pickerSummary()}</div><div class="selected-chips" id="selected-chips">${selectedChips()}</div><p class="note">Select every parent folder or deck you want to sit together in this exam. Each selection stays in its original folder and keeps its existing schedule.</p><div class="form-error" id="form-error" role="alert"></div></form>`;
        footer=btn('close-dialog','Cancel',null)+`<button type="submit" form="study-form" class="primary">${icon('focus',16)}Save active study</button>`;
      }else if(type==='study-branch'&&n){
        title='Study this whole folder?';desc=n.name;
        body=`<p class="note">Study this folder and its lectures together. The lecture label shows where each card belongs. Your cards stay in their original decks.</p><label class="field" for="folder-study-order">Card order<select id="folder-study-order"><option value="shuffle" selected>Shuffle between lectures</option><option value="current">Keep current Anki order</option></select></label><p class="note">Shuffle mixes eligible new cards and due reviews across lectures. Anki still controls their new/review mix, learning-step timing, daily limits, and sibling burying.</p><details class="folder-order-details"><summary>What changes?</summary><p class="note">Shuffle saves this parent folder’s display order in Anki. If its options preset is shared, a copy is assigned only to this parent. Other settings and subdeck presets stay the same. The order stays saved and syncs with Anki; it is not a temporary practice session. It stops prioritizing oldest-due reviews first.</p><p class="note">Use Anki’s Undo before reviewing to reverse the setting change, or open Deck options to change the order or reselect your original preset later. Keep current Anki order makes no option changes; it does not restore an earlier preset.</p></details><div class="form-error" id="folder-study-error" role="alert"></div>`;
        footer=btn('close-dialog','Choose a lecture','back')+btn('study','Study whole folder','play','primary',`data-id="${n.id}" data-confirmed="true"`);
      }else if(type==='remove-study'){
        const study=state.profile.studies.find(s=>s.id===data.id);title='Remove this study shortcut?';desc=study?.name||'';body='<p class="note">This removes only the local Atelier study setup. It does not delete folders, decks, notes or cards.</p>';footer=btn('close-dialog','Cancel',null)+btn('confirm-remove','Remove shortcut','close','primary',`data-id="${data.id}"`);
      }else if(type==='create'||type==='rename'||type==='move'){
        const moving=type==='move',renaming=type==='rename',kind=data.kind||'deck',parent=data.parent||(moving?n?.parent:state.location)||'0';
        title=moving?'Move to a folder.':renaming?'A clearer name.':kind==='folder'?'Create a folder.':'Create a deck.';
        desc=moving?`Move “${n?.name||''}” and its subfolders together.`:renaming?'Keep the contents. Change the name.':'Choose where it belongs. No special naming syntax needed.';
        body=`<form id="organize-form">${!moving?`<label class="field">${kind==='folder'?'Folder':'Deck'} name<input id="entry-name" required maxlength="120" value="${esc(renaming?n?.name:'')}" placeholder="${kind==='folder'?'e.g. Exam 3':'e.g. Bradycardia'}" autocomplete="off"></label>`:''}${!renaming?`<label class="field">${moving?'Move into':'Create inside'}<select id="entry-parent">${parentOptions(parent,moving?data.id:'')}</select></label>`:''}<div class="path-preview">${icon('folder',18)}<span id="path-preview"></span></div><p class="note">${moving?'This moves the folder in Anki. Its new parent’s daily limits may affect which cards are offered. You can undo the move in Anki.':renaming?'Subfolders follow the new parent name. Your cards and review history stay intact.':'A folder is a normal Anki parent deck. It can hold cards and other decks, so your structure still works without Atelier.'}</p><div id="form-error" class="form-error" role="alert"></div></form>`;
        footer=btn('close-dialog','Cancel',null)+`<button type="submit" form="organize-form" class="primary">${moving?'Move here':renaming?'Save name':'Create '+kind}${icon('arrow',16)}</button>`;
      }else if(type==='organize'&&n){
        title=n.name;desc=nicePath(n.path);
        body=`<div class="menu-actions">${btn('study','Study in Anki','play','menu-action',`data-id="${n.id}"`)}${btn('quick-exam',exactExams(n).length?'Remove from active exams':'Set as upcoming exam','focus','menu-action',`data-id="${n.id}"`)}${btn('plan-folder','Create exam plan','calendar','menu-action',`data-id="${n.id}"`)}${btn('focus-deck','Custom exam setup…','edit','menu-action',`data-id="${n.id}"`)}${btn('rename','Rename','edit','menu-action',`data-id="${n.id}"`)}${!n.filtered?btn('move','Move to another folder','move','menu-action',`data-id="${n.id}"`):''}${!n.filtered?btn('create','New subfolder here','plus','menu-action',`data-kind="folder" data-parent="${n.id}"`):''}${btn('browse','Browse cards','layers','menu-action',`data-id="${n.id}"`)}${btn('export-deck','Export / share this deck…','export','menu-action',`data-id="${n.id}"`)}${btn('options','Anki deck options','palette','menu-action',`data-id="${n.id}"`)}${btn('folder-label',state.profile.folders.includes(n.id)?'Remove folder label':'Show as a folder','folder','menu-action',`data-id="${n.id}"`)}</div><div class="settings-label">FOLDER COLOR</div><div class="color-options">${['violet','blue','rose','green','amber','cyan'].map(c=>`<button type="button" class="color-option tone-${c} ${tone(n)===c?'selected':''}" data-action="color" data-id="${n.id}" data-color="${c}" aria-label="${c} folder color" aria-pressed="${tone(n)===c}"></button>`).join('')}</div><p class="note">Export / share opens Anki’s normal format, media, and destination choices for this folder or deck. Nothing is copied or published until you confirm it in Anki.</p>`;footer=btn('close-dialog','Done','check','primary');
      }else if(type==='help'){
        title='Find your way, without the guesswork.';desc='Your existing structure, made easier to navigate.';
        body=`<div class="help-items"><div>${icon('folder',23)}<span><strong>Click a folder to look inside.</strong><p>The arrow beside its name expands the sidebar. It never moves your cards.</p></span></div><div>${icon('up',23)}<span><strong>Parent takes you up one level.</strong><p>Back returns to the place you last visited. Every name in the breadcrumb path is clickable.</p></span></div><div>${icon('refresh',23)}<span><strong>Recent is your shortcut shelf.</strong><p>Recently opened remembers visits. Recently added tracks decks first seen after Atelier starts tracking—not the creation date of imported cards.</p></span></div><div>${icon('focus',23)}<span><strong>Active studies are not new decks.</strong><p>Choose the existing exam folders. Old exams stay in All folders but leave your focus totals.</p></span></div></div>`;footer=btn('close-dialog','Got it','check','primary');
      }else if(type==='preview-action'){
        title=boot.preview?'Anki takes it from here.':'This tool is not available yet';desc=boot.preview?'This file is an interface preview with sample data.':'Your work has not been changed.';body=`<p class="note">${esc(data.message||'The installed add-on opens Anki’s native tools. This preview does not contain a live collection.')}</p>`;footer=btn('close-dialog',boot.preview?'Back to the preview':'Close','back','primary');
      }else{closeDialog(true);return;}
      const overlay=document.createElement('div');overlay.className='overlay';
      overlay.innerHTML=`<section class="dialog ${wide?'wide':''}" role="dialog" aria-modal="true" aria-labelledby="atelier-dialog-title" tabindex="-1"><header class="dialog-header"><div><h2 id="atelier-dialog-title">${esc(title)}</h2><p>${esc(desc)}</p></div>${ib('close-dialog','Close dialog','close')}</header><div class="dialog-alerts" aria-live="polite"></div><div class="dialog-body">${body}</div><footer class="dialog-footer">${footer}</footer></section>`;
      app.append(overlay);if(type==='study-progress'){const select=shadow.getElementById('progress-scope');if(data.progressScope&&[...select.options].some(o=>o.value===data.progressScope))select.value=data.progressScope;else data.progressScope=select.value;const days=shadow.getElementById('progress-days');days.value=String(data.progressDays||7);}
      if(activeNotice)overlay.querySelector('.dialog-alerts').append(activeNotice);updatePath();syncCapture();if(type==='appearance')filterWorlds(data.worldFilter||'all');
      if(preserve)overlay.querySelector('.dialog-body').scrollTop=scroll;
      requestAnimationFrame(()=>{const target=shadow.getElementById('entry-name')||shadow.getElementById('study-name')||overlay.querySelector('.dialog');target?.focus({preventScroll:true});});
    }
    function selectedChips(){
      return state.dialogData.draft.deck_ids.map(id=>`<button type="button" class="selected-chip" data-action="unpick" data-id="${id}" title="Remove this selection">${esc(state.map.get(id)?.name||'Missing deck '+id)}${icon('close',12)}</button>`).join('');
    }
    function refreshPickerSummary(){
      const summary=shadow.getElementById('picker-summary');if(summary)summary.textContent=pickerSummary();
      const chips=shadow.getElementById('selected-chips');if(chips)chips.innerHTML=selectedChips();
    }
    function updatePath(){
      const target=shadow.getElementById('path-preview');if(!target)return;
      const n=state.map.get(state.dialogData.id),name=shadow.getElementById('entry-name')?.value||n?.name||'New '+(state.dialogData.kind||'deck');
      const parent=shadow.getElementById('entry-parent')?.value||n?.parent||state.location;
      target.textContent='All folders › '+(state.map.has(parent)?nicePath(state.map.get(parent).path)+' › ':'')+name;
    }
    function busyDialog(value){state.busy=value;shadow.querySelectorAll('.dialog button,.dialog input,.dialog select').forEach(el=>el.disabled=value);}
    async function submitStudy(){
      if(state.busy)return;
      const draft={...state.dialogData.draft,name:shadow.getElementById('study-name').value.trim(),date:shadow.getElementById('study-date').value},error=shadow.getElementById('form-error');
      if(!draft.name||draft.name.length>100){error.textContent='Give the study a name of 1–100 characters.';return;}
      if(!draft.deck_ids.length){error.textContent='Choose at least one folder or deck.';return;}
      if(draft.deck_ids.length>500){error.textContent='Choose up to 500 folders or decks. Selecting a parent already includes its children.';return;}
      if(draft.date&&Model.dayState(draft.date,now())===null){error.textContent='Choose a valid exam date, or leave it blank.';return;}
      busyDialog(true);
      const ok=await updatePref({key:'study',value:draft},false);busyDialog(false);
      if(ok){closeDialog();go('desk');announce('Study saved. Your cards and their due dates are unchanged.');}
    }
    async function submitOrganization(){
      if(state.busy)return;
      const type=state.dialog,data=state.dialogData,n=state.map.get(data.id),error=shadow.getElementById('form-error');
      const name=shadow.getElementById('entry-name')?.value.trim(),parent=shadow.getElementById('entry-parent')?.value||'0';
      if(type!=='move'&&(!name||name.includes('::')||/[<>\x00-\x1f]/.test(name)||name.startsWith(':')||name.endsWith(':'))){error.textContent='Enter a plain name. Choose the location below instead of typing ::.';return;}
      const payload=type==='create'?{kind:data.kind||'deck',name,parent}:{id:data.id,expected:n?.path,...(type==='move'?{parent}:{name})};
      busyDialog(true);
      try{const out=await request(type,payload);busyDialog(false);closeDialog();await load();if(type==='create'&&out.id)go('library',parent);announce(out.warning|| (type==='create'?'Created. Open it to add decks or cards.':'Updated. Undo is available in Anki’s Edit menu.'));}
      catch(e){busyDialog(false);error.textContent=e.message;}
    }
    function closeMenu(restore=true){
      const previous=state.menu?.anchor;shadow.querySelector('.context-menu')?.remove();state.menu=null;
      if(restore&&previous?.isConnected)previous.focus({preventScroll:true});syncCapture();
    }
    function openMenu(n,x,y,anchor,originalTarget=null){
      closeMenu(false);state.menu={id:n.id,anchor,originalTarget,x,y};
      const menu=document.createElement('div');menu.className='context-menu';menu.setAttribute('role','menu');menu.setAttribute('aria-label','Folder actions');
      menu.innerHTML=`<div class="context-label">${esc(n.name)}</div>${btn('quick-exam',exactExams(n).length?'Remove from active exams':'Set as upcoming exam',exactExams(n).length?'close':'focus','context-action',`data-id="${n.id}" role="menuitem"`)}${btn(originalTarget?'shared-navigate':'navigate','Browse contents','folder','context-action',`data-id="${n.id}" role="menuitem"`)}${btn('study',children(n.id).length?'Study entire folder…':'Study this lecture','play','context-action',`data-id="${n.id}" role="menuitem"`)}${btn('export-deck','Export / share…','export','context-action',`data-id="${n.id}" role="menuitem"`)}<div class="context-divider"></div>${btn('create','New subfolder','plus','context-action',`data-kind="folder" data-parent="${n.id}" role="menuitem"`)}${btn('rename','Rename','edit','context-action',`data-id="${n.id}" role="menuitem"`)}${btn('organize','More options…','more','context-action',`data-id="${n.id}" role="menuitem"`)}`;
      if(originalTarget)menu.insertAdjacentHTML('beforeend',`<div class="context-divider"></div>${btn('original-menu','Original folder menu…','external','context-action','role="menuitem"')}<p class="context-tip">Shift + right-click also keeps the original menu.</p>`);
      app.append(menu);const r=menu.getBoundingClientRect();menu.style.left=Math.max(8,Math.min(x,innerWidth-r.width-8))+'px';menu.style.top=Math.max(8,Math.min(y,innerHeight-r.height-8))+'px';menu.querySelector('button')?.focus({preventScroll:true});syncCapture();
    }
    function undoNotice(text,studies){
      undoStudy=studies;announce(text);
      const toast=shadow.querySelector('.toast');if(toast){const b=document.createElement('button');b.type='button';b.dataset.action='undo-exam';b.textContent='Undo';b.className='toast-undo';toast.insertBefore(b,toast.querySelector('.toast-dismiss'));toast.dataset.duration='11000';clearTimeout(toastTimer);toastTimer=setTimeout(()=>{if(!toast.matches(':hover,:focus-within'))toast.remove();},11000);}
    }
    async function finishStudy(id){
      if(quickPending.has(id))return;quickPending.add(id);
      const before=state.profile.studies.find(x=>x.id===id);
      try{if(before&&await updatePref({key:'study_active',id,value:false})){closeDialog(true);undoNotice('Removed from active exams. Your decks are untouched.',[{...before}]);}}finally{quickPending.delete(id);}
    }
    async function quickExam(n){
      if(!n||quickPending.has(n.id))return;quickPending.add(n.id);
      const before=exactExams(n).map(x=>({...x})),active=!before.length;
      try{if(await updatePref({key:'quick_study',id:n.id,value:active})){closeDialog(true);if(active)announce(n.name+' is now active. Choose its lectures in Study desk.');else undoNotice('Exam removed from focus. All lectures stay in your library.',before);}}finally{quickPending.delete(n.id);}
    }
    async function handle(el){
      const a=el.dataset.action,id=el.dataset.id,n=state.map.get(id);
      if(state.busy)return;
      const originalMenu=state.menu;
      if(state.menu)closeMenu(false);
      if(a.startsWith('nw-')){await nativeWidgets.handle(a,id);return;}
      if(state.dialog==='widget-tools')closeDialog();
      switch(a){
        case 'world-filter':filterWorlds(el.dataset.filter);break;
        case 'tool-category':state.toolsGroup=el.dataset.category;render();break;
        case 'reset-tools':state.query='';state.toolsGroup='all';render();remember();shadow.getElementById('atelier-search')?.focus();break;
        case 'remote-open':{el.disabled=true;try{if(boot.preview)announce('The installed add-on opens Remote controls, with a safe button test and optional mappings.');else await request('remote_setup',{});}finally{if(el.isConnected)el.disabled=false;}break;}
        case 'native-tool':{if(el.dataset.command==='export'){openDialog('export-picker');break;}el.disabled=true;try{await request('native_tool',{command:el.dataset.command});}finally{if(el.isConnected)el.disabled=false;}break;}
        case 'export-picker':openDialog('export-picker');break;
        case 'export-select':await request('export_deck',{id});closeDialog();break;
        case 'export-deck':closeDialog(true);await request('export_deck',{id});break;
        case 'export-all':await request('native_tool',{command:'export'});closeDialog();break;
        case 'export-more':state.dialogData.exportLimit=(state.dialogData.exportLimit||50)+50;shadow.getElementById('export-results').innerHTML=exportRows();break;
        case 'study-progress':if(state.config.mode==='native')await updateConfig({mode:'workspace'},true);openDialog('study-progress');break;
        case 'progress-refresh':fetchProgress();break;
        case 'progress-native':await request('native_tool',{command:'stats'});break;
        case 'pip-groups':await request('suite_open',{view:'pip'});break;
        case 'focus-practice':await focusedPractice();break;
        case 'focus-pip':await focusedPip();break;
        case 'practice-pick':closeDialog();await request('suite_open',{view:'practice',id});break;
        case 'practice-plans':closeDialog();await request('suite_open',{view:'overview'});break;
        case 'authoring-open':await request('authoring_open',{view:el.dataset.view||'studio',...(el.dataset.deck?{deck_id:el.dataset.deck}:{})});break;
        case 'suite-open':await request('suite_open',{view:el.dataset.view||'overview',id:id||''});break;
        case 'suite-focus':{const result=await request('suite_focus',{id});state.profile=normalizeProfile(result.profile);go('desk');announce(result.reused?'Existing focus reopened. No duplicate was created.':'Exam folders pinned for normal review.');break;}
        case 'plan-folder':if(n)await request('suite_open',{view:'new',setup:{name:n.name,deck_ids:[n.id]}});break;
        case 'sprout-open': await request('sprout_open'); break;
        case 'sprout-practice': if(!sproutAvailable()){openDialog('preview-action',{message:'Exam Studio is not ready. Open Tools → Atelier → Exam Sprout diagnostics. Do not enable a second standalone copy.'});break;}await request('sprout_practice');break;
        case 'quick-session': openDialog('quick-session');break;
        case 'owner-settings':openDialog('owner');break;
        case 'rescan-makeovers':{const r=await request('rescan_makeovers');boot.integrations={...boot.integrations,...r};openDialog('owner');break;}
        case 'choose-owner':{if(state.busy)break;state.busy=true;try{const cfg=await request('visual_owner',{owner:el.dataset.owner});if(boot.preview){document.documentElement.dataset.atelierShared='false';state.config={...state.config,...cfg};configSaved={...state.config};closeDialog();render({resetMain:true});}else{el.textContent='Applying appearance…';el.disabled=true;/* Native owner switch reloads the document. Never sample a partly themed old page. */}}finally{state.busy=false;}break;}
        case 'study-now': if(n&&!n.children.length){closeDialog();await request('study_now',{id});}break;
        case 'shared-desk':await updateConfig({mode:'workspace'},true);go('desk');break;
        case 'shared-organizer':await updateConfig({mode:'workspace'},true);go('library');break;
        case 'shared-navigate':await updateConfig({mode:'workspace'},true);go('library',id);break;
        case 'shared-study':await updatePref({key:'selected_study',value:id},false);await updateConfig({mode:'workspace'},true);go('desk');break;
        case 'original-menu':home?.originalMenu(originalMenu?.originalTarget,originalMenu?.x,originalMenu?.y);break;
        case 'home-balanced':case 'home-original':{const mode=a==='home-balanced'?'balanced':'original';if(state.profile.home_layout?.enabled)await updatePref({key:'home_layout',value:{...state.profile.home_layout,enabled:false}},false);await updateConfig({widget_mode:mode},true);closeDialog();home?.refresh();announce(mode==='balanced'?'Balanced layout applied. Custom positions remain saved.':'Original widget positions restored.');break;}
        case 'home-edit':await updateConfig({mode:'native'},true);openDialog('home-edit');break;
        case 'home-rescan':home?.refresh();openDialog('home-edit');break;
        case 'home-up':case 'home-down':{const items=state.dialogData.layout.items,i=items.findIndex(x=>x.id===id),j=i+(a==='home-up'?-1:1);if(i>=0&&j>=0&&j<items.length){[items[i],items[j]]=[items[j],items[i]];renderDialog(true);}break;}
        case 'home-apply':{const draft=state.dialogData.layout;draft.enabled=true;state.busy=true;const ok=await updatePref({key:'home_layout',value:draft},false);state.busy=false;if(ok){closeDialog();render();home?.refresh();announce('Shared-home layout saved. Widgets remain in their original add-ons.');}break;}
        case 'home-reset':await updateConfig({widget_mode:'original'},true);if(await updatePref({key:'home_layout',value:{...state.profile.home_layout,enabled:false}})){home?.refresh();openDialog('home-edit');announce('Original widget layout restored.');}break;
        case 'external-layout':try{await request('external_layout');}catch(e){announce(e.message,true);}break;
        case 'quick-exam':await quickExam(n);break;
        case 'finish-study':await finishStudy(id);break;
        case 'undo-exam':{const saved=undoStudy;undoStudy=null;if(saved){for(const x of saved)await updatePref({key:'study',value:x},false);render();announce('Exam restored to active studies.');}break;}
        case 'peek':state.peek.has(id)?state.peek.delete(id):state.peek.add(id);render();break;
        case 'lecture-expand':state.collapsedLectures.has(id)?state.collapsedLectures.delete(id):state.collapsedLectures.add(id);render();break;
        case 'board-more':state.boardLimit+=100;render();break;
        case 'choose-lectures':{const target=shadow.getElementById('lecture-board')||shadow.querySelector('.library');const header=shadow.querySelector('.unified-topbar');if(target){target.style.scrollMarginTop=Math.ceil((header?.getBoundingClientRect().height||0)+20)+'px';target.scrollIntoView({block:'start',behavior:state.config.motion&&!matchMedia('(prefers-reduced-motion: reduce)').matches?'smooth':'auto'});target.focus({preventScroll:true});}break;}
        case 'widget-page':await openWidgets();break;
        case 'home':go('desk');break;
        case 'page':go(el.dataset.page);break;
        case 'navigate':go('library',id);break;
        case 'back':travel(true);break;
        case 'forward':travel(false);break;
        case 'up':go('library',state.map.get(state.location)?.parent||'0');break;
        case 'expand':state.expanded.has(id)?state.expanded.delete(id):state.expanded.add(id);render();break;
        case 'collapse-all':state.expanded.clear();render();break;
        case 'tree-more':state.treeLimit+=240;render();break;
        case 'mobile':state.mobile=true;render();shadow.querySelector('.drawer-close')?.focus();break;
        case 'close-nav':state.mobile=false;render();shadow.querySelector('[data-action="mobile"]')?.focus();break;
        case 'filter':if(state.page==='recent')state.recentTab=el.dataset.filter;else state.filter=el.dataset.filter;state.limit=60;render();break;
        case 'clear-search':state.query='';render({resetMain:true});remember();break;
        case 'more-results':state.limit+=60;shadow.getElementById('library-results').innerHTML=results();break;
        case 'view':await updateConfig({view:el.dataset.view},true);break;
        case 'favorite':if(n)await updatePref({key:'favorites',id,value:!favorite(n)});break;
        case 'folder-label':if(n){const ok=await updatePref({key:'folders',id,value:!state.profile.folders.includes(id)});if(ok)closeDialog();}break;
        case 'color':if(await updatePref({key:'color',id,value:el.dataset.color})){shadow.querySelectorAll('.color-option').forEach(x=>{const selected=x.dataset.color===el.dataset.color;x.classList.toggle('selected',selected);x.setAttribute('aria-pressed',String(selected));});}break;
        case 'theme':await updateConfig({theme:el.dataset.themeChoice});break;
        case 'toggle-setting':await updateConfig({[el.dataset.setting]:!state.config[el.dataset.setting]});break;
        case 'appearance':openDialog('appearance');break;
        case 'studies':openDialog('studies');break;
        case 'new-study':openDialog('study-edit');break;
        case 'edit-study':openDialog('study-edit',{id});break;
        case 'focus-deck':openDialog('study-edit',{deck:id});break;
        case 'focus-toggle':if(await updatePref({key:'focus_enabled',value:!state.profile.focus_enabled})){renderDialog(true);}break;
        case 'select-study':await updatePref({key:'selected_study',value:id});go('desk');break;
        case 'toggle-study':{
          const s=state.profile.studies.find(x=>x.id===id);if(s&&await updatePref({key:'study',value:{...s,active:!s.active}})){renderDialog(true);}break;
        }
        case 'remove-study':openDialog('remove-study',{id});break;
        case 'confirm-remove':if(await updatePref({key:'remove_study',value:id})){openDialog('studies');}break;
        case 'unpick':state.dialogData.draft.deck_ids=state.dialogData.draft.deck_ids.filter(x=>x!==id);shadow.getElementById('deck-picker').innerHTML=studyPicker();refreshPickerSummary();break;
        case 'picker-more':state.dialogData.limit+=80;{const list=shadow.getElementById('deck-picker'),pos=list.scrollTop;list.innerHTML=studyPicker();list.scrollTop=pos;}break;
        case 'help':openDialog('help');break;
        case 'create':openDialog('create',{kind:el.dataset.kind||'deck',parent:el.dataset.parent||state.location});break;
        case 'organize':if(n)openDialog('organize',{id});break;
        case 'rename':if(n)openDialog('rename',{id,kind:isFolder(n)?'folder':'deck'});break;
        case 'move':if(n)openDialog('move',{id});break;
        case 'close-dialog':closeDialog();break;
        case 'refresh':await load();break;
        case 'native':case 'provider-home':await openProvider();break;
        case 'workspace':await updateConfig({mode:'workspace'},true);if(!state.loaded)await load();break;
        case 'study':if(n&&children(n.id).length){
          if(el.dataset.confirmed!=='true'){openDialog('study-branch',{id});break;}
          const order=shadow.getElementById('folder-study-order')?.value;
          if(!['shuffle','current'].includes(order))break;
          const dialog=state.dialogData;
          state.busy=true;el.disabled=true;
          try{await request('study_folder',{id,expected:n.path,order});if(state.dialog==='study-branch'&&state.dialogData===dialog)closeDialog(true);}
          catch(e){const error=shadow.getElementById('folder-study-error');if(error)error.textContent=e.message;else announce(e.message,true);}
          finally{state.busy=false;if(el.isConnected)el.disabled=false;}
          break;
        }
        case 'browse':case 'options':case 'add':case 'import':case 'stats':case 'website':
          if(state.dialog)closeDialog();
          try{await request(a,id?{id}:{});}catch(e){announce(e.message,true);}break;
      }
    }
    shadow.addEventListener('click',event=>{const el=event.target.closest?.('[data-action]');if(el&&!el.disabled){event.preventDefault();handle(el).catch(e=>announce(e.message,true));}});
    shadow.addEventListener('submit',event=>{event.preventDefault();event.stopPropagation();(event.target.id==='study-form'?submitStudy():submitOrganization()).catch(e=>{busyDialog(false);announce(e.message,true);});});
    shadow.addEventListener('input',event=>{
      const id=event.target.id;
      if(id==='atelier-search'){
        const value=event.target.value,start=event.target.selectionStart;
        state.query=value;state.limit=60;render();const input=shadow.getElementById(id);input?.focus({preventScroll:true});try{input.setSelectionRange(start,start);}catch(_){}remember();
      }else if(id==='export-search'){state.dialogData.exportQuery=event.target.value;state.dialogData.exportLimit=50;shadow.getElementById('export-results').innerHTML=exportRows();}
      else if(id==='entry-name')updatePath();
      else if(id==='picker-search'){state.dialogData.search=event.target.value;state.dialogData.limit=80;shadow.getElementById('deck-picker').innerHTML=studyPicker();}
      else if(id==='study-name')state.dialogData.draft.name=event.target.value;
      else if(id==='study-date')state.dialogData.draft.date=event.target.value;
    });
    shadow.addEventListener('change',event=>{
      const el=event.target;
      if(nativeWidgets?.change(el))return;
      if(el.id==='export-sort'){state.dialogData.exportSort=el.value;shadow.getElementById('export-results').innerHTML=exportRows();return;}
      if(el.id==='progress-scope'||el.id==='progress-days'){state.dialogData[el.id==='progress-scope'?'progressScope':'progressDays']=el.id==='progress-days'?Number(el.value):el.value;fetchProgress();return;}
      if(state.dialog==='home-edit'){
        if(el.id==='home-columns'){state.dialogData.layout.columns=Number(el.value);return;}
        const id=el.dataset.homeVisible||el.dataset.homeSize||el.dataset.homeHeight;
        const item=state.dialogData.layout.items.find(x=>x.id===id);
        if(item){if(el.dataset.homeVisible){item.visible=el.checked;el.closest('.home-widget-row')?.classList.toggle('is-hidden',!el.checked);}else if(el.dataset.homeSize)item.size=el.value;else item.height=el.value;return;}
      }
      if(el.id==='setting-review-style'){updateConfig({review_style:el.value});return;}
      if(el.id==='setting-review-context'){updateConfig({review_context:el.value});return;}
      if(el.id==='setting-review-width'){updateConfig({review_width:el.value});return;}
      if(el.id==='atelier-sort')updateConfig({sort:el.value},true);
      else if(el.id==='setting-density')updateConfig({density:el.value},true);
      else if(el.id==='entry-parent')updatePath();
      else if(el.id==='active-study-selector'||el.id==='side-study-selector'){updatePref({key:'selected_study',value:el.value});}
      else if(el.dataset.pickDeck){const id=el.dataset.pickDeck;state.dialogData.draft.deck_ids=state.dialogData.draft.deck_ids.filter(x=>x!==id);if(el.checked)state.dialogData.draft.deck_ids.push(id);el.closest('.picker-row').classList.toggle('checked',el.checked);refreshPickerSummary();}
    });
    function syncCapture(){
      let el=shadow.activeElement;while(el?.shadowRoot?.activeElement)el=el.shadowRoot.activeElement;
      const capture=!!(state.config.mode!=='native'&&(state.dialog||state.mobile||state.menu||el&&(/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName)||el.isContentEditable)));
      if(capture===lastKeyCapture)return;lastKeyCapture=capture;
      request('focus',{active:capture}).catch(()=>{lastKeyCapture=!capture;});
    }
    shadow.addEventListener('focusin',event=>{syncCapture();const el=event.target,main=shadow.querySelector('.main'),bar=shadow.querySelector('.unified-topbar');if(!state.dialog&&!state.menu&&main&&bar&&main.contains(el)&&!bar.contains(el)&&el.matches?.(':focus-visible')){const top=bar.getBoundingClientRect().bottom+10,r=el.getBoundingClientRect();if(r.top<top)main.scrollTop-=top-r.top;}});shadow.addEventListener('focusout',()=>queueMicrotask(syncCapture));
    shadow.addEventListener('keydown',event=>{
      const origin=event.composedPath?.()[0]||event.target;
      const editable=/^(INPUT|TEXTAREA|SELECT)$/.test(origin.tagName)||origin.isContentEditable;
      if(state.menu){
        if(event.key==='Escape'){event.preventDefault();event.stopPropagation();closeMenu();return;}
        if(['ArrowDown','ArrowUp','Home','End'].includes(event.key)){event.preventDefault();event.stopPropagation();const items=[...shadow.querySelectorAll('.context-menu button')],at=items.indexOf(shadow.activeElement);items[event.key==='Home'?0:event.key==='End'?items.length-1:(at+(event.key==='ArrowDown'?1:-1)+items.length)%items.length]?.focus();return;}
        if(event.key==='Tab')closeMenu(false);
      }
      if(!editable&&(event.key==='ContextMenu'||event.shiftKey&&event.key==='F10')){const node=event.target.closest?.('[data-node]'),n=state.map.get(node?.dataset.node);if(n){event.preventDefault();const r=event.target.getBoundingClientRect();openMenu(n,r.left,r.bottom,event.target);return;}}
      if(state.dialog||state.mobile){
        event.stopPropagation();
        if(event.key==='Escape'){event.preventDefault();if(state.dialog)closeDialog();else{state.mobile=false;render();shadow.querySelector('[data-action="mobile"]')?.focus();}return;}
        if(event.key==='Tab'){
          const container=shadow.querySelector(state.dialog?'.dialog':'.sidebar'),items=[...container.querySelectorAll('button:not(:disabled),input:not(:disabled),textarea:not(:disabled),select:not(:disabled),summary,a[href],[tabindex="0"]')].filter(el=>el.getClientRects().length&&el.tabIndex>=0);
          const first=items[0],last=items[items.length-1],active=shadow.activeElement;
          if(event.shiftKey&&(active===first||active===container)){event.preventDefault();last?.focus();}
          else if(!event.shiftKey&&(active===last||active===container)){event.preventDefault();first?.focus();}
        }return;
      }
      if(editable){event.stopPropagation();if(event.key==='Escape'&&event.target.id==='atelier-search'){event.preventDefault();state.query='';render();shadow.getElementById('atelier-search')?.focus();}return;}
      if(event.key==='/'&&!event.ctrlKey&&!event.metaKey){event.preventDefault();event.stopPropagation();shadow.getElementById('atelier-search')?.focus();}
      if(event.altKey&&event.key==='ArrowLeft'){event.preventDefault();travel(true);}
      if(event.altKey&&event.key==='ArrowUp'){event.preventDefault();go('library',state.map.get(state.location)?.parent||'0');}
    });
    document.addEventListener('keydown',e=>{if(state.config.mode==='native'||state.dialog||e.defaultPrevented)return;if(e.key==='/'&&!e.ctrlKey&&!e.metaKey&&(document.activeElement===document.body||document.activeElement===host)){e.preventDefault();shadow.getElementById('atelier-search')?.focus();}});
    shadow.addEventListener('contextmenu',e=>{const card=e.target.closest?.('[data-node]'),n=state.map.get(card?.dataset.node);if(n){e.preventDefault();e.stopPropagation();openMenu(n,e.clientX,e.clientY,card.querySelector('button'));}});
    shadow.addEventListener('pointerdown',e=>{if(state.menu&&!e.target.closest?.('.context-menu'))closeMenu(false);});
    shadow.addEventListener('scroll',event=>{if(state.menu&&!event.target.closest?.('.context-menu'))closeMenu(false);},true);
    let dragging='';
    shadow.addEventListener('dragstart',e=>{const card=e.target.closest?.('[data-node]');if(card?.draggable){dragging=card.dataset.node;e.dataTransfer.setData('application/x-atelier-deck',dragging);e.dataTransfer.effectAllowed='move';card.classList.add('dragging');e.stopPropagation();}});
    shadow.addEventListener('dragover',e=>{const target=e.target.closest?.('[data-drop]');if(dragging&&target?.dataset.drop&&target.dataset.drop!==dragging){e.preventDefault();e.stopPropagation();target.classList.add('drop-target');}});
    shadow.addEventListener('dragleave',e=>e.target.closest?.('[data-drop]')?.classList.remove('drop-target'));
    shadow.addEventListener('drop',e=>{
      const target=e.target.closest?.('[data-drop]');shadow.querySelectorAll('.drop-target').forEach(el=>el.classList.remove('drop-target'));
      if(!dragging||!target?.dataset.drop)return;
      e.preventDefault();e.stopPropagation();const source=state.map.get(dragging),parent=state.map.get(target.dataset.drop);dragging='';
      if(!source)return;
      if(source.id===target.dataset.drop||parent?.path.startsWith(source.path+'::')){announce('A folder cannot be placed inside itself or its subfolders.',true);return;}
      if(source.parent===target.dataset.drop){announce('It is already in that folder.');return;}
      openDialog('move',{id:source.id,parent:target.dataset.drop});
    });
    shadow.addEventListener('dragend',()=>{dragging='';shadow.querySelectorAll('.dragging,.drop-target').forEach(el=>el.classList.remove('dragging','drop-target'));});
    window.addEventListener('resize',()=>{closeMenu(false);if(innerWidth>820&&state.mobile){state.mobile=false;render();}});
    // Reopen/focus never resets scroll. Appearance mutates tokens only; it does
    // not rebuild either the dialog, the library or the sidebar.
    function applyAppearance(message){
      if(!message||message.token!==boot.token||configPending)return false;
      const settings=message.settings||{};
      // Cross-window delivery is presentation-only. Never replace a form,
      // reload the collection, or bypass the owner-selection reload boundary.
      for(const key of ['theme','density','motion','ambience','review_style','review_width','review_context','native_surfaces','match_sprout']){
        if(Object.prototype.hasOwnProperty.call(settings,key))state.config[key]=settings[key];
      }
      configSaved={...state.config};setHost();updateThemeControls();return true;
    }
    function updateAuthoring(message){if(!message||message.token!==boot.token)return false;state.authoring=message.authoring||{available:false};const region=shadow.getElementById('atelier-authoring-hub');if(region)region.innerHTML=authoringHub();const inbox=shadow.getElementById('atelier-workflow-inbox');if(inbox)inbox.innerHTML=workflowInbox();nativeWidgets?.updateWork();return true;}
    window.AtelierMakeover=Object.freeze({receive,applyAppearance,updateAuthoring,openWidgets:message=>message?.token===boot.token?openWidgets():Promise.resolve(false),reload:load,version:boot.version,sharedDiagnostics:()=>({home:home?.diagnostics(),cohesion:window.AtelierCohesion?.diagnostics()}),openAppearance:()=>openDialog('appearance'),theme:()=>({name:state.config.theme,active:state.config.mode!=='native'}),
      diagnostics:()=>({version:boot.version,mode:state.config.mode,theme:state.config.theme,page:state.page,location:state.location,surface:state.config.mode==='native'?'original-provider':state.page==='widgets'?'atelier-widgets':'atelier-workspace',widgetsReady:!!nativeWidgets,loaded:state.loaded,pendingSettings:configPending,focusEnabled:state.profile.focus_enabled,focusRoots:scope().roots.map(n=>n.id),activeStudies:state.profile.studies.filter(s=>s.active).map(s=>s.id),lastStudied:state.profile.last_studied})});
    // Standalone preview uses the exact shipped renderer and clearly labeled
    // sample data. Only this adapter simulates collection changes.
    let demo;
    function demoData(){
      if(demo)return demo;
      try{const saved=JSON.parse(localStorage.getItem('atelier-preview-v070')||'null');demo=saved?.nodes&&Array.isArray(saved.nodes)?saved:JSON.parse(JSON.stringify(boot.demo));}
      catch(_){demo=JSON.parse(JSON.stringify(boot.demo));}
      demo.profile=normalizeProfile(demo.profile);return demo;
    }
    function demoSave(){try{localStorage.setItem('atelier-preview-v070',JSON.stringify(demo));}catch(_){} }
    async function demoRequest(action,data){
      const d=demoData();
      if(boot.demoDelay&&action==='settings')await new Promise(r=>setTimeout(r,boot.demoDelay));
      if(action==='load')return JSON.parse(JSON.stringify(d));
      if(action==='focus'||action==='ui'||action==='companion_palette')return true;
      if(action==='rescan_makeovers')return boot.integrations||{};
      if(action==='visual_owner'){d.settings={...d.settings,visual_owner:data.owner,mode:data.owner==='atelier'?'workspace':'native'};demoSave();return {...d.settings};}
      if(action==='native_tool'){window.dispatchEvent(new CustomEvent('atelier:preview-native',{detail:{command:data.command}}));openDialog('preview-action',{message:`The installed suite opens Anki’s ${data.command.replaceAll('_',' ')} tool with its original controls. No native action runs in this offline preview.`});return {opened:true};}
      if(action==='authoring_open'){window.dispatchEvent(new CustomEvent('atelier:preview-authoring',{detail:data}));openDialog('preview-action',{message:'In the installed suite, this opens the built-in Card Studio, not another add-on. Sources, drafts, masks and repair tools remain in one workspace.'});return {opened:true};}
      if(action==='suite_open'){window.dispatchEvent(new CustomEvent('atelier:preview-suite',{detail:data}));if(window.AtelierPreviewNavigate){window.AtelierPreviewNavigate(data);}else openDialog('preview-action',{message:'The installed suite opens its bundled Exam Studio. Plans, practice, saved sessions, readiness and Pip remain in the existing engine.'});return {opened:true};}
      if(action==='suite_focus'){const plan=(d.suite?.plans||boot.suite?.plans||[]).find(x=>x.id===data.id);if(!plan)throw new Error('No matching plan.');let study=d.profile.studies.find(s=>examKey(s)===examKey(plan));if(!study){study={id:'plan-'+plan.id,name:plan.name,deck_ids:plan.deck_ids,date:plan.due.slice(0,10),active:true};d.profile.studies.push(study);}study.active=true;d.profile.focus_enabled=true;d.profile.selected_study=study.id;demoSave();return {profile:JSON.parse(JSON.stringify(d.profile)),reused:true};}
      if(action==='sprout_practice'){window.dispatchEvent(new CustomEvent('atelier:preview-practice'));openDialog('preview-action',{message:'In Anki, this opens the Practice page in your existing Exam Sprout planner. Select its exam and build a practice sample there. It does not silently copy an Atelier exam or start a session.'});return true;}
      if(action==='sprout_open'){if(typeof window.pycmd==='function')window.pycmd('exam-sprout:open:');else openDialog('preview-action',{message:'In Anki this opens your existing Exam Sprout planner. No exams are copied or changed.'});return true;}
      if(action==='external_layout'){openDialog('preview-action',{message:'The installed add-on opens Onigiri’s settings when its public API is available. Enable additional widgets there; this standalone preview cannot change another add-on’s settings.'});return true;}
      if(action==='settings'){d.settings={...d.settings,...data};demoSave();return {...d.settings};}
      if(action==='preference'){
        const p=d.profile;
        if(data.key==='native_widgets'){p.native_widgets=window.AtelierNativeWidgets.normalize(data.value);}
        else if(data.key==='native_widget_note'){if(typeof data.value!=='string'||data.value.length>4000||data.value.includes('\0'))throw new Error('Keep notes to 4,000 characters.');p.native_widget_note=data.value;}
        else if(data.key==='home_layout'){p.home_layout=JSON.parse(JSON.stringify(data.value));}
        else if(data.key==='study'){
          const s=data.value;
          if(!s.name?.trim()||!s.deck_ids?.length)throw new Error('Name the study and choose its decks.');
          if(s.active&&p.studies.some(x=>x.active&&x.id!==s.id&&examKey(x)===examKey(s)))throw new Error('That folder selection is already an active exam. Open the existing exam to edit its name or date.');
          p.studies=p.studies.filter(x=>x.id!==s.id).concat([JSON.parse(JSON.stringify(s))]);p.focus_enabled=true;
          if(!p.studies.some(x=>x.id===p.selected_study&&x.active))p.selected_study='all';
        }else if(data.key==='quick_study'){
          let found=p.studies.find(x=>x.deck_ids.length===1&&x.deck_ids[0]===data.id&&x.active)||p.studies.find(x=>x.deck_ids.length===1&&x.deck_ids[0]===data.id);
          if(found){for(const x of p.studies.filter(x=>x.deck_ids.length===1&&x.deck_ids[0]===data.id))x.active=data.value&&x===found;}
          else if(data.value){if(p.studies.length>=24)throw new Error('Remove an old study setup first.');p.studies.push({id:'deck-'+data.id,name:(()=>{const n=d.nodes.find(x=>x.id===data.id),parts=n.path.split('::');return (parts.length>1&&/^(exam|test|quiz|assessment|midterm|final)\b/i.test(n.name)?parts.at(-2)+' · '+n.name:n.name).slice(0,100);})(),date:'',deck_ids:[data.id],active:true});}
          if(data.value)p.focus_enabled=true;
          if(!p.studies.some(x=>x.id===p.selected_study&&x.active))p.selected_study='all';
        }else if(data.key==='study_active'){const study=p.studies.find(x=>x.id===data.id);if(!study)throw new Error('That exam setup no longer exists.');study.active=data.value;if(data.value){p.focus_enabled=true;for(const other of p.studies)if(other.id!==study.id&&examKey(other)===examKey(study))other.active=false;}if(!data.value&&p.selected_study===data.id)p.selected_study='all';
        }else if(data.key==='remove_study'){p.studies=p.studies.filter(s=>s.id!==data.value);if(p.selected_study===data.value)p.selected_study='all';}
        else if(data.key==='color')p.colors[data.id]=data.value;
        else if(data.key==='last_location'){p.last_location=data.value;if(data.value!=='0')p.recent_locations=[data.value,...p.recent_locations.filter(id=>id!==data.value)].slice(0,32);}
        else if(['focus_enabled','selected_study'].includes(data.key))p[data.key]=data.value;
        else{p[data.key]=p[data.key].filter(id=>id!==data.id);if(data.value)p[data.key].push(data.id);}
        demoSave();return JSON.parse(JSON.stringify(p));
      }
      if(['create','rename','move'].includes(action)){
        const n=d.nodes.find(n=>n.id===data.id),p=d.nodes.find(n=>n.id===data.parent);
        if(action!=='create'&&!n)throw new Error('This deck is no longer in the library.');
        if(action!=='create'&&n.path!==data.expected)throw new Error('This deck changed while the dialog was open. Refresh first.');
        if(p?.filtered)throw new Error('A filtered deck cannot be used as a folder.');
        let newPath,oldPath=n?.path,created='';
        if(action==='move'){
          if(n.filtered)throw new Error('Manage filtered decks in Anki’s original view.');
          if(p&&(p.id===n.id||p.path.toLowerCase().startsWith(n.path.toLowerCase()+'::')))throw new Error('A folder cannot go inside itself.');
          newPath=(p?p.path+'::':'')+n.name;
        }else if(action==='rename')newPath=(n.path.includes('::')?n.path.slice(0,n.path.lastIndexOf('::')+2):'')+data.name;
        else newPath=(p?p.path+'::':'')+data.name;
        if(d.nodes.some(x=>x.id!==n?.id&&x.path.toLowerCase()===newPath.toLowerCase()))throw new Error('That name already exists in this location. Atelier never merges decks automatically.');
        if(action==='create'){
          created=String(Date.now());d.nodes.push({id:created,parent:data.parent,name:data.name,path:newPath,depth:newPath.split('::').length-1,children:[],new:0,learn:0,review:0,filtered:false});
          if(data.kind==='folder')d.profile.folders.push(created);
          d.profile.recent_added=[{id:created,observed:new Date().toISOString()},...d.profile.recent_added].slice(0,32);
        }else{
          n.path=newPath;n.name=newPath.split('::').pop();if(action==='move')n.parent=data.parent;
          for(const x of d.nodes)if(x.id!==n.id&&x.path.startsWith(oldPath+'::'))x.path=newPath+x.path.slice(oldPath.length);
        }
        for(const x of d.nodes){x.children=d.nodes.filter(v=>v.parent===x.id).map(v=>v.id);x.depth=x.path.split('::').length-1;}
        for(const x of [...d.nodes].sort((a,b)=>b.depth-a.depth))if(x.children.length){for(const key of ['new','learn','review'])x[key]=d.nodes.filter(v=>v.parent===x.id).reduce((s,v)=>s+v[key],0);}
        demoSave();return {ok:true,id:created};
      }
      if(action==='study'||action==='study_now'||action==='study_folder'){d.profile.last_studied=data.id;demoSave();state.profile.last_studied=data.id;}
      const messages={study_folder:'In Anki, this confirms the selected parent folder and saves the requested display order using its native options. This browser preview does not change options or run a scheduler.',study_now:'The installed add-on starts native Anki review for this lecture only. Anki’s scheduling and normal answer hooks still apply.',study:'The installed add-on opens only this selected deck in Anki’s native study overview. The reviewer controls follow your palette. Anki retains its card rendering, media, scheduling and gamification hooks.',browse:'The installed add-on opens Anki’s card browser. This preview contains no actual flashcards.',options:'The installed add-on opens Anki’s own deck options.',import:'The installed add-on opens Anki’s normal Import dialog. New decks observed afterward appear under Recently added.',add:'The installed add-on opens Anki’s native Add Cards window.',stats:'The installed add-on opens your real Anki statistics. The preview does not fabricate study history.',website:'Made by Daedalus Works · daedalusworks.net. In Anki, this opens the website in your browser.'};
      openDialog('preview-action',{message:messages[action]});return true;
    }
    nativeWidgets=window.AtelierNativeWidgets?.create({
      state,shadow,host,esc,icon,btn,ib,scope,now,preview:!!boot.preview,onigiri:()=>!!boot.integrations?.onigiri,
      openDialog,closeDialog,renderDialog,updatePref,render,announce,busy:busyDialog,reload:load,
      original:openProvider,
      progress:scopeId=>boot.preview?Promise.resolve(demoProgress(scopeId,7)):request('study_progress',{scope:scopeId,days:7})
    });
    home=window.AtelierSharedHome?.create({
      version:boot.version,state:()=>state,onigiri:()=>!!boot.integrations?.onigiri,
      tokens:()=>Object.fromEntries(['text','muted','accent','panel','line','raised','hover','scheme'].map(k=>[k,getComputedStyle(host).getPropertyValue('--'+k).trim()])),
      action:(action,id,command)=>handle({dataset:{action,id,command}}).catch(e=>announce(e.message,true)),
      context:(n,x,y,anchor,target)=>openMenu(n,x,y,anchor,target),closeMenu:()=>closeMenu(false)
    });
    render();load();
  });
})();
