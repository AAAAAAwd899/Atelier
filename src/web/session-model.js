/* Read-only result presentation. Uses recorded points/percent; never grades or schedules. */
(function(global){'use strict';
 const finite=v=>typeof v==='number'&&Number.isFinite(v);
 const filters=Object.freeze([
  {id:'all',label:'All questions'}, {id:'review',label:'Needs review'},
  {id:'confident',label:'Confident misses'}, {id:'flagged',label:'Flagged'},
  {id:'ungraded',label:'Not graded'}
 ].map(Object.freeze));
 function inspect(result){
  const items=Array.isArray(result.items)?result.items:[],flags=new Set(result.flagged_ids||[]);
  const rows=items.map((item,index)=>{
   const grade=[0,.5,1].includes(item.grade)?item.grade:null;
   const status=item.render_error?'Render failure':grade===1?'Correct':grade===.5?'Partly right':grade===0?'Missed':item.attempted===false?'Unanswered':'Not graded';
   return Object.freeze({number:index+1,cardId:String(item.card_id),deckId:String(item.deck_id),grade,status,
    flagged:flags.has(item.card_id),confident:item.confidence===3&&grade!==null&&grade<1,
    confidence:['Not recorded','Guessing','Unsure','Confident'][item.confidence]||'Not recorded',
    error:typeof item.error_type==='string'&&item.error_type!=='none'?item.error_type:'',
    seconds:finite(item.seconds)&&item.seconds>=0?item.seconds:null,
    scheduled:item.scheduled===true,renderError:item.render_error===true,
    needsReview:grade===null||grade<1});
  });
  const scheduled=rows.filter(r=>r.scheduled).length;
  return Object.freeze({rows:Object.freeze(rows),confident:rows.filter(r=>r.confident).length,
   scheduled,hasItemDetail:Array.isArray(result.items),
   label:result.pip_study?'Pip Study':result.kind==='exam'?'Mock exam':'Focus practice',
   scheduleLabel:!Array.isArray(result.items)?'Scheduling detail is not available for this older result':scheduled?`${scheduled} new card${scheduled===1?'':'s'} received an explicit Anki rating`:'No Anki scheduling writes recorded in this session',
   partial:result.interrupted===true,targeted:result.sampling==='adaptive',
   percent:finite(result.percent)?result.percent:null,
   total:finite(result.total)?result.total:0,points:finite(result.points)?result.points:0});
 }
 function page(result,filter='all',index=0,size=25){
  if(!filters.some(f=>f.id===filter))throw new Error('Unknown result filter');
  if(!Number.isInteger(index)||index<0||!Number.isInteger(size)||size<1||size>50)throw new Error('Invalid result page');
  const data=inspect(result),rows=data.rows.filter(r=>filter==='all'||filter==='review'&&r.needsReview||filter==='confident'&&r.confident||filter==='flagged'&&r.flagged||filter==='ungraded'&&r.grade===null);
  const pages=Math.max(1,Math.ceil(rows.length/size));index=Math.min(index,pages-1);
  return {rows:rows.slice(index*size,(index+1)*size),total:rows.length,page:index,pages,
   from:rows.length?index*size+1:0,to:Math.min((index+1)*size,rows.length)};
 }
 const api=Object.freeze({filters,inspect,page});
 if(typeof module==='object'&&module.exports)module.exports=api;
 if(global)global.AtelierSessionModel=api;
})(typeof window!=='undefined'?window:null);
