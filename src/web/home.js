/* Atelier Shared Home 1.0.0.
 * Interoperability layer, not a replacement for another add-on's renderer.
 * Widgets normally remain in their original DOM ancestry. When Atelier owns
 * the home, an installed Onigiri page may be moved as one intact live subtree
 * into Atelier's rewards slot. The move is reversible and never copies HTML,
 * replaces handlers, patches Onigiri, intercepts pycmd, or writes progress.
 */
(() => {
  'use strict';
  const own = el => el?.closest?.('#atelier-root,[data-atelier-native-rail],[data-atelier-row-control]');
  const escape = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const hash = text => {let h=2166136261;for(const c of text){h^=c.charCodeAt(0);h=Math.imul(h,16777619);}return (h>>>0).toString(36);};
  const blank = () => ({enabled:false,columns:3,items:[]});
  const railCSS = `
    :host{all:initial;display:block;box-sizing:border-box;width:100%;min-width:0;font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--at-text,#eeecf6);text-align:left;color-scheme:var(--at-scheme,dark)}
    :host([hidden]){display:none!important}*{box-sizing:border-box}button{font:inherit;cursor:pointer}button:focus-visible{outline:2px solid var(--at-accent,#b8a2f0);outline-offset:3px}button:disabled{opacity:.5;cursor:wait}
    .rail{padding:18px 20px;border:1px solid var(--at-line,#363044);border-radius:18px;background:var(--at-panel,#1c1928);box-shadow:0 6px 24px #00000012;margin:0 0 24px;min-width:0}
    .heading{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}.label{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.wordmark{font-size:19px;font-weight:750;letter-spacing:-.7px}.build{font:11px/1.2 ui-monospace,monospace;border:1px solid var(--at-line);padding:5px 7px;border-radius:6px;color:var(--at-muted,#b0a9bf)}
    .actions{display:flex;gap:8px;flex-wrap:wrap}.action{border:1px solid var(--at-line);border-radius:9px;background:var(--at-raised,#242030);color:inherit;padding:8px 12px;min-height:36px}.action:hover{border-color:var(--at-accent)}
    .exams{display:flex;gap:10px;flex-wrap:wrap;margin-top:15px}.exam{display:flex;align-items:stretch;border:1px solid var(--at-line);border-radius:10px;min-width:0;max-width:100%;background:var(--at-raised,#242030)}
    .exam-open{border:0;background:none;color:inherit;padding:9px 12px;text-align:left;min-width:0;max-width:360px}.exam-open strong{display:block;overflow-wrap:anywhere;font-weight:600;font-size:13px}.exam-open small{display:block;color:var(--at-muted);font-size:11px;margin-top:3px}
    .exam-remove{flex:0 0 auto;border:0;border-left:1px solid var(--at-line);background:none;color:var(--at-muted);min-width:44px;padding:8px;border-radius:0 10px 10px 0;font-size:12px}.exam-remove:hover{background:var(--at-hover,#2b263b);color:var(--at-text)}
    .hint{font-size:12px;color:var(--at-muted);margin:12px 0 0;max-width:100%}.empty{color:var(--at-muted);font-size:13px;margin:13px 0 0}.dot{color:var(--at-accent);margin-right:4px}
    .companion-dock{padding:7px;border:1px solid var(--at-line);border-radius:14px;background:var(--at-panel);color:var(--at-text);box-shadow:0 8px 28px #0003}
    .dock-main{display:flex;align-items:center;gap:6px;min-width:0}.dock-main .action{font-size:12px;padding:7px 9px;min-height:34px}
    .dock-open{background:none;color:inherit;border:0;font-size:18px;font-weight:750;letter-spacing:-.7px;cursor:pointer;padding:5px 10px}
    .dock-details{margin-left:auto}.dock-details summary{list-style:none;cursor:pointer;padding:10px;border-radius:8px}.dock-details summary:focus-visible{outline:2px solid var(--at-accent)}
    .dock-details summary:hover{background:var(--at-raised)}.dock-popover{position:absolute;bottom:calc(100% + 9px);right:0;width:min(420px,calc(100vw - 32px));box-sizing:border-box;background:var(--at-panel);border:1px solid var(--at-line);border-radius:14px;padding:14px;max-height:60vh;overflow:auto;box-shadow:0 12px 32px #0004}
    .dock-title{font-size:11px;color:var(--at-muted);margin-bottom:10px}.dock-popover .exam{margin-bottom:8px}.dock-popover .exam-open{flex:1}.dock-popover>.action{margin-top:10px}
    @media(max-width:580px){.rail{padding:14px}.heading{gap:10px}.exams{display:grid;grid-template-columns:minmax(0,1fr)}.exam-open{flex:1}.action{padding:8px;font-size:12px}.hint{line-height:1.7}}
    .studio-rail{padding:12px 0 20px;border:0;border-radius:0;box-shadow:none;background:transparent;margin:0 0 10px;border-bottom:1px solid var(--at-line)}
    .back-desk{border:0;background:transparent;padding-left:0}.widget-taskbar{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-top:15px}.studio-rail .primary{border-color:var(--at-accent)}
    .small-exams{gap:8px;margin-top:16px}.small-exams .exam-open{padding:7px 10px}.small-exams .exam-open strong{font-size:12px;font-weight:500}.small-exams .exam-remove{min-width:32px;padding:6px}
    .more-tools{position:relative}.more-tools summary{cursor:pointer;list-style:none;padding:9px 12px;border:1px solid var(--at-line);border-radius:9px;min-height:36px;font-size:13px}.more-tools summary:focus-visible{outline:2px solid var(--at-accent)}
    .more-menu{position:absolute;right:0;top:calc(100% + 7px);width:220px;background:var(--at-panel);border:1px solid var(--at-line);border-radius:12px;box-shadow:0 18px 40px #0003;padding:8px;z-index:5;display:flex;flex-direction:column;gap:6px;max-height:50vh;overflow:auto}
    @media(max-width:580px){.studio-rail .heading{align-items:flex-start}.studio-rail .label{gap:8px}.studio-rail .exams{display:flex}.studio-rail .wordmark{font-size:18px}.studio-rail .build{font-size:10px}.widget-taskbar>.actions{flex-wrap:wrap}.more-menu{left:0;right:auto;width:min(220px,70vw)}}
    .studio-rail{max-width:none;margin:0 0 20px;padding:0 0 18px;border:0;border-bottom:1px solid var(--at-line);border-radius:0;background:none;box-shadow:none}
    .studio-rail .heading{gap:14px;align-items:center}.studio-rail .label{flex:1;flex-wrap:wrap;gap:12px}.studio-rail .wordmark{font-size:22px}
    .studio-rail .widget-taskbar{display:flex;flex-wrap:wrap;justify-content:flex-start;gap:10px;margin-top:16px}.studio-rail .widget-taskbar>.actions{gap:8px}
    .studio-rail .action{min-height:38px;padding:8px 12px;font-size:13px;box-shadow:none;transform:none!important}
    .studio-rail .primary{border-color:var(--at-accent);font-weight:650}
    .studio-rail .small-exams{gap:8px;margin-top:12px}.studio-rail .small-exams .exam{border-radius:9px}.studio-rail .exam-open{padding:7px 10px}
    .studio-rail .back-desk{padding-left:0;border:0;background:none;color:var(--at-muted)}
    .studio-rail .more-tools{position:relative}.studio-rail .more-menu{right:0;left:auto;max-width:calc(100vw - 44px)}
    @media(max-width:640px){.studio-rail .heading>.actions{width:100%}.studio-rail .wordmark{font-size:20px}.studio-rail .build{display:none}.studio-rail .actions{flex-wrap:wrap}.studio-rail .widget-taskbar{gap:8px}.studio-rail .label{gap:6px;align-items:flex-start;flex-direction:column}}
  `;
  function create(api) {
    let rail=null, railShadow=null, scheduled=false, restoring=false, lastFingerprint='', records=[];
    const inline={host:null,enabled:false,node:null,parent:null,next:null,slot:null,attrs:new Map(),observer:null};
    const pins=new Map(), styling=new Map(), resized=new Set();
    const native = () => {const s=api.state();return s.loaded && s.config.mode==='native' && s.config.visual_owner!=='ask';};
    const state = () => api.state();
    const passive = () => ['onigiri','external'].includes(state().config.visual_owner);
    const enhanceRows = () => native() && (!passive() || state().config.companion_shortcuts===true);
    const layout = () => state().profile.home_layout || blank();
    const exact = id => state().profile.studies.filter(s=>s.active&&s.deck_ids.length===1&&s.deck_ids[0]===id);
    function setStyle(el,name,value) {
      if(!styling.has(el))styling.set(el,new Map());
      const entries=styling.get(el), current=el.style.getPropertyValue(name), priority=el.style.getPropertyPriority(name);
      let old=entries.get(name);
      if(old && current===old.applied && priority===old.appliedPriority){
        if(old.requested===value)return;
      }else{
        // A real external change becomes the new restoration baseline. Browser
        // serialization (e.g. 0 -> 0px) is not an external change.
        old={value:current,priority};entries.set(name,old);
      }
      el.style.setProperty(name,value,'important');
      old.requested=value;old.applied=el.style.getPropertyValue(name);old.appliedPriority=el.style.getPropertyPriority(name);
    }
    function restoreStyles() {
      restoring=true;
      for(const [el,entries] of styling){for(const [key,v] of entries){if(el.style.getPropertyValue(key)===v.applied&&el.style.getPropertyPriority(key)===v.appliedPriority){if(v.value)el.style.setProperty(key,v.value,v.priority);else el.style.removeProperty(key);}}}
      styling.clear();restoring=false;
    }
    function providerRoot() {
      return [...document.querySelectorAll('.modern-main-menu')].find(el=>!own(el))||null;
    }
    function inlineAttr(el,name,value) {
      if(!inline.attrs.has(el))inline.attrs.set(el,new Map());
      const saved=inline.attrs.get(el);
      if(!saved.has(name))saved.set(name,{present:el.hasAttribute(name),value:el.getAttribute(name)});
      if(value===null)el.removeAttribute(name);else el.setAttribute(name,value);
    }
    function restoreInlineLayout() {
      inline.observer?.disconnect();inline.observer=null;
      for(const [el,attrs] of inline.attrs)for(const [name,old] of attrs){
        if(old.present)el.setAttribute(name,old.value);else el.removeAttribute(name);
      }
      inline.attrs.clear();
    }
    function packInline() {
      const node=inline.node;if(!node?.isConnected||node.parentNode!==inline.host)return false;
      const width=inline.host?.clientWidth||node.clientWidth||innerWidth;
      const cols=width>=900?4:width>=540?2:1;
      for(const grid of node.querySelectorAll('.unified-grid,[data-atelier-widget-grid]')){
        inlineAttr(grid,'data-atelier-inline-grid',String(cols));
        for(const el of grid.children){
          if(!(el instanceof HTMLElement)||el.matches('script,style,template'))continue;
          let role='widget';
          if(el.querySelector('.onigiri-restaurant-level-widget'))role='building';
          else if(el.matches('.external-widget-container')||el.hasAttribute('data-atelier-sprout-wrap'))role='external';
          else if(el.querySelector('.onigiri-widget-title'))role='title';
          else if(el.querySelector('.stat-card'))role='metric';
          inlineAttr(el,'data-atelier-inline-item',role);
        }
      }
      return true;
    }
    function restoreInline() {
      const node=inline.node;if(!node)return false;
      restoreInlineLayout();
      node.removeAttribute('data-atelier-inline-rewards');
      if(inline.slot===null)node.removeAttribute('slot');else node.setAttribute('slot',inline.slot);
      if(inline.parent?.isConnected){
        if(inline.next?.parentNode===inline.parent)inline.parent.insertBefore(node,inline.next);else inline.parent.append(node);
      }
      inline.node=inline.parent=inline.next=null;inline.slot=null;
      return true;
    }
    function syncInline() {
      if(!inline.enabled||!inline.host?.isConnected){restoreInline();return false;}
      if(inline.node?.isConnected&&inline.node.parentNode===inline.host)return packInline();
      restoreInline();
      const node=providerRoot();if(!node)return false;
      inline.node=node;inline.parent=node.parentNode;inline.next=node.nextSibling;inline.slot=node.getAttribute('slot');
      node.setAttribute('slot','atelier-onigiri-rewards');node.setAttribute('data-atelier-inline-rewards','true');
      inline.host.append(node);
      packInline();
      inline.observer=new MutationObserver(()=>queue());
      inline.observer.observe(node,{childList:true,subtree:true});
      return true;
    }
    function embed(host,enabled) {
      inline.host=host;inline.enabled=!!enabled;
      const mounted=syncInline();
      host.dataset.onigiriEmbedded=String(mounted);
      return mounted;
    }
    function rowFrom(target) {
      if(!(target instanceof Element) || own(target))return null;
      const row=target.closest('#decktree tr,table.deck-table tr,#deck-list-container [data-did]');
      if(!row)return null;
      let id=row.getAttribute('data-did')||row.getAttribute('data-deck-id')||row.id;
      if(!/^\d{1,19}$/.test(id||'')){
        const link=row.querySelector('a.deck[onclick]');
        id=link?.getAttribute('onclick')?.match(/(?:open|study):([0-9]{1,19})\b/)?.[1];
      }
      return id&&state().map.has(id)?{row,id,node:state().map.get(id)}:null;
    }
    function makeRail() {
      const parent=passive()?document.documentElement:(document.querySelector('.modern-main-menu .main-content') || document.body);
      if(!rail){
        rail=document.createElement('section');rail.dataset.atelierNativeRail='';
        rail.setAttribute('aria-label','Atelier active exams and shared home controls');
        rail.style.cssText='display:block!important;width:100%!important;max-width:none!important;min-width:0!important;grid-column:1 / -1!important;box-sizing:border-box!important;flex-shrink:0!important;';
        railShadow=rail.attachShadow({mode:'open'});railShadow.innerHTML='<style>'+railCSS+'</style><div class="mount"></div>';
        railShadow.addEventListener('keydown',e=>{if(e.key==='Escape'){const d=railShadow.querySelector('.more-tools[open]');if(d){e.preventDefault();e.stopPropagation();d.open=false;d.querySelector('summary')?.focus();}}});
        railShadow.addEventListener('click',e=>{const b=e.target.closest('[data-action]');if(!b||b.disabled)return;e.preventDefault();e.stopPropagation();b.disabled=true;Promise.resolve(api.action(b.dataset.action,b.dataset.id,b.dataset.command)).finally(()=>{if(b.isConnected)b.disabled=false;});});
      }
      if(!rail.isConnected || rail.parentNode!==parent)parent.prepend(rail);
      rail.hidden=!native();rail.style.setProperty('display',native()?'block':'none','important');
      rail.dataset.atelierCompanion=String(passive());
      for(const k of ['position','inset','width','max-width','z-index'])rail.style.removeProperty(k);
      if(passive()){
        rail.style.setProperty('position','fixed','important');rail.style.setProperty('inset','auto 16px 16px auto','important');
        rail.style.setProperty('width','min(460px,calc(100vw - 32px))','important');rail.style.setProperty('max-width','100%','important');
        rail.style.setProperty('z-index','2147482001','important');
      }else{rail.style.setProperty('width','100%','important');}

      // Shared home should visually match the native/Onigiri surface when present.
      const base=api.tokens();
      const doc=getComputedStyle(document.documentElement);
      const pick=name=>doc.getPropertyValue('--ats-'+name).trim()||base[name]||'';
      const tokens={text:pick('text'),muted:pick('muted'),accent:pick('accent'),panel:pick('panel'),line:pick('line'),raised:pick('raised'),hover:pick('hover'),scheme:pick('scheme')};
      for(const key of ['text','muted','accent','panel','line','raised','hover','scheme'])rail.style.setProperty('--at-'+key,tokens[key]||'');
      const active=state().profile.studies.filter(s=>s.active);
      const hasSprout=!!(state().suite?.available||window.ExamSproutCountdown||document.getElementById('es-countdowns'));
      const fingerprint=JSON.stringify([active,api.version,native(),hasSprout,passive()]);
      if(fingerprint!==lastFingerprint){
        lastFingerprint=fingerprint;
        if(passive()){
          railShadow.querySelector('.mount').innerHTML=`<div class="companion-dock"><div class="dock-main"><button class="dock-open" data-action="shared-organizer" title="Open Atelier organizer">atelier</button><button class="action" data-action="quick-session">Quick study</button>${hasSprout?'<button class="action" data-action="sprout-practice">Practice ↗</button>':''}<details class="dock-details"><summary title="Exam shortcuts and appearance">•••</summary><div class="dock-popover"><div class="dock-title">Atelier ${escape(api.version)} · ${active.length} active exams</div>${active.map(s=>`<div class="exam"><button class="exam-open" data-action="shared-study" data-id="${escape(s.id)}"><strong>${escape(s.name)}</strong><small>Choose lectures →</small></button><button class="exam-remove" data-action="finish-study" data-id="${escape(s.id)}" aria-label="Remove ${escape(s.name)} from active exams">× Remove</button></div>`).join('')||'<p class="hint">Pin exams inside the organizer.</p>'}<button class="action" data-action="widget-page">Atelier widgets</button><button class="action" data-action="appearance">Appearance & compatibility</button></div></details></div></div>`;
          return;
        }
        railShadow.querySelector('.mount').innerHTML=`<div class="rail studio-rail"><div class="heading"><div class="label"><button class="action back-desk" data-action="widget-page">← Atelier widgets</button><span class="wordmark">${api.onigiri?.()?'Onigiri rewards & widgets':'Other add-ons — original page'}</span><span class="build">${escape(api.version)}</span></div><div class="actions"><button class="action" data-action="home-edit">Arrange provider widgets</button><button class="action" data-action="appearance">Appearance</button></div></div><div class="widget-taskbar"><div class="actions"><button class="action primary" data-action="quick-session">Quick study</button><button class="action" data-action="sprout-practice">Practice exam ↗</button></div><div class="actions"><details class="more-tools"><summary>More tools</summary><div class="more-menu"><button class="action" data-action="shared-desk">Study desk</button><button class="action" data-action="study-progress">Study progress</button><button class="action" data-action="pip-groups">Pip Study</button><button class="action" data-action="native-tool" data-command="add">Add cards</button><button class="action" data-action="native-tool" data-command="browse">Browse</button><button class="action" data-action="native-tool" data-command="sync">Sync</button><button class="action" data-action="sprout-open">Exam Studio</button><button class="action" data-action="shared-organizer">Library & tools</button><button class="action" data-action="export-picker">Export cards</button><button class="action" data-action="home-balanced">Balanced layout</button><button class="action" data-action="home-original">Original positions</button></div></details></div></div>${active.length?`<div class="exams small-exams" aria-label="Study shortcuts">${active.map(s=>`<div class="exam"><button class="exam-open" data-action="shared-study" data-id="${escape(s.id)}"><strong>${escape(s.name)}</strong></button><button class="exam-remove" data-action="finish-study" data-id="${escape(s.id)}" aria-label="Remove ${escape(s.name)} from active exams" title="Remove shortcut; keep all cards">×</button></div>`).join('')}</div>`:''}</div>`;
      }
    }
    function updateRows() {
      if(!enhanceRows()){for(const pin of pins.values())pin.remove();pins.clear();return;}
      for(const [row,pin] of pins)if(!row.isConnected||!pin.isConnected)pins.delete(row);
      const rows=document.querySelectorAll('#decktree tr,table.deck-table tr,#deck-list-container [data-did]');
      let count=0;
      for(const row of rows){
        if(++count>5000)break;
        const ref=rowFrom(row);if(!ref)continue;
        let pin=pins.get(row);
        if(!pin){
          const cell=row.querySelector('.decktd')||row.querySelector('td');if(!cell)continue;
          pin=document.createElement('span');pin.dataset.atelierRowControl=ref.id;
          pin.style.cssText='display:inline-flex!important;width:28px!important;height:28px!important;min-width:28px!important;flex:0 0 28px!important;vertical-align:middle!important;margin:0 3px!important;position:relative!important;';
          const sr=pin.attachShadow({mode:'open'});
          sr.innerHTML='<style>:host{all:initial;display:inline-flex}button{all:initial;box-sizing:border-box;display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border:1px solid var(--at-pin-line,#7f7e8380);border-radius:7px;background:transparent;color:var(--at-pin-fg,#cac7d1);font:600 17px/1 system-ui;cursor:pointer}button:hover{background:var(--at-pin-hover,#7f7e8325)}button:focus-visible{outline:2px solid currentColor;outline-offset:2px}button[aria-pressed="true"]{background:var(--at-pin-hover,#7f7e8325)}button:disabled{opacity:.5;cursor:wait}</style><button type="button"></button>';
          sr.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();const b=sr.querySelector('button');if(b.disabled)return;b.disabled=true;Promise.resolve(api.action('quick-exam',rowFrom(row)?.id)).finally(()=>{if(b.isConnected)b.disabled=false;});});
          // Avoid native delegated row-navigation/drag handlers without replacing them.
          for(const name of ['pointerdown','mousedown','dblclick','contextmenu'])sr.addEventListener(name,e=>e.stopPropagation());
          cell.append(pin);pins.set(row,pin);
        }
        const active=exact(ref.id).length>0, b=pin.shadowRoot.querySelector('button');
        b.textContent=active?'✓':'+';b.setAttribute('aria-pressed',String(active));
        const text=active?'Remove '+ref.node.name+' from active exams':'Set '+ref.node.name+' as upcoming exam';b.title=text;b.setAttribute('aria-label',text);
        const color=getComputedStyle(row.querySelector('a.deck')||row).color;
        pin.style.setProperty('--at-pin-fg',color);pin.hidden=!native();
        pin.style.setProperty('display',native()?'inline-flex':'none','important');
      }
    }
    function identify(el) {
      if(el.querySelector('#es-countdowns')||el.hasAttribute('data-atelier-sprout-wrap'))return {id:'widget.exam-sprout-countdowns',title:'Exam Sprout countdowns (automatic height)',source:'Exam Sprout'};
      const source=el.matches('.onigiri-widget-container')?'Onigiri':el.matches('.external-widget-container')?'External add-on':'Home add-on';
      const explicit=el.getAttribute('data-atelier-widget')||el.getAttribute('data-onigiri-external-hook')||el.id;
      const inner=el.querySelector('[id]')?.id;
      const titleNode=el.querySelector('[data-widget-title],h1,h2,h3,h4,.stat-label,.stat-title,.widget-title,.title');
      let title=el.getAttribute('data-widget-title')||titleNode?.textContent.trim().replace(/\s+/g,' ').slice(0,90)||'';
      const stable=explicit||inner||title;
      if(!stable)return null; // Never persist positions using a fragile list index.
      if(!title)title=stable.replace(/[_-]/g,' ').replace(/\b\w/g,c=>c.toUpperCase()).slice(0,90);
      return {id:'widget.'+hash(source+':'+stable),title,source};
    }
    function discover() {
      const candidates=[...document.querySelectorAll('.onigiri-widget-container,.external-widget-container,[data-atelier-widget],#review-heatmap,#reviewHeatmap,#cal-heatmap')].filter(el=>!own(el));
      const top=candidates.filter(el=>!candidates.some(other=>other!==el&&other.contains(el)));
      const found=[], keys=new Set(),duplicates=new Set();
      for(const el of top.slice(0,100)){
        const label=identify(el);if(!label)continue;
        if(keys.has(label.id)){duplicates.add(label.id);continue;}keys.add(label.id);
        const old=records.find(r=>r.el===el);
        found.push({...label,el,parent:el.parentElement,naturalHeight:old?.naturalHeight||Math.max(96,Math.min(900,Math.ceil(el.getBoundingClientRect().height)||200))});
      }
      records=found.filter(r=>!duplicates.has(r.id));
      return records;
    }
    function applyLayout() {
      const prefs=layout();
      if(passive()||!prefs.enabled){restoreStyles();return;}
      const configured=new Map(prefs.items.map((x,i)=>[x.id,{...x,order:i}]));
      const groups=new Map();
      for(const rec of records){if(!groups.has(rec.parent))groups.set(rec.parent,[]);groups.get(rec.parent).push(rec);}
      for(const [parent,items] of groups){
        // Only recognized widget grids, never the page or deck tree, are reflowed.
        const groupSafe=parent.matches('.unified-grid,[data-atelier-widget-grid]');
        const cols=Math.max(1,Math.min(prefs.columns,Math.floor((parent.clientWidth||800)/235)||1));
        if(groupSafe){setStyle(parent,'display','grid');setStyle(parent,'grid-template-columns',`repeat(${cols}, minmax(0, 1fr))`);setStyle(parent,'grid-template-rows','none');setStyle(parent,'grid-auto-rows','minmax(0, auto)');setStyle(parent,'gap','16px');setStyle(parent,'align-items','start');setStyle(parent,'max-width','100%');setStyle(parent,'min-width','0');}
        for(const rec of items){
          const p=configured.get(rec.id);if(!p)continue;
          if(!p.visible){setStyle(rec.el,'display','none');continue;}
          // Restore a previously hidden widget when its checkbox is switched on.
          const display=styling.get(rec.el)?.get('display');if(display){if(display.value)rec.el.style.setProperty('display',display.value,display.priority);else rec.el.style.removeProperty('display');styling.get(rec.el).delete('display');}
          if(groupSafe){
            const span=p.size==='full'?cols:p.size==='wide'?Math.min(2,cols):1;
            setStyle(rec.el,'grid-row-start','auto');setStyle(rec.el,'grid-row-end','auto');setStyle(rec.el,'grid-column-start',`span ${span}`);setStyle(rec.el,'grid-column-end','auto');setStyle(rec.el,'order',String(p.order));setStyle(rec.el,'min-width','0');setStyle(rec.el,'max-width','100%');
          }
          if(rec.el.hasAttribute('data-atelier-sprout-wrap')){
            if(groupSafe){setStyle(rec.el,'grid-column-start','1');setStyle(rec.el,'grid-column-end','-1');}
            setStyle(rec.el,'height','auto');setStyle(rec.el,'min-height','0');setStyle(rec.el,'overflow','visible');
          }else{
            const h=p.height==='short'?160:p.height==='tall'?420:rec.naturalHeight;
            setStyle(rec.el,'height',h+'px');setStyle(rec.el,'min-height',h+'px');setStyle(rec.el,'overflow','auto');
          }
          // Deliberately no descendant image/canvas/input/style overrides.
        }
      }
    }
    function sync() {
      if(!state().loaded)return;
      makeRail();updateRows();discover();applyLayout();
    }
    function queue() {
      if(scheduled||restoring)return;scheduled=true;
      setTimeout(()=>{scheduled=false;syncInline();sync();},80);
    }
    const observer=new MutationObserver(changes=>{
      if(changes.some(c=>!own(c.target)&&(c.type==='attributes'||[...c.addedNodes,...c.removedNodes].some(n=>n.nodeType===1&&!own(n)))))queue();
    });
    observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['data-did','data-deck-id']});
    function context(e) {
      if(!enhanceRows()||e.shiftKey||e.__atelierOriginal)return;
      const ref=rowFrom(e.target);if(!ref)return;
      e.preventDefault();e.stopImmediatePropagation();
      api.context(ref.node,e.clientX,e.clientY,ref.row.querySelector('a.deck'),e.target);
    }
    window.addEventListener('contextmenu',context,true);
    window.addEventListener('keydown',e=>{
      if(!enhanceRows()||!(e.key==='ContextMenu'||e.shiftKey&&e.key==='F10'))return;
      const ref=rowFrom(e.target);if(!ref)return;
      const r=ref.row.getBoundingClientRect();e.preventDefault();e.stopImmediatePropagation();api.context(ref.node,Math.max(8,r.left+20),r.top+20,ref.row.querySelector('a.deck'),e.target);
    },true);
    document.addEventListener('pointerdown',e=>{if(native()&&!own(e.target))api.closeMenu();},true);
    window.addEventListener('resize',queue);
    if(window.ResizeObserver){const ro=new ResizeObserver(queue);for(const el of document.querySelectorAll('.unified-grid,[data-atelier-widget-grid]')){ro.observe(el);resized.add(el);}}
    return Object.freeze({
      sync, embed, hasRail:()=>!!rail?.isConnected,
      list(){discover();const saved=layout().items||[], order=new Map(saved.map((x,i)=>[x.id,i]));return records.map(r=>({id:r.id,title:r.title,source:r.source,reflow:r.parent.matches('.unified-grid,[data-atelier-widget-grid]'),...(saved.find(x=>x.id===r.id)||{visible:true,size:'small',height:'auto'})})).sort((a,b)=>(order.get(a.id)??999)-(order.get(b.id)??999));},
      originalMenu(target,x,y){if(!target?.isConnected)return;const e=new MouseEvent('contextmenu',{bubbles:true,cancelable:true,view:window,clientX:x,clientY:y,button:2});Object.defineProperty(e,'__atelierOriginal',{value:true});target.dispatchEvent(e);},
      refresh(){sync();window.dispatchEvent(new Event('resize'));},
      diagnostics:()=>({rail:!!rail?.isConnected,rowControls:pins.size,widgets:records.map(r=>({id:r.id,title:r.title})),layoutEnabled:layout().enabled,onigiriEmbedded:!!inline.node?.isConnected,widgetNodesMoved:inline.node?1:0}),
      dispose(){observer.disconnect();window.removeEventListener('contextmenu',context,true);restoreInline();restoreStyles();rail?.remove();for(const pin of pins.values())pin.remove();}
    });
  }
  window.AtelierSharedHome=Object.freeze({create});
})();
