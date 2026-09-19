"""Capture the final 1.0.3 fullscreen and responsive Home evidence.

This uses fictional fixture data and Chromium. It is not native Anki evidence.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "playwright" / "current-art"
URL = "http://127.0.0.1:8765/output/playwright/current-art/sunset-beach-home-final.html"


def browser_path() -> str:
    configured = os.environ.get("ATELIER_TEST_BROWSER")
    if configured:
        return configured
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    candidates = sorted(root.glob("chromium-*/chrome-win64/chrome.exe"), reverse=True)
    if not candidates:
        raise RuntimeError("No Playwright Chromium installation found")
    return str(candidates[0])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    evidence: list[dict[str, object]] = []
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=browser_path())
        for width, height, name in (
            (1915, 1000, "sunset-beach-home-fullscreen-1915x1000.png"),
            (1280, 800, "sunset-beach-home-final-1280x800.png"),
            (390, 720, "sunset-beach-home-final-390x720.png"),
        ):
            page = browser.new_page(viewport={"width": width, "height": height})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(URL, wait_until="load")
            page.locator("#atelier-root").wait_for()
            page.wait_for_function("document.querySelector('#atelier-root')?.shadowRoot?.querySelector('.layout')")
            page.wait_for_timeout(250)
            metrics = page.evaluate(
                """() => {
                  const host=document.querySelector('#atelier-root');
                  const shadow=host.shadowRoot;
                  const layout=shadow.querySelector('.layout');
                  const main=shadow.querySelector('.main');
                  const active=shadow.querySelector('.nav-row.active');
                  return {
                    viewport: innerWidth,
                    documentWidth: document.documentElement.scrollWidth,
                    host: host.getBoundingClientRect().toJSON(),
                    layout: layout.getBoundingClientRect().toJSON(),
                    mainScrollWidth: main.scrollWidth,
                    mainClientWidth: main.clientWidth,
                    activeNavWidth: active?.getBoundingClientRect().width || 0,
                  };
                }"""
            )
            page.screenshot(path=str(OUT / name), animations="disabled")
            evidence.append({"file": name, "viewport": [width, height], "metrics": metrics})
            page.close()
        browser.close()
    report = {
        "version": "1.0.3",
        "source": "current shipping source rendered with fictional browser fixture data",
        "native_anki": False,
        "captures": evidence,
        "page_errors": errors,
    }
    (OUT / "final-responsive-evidence.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)
    for capture in evidence:
        metrics = capture["metrics"]
        if metrics["host"]["width"] != capture["viewport"][0] or metrics["layout"]["width"] != capture["viewport"][0]:
            raise SystemExit("Atelier shell does not fill the viewport")
        if metrics["mainScrollWidth"] != metrics["mainClientWidth"]:
            raise SystemExit("Horizontal overflow detected in Atelier main surface")


if __name__ == "__main__":
    main()
