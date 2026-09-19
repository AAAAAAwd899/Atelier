"""Validate that the maintained 1.0.3 audit describes the current runtime.

The audit is intentionally reviewed prose rather than generated marketing copy.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from release_tools import runtime_digest  # noqa: E402


def main() -> None:
    audit = (ROOT / "AUDIT-1.0.3.md").read_text(encoding="utf-8")
    verified = json.loads((ROOT / "verification" / "verified.json").read_text(encoding="utf-8"))
    python_receipt = json.loads((ROOT / "verification" / "python-current.json").read_text(encoding="utf-8"))
    fingerprint = runtime_digest()
    assert verified["version"] == "1.0.3"
    assert verified["runtime_sha256"] == fingerprint
    assert python_receipt["runtime_sha256"] == fingerprint
    assert verified["python_total"] == 1902
    assert verified["browser_total"] == 2628
    assert verified["python_failed"] == 0 and verified["python_skipped"] == 0
    assert verified["browser_errors"] == 0
    for required in (fingerprint, "seventeen worlds", "1,233", "2,628", "1915"):
        assert required in audit, f"audit is missing current evidence: {required}"
    for stale in ("accepted twelve-world catalogue remains unchanged", "WinError 5", "1,836 total"):
        assert stale not in audit, f"audit retains stale evidence: {stale}"
    print("AUDIT-1.0.3.md matches the current verified runtime")


if __name__ == "__main__":
    main()
