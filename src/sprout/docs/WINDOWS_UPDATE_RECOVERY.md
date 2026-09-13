# Exam Sprout 0.10.1 — Windows update recovery

Use **Exam_Sprout_0.10.1.ankiaddon**, the complete replacement installer. Do not
use the UPLOAD_ONLY file from the publication bundle for a local install.

## What the reported traceback means

Anki was replacing `addons21/exam_sprout`. Sending the old folder to the Recycle
Bin failed; its fallback directory removal then reported WinError 32 on
`web/pip/tiny-stage1-idle.webp`. The old Pip animation player used QMovie's
filename path, which can retain an open asset handle during playback/pausing.
The reported active build was 0.9.7; this is an installer failure, not a traceback
from running the newer exam/readiness engine.

Some old add-on files may already have been removed before the error. Do not
continue using that installation until a full installer has completed.
The error names add-on program artwork, not `collection.anki2` or a profile's
Exam Sprout state. It is not evidence of lost cards. This does not certify the
condition of a collection that has not been inspected.

## Safe recovery (no folder deletion normally required)

1. Save the 0.10.1 installer, but do not double-click it into the running old Anki.
2. Quit Anki completely. If it cannot close, end Anki in Task Manager, or restart
   Windows. Do not indiscriminately end unrelated Python applications.
3. Hold **Shift** while starting the Anki application. Keep holding it until the
   safe-mode message appears. This temporarily stops all add-ons from loading.
4. In this safe-mode Anki, use **Tools → Add-ons → Install from file…**, select
   `Exam_Sprout_0.10.1.ankiaddon`, and wait for the installation confirmation.
5. Quit and restart Anki normally. Keep Atelier enabled. Check the add-on list
   or **Tools → Exam Sprout diagnostics…** for **0.10.1**. Re-enable Exam Sprout
   only if you separately disabled it manually; safe mode itself is temporary.

Keep your normal backup. With Anki fully closed, a copy of `%APPDATA%\Anki2`
kept outside the original folder also preserves profile-local Exam Sprout data
which is not part of Anki's ordinary collection-only backups.

The new installer cannot free a file handle held by the already running old code.
The full close + safe-mode first install is necessary even with the repaired file.
Do not run as administrator, disable antivirus, change permissions, reinstall
Anki itself, or delete the Anki2/profile folders for this specific error.

## Only if the safe-mode reinstall still fails

Restart Windows and repeat the safe-mode installation first. If the same
`addons21/exam_sprout` folder remains damaged or locked after Anki has fully
closed, move **only** that exact add-on folder to a clearly named backup folder
on your Desktop, **outside addons21**, then repeat the safe-mode installation.
Do not merely rename it to another name inside addons21: that can create another
loadable add-on copy. If Windows still refuses the move, stop instead of forcing
deletion. Copy the new error details to identify the process or remaining issue.

Do not move/delete an `exam_sprout` folder inside your profile. Plans, results,
written-answer files, drafts and Pip effort are stored there, not in the
`addons21/exam_sprout` program folder. The 0.10.1 package leaves those storage
paths and code unchanged. Do not delete `collection.anki2` or `collection.media`.

## Preventive change in 0.10.1

Pip now reads a bounded animation payload, closes the Python file handle, then
plays those bytes through a retained QBuffer. The movie never receives an asset
filename. Pause/resume reuses the same buffer/frame. On an action change or
cleanup, the decoder detaches before the buffer is cleared. Corrupt/missing assets
fall back to still artwork instead of repeated errors. Animation/artwork and
all study/exam/readiness/scheduling code are unchanged from 0.10.0.

This is a targeted repair, not certification that other programs/add-ons cannot
lock files. Continue to restart Anki after every add-on update. Real Windows
installer and native scheduling acceptance remain release gates.

## Primary documentation

- Anki safe-mode and shutdown recovery: https://docs.ankiweb.net/troubleshooting.html
- Qt 6.9 QMovie device playback: https://doc.qt.io/archives/qt-6.9/qmovie.html
- Qt 6.9 QBuffer ownership and open/close semantics: https://doc.qt.io/qt-6.9/qbuffer.html
