// Actual isolated Anki/Qt webviews, not a browser fixture. Local CDP only.
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const out=path.join(root,'output/listing-native-117-onigiri');
let info;for(let i=0;i<200;i++){try{info=JSON.parse(await fs.readFile(path.join(out,'cdp.json'),'utf8'));if(info.ready)break;}catch{}await new Promise(r=>setTimeout(r,300));}
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

const pause=ms=>new Promise(r=>setTimeout(r,ms));
for(let i=0;i<75;i++){if(await page.evaluate('window.AtelierMakeover?.diagnostics().loaded'))break;await pause(200);}
await page.evaluate('document.querySelector("#onigiri-welcome-overlay .btn-continue")?.click()');
await page.evaluate('document.getElementById("atelier-root").shadowRoot.querySelector("[data-action=close-dialog]")?.click()');
await page.evaluate('document.getElementById("atelier-root").shadowRoot.querySelector(".nav-row[data-action=home]")?.click()');
await pause(400);
await page.evaluate('document.getElementById("atelier-root").shadowRoot.querySelector("[data-action=tour-skip]")?.click()');
await page.evaluate('(()=>{const s=document.getElementById("atelier-root").shadowRoot;if(!s.querySelector(".onigiri-inline.is-expanded"))s.querySelector("[data-action=onigiri-toggle]")?.click()})()');await pause(1200);
await page.evaluate('document.getElementById("atelier-root").shadowRoot.querySelector(".onigiri-inline")?.scrollIntoView({block:"start"})');await pause(500);
await page.evaluate('document.getElementById("atelier-root").shadowRoot.querySelector("[data-command=check_updates]").click()');await pause(700);await fs.writeFile(path.join(out,'verify-updates.flag'),'');
const data=await page.evaluate(`(()=>{const n=document.querySelector('[data-atelier-inline-rewards]');return {exists:!!n,grids:[...n.querySelectorAll('.unified-grid')].map(g=>({height:g.getBoundingClientRect().height,cols:getComputedStyle(g).gridTemplateColumns,items:[...g.children].filter(x=>x instanceof HTMLElement).map(x=>({role:x.dataset.atelierInlineItem,classes:x.className,height:x.getBoundingClientRect().height,text:x.textContent.trim().slice(0,85)}))})),restaurant:!!n.querySelector('.onigiri-restaurant-level-widget'),images:[...n.querySelectorAll('img')].map(i=>({width:i.naturalWidth,loaded:i.complete}))}})()`);
await fs.writeFile(path.join(out,'restaurant-layout.json'),JSON.stringify(data,null,2));
const shot=await page.call('Page.captureScreenshot',{format:'png',fromSurface:true});await fs.writeFile(path.join(out,'restaurant-layout.png'),Buffer.from(shot.data,'base64'));const r=await page.evaluate(`(()=>{const n=document.querySelector('.onigiri-restaurant-level-widget');const r=n.getBoundingClientRect(),h=n.querySelector('.rl-widget-head').getBoundingClientRect(),b=n.querySelector('.rl-widget-body').getBoundingClientRect();return {width:r.width,height:r.height,bodyWidth:b.width,bodyUnderHeader:b.top>=h.bottom-1,overflow:document.documentElement.scrollWidth>innerWidth}})()`);if(!r.bodyUnderHeader||r.width<300||r.overflow)throw new Error('Restaurant layout failed '+JSON.stringify(r));
await fs.writeFile(path.join(out,'layout-check.json'),JSON.stringify(r,null,2));
const ts=await targets();const toolbar=ts.find(t=>/toolbar/i.test(t.title)&&!/bottom/i.test(t.title));if(toolbar){const c=await connect(toolbar);const v=await c.evaluate('({title:document.title,labels:[...document.querySelectorAll("a,button")].map(x=>x.textContent.trim())})');await fs.writeFile(path.join(out,'toolbar-labels.json'),JSON.stringify(v,null,2));const shot=await c.call('Page.captureScreenshot',{format:'png',fromSurface:true});await fs.writeFile(path.join(out,'native-toolbar.png'),Buffer.from(shot.data,'base64'));c.close();}
await page.evaluate(`(()=>{const s=document.getElementById('atelier-root').shadowRoot;const m=s.querySelector('[data-action=mobile]');if(m&&m.getBoundingClientRect().width&&getComputedStyle(m).display!=='none')m.click();s.querySelector('.nav-row[data-page=library]').click()})()`);await pause(500);
await page.evaluate(`document.getElementById('atelier-root').shadowRoot.querySelector('[data-action=view][data-view=outline]').click()`);await pause(400);
await page.evaluate(`document.getElementById('atelier-root').shadowRoot.querySelector('.outline-row[data-node="${info.parent}"] [data-action=organize]').click()`);await pause(400);
await page.evaluate(`(()=>{const b=document.getElementById('atelier-root').shadowRoot.querySelector('[data-action=folder-icon][data-icon=fox]');b.scrollIntoView({block:'center'});b.click()})()`);
for(let i=0;i<50;i++){if(await page.evaluate(`document.getElementById('atelier-root').shadowRoot.querySelector('[data-icon=fox]')?.getAttribute('aria-pressed')==='true'`))break;await pause(200);}
const cute=await page.evaluate(`(()=>{const h=document.getElementById('atelier-root'),s=h.shadowRoot;return {decoded:h.dataset.folderCuteExtraArt,selected:s.querySelector('[data-icon=fox]')?.getAttribute('aria-pressed'),art:s.querySelector('.personalization-art .folder-symbol')?.dataset.folderSymbol,choices:s.querySelectorAll('[data-action=folder-icon]').length}})()`);if(cute.decoded!=='ready'||cute.selected!=='true'||cute.art!=='fox'||cute.choices!==37)throw new Error('Native cute icon UI failed '+JSON.stringify(cute));
const cs=await page.call('Page.captureScreenshot',{format:'png',fromSurface:true});await fs.writeFile(path.join(out,'cute-folder-native.png'),Buffer.from(cs.data,'base64'));await fs.writeFile(path.join(out,'verify-cute.flag'),'');await pause(800);
console.log(JSON.stringify({layout:r,cute,targets:ts.map(t=>t.title)}));page.close();await fs.writeFile(path.join(out,'stop.flag'),'');
