# Anki desktop add-on review — 1.0.5

Reviewed 2026-10-19 against the current official documentation and AnkiWeb terms. This is technical and source-license evidence, not an Anki/AnkiWeb endorsement or a legal opinion.

Atelier is a desktop Python add-on loaded from `__init__.py`. Its root-level `.ankiaddon` ZIP includes `manifest.json`, a stable private package identity, version, name and conflicts with the separately installed bundled engines. Python caches, profile databases, private `meta.json`, credentials and saved user work are excluded. The manifest now declares the supported minimum host, Anki 25.09.5; this is a minimum requirement, not proof of every future host.

The runtime uses Anki hooks, scoped webview assets and its context/nonce-restricted bridge. The tour uses that existing path and writes only a validated profile-local onboarding marker. Original Anki editor, import/export and scheduling operations remain native; the tour never invokes them merely to highlight a button. Other appearance owners do not receive an automatic tour. No AnkiWeb login, sync client, scraping or automatic upload implementation was added. Shared-deck links open through the normal browser/native tools.

Atelier, Sprout and Workshop retain their permissive MIT/Expat-style notices; the bundled pypdf parser retains its BSD notice. AnkiWeb requires AGPL3 or a compatible license. GNU identifies the Expat and modified BSD families as GPL-compatible and its compatibility FAQ applies the GPLv3 matrix to AGPLv3. This supports the packaging/license approach; it does not establish rights to unreviewed user decks, Anki branding, third-party add-ons or exclusive rights in generated scenery. Existing provenance and professional-review limits remain in force. Anki/Qt/Onigiri binaries and user data are not bundled.

The `tools/check_anki_addon.py` gate checks the actual installer. Actual native install/tour evidence, with exact host and limitations, is recorded separately after execution. Public AnkiWeb account eligibility, upload acceptance, listing ID, final listing text, identity migration and public website approval remain pending. A private package being installable does not create AnkiWeb automatic updates.

Sources checked:

- [Official sharing format](https://github.com/ankitects/anki/blob/main/docs-site/addons/sharing.mdx)
- [Official hooks and webview guidance](https://github.com/ankitects/anki/blob/main/docs-site/addons/hooks-and-filters.mdx)
- [AnkiWeb terms, rendered in a browser](https://ankiweb.net/account/terms)
- [GNU compatible license list](https://www.gnu.org/licenses/license-list.en.html#Expat)
- [GNU compatibility FAQ](https://www.gnu.org/licenses/gpl-faq.en.html#AllCompatibility)
- [Current stable Anki 26.09.3 release](https://github.com/ankitects/anki/releases/tag/26.09.3)
- [Anki 26.09 removed-API notice](https://github.com/ankitects/anki/releases/tag/26.09)

The dependency audit found that the old namespaced pypdf 5.9.0 predated published resource-exhaustion fixes. Version 1.0.5 ships official pypdf 6.21.1 with retained BSD and embedded Adobe metrics notices. Relative imports are the only upstream adjustments; modified files carry an adjustment note. The lock records exact upstream and shipped hashes. Tests verify namespace isolation, PDF text/page order and bounded decompression. See [upstream advisory](https://github.com/py-pdf/pypdf/security/advisories/GHSA-g9cg-prrw-2r8q) and [official release](https://pypi.org/project/pypdf/6.21.1/). This is a scoped remediation, not a guarantee that every untrusted PDF is safe.

Classification: local desktop extension with private development/testing (I/J), local collection/source data and optional explicitly configured provider assistance (H when used). No account, payments, hosted database, SEO route or public API was added. The shared `projects/atelier/AUDIT.md` names a different older browser-local editor path; it is not release authority for this Anki package. The version-matched local audit and receipts govern this build.
