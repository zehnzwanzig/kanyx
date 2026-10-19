# Kanyx 1.0.0-rc.1 — Windows feedback and regression retest

**Status:** candidate patch, not yet validated on a real Windows desktop.

The changes in this patch affect the **shared UI code**, so Linux must also be tested before its release is considered stable. Do not replace the existing `v1.0.0-rc.1` binary or tag in place.

## Before testing

- Extract a **new** Windows build (created from the fixed source) to a **separate writable directory**. Do not run tests in your existing personal workspace.
- Create a full `.kanyx` workspace export and keep it outside the application directory before testing imports or updates.
- Record OS version, Windows display scaling, Kanyx interface scaling, screen resolution, path and whether the test is on USB.
- After merging the patch into `main` and passing CI, build a **new release candidate**, for example `v1.0.0-rc.2`. The existing `rc.1` downloads contain the old behavior.

## Focused Windows retest

- [ ] **W04-P1 – Narrow window:** At 100%, 120% and 140% Kanyx interface scale, shrink the main window to its minimum size. Toolbar buttons remain readable via a *horizontal toolbar scroll*, and the separate search/filter row remains usable. The buttons must not overlap.
- [ ] **W05-P1 – Windows DPI scaling:** Repeat at Windows display scaling 100%, 125% and 150%, with a narrow window. Open a task containing many checklist entries/attachments and confirm the dialog can scroll while Save and Cancel remain visible.
- [ ] **Column drag ghost:** Drag a full column by its grip. A translucent preview of the **column** follows the pointer. Drop it before/after another column; order persists after reopening Kanyx.
- [ ] **Remove attachment + Cancel:** Attach a disposable test file to an existing card and save. Reopen, select the attachment, choose Remove attachment, then Cancel. The attachment, its on-disk copy and the database reference must all remain.
- [ ] **Remove attachment + Save:** Repeat, but choose Save. The attachment disappears and the Kanyx-managed file is deleted. The external source file is unaffected.
- [ ] **Attach file + Cancel:** Add a new attachment in the editor and Cancel. No new attachment record or copied file should exist in `data/attachments/`.
- [ ] **Attach file + Save:** Add a file and Save. The file appears in the card and remains available after restarting Kanyx.
- [ ] **Create task + Cancel:** Click Add task, provide a title, then Cancel in the detailed editor. Neither the new task nor copied attachments may remain in the workspace or after restarting Kanyx.
- [ ] **Create task + Save:** Repeat but save the editor. Title, checklist, tags and attachments persist after restart.
- [ ] **Workspace appearance import:** Export a disposable workspace configured at e.g. 135% UI scale and 60% column opacity. Import it into a separate test installation with different appearance values. Confirm UI scale/opacity update **immediately** on import, without opening Appearance.
- [ ] **Appearance Cancel:** After changing an appearance slider temporarily, Cancel must restore the original imported values.
- [ ] **Data integrity:** Run Workspace > Check data integrity and confirm the expected success result after attachment operations.

## Observations, not currently classified as regressions

- **Moving Kanyx to USB:** A first attempt was blocked by a Windows file lock, and succeeded after closing Python Install Manager. There is not yet evidence that Kanyx itself causes the lock. If it recurs, close Kanyx completely and look for the locking handle in Windows Resource Monitor (`resmon.exe` > CPU > Associated Handles) or Process Explorer; record the process name and the exact file. Do not move a running application folder or its database.
- **SmartScreen:** No warning appeared. This is normal: SmartScreen warnings depend on reputation, download method, and local security state; they are **not** required to appear on every unsigned build.

## Failure report format

| Test | OS / DPI / UI scale | Actual result | Expected result | Status (PASS / FAIL / BLOCKED) | Issue |
|---|---|---|---|---|---|
| W04-P1 | | | No overlapping controls | | |
| W05-P1 | | | All controls reachable | | |
| Column drag | | | Transparent ghost | | |
| Attachment Cancel | | | No persistent changes | | |
| New task Cancel | | | No task created | | |
| Import appearance | | | Immediate style update | | |

When a test fails, please submit an issue at https://github.com/zehnzwanzig/kanyx/issues/new/choose with the reproduction steps. Avoid uploading personal workspace data or private attachments.
