"""Load versioned AI personality test packs."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any


PACK_FILES = {
    "ai-personality-v0.1": "ai-personality-v0.1.json",
}


def load_pack(pack_id: str) -> dict[str, Any]:
    """Load a bundled test pack by id."""
    try:
        filename = PACK_FILES[pack_id]
    except KeyError as exc:
        known = ", ".join(sorted(PACK_FILES))
        raise ValueError(f"unknown test pack {pack_id!r}; known packs: {known}") from exc

    data_ref = resources.files("ai_personality_eval.data").joinpath(filename)
    with data_ref.open("r", encoding="utf-8") as handle:
        pack = json.load(handle)

    _validate_pack(pack)
    return pack


def _validate_pack(pack: dict[str, Any]) -> None:
    if "id" not in pack or "items" not in pack:
        raise ValueError("test pack must include id and items")
    seen = set()
    for item in pack["items"]:
        item_id = item.get("id")
        if not item_id:
            raise ValueError("every item must include an id")
        if item_id in seen:
            raise ValueError(f"duplicate item id: {item_id}")
        seen.add(item_id)
        if not item.get("options"):
            raise ValueError(f"item {item_id} must include options")
