/* Palette ownership. Read the unmodified native surface; color only Atelier's
   shadow-root organizer and compact launcher. Never repair foreign colors. */
(() => {
  'use strict';
  const r=document.documentElement;
  let snapshot=null;
  const hex=color=>{
    if(/^#[\da-f]{6}$/i.test(color||''))return color.toLowerCase();
    const m=String(color||'').match(/^rgba?\(([^)]+)\)$/i);
    if(!m)return null;
    const n=m[1].match(/[\d.]+/g)?.map(Number);
    if(!n||n.length<3||(n.length>3&&n[3]<.99))return null;
    return '#'+n.slice(0,3).map(v=>Math.max(0,Math.min(255,Math.round(v))).toString(16).padStart(2,'0')).join('');
  };
  const rgb=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));
  const mix=(a,b,f)=>'#'+rgb(a).map((v,i)=>Math.round(v*(1-f)+rgb(b)[i]*f).toString(16).padStart(2,'0')).join('');
  const lum=h=>rgb(h).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
  const ratio=(a,b)=>(Math.max(lum(a),lum(b))+.05)/(Math.min(lum(a),lum(b))+.05);
  function read(){
    if(!['onigiri','external'].includes(r.dataset.atelierOwner)||!document.body)return null;
    const pick=(selectors,prop,fallback)=>{for(const selector of selectors){for(const el of document.querySelectorAll(selector)){if(el.closest('#atelier-root,[data-atelier-native-rail]'))continue;const h=hex(getComputedStyle(el)[prop]);if(h)return h;}}return fallback;};
    // A native light canvas may contain dark widgets. One text color cannot fit
    // both. Use a coherent panel-derived palette only for OUR companion UI.
    const panel=pick(['.modern-main-menu .stat-card','.modern-main-menu .sidebar-left','body'],'backgroundColor','#252824');
    const dark=lum(panel)<.35;
    const bg=mix(panel,dark?'#080b09':'#ffffff',.14);
    const raised=mix(panel,dark?'#ffffff':'#18241b',.045);
    const hover=mix(panel,dark?'#ffffff':'#18241b',.075);
    const surfaces=[bg,panel,raised,hover];
    const score=c=>Math.min(...surfaces.map(b=>ratio(c,b)));
    const candidates=['#fcfcf8','#121a14',pick(['.modern-main-menu .stat-card .stat-value','.modern-main-menu .stat-card'],'color','#fcfcf8')];
    const text=candidates.sort((a,b)=>score(b)-score(a))[0];
    let accent=pick(['.modern-main-menu .stat-card h3','.modern-main-menu .menu-item','.modern-main-menu a.deck'],'color',text);
    if(score(accent)<4.5)accent=text;
    const readableMuted=f=>{const c=mix(text,panel,f);return score(c)>=4.5?c:text;};
    snapshot={bg,panel,side:bg,raised,hover,text,muted:readableMuted(.13),quiet:readableMuted(.18),accent,'accent-strong':accent,
      line:mix(panel,text,.3),'line-soft':mix(panel,text,.2),'accent-soft':raised,'on-accent':ratio('#111811',accent)>ratio('#ffffff',accent)?'#111811':'#ffffff',
      blue:accent,green:accent,pink:accent,amber:accent,hero:panel,'hero-end':panel,scheme:dark?'dark':'light'};
    return snapshot;
  }
  function apply(host,config){
    r.dataset.atelierOwner=config.visual_owner||'ask';host.dataset.owner=config.visual_owner||'ask';
    if(['onigiri','external'].includes(config.visual_owner)){
      if(!snapshot)read();
      if(snapshot)for(const [k,v] of Object.entries(snapshot))host.style.setProperty('--'+k,v);
      host.dataset.companion='true';
    }else{
      if(snapshot)for(const k of Object.keys(snapshot))host.style.removeProperty('--'+k);
      snapshot=null;delete host.dataset.companion;
    }
    return snapshot;
  }
  window.AtelierOwnership=Object.freeze({apply,read,get:()=>snapshot?{...snapshot}:null});
})();
