"""Whole-folder order using Anki's native deck-option transaction.

No card/queue rewriting, filtered deck, event interception, or transient preset.
The explicit confirmation saves display order for ONE parent deck. A shared
preset is copied before the change, never changed for unrelated decks.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .core import ValidationError, deck_id

ORDER_FIELDS = ("new_card_gather_priority", "new_card_sort_order", "review_order")
GLOBAL_FIELDS = (
    "card_state_customizer", "new_cards_ignore_review_limit", "fsrs",
    "apply_all_parent_limits", "fsrs_health_check",
)


def validate_folder(col: Any, value: Any, expected: Any) -> int:
    did = int(deck_id(value))
    if not isinstance(expected, str) or not expected:
        raise ValidationError("Refresh the library, then choose the folder again.")
    deck = col.decks.get(did, default=False)
    if not deck or deck.get("name") != expected:
        raise ValidationError("That folder changed. Refresh the library and choose it again.")
    prefix = expected + "::"
    if not any(x.name.startswith(prefix) for x in col.decks.all_names_and_ids()):
        raise ValidationError("Choose a folder containing lecture decks. Use Study deck for an individual lecture.")
    return did


def _native_types() -> Any:
    try:
        from anki import deck_config_pb2
        return deck_config_pb2
    except (ImportError, AttributeError) as exc:
        raise ValidationError(
            "This Anki version does not expose the supported shuffle settings. "
            "Choose Keep current Anki order, or change Display Order in Anki's deck options."
        ) from exc


def build_request(snapshot: Any, did: int, api: Any = None) -> Any | None:
    """Build a minimal native transaction from a fresh options snapshot.

    Copy every option, unknown protobuf field and opaque plugin data. Only the
    three display-order enum fields change. Inactive 'today only' limits must
    not be accidentally reactivated by the native update endpoint.
    """
    api = api or _native_types()
    try:
        config_id = int(snapshot.current_deck.config_id)
        rows = [x for x in snapshot.all_config if int(x.config.id) == config_id]
        if config_id <= 0 or len(rows) != 1 or int(rows[0].use_count) < 1:
            raise ValueError("Missing or ambiguous current preset")
        entry = rows[0]
        selected = deepcopy(entry.config)
        wanted = (
            api.DeckConfig.Config.NEW_CARD_GATHER_PRIORITY_RANDOM_CARDS,
            api.DeckConfig.Config.NEW_CARD_SORT_ORDER_RANDOM_CARD,
            api.DeckConfig.Config.REVIEW_CARD_ORDER_RANDOM,
        )
        if all(getattr(selected.config, field) == value
               for field, value in zip(ORDER_FIELDS, wanted)):
            return None  # Reopening must not create new presets or undo entries.
        for field, value in zip(ORDER_FIELDS, wanted):
            setattr(selected.config, field, value)
        if entry.use_count > 1:
            selected.id = 0  # Native backend allocates and assigns atomically.
            label = snapshot.current_deck.name.split("::")[-1].strip() or "Folder"
            stem = f"Shuffle · {label[:70]} · {did}"
            taken = {x.config.name.casefold() for x in snapshot.all_config}
            name, i = stem, 2
            while name.casefold() in taken:
                name, i = f"{stem} ({i})", i + 1
            selected.name = name
        request = api.UpdateDeckConfigsRequest()
        request.target_deck_id = did
        request.configs.add().CopyFrom(selected)
        request.mode = api.UPDATE_DECK_CONFIGS_MODE_NORMAL  # NOT apply-to-children.
        request.limits.CopyFrom(snapshot.current_deck.limits)
        if not request.limits.review_today_active:
            request.limits.ClearField("review_today")
        if not request.limits.new_today_active:
            request.limits.ClearField("new_today")
        for field in GLOBAL_FIELDS:
            setattr(request, field, getattr(snapshot, field))
        request.fsrs_reschedule = False
        return request
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValidationError(
            "Anki's folder options could not be read safely. No shuffle settings were saved. "
            "Choose Keep current Anki order or open the folder's deck options."
        ) from exc


def select_folder(col: Any, value: Any, expected: Any, order: Any) -> Any:
    """Run only inside the host's serialized CollectionOp; return its changes.

    Native deck-option updates are atomic and undoable. Selection is grouped
    with that update. On a rare later selection failure, report that the saved
    order still exists instead of claiming the entire operation was rolled back.
    """
    if order not in ("shuffle", "current"):
        raise ValidationError("Choose Shuffle lectures or Keep current Anki order.")
    did = validate_folder(col, value, expected)
    deck = col.decks.get(did, default=False)
    if order == "current":
        return col.decks.set_current(did)
    if deck.get("dyn"):
        raise ValidationError("Filtered folders keep their own selection rules. Choose Keep current Anki order.")
    if not callable(getattr(col.decks, "get_deck_configs_for_update", None)) or not callable(getattr(col.decks, "update_deck_configs", None)):
        raise ValidationError("Native shuffle settings are unavailable. Choose Keep current Anki order.")
    request = build_request(col.decks.get_deck_configs_for_update(did), did)
    if request is None:
        return col.decks.set_current(did)
    if not callable(getattr(col, "add_custom_undo_entry", None)) or not callable(getattr(col, "merge_undo_entries", None)):
        raise ValidationError("Anki's undo support is unavailable. No shuffle settings were saved.")
    undo_id = col.add_custom_undo_entry("Shuffle folder")
    saved = False
    try:
        col.decks.update_deck_configs(request)
        saved = True
        col.decks.set_current(did)
    except Exception as exc:
        try:
            col.merge_undo_entries(undo_id)
        except Exception:
            pass  # Never undo unrelated work in an attempt to repair selection.
        if saved:
            raise ValidationError(
                "The shuffled order was saved, but the folder could not open. "
                "Open it again, or use Anki's Undo before reviewing to restore its options."
            ) from exc
        raise ValidationError(
            "Anki could not save the shuffled order. No shuffle settings were applied. "
            "Choose Keep current Anki order or retry after Anki finishes its current operation."
        ) from exc
    try:
        return col.merge_undo_entries(undo_id)
    except Exception as exc:
        raise ValidationError(
            "The shuffled order was saved, but Anki could not group the undo entries. "
            "Open the folder again; its settings are available in Deck options."
        ) from exc
