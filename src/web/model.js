/* Framework-independent display model. No Anki writes or scheduling logic. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.AtelierModel = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function roots(nodes, ids) {
    const map = new Map(nodes.map(n => [n.id, n]));
    const selected = new Set(ids.filter(id => map.has(id)));
    return [...selected].filter(id => {
      let p = map.get(id).parent; const seen = new Set([id]);
      while (map.has(p) && !seen.has(p)) {
        if (selected.has(p)) return false;
        seen.add(p); p = map.get(p).parent;
      }
      return true;
    }).map(id => map.get(id));
  }
  function totals(nodes) {
    return nodes.reduce((out, n) => {
      for (const k of ['new', 'learn', 'review']) out[k] += Math.max(0, Number(n[k]) || 0);
      return out;
    }, {new: 0, learn: 0, review: 0});
  }
  function scope(nodes, profile) {
    const active = (profile.studies || []).filter(s => s.active);
    const selected = profile.selected_study === 'all' || !active.some(s => s.id === profile.selected_study)
      ? active : active.filter(s => s.id === profile.selected_study);
    const enabled = !!profile.focus_enabled;
    const ids = [...new Set(selected.flatMap(s => s.deck_ids || []))];
    const known = new Set(nodes.map(n => n.id));
    const top = enabled ? roots(nodes, ids) : nodes.filter(n => n.parent === '0');
    return {enabled, active, selected, roots: top, totals: totals(top),
      missing: enabled ? ids.filter(id => !known.has(id)) : []};
  }
  function dayState(value, now = new Date()) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return null;
    const [y, m, d] = value.split('-').map(Number);
    const epoch = Date.UTC(y, m - 1, d);
    const check = new Date(epoch);
    if (check.getUTCFullYear() !== y || check.getUTCMonth() !== m - 1 || check.getUTCDate() !== d) return null;
    return Math.round((epoch - Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())) / 86400000);
  }
  function belongs(nodes, roots, id) {
    const selected = new Set(roots.map(n => n.id)), map = new Map(nodes.map(n => [n.id, n]));
    let n = map.get(id); const seen = new Set();
    while (n && !seen.has(n.id)) {
      if (selected.has(n.id)) return true;
      seen.add(n.id); n = map.get(n.parent);
    }
    return false;
  }
  // Sort siblings only: native deck ancestry and card order never change.
  const collator = new Intl.Collator(undefined, {numeric: true, sensitivity: 'base'});
  function compareNames(a, b) {
    return collator.compare(String(a.name || ''), String(b.name || '')) ||
      collator.compare(String(a.path || ''), String(b.path || '')) ||
      collator.compare(String(a.id || ''), String(b.id || ''));
  }
  function sortNodes(items, {sort='name', recent=[], folderIds=[], groupFolders=true}={}) {
    const folders = new Set(folderIds), rank = new Map(recent.map((id, i)=>[id,i]));
    const folder = n => !!(n.children?.length || folders.has(n.id));
    const due = n => Math.max(0,Number(n.review)||0) + Math.max(0,Number(n.learn)||0);
    return [...items].sort((a,b)=>
      (sort==='due' ? due(b)-due(a) :
       sort==='recent' ? (rank.get(a.id)??Infinity)-(rank.get(b.id)??Infinity) || 0 :
       groupFolders ? Number(folder(b))-Number(folder(a)) : 0) || compareNames(a,b));
  }

  const TOOL_GROUPS = Object.freeze([
    {id:'everyday',name:'Everyday',description:'The things you reach for most.'},
    {id:'organize',name:'Organize & study',description:'Work with cards, templates and study decks.'},
    {id:'maintenance',name:'Care & maintenance',description:'Inspect first. Anki keeps its original confirmations.'},
    {id:'settings',name:'Settings & help',description:'Your environment, preferences and support.'}
  ].map(Object.freeze));
  const TOOLS = Object.freeze([
    ['add','Add cards','Write a note, add an image, or make an image-occlusion card.','plus','everyday','create notes editor new cards',''],
    ['browse','Browse & edit','Find cards, change notes, add tags and manage your collection.','browse','everyday','search find suspend tags notes browser',''],
    ['sync','Sync with AnkiWeb','Opens Anki’s sync. Local exam plans and Pip effort are not included.','sync','everyday','upload download account backup','Finish or save a practice session first.'],
    ['stats','Statistics','Your real scheduled-review history in Anki’s original graphs.','chart','everyday','history graphs progress stats',''],
    ['import','Import decks or notes','Bring in a deck package or a supported notes file.','import','everyday','open apkg colpkg csv tsv text collection',''],
    ['export','Export & share','Choose the decks, notes and media to export with Anki.','export','everyday','save apkg colpkg csv backup share',''],
    ['note_types','Note types & templates','Manage fields and the cards generated from each note.','note-types','organize','fields basic cloze templates formatting','Template changes can affect many cards.'],
    ['filtered_deck','Filtered deck','Open Anki’s custom-study deck builder with its full settings.','filter','organize','custom study cram filtered search','Scheduling depends on the settings you choose.'],
    ['undo','Undo collection change','Use Anki’s normal Undo; local exam results are separate.','undo','organize','restore reverse undo',''],
    ['redo','Redo collection change','Reapply the next change in Anki’s collection redo history.','redo','organize','redo reverse',''],
    ['check_media','Check media','Inspect missing or unused files in Anki’s media-check dialog.','media','maintenance','missing images audio unused files repair','Review the findings before deleting media.'],
    ['check_database','Check database','Run Anki’s collection check and follow its own prompts.','database','maintenance','integrity repair check collection','Save or close an unfinished exam first.'],
    ['empty_cards','Empty cards','Inspect empty generated cards before any cleanup.','blank','maintenance','delete cleanup empty cloze','Removing cards is a collection change.'],
    ['preferences','Anki preferences','Anki’s account, editing, reviewing and application preferences.','sliders','settings','options settings language theme',''],
    ['addons','Manage add-ons','Enable, disable or configure add-ons in Anki’s manager.','addons','settings','plugins extensions addons','A restart may be needed after changes.'],
    ['profiles','Switch profile','Open Anki’s profile chooser, keeping its close/save checks.','profiles','settings','user account collection profile backups','Save or close a practice session first.'],
    ['fullscreen','Full screen','Toggle Anki’s native full-screen mode.','fullscreen','settings','window maximize minimise display',''],
    ['check_updates','Check Anki updates','Use Anki’s original update check.','updates','settings','upgrade version update',''],
    ['help','Anki manual','Open the official documentation in your browser.','book','settings','support help documentation instructions','Opens your browser.']
  ].map(([id,label,description,icon,group,keywords,note])=>Object.freeze({id,label,description,icon,group,keywords,note})));
  const normalizeSearch = value => String(value||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();
  function findTools(query='',group='all') {
    const parts=normalizeSearch(query).split(/\s+/).filter(Boolean);
    return TOOLS.filter(t=>(group==='all'||t.group===group)&&parts.every(q=>normalizeSearch([t.id,t.label,t.description,t.keywords,t.note].join(' ')).includes(q)));
  }
  function continueDeck(nodes,profile) {
    const last=nodes.find(n=>n.id===profile.last_studied);
    if(!last||last.children?.length)return null;
    const f=scope(nodes,profile);
    if(f.enabled&&!belongs(nodes,f.roots,last.id))return null;
    return last;
  }
  function lastFolder(nodes,profile,current='0') {
    const map=new Map(nodes.map(n=>[n.id,n])),folders=new Set(profile.folders||[]);
    for(const id of [profile.last_location,...(profile.recent_locations||[])]){
      let n=map.get(id);if(!n)continue;
      if(!n.children?.length&&!folders.has(n.id))n=map.get(n.parent);
      if(n&&n.id!==current&&(n.children?.length||folders.has(n.id)))return n;
    }
    return null;
  }
  return Object.freeze({compareNames, sortNodes, roots, totals, scope, dayState, belongs, TOOL_GROUPS, TOOLS, findTools, continueDeck, lastFolder});
});
