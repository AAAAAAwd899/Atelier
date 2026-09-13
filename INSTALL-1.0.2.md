# Atelier 1.0.2

## Install or update

Save and close active practice and card-building work. Back up your Anki collection, Atelier's `user_files`, and the complete profile-local `exam_sprout` and `workshop` folders. Keep standalone Sprout and Workshop disabled.

In Anki choose **Tools → Add-ons → Install from file**, select **Atelier-1.0.2.ankiaddon**, then completely restart Anki. Do not unzip the installer or delete your current installation. Confirm **Tools → Atelier · 1.0.2**. The private package remains `daedalus_atelier`.

## Shuffle a whole folder

Open a folder in Library, choose **Study entire folder**, leave **Shuffle between lectures** selected, and confirm **Study whole folder**. The same confirmation is reached from the active-group footer and a folder's context menu. Anki's normal overview then opens; choose **Study Now**.

New cards are gathered/sorted randomly across that folder's lecture decks, and eligible review cards use random order. Learning due times still take priority where Anki requires them. Existing new/review mixing, daily limits and sibling burying remain. The sequence may contain consecutive cards from the same lecture; this is random order, not strict round-robin balancing. Anki may reuse a stable order on the same day.

The small lecture label continues using the current card's own deck when context is enabled. It is not changed to the parent folder merely because that folder was selected.

## Important: the order stays saved

Shuffle is a **saved Anki display-order setting**, not a temporary practice session. It applies only after explicit confirmation, not on installation or when opening the dialog. If the parent uses a shared preset, Atelier makes a copy and assigns it only to that parent. Other decks and subdeck presets are not changed. Later edits to the old shared preset will not automatically propagate to that copied parent.

Random review order no longer prioritizes the oldest due cards first. Due dates, intervals, card positions, FSRS parameters and learn/relearn steps are not reset or rewritten. Normal answer ratings continue to update scheduling.

**Keep current Anki order** opens the same folder without changing any option. It does not restore an earlier setting. Use **Undo before answering cards** to reverse a fresh shuffle operation. Later, open **Deck options → Display Order** to change the ordering, or reselect your original preset. The copied preset can remain available; no automatic deletion or forced full sync is introduced.

Filtered decks retain their own selection rules. An unsupported options contract produces a message rather than a replacement scheduler. A late selection error explicitly distinguishes a saved order from a failed write.

## Everything else stays the same

Individual-lecture buttons, Quick study, independent practice and mock sessions, Card Studio, masks, saved work, widgets, sources, keyboard remotes and Onigiri ownership modes retain their existing routes. No exam/source data migration is performed. Original-source and remote-specific protections from 1.0.1 remain.

## Native acceptance checklist

Use a spare profile with at least three lecture subdecks and a second unrelated deck sharing the original parent preset. Confirm Shuffle produces a parent-only preset copy, preserves the other options, and presents eligible cards from across the lectures. Inspect the actual source lecture label. Cancel/open the order dialog without saving and verify no new preset appears. Reopen Shuffle and confirm no repeated copy is created. Test Keep current, Undo before reviewing, a missing/deleted folder, filtered-deck handling, regular reviews, and a learning card due shortly.

Windows desktop Anki 26.08.1 is the inspected API target. The new code has not been executed against the native Rust scheduler or Qt here. macOS remains a controlled trial, not newly certified support. Current browser and native-interface-double tests are described separately in the verification report.

## Recovery

Use Anki's Undo/Deck options for the saved folder order. Disabling Atelier does not reset saved Anki deck options. For presentation conflicts, use **Tools → Atelier → Use original reviewer styling**. Disable the add-on and restart rather than deleting your local data. Keep independent Sprout/Workshop copies disabled while the bundled controllers are running.
