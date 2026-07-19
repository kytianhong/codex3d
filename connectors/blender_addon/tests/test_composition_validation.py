from codex3d_blender_connector.composition_validation import evaluate_composition


def _curves(visible: bool = True):
    return [{"name": f"Orbit_{index}", "intersects_frame": visible} for index in range(6)]


def test_composition_accepts_centered_visible_subject() -> None:
    result = evaluate_composition(
        inside_frame_ratio=1.0,
        subject_frame_coverage=0.58,
        center_offset=0.04,
        overexposed_pixel_ratio=0.03,
        unwanted_visible_objects=[],
        curve_visibility=_curves(),
    )
    assert result["passed"] is True


def test_composition_reports_crop_overexposure_and_unwanted_object() -> None:
    result = evaluate_composition(
        inside_frame_ratio=0.75,
        subject_frame_coverage=0.9,
        center_offset=0.24,
        overexposed_pixel_ratio=0.3,
        unwanted_visible_objects=[{"name": "Cube"}],
        curve_visibility=_curves(False),
    )
    assert result["passed"] is False
    assert {"SUBJECT_CROPPED", "CAMERA_TOO_CLOSE", "CORE_OVEREXPOSED", "UNWANTED_OBJECT_VISIBLE"} <= set(result["failures"])
