from pathlib import Path

class RankingConfigLoader:
    """Loads ranking configuration order from text files."""

    SECTION_MARKER = "{{# RANKING:}}"
    
    _VALID_KEYS = {
        "min_days_required",
        "avg_days_all",
        "elective_conflicts",
        "span_required",
        "max_exams_per_day",
        "avg_room_distance",
    }

    @staticmethod
    def from_file(path: str) -> list[str]:
        """Parse the ranking metrics order from a configuration file."""
        if not path or not Path(path).exists():
            return []
            
        ranking_order = []
        in_section = False
        
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            
            if not stripped:
                continue
                
            if stripped == RankingConfigLoader.SECTION_MARKER:
                in_section = True
                continue
                
            if in_section:
                # Stop parsing if we hit another block or a comment starting with '#'
                if stripped.startswith("#") or stripped.startswith("{{#") or "=" in stripped:
                    in_section = False
                    continue
                
                if stripped in RankingConfigLoader._VALID_KEYS:
                    ranking_order.append(stripped)
                    
        return ranking_order
