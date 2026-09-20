# Atelier native home widgets — API 1

Atelier 0.9.0-rc6 renders Widgets in its own Anki DeckBrowser webview. No Onigiri install or DOM is needed. Built-in widgets are ready to use. A third-party widget is opt-in and must be supplied by an already installed, trusted Anki add-on.

This is **not** an arbitrary HTML/URL importer, an iframe portal, an add-on installer, or a security sandbox. Shadow DOM isolates CSS, not authority. Installed Python/JavaScript add-ons are trusted code and retain their normal permissions. Only install providers you trust. Atelier does not automatically send widget information over the network.

## Register a widget

Use Anki's `gui_hooks.webview_will_set_content` and `setWebExports` to supply your own script to DeckBrowser documents. Scope injection to `aqt.deckbrowser.DeckBrowser`. Do not put the script in card templates or the reviewer. Runtime paths must use the actual provider package ID from Anki; never hard-code a numeric ID.

Anki's official webview hook documentation: https://addon-docs.ankiweb.net/hooks-and-filters.html

Your script must support either load order:

```javascript
(() => {
  let registered = false;
  function register() {
    const host = window.AtelierWidgets;
    if (registered || !host || host.apiVersion !== 1) return;
    registered = true;
    host.register({
      id: 'addon.my_provider.status',
      title: 'My status',
      description: 'A status panel from an installed add-on.',
      mount(container, context) {
        // Use textContent for untrusted data. Registration alone does not mount.
        const message = document.createElement('p');
        message.textContent = 'Your provider is connected.';
        container.append(message);
        let disposed = false;
        // Async work may be started here. Do not return a Promise.
        // Guard late responses with disposed and use AbortController when possible.
        return () => {
          disposed = true;
          // Abort requests and remove timers/subscriptions/listeners here.
        };
      },
      theme(container, context) {
        container.style.color = context.tokens.text;
        // Presentation only: do not recreate inputs or restart business logic.
      }
    });
  }
  register();
  window.addEventListener('atelier:widgets-ready', register, {once:true});
})();
```

`register()` returns an unregister function. IDs use `addon.` followed by lowercase letters, numbers, dots, underscores or hyphens; duplicate IDs and more than 32 registrations are rejected. Titles and descriptions are bounded. Registration makes the widget available in Arrange widgets; it **does not run its mount function** until the user adds it to a displayed page.

`mount(container, context)` receives a fresh container inside a provider-specific ShadowRoot. Return a cleanup function synchronously. A thrown mount error is contained in the widget and does not replace the home. Do not rely on the container remaining mounted through page navigation or layout saves. Persist your provider's own state through your own safe storage, not by querying Atelier's private controller.

`context` is a frozen object with `surface` (`widgets` or `study-desk`), `owner`, `theme`, and a copied/frozen `tokens` object. The theme is the selected world in Atelier mode and `original` in passive-owner companion mode. Use the supplied tokens for effective colors rather than assuming a palette from a saved name. Available tokens are bg, panel, raised, text, muted, accent, line and scheme. CSS custom properties inherit from the home as well. Changes in Atelier's theme call `theme` without remounting the input. A newly registered unrelated provider does not replace existing widget inputs.

Atelier cleans up mounts on page redraw/navigation, removal/unregistration and pagehide. Providers own their asynchronous work and cleanup. Do not use global selectors to recolor the home, hijack Anki's pycmd dispatcher, bypass approval, or write scheduling information through a display widget.

## Preferences and unavailable providers

Users add/remove/reorder each widget, choose Normal/Wide, and optionally Show on Study desk. These edits save in one profile-local layout through the existing Atelier preference store. Removing a widget does not call provider delete-data actions. Temporarily unavailable `addon.*` IDs retain their saved placements and show an unavailable state, so disabling a provider does not erase the user's choices.

The built-in My note is plain text saved explicitly, limited to 4,000 characters; deleting its widget leaves the saved text. It is not an HTML or code surface. Local notes/layout are not part of Anki's collection sync.

## Verification boundary

The included browser suite covers both registration-before-enabling and registration after the home loads; opt-in mount, duplicate rejection, isolated failure, cleanup, nested input shortcuts, theme/input preservation, late-provider registration, and absent-provider layout retention. It uses a local fixture provider, not every third-party add-on. Native Windows Anki and your actual provider require acceptance testing. Onigiri is handled as a live Home subtree rather than converted into this API: Atelier moves the one intact provider wrapper into a named Study-desk slot and restores its original parent for compatibility mode.
