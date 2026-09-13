# Atelier 1.0.2 — repository and release handoff

## Status and authorization

The ChatGPT GitHub connection returned account `AAAAAAwd899`. Its accessible-repository list and Atelier repository search both returned no repositories. No repository, branch, commit, pull request, release, or AnkiWeb listing was created by this task.

Do not invent a repository, public visibility, support URL, rating, compatibility certification or AnkiWeb ID. Ask the owner for the intended repository and visibility, or use the exact target they provide. Grant the connected application access to that repository before expecting ChatGPT to write it. A request to check upload capability is not approval to make a new public repository.

The name is **Atelier**. Only increment its version number. Keep the private installer ID `daedalus_atelier` unless an actual AnkiWeb ID migration has been explicitly planned and verified.

## Authoritative runtime

Use `src/` from this exact 1.0.2 source kit. Do not substitute the older 0.8/0.9 source branches or restore 1.0.1 over the new folder operation. The source is paired to the .ankiaddon by per-file SHA-256 and runtime fingerprint in the versioned Build/Files JSON records. Retain the included license and component notices.

Changes from 1.0.1: `folder_study.py`, its guarded whole-folder route in `integration.py`, confirmation UI in `web/atelier.js`, version labels and consumer docs. Embedded Sprout/Workshop and remote/mask/reviewer geometry code are unchanged. The new behavior changes native display-order settings after consent; it is not a custom queue or a filtered deck.

## Repository contents

Include `src/`, tests, developer harnesses, verifier/packager scripts, exact baseline and patch manifests, current docs and selected screenshot assets. Do not commit local Anki profiles, `.env`, API credentials, collection/media data, add-on user preferences, source uploads, `exam_sprout/` or `workshop/` profile stores, Python caches or font files. The directories `src/sprout` and `src/workshop` are licensed bundled code, not profile data; do not delete them by an overly broad ignore pattern.

Keep the ~64 MB installer and ZIP distributions as versioned GitHub Release assets rather than repeatedly committing binary releases into the source history. Source fixture artwork belongs to the code; retain required bundled assets. Never remove license notices to reduce size.

## Suggested Codex workflow with authenticated gh/git

1. Confirm the exact owner/repository and visibility with the user. Verify `gh auth status` and repository permissions locally without printing tokens.
2. Fetch the target branch and inspect existing files. Work on a versioned branch, never overwrite unrelated repository content or force-push history.
3. Stage the reviewed source and selected current screenshots. Run the full verifier and package checks. Keep evidence separate from false native compatibility claims.
4. Commit and open a PR for an existing project, or initialize the explicitly authorized new repository. Do not auto-merge unless authorized.
5. Upload `Atelier-1.0.2.ankiaddon`, source ZIP, checksums and concise notes as a release only after release authorization. Check the uploaded asset hashes and links.
6. Use Windows user-acceptance language and label macOS as unverified/trial. Keyboard remotes are keyboard/HID mode; no universal gamepad/Bluetooth driver support is claimed.

## Marketing assets

Use the current screenshot-based multitheme gallery/posters. Their UI pixels come from the shipped 1.0.2 renderer with fictional data. They are not native Windows screenshots or generated promises. Do not reuse the previous Forest-only AI mockups as proof of the installed UI; they altered details and included stale version labels.

Primary product copy: “Atelier — organize, create, and study in Anki.” Explain normal scheduled review separately from independent practice. Never say all study leaves scheduling unchanged: normal ratings and explicitly enabled new-card learning affect scheduling. Do not advertise generated scores as predicted exam grades.

Optional Gemini/Veo work should animate only the surrounding presentation or camera over an approved screenshot; preserve the screenshot itself as a composited layer, not a generated reconstruction. No video was generated or published in this task. Do not claim the video demonstrates interactions unless they were recorded from the app.
