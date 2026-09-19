"""Render the six shipped world-companion families with fictional planner data."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from playwright.sync_api import sync_playwright  # noqa: E402
import planner_suite_fixture as fixture  # noqa: E402
from release_tools import runtime_digest  # noqa: E402


REPRESENTATIVES = {
    "cutesy": "rose",
    "green": "forest",
    "water": "tidal",
    "orbit": "midnight",
    "ember": "ember",
    "linen": "linen",
}


def current_html(world: str) -> str:
    """Assemble the current packaged planner around the synthetic native bridge."""
    fixture.ACTIVE_THEME = world
    web = ROOT / "src" / "sprout" / "web"
    config = fixture.core.settings(
        {
            "visual_owner": "atelier",
            "theme": world,
            "ambience": True,
            "match_sprout": True,
            "motion": False,
        }
    )
    css = "\n".join(
        (web / name).read_text(encoding="utf8")
        for name in ("app.css", "countdown.css", "pip.css")
    )
    scripts = ";\n".join(
        (web / name).read_text(encoding="utf8")
        for name in ("countdown.js", "pip-scene.js", "pip.js", "app.js")
    )
    head = fixture.worlds.planner_head(config, "daedalus_atelier")
    head += '<style id="atelier-sprout-tokens">' + fixture.link.tokens_css(config) + "</style>"
    head += '<style id="atelier-sprout-css">' + (ROOT / "src/web/sprout.css").read_text(encoding="utf8") + "</style>"
    head += '<script>document.documentElement.dataset.atelierSprout="true";</script>'
    return (
        '<!doctype html><html lang="en"><head><base href="http://sprout.test/">'
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        + head
        + "<style>"
        + css
        + "</style></head><body><main id=\"es-app\"></main>"
        '<script>window.pycmd=m=>window.fixtureCommand(JSON.parse(m.slice(12))).then(window.ExamSprout.receive);</script><script>'
        + scripts
        + "</script></body></html>"
    )


def main() -> None:
    out = ROOT / "output" / "playwright" / "companion-family"
    out.mkdir(parents=True, exist_ok=True)
    fingerprint = runtime_digest()
    records: list[dict[str, object]] = []
    errors: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get("ATELIER_TEST_BROWSER"))
        for family, world in REPRESENTATIVES.items():
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "requestfailed",
                lambda request: errors.append(
                    f"request failed: {request.url} · {request.failure}"
                ),
            )
            fixture.expose(page)
            page.set_content(current_html(world))
            card = page.locator(".es-companion-panel")
            card.wait_for()
            page.evaluate(
                "world => { ExamSprout.suiteWorld(world); AtelierWorlds.configure({theme:world}); }",
                world,
            )
            portrait = page.locator(".pip-image")
            portrait.wait_for()
            page.wait_for_timeout(500)
            dimensions = portrait.evaluate("image => [image.naturalWidth, image.naturalHeight]")
            assert dimensions == [512, 512], (
                world,
                portrait.get_attribute("src"),
                dimensions,
                errors,
            )
            target = out / f"{family}-{world}.png"
            card.screenshot(path=str(target), animations="disabled")
            contrast = page.evaluate("""() => {
              const rgb=value=>value.startsWith('#')?[1,3,5].map(index=>parseInt(value.slice(index,index+2),16)):value.match(/[.\d]+/g).slice(0,3).map(Number),lum=value=>{
                const values=rgb(value).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;});
                return values[0]*.2126+values[1]*.7152+values[2]*.0722;
              },ratio=(a,b)=>{a=lum(a);b=lum(b);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);};
              const panel=document.querySelector('.es-pip-progress'),body=panel.querySelector('p'),strong=body.querySelector('strong'),label=panel.querySelector('.es-pip-stage-label'),root=getComputedStyle(document.documentElement);
              const backgrounds=[root.getPropertyValue('--ats-panel').trim(),root.getPropertyValue('--ats-side').trim()],bodyColor=getComputedStyle(body).color,strongColor=getComputedStyle(strong).color,labelColor=getComputedStyle(label).color,worst=color=>Math.min(...backgrounds.map(background=>ratio(color,background)));
              return {backgrounds,body:bodyColor,strong:strongColor,label:labelColor,bodyRatio:worst(bodyColor),strongRatio:worst(strongColor),labelRatio:worst(labelColor)};
            }""")
            records.append(
                {
                    "family": family,
                    "world": world,
                    "file": target.name,
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                    "portrait": portrait.get_attribute("src"),
                    "label": page.locator(".pip-world-label").inner_text(),
                    "stages": page.locator(".es-growth-steps span").all_inner_texts(),
                    "renderer": page.locator(".pip-card").get_attribute("data-pip-renderer"),
                    "contrast": contrast,
                }
            )
            page.close()
        browser.close()
    assert not errors, errors
    assert runtime_digest() == fingerprint, "Runtime changed during capture"
    assert len(records) == len(REPRESENTATIVES)
    assert all(record["renderer"] == "portrait" for record in records)
    assert all(min(record["contrast"][key] for key in ("bodyRatio", "strongRatio", "labelRatio")) >= 4.5 for record in records), records
    (out / "results.json").write_text(
        json.dumps(
            {
                "category": "shipped Exam Studio UI; fictional planner data",
                "runtime_sha256": fingerprint,
                "records": records,
                "errors": errors,
            },
            indent=2,
        )
        + "\n",
        encoding="utf8",
    )
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
