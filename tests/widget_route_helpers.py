"""Click the real, explicit provider destination, never a private frontend state."""
def open_original_provider(page):
    page.locator('.sidebar .native-link[data-action="widget-page"]').click()
    page.locator('.nw-toolbar [data-action="nw-tools"]').click()
    page.locator('.nw-tools-list [data-action="nw-original"]').click()
