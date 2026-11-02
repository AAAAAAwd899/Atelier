// Actual isolated Anki/Qt webviews, not a browser fixture. Local CDP only.
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const out=path.join(root,'output/listing-native-109');
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

const dest=path.join(root,'screenshots/native-navigation-109');await fs.mkdir(dest,{recursive:true});
const receipt={category:'actual installed Anki 26.09.3 Qt webviews; native outer chrome excluded',example_profile:true,owner_profile_accessed:false,images:[]};
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function wait(client,expr){for(let i=0;i<75;i++){if(await client.evaluate(expr))return;await pause(200);}throw new Error('Native view not ready: '+expr);}
async function capture(name,client){await client.evaluate('document.fonts.ready.then(()=>true)');await pause(500);const r=await client.call('Page.captureScreenshot',{format:'png',fromSurface:true});await fs.writeFile(path.join(dest,name),Buffer.from(r.data,'base64'));receipt.images.push({file:name,viewport:await client.evaluate('({width:innerWidth,height:innerHeight})')});console.log('Captured '+name);}
async function click(client,selector,shadow=false){const expr=(shadow?'document.getElementById("atelier-root").shadowRoot':'document')+'.querySelector('+JSON.stringify(selector)+')';await wait(client,`Boolean(${expr})`);await client.evaluate(`(()=>{const b=${expr};if(b.disabled)throw new Error('Control disabled');b.click();return true})()`);}
async function findView(selector){for(let n=0;n<75;n++){for(const t of await targets()){const c=await connect(t);if(await c.evaluate('Boolean(document.querySelector('+JSON.stringify(selector)+'))'))return c;c.close();}await pause(200);}throw new Error('Native view missing '+selector);}
await wait(page,'window.AtelierMakeover?.diagnostics().loaded');
await capture('01-study-desk.png',page);
await click(page,'.decks-top',true);await click(page,'[data-view="outline"]',true);
await click(page,'.outline-row[data-node="'+info.move_target+'"] [data-action="expand"]',true);
await capture('02-folder-tree.png',page);
await click(page,'.outline-row[data-node="'+info.move_target+'"] [data-action="organize"]',true);
await click(page,'[data-action="folder-icon"][data-icon="pills"]',true);
await wait(page,`document.getElementById("atelier-root").shadowRoot.querySelector('[data-icon="pills"]')?.getAttribute("aria-pressed")==="true"`);
await capture('03-folder-icons.png',page);
await click(page,'.dialog-header [data-action="close-dialog"]',true);
await wait(page,`Boolean(document.getElementById('atelier-root').shadowRoot.querySelector('.outline-row[data-node="'+${JSON.stringify(info.move_target)}+'"] .custom-folder-icon'))`);
await capture('04-personalized-library.png',page);
await click(page,'.header-utilities [data-action="appearance"]',true);
const geometry=()=>page.evaluate(`(()=>{const r=document.getElementById('atelier-root').shadowRoot;return [...r.querySelectorAll('.theme-tile')].map(e=>[e.offsetLeft,e.offsetTop,e.offsetWidth,e.offsetHeight])})()`);
const original=JSON.stringify(await geometry());receipt.theme_geometry=[];
for(const id of ['rose','forest','castle','obsidian']){
 await click(page,'[data-theme-choice="'+id+'"]',true);
 await wait(page,`window.AtelierMakeover.diagnostics().theme===${JSON.stringify(id)}&&window.AtelierMakeover.diagnostics().pendingSettings===0`);
 const same=JSON.stringify(await geometry())===original;receipt.theme_geometry.push({theme:id,unchanged:same});if(!same)throw new Error('Native theme chooser moved: '+id);
}
await capture('05-stable-worlds.png',page);
await click(page,'.dialog-header [data-action="close-dialog"]',true);
await fs.writeFile(path.join(out,'verify-icons.flag'),'verify');
for(let i=0;i<75;i++){try{const r=JSON.parse(await fs.readFile(path.join(out,'icons-verified.json'),'utf8'));if(!Object.values(r.checks).every(Boolean))throw new Error('Native icon check failed');receipt.native_icons=r;break;}catch(e){if(i===74)throw e;await pause(200);}}
receipt.action_bar=await page.evaluate(`(()=>{const r=document.getElementById('atelier-root').shadowRoot;return [...r.querySelectorAll('.anki-commandbar button')].map(e=>({label:e.textContent.trim(),visible:e.getBoundingClientRect().height>0}))})()`);
if(receipt.action_bar.length!==6||!receipt.action_bar.every(x=>x.visible))throw new Error('Missing native action');
await fs.writeFile(path.join(out,'capture-receipt.json'),JSON.stringify(receipt,null,2)+'\n');
await fs.writeFile(path.join(out,'stop.flag'),'stop');page.close();
