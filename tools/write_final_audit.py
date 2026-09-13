"""Write current audit from measured receipts, without granting release approval."""
from pathlib import Path
import argparse,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--proof-dir',type=Path,required=True);ap.add_argument('--ci-run-url',required=True);args=ap.parse_args()
 def read(p):return json.loads(p.read_text())
 fingerprint=runtime_digest();proof=read(args.proof_dir/'verified.json');assert proof['runtime_sha256']==fingerprint
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 delta=read(ROOT/'patch-103-changes.json');changed=len(delta['changed']);added=len(delta['added']);removed=len(delta['removed'])
 def native_receipt(prefix):
  matches=[]
  for folder in (ROOT/'output').glob(prefix+'*'):
   result=folder/'results.json'
   if result.is_file():
    receipt=read(result)
    if receipt.get('runtime_sha256')==fingerprint and not receipt.get('errors'):matches.append(receipt)
  assert len(matches)==1,(prefix,len(matches));return matches[0]
 native_desktop=native_receipt('native-desktop-');native_io=native_receipt('native-io-');native_folder=read(ROOT/'output/native-folder/results.json');native_install=read(ROOT/'output/native-install/results.json')
 native_version=native_desktop['version'];assert native_io['anki']==native_folder['anki']==native_install['anki']==native_version
 native_first=native_desktop['captures'][0];logical='×'.join(map(str,native_first['logical_window']));pixels='×'.join(map(str,native_first['pixel_size']));native_build=native_folder['build']
 endurance=read(ROOT/'output/endurance/results.json');assert endurance['completed'] and not endurance['errors']
 warm=next(s for s in endurance['samples'] if s['cycle']>=18);last=endurance['samples'][-1]
 baseline=read(ROOT/'output/performance/baseline.json')['summary'];candidate=read(ROOT/'output/performance/candidate.json')['summary']
 memory=read(ROOT/'output/memory-followup/results.json');assert memory['completed'] and not memory['errors'];ma,mb=memory['samples'][0],memory['samples'][-1]
 performance='\n'.join(f"| {key} | {baseline[key]['n']} | {baseline[key]['median_ms']:.1f} / {baseline[key]['p95_ms']:.1f} | {candidate[key]['median_ms']:.1f} / {candidate[key]['p95_ms']:.1f} |" for key in baseline)
 text=f'''# Atelier 1.0.3 — private candidate audit

Status: implemented and packaged for owner review, with the automated verification recorded below. This is not public-release approval or universal compatibility acceptance. The owner rejected the first flat Forest render. Final captures use the revised runtime; earlier renders remain historical failure evidence.

## Source and checkpoints

The supplied 1.0.2 source archive was checked and extracted. Its 233 runtime entries matched the recorded baseline. The original installer itself was not supplied for independent rechecking; the kit records its earlier source/installer equality. No newer accepted build existed. Git main preserves the baseline.

The final runtime fingerprint is `{fingerprint}`. The explicit delta contains {changed} changed files, {added} added files and {removed} removed files: 248 runtime files total. Original exam and authoring runtime trees, stores, scheduling/folder-order operation, remotes, mask publication and widget data logic remain byte-identical. The generated palette contract and scoped presentation adapters contain the upgrade; source images and stored mask coordinates are not converted.

- A: canonical roles, retired duplicate home layer, compact Home/Widgets hierarchy and twelve local landscapes. Midnight, Rose and Forest were rendered in actual Anki. The original Forest screenshot was superseded after inspection.
- B: existing world IDs retained across Home, Library list/grid, Card Studio, Mask Studio, Exam setup, Practice builder, reviewer question/answer, Results, Pip, Widgets, Progress and Tools. Captures include all twelve worlds at 1440×900, 1280×720, 1024×768, 800×600 and browser-only 390×720. There are 900 default captures, including 60 additional generic-Library captures; these are repeated palette/viewport cases, not 900 independent integrations.
- C: preserved-engine verification, exact stock IO native lifecycle tests, actual folder scheduler checks, cumulative installer, matching source, repeat-build equality, extracted-payload checks, real recording and private GitHub handoff. Owner visual acceptance and the unavailable host/hardware gates remain open.

## Current automated evidence

Full verifier receipt: {proof['python_total']} Python test cases, zero failures/skips; {len(proof['browser_suites'])} browser suites with {proof['browser_total']} checks and zero reported page errors. Evidence uses the exact fingerprint above. Pure logic/model/storage tests and browser native-API doubles are identified in the individual receipts. Native tests are separate below. The full verification gate is `verify_release.py`; deterministic packaging additionally checks syntax, manifest, ZIP CRC, preserved engine hashes, forbidden/private files, exact source/installer bytes and repeat builds.

The complete CI run is {args.ci_run_url}, runtime source commit `{head}`. The combined Card Studio launcher checks, including repeated mount, narrow layouts, theme-specific materials and original-theme round trips, are included in the full-verifier total above.

All 900 default captures reported no horizontal page overflow or uncaught page errors. Contact sheets for every captured screen were inspected at 1440×900 and 390×720 across all twelve worlds. The unpublished add-on information page was also rendered at desktop and phone widths with its real interface images loaded, no horizontal overflow and no page errors. Nine scoped axe scans (Midnight/Rose/Forest × Home/Widgets/Tools) found zero violations; incomplete axe checks are retained. The conservative 78%-canvas composited backdrop probe passes normal-text 4.5:1 for the twelve worlds, with a minimum measured 4.653:1. These probes are not a complete accessibility certification or a claim that every possible user template was checked.

The extracted installer ran 16 unit checks and the designated 1.0.3 IO, 1.0.1 reviewer/remote-focus and 1.0.2 folder/browser checks. Their separate logs bind execution to the extracted files, whose runtime bytes equal the delivered source. Initial extracted 1.0.1 testing exposed a fixed 40 ms test race; the harness now waits for the measured long-content layout before testing user scrolling, retaining the scroll assertion.

Windows original authoring tests passed 208 of 209; the unchanged filesystem symlink test requires Windows privilege 1314. The complete Linux verifier passed all 209 authoring cases. Windows DST fixtures now use explicit America/Chicago transitions with their original 23/25-hour assertions. Older world font assertions were corrected to check every computed heading against the existing catalog; the original catalog had two font stacks, not three. Panel-radius regression and insufficient muted-text contrast found during rendering were fixed. CI Pip timeouts led to explicit loaded-screen waits and sequential browser execution; assertions were retained.

The project development environment dependency scan initially reported vulnerable pip/setuptools versions. Updating those project-local packaging tools produced a clean rescan. Both scan receipts are included. This covers the scanned development environment, not Anki's own Python/Qt distribution or a guarantee against unknown vulnerabilities.

## Actual native evidence

Windows, installed Anki {native_version} build {native_build}; disposable synthetic profiles only, no owner profile or sync. Payload bytes are checked against the installer source before loading. Rendering tests copy the extracted payload into the QA add-on folder. A separate real AddonManager installer test exercises the ZIP update path; the GUI file picker was not automated.

- Six real main-window captures: Home and fully loaded built-in Widgets in Midnight, Rose and Forest. Measured logical window {logical}, screenshot {pixels}, device pixel ratio {native_first['device_pixel_ratio']}. No fabricated title bars or substituted statistics.
- Stock native IO: real question/answer canvases, fitted whole image/mask registration, Actual size, original note/media preservation, native rating/revlog and native Undo. Nine checks pass. A known landmark is visibly occluded on question and revealed on answer. Fit support is restricted to the documented exact stock-template fingerprint; unknown/custom templates fail closed.
- Actual Anki folder backend: eight checks pass for parent preset isolation, unchanged lecture/unrelated presets, preserved global options, native Undo, no repeated preset clone, exact scope and a native queue containing all three synthetic lecture decks. The recorded order does not promise strict alternation or override Anki limits/learning rules.
- Actual Anki AddonManager: eight checks pass for baseline installation, cumulative update, payload equality, retained preferences, retained `user_files`, untouched profile-local saved-file sentinels, private package identity and no conflicting installs. The native compatible flag is true on this host. Saved-file sentinels test update preservation, while semantic store operations are covered by the separate original engine suites. A test-profile lock collision was resolved with a fresh unique QA profile for each native IO run.

Input was scripted API/JavaScript, not a physical remote. Native GPU initialization warnings occurred and rendering used the software path; no live GPU claim. Requested 100% scaling was clamped by the host, so those attempts are not independent 100/125/200% tests. Initial offscreen/late-sizing/blank-canvas failures are retained separately; final screenshots wait for actual canvas painting. Native QA shutdown can block in collection close after completed receipts; the harness bounds shutdown for its disposable profile.

Final gallery inspection also caught stale native compositor frames in two Home/Widgets captures despite ready browser diagnostics. The capture harness now checks the requested world and route, allows the native compositor to settle, and the six-screen set was retaken and inspected. The rejected frames remain explicitly labelled capture failures, not final passing screenshots.

## Performance evidence

Same local Windows host, baseline source and candidate fixtures. Baseline measurements were run from the untouched Git baseline during final verification, not recorded before development began. Other task processes were active. Values are median / p95 milliseconds.

| Probe | Samples each | Baseline 1.0.2 | Candidate 1.0.3 |
|---|---:|---:|---:|
{performance}

Open means HTML through controls, fonts and two frames, not disk-cold scenery or native Anki startup. Navigation includes automation and two frames; 5,000-deck search includes production debounce and paint. The table records both median and p95 so the observed search-tail variance remains visible; this is not an isolated-host speed claim.

The browser endurance probe completed {endurance['elapsed_seconds']:.1f} seconds and {endurance['cycles']} route/theme cycles with no page errors. After the first complete palette rotation, retained nodes stayed at {last['nodes']}, listeners at {last['jsEventListeners']} and documents at {last['documents']}. Forced-GC JavaScript heap rose from {warm['heap_bytes']/1048576:.2f} MiB at cycle {warm['cycle']} to {last['heap_bytes']/1048576:.2f} MiB at the last sample. This small rise remains an observation, not a no-leak guarantee. Decoded scenery/GPU memory, native 30–60-minute review endurance and isolated source/figure-load timing remain unmeasured.

An additional 288-cycle accelerated investigation captured actual V8 heap snapshots after warmup. DOM/listener/document counts remained unchanged. Between cycles 48 and 288, snapshot `code` entries grew by {mb['bytes_by_node_type']['code']-ma['bytes_by_node_type']['code']} bytes, while closure self-size was unchanged and object self-size grew by only {mb['bytes_by_node_type']['object']-ma['bytes_by_node_type']['object']} bytes. The observed growth was dominated by V8 code entries rather than retained page nodes/handlers. Embedder heap use fell from {ma['runtime_heap']['embedderHeapUsedSize']} to {mb['runtime_heap']['embedderHeapUsedSize']} bytes across those samples. This investigation does not measure total decoded-image or GPU RAM.

## Visual scorecard and open gates

Composition: richer local scenery, tighter hierarchy and world-specific shapes; actual captures support the change. Readability: composited palette and scoped axe checks pass; arbitrary card content remains outside that claim. Consistency: catalog font/shape and theme-switch assertions pass. Task clarity: preserved actual workflows and default/empty/error/long/dirty-form browser cases are in the evidence; an uncoached newcomer study is still needed. Native integration: limited Windows Home/Widgets/IO and folder backend checks pass.

Representative full-size screens were inspected and failures corrected. This does not claim a human inspected every one of the 900 files or every possible visual state. Owner acceptance of the five scorecard dimensions remains pending. The recording shows actual browser interactions using explicitly synthetic data; generated landscapes have separate provenance and are never presented as UI test evidence.

Unperformed release gates: macOS/Retina, physical keyboard-mode remotes, native Windows 100/125/200% configurations, native fullscreen/autohide combinations, third-party IO Enhanced edit acceptance, every custom/media template, full native workflow integration, decoded-image memory, native endurance, 200% text enlargement across every surface, complete manual visual-state/accessibility review and uncoached newcomer tests. These require additional work and/or an available host/device; do not call the candidate production ready.

## Release boundary

Private repository: https://github.com/AAAAAAwd899/Atelier. Source branch `atelier-1.0.3`; no public visibility change, AnkiWeb listing or website deployment. `site/` contains unpublished add-on information with no invented numeric code, public download or approval flag. A GitHub push/site change cannot update installed copies. A future numeric AnkiWeb listing requires a verified one-time migration from private `daedalus_atelier`; subsequent approved updates must use that same listing. Account eligibility and the date it changes have not been verified.

Before public rollout, approve the exact installer hash, support statement, real listing and website destination. See MANUAL_ACTIONS_REQUIRED.md, PROFESSIONAL_REVIEW_REQUIRED.md and INSTALL-1.0.3.md. Historical marketing/acceptance files retained from the source kit do not grant current approval. The shared Daedalus standards were consulted; no Atelier-specific shared dashboard report existed, so this repository audit is the current project report.
'''
 (ROOT/'AUDIT-1.0.3.md').write_text(text,encoding='utf8',newline='\n')
if __name__=='__main__':main()
