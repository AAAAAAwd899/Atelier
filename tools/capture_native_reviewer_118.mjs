// Actual isolated Anki/Qt webviews, not a browser fixture. Local CDP only.
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const out=path.join(root,'output/onigiri-coexistence-118');
let info;for(let i=0;i<400;i++){try{info=JSON.parse(await fs.readFile(path.join(out,'cdp.json'),'utf8'));if(info.ready)break;}catch{}await new Promise(r=>setTimeout(r,300));}
if(!info.ready)throw new Error('Native example profile is not ready');
const targets=()=>fetch(`http://127.0.0.1:${info.port}/json/list`).then(r=>r.json());
async function connect(target){
 const socket=new WebSocket(target.webSocketDebuggerUrl);let id=0;const pending=new Map();
 await new Promise((ok,no)=>{socket.addEventListener('open',ok,{once:true});socket.addEventListener('error',no,{once:true});});
 socket.addEventListener('message',e=>{const r=JSON.parse(e.data);if(!r.id)return;const item=pending.get(r.id);if(!item)return;pending.delete(r.id);clearTimeout(item.timeout);r.error?item.no(new Error(JSON.stringify(r.error))):item.ok(r.result);});
 const call=(method,params={})=>new Promise((ok,no)=>{const key=++id;const timeout=setTimeout(()=>{pending.delete(key);no(new Error(method+' timed out'));},15000);pending.set(key,{ok,no,timeout});socket.send(JSON.stringify({id:key,method,params}));});
 const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 return {call,evaluate,close:()=>socket.close()};
}
let matches=[];for(let i=0;i<75;i++){matches=(await targets()).filter(t=>t.title==='main webview');if(matches.length===1)break;await new Promise(r=>setTimeout(r,200));}
if(matches.length!==1)throw new Error('Expected one actual native main webview after startup settled');
const page=await connect(matches[0]);await page.call('Page.enable');

const tb=(await targets()).find(t=>t.title==='top toolbar');if(!tb)throw new Error('Native top toolbar missing');
const toolbar=await connect(tb);await toolbar.call('Page.enable');
const labels=await toolbar.evaluate("['decks','add','browse','stats','sync'].map(name=>{const b=[...document.querySelectorAll('a,button')].find(e=>e.textContent.trim().toLowerCase()===name);const r=b?.getBoundingClientRect();return {name,hit:Boolean(r&&r.width>0&&r.height>0&&r.bottom<=innerHeight+1&&b.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)))};})");
if(labels.some(x=>!x.hit))throw new Error('Native toolbar hit test failed '+JSON.stringify(labels));
const body=await page.evaluate('document.getElementById("qa")?.textContent||""');if(!body.includes('Synthetic companion question'))throw new Error('Expected the actual native question');
for(const [name,c] of [['reviewer-question.png',page],['reviewer-toolbar.png',toolbar]]){await c.evaluate('document.fonts.ready.then(()=>true)');const shot=await c.call('Page.captureScreenshot',{format:'png',fromSurface:true});await fs.writeFile(path.join(out,name),Buffer.from(shot.data,'base64'));}
await fs.writeFile(path.join(out,'reviewer-capture.json'),JSON.stringify({category:'actual installed Anki 26.09.3 Qt offscreen native reviewer and toolbar webviews; synthetic card; no physical-display claim',labels},null,2));
await fs.writeFile(path.join(out,'captured-question.flag'),'');page.close();toolbar.close();console.log('Actual reviewer and all five native toolbar hit areas captured');
