from research_engine.signal_logic import classify_vwap_location, expected_direction_for_side


def test_vwap_location_labels():
    assert classify_vwap_location(110, 100, 10, near_threshold_atr=0.25) == "above_vwap"
    assert classify_vwap_location(90, 100, 10, near_threshold_atr=0.25) == "below_vwap"
    assert classify_vwap_location(101, 100, 10, near_threshold_atr=0.25) == "near_vwap"
    assert expected_direction_for_side("above_vwap") == "down"
    assert expected_direction_for_side("below_vwap") == "up"
