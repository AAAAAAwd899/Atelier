"""Build the current-runtime review bundle without stale native captures."""
from __future__ import annotations

import datetime
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from release_tools import runtime_digest, write_archive  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    dist = ROOT / "dist"
    fingerprint = runtime_digest()
    verified = json.loads((ROOT / "verification/verified.json").read_text(encoding="utf8"))
    native = json.loads((ROOT / "verification/native-install-current.json").read_text(encoding="utf8"))
    companion = json.loads((ROOT / "output/playwright/companion-family/results.json").read_text(encoding="utf8"))
    matrix_paths = {
        "core": ROOT / "output/playwright/final-matrix/results.json",
        "home-workflows": ROOT / "output/playwright/final-home-workflows/results.json",
        "planner": ROOT / "output/playwright/final-planner/results.json",
        "card": ROOT / "output/playwright/final-card/results.json",
    }
    matrices = {name: json.loads(path.read_text(encoding="utf8")) for name, path in matrix_paths.items()}
    world_receipt = json.loads((ROOT / "verification/world-suite/results.json").read_text(encoding="utf8"))
    installer = dist / "Atelier-1.0.3.ankiaddon"
    source = dist / "Atelier-1.0.3-Source.zip"
    build = dist / "Atelier-1.0.3-Build.json"
    files = dist / "Atelier-1.0.3-Files.json"

    assert verified["runtime_sha256"] == native["runtime_sha256"] == companion["runtime_sha256"] == fingerprint
    assert verified["python_total"] == 1902 and verified["browser_total"] == 2656
    assert verified["python_failed"] == verified["python_skipped"] == verified["browser_errors"] == 0
    assert world_receipt["count"] == verified["browser_suites"]["world-suite"] == 175
    assert not world_receipt["errors"] and not native["errors"] and all(native["checks"].values())
    assert native["installer_sha256"] == sha(installer)
    assert len(companion["records"]) == 6 and not companion["errors"]
    assert all(row["renderer"] == "portrait" for row in companion["records"])
    assert all(min(row["contrast"][key] for key in ("bodyRatio", "strongRatio", "labelRatio")) >= 4.5 for row in companion["records"])

    expected_matrix_counts = {"core": 510, "home-workflows": 255, "planner": 340, "card": 170}
    overflow_keys = ("horizontal_overflow", "page_overflow")
    for name, receipt in matrices.items():
        assert receipt["runtime_sha256"] == fingerprint
        assert len(receipt["records"]) == expected_matrix_counts[name]
        assert not receipt["errors"]
        assert all(not any(row.get(key, False) for key in overflow_keys) for row in receipt["records"])
    matrix_render_count = sum(len(receipt["records"]) for receipt in matrices.values())
    assert matrix_render_count == 1275

    archive_files: list[tuple[Path, str]] = []
    manifest: list[dict[str, object]] = []
    matrix_folders = {
        "core": ROOT / "output/playwright/final-matrix",
        "home-workflows": ROOT / "output/playwright/final-home-workflows",
        "planner": ROOT / "output/playwright/final-planner",
        "card": ROOT / "output/playwright/final-card",
    }
    selected_matrix_count = 0
    for name, receipt in matrices.items():
        for row in receipt["records"]:
            if row["viewport"] not in ([1440, 900], [390, 720]):
                continue
            path = matrix_folders[name] / row["file"]
            assert path.is_file() and sha(path) == row["sha256"]
            relative = f"screens/{name}/{path.name}"
            archive_files.append((path, "Atelier-1.0.3-Screenshots/" + relative))
            manifest.append({
                "file": relative,
                "sha256": row["sha256"],
                "bytes": path.stat().st_size,
                "category": "current shipped interface; fictional data",
                "world": row["world"],
                "screen": row["screen"],
                "viewport": row["viewport"],
            })
            selected_matrix_count += 1
    assert selected_matrix_count == 510

    review_boards = sorted((ROOT / "output/playwright/visual-review-boards").glob("*.png"))
    assert len(review_boards) == 5
    for path in review_boards:
        relative = f"review-boards/{path.name}"
        archive_files.append((path, "Atelier-1.0.3-Screenshots/" + relative))
        manifest.append({"file": relative, "sha256": sha(path), "bytes": path.stat().st_size, "category": "all-screen visual inspection board"})
    companion_folder = ROOT / "output/playwright/companion-family"
    for row in companion["records"]:
        path = companion_folder / row["file"]
        assert sha(path) == row["sha256"]
        relative = f"companions/{path.name}"
        archive_files.append((path, "Atelier-1.0.3-Screenshots/" + relative))
        manifest.append({"file": relative, "sha256": row["sha256"], "bytes": path.stat().st_size, "category": "current shipped companion panel; fictional data", "contrast": row["contrast"]})

    onigiri_folder = ROOT / "screenshots/widget-routing"
    for name, viewport in (
        ("embedded-onigiri-home-1440.png", [1440, 950]),
        ("embedded-onigiri-panel-1440.png", [1144, 830]),
        ("embedded-onigiri-home-390.png", [390, 760]),
    ):
        path = onigiri_folder / name
        assert path.is_file()
        relative = f"onigiri-integration/{name}"
        archive_files.append((path, "Atelier-1.0.3-Screenshots/" + relative))
        manifest.append({
            "file": relative,
            "sha256": sha(path),
            "bytes": path.stat().st_size,
            "category": "live-subtree Onigiri integration; provider-shaped fictional browser fixture",
            "viewport": viewport,
        })

    receipt_files = [
        (ROOT / "verification/world-suite/results.json", "receipts/world-suite.json"),
        (ROOT / "output/playwright/companion-family/results.json", "receipts/companion-family.json"),
        (ROOT / "verification/native-install-current.json", "receipts/native-install-current.json"),
        (ROOT / "verification/verified.json", "receipts/verified.json"),
    ]
    receipt_files.extend((path, f"receipts/{name}.json") for name, path in matrix_paths.items())
    for path, relative in receipt_files:
        archive_files.append((path, "Atelier-1.0.3-Screenshots/" + relative))

    screenshot_manifest = dist / ".Atelier-1.0.3-Screenshot-Manifest.json"
    screenshot_manifest.write_text(json.dumps({
        "version": "1.0.3",
        "runtime_sha256": fingerprint,
        "browser_world_checks": 175,
        "visual_matrix_renders": matrix_render_count,
        "visual_matrix_errors": 0,
        "visual_matrix_overflow_failures": 0,
        "selected_desktop_and_phone_renders": selected_matrix_count,
        "screenshots": manifest,
        "limitations": "Browser renders use fictional data. Native installer evidence uses a disposable profile and has no screenshots. Earlier native visual captures are historical and excluded from this current bundle.",
    }, indent=2) + "\n", encoding="utf8")
    archive_files.append((screenshot_manifest, "Atelier-1.0.3-Screenshots/manifest.json"))
    screenshot_zip = dist / "Atelier-1.0.3-Screenshots.zip"
    try:
        write_archive(screenshot_zip, archive_files)
    finally:
        screenshot_manifest.unlink(missing_ok=True)
    with zipfile.ZipFile(screenshot_zip) as archive:
        assert not archive.testzip() and len(archive.namelist()) == len(archive_files)

    delivery = {
        "name": "Atelier",
        "version": "1.0.3",
        "runtime_sha256": fingerprint,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "automated": verified,
        "native_installer": native,
        "screenshots": {
            "count": len(manifest),
            "sha256": sha(screenshot_zip),
            "companion_count": 6,
            "onigiri_integration_count": 3,
            "review_board_count": len(review_boards),
            "selected_interface_count": selected_matrix_count,
            "full_matrix_render_count": matrix_render_count,
            "full_matrix_errors": 0,
            "full_matrix_overflow_failures": 0,
        },
        "publicly_published": False,
        "owner_accepted": False,
        "limits": "See AUDIT-1.0.3.md. Browser screenshots use fictional data; the AddonManager check used a disposable Anki profile. macOS, physical remotes, full native scaling, live GPU Pip, and uncoached-user acceptance remain unverified.",
    }
    verification = dist / "Atelier-1.0.3-Verification.json"
    verification.write_text(json.dumps(delivery, indent=2) + "\n", encoding="utf8")
    checksum = dist / "Atelier-1.0.3-Delivery-SHA256.txt"
    deliverables = [installer, source, screenshot_zip, verification, build, files]
    checksum.write_text("".join(f"{sha(path)}  {path.name}\n" for path in deliverables), encoding="utf8")
    print(json.dumps({"runtime_sha256": fingerprint, "screenshots": len(manifest), "screenshots_sha256": sha(screenshot_zip), "verification_sha256": sha(verification)}, indent=2))


if __name__ == "__main__":
    main()
