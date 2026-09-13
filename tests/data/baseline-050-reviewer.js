/* Presentation only. Layout-only bridge; no answer handlers, template edits, scheduling or keys. */
(() => {
  'use strict';
  const start=()=>{
    const boot=document.getElementById('atelier-review-boot');
    if(!boot||window.AtelierReview)return;
    let config;try{config=JSON.parse(boot.textContent);}catch(_){return;}
    const root=document.documentElement;
    let lastGeometry='', geometryTimer=null, observedOuter=null, footerObserver=null;
    let info=window.__atelierReviewCard||{eligible:false,path:[],stage:'question'},header=null,scheduled=false;
    // Keep all flags/classes/styles owned by the card and every node in #qa.
    // Advanced/IO layouts retain their exact canvas and image geometry.
    function complexContent(){
      const qa=document.getElementById('qa');
      if(!qa)return true;
      return !!qa.querySelector('canvas,iframe,object,embed,#image-occlusion-container,#image-occlusion-canvas,#io-wrapper,#io-overlay,[data-occlusions],.io-overlay,.io-wrapper') || /(?:image.occlusion|io-overlay|io-wrapper)/i.test(qa.innerHTML);
    }
    function stockFooter(){
      const outer=document.getElementById('outer'),table=document.getElementById('innertable'),middle=document.getElementById('middle');
      if(!outer||!table||!middle||!outer.contains(table)||!table.contains(middle))return false;
      // A replacement bar owns its own sizing. Fail closed when the native
      // three-cell row is no longer present, rather than breaking its layout.
      const row=table.tBodies[0]?.rows[0];
      return !!row && row.cells.length===3 && row.cells[1]===middle &&
        row.cells[0].classList.contains('stat') && row.cells[2].classList.contains('stat');
    }
    function requestFooterFit(force=false){
      if(config.screen!=='review-bottom')return;
      clearTimeout(geometryTimer);
      geometryTimer=setTimeout(()=>{
        const outer=document.getElementById('outer');
        if(!outer)return;
        const key=[Math.ceil(outer.getBoundingClientRect().height),document.documentElement.clientWidth,root.dataset.atelierToolbar||'native',config.style].join(':');
        if(key===lastGeometry&&!force)return;lastGeometry=key;
        if(typeof window.pycmd==='function'&&config.layoutToken){
          window.pycmd('atelier:review-layout:'+config.layoutToken);
        }
        // Offline preview listens here; native Anki uses its own height fitter.
        window.dispatchEvent(new CustomEvent('atelier:review-layout',{detail:{height:Math.ceil(outer.getBoundingClientRect().bottom)+4}}));
      },60);
    }
    function footer(){
      if(config.screen!=='review-bottom')return;
      const stock=stockFooter();
      if(stock)root.dataset.atelierToolbar='stock';else delete root.dataset.atelierToolbar;
      const outer=document.getElementById('outer');
      if(outer!==observedOuter&&window.ResizeObserver){footerObserver?.disconnect();observedOuter=outer;if(outer){footerObserver=new ResizeObserver(()=>requestFooterFit());footerObserver.observe(outer);}}
      requestFooterFit();
    }
    function update(){
      scheduled=false;
      const enabled=config.style!=='off';
      if(!enabled){delete root.dataset.atelierScreen;delete root.dataset.atelierCard;delete root.dataset.atelierToolbar;header?.remove();header=null;requestFooterFit();return;}
      root.dataset.atelierScreen=config.screen;root.dataset.atelierMotion=config.motion?'on':'off';root.dataset.atelierWidth=config.width;
      if(config.screen==='review-bottom'){footer();return;}
      if(config.screen!=='review')return;
      const reading=config.style==='adaptive'&&info.eligible===true&&!complexContent();
      root.dataset.atelierCard=reading?'reading':'native';
      if(reading){
        if(!header){
          header=document.createElement('div');header.id='atelier-review-header';
          const label=document.createElement('span');label.className='atelier-review-stage';
          const title=document.createElement('strong');title.className='atelier-review-lecture';
          const path=document.createElement('span');path.className='atelier-review-path';
          header.append(label,title,path);
          const qa=document.getElementById('qa');if(qa)qa.before(header);
        }
        const path=Array.isArray(info.path)?info.path.map(String):[];
        header.querySelector('.atelier-review-stage').textContent=info.stage==='answer'?'REVEAL & REFLECT':'RECALL';
        header.querySelector('.atelier-review-lecture').textContent=path.at(-1)||'Your study session';
        header.querySelector('.atelier-review-path').textContent=path.slice(0,-1).join('  ›  ');
        header.querySelector('.atelier-review-path').title=path.join(' › ');
      }else{header?.remove();header=null;}
    }
    const queue=()=>{if(!scheduled){scheduled=true;requestAnimationFrame(update);}};
    const api={setCard(value){info=value||{eligible:false,path:[]};queue();},configure(value){config={...config,...value};update();},diagnostics(){return {screen:root.dataset.atelierScreen||'off',card:root.dataset.atelierCard||'native',width:config.width,toolbar:root.dataset.atelierToolbar||'native',layout:lastGeometry};}};
    window.AtelierReview=Object.freeze(api);
    const qa=document.getElementById('qa');
    if(qa){new MutationObserver(queue).observe(qa,{childList:true,subtree:true});}
    if(config.screen==='review-bottom'){
      new MutationObserver(queue).observe(document.body,{childList:true,subtree:true});
      window.addEventListener('resize',()=>requestFooterFit());
      document.fonts?.ready.then(()=>requestFooterFit(true));
    }
    update();
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
