/* Atelier Mask Studio. No collection writes: produces normalized draft rectangles. */
(() => {
'use strict';
const clone=x=>JSON.parse(JSON.stringify(x));
const uid=()=>Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(16).padStart(2,'0')).join('');
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const groups=items=>[...new Set(items.map(x=>x.group))].sort((a,b)=>a-b);
function grid(region,rows,columns,by,start=1) {
  if(!Number.isInteger(rows)||!Number.isInteger(columns)||rows<1||rows>20||columns<1||columns>20)throw Error('Use 1–20 rows and columns.');
  if(!['cell','row','column','together'].includes(by))throw Error('Choose a grouping for the table.');
  const count=by==='cell'?rows*columns:by==='row'?rows:by==='column'?columns:1;
  if(start+count-1>500)throw Error('One image supports at most 500 numbered questions.');
  const out=[];
  for(let r=0;r<rows;r++)for(let c=0;c<columns;c++)out.push({id:uid(),group:start+(by==='cell'?r*columns+c:by==='row'?r:by==='column'?c:0),
    x:region.x+c*region.w/columns,y:region.y+r*region.h/rows,w:region.w/columns,h:region.h/rows});
  return out;
}
function mount(container, options) {
 const state={masks:clone(options.masks||[]),hide:options.hideOthers!==false,mode:'separate',tool:'draw',group:1,
   selected:new Set(),past:[],future:[],gesture:null,last:null,region:null,preview:false,reveal:false,previewGroup:1};
 let disposed=false;
 const button=(a,label,attrs='')=>`<button type="button" data-mask-action="${a}" ${attrs}>${label}</button>`;
 container.innerHTML=`<section class="mask-studio" aria-label="Mask Studio">
   <div class="mask-modebar"><div class="mask-segments" role="group" aria-label="Question grouping">${button('separate','Separate questions')}${button('same','Same question')}</div>
     <span class="mask-count" role="status"></span></div>
   <div class="mask-toolbar" aria-label="Mask tools"><div class="mask-segments">${button('draw','Draw')}${button('stamp','Stamp')}${button('select','Select')}${button('table','Table')}${button('preview','Preview')}</div>
     <label class="mask-zoom">View <select data-mask-field="zoom" aria-label="Mask image zoom"><option value="100">Fit width</option><option value="125">125%</option><option value="150">150%</option><option value="200">200%</option></select></label><div class="mask-edit-tools">${button('undo','Undo')}${button('redo','Redo')}${button('duplicate','Duplicate')}${button('remove','Delete')}</div></div>
   <div class="mask-options"><label>Question <select data-mask-field="group" aria-label="Active question"></select></label>${button('next-group','Next question')}${button('group-selected','Put selection in this question')}
     <label class="mask-hide"><input type="checkbox" data-mask-field="hide" ${state.hide?'checked':''}> Keep other answers covered</label></div>
   <div class="mask-grid-settings" hidden><strong>Divide the selected region</strong><div class="mask-grid-inputs"><label>Rows <input type="number" data-mask-field="rows" value="3" min="1" max="20"></label><label>Columns <input type="number" data-mask-field="cols" value="2" min="1" max="20"></label><label>Create <select data-mask-field="grid-group"><option value="cell">One question per cell</option><option value="row">One per row</option><option value="column">One per column</option><option value="together">All cells together</option></select></label>${button('apply-grid','Create masks')}${button('cancel-grid','Cancel')}</div><p>Draw around only the answer cells. Leave headers outside this region.</p></div>
   <div class="mask-preview-controls" hidden><label>Preview question <select data-mask-field="preview-group"></select></label>${button('flip','Show answer')}<span>Layout preview · approved cards use Anki’s native Image Occlusion template.</span></div>
   <p class="mask-instruction" role="status"></p>
   <div class="mask-scroll"><div class="mask-image-area" tabindex="0" aria-label="Image mask workspace. Draw with the pointer; select a mask to move it with the arrow keys."><img src="${esc(options.image)}" draggable="false" alt="Source image for occlusion"><div class="mask-overlays"></div></div></div>
   <div class="mask-status"><span class="mask-selected"></span><span>Shift: multi-select / larger nudges · Delete: remove · Ctrl Z: undo</span></div>
   <p class="mask-error" role="alert" hidden></p></section>`;
 const q=s=>container.querySelector(s),area=q('.mask-image-area'),overlay=q('.mask-overlays');
 const error=message=>{const el=q('.mask-error');el.textContent=message;el.hidden=!message;};
 const next=()=>Math.max(0,...state.masks.map(m=>m.group))+1;
 function snapshot(){return clone(state.masks);}
 function changed(before){
   if(JSON.stringify(before)===JSON.stringify(state.masks)){paint();return;}
   state.past.push(before);if(state.past.length>80)state.past.shift();state.future=[];
   if(state.masks.length>1000){state.masks=state.past.pop();throw Error('One image can contain up to 1,000 masks.');}
   state.selected=new Set([...state.selected].filter(id=>state.masks.some(m=>m.id===id)));
   options.onChange?.(clone(state.masks),state.hide);paint();
 }
 function addMask(rect){
   const group=state.mode==='same'?state.group:next();
   if(group>500)throw Error('Use up to 500 questions on one image.');
   const m={id:uid(),group,...rect};state.masks.push(m);state.selected=new Set([m.id]);state.group=group;state.last={w:m.w,h:m.h};return m;
 }
 function selectOptions(el,current,values){el.innerHTML=values.map(n=>`<option value="${n}"${current===n?' selected':''}>${n}</option>`).join('');}
 function paint(){
   if(disposed)return;
   const gs=groups(state.masks),values=[...new Set([...gs,state.group])].sort((a,b)=>a-b);
   q('.mask-count').textContent=`${state.masks.length} masks · ${gs.length} cards`;
   for(const b of container.querySelectorAll('[data-mask-action]')){
     const a=b.dataset.maskAction;
     if(['separate','same'].includes(a))b.setAttribute('aria-pressed',String(a===state.mode));
     if(['draw','stamp','select','table','preview'].includes(a))b.setAttribute('aria-pressed',String(a===(state.preview?'preview':state.tool)));
     if(a==='undo')b.disabled=!state.past.length||state.preview;
     if(a==='redo')b.disabled=!state.future.length||state.preview;
     if(['duplicate','remove','group-selected'].includes(a))b.disabled=!state.selected.size||state.preview;
     if(a==='next-group')b.disabled=state.preview||next()>500;
   }
   selectOptions(q('[data-mask-field="group"]'),state.group,values);
   if(!gs.includes(state.previewGroup))state.previewGroup=gs[0]||1;
   selectOptions(q('[data-mask-field="preview-group"]'),state.previewGroup,gs.length?gs:[1]);
   q('.mask-preview-controls').hidden=!state.preview;
   q('.mask-options').hidden=state.preview;
   q('.mask-grid-settings').hidden=!state.region||state.preview;
   q('[data-mask-action="flip"]').textContent=state.reveal?'Hide answer':'Show answer';
   area.dataset.tool=state.preview?'preview':state.tool;
   const messages={draw:state.mode==='same'?`Draw boxes for question ${state.group}. Choose Next question when this group is complete.`:'Draw an answer box. Each new box becomes a separate question.',
     stamp:state.last?'Click to place another mask of the same size.':'Draw a first rectangle, then use Stamp to repeat its size.',
     select:'Click a mask to select it. Drag to move; use a corner handle to resize. Shift-click adds to your selection.',
     table:'Drag around the answer cells, then choose the number of rows and columns.'};
   q('.mask-instruction').textContent=state.preview?`Question ${state.previewGroup} · ${state.reveal?'Answer revealed':'Recall the hidden content'}`:messages[state.tool];
   q('.mask-selected').textContent=state.selected.size?`${state.selected.size} selected`:'No masks selected';
   const rectangles=[...state.masks];if(state.gesture?.temp)rectangles.push({...state.gesture.temp,id:'temporary',group:state.group});
   overlay.innerHTML=rectangles.map(m=>{
     const chosen=state.selected.has(m.id),target=m.group===state.previewGroup;
     if(state.preview&&((target&&state.reveal)||(!target&&!state.hide)))return '';
     return `<div class="mask-rect ${chosen&&!state.preview?'selected':''} ${state.preview?'mask-opaque '+(target?'current':'inactive'):''}" data-mask-id="${m.id}" style="left:${m.x*100}%;top:${m.y*100}%;width:${m.w*100}%;height:${m.h*100}%" role="img" aria-label="Question ${m.group} mask">
       ${!state.preview?`<span class="mask-number">${m.group}</span>`:''}${chosen&&!state.preview&&state.selected.size===1?['nw','ne','sw','se'].map(c=>`<span class="mask-handle ${c}" data-mask-handle="${c}" data-mask-id="${m.id}"></span>`).join(''):''}</div>`;
   }).join('');
   if(state.region)overlay.insertAdjacentHTML('beforeend',`<div class="mask-table-region" style="left:${state.region.x*100}%;top:${state.region.y*100}%;width:${state.region.w*100}%;height:${state.region.h*100}%"></div>`);
 }
 function point(e){const r=area.getBoundingClientRect();return {x:clamp((e.clientX-r.left)/r.width,0,1),y:clamp((e.clientY-r.top)/r.height,0,1)};}
 const fromPoints=(a,b)=>({x:Math.min(a.x,b.x),y:Math.min(a.y,b.y),w:Math.abs(a.x-b.x),h:Math.abs(a.y-b.y)});
 function down(e){
   if(state.preview||e.button!==0||!q('img').complete)return;
   e.preventDefault();area.focus({preventScroll:true});error('');
   const p=point(e),hit=e.target.closest('[data-mask-id]'),handle=e.target.dataset.maskHandle,before=snapshot();
   if(state.tool==='stamp'){
     if(!state.last){state.tool='draw';paint();return;}
     try{const {w,h}=state.last;addMask({x:clamp(p.x-w/2,0,1-w),y:clamp(p.y-h/2,0,1-h),w,h});changed(before);}catch(err){error(err.message);}return;
   }
   if(state.tool==='select'||handle){
     if(!hit){state.selected.clear();paint();return;}
     const id=hit.dataset.maskId;
     if(e.shiftKey){state.selected.has(id)?state.selected.delete(id):state.selected.add(id);paint();return;}
     if(!state.selected.has(id))state.selected=new Set([id]);
     state.gesture={type:handle?'resize':'move',handle,id,start:p,before};
   }else state.gesture={type:state.tool,start:p,before,temp:null};
   area.setPointerCapture(e.pointerId);paint();
 }
 function move(e){
   const g=state.gesture;if(!g)return;
   const p=point(e);
   if(g.type==='draw'||g.type==='table')g.temp=fromPoints(g.start,p);
   if(g.type==='move'){
     const chosen=g.before.filter(m=>state.selected.has(m.id));
     let dx=p.x-g.start.x,dy=p.y-g.start.y;
     dx=clamp(dx,-Math.min(...chosen.map(m=>m.x)),1-Math.max(...chosen.map(m=>m.x+m.w)));
     dy=clamp(dy,-Math.min(...chosen.map(m=>m.y)),1-Math.max(...chosen.map(m=>m.y+m.h)));
     state.masks=g.before.map(m=>state.selected.has(m.id)?{...m,x:m.x+dx,y:m.y+dy}:m);
   }
   if(g.type==='resize'){
     const original=g.before.find(m=>m.id===g.id),c=g.handle;
     const anchor={x:c.includes('w')?original.x+original.w:original.x,y:c.includes('n')?original.y+original.h:original.y};
     const box=fromPoints(anchor,p);
     if(box.w>=.0005&&box.h>=.0005){state.masks=g.before.map(m=>m.id===g.id?{...m,...box}:m);state.last={w:box.w,h:box.h};}
   }
   paint();
 }
 function up(e){
   const g=state.gesture;if(!g)return;move(e);state.gesture=null;
   try{
     if(g.type==='draw'||g.type==='table'){
       const rect=g.temp,r=area.getBoundingClientRect();
       if(!rect||rect.w*r.width<5||rect.h*r.height<5){paint();return;}
       if(g.type==='table'){state.region=rect;paint();return;}
       addMask(rect);
     }
     changed(g.before);
   }catch(err){state.masks=g.before;paint();error(err.message);}
 }
 function cancel(){if(state.gesture){state.masks=state.gesture.before;state.gesture=null;paint();}}
 function action(a){
   error('');const before=snapshot();
   if(['separate','same'].includes(a)){state.mode=a;state.preview=false;paint();return;}
   if(['draw','stamp','select','table','preview'].includes(a)){state.preview=a==='preview';if(!state.preview)state.tool=a;state.reveal=false;state.region=null;paint();return;}
   if(a==='next-group'){state.group=Math.min(500,next());state.mode='same';paint();return;}
   if(a==='undo'||a==='redo'){
     const source=a==='undo'?state.past:state.future,destination=a==='undo'?state.future:state.past;
     if(!source.length)return;destination.push(before);state.masks=source.pop();state.selected.clear();options.onChange?.(clone(state.masks),state.hide);paint();return;
   }
   if(a==='remove')state.masks=state.masks.filter(m=>!state.selected.has(m.id));
   if(a==='duplicate'){
     const selected=state.masks.filter(m=>state.selected.has(m.id));
     if(state.masks.length+selected.length>1000||(state.mode==='separate'&&next()+selected.length-1>500))throw Error('Duplicating this selection would exceed the image limits.');
     const ids=[];
     for(const m of selected){const fresh=addMask({x:clamp(m.x+.02,0,1-m.w),y:clamp(m.y+.02,0,1-m.h),w:m.w,h:m.h});ids.push(fresh.id);}
     state.selected=new Set(ids);
   }
   if(a==='group-selected')state.masks=state.masks.map(m=>state.selected.has(m.id)?{...m,group:state.group}:m);
   if(a==='apply-grid'){
     const made=grid(state.region,Number(q('[data-mask-field="rows"]').value),Number(q('[data-mask-field="cols"]').value),q('[data-mask-field="grid-group"]').value,state.mode==='same'?state.group:next());
     if(state.masks.length+made.length>1000)throw Error('This would exceed 1,000 masks. Use a smaller table.');
     state.masks.push(...made);state.region=null;state.tool='select';state.selected=new Set(made.map(m=>m.id));
   }
   if(a==='cancel-grid'){state.region=null;paint();return;}
   if(a==='flip'){state.reveal=!state.reveal;paint();return;}
   changed(before);
 }
 const click=e=>{const b=e.target.closest('[data-mask-action]');if(!b||b.disabled)return;e.preventDefault();e.stopPropagation();try{action(b.dataset.maskAction);}catch(err){error(err.message);}};
 const change=e=>{const key=e.target.dataset.maskField;if(key==='zoom'){area.style.maxWidth='none';area.style.width=e.target.value+'%';return;}if(key==='hide'){state.hide=e.target.checked;options.onChange?.(clone(state.masks),state.hide);}if(key==='group')state.group=Number(e.target.value);if(key==='preview-group'){state.previewGroup=Number(e.target.value);state.reveal=false;}paint();};
 const key=e=>{
   if(e.target!==area||state.preview||e.isComposing)return;
   const k=e.key.toLowerCase();
   if((e.ctrlKey||e.metaKey)&&['z','y','d'].includes(k)){e.preventDefault();try{action(k==='d'?'duplicate':k==='y'||e.shiftKey?'redo':'undo');}catch(err){error(err.message);}return;}
   if(['delete','backspace'].includes(k)){e.preventDefault();action('remove');return;}
   if(!['arrowleft','arrowright','arrowup','arrowdown'].includes(k)||!state.selected.size)return;
   e.preventDefault();const before=snapshot(),step=e.shiftKey?.01:.001;let dx=k==='arrowleft'?-step:k==='arrowright'?step:0,dy=k==='arrowup'?-step:k==='arrowdown'?step:0;
   const chosen=state.masks.filter(m=>state.selected.has(m.id));
   dx=clamp(dx,-Math.min(...chosen.map(m=>m.x)),1-Math.max(...chosen.map(m=>m.x+m.w)));dy=clamp(dy,-Math.min(...chosen.map(m=>m.y)),1-Math.max(...chosen.map(m=>m.y+m.h)));
   state.masks=state.masks.map(m=>state.selected.has(m.id)?{...m,x:m.x+dx,y:m.y+dy}:m);changed(before);
 };
 container.addEventListener('click',click);container.addEventListener('change',change);area.addEventListener('pointerdown',down);area.addEventListener('pointermove',move);area.addEventListener('pointerup',up);area.addEventListener('pointercancel',cancel);area.addEventListener('keydown',key);
 q('img').addEventListener('error',()=>error('This image could not load. Close the editor and reattach the original image. No cards were created.'),{once:true});
 paint();return {state,action,getValue:()=>({masks:clone(state.masks),hideOthers:state.hide}),dispose(){disposed=true;cancel();container.removeEventListener('click',click);container.removeEventListener('change',change);area.removeEventListener('pointerdown',down);area.removeEventListener('pointermove',move);area.removeEventListener('pointerup',up);area.removeEventListener('pointercancel',cancel);area.removeEventListener('keydown',key);}};
}
window.WorkshopMasks={mount,grid,groups};
})();
