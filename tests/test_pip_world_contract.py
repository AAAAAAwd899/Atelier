"""Static and asset contracts for the themed Pip companion family."""
from pathlib import Path
import hashlib
import json
import struct


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "src/sprout/web/app.js").read_text(encoding="utf8")
CSS = (ROOT / "src/sprout/web/pip.css").read_text(encoding="utf8")
PIP = (ROOT / "src/sprout/web/pip.js").read_text(encoding="utf8")
ATELIER = (ROOT / "src/web/atelier.js").read_text(encoding="utf8")


def test_pip_worlds_keep_shared_growth_and_use_authored_portraits():
    assert "function pipWorld(theme)" in APP
    for kind in ("cutesy", "green", "water", "orbit", "ember", "linen"):
        assert f"kind:'{kind}'" in APP
        assert f"pip-world-{kind}" in CSS
        asset = ROOT / f"src/sprout/web/pip/companion-{kind}-1.0.3.png"
        data = asset.read_bytes()
        assert data.startswith(b"\x89PNG\r\n\x1a\n")
        assert struct.unpack(">II", data[16:24]) == (512, 512)
    assert "pipWorldMark(world.kind)" in APP
    assert "data-pip-portrait" in APP and "companion-${world.kind}-1.0.3.png" in APP
    assert "Illustrated companion · Local only" in PIP
    assert "s.portrait" in PIP and "pip-portrait-greet" in CSS
    assert "data-pip-stage" in APP and "data-pip-animate" in APP
    assert "function pipStageLabel(kind, stage)" in APP
    assert 'class="es-pip-stage-label"' in APP
    assert "growth.label" not in APP
    assert "data-pip-action=\"pet\"" in APP and "data-pip-action=\"water\"" in APP
    for label in ("Curious", "Canopy", "Horizon", "Constellation", "Hearth", "Archive"):
        assert label in APP


def test_exam_picker_explains_multiple_parent_folders():
    assert "combine parents for one exam" in ATELIER
    assert "overlapping branches count once" in ATELIER
    assert "Select every parent folder or deck" in ATELIER


def test_focus_desk_has_direct_pip_entry_and_clear_first_step():
    assert "focus-pip" in ATELIER
    assert "Study with Pip" in ATELIER
    assert "Set your focus" in ATELIER
    assert "parent ${(e.deck_ids?.length||0)===1?'folder':'folders'} / decks" in ATELIER


def test_companion_portrait_provenance_matches_packaged_bytes():
    records = json.loads((ROOT / "ASSET-PROVENANCE-1.0.3.json").read_text(encoding="utf8"))
    companions = {row["file"]: row for row in records if "/pip/companion-" in row["file"]}
    assert len(companions) == 6
    for relative, record in companions.items():
        payload = (ROOT / relative).read_bytes()
        assert record["bytes"] == len(payload)
        assert record["sha256"] == hashlib.sha256(payload).hexdigest()
        assert "OpenAI image generation" in record["origin"]


def test_live_world_switch_updates_companion_without_rerendering_form():
    worlds = (ROOT / "src/web/worlds.js").read_text(encoding="utf8")
    update = APP.split("function updateCompanionWorld(theme)", 1)[1].split("function pipWorldMark", 1)[0]
    assert "suiteWorld(theme)" in APP
    assert "window.ExamSprout.suiteWorld?.(saved.theme)" in worlds
    assert "card.dataset.pipPortrait=portrait" in update
    assert "window.PipCompanion?.mount?.()" in update
    assert "render()" not in update
