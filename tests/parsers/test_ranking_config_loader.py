import pytest
from src.parsers.ranking_config_loader import RankingConfigLoader

def test_from_file_loads_valid_metrics(tmp_path):
    config = tmp_path / "constraints.txt"
    config.write_text(
        """
# ADVANCED_CONSTRAINTS
daily_cap_enabled=true
daily_cap_k=3

{{# RANKING:}}
min_days_required
avg_days_all
invalid_metric_will_be_ignored
span_required
""",
        encoding="utf-8",
    )

    ranking = RankingConfigLoader.from_file(str(config))
    assert ranking == ["min_days_required", "avg_days_all", "span_required"]

def test_from_file_ignores_sections_after_ranking(tmp_path):
    config = tmp_path / "constraints.txt"
    config.write_text(
        """
{{# RANKING:}}
max_exams_per_day
avg_room_distance

# ADVANCED_CONSTRAINTS
daily_cap_enabled=true
""",
        encoding="utf-8",
    )

    ranking = RankingConfigLoader.from_file(str(config))
    assert ranking == ["max_exams_per_day", "avg_room_distance"]

def test_from_file_empty_or_no_ranking(tmp_path):
    config = tmp_path / "constraints.txt"
    config.write_text("just some text", encoding="utf-8")
    assert RankingConfigLoader.from_file(str(config)) == []
