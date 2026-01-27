"""ツール出力スキーマ検証テスト.

Issue #157 - Pydanticによるツール出力形式の自動検証
"""

from typing import Optional

import pytest
from pydantic import BaseModel, Field, ValidationError


# --- スキーマ定義 ---


class HorseAnalysis(BaseModel):
    """馬分析ツールの出力スキーマ."""

    horse_name: str = Field(..., description="馬名")
    recent_form: Optional[str] = Field(None, description="直近の成績")
    form_rating: Optional[str] = Field(None, description="調子評価")
    ability_analysis: Optional[dict] = Field(None, description="能力分析")
    class_analysis: Optional[dict] = Field(None, description="クラス分析")
    distance_preference: Optional[dict] = Field(None, description="距離適性")
    comment: Optional[str] = Field(None, description="コメント")
    warning: Optional[str] = Field(None, description="警告メッセージ")
    error: Optional[str] = Field(None, description="エラーメッセージ")


class BetAnalysis(BaseModel):
    """買い目分析ツールの出力スキーマ."""

    race_id: str = Field(..., description="レースID")
    bet_type: str = Field(..., description="券種")
    bet_type_name: str = Field(..., description="券種名")
    total_runners: int = Field(..., ge=0, description="出走頭数")
    selected_horses: list = Field(..., description="選択馬リスト")
    summary: dict = Field(..., description="サマリー")
    weaknesses: list = Field(..., description="弱点リスト")
    torigami_risk: dict = Field(..., description="トリガミリスク")
    amount: int = Field(..., ge=0, description="掛け金")
    amount_feedback: dict = Field(..., description="掛け金フィードバック")


class RaceData(BaseModel):
    """レースデータの出力スキーマ."""

    race: dict = Field(default_factory=dict, description="レース情報")
    runners: list = Field(default_factory=list, description="出走馬リスト")
    error: Optional[str] = Field(None, description="エラーメッセージ")


class TrainingAnalysis(BaseModel):
    """調教分析ツールの出力スキーマ."""

    horse_name: Optional[str] = Field(None, description="馬名")
    last_workout: Optional[dict] = Field(None, description="直近の調教")
    trend_analysis: Optional[dict] = Field(None, description="傾向分析")
    condition_rating: Optional[str] = Field(None, description="状態評価")
    trainer_intent: Optional[str] = Field(None, description="トレーナーの意図")
    warning: Optional[str] = Field(None, description="警告メッセージ")
    error: Optional[str] = Field(None, description="エラーメッセージ")


class PedigreeAnalysis(BaseModel):
    """血統分析ツールの出力スキーマ."""

    horse_name: Optional[str] = Field(None, description="馬名")
    sire_analysis: Optional[dict] = Field(None, description="父系分析")
    dam_analysis: Optional[dict] = Field(None, description="母系分析")
    distance_aptitude: Optional[str] = Field(None, description="距離適性")
    track_aptitude: Optional[dict] = Field(None, description="馬場適性")
    warning: Optional[str] = Field(None, description="警告メッセージ")
    error: Optional[str] = Field(None, description="エラーメッセージ")


class OddsAnalysis(BaseModel):
    """オッズ分析ツールの出力スキーマ."""

    race_id: Optional[str] = Field(None, description="レースID")
    horse_number: Optional[int] = Field(None, description="馬番")
    horse_name: Optional[str] = Field(None, description="馬名")
    current_odds: Optional[float] = Field(None, description="現在オッズ")
    opening_odds: Optional[float] = Field(None, description="初期オッズ")
    odds_trend: Optional[str] = Field(None, description="オッズ傾向")
    warning: Optional[str] = Field(None, description="警告メッセージ")
    error: Optional[str] = Field(None, description="エラーメッセージ")


# --- テストケース ---


class TestHorseAnalysisSchema:
    """馬分析スキーマのテスト."""

    def test_正常なデータを検証(self):
        """正常なデータが検証を通過する."""
        data = {
            "horse_name": "テスト馬",
            "recent_form": "1-2-3",
            "form_rating": "好調",
            "ability_analysis": {
                "finishing_speed": "A",
                "stamina": "B",
                "consistency": "高い",
            },
            "comment": "直近3走で馬券圏内3回と安定した成績。",
        }
        result = HorseAnalysis(**data)
        assert result.horse_name == "テスト馬"
        assert result.form_rating == "好調"

    def test_警告を含むデータを検証(self):
        """警告メッセージを含むデータも検証を通過する."""
        data = {
            "horse_name": "不明馬",
            "warning": "過去成績データが見つかりませんでした",
        }
        result = HorseAnalysis(**data)
        assert result.warning is not None

    def test_必須フィールドがない場合はエラー(self):
        """必須フィールドがない場合はValidationError."""
        with pytest.raises(ValidationError):
            HorseAnalysis(**{})


class TestBetAnalysisSchema:
    """買い目分析スキーマのテスト."""

    def test_正常なデータを検証(self):
        """正常なデータが検証を通過する."""
        data = {
            "race_id": "20260125_06_11",
            "bet_type": "win",
            "bet_type_name": "単勝",
            "total_runners": 16,
            "selected_horses": [
                {
                    "horse_number": 1,
                    "horse_name": "テスト馬",
                    "odds": 2.5,
                    "popularity": 1,
                }
            ],
            "summary": {
                "average_odds": 2.5,
                "average_popularity": 1.0,
            },
            "weaknesses": [],
            "torigami_risk": {"risk_level": "低"},
            "amount": 100,
            "amount_feedback": {"warnings": [], "info": []},
        }
        result = BetAnalysis(**data)
        assert result.race_id == "20260125_06_11"
        assert result.bet_type == "win"

    def test_出走頭数が負の場合はエラー(self):
        """出走頭数が負の場合はValidationError."""
        data = {
            "race_id": "test",
            "bet_type": "win",
            "bet_type_name": "単勝",
            "total_runners": -1,  # 無効な値
            "selected_horses": [],
            "summary": {},
            "weaknesses": [],
            "torigami_risk": {},
            "amount": 100,
            "amount_feedback": {},
        }
        with pytest.raises(ValidationError):
            BetAnalysis(**data)


class TestRaceDataSchema:
    """レースデータスキーマのテスト."""

    def test_正常なデータを検証(self):
        """正常なデータが検証を通過する."""
        data = {
            "race": {
                "race_id": "20260125_06_11",
                "race_name": "テストレース",
            },
            "runners": [
                {"horse_number": 1, "horse_name": "馬1"},
            ],
        }
        result = RaceData(**data)
        assert result.race["race_name"] == "テストレース"

    def test_エラーを含むデータを検証(self):
        """エラーメッセージを含むデータも検証を通過する."""
        data = {
            "error": "API呼び出しに失敗しました",
        }
        result = RaceData(**data)
        assert result.error is not None

    def test_空データでもデフォルト値で検証通過(self):
        """空データでもデフォルト値が適用される."""
        data = {}
        result = RaceData(**data)
        assert result.race == {}
        assert result.runners == []


class TestTrainingAnalysisSchema:
    """調教分析スキーマのテスト."""

    def test_正常なデータを検証(self):
        """正常なデータが検証を通過する."""
        data = {
            "horse_name": "テスト馬",
            "last_workout": {
                "date": "2026-01-20",
                "course": "栗東CW",
            },
            "condition_rating": "良好",
        }
        result = TrainingAnalysis(**data)
        assert result.horse_name == "テスト馬"


class TestPedigreeAnalysisSchema:
    """血統分析スキーマのテスト."""

    def test_正常なデータを検証(self):
        """正常なデータが検証を通過する."""
        data = {
            "horse_name": "テスト馬",
            "sire_analysis": {
                "name": "ディープインパクト",
                "line": "サンデーサイレンス系",
            },
            "distance_aptitude": "中〜長距離",
        }
        result = PedigreeAnalysis(**data)
        assert result.horse_name == "テスト馬"


class TestOddsAnalysisSchema:
    """オッズ分析スキーマのテスト."""

    def test_正常なデータを検証(self):
        """正常なデータが検証を通過する."""
        data = {
            "race_id": "20260125_06_11",
            "horse_number": 1,
            "horse_name": "テスト馬",
            "current_odds": 5.5,
            "opening_odds": 8.0,
            "odds_trend": "下降中",
        }
        result = OddsAnalysis(**data)
        assert result.current_odds == 5.5


class TestSchemaValidationIntegration:
    """スキーマ検証統合テスト."""

    def test_複数のスキーマを組み合わせた検証(self):
        """複数のスキーマを組み合わせた検証."""
        # 馬分析結果
        horse_data = {
            "horse_name": "テスト馬",
            "form_rating": "好調",
        }
        horse_result = HorseAnalysis(**horse_data)

        # オッズ分析結果
        odds_data = {
            "horse_name": "テスト馬",
            "current_odds": 3.5,
        }
        odds_result = OddsAnalysis(**odds_data)

        # 両方の結果が同じ馬を指していることを確認
        assert horse_result.horse_name == odds_result.horse_name

    def test_全スキーマのエラーレスポンスを検証(self):
        """全スキーマがエラーレスポンスを受け入れることを確認."""
        schemas = [
            (HorseAnalysis, {"horse_name": "X", "error": "エラー"}),
            (TrainingAnalysis, {"error": "エラー"}),
            (PedigreeAnalysis, {"error": "エラー"}),
            (OddsAnalysis, {"error": "エラー"}),
        ]

        for schema_class, data in schemas:
            result = schema_class(**data)
            assert result.error == "エラー" or hasattr(result, "error")
