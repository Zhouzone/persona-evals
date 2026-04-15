"""Release-shape validation for bundled personality test packs."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ai_personality_eval.scoring import (
    MBTI_AXES,
    SBTI_DIMENSION_LABELS,
    SBTI_TYPE_PROFILES,
)


def validate_pack_for_release(pack: dict[str, Any]) -> dict[str, Any]:
    """Return a release-readiness report for the public v0.1 test shape."""
    errors: list[str] = []
    items = pack.get("items", [])
    mbti_items = [item for item in items if item.get("section") == "mbti_like"]
    sbti_items = [item for item in items if item.get("section") == "sbti_style"]
    mbti_axis_counts = Counter(item.get("dimension") for item in mbti_items)
    sbti_dimension_counts = Counter(item.get("dimension") for item in sbti_items)

    _check_count(errors, "total item count", len(items), 95)
    _check_count(errors, "MBTI-like item count", len(mbti_items), 64)
    _check_count(errors, "SBTI-style item count", len(sbti_items), 31)

    for axis, left, right in MBTI_AXES:
        _check_count(errors, f"MBTI axis {axis}", mbti_axis_counts.get(axis, 0), 16)
        for item in [candidate for candidate in mbti_items if candidate.get("dimension") == axis]:
            _check_option_count(errors, item, 2)
            _check_scores_in_set(errors, item, {left, right})

    expected_sbti_dimensions = set(SBTI_DIMENSION_LABELS)
    if set(sbti_dimension_counts) != expected_sbti_dimensions:
        errors.append(
            "SBTI dimensions mismatch: "
            f"expected {sorted(expected_sbti_dimensions)}, got {sorted(sbti_dimension_counts)}"
        )
    for dimension in expected_sbti_dimensions:
        count = sbti_dimension_counts.get(dimension, 0)
        if count < 2:
            errors.append(f"SBTI dimension {dimension} has {count} items; expected at least 2")

    if len(SBTI_TYPE_PROFILES) != 27:
        errors.append(f"SBTI type profiles count is {len(SBTI_TYPE_PROFILES)}; expected 27")
    for type_name, profile in SBTI_TYPE_PROFILES.items():
        if set(profile) != expected_sbti_dimensions:
            errors.append(f"SBTI profile {type_name} does not cover all dimensions")
        bad_values = {
            dimension: value
            for dimension, value in profile.items()
            if value not in {-1, 0, 1}
        }
        if bad_values:
            errors.append(f"SBTI profile {type_name} has invalid values: {bad_values}")

    for item in sbti_items:
        _check_option_count(errors, item, 3)
        dimension = item.get("dimension")
        score_values = [
            option.get("scores", {}).get(dimension)
            for option in item.get("options", [])
        ]
        if set(score_values) != {-1, 0, 1}:
            errors.append(
                f"item {item.get('id')} must give primary dimension {dimension} "
                f"exactly one -1, one 0, and one 1 option; got {score_values}"
            )
        unknown_score_keys = set()
        for option in item.get("options", []):
            unknown_score_keys.update(set(option.get("scores", {})) - expected_sbti_dimensions)
        if unknown_score_keys:
            errors.append(f"item {item.get('id')} has unknown SBTI score keys: {sorted(unknown_score_keys)}")

    return {
        "ok": not errors,
        "errors": errors,
        "total_items": len(items),
        "mbti_items": len(mbti_items),
        "sbti_items": len(sbti_items),
        "mbti_axis_counts": dict(mbti_axis_counts),
        "sbti_dimension_counts": dict(sbti_dimension_counts),
        "sbti_type_profiles": len(SBTI_TYPE_PROFILES),
    }


def _check_count(errors: list[str], label: str, actual: int, expected: int) -> None:
    if actual != expected:
        errors.append(f"{label} is {actual}; expected {expected}")


def _check_option_count(errors: list[str], item: dict[str, Any], expected: int) -> None:
    actual = len(item.get("options", []))
    if actual != expected:
        errors.append(f"item {item.get('id')} has {actual} options; expected {expected}")


def _check_scores_in_set(
    errors: list[str], item: dict[str, Any], allowed: set[str]
) -> None:
    for option in item.get("options", []):
        score_keys = set(option.get("scores", {}))
        if not score_keys:
            errors.append(f"item {item.get('id')} option {option.get('id')} has no scores")
            continue
        if not score_keys <= allowed:
            errors.append(
                f"item {item.get('id')} option {option.get('id')} has score keys "
                f"{sorted(score_keys)}; expected subset of {sorted(allowed)}"
            )
