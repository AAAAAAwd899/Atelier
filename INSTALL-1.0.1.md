# Atelier 1.0.1

## Update

Save and close practice and authoring work. Wait for imports or card publication to finish. Back up your Anki collection, Atelier `user_files`, and both profile-local `exam_sprout` and complete `workshop` folders (including original sources). Keep standalone Sprout and Workshop disabled.

Install **Atelier-1.0.1.ankiaddon** using **Tools → Add-ons → Install from file**, over the existing Atelier installation. Fully quit and restart Anki. Do not unzip or delete the old add-on first. Confirm **Tools → Atelier · 1.0.1**. The same local stores, worlds and owner choice are retained. Nothing is published to AnkiWeb.

## Reviewer

Short supported text cards should fit with one allowance for the top header. Long content retains scrolling, and the next question returns to its starting position. Grading buttons stay stationary. Images and masks are not automatically resized or rewritten. For a specialized template, use **Appearance → Reviewer → Controls only** or **Tools → Atelier → Use original design for this note type**. **Use original reviewer styling** disables the reviewer theme independently.

The latest screenshot message did not contain a usable attachment. This build corrects reproduced spacing and protects additional mask layouts; it cannot certify that unseen screenshot's exact mask defect.

## Remote controls, without clutter

Open **Anki tools → Remote controls**, or **Tools → Atelier · 1.0.1 → Remote controls…**. The tools search also finds “remote” and “controller”. Nothing is added to the reviewer toolbar.

1. Pair in your computer's Bluetooth settings, or connect its USB receiver. Select **Keyboard / Key mode** on the remote where available.
2. Choose **Test remote buttons**. Press a button; the dialog shows the received key. This test cannot reveal, grade or change a card. Escape stops testing.
3. A remote sending your existing Anki keys needs no custom map. For other keys, use **Assign** beside Show answer, Again, Hard, Good, Easy, Replay or Scroll. Assignments must be unique and unmodified.
4. Check **Use custom buttons during scheduled review**, then **Save**. Until saved, the new mapping is not enabled. Cancel keeps the original settings.
5. Test with sample cards. Show answer only reveals; a rating requires the answer side. Hold/repeat is ignored. Review or its answer bar must be focused; typed-answer fields, dialogs and other windows retain their normal handling.

**Use original Anki controls** turns off the custom map; select Save to apply that choice. It keeps saved assignments for later. There is no hardware driver or background Bluetooth scan. Keyboard-mode remotes are the supported input path. Gamepad-only/mouse-only/proprietary devices need their own supported mapping software. When using Contanki or a manufacturer's mapping add-on, keep Atelier's custom mapping off to avoid competing mappings.

The same keys on a regular keyboard share the custom actions during review. No device name, battery status or hardware compatibility is inferred from a received key.

## Native acceptance checklist

- Short → long → short review, answer reveal, Details/Card only, and a short window with Onigiri's top header.
- Native and legacy image occlusion, original images and pseudo-masks, typed answers and custom interactive notes.
- Remote test, assignment, cancellation and save; press-and-hold, rapid repeated presses, modified system shortcuts, switching away from Anki, clicking a field and clicking Show Answer before the next remote press.
- Disable custom mapping and confirm normal Anki/Contanki keys. Verify existing plans, saved practice, source drafts, publishing and Undo remain.

No Windows/macOS native runtime or physical remote was tested here. Browser frames and Qt stand-ins do not establish hardware or native display compatibility. Mac remains a controlled trial target. The verification report records the actual tests and limitations.

## Recovery

Use **Tools → Atelier → Use original reviewer styling** for a template conflict. In Remote controls, uncheck custom buttons and Save to restore native input. If necessary, disable Atelier and restart rather than deleting its data. Before rollback, close/save work and back up every local store. Do not enable standalone Sprout/Workshop while the combined engine is active.
