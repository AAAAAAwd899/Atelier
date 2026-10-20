// Actual isolated Anki/Qt webviews, not a browser fixture. Local CDP only.
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const out=path.join(root,'output/listing-native-106');
const info=JSON.parse(await fs.readFile(path.join(out,'cdp.json'),'utf8'));
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
const list=await targets();const matches=list.filter(t=>t.title==='main webview');
if(matches.length!==1)throw new Error('Expected one actual native main webview');
const page=await connect(matches[0]);await page.call('Page.enable');

const dest=path.join(root,'listing/ankiweb-1.0.6/screenshots');await fs.mkdir(dest,{recursive:true});
const receipt={category:'actual installed Anki 26.09.3 Qt webviews; native outer chrome excluded',example_profile:true,owner_profile_accessed:false,images:[]};
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function wait(client,expr){for(let i=0;i<75;i++){if(await client.evaluate(expr))return;await pause(200);}throw new Error('Native view not ready: '+expr);}
async function capture(name,client){await client.evaluate('document.fonts.ready.then(()=>true)');await pause(500);const r=await client.call('Page.captureScreenshot',{format:'png',fromSurface:true});await fs.writeFile(path.join(dest,name),Buffer.from(r.data,'base64'));receipt.images.push({file:name,viewport:await client.evaluate('({width:innerWidth,height:innerHeight})')});console.log('Captured '+name);}
async function click(client,selector,shadow=false){const expr=(shadow?'document.getElementById("atelier-root").shadowRoot':'document')+'.querySelector('+JSON.stringify(selector)+')';await wait(client,`Boolean(${expr})`);await client.evaluate(`(()=>{const b=${expr};if(b.disabled)throw new Error('Control disabled');b.click();return true})()`);}
async function findView(selector){for(let n=0;n<75;n++){for(const t of await targets()){const c=await connect(t);if(await c.evaluate('Boolean(document.querySelector('+JSON.stringify(selector)+'))'))return c;c.close();}await pause(200);}throw new Error('Native view missing '+selector);}

const cards=await findView('#workshop');
await click(page,'[data-action="new-study"]',true);
await wait(page,'Boolean(document.getElementById("atelier-root").shadowRoot.querySelector("#study-name"))');
await page.evaluate('(()=>{const r=document.getElementById("atelier-root").shadowRoot;const n=r.querySelector("#study-name");n.value="Biology & Chemistry · Final";n.dispatchEvent(new Event("input",{bubbles:true}));const d=r.querySelector("#study-date");d.value="2026-11-06";d.dispatchEvent(new Event("input",{bubbles:true}));for(const title of ["Biology 101","Chemistry 101"]){const row=Array.from(r.querySelectorAll(".picker-row")).find(e=>e.querySelector("strong")?.textContent===title);const cb=row.querySelector("input");if(!cb.checked)cb.click();}return true})()');
await wait(page,'document.getElementById("atelier-root").shadowRoot.querySelectorAll(".picker-row input:checked").length===2');
await capture('06-combine-folders.png',page);
await fs.writeFile(path.join(out,'capture-scope.json'),JSON.stringify(receipt,null,2)+'\n');cards.close();page.close();
