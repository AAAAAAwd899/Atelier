# What Add-on tools supports

Add-on tools reads existing commands in Anki’s Tools menu and added top-level menus. It keeps the original QAction, shortcut, check state, enabled state and handler. It does not import add-ons, invoke menu preparation signals, copy their code, change their settings or install anything. Search stays local. Opening a command is a deliberate native-window action, never an arbitrary JavaScript command identifier.

Ankimon and other companion/reward add-ons can use their own menu commands here when registered through standard Qt menus. Their actual game, media, accounts and widgets remain owned by them. Editor buttons, context menus, dynamically created controls and other embedded surfaces stay in their original windows. If a command is created when its menu opens, open that menu once and Refresh. The index is bounded to 500 commands and eight submenu levels, with an explicit limit notice.

Existing native editing remains the route for specialized note types and editor extensions. Onigiri’s optional provider routing, native widgets, original-theme ownership and original interface recovery are unchanged.

Verification uses actual Windows Anki 26.09.3 and native Qt menu providers created for the test. It checks command identity, single invocation, check-state changes, unchanged shortcuts, disabled ancestors, refresh, collection preservation and lifecycle cleanup. No installed Ankimon, Review Heatmap, Image Occlusion Enhanced or AnkiConnect combination was tested in this pass. Stock native image occlusion is tested separately. This is broader access to standard menu commands, not a universal compatibility certification.

Primary contracts: https://docs.ankiweb.net/addons/hooks-and-filters and https://doc.qt.io/qt-6/qaction.html .
