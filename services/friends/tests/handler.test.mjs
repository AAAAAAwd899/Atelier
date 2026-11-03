import {test} from 'node:test';
import assert from 'node:assert/strict';
import {sha256} from '@noble/hashes/sha2.js';
import {createHandler} from '../supabase/functions/atelier-friends/handler.mjs';
const A='11111111-1111-4111-8111-111111111111',S='55555555-5555-4555-8555-555555555555';
const bytes=Uint8Array.from([80,75,3,4,11,22,33,44]),digest=b=>Buffer.from(sha256(b)).toString('hex');
const userToken='a'.repeat(40),service='server-only-secret',pub='public-key';
function setup(options={}){
 const calls=[];let uploaded=null;
 const ticket={owner_id:A,path:A+'/'+S+'.apkg',bytes:bytes.length,sha256:digest(bytes),lease:S,...options.ticket};
 const fetcher=async(url,o={})=>{calls.push({url,o});assert.equal(o.redirect,'error');const path=new URL(url).pathname;
  if(path==='/auth/v1/user')return Response.json({id:A},{status:options.authStatus||200});
  if(path.startsWith('/rest/v1/rpc/')){const args=JSON.parse(o.body);if(path.endsWith('/atelier_friends')){assert.equal(o.headers.authorization,'Bearer '+userToken);if(options.rpcError)return Response.json({error:'Private membership is required.',status:403});if(args.op==='upload_ticket'||args.op==='download_ticket')return Response.json(ticket);return Response.json({friends:[]});}
   assert.equal(o.headers.authorization,'Bearer '+service);if(path.endsWith('atelier_finish_upload')){assert.equal(args.p_bytes,bytes.length);assert.equal(args.p_sha256,digest(bytes));return Response.json({published:true,version:1});}return Response.json([]);}
  if(path.startsWith('/storage/v1/object/')){assert.equal(o.headers.apikey,service);if(o.method==='POST'){assert.equal(o.headers['x-upsert'],'false');uploaded=new Uint8Array(await new Response(o.body).arrayBuffer());return new Response('',{status:options.uploadStatus||200});}if(o.method==='DELETE')return new Response('');return new Response(options.downloadBytes||bytes);}
  throw new Error('Unexpected request');
 };
 const handler=createHandler({url:'https://private.example',publicKey:pub,serviceKey:service,createHash:()=>sha256.create(),fetcher,timeoutMs:1000});
 const request=(path='',o={})=>new Request('https://edge.example/functions/v1/atelier-friends'+path,{method:'POST',headers:{authorization:'Bearer '+userToken,...o.headers},...o,duplex:'half'});
 return {handler,request,calls,get uploaded(){return uploaded;}};
}
test('auth is verified before metadata or private Storage',async()=>{const t=setup({authStatus:401});const r=await t.handler(t.request('',{body:JSON.stringify({op:'home'})}));assert.equal(r.status,401);assert.equal(t.calls.length,1);assert.equal(t.calls[0].o.headers.apikey,pub);});
test('foreign origins and missing tokens are rejected before any upstream request',async()=>{for(const headers of [{origin:'https://attacker.example',authorization:'Bearer '+userToken},{authorization:''}]){const t=setup();const r=await t.handler(t.request('',{headers}));assert.ok([401,403].includes(r.status));assert.equal(t.calls.length,0);}});
test('metadata allowlist and request bytes are bounded',async()=>{for(const body of [JSON.stringify({op:'upload_ticket'}),' '.repeat(32769)]){const t=setup();const r=await t.handler(t.request('',{body}));assert.ok([400,413].includes(r.status));assert.equal(t.calls.length,1);}});
test('only current authorized owners can start private Storage upload',async()=>{const t=setup({ticket:{owner_id:S}});const r=await t.handler(t.request('/upload?id='+S,{method:'PUT',headers:{authorization:'Bearer '+userToken,'content-length':String(bytes.length)},body:bytes}));assert.equal(r.status,400);assert.equal(t.calls.filter(x=>x.url.includes('/storage/')).length,0);});
test('a matching stream is stored once and service-verified before publishing',async()=>{const t=setup();const r=await t.handler(t.request('/upload?id='+S,{method:'PUT',headers:{authorization:'Bearer '+userToken,'content-length':String(bytes.length)},body:bytes}));assert.equal(r.status,200);assert.deepEqual(await r.json(),{published:true,version:1});assert.deepEqual(t.uploaded,bytes);assert.equal(t.calls.filter(x=>x.url.endsWith('atelier_finish_upload')).length,1);});
test('wrong digest, non-ZIP and truncated uploads never publish',async()=>{for(const body of [Uint8Array.from([80,75,3,4,99,22,33,44]),new Uint8Array(8),bytes.slice(0,6)]){const t=setup();const r=await t.handler(t.request('/upload?id='+S,{method:'PUT',headers:{authorization:'Bearer '+userToken,'content-length':String(bytes.length)},body}));assert.notEqual(r.status,200);assert.equal(t.calls.filter(x=>x.url.endsWith('atelier_finish_upload')).length,0);assert.ok(t.calls.some(x=>x.o.method==='DELETE'));}});
test('oversized upload is rejected before a ticket or storage acquisition',async()=>{const t=setup();const r=await t.handler(t.request('/upload?id='+S,{method:'PUT',headers:{authorization:'Bearer '+userToken,'content-length':'41943041'},body:bytes}));assert.equal(r.status,413);assert.equal(t.calls.length,1);});
test('nonmembers never obtain package bytes',async()=>{const t=setup({rpcError:true});const r=await t.handler(t.request('/download?id='+S,{method:'GET'}));assert.equal(r.status,403);assert.equal(t.calls.filter(x=>x.url.includes('/storage/')).length,0);});
test('download is streamed with exact hash/size and no public cache',async()=>{const t=setup();const r=await t.handler(t.request('/download?id='+S,{method:'GET'}));assert.equal(r.status,200);assert.equal(r.headers.get('cache-control'),'no-store');assert.equal(r.headers.get('x-atelier-sha256'),digest(bytes));assert.deepEqual(new Uint8Array(await r.arrayBuffer()),bytes);});
test('corrupt or truncated Storage downloads fail their body integrity check',async()=>{for(const downloadBytes of [bytes.slice(0,5),Uint8Array.from([80,75,3,4,0,0,0,0])]){const t=setup({downloadBytes});const r=await t.handler(t.request('/download?id='+S,{method:'GET'}));await assert.rejects(r.arrayBuffer(),/integrity/);}});
test('Storage failure cannot mark a package ready or leak credentials in errors',async()=>{const t=setup({uploadStatus:500});const r=await t.handler(t.request('/upload?id='+S,{method:'PUT',headers:{authorization:'Bearer '+userToken,'content-length':String(bytes.length)},body:bytes}));const body=await r.text();assert.equal(r.status,502);assert.ok(!body.includes(service));assert.equal(t.calls.filter(x=>x.url.endsWith('atelier_finish_upload')).length,0);});
