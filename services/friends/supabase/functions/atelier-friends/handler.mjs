// Shared by the deployed Deno adapter and Node tests. No client service keys.
const UUID=/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
const OPS=new Set(['home','profile','invite_create','invite_preview','invite_accept','friend_remove','course_create','course_update','snapshot_begin','snapshot_cancel','course_revoke']);
const MAX=41943040;
class SafeError extends Error{constructor(message,status=400){super(message);this.status=status;}}
function json(data,status=200){return new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json','cache-control':'no-store','referrer-policy':'no-referrer','x-content-type-options':'nosniff'}});}
function id(value){if(typeof value!=='string'||!UUID.test(value))throw new SafeError('Choose a valid shared course.');return value;}
function safeMessage(value){const text=String(value||'');return /^(Private membership|Please wait|Your |Choose |Use a name|That invite|That course|That upload|That shared|That unfinished|This course|This package|A friend list|A newer version|The private service|Private storage)/.test(text)&&text.length<180?text:'Friends could not complete that request. Please try again.';}
async function limitedJson(req){const n=Number(req.headers.get('content-length'));if(n>32768)throw new SafeError('That request is too large.',413);if(!req.body)return{};const reader=req.body.getReader();let bytes=0;const chunks=[];for(;;){const r=await reader.read();if(r.done)break;bytes+=r.value.byteLength;if(bytes>32768){await reader.cancel();throw new SafeError('That request is too large.',413);}chunks.push(r.value);}const all=new Uint8Array(bytes);let p=0;for(const c of chunks){all.set(c,p);p+=c.length;}try{const x=JSON.parse(new TextDecoder().decode(all));if(!x||typeof x!=='object'||Array.isArray(x))throw 0;return x;}catch{throw new SafeError('Check the information and try again.');}}
function measured(body,expected,createHash,signal,expectedHash=null,requireZip=false){
 if(!body)throw new SafeError('The package is empty.');let count=0;const hash=createHash();const prefix=[];let finish,fail;const done=new Promise((ok,no)=>{finish=ok;fail=no;});done.catch(()=>{});signal.addEventListener('abort',()=>fail(new SafeError('The transfer timed out. Please try again.',408)),{once:true});
 const stream=body.pipeThrough(new TransformStream({transform(chunk,controller){if(!(chunk instanceof Uint8Array)){const e=new SafeError('Invalid package bytes.');fail(e);throw e;}count+=chunk.byteLength;if(count>expected||count>MAX){const e=new SafeError('The package size did not match.',413);fail(e);throw e;}for(const x of chunk){if(prefix.length>=4)break;prefix.push(x);}if(requireZip&&prefix.length===4&&!(prefix[0]===80&&prefix[1]===75&&prefix[2]===3&&prefix[3]===4)){const e=new SafeError('Choose an Anki deck package.');fail(e);throw e;}hash.update(chunk);controller.enqueue(chunk);},flush(){const digest=Array.from(hash.digest(),x=>x.toString(16).padStart(2,'0')).join('');if(count!==expected||(expectedHash&&digest!==expectedHash)){const e=new SafeError('The package integrity check failed.');fail(e);throw e;}finish({bytes:count,sha256:digest});}}));return{stream,done};
}
export function createHandler({url,publicKey,serviceKey,createHash,fetcher=fetch,timeoutMs=120000,allowedOrigin=''}){
 const base=new URL(url);if(base.protocol!=='https:'||base.username||base.password||base.search||base.hash)throw new Error('Use a trusted HTTPS Supabase origin.');const origin=base.origin;
 if(!publicKey||!serviceKey||!createHash)throw new Error('Server configuration is incomplete.');
 const headers=(token,key=publicKey)=>({'apikey':key,'authorization':'Bearer '+token});
 async function callRpc(name,args,token,service=false){const res=await fetcher(origin+'/rest/v1/rpc/'+name,{method:'POST',headers:{...headers(token,service?serviceKey:publicKey),'content-type':'application/json'},body:JSON.stringify(args),redirect:'error',signal:AbortSignal.timeout(20000)});if(!res.ok){let e={};try{e=await res.json();}catch{}throw new SafeError(safeMessage(e.message),res.status===401?401:res.status===403?403:400);}if(res.status===204)return null;const text=await res.text();return text?JSON.parse(text):null;}
 async function rpc(op,payload,token){const result=await callRpc('atelier_friends',{op,payload},token);if(result?.error)throw new SafeError(safeMessage(result.error),[400,403,429].includes(result.status)?result.status:400);return result;}
 async function storage(path,options={}){if(!/^[a-f0-9-]{36}\/[a-f0-9-]{36}\.apkg$/i.test(path))throw new SafeError('The package location is invalid.');return fetcher(origin+'/storage/v1/object/atelier-friends/'+path,{...options,headers:{...headers(serviceKey,serviceKey),...(options.headers||{})},redirect:'error'});}
 async function cleanup(){const rows=await callRpc('atelier_cleanup_candidates',{},serviceKey,true);for(const row of rows||[]){const res=await storage(row.path,{method:'DELETE',signal:AbortSignal.timeout(10000)});if(res.ok||res.status===404)await callRpc('atelier_confirm_cleanup',{p_id:row.id},serviceKey,true);}}
 return async function handle(req){
  try{
   const requestOrigin=req.headers.get('origin');if(requestOrigin&&requestOrigin!==allowedOrigin)throw new SafeError('This client origin is not allowed.',403);
   const path=new URL(req.url).pathname.replace(/\/$/,'');const root='/functions/v1/atelier-friends';if(![root,root+'/upload',root+'/download'].includes(path))throw new SafeError('Not found.',404);
   if(!['POST','PUT','GET'].includes(req.method))throw new SafeError('That method is not available.',405);
   const auth=req.headers.get('authorization')||'';if(!/^Bearer [^\s]{20,8192}$/.test(auth))throw new SafeError('Sign in to Friends first.',401);const token=auth.slice(7);
   const who=await fetcher(origin+'/auth/v1/user',{headers:headers(token),redirect:'error',signal:AbortSignal.timeout(15000)});if(!who.ok)throw new SafeError('Sign in to Friends again.',401);const user=await who.json();id(user.id);
   if(path===root&&req.method==='POST'){
    const data=await limitedJson(req);if(!OPS.has(data.op))throw new SafeError('That Friends action is not available.');const result=await rpc(data.op,data.payload||{},token);
    if(['course_revoke','snapshot_cancel'].includes(data.op)){try{await cleanup();}catch{/* Quota stays reserved until a later safe cleanup; never claim deletion. */}}
    return json(result);
   }
   const share=id(new URL(req.url).searchParams.get('id'));
   if(path===root+'/upload'&&req.method==='PUT'){
    const length=Number(req.headers.get('content-length'));if(!Number.isSafeInteger(length)||length<1||length>MAX)throw new SafeError('Choose a package no larger than 40 MiB.',413);
    const ticket=await rpc('upload_ticket',{id:share},token);if(ticket.owner_id!==user.id||ticket.bytes!==length)throw new SafeError('The package size did not match.');
    const signal=AbortSignal.timeout(timeoutMs);const transfer=measured(req.body,length,createHash,signal,ticket.sha256,true);
    try{
     const result=await storage(ticket.path,{method:'POST',headers:{'content-type':'application/octet-stream','content-length':String(length),'x-upsert':'false'},body:transfer.stream,duplex:'half',signal});
     if(!result.ok)throw new SafeError('This package could not be uploaded. Retry or cancel the unfinished upload.',502);
     const actual=await transfer.done;const out=await callRpc('atelier_finish_upload',{p_owner:user.id,p_id:share,p_lease:ticket.lease,p_bytes:actual.bytes,p_sha256:actual.sha256},serviceKey,true);
     try{await cleanup();}catch{}return json(out);
    }catch(error){try{await storage(ticket.path,{method:'DELETE',signal:AbortSignal.timeout(10000)});}catch{}throw error;}
   }
   if(path===root+'/download'&&req.method==='GET'){
    const ticket=await rpc('download_ticket',{id:share},token);const signal=AbortSignal.timeout(timeoutMs);const res=await storage(ticket.path,{method:'GET',signal});if(!res.ok)throw new SafeError('This shared version could not be downloaded.',502);
    const transfer=measured(res.body,ticket.bytes,createHash,signal,ticket.sha256,true);
    return new Response(transfer.stream,{headers:{'content-type':'application/octet-stream','content-length':String(ticket.bytes),'x-atelier-sha256':ticket.sha256,'content-disposition':'attachment; filename="Atelier-'+share+'.apkg"','cache-control':'no-store','referrer-policy':'no-referrer','x-content-type-options':'nosniff'}});
   }
   throw new SafeError('That method is not available.',405);
  }catch(error){return json({error:error instanceof SafeError?error.message:'Friends could not complete the request. Your local decks are unchanged.'},error instanceof SafeError?error.status:502);}
 };
}
