from __future__ import annotations

from typing import Any


DEFAULT_THRESHOLDS = {
    "inside_frame_ratio": 0.95,
    "max_center_offset": 0.18,
    "max_coverage": 0.82,
    "max_overexposed_ratio": 0.12,
}


def evaluate_composition(
    *,
    inside_frame_ratio: float,
    subject_frame_coverage: float,
    center_offset: float,
    overexposed_pixel_ratio: float,
    unwanted_visible_objects: list[dict[str, Any]],
    curve_visibility: list[dict[str, Any]],
) -> dict[str, Any]:
    failures: list[str] = []
    if inside_frame_ratio < DEFAULT_THRESHOLDS["inside_frame_ratio"]:
        failures.append("SUBJECT_CROPPED" if subject_frame_coverage > 0 else "SUBJECT_NOT_VISIBLE")
    if center_offset > DEFAULT_THRESHOLDS["max_center_offset"]:
        failures.append("COMPOSITION_OFF_CENTER")
    if subject_frame_coverage > DEFAULT_THRESHOLDS["max_coverage"]:
        failures.append("CAMERA_TOO_CLOSE")
    if overexposed_pixel_ratio > DEFAULT_THRESHOLDS["max_overexposed_ratio"]:
        failures.append("CORE_OVEREXPOSED")
    if unwanted_visible_objects:
        failures.append("UNWANTED_OBJECT_VISIBLE")
    if len(curve_visibility) < 6 or any(not item.get("intersects_frame") for item in curve_visibility):
        failures.append("CORE_CURVES_NOT_ALL_VISIBLE")
    return {"passed": not failures, "failures": failures, "thresholds": dict(DEFAULT_THRESHOLDS)}
