"""AgentCore カスタムツール."""

from .race_data import get_race_data
from .bet_analysis import analyze_bet_selection
from .pace_analysis import analyze_race_development, analyze_running_style_match
from .historical_analysis import (
    analyze_past_race_trends,
    analyze_jockey_course_stats,
    analyze_bet_roi,
)
from .horse_analysis import analyze_horse_performance
from .training_analysis import analyze_training_condition
from .pedigree_analysis import analyze_pedigree_aptitude
from .trainer_analysis import analyze_trainer_tendency
from .course_aptitude_analysis import analyze_course_aptitude
from .jockey_analysis import analyze_jockey_factor
from .odds_analysis import analyze_odds_movement
from .weight_analysis import analyze_weight_trend
from .gate_analysis import analyze_gate_position
from .sire_analysis import analyze_sire_offspring
from .race_comprehensive_analysis import analyze_race_comprehensive
from .bet_combinations import suggest_bet_combinations
from .rotation_analysis import analyze_rotation
# Issue #102-111 追加ツール
from .bet_probability_analysis import analyze_bet_probability
from .track_condition_analysis import analyze_track_condition_impact
from .last_race_analysis import analyze_last_race_detail
from .class_analysis import analyze_class_factor
from .distance_change_analysis import analyze_distance_change
from .momentum_analysis import analyze_momentum
from .track_change_analysis import track_course_condition_change
from .scratch_impact_analysis import analyze_scratch_impact
from .time_analysis import analyze_time_performance
# AI予想データ
from .ai_prediction import get_ai_prediction, list_ai_predictions_for_date

__all__ = [
    "get_race_data",
    "analyze_bet_selection",
    "analyze_race_development",
    "analyze_running_style_match",
    "analyze_past_race_trends",
    "analyze_jockey_course_stats",
    "analyze_bet_roi",
    "analyze_horse_performance",
    "analyze_training_condition",
    "analyze_pedigree_aptitude",
    "analyze_trainer_tendency",
    "analyze_course_aptitude",
    "analyze_jockey_factor",
    "analyze_odds_movement",
    "analyze_weight_trend",
    "analyze_gate_position",
    "analyze_sire_offspring",
    "analyze_race_comprehensive",
    "suggest_bet_combinations",
    "analyze_rotation",
    # Issue #102-111 追加ツール
    "analyze_bet_probability",
    "analyze_track_condition_impact",
    "analyze_last_race_detail",
    "analyze_class_factor",
    "analyze_distance_change",
    "analyze_momentum",
    "track_course_condition_change",
    "analyze_scratch_impact",
    "analyze_time_performance",
    # AI予想データ
    "get_ai_prediction",
    "list_ai_predictions_for_date",
]
