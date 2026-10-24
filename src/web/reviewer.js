/* Presentation only. Layout-only bridge; no answer handlers, template edits, scheduling or keys. */
(() => {
  'use strict';
  const start=()=>{
    const boot=document.getElementById('atelier-review-boot');
    if(!boot||window.AtelierReview)return;
    let config;try{config=JSON.parse(boot.textContent);}catch(_){return;}
    const root=document.documentElement;
    let lastGeometry='', geometryTimer=null, observedOuter=null, footerObserver=null;
    let info=window.__atelierReviewCard||{eligible:false,path:[],stage:'question'},header=null,scheduled=false,resetQuestion=false;
    let gapOriginal=null,gapNode=null,qaSizeObserver=null,observedQA=null,alignFrame=0,settleUntil=0,userMoved=false,paintKey='',disposed=false;
    const keyOf=x=>String(x?.id||'')+':'+String(x?.stage||'question');
    let fitted=null,fitEnabled=true,fitControl=null,fitTimers=[],imageSizeObserver=null,observedImageStage=null;
    function releaseImageFit(keepObserver=false){
      if(!keepObserver){imageSizeObserver?.disconnect();imageSizeObserver=null;observedImageStage=null;}
      if(fitted){const {stage,box}=fitted;if(box.isConnected&&box.contains(stage))box.replaceWith(stage);fitted=null;}
    }
    function sizeImageFit(){
      if(!fitted)return;
      const {stage,box,plane,qa}=fitted,w=stage.offsetWidth,h=stage.offsetHeight;
      if(w<1||h<1)return;
      const top=box.getBoundingClientRect().top+scrollY;
      const tail=Math.max(0,qa.getBoundingClientRect().bottom-box.getBoundingClientRect().bottom);
      const scale=Math.min(1,Math.max(120,innerHeight-top-tail-28)/h,Math.max(120,qa.clientWidth-16)/w);
      const key=w+':'+h+':'+scale;
      if(fitted.size===key)return;
      fitted.size=key;fitted.scale=scale;
      box.style.width=w*scale+'px';box.style.height=h*scale+'px';
      plane.style.transform=`scale(${scale})`;
    }
    function fitImage(){
      const viewport=innerWidth+'x'+innerHeight+':'+(header?.offsetHeight||0);
      if(fitEnabled&&fitted?.box.isConnected&&fitted.viewport===viewport){sizeImageFit();return;}
      releaseImageFit(true);
      const qa=document.getElementById('qa'),stage=qa?.querySelector('#image-occlusion-container');
      const supported=config.style==='adaptive'&&info.ioFit===true&&!info.protected&&
        stage&&stage.children.length===2&&stage.children[0].tagName==='IMG'&&
        stage.children[1].matches('canvas#image-occlusion-canvas')&&typeof window.anki?.imageOcclusion?.setup==='function';
      if(!supported){releaseImageFit();fitControl?.remove();fitControl=null;return;}
      // Native setup can enlarge the stage after image load, including when its
      // first measured size needed no fit. Observe before every early return.
      if(window.ResizeObserver&&observedImageStage!==stage){
        imageSizeObserver?.disconnect();observedImageStage=stage;
        imageSizeObserver=new ResizeObserver(scheduleLayout);imageSizeObserver.observe(stage);
      }
      if(!fitControl){
        fitControl=document.createElement('button');fitControl.type='button';fitControl.id='atelier-image-fit';
        fitControl.addEventListener('click',()=>{fitEnabled=!fitEnabled;fitImage();});
      }
      if(!fitControl.isConnected)qa.before(fitControl);
      fitControl.textContent=fitEnabled?'Actual size':'Fit image';fitControl.setAttribute('aria-label',fitEnabled?'Show image at original view size':'Fit image and masks together');
      fitControl.setAttribute('aria-pressed',String(fitEnabled));
      if(!fitEnabled||!stage.children[0].complete||!stage.children[0].naturalWidth)return;
      const r=stage.getBoundingClientRect();if(r.width<1||r.height<1)return;
      const clearance=Math.max(0,Number(window.onigiriReviewerHeaderOffsetPx)||0);
      const top=Math.max(clearance+48,r.top+scrollY);
      const scale=Math.min(1,Math.max(120,innerHeight-top-40)/r.height,Math.max(120,qa.clientWidth-16)/r.width);
      if(scale>=.999)return;
      // A single transform on an owned parent scales image and native canvas
      // together. Neither original node, canvas dimensions nor masks are edited.
      const box=document.createElement('div'),plane=document.createElement('div');
      box.className='atelier-image-fit-box';box.style.cssText=`position:relative;width:${r.width*scale}px;height:${r.height*scale}px;margin:12px auto;`;
      plane.style.cssText=`position:absolute;inset:0 auto auto 0;width:${r.width}px;height:${r.height}px;transform-origin:0 0;transform:scale(${scale});`;
      stage.before(box);box.append(plane);plane.append(stage);fitted={stage,box,plane,qa,scale,viewport};
      sizeImageFit();
    }
    // Keep all flags/classes/styles owned by the card and every node in #qa.
    // Advanced/IO layouts retain their exact canvas and image geometry.
    function complexContent(){
      const qa=document.getElementById('qa');
      if(!qa)return true;
      return info.protected===true || !!qa.querySelector('canvas,iframe,object,embed,#image-occlusion-container,#image-occlusion-canvas,[id^=io-],[id^=io_],[data-occlusions],.io-overlay,.io-wrapper,.io-mask,.image-occlusion') || /(?:image.occlusion|io[-_](?:overlay|wrapper|qmask|amask|original|container))/i.test(qa.innerHTML) || [...qa.querySelectorAll('[style]')].some(e=>/position\s*:\s*(absolute|fixed|sticky)|transform\s*:|zoom\s*:/.test(e.getAttribute('style')||''));
    }
    function imageOcclusion(){
      if(info.protected===true)return false;
      const qa=document.getElementById('qa');
      return !!qa?.querySelector('#image-occlusion-container,#image-occlusion-canvas,#io-wrapper,#io-overlay,[data-occlusions],.io-wrapper,.io-overlay') || info.imageOcclusion===true;
    }
    // Only own #qa's top gap for eligible reading cards; never resize, wrap or
    // transform the original image/canvas/masks. Restore the latest foreign value.
    function releaseGap(){
      if(gapNode&&gapOriginal&&gapNode.style.getPropertyValue('margin-top')===gapOriginal.applied&&gapNode.style.getPropertyPriority('margin-top')==='important'){
        if(gapOriginal.value)gapNode.style.setProperty('margin-top',gapOriginal.value,gapOriginal.priority);else gapNode.style.removeProperty('margin-top');
      }
      gapNode=null;gapOriginal=null;
    }
    function ownGap(qa){
      if(gapNode!==qa){releaseGap();gapNode=qa;}
      const v=qa.style.getPropertyValue('margin-top'),p=qa.style.getPropertyPriority('margin-top'),desired=config.context==='hidden'?'auto':'0px';
      if(gapOriginal&&v===gapOriginal.applied&&p==='important'){if(v!==desired){qa.style.setProperty('margin-top',desired,'important');gapOriginal.applied=desired;}return;}
      gapOriginal={value:v,priority:p,applied:desired};qa.style.setProperty('margin-top',desired,'important');
    }
    function observeSize(qa){
      if(observedQA===qa)return;
      qaSizeObserver?.disconnect();observedQA=qa;
      if(qa&&window.ResizeObserver){qaSizeObserver=new ResizeObserver(scheduleLayout);qaSizeObserver.observe(qa);}
    }
    function settleLayout(){
      alignFrame=0;
      if(!disposed&&config.screen==='review'&&info.ioFit===true){fitImage();return;}
      if(disposed||config.screen!=='review'||root.dataset.atelierCard!=='reading')return;
      const qa=document.getElementById('qa');if(!qa)return;
      ownGap(qa);observeSize(qa);
      const clearance=Math.max(0,Number(window.onigiriReviewerHeaderOffsetPx)||0);
      const v=clearance+'px';if(root.style.getPropertyValue('--atelier-header-clearance')!==v)root.style.setProperty('--atelier-header-clearance',v);
      const st=getComputedStyle(document.body),qr=qa.getBoundingClientRect();
      const hr=header?.isConnected?header.getBoundingClientRect():null;
      const pad=parseFloat(st.paddingTop)+parseFloat(st.paddingBottom);
      const total=qr.height+(hr?hr.height+10:0)+pad;
      root.dataset.atelierFit=total<=innerHeight+1?'fits':'scroll';
      // Counter Anki's delayed answer scroll ONLY when the whole reading card fits.
      // Long answers retain native answer-anchor scrolling and manual scrolling wins.
      if(!userMoved && performance.now()<settleUntil && (resetQuestion||total<=innerHeight+1)){
        window.scrollTo({top:0,left:0,behavior:'instant'});resetQuestion=false;
      }
    }
    function scheduleLayout(){if(!alignFrame&&!disposed)alignFrame=requestAnimationFrame(settleLayout);}
    function newPaint(value){
      if(keyOf(value)!==paintKey){releaseImageFit();fitControl?.remove();fitControl=null;fitTimers.forEach(clearTimeout);fitTimers=[60,180,450,1000].map(ms=>setTimeout(scheduleLayout,ms));}
      const key=keyOf(value);if(key!==paintKey){paintKey=key;userMoved=false;settleUntil=performance.now()+1600;resetQuestion=value?.stage==='question';if(header){header.dataset.expanded='false';const b=header.querySelector('button');if(b){b.setAttribute('aria-expanded','false');b.textContent='Details';}}}
      info=value||{eligible:false,path:[]};queue();scheduleLayout();
    }
    function stockFooter(){
      const outer=document.getElementById('outer'),table=document.getElementById('innertable'),middle=document.getElementById('middle');
      if(!outer||!table||!middle||!outer.contains(table)||!table.contains(middle))return false;
      // A replacement bar owns its own sizing. Fail closed when the native
      // three-cell row is no longer present, rather than breaking its layout.
      const row=table.tBodies[0]?.rows[0];
      return !!row && row.cells.length>=3 && Array.from(row.cells).includes(middle) &&
        row.cells[0].classList.contains('stat') && row.cells[row.cells.length-1].classList.contains('stat');
    }
    function measureFooter(){
      if(config.screen!=='review-bottom'||config.style==='off'||!stockFooter())return null;
      const outer=document.getElementById('outer'),r=outer.getBoundingClientRect();
      const height=Math.ceil(Math.max(r.height,outer.scrollHeight)+Math.max(0,r.top)+2);
      return {token:config.layoutToken,height,width:root.clientWidth,version:config.version||'1.0.8'};
    }
    function requestFooterFit(force=false){
      if(config.screen!=='review-bottom')return;
      clearTimeout(geometryTimer);
      geometryTimer=setTimeout(()=>{
        const outer=document.getElementById('outer');
        if(!outer)return;
        const key=[Math.ceil(outer.getBoundingClientRect().height),document.documentElement.clientWidth,window.innerHeight,root.dataset.atelierToolbar||'native',config.style].join(':');
        if(key===lastGeometry&&!force)return;lastGeometry=key;
        if(typeof window.pycmd==='function'&&config.layoutToken){
          window.pycmd('atelier:review-layout:'+config.layoutToken);
        }
        // Offline preview listens here; native Anki receives the guarded measurement.
        window.dispatchEvent(new CustomEvent('atelier:review-layout',{detail:{height:Math.ceil(outer.getBoundingClientRect().bottom)+4}}));
      },60);
    }
    function footer(){
      if(config.screen!=='review-bottom')return;
      const stock=stockFooter();
      if(stock){root.dataset.atelierToolbar='stock';root.dataset.atelierExtraCells=String(document.getElementById('innertable').tBodies[0].rows[0].cells.length>3);}else{delete root.dataset.atelierToolbar;delete root.dataset.atelierExtraCells;}
      const outer=document.getElementById('outer');
      if(outer!==observedOuter&&window.ResizeObserver){footerObserver?.disconnect();observedOuter=outer;if(outer){footerObserver=new ResizeObserver(()=>requestFooterFit());footerObserver.observe(outer);}}
      requestFooterFit();
    }
    function update(){
      scheduled=false;
      const enabled=config.style!=='off';
      if(!enabled){releaseImageFit();fitControl?.remove();fitControl=null;releaseGap();observeSize(null);delete root.dataset.atelierFit;delete root.dataset.atelierScreen;delete root.dataset.atelierCard;delete root.dataset.atelierToolbar;header?.remove();header=null;delete root.dataset.atelierContext;requestFooterFit();return;}
      root.dataset.atelierScreen=config.screen;root.dataset.atelierWorld=config.theme;root.dataset.atelierMotion=config.motion?'on':'off';root.dataset.atelierWidth=config.width;root.dataset.atelierAmbience=String(config.ambience!==false);root.dataset.atelierContext=['compact','full','hidden'].includes(config.context)?config.context:'compact';
      if(config.screen==='review-bottom'){footer();return;}
      if(config.screen!=='review')return;
      const reading=config.style==='adaptive'&&info.eligible===true&&!complexContent();
      root.dataset.atelierCard=reading?'reading':config.style==='adaptive'&&imageOcclusion()?'media':'native';
      if((reading||info.ioFit===true)&&config.context!=='hidden'){
        if(!header){
          header=document.createElement('div');header.id='atelier-review-header';
          const label=document.createElement('span');label.className='atelier-review-stage';
          const title=document.createElement('strong');title.className='atelier-review-lecture';
          const path=document.createElement('span');path.className='atelier-review-path';
          const toggle=document.createElement('button');toggle.type='button';toggle.className='atelier-review-details';
          toggle.textContent='Details';toggle.title='Show lecture path';toggle.setAttribute('aria-label','Show lecture path');toggle.setAttribute('aria-expanded','false');
          path.id='atelier-review-path';toggle.setAttribute('aria-controls',path.id);
          toggle.addEventListener('click',()=>{const open=header.dataset.expanded!=='true';header.dataset.expanded=String(open);toggle.setAttribute('aria-expanded',String(open));toggle.textContent=open?'Less':'Details';scheduleLayout();});
          header.append(label,title,toggle,path);
          const qa=document.getElementById('qa');if(qa)qa.before(header);
        }
        const path=Array.isArray(info.path)?info.path.map(String):[];
        if(!header.isConnected){document.getElementById('qa')?.before(header);}
        header.querySelector('.atelier-review-stage').textContent=info.stage==='answer'?'REVEAL & REFLECT':'RECALL';
        header.querySelector('.atelier-review-lecture').textContent=path.at(-1)||'Your study session';
        header.querySelector('.atelier-review-path').textContent=path.slice(0,-1).join('  ›  ');
        header.querySelector('.atelier-review-path').title=path.join(' › ');
      }else{header?.remove();header=null;}
      if(reading){ownGap(document.getElementById('qa'));scheduleLayout();}
      else {resetQuestion=false;releaseGap();observeSize(null);delete root.dataset.atelierFit;}
      if(info.ioFit===true)scheduleLayout();else{releaseImageFit();fitControl?.remove();fitControl=null;}

    }
    const queue=()=>{if(!scheduled){scheduled=true;queueMicrotask(update);}};
    const api={painted:newPaint,settled(value){if(keyOf(value)===keyOf(info)){newPaint(value);scheduleLayout();}},measureFooter,refit:()=>requestFooterFit(true),setCard(value){newPaint(value);},configure(value){config={...config,...value};update();},diagnostics(){return {screen:root.dataset.atelierScreen||'off',card:root.dataset.atelierCard||'native',width:config.width,toolbar:root.dataset.atelierToolbar||'native',context:root.dataset.atelierContext||'original',layout:lastGeometry,version:config.version||'1.0.3',height:measureFooter()?.height||0,viewportHeight:innerHeight,scrollHeight:document.scrollingElement?.scrollHeight,fit:root.dataset.atelierFit||'native',headerClearance:root.style.getPropertyValue('--atelier-header-clearance'),bodyBackground:getComputedStyle(document.body).backgroundColor,controls:[...document.querySelectorAll('#outer button')].map(b=>{const r=b.getBoundingClientRect();return {command:b.getAttribute('onclick')?.match(/(?:ease[1-4]|ans|edit|more)/)?.[0]||'extension',x:r.x,y:r.y,width:r.width,height:r.height};})};}};
    window.AtelierReview=Object.freeze(api);
    const qa=document.getElementById('qa');
    if(qa){new MutationObserver(queue).observe(qa,{childList:true,subtree:true});new MutationObserver(scheduleLayout).observe(qa,{attributes:true,attributeFilter:['style']});}
    if(config.screen==='review-bottom'){
      new MutationObserver(queue).observe(document.body,{childList:true,subtree:true});
      window.addEventListener('resize',()=>requestFooterFit());
      document.fonts?.ready.then(()=>requestFooterFit(true));
    }
    if(config.screen==='review'){
      window.addEventListener('onigiri-reviewer-header-offset',queue);window.addEventListener('resize',queue);
      document.addEventListener('load',scheduleLayout,true);document.fonts?.ready.then(scheduleLayout);
      for(const name of ['wheel','touchmove','pointerdown'])window.addEventListener(name,()=>{userMoved=true;},{passive:true});
      window.addEventListener('keydown',e=>{if(['PageDown','PageUp','ArrowDown','ArrowUp','Home','End'].includes(e.key))userMoved=true;},true);
      window.addEventListener('pagehide',()=>{disposed=true;cancelAnimationFrame(alignFrame);qaSizeObserver?.disconnect();},{once:true});
    }
    update();
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
