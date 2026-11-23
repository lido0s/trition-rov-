from gcs.input.mapper import apply_deadzone


def test_drift_is_zeroed():
    assert apply_deadzone(0.05, 0.1) == 0.0
    assert apply_deadzone(-0.09, 0.1) == 0.0


def test_full_deflection_still_reaches_one():
    assert apply_deadzone(1.0, 0.1) == 1.0
    assert apply_deadzone(-1.0, 0.1) == -1.0
