/* Owns the live 3D habitat and its exact-model low-power fallback. */
(()=>{'use strict';
window.PipCompanion?.dispose?.();
const live=new Map(),reduced=matchMedia('(prefers-reduced-motion: reduce)');
let hostPaused=false,disposed=false,mutating=false;
function stopTimer(s){if(s.timer)clearTimeout(s.timer);s.timer=null;}
function fallback(s,action='idle'){
 s.root.dataset.pipRenderer='fallback';s.canvas.hidden=true;s.image.hidden=false;
 const still=hostPaused||document.hidden||reduced.matches||s.userPaused||!s.visible;
 const url=`${s.base}/stage${s.stage}${still?'.png':'-'+action+'.webp'}`;
 if(s.image.getAttribute('src')!==url)s.image.src=url;
}
function sync(s){if(!s.root.isConnected)return;
 const pause=hostPaused||document.hidden||reduced.matches||s.userPaused;
 if(s.scene){
  const present=s.visible&&!hostPaused&&!document.hidden;
  s.scene.setHidden(!present);s.scene.setPaused(pause);
  // Off-screen WebGL buffers may be discarded by the host. Keep an exact-model
  // still visible instead of leaving a blank habitat, and draw on re-entry.
  if(s.canvas.hidden===present){s.canvas.hidden=!present;s.image.hidden=present;if(present){s.scene.resize();s.scene.render(s.scene.time);}else{s.image.src=`${s.base}/stage${s.stage}.png`;}}
 }
 else fallback(s);
 const b=s.root.querySelector('.pip-pause');if(b){b.setAttribute('aria-pressed',String(s.userPaused));const text=s.userPaused?'Resume motion':'Pause motion';if(b.textContent!==text)b.textContent=text;}
 s.root.dataset.pipPaused=String(pause);const mode=s.root.querySelector('.pip-mode'),text=s.scene?'Live 3D · Local only':'Low-power animation · Local only';if(mode&&mode.textContent!==text)mode.textContent=text;
}
function mount(){if(disposed||mutating)return;mutating=true;
 for(const [root,s]of live){if(!root.isConnected){stopTimer(s);intersection.unobserve(root);s.scene?.dispose();live.delete(root);}}
 document.querySelectorAll('.pip-card').forEach(root=>{if(live.has(root)){const s=live.get(root);s.userPaused=root.dataset.pipAnimate==='false';sync(s);return;}const image=root.querySelector('.pip-image'),canvas=root.querySelector('.pip-canvas');if(!image||!canvas)return;
 const s={root,image,canvas,base:root.dataset.pipBase,stage:Math.max(1,Math.min(4,Number(root.dataset.pipStage)||1)),userPaused:root.dataset.pipAnimate==='false',visible:true,scene:null,timer:null,down:null};live.set(root,s);
 try{if(!window.PipScene)throw Error('3D module is unavailable');s.scene=new PipScene.Scene(canvas,{stage:s.stage,onLost:()=>{s.scene?.dispose();s.scene=null;fallback(s);sync(s);}});root.dataset.pipRenderer='webgl2';image.hidden=true;canvas.hidden=false;}
 catch(error){root.dataset.pipFallbackReason='WebGL 2 unavailable';fallback(s);}
 intersection.observe(root);sync(s);
 });mutating=false;
}
function act(s,action){if(!['pet','water','greet'].includes(action))return;
 const speech=s.root.querySelector('.pip-speech');speech.textContent=action==='water'?'A small sip. A happy leaf.':action==='greet'?'Hello again. Ready when you are.':'A little encouragement goes a long way.';
 stopTimer(s);const still=hostPaused||document.hidden||reduced.matches||s.userPaused;
 if(!still){if(s.scene)s.scene.setAction(action);else fallback(s,action==='greet'?'pet':action);}
 s.timer=setTimeout(()=>{s.timer=null;if(!s.root.isConnected)return;speech.textContent='Quiet company. No distractions.';if(!s.scene)fallback(s);/* Live actions finish on scene time, never while their paused clock is stopped. */},3200);
}
function click(e){const b=e.target.closest('[data-pip-action]'),root=b?.closest('.pip-card'),s=live.get(root);if(!s)return;
 if(s.dragged){s.dragged=false;return;}
 if(b.dataset.pipAction==='pause'){s.userPaused=!s.userPaused;root.dataset.pipAnimate=String(!s.userPaused);stopTimer(s);sync(s);root.dispatchEvent(new CustomEvent('pip-preference',{bubbles:true,detail:{animate:!s.userPaused}}));return;}
 act(s,b.dataset.pipAction);
}
function pointer(e){const root=e.target.closest('.pip-card'),s=live.get(root);if(!s?.scene)return;const box=s.canvas.getBoundingClientRect();s.scene.setPointer((e.clientX-box.left)/box.width*2-1,(e.clientY-box.top)/box.height*2-1);
 if(s.down&&e.buttons===1){const d=e.clientX-s.down.x;if(Math.abs(d)>3)s.dragged=true;if(s.dragged){s.scene.setTurn(d*.006);s.down.x=e.clientX;}}
}
function down(e){const root=e.target.closest('.pip-touch'),s=root&&live.get(root.closest('.pip-card'));if(s){s.down={x:e.clientX};s.dragged=false;}}
function up(){for(const s of live.values())s.down=null;}
function leave(e){const s=live.get(e.target.closest?.('.pip-card'));if(s?.scene&&!s.down)s.scene.setPointer(0,0);}
function syncAll(){live.forEach(sync);}
function pause(){hostPaused=true;syncAll();}
function resume(){hostPaused=false;mount();syncAll();}
function unmount(){live.forEach(s=>{stopTimer(s);s.scene?.dispose();intersection.unobserve(s.root);});live.clear();}
function dispose(){if(disposed)return;disposed=true;unmount();observer.disconnect();intersection.disconnect();document.removeEventListener('click',click);document.removeEventListener('pointermove',pointer);document.removeEventListener('pointerdown',down);document.removeEventListener('pointerup',up);document.removeEventListener('visibilitychange',syncAll);document.removeEventListener('pointercancel',up);document.removeEventListener('pointerleave',leave,true);reduced.removeEventListener('change',syncAll);}
const intersection=new IntersectionObserver(entries=>{for(const e of entries){const s=live.get(e.target);if(s){s.visible=e.isIntersecting;sync(s);}}},{threshold:.03});
const observer=new MutationObserver(records=>{if(records.some(r=>[...r.addedNodes,...r.removedNodes].some(n=>n.nodeType===1&&(n.matches?.('.pip-card')||n.querySelector?.('.pip-card')))))mount();});observer.observe(document.documentElement,{childList:true,subtree:true});
document.addEventListener('click',click);document.addEventListener('pointermove',pointer,{passive:true});document.addEventListener('pointerdown',down,{passive:true});document.addEventListener('pointerup',up,{passive:true});document.addEventListener('visibilitychange',syncAll);document.addEventListener('pointercancel',up);document.addEventListener('pointerleave',leave,true);reduced.addEventListener('change',syncAll);
window.PipCompanion={mount,pause,resume,dispose,unmount,info:()=>[...live.values()].map(s=>s.scene?.info()||{renderer:'fallback',stage:s.stage}),version:'0.9.7'};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
})();
