"""Static contract for the themed Pip companion treatment."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "src/sprout/web/app.js").read_text(encoding="utf8")
CSS = (ROOT / "src/sprout/web/pip.css").read_text(encoding="utf8")
ATELIER = (ROOT / "src/web/atelier.js").read_text(encoding="utf8")


def test_pip_worlds_keep_shared_growth_and_add_authored_marks():
    assert "function pipWorld(theme)" in APP
    for kind in ("cutesy", "green", "water", "orbit", "ember", "linen"):
        assert f"kind:'{kind}'" in APP
        assert f"pip-world-{kind}" in CSS
    assert "pipWorldMark(world.kind)" in APP
    assert "data-pip-stage" in APP and "data-pip-animate" in APP
    assert "data-pip-action=\"pet\"" in APP and "data-pip-action=\"water\"" in APP


def test_exam_picker_explains_multiple_parent_folders():
    assert "combine parents for one exam" in ATELIER
    assert "overlapping branches count once" in ATELIER
    assert "Select the two parent folders" in ATELIER


def test_focus_desk_has_direct_pip_entry_and_clear_first_step():
    assert "focus-pip" in ATELIER
    assert "Study with Pip" in ATELIER
    assert "Set your focus" in ATELIER
    assert "parent ${(e.deck_ids?.length||0)===1?'folder':'folders'} / decks" in ATELIER
