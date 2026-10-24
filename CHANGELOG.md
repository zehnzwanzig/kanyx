# Changelog

## [Unreleased]

## [1.0.2] – 2026-10-24

- Harden attachment path validation against traversal and unsafe filesystem paths.
- Make card saves transactional when attachments fail, preventing partial edits.
- Display a warning when an attached file is missing instead of trying to open it.
- Handle case-insensitive duplicate tags without a database constraint error.
- Treat percent (%) and underscore (_) as literal characters in card searches.
- Ask whether to delete or keep attachment files when deleting a card, with a cancel option; localized across 13 languages.
- Add regression and robustness tests for these behaviors.
- No workspace schema migration is required.

## [1.0.1] – 2026-10-23

- Arabic added as the thirteenth interface language (initial translation).
- Localized active-filter and clear-filter controls in the original six languages.
- Added a live left/right insertion guide while reordering columns.
- No data-file format changes.

## [1.0.0] – 2026-10-23

- First stable Windows release, with an experimental Linux build.
- 12 interface languages, clearer collapsed columns and visible active filters.
- Includes RC2 fixes for scaling, drag previews, attachment Save/Cancel, cancelled new-task creation and imported appearance settings.
- Portable Kanban functionality, workspace export/import, backups and integrity checks.
- No workspace schema migration or user-data path change.

## [0.9.0]
- Wallpaper brightness, column opacity and text scaling controls.

## [0.8.0]
- Portable `.kanyx` workspace import/export, integrity checks and manual backups.

## [0.7.2]
- Open existing cards in Markdown preview mode.

## [0.7.1]
- Markdown source preservation, clearer preview state and color swatches.

## [0.7.0]
- Card colors, Markdown preview, checklist progress, templates and shortcuts.

## [0.6.1]
- Checklist editing visibility and translucent drag preview.

## [0.6.0]
- Card archive, duplication, undo/redo and collapsible columns.

## [0.5.0]
- Six UI languages (English default).

## [0.4.0]
- Renamed project Pyban to Kanyx, with legacy database compatibility.

### GitHub publishing preparation (no app-version change)
- Added separate third-party license notices and LGPL/GPL license texts.
- Added portable onedir release scripts and updated GitHub Actions release candidates.
- Added release compliance checklist and updated README.
