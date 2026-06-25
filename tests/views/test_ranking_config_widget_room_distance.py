from src.views.settings_screen import ranking_config_widget as ranking_widget


# Test that avg_room_distance is registered as a visible ranking metric.
def test_avg_room_distance_registered_in_metric_titles():
    assert "avg_room_distance" in ranking_widget._METRIC_TITLES
    assert ranking_widget._METRIC_TITLES["avg_room_distance"] == "Average room distance"


# Test that avg_room_distance has a user-facing description.
def test_avg_room_distance_registered_in_metric_descriptions():
    assert "avg_room_distance" in ranking_widget._METRIC_DESCRIPTIONS
    assert "lower" in ranking_widget._METRIC_DESCRIPTIONS["avg_room_distance"]


# Test that avg_room_distance appears in the default ranking order.
def test_avg_room_distance_registered_in_default_order():
    assert "avg_room_distance" in ranking_widget._DEFAULT_ORDER
