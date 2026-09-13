"""Atelier: one reversible runtime, no partial hook registration on failure."""
import logging

try:
    from .integration import install
    _atelier = install(__name__)
except Exception as exc:
    logging.getLogger("atelier").exception("Atelier did not start; its startup registrations were rolled back")
    # A delayed, plain-text message avoids hiding the failure while allowing
    # the host to finish opening. The add-on never publishes/uploads anything.
    try:
        from aqt import mw
        from aqt.utils import showInfo
        from .lifecycle import StartupBlocked
        reason = str(exc) if isinstance(exc, StartupBlocked) else "Atelier could not finish starting. Its startup registrations were rolled back. Disable Atelier and restart if needed; your card collection has not been changed."
        mw.progress.single_shot(1500, lambda message=reason: showInfo(message, textFormat="plain"))
    except Exception:
        pass
