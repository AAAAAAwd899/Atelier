-- Dedicated Supabase project; no anonymous signup or public Storage bucket.
-- The client never receives a service-role key. RLS denies raw table/object access.
create table public.atelier_members(uid uuid primary key references auth.users(id) on delete cascade, display_name text not null check(length(display_name) between 1 and 60), active boolean not null default true);
create table public.atelier_friendships(a uuid references public.atelier_members(uid), b uuid references public.atelier_members(uid), created_at timestamptz not null default now(), primary key(a,b), check(a<b));
create table public.atelier_invites(id uuid primary key default gen_random_uuid(), owner_id uuid not null references public.atelier_members(uid), token_hash text not null unique, expires_at timestamptz not null default now()+interval '7 days', used_by uuid references public.atelier_members(uid), created_at timestamptz not null default now());
create table public.atelier_courses(id uuid primary key default gen_random_uuid(), owner_id uuid not null references public.atelier_members(uid), title text not null check(length(title) between 1 and 100), recipients uuid[] not null, enabled boolean not null default true, version integer not null default 0, latest_id uuid, created_at timestamptz not null default now(), updated_at timestamptz not null default now());
create table public.atelier_snapshots(id uuid primary key default gen_random_uuid(), course_id uuid not null references public.atelier_courses(id), owner_id uuid not null references public.atelier_members(uid), version integer not null, object_path text not null unique, bytes bigint not null check(bytes between 512 and 41943040), sha256 text not null check(sha256 ~ '^[a-f0-9]{64}$'), state text not null default 'pending' check(state in ('pending','uploading','ready','revoked')), lease uuid, lease_until timestamptz, created_at timestamptz not null default now());
create unique index atelier_live_version on public.atelier_snapshots(course_id,version) where state<>'revoked';
create table public.atelier_usage(id boolean primary key default true check(id), reserved_bytes bigint not null default 0, month date not null default date_trunc('month',now() at time zone 'UTC')::date, egress_bytes bigint not null default 0, ingress_bytes bigint not null default 0);
insert into public.atelier_usage(id) values(true);
create table public.atelier_rates(uid uuid references public.atelier_members(uid), minute timestamptz not null, hits integer not null, primary key(uid,minute));
create index on public.atelier_courses(owner_id,updated_at desc);
create index on public.atelier_snapshots(owner_id,created_at desc);
create index on public.atelier_invites(owner_id,created_at desc);
do $$declare t text;begin foreach t in array array['atelier_members','atelier_friendships','atelier_invites','atelier_courses','atelier_snapshots','atelier_usage','atelier_rates'] loop execute format('alter table public.%I enable row level security',t);execute format('alter table public.%I force row level security',t);execute format('revoke all on public.%I from public,anon,authenticated',t);end loop;end$$;

create function public.atelier_connected(x uuid,y uuid) returns boolean language sql stable security definer set search_path=pg_catalog,public as $$select exists(select 1 from public.atelier_friendships f join public.atelier_members m on m.uid=y and m.active where f.a=least(x,y) and f.b=greatest(x,y))$$;
revoke all on function public.atelier_connected(uuid,uuid) from public,anon,authenticated;

create function public.atelier_friends(op text,payload jsonb default '{}'::jsonb) returns jsonb language plpgsql security definer set search_path=pg_catalog,public,auth as $$
declare u uuid:=auth.uid(); c public.atelier_courses; s public.atelier_snapshots; inv public.atelier_invites; v_id uuid; peer uuid; ids uuid[]; code text; name text; n integer; used bigint; m date:=date_trunc('month',now() at time zone 'UTC')::date; result jsonb;begin
 if u is null or not exists(select 1 from public.atelier_members where uid=u and active) then raise exception using errcode='42501',message='Private membership is required.';end if;
 if jsonb_typeof(payload)<>'object' or pg_column_size(payload)>32768 then raise exception 'Invalid request.';end if;
 delete from public.atelier_rates where uid=u and minute<now()-interval '2 days';
 insert into public.atelier_rates values(u,date_trunc('minute',now()),1) on conflict(uid,minute) do update set hits=least(1000,atelier_rates.hits+1) returning hits into n;
 if n>100 then return jsonb_build_object('error','Please wait before trying again.','status',429);end if;
 -- Action failures roll back their subtransaction, while failed attempts still count.
 begin
 if op='home' then
  select jsonb_build_object('profile',jsonb_build_object('id',u,'name',display_name),'limits',jsonb_build_object('max_file_bytes',41943040,'max_courses',25,'max_friends',20)) into result from public.atelier_members where uid=u;
  result:=result||jsonb_build_object('friends',coalesce((select jsonb_agg(jsonb_build_object('id',p.uid,'name',p.display_name) order by p.display_name) from public.atelier_members p where p.active and public.atelier_connected(u,p.uid)),'[]'::jsonb));
  result:=result||jsonb_build_object('courses',coalesce((select jsonb_agg(to_jsonb(q) order by q.updated_at desc) from (select id,title,recipients,enabled,version,latest_id,updated_at,(select ss.id from public.atelier_snapshots ss where ss.course_id=atelier_courses.id and ss.state in('pending','uploading') limit 1) as pending_id from public.atelier_courses where owner_id=u order by updated_at desc limit 25) q),'[]'::jsonb));
  result:=result||jsonb_build_object('inbox',coalesce((select jsonb_agg(to_jsonb(q) order by q.updated_at desc) from (select c0.id,c0.title,c0.version,c0.latest_id,c0.updated_at,p0.display_name as sender,s0.bytes,s0.sha256 from public.atelier_courses c0 join public.atelier_members p0 on p0.uid=c0.owner_id and p0.active join public.atelier_snapshots s0 on s0.id=c0.latest_id and s0.state='ready' where c0.enabled and u=any(c0.recipients) and public.atelier_connected(u,c0.owner_id) order by c0.updated_at desc limit 100) q),'[]'::jsonb));return result;
 elsif op='profile' then
  name:=btrim(payload->>'name');if name is null or length(name) not between 1 and 60 or name ~ '[[:cntrl:]]' then raise exception 'Use a name between 1 and 60 characters.';end if;update public.atelier_members set display_name=name where uid=u;return jsonb_build_object('name',name);
 elsif op='invite_create' then
  delete from public.atelier_invites where owner_id=u and expires_at<now()-interval '2 days';
  if (select count(*) from public.atelier_friendships where a=u or b=u)>=20 then raise exception 'Your friend list is full.';end if;
  if (select count(*) from public.atelier_invites where owner_id=u and created_at>now()-interval '1 day')>=10 then raise exception 'Your daily invite limit is reached.';end if;
  code:=replace(gen_random_uuid()::text,'-','')||replace(gen_random_uuid()::text,'-','');insert into public.atelier_invites(owner_id,token_hash) values(u,encode(sha256(convert_to(code,'UTF8')),'hex')) returning * into inv;return jsonb_build_object('code',code,'expires_at',inv.expires_at);
 elsif op in ('invite_preview','invite_accept') then
  code:=payload->>'code';if code is null or code !~ '^[a-f0-9]{64}$' then raise exception 'That invite is not available.';end if;
  select * into inv from public.atelier_invites where token_hash=encode(sha256(convert_to(code,'UTF8')),'hex') for update;
  if not found or inv.used_by is not null or inv.expires_at<=now() or inv.owner_id=u or not exists(select 1 from public.atelier_members where uid=inv.owner_id and active) then raise exception 'That invite is not available.';end if;
  if op='invite_preview' then return (select jsonb_build_object('name',display_name) from public.atelier_members where uid=inv.owner_id);end if;
  -- Serialize concurrent accepts for either user's bounded friend list.
  perform uid from public.atelier_members where uid in(u,inv.owner_id) order by uid for update;
  if (select count(*) from public.atelier_friendships where a=u or b=u)>=20 or (select count(*) from public.atelier_friendships where a=inv.owner_id or b=inv.owner_id)>=20 then raise exception 'A friend list is full.';end if;
  insert into public.atelier_friendships(a,b) values(least(u,inv.owner_id),greatest(u,inv.owner_id)) on conflict do nothing;update public.atelier_invites set used_by=u where id=inv.id;return jsonb_build_object('connected',true);
 elsif op='friend_remove' then
  peer:=(payload->>'id')::uuid;delete from public.atelier_friendships where a=least(u,peer) and b=greatest(u,peer);return jsonb_build_object('removed',true);
 elsif op in ('course_create','course_update') then
  name:=btrim(payload->>'title');if name is null or length(name) not between 1 and 100 or name ~ '[[:cntrl:]]' then raise exception 'Choose a short course title.';end if;
  if jsonb_typeof(payload->'recipients')<>'array' or jsonb_array_length(payload->'recipients') not between 1 and 20 then raise exception 'Choose at least one friend.';end if;
  select array_agg(distinct x::uuid) into ids from jsonb_array_elements_text(payload->'recipients') x;
  foreach peer in array ids loop if not public.atelier_connected(u,peer) then raise exception using errcode='42501',message='Choose a current friend.';end if;end loop;
  perform uid from public.atelier_members where uid=u for update;
  if op='course_create' then
   if (select count(*) from public.atelier_courses where owner_id=u)>=100 then raise exception 'Your shared course history is full. Ask the service administrator to clear stopped courses.';end if;
   if (select count(*) from public.atelier_courses where owner_id=u and enabled)>=25 then raise exception 'Your shared course limit is reached.';end if;
   insert into public.atelier_courses(owner_id,title,recipients) values(u,name,ids) returning * into c;
  else
   update public.atelier_courses set title=name,recipients=ids,updated_at=now() where id=(payload->>'id')::uuid and owner_id=u and enabled returning * into c;if not found then raise exception using errcode='42501',message='That course is not available.';end if;
  end if;return jsonb_build_object('id',c.id,'version',c.version);
 elsif op='snapshot_begin' then
  select * into c from public.atelier_courses where id=(payload->>'course_id')::uuid and owner_id=u and enabled for update;
  if not found then raise exception using errcode='42501',message='That course is not available.';end if;
  if c.version<>(payload->>'previous_version')::int then raise exception 'A newer version is available. Refresh first.';end if;
  if exists(select 1 from public.atelier_snapshots where course_id=c.id and state in ('pending','uploading')) then raise exception 'This course already has an unfinished upload.';end if;
  used:=(payload->>'bytes')::bigint;if used not between 512 and 41943040 or coalesce(payload->>'sha256','') !~ '^[a-f0-9]{64}$' then raise exception 'This package is too large or incomplete.';end if;
  perform id from public.atelier_usage where id=true for update;
  if (select count(*) from public.atelier_snapshots where owner_id=u)>=200 or (select count(*) from public.atelier_snapshots)>=10000 then raise exception 'The private service needs safe package cleanup before another upload.';end if;update public.atelier_usage set month=m,egress_bytes=0,ingress_bytes=0 where id=true and month<>m;
  if (select ingress_bytes from public.atelier_usage where id=true)+used>2147483648 then raise exception 'The private service has reached its monthly upload limit.';end if;
  if (select reserved_bytes from public.atelier_usage where id=true)+used>524288000 or coalesce((select sum(bytes) from public.atelier_snapshots where owner_id=u),0)+used>134217728 then raise exception 'Private storage is full. Remove an older share first.';end if;
  v_id:=gen_random_uuid();insert into public.atelier_snapshots(id,course_id,owner_id,version,object_path,bytes,sha256) values(v_id,c.id,u,c.version+1,u::text||'/'||v_id::text||'.apkg',used,payload->>'sha256') returning * into s;update public.atelier_usage set reserved_bytes=reserved_bytes+used,ingress_bytes=ingress_bytes+used where id=true;return jsonb_build_object('id',s.id,'bytes',s.bytes,'version',s.version);
 elsif op='upload_ticket' then
  select * into s from public.atelier_snapshots where id=(payload->>'id')::uuid and owner_id=u for update;
  if not found or s.state<>'pending' or not exists(select 1 from public.atelier_courses where id=s.course_id and enabled) then raise exception using errcode='42501',message='That upload is not available.';end if;
  update public.atelier_snapshots set state='uploading',lease=gen_random_uuid(),lease_until=now()+interval '10 minutes' where id=s.id returning * into s;return jsonb_build_object('id',s.id,'owner_id',u,'path',s.object_path,'bytes',s.bytes,'sha256',s.sha256,'lease',s.lease);
 elsif op='download_ticket' then
  select s0.* into s from public.atelier_snapshots s0 join public.atelier_courses c0 on c0.id=s0.course_id where s0.id=(payload->>'id')::uuid and s0.state='ready' and c0.enabled and (c0.owner_id=u or (u=any(c0.recipients) and public.atelier_connected(u,c0.owner_id)));
  if not found then raise exception using errcode='42501',message='That shared version is not available.';end if;
  perform id from public.atelier_usage where id=true for update;update public.atelier_usage set month=m,egress_bytes=0,ingress_bytes=0 where id=true and month<>m;
  if (select egress_bytes from public.atelier_usage where id=true)+s.bytes>2147483648 then raise exception 'The private service has reached its monthly download limit.';end if;
  update public.atelier_usage set egress_bytes=egress_bytes+s.bytes where id=true;return jsonb_build_object('path',s.object_path,'bytes',s.bytes,'sha256',s.sha256,'id',s.id);
 elsif op='snapshot_cancel' then
  update public.atelier_snapshots set state='revoked' where id=(payload->>'id')::uuid and owner_id=u and state in('pending','uploading') returning * into s;if not found then raise exception 'That unfinished upload is not available.';end if;return jsonb_build_object('cancelled',true);
 elsif op='course_revoke' then
  update public.atelier_courses set enabled=false,updated_at=now() where id=(payload->>'id')::uuid and owner_id=u and enabled returning * into c;if not found then raise exception using errcode='42501',message='That course is not available.';end if;
  update public.atelier_snapshots set state='revoked' where course_id=c.id;return jsonb_build_object('revoked',true);
 else raise exception 'Unknown Friends action.';end if;
 exception when others then return jsonb_build_object('error',case when sqlstate in('P0001','42501') then sqlerrm else 'Friends could not complete that request.' end,'status',case when sqlstate='42501' then 403 else 400 end);end;
end$$;
revoke all on function public.atelier_friends(text,jsonb) from public,anon;
grant execute on function public.atelier_friends(text,jsonb) to authenticated;

-- Only the edge service can assert actual bytes/hash or delete Storage ledger rows.
create function public.atelier_finish_upload(p_owner uuid,p_id uuid,p_lease uuid,p_bytes bigint,p_sha256 text) returns jsonb language plpgsql security definer set search_path=pg_catalog,public as $$declare s public.atelier_snapshots;cid uuid;begin
 select course_id into cid from public.atelier_snapshots where id=p_id and owner_id=p_owner;perform id from public.atelier_courses where id=cid and enabled for update;if not found then raise exception 'This course is no longer shared.';end if;
 select * into s from public.atelier_snapshots where id=p_id and owner_id=p_owner and state='uploading' and lease=p_lease and lease_until>now() for update;
 if not found or s.bytes<>p_bytes or s.sha256<>p_sha256 then raise exception 'The uploaded package did not match.';end if;
 if not exists(select 1 from public.atelier_members where uid=p_owner and active) or not exists(select 1 from public.atelier_courses where id=s.course_id and enabled) then raise exception 'This course is no longer shared.';end if;
 update public.atelier_snapshots set state='ready',lease=null,lease_until=null where id=s.id;update public.atelier_courses set version=s.version,latest_id=s.id,updated_at=now() where id=s.course_id;return jsonb_build_object('published',true,'version',s.version);
end$$;
create function public.atelier_cleanup_candidates() returns jsonb language sql security definer set search_path=pg_catalog,public as $$with candidates as(select s.id from public.atelier_snapshots s where (s.state='revoked' and (s.lease_until is null or s.lease_until<now())) or (s.state in('pending','uploading') and s.created_at<now()-interval '1 day' and (s.lease_until is null or s.lease_until<now())) or (s.state='ready' and (select count(*) from public.atelier_snapshots n where n.course_id=s.course_id and n.state='ready' and n.version>s.version)>=2) order by s.created_at for update skip locked limit 10), claimed as(update public.atelier_snapshots set state='revoked' where id in(select id from candidates) returning id,object_path as path) select coalesce(jsonb_agg(to_jsonb(claimed)),'[]'::jsonb) from claimed$$;
create function public.atelier_confirm_cleanup(p_id uuid) returns void language plpgsql security definer set search_path=pg_catalog,public as $$declare n bigint;begin
 delete from public.atelier_snapshots where id=p_id and state='revoked' and (lease_until is null or lease_until<now()) returning bytes into n;
 if n is not null then update public.atelier_usage set reserved_bytes=greatest(0,reserved_bytes-n) where id=true;end if;
 delete from public.atelier_rates where minute<now()-interval '2 days';delete from public.atelier_invites where expires_at<now()-interval '2 days';
end$$;
revoke all on function public.atelier_finish_upload(uuid,uuid,uuid,bigint,text),public.atelier_cleanup_candidates(),public.atelier_confirm_cleanup(uuid) from public,anon,authenticated;
grant execute on function public.atelier_finish_upload(uuid,uuid,uuid,bigint,text),public.atelier_cleanup_candidates(),public.atelier_confirm_cleanup(uuid) to service_role;

insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types) values('atelier-friends','atelier-friends',false,41943040,array['application/octet-stream','application/zip']) on conflict(id) do nothing;
-- Restrictive exclusions protect this bucket even if a project has broad policies.
create policy atelier_private_objects on storage.objects as restrictive for all to anon,authenticated using(bucket_id<>'atelier-friends') with check(bucket_id<>'atelier-friends');
create policy atelier_private_bucket on storage.buckets as restrictive for all to anon,authenticated using(id<>'atelier-friends') with check(id<>'atelier-friends');
