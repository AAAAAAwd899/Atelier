# Atelier 1.0.14 audit

Presentation-only world chooser update from packaged 1.0.13. Existing artwork is byte-preserved; scene layers use inherited packaged art and per-world palette tokens. Motion is finite and contained, with unchanged button, label and dialog geometry. No engine, saved-data, provider, widget or scheduling logic changes; runtime version declarations are incremented.

Use verification/verified.json for the complete current-runtime local gate, verification/themes-114/results.json for actual transform/lighting samples, selection saving, all seventeen worlds, stable bounds, finite settling, keyboard, reduced-motion and motion-off checks. Browser captures/video show shipped UI with synthetic data. Separately labelled actual Anki/Onigiri tests use an isolated Qt-offscreen profile and do not certify physical desktop displays or every add-on combination.

Hosted Linux CI is recorded separately. The prior Ubuntu 320px library containment assertion remains a known limitation; local Windows regression results do not certify Linux support. No AnkiWeb listing, public binary or website publication is performed. The previous listing draft needs refresh and exact final approval before future upload.
