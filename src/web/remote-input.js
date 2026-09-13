/* Focus permission only. No key recording or key handlers in the card DOM. */
(()=>{'use strict';
 window.AtelierRemoteInput?.dispose();
 const token=window.AtelierRemoteToken;
 if(!token)return;
 let disposed=false,last='',queued=false;
 function check(fromFooter=false){
   let el=document.activeElement;
   while(el?.shadowRoot?.activeElement)el=el.shadowRoot.activeElement;
   const editable=!!(el?.isContentEditable||el?.closest?.('input,textarea,select,[contenteditable]:not([contenteditable="false"]),[role="textbox"],iframe,object,embed'));
   const modal=!!document.querySelector('dialog[open],[aria-modal="true"]');
   return {token,ready:!disposed&&(fromFooter||document.hasFocus())&&!document.hidden&&(fromFooter||!editable)&&!modal};
 }
 function report(){queued=false;if(disposed)return;const value=check().ready?'ready':'blocked';if(value!==last){last=value;window.pycmd?.('atelier-remote-focus:'+token+':'+value);}}
 function queue(){if(!queued){queued=true;queueMicrotask(report);}}
 const events=['focusin','focusout','visibilitychange'];for(const n of events)document.addEventListener(n,queue,true);
 window.addEventListener('focus',queue);window.addEventListener('blur',queue);
 const observer=new MutationObserver(queue);observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['open','aria-modal']});
 function dispose(){disposed=true;observer.disconnect();for(const n of events)document.removeEventListener(n,queue,true);window.removeEventListener('focus',queue);window.removeEventListener('blur',queue);window.removeEventListener('pagehide',dispose);}
 window.addEventListener('pagehide',dispose,{once:true});window.AtelierRemoteInput=Object.freeze({check,dispose});report();
})();
