"""Capture the unpublished local information page; never deploys it."""
from pathlib import Path
import hashlib, json, os
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
OUT = ROOT / "output" / "site-preview"
OUT.mkdir(parents=True, exist_ok=True)
records = []
errors = []

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=os.environ.get("ATELIER_TEST_BROWSER"))
    try:
        for width, height in ((1440, 900), (390, 720)):
            page = browser.new_page(viewport={"width": width, "height": height})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto((SITE / "index.html").as_uri(), wait_until="networkidle")
            page.wait_for_function("Array.from(document.images).every(image => image.complete && image.naturalWidth > 0)")
            name = f"site-polished-{width}x{height}.png"
            target = OUT / name
            page.screenshot(path=str(target), full_page=True, animations="disabled")
            records.append({
                "file": name,
                "viewport": [width, height],
                "horizontal_overflow": page.evaluate("document.documentElement.scrollWidth > innerWidth + 2"),
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "images_loaded": page.evaluate("Array.from(document.images).every(image => image.complete && image.naturalWidth > 0)"),
            })
            page.close()
    finally:
        browser.close()

html = (SITE / "index.html").read_text(encoding="utf8")
checks = {
    "private_status": "Private 1.0.3 candidate" in html,
    "no_ankiweb_id": "No public download or AnkiWeb code is active yet" in html,
    "no_public_download": "download=\"" not in html.lower(),
    "no_website_destination": "Prepared for review, held for approval" in html,
    "owner_release_not_approved": "held for approval" in html,
    "noindex": "noindex,nofollow" in html,
    "real_images_present": "atelier-card-studio.png" in html,
    "all_images_loaded": all(row["images_loaded"] for row in records),
    "no_horizontal_overflow": not any(row["horizontal_overflow"] for row in records),
}
source_files = [SITE / "index.html", SITE / "style.css", SITE / "release-info.json", SITE / "assets" / "atelier-card-studio.png"]
result = {
    "category": "unpublished local add-on information page; real Atelier screenshots with synthetic data",
    "records": records,
    "errors": errors,
    "checks": checks,
    "source_sha256": {str(path.relative_to(SITE)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files},
}
(OUT / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
assert not errors and all(checks.values())
