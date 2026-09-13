(() => {'use strict';
 if(window.WorkshopHome){window.WorkshopHome.mount();return;}
 let node=null,anchor=null,disposed=false;
 function mount(html){
  if(disposed)return;
  let root=document.getElementById('ws-home');
  if(html!==undefined){if(!html){root?.remove();return;}if(!root){const t=document.createElement('template');t.innerHTML=html;root=t.content.firstElementChild;document.body.append(root);}}
  if(!root)return;
  if(root!==node){node=root;anchor=document.createComment('workshop-home');root.before(anchor);root.addEventListener('click',e=>{if(e.target.closest('[data-ws-open]')&&typeof pycmd==='function')pycmd('workshop:open');});}
  const host=document.getElementById('atelier-root');
  if(host?.shadowRoot?.querySelector('slot[name="atelier-widgets"]')&&document.body.classList.contains('atelier-home')){
   root.slot='atelier-widgets';host.append(root);root.dataset.host='atelier';root.style.setProperty('--ws-host-text',getComputedStyle(host).getPropertyValue('--text'));
  }else{root.removeAttribute('slot');delete root.dataset.host;if(anchor?.isConnected&&root.previousSibling!==anchor)anchor.after(root);}
 }
 const refresh=()=>mount();
 window.addEventListener('atelier:theme-change',refresh);window.addEventListener('atelier-theme-changed',refresh);document.addEventListener('DOMContentLoaded',refresh,{once:true});
 window.addEventListener('pagehide',()=>{disposed=true;window.removeEventListener('atelier:theme-change',refresh);window.removeEventListener('atelier-theme-changed',refresh);},{once:true});
 window.WorkshopHome={mount};mount();
})();
