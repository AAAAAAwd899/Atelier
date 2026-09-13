/* Unified world switcher. Changes presentation in place; never resets a draft. */
(()=>{'use strict';
 const boot=window.AtelierWorldBootstrap;if(!boot||window.AtelierWorlds)return;
 let config={...boot.config},busy=false,queued=false;
 const root=document.documentElement;
 function configure(next){config={...config,...next};root.dataset.atelierWorld=config.theme;root.dataset.atelierScenery=String(config.enabled&&config.ambience);root.dataset.atelierWorldEnabled=String(config.enabled);root.dataset.atelierWorldMotion=String(config.motion);mount();}
 function mount(){
  const header=document.querySelector('#es-app .es-app-header');if(!header)return;
  let shell=header.querySelector('.suite-world-switch');
  if(!config.enabled){shell?.remove();return;}
  if(!shell){
   shell=document.createElement('label');shell.className='suite-world-switch';shell.append(document.createTextNode('World'));
   const select=document.createElement('select');select.setAttribute('aria-label','Study world');
   for(const world of boot.catalog){const option=document.createElement('option');option.value=world.id;option.textContent=world.name;select.append(option);}
   select.addEventListener('change',async()=>{
    if(busy)return;const restoreFocus=document.activeElement===select;busy=true;select.disabled=true;const was=config.theme;
    try{const saved=await window.ExamSprout.suiteRequest('suite_theme',{theme:select.value});configure({theme:saved.theme});}
    catch(err){select.value=was;const msg=document.createElement('span');msg.className='suite-world-error';msg.setAttribute('role','alert');msg.textContent=err.message;shell.append(msg);setTimeout(()=>msg.remove(),7000);}
    finally{busy=false;select.disabled=false;if(restoreFocus&&select.isConnected&&[document.body,document.documentElement,select].includes(document.activeElement))select.focus({preventScroll:true});}
   });shell.append(select);header.querySelector('.es-top-nav')?.before(shell);
  }
  const select=shell.querySelector('select');if(select.value!==config.theme)select.value=config.theme;
 }
 function queue(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;mount();});}
 function start(){configure(config);const app=document.getElementById('es-app');if(app){new MutationObserver(records=>{if(records.some(r=>Array.from(r.addedNodes).some(n=>n.nodeType===1&&!n.matches('.suite-world-switch,.suite-world-error')&&(n.matches('.es-app-header')||n.querySelector?.('.es-app-header')))))queue();}).observe(app,{childList:true,subtree:true});}}
 window.AtelierWorlds=Object.freeze({configure,getConfig:()=>({...config})});
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
