/* Executes production helper/action functions; not a browser or native Anki test. */
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict'),path=require('path');
const app=fs.readFileSync(path.join(__dirname,'../addon/web/app.js'),'utf8');
const growth=app.slice(app.indexOf('  function readinessData('),app.indexOf('  function focusRows('));
const action=app.slice(app.indexOf('  async function action('),app.indexOf('  function handleField('));
let raw='1',renders=0;
const context={S:{draft:{scopes:[{deck_id:1,confidence:3,weight:2},{deck_id:2,confidence:4,weight:3}]}},
 root:{querySelector:()=>({value:raw})},markDirty:()=>{},renderDeckList:()=>{renders++;},toast:()=>{}};
vm.createContext(context);
vm.runInContext(growth+action+';this.fns={readinessData,action};',context);
(async()=>{
 let checks=0;
 const r={total:100,new:100,due:100,weight:1,confidence:3,recent_attempts:0,recent_misses:0};
 const get=overrides=>context.fns.readinessData({rows:[{...r,...overrides}]});
 assert.equal(get({due:100}).score,get({due:0}).score);checks++;
 assert.ok(get({new:0,recent_attempts:80,recent_misses:0}).score>get({}).score);checks++;
 assert.ok(get({new:0,recent_attempts:80,recent_misses:60}).score<get({new:0,recent_attempts:80,recent_misses:0}).score);checks++;
 assert.equal(get({new:0,confidence:5,recent_attempts:80,recent_misses:0}).stage,4);checks++;
 assert.equal(get({}).stage,1);checks++;
 await context.fns.action({dataset:{action:'apply-bulk',kind:'confidence'}});
 assert.ok(context.S.draft.scopes.every(s=>s.confidence===1));checks++;
 raw='7.5';await context.fns.action({dataset:{action:'apply-bulk',kind:'emphasis'}});
 assert.ok(context.S.draft.scopes.every(s=>s.weight===7.5));checks++;
 raw='0';await context.fns.action({dataset:{action:'apply-bulk',kind:'emphasis'}});
 assert.ok(context.S.draft.scopes.every(s=>s.weight===0));checks++;
 for(const value of ['','-1','1001','NaN']){
   raw=value;
   await assert.rejects(context.fns.action({dataset:{action:'apply-bulk',kind:'emphasis'}}));checks++;
 }
 raw='2.5';await assert.rejects(context.fns.action({dataset:{action:'apply-bulk',kind:'confidence'}}));checks++;
 assert.equal(renders,3);checks++;
 console.log(JSON.stringify({checks,passed:checks,scope:'Production helper/action functions in Node; not native Anki or DOM rendering.'}));
})().catch(e=>{console.error(e);process.exit(1);});
