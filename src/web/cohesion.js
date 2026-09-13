/* Stable, additive home contract for Exam Sprout 0.9.5 and recognized widgets.
   No widget cloning, scheduler messages, foreign state writes or polling loops. */
(() => {
  'use strict';
  if(window.AtelierCohesion?.version==='1.0.0')return;
  const root=document.documentElement;
  const keys=['bg','side','panel','raised','hover','text','muted','quiet','line','line-soft','accent','accent-strong','accent-soft','on-accent','blue','green','pink','amber','scheme','hero','hero-end'];
  let current=null,scheduled=false,disposed=false,knownCountdown=null,retiredCountdowns=0;
  const grids=new Map(),sproutWrappers=new Set();
  const put=(el,k,v)=>{if(el.getAttribute(k)!==v)el.setAttribute(k,v);};
  const css=(el,k,v)=>{if(el.style.getPropertyValue(k)!==String(v))el.style.setProperty(k,String(v));};
  function palette(host){const s=getComputedStyle(host);return Object.fromEntries(keys.map(k=>[k,s.getPropertyValue('--'+k).trim()]));}
  // Own ONLY layout properties on known wrappers. Inline provider !important
  // dimensions outrank stylesheets, so the entire width chain needs a reversible fit.
  const fitted=new Map();
  const sizeObserver=new MutationObserver(records=>{if(records.some(r=>fitted.has(r.target)&&[...fitted.get(r.target)].some(([k,v])=>r.target.style.getPropertyValue(k)!==v.applied||r.target.style.getPropertyPriority(k)!==v.appliedPriority)))queue();});
  function fit(el,key,value){
    if(!el)return;if(!fitted.has(el)){fitted.set(el,new Map());sizeObserver.observe(el,{attributes:true,attributeFilter:['style']});}const m=fitted.get(el);
    const now=el.style.getPropertyValue(key),priority=el.style.getPropertyPriority(key);let old=m.get(key);
    if(old&&now===old.applied&&priority===old.appliedPriority&&old.requested===value)return;
    if(!old||now!==old.applied||priority!==old.appliedPriority){old={value:now,priority};m.set(key,old);}
    el.style.setProperty(key,value,'important');old.applied=el.style.getPropertyValue(key);old.appliedPriority='important';old.requested=value;
  }
  function releaseFit(){
    sizeObserver.disconnect();
    for(const [el,m] of fitted)for(const [k,v] of m)if(el.style.getPropertyValue(k)===v.applied&&el.style.getPropertyPriority(k)===v.appliedPriority){if(v.value)el.style.setProperty(k,v.value,v.priority);else el.style.removeProperty(k);}
    fitted.clear();
  }
  function fitWrappers(g){
    const main=g.closest('.main-content'),wrap=g.closest('.injected-stats-block');
    for(const el of [main,wrap,g]){fit(el,'box-sizing','border-box');fit(el,'min-width','0');fit(el,'width','100%');fit(el,'max-width',el===main?'1280px':'100%');}
    fit(main,'margin','0 auto');fit(main,'padding',innerWidth<600?'16px':'24px 28px 40px');
    fit(wrap,'align-items','stretch');fit(wrap,'margin','0');fit(g,'margin','0');
  }
  function gridSizing(){
    for(const [g] of grids)if(!g.isConnected)grids.delete(g);
    for(const g of document.querySelectorAll('.modern-main-menu .unified-grid')){
      if(!grids.has(g)){
        const columns=getComputedStyle(g).gridTemplateColumns.split(/\s+/).filter(x=>x&&x!=='none').length||4;
        grids.set(g,{columns:Math.max(1,Math.min(columns,12)),spans:new WeakMap()});
      }
      const saved=grids.get(g);
      if(current.shared&&current.widgetMode!=='original')fitWrappers(g);
      if(!current.shared||current.layoutEnabled||current.widgetMode==='original'){g.removeAttribute('data-atelier-grid-columns');g.removeAttribute('data-atelier-grid-compact');g.removeAttribute('data-atelier-balanced');continue;}
      const width=g.parentElement?.clientWidth||g.clientWidth;
      const cols=width>=900?4:width>=540?2:1;
      const compact=true;
      put(g,'data-atelier-balanced',String(cols));
      put(g,'data-atelier-grid-columns',String(cols));css(g,'--ats-grid-columns',cols);
      put(g,'data-atelier-grid-compact',String(compact));
      for(const el of g.children){
        if(!el.matches('.onigiri-widget-container,.external-widget-container'))continue;
        if(!saved.spans.has(el)){
          // Read the inline native placement before our responsive override.
          const end=el.style.gridColumnEnd||getComputedStyle(el).gridColumnEnd;
          const start=el.style.gridColumnStart||getComputedStyle(el).gridColumnStart;
          let span=Number(end.match(/span\s+(\d+)/)?.[1]||start.match(/span\s+(\d+)/)?.[1]||1);
          saved.spans.set(el,Math.max(1,Math.min(span,12)));
        }
        css(el,'--ats-widget-span',Math.min(saved.spans.get(el),cols));
        if(el.querySelector('.onigiri-widget-title'))put(el,'data-atelier-widget-title','true');
        if(el.querySelector('.onigiri-restaurant-level-widget'))put(el,'data-atelier-building','true');
        if(el.querySelector('.stat-card'))put(el,'data-atelier-metric','true');
      }
    }
  }
  function sproutSizing(){
    // A partial native widget redraw can supply a fresh countdown while the old
    // Sprout-owned node is slotted in Atelier. Retire only that exact previously
    // observed read-only countdown, then let Sprout rebind its own new markup.
    // This never touches a planner, custom widget, input, or stored exam record.
    const candidates=[...document.querySelectorAll('section#es-countdowns[data-theme]')].filter(n=>!n.closest('#es-app'));
    if(knownCountdown?.isConnected && candidates.length===2 && candidates.includes(knownCountdown)){
      const fresh=candidates.find(n=>n!==knownCountdown);
      if(fresh?.querySelector('.es-chip[data-exam-id]') && window.ExamSproutCountdown?.mount){
        knownCountdown.remove();knownCountdown=fresh;retiredCountdowns++;
        window.ExamSproutCountdown.mount();
      }
    }
    const node=document.getElementById('es-countdowns');
    if(node?.matches('section[data-theme]')&&!node.closest('#es-app'))knownCountdown=node;
    const wrap=node?.closest('.external-widget-container');
    if(wrap)sproutWrappers.add(wrap);
    for(const w of sproutWrappers){
      if(!w.isConnected){sproutWrappers.delete(w);continue;}
      // Sprout's OWN script rehomes its own node using a light-DOM slot.
      // Only hide an empty source wrapper, never another extension's content.
      const contains=!!w.querySelector('#es-countdowns');
      const other=[...w.children].some(e=>!e.matches('#es-countdowns,style,script'));
      if(contains)put(w,'data-atelier-sprout-wrap','present');
      else if(!other)put(w,'data-atelier-sprout-wrap','empty');
      else w.removeAttribute('data-atelier-sprout-wrap');
    }
  }
  function updateNodes(){
    if(!current||disposed)return;
    if(current.owner!=='atelier'){
      releaseFit();
      for(const [g] of grids){g.removeAttribute('data-atelier-grid-columns');g.removeAttribute('data-atelier-grid-compact');g.removeAttribute('data-atelier-balanced');}
      for(const w of sproutWrappers)w.removeAttribute('data-atelier-sprout-wrap');
      return;
    }
    if(current.widgetMode==='original')releaseFit();
    gridSizing();sproutSizing();
  }
  function queue(){
    if(scheduled||disposed)return;scheduled=true;
    requestAnimationFrame(()=>{scheduled=false;updateNodes();});
  }
  function sync({host,config,layoutEnabled=false}){
    if(disposed||!host)return;
    window.AtelierOwnership?.apply(host,config);
    const t=palette(host),workspace=config.mode!=='native'||config.visual_owner==='ask';
    current={host,owner:config.visual_owner,shared:config.visual_owner==='atelier',matchSprout:config.visual_owner==='atelier'&&config.match_sprout!==false,layoutEnabled,widgetMode:config.widget_mode||'balanced',tokens:t,theme:config.visual_owner==='onigiri'?'Onigiri companion':config.theme,workspace};
    for(const k of keys)if(t[k])css(root,'--ats-'+k,t[k]);
    put(root,'data-atelier-shared',String(current.shared));
    put(root,'data-atelier-match-sprout',String(current.matchSprout));
    put(root,'data-atelier-palette',config.theme);
    // Exam Sprout 0.9.5's adapter requires this marker. It must be set BEFORE
    // the theme-change event, and cleared BEFORE returning to the shared home.
    document.body.classList.toggle('atelier-home',workspace&&config.visual_owner==='atelier');
    put(host,'data-atelier-host-version','1');
    updateNodes();
    // Native scripts may mount after Atelier. A bounded next-frame call supports
    // both load orders and idempotently keeps ONE native countdown/timer.
    queue();
  }
  const relevant=n=>n.nodeType===1&&(n.matches?.('.modern-main-menu,.unified-grid,.external-widget-container,#es-countdowns')||n.querySelector?.('.modern-main-menu,.unified-grid,.external-widget-container,#es-countdowns'));
  const observer=new MutationObserver(records=>{
    if(records.some(r=>[...r.addedNodes,...r.removedNodes].some(relevant)))queue();
  });
  observer.observe(root,{childList:true,subtree:true});
  window.addEventListener('resize',queue);
  function dispose(){disposed=true;observer.disconnect();releaseFit();window.removeEventListener('resize',queue);}
  window.addEventListener('pagehide',dispose,{once:true});
  window.AtelierHost=Object.freeze({apiVersion:1,getTheme:()=>current?{name:current.theme,active:current.workspace&&current.owner==='atelier',tokens:{...current.tokens}}:null});
  window.AtelierCohesion=Object.freeze({version:'1.0.0',sync,refresh:queue,dispose,diagnostics:()=>({version:'1.0.0',sharedTheme:current?.shared??false,matchSprout:current?.matchSprout??false,workspace:current?.workspace??false,sproutPresent:!!document.getElementById('es-countdowns'),sproutSlotted:document.getElementById('es-countdowns')?.parentElement?.id==='atelier-root',gridCount:grids.size,retiredCountdowns,widgetNodesCloned:0})});
})();
