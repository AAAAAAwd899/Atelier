import { sha256 } from "npm:@noble/hashes@2.4.0/sha2.js";
import { createHandler } from "./handler.mjs";
Deno.serve(createHandler({url:Deno.env.get("SUPABASE_URL"),publicKey:Deno.env.get("SUPABASE_ANON_KEY"),serviceKey:Deno.env.get("SUPABASE_SERVICE_ROLE_KEY"),createHash:()=>sha256.create(),allowedOrigin:Deno.env.get("ATELIER_ALLOWED_ORIGIN")||""}));
