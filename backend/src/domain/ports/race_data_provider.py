"""レースデータ取得インターフェース（ポート）."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

from ..identifiers import RaceId


@dataclass(frozen=True)
class RaceData:
    """レース情報."""

    race_id: str
    race_name: str
    race_number: int
    venue: str
    start_time: datetime
    betting_deadline: datetime
    track_condition: str  # 馬場状態
    track_type: str = ""  # コース種別（芝/ダ/障）
    distance: int = 0  # 距離（メートル）
    horse_count: int = 0  # 出走頭数
    # 条件フィールド
    grade_class: str = ""  # クラス（新馬、未勝利、1勝、2勝、3勝、OP、L、G3、G2、G1）
    age_condition: str = ""  # 年齢条件（3歳、4歳以上など）
    is_obstacle: bool = False  # 障害レース
    # JRA出馬表URL生成用
    kaisai_kai: str = ""  # 回次（01, 02など）
    kaisai_nichime: str = ""  # 日目（01, 02など）


@dataclass(frozen=True)
class RunnerData:
    """出走馬情報."""

    horse_number: int
    horse_name: str
    horse_id: str
    jockey_name: str
    jockey_id: str
    odds: str
    popularity: int
    waku_ban: int = 0  # 枠番（1-8）


@dataclass(frozen=True)
class PerformanceData:
    """過去成績データ."""

    race_date: datetime
    race_name: str
    venue: str
    finish_position: int
    distance: int
    track_condition: str
    time: str


@dataclass(frozen=True)
class JockeyStatsData:
    """騎手のコース成績データ."""

    jockey_id: str
    jockey_name: str
    course: str
    total_races: int
    wins: int
    win_rate: float
    place_rate: float


@dataclass(frozen=True)
class PedigreeData:
    """血統情報."""

    horse_id: str
    horse_name: str | None
    sire_name: str | None       # 父
    dam_name: str | None        # 母
    broodmare_sire: str | None  # 母父


@dataclass(frozen=True)
class WeightData:
    """馬体重データ."""

    weight: int          # 馬体重(kg)
    weight_diff: int     # 前走比増減


@dataclass(frozen=True)
class PopularityStats:
    """人気別統計データ."""

    popularity: int
    total_runs: int
    wins: int
    places: int
    win_rate: float
    place_rate: float


@dataclass(frozen=True)
class PastRaceStats:
    """過去レース統計."""

    total_races: int
    popularity_stats: list[PopularityStats]
    avg_win_payout: float | None
    avg_place_payout: float | None
    track_type: str
    distance: int
    grade_class: str | None


@dataclass(frozen=True)
class HorsePerformanceData:
    """馬の過去成績詳細データ."""

    race_id: str
    race_date: str  # YYYYMMDD形式
    race_name: str
    venue: str
    distance: int
    track_type: str  # 芝/ダート/障害
    track_condition: str  # 良/稍/重/不
    finish_position: int
    total_runners: int
    time: str  # 例: "1:33.5"
    horse_name: str | None = None  # 馬名
    time_diff: str | None = None  # 例: "+0.2"
    last_3f: str | None = None  # 上がり3ハロン 例: "33.8"
    weight_carried: float | None = None  # 斤量
    jockey_name: str | None = None
    odds: float | None = None
    popularity: int | None = None
    margin: str | None = None  # 着差 例: "クビ"
    race_pace: str | None = None  # S/M/H
    running_style: str | None = None  # 逃げ/先行/差し/追込


@dataclass(frozen=True)
class JockeyInfoData:
    """騎手基本情報."""

    jockey_id: str
    jockey_name: str
    jockey_name_kana: str | None = None
    birth_date: str | None = None  # YYYY-MM-DD形式
    affiliation: str | None = None  # 美浦/栗東
    license_year: int | None = None


@dataclass(frozen=True)
class TrainingRecordData:
    """調教データ."""

    date: str  # YYYYMMDD形式
    course: str  # 栗東CW, 美浦南W など
    course_condition: str  # 良/稍/重/不
    distance: int  # メートル
    time: str  # 例: "52.3"
    last_3f: str | None = None  # 例: "12.5"
    last_1f: str | None = None  # 例: "12.0"
    training_type: str | None = None  # 馬なり/一杯/強め など
    partner_horse: str | None = None  # 併せ馬
    evaluation: str | None = None  # A/B/C など
    comment: str | None = None


@dataclass(frozen=True)
class TrainingSummaryData:
    """調教サマリー."""

    recent_trend: str  # 上昇/平行/下降
    average_time: str | None = None
    best_time: str | None = None


@dataclass(frozen=True)
class JockeyStatsDetailData:
    """騎手成績統計データ."""

    jockey_id: str
    jockey_name: str
    total_rides: int
    wins: int
    second_places: int
    third_places: int
    win_rate: float
    place_rate: float
    period: str  # recent/ytd/all/year
    year: int | None = None


@dataclass(frozen=True)
class AncestorData:
    """先祖馬データ."""

    name: str
    sire: str | None = None  # 父
    dam: str | None = None  # 母
    broodmare_sire: str | None = None  # 母父


@dataclass(frozen=True)
class InbreedingData:
    """インブリードデータ."""

    ancestor: str  # 共通先祖名
    pattern: str  # 例: "3x4"
    percentage: float  # 血量パーセンテージ


@dataclass(frozen=True)
class ExtendedPedigreeData:
    """拡張血統情報（3代血統）."""

    horse_id: str
    horse_name: str | None
    sire: AncestorData | None  # 父
    dam: AncestorData | None  # 母
    inbreeding: list[InbreedingData]  # インブリード情報
    lineage_type: str | None  # 系統タイプ（例: サンデーサイレンス系）


@dataclass(frozen=True)
class OddsSnapshotData:
    """オッズスナップショットデータ（馬ごと）."""

    horse_number: int
    win_odds: float
    place_odds_min: float | None
    place_odds_max: float | None
    popularity: int


@dataclass(frozen=True)
class OddsTimestampData:
    """時系列オッズデータ."""

    timestamp: str  # ISO8601形式
    odds: list[OddsSnapshotData]


@dataclass(frozen=True)
class OddsMovementData:
    """オッズ推移データ."""

    horse_number: int
    initial_odds: float
    final_odds: float
    change_rate: float  # 変化率（%）
    trend: str  # 上昇/下降/横ばい


@dataclass(frozen=True)
class NotableMovementData:
    """注目のオッズ変動データ."""

    horse_number: int
    description: str


@dataclass(frozen=True)
class OddsHistoryData:
    """オッズ履歴総合データ."""

    race_id: str
    odds_history: list[OddsTimestampData]
    odds_movement: list[OddsMovementData]
    notable_movements: list[NotableMovementData]


@dataclass(frozen=True)
class RunningStyleData:
    """脚質データ."""

    horse_number: int
    horse_name: str
    running_style: str  # 逃げ/先行/差し/追込
    running_style_tendency: str  # 主な脚質傾向


@dataclass(frozen=True)
class VenueAptitudeData:
    """競馬場別適性データ."""

    venue: str
    starts: int
    wins: int
    places: int
    win_rate: float
    place_rate: float


@dataclass(frozen=True)
class TrackTypeAptitudeData:
    """コース種別適性データ."""

    track_type: str  # 芝/ダート/障害
    starts: int
    wins: int
    win_rate: float


@dataclass(frozen=True)
class DistanceAptitudeData:
    """距離別適性データ."""

    distance_range: str  # 例: "1600-1800m"
    starts: int
    wins: int
    win_rate: float
    best_time: str | None = None


@dataclass(frozen=True)
class ConditionAptitudeData:
    """馬場状態別適性データ."""

    condition: str  # 良/稍/重/不
    starts: int
    wins: int
    win_rate: float


@dataclass(frozen=True)
class PositionAptitudeData:
    """枠番位置別適性データ."""

    position: str  # 例: "内枠(1-4)"
    starts: int
    wins: int
    win_rate: float


@dataclass(frozen=True)
class AptitudeSummaryData:
    """適性サマリーデータ."""

    best_venue: str | None
    best_distance: str | None
    preferred_condition: str | None
    preferred_position: str | None


@dataclass(frozen=True)
class CourseAptitudeData:
    """コース適性総合データ."""

    horse_id: str
    horse_name: str | None
    by_venue: list[VenueAptitudeData]
    by_track_type: list[TrackTypeAptitudeData]
    by_distance: list[DistanceAptitudeData]
    by_track_condition: list[ConditionAptitudeData]
    by_running_position: list[PositionAptitudeData]
    aptitude_summary: AptitudeSummaryData | None


@dataclass(frozen=True)
class TrainerInfoData:
    """厩舎（調教師）基本情報."""

    trainer_id: str
    trainer_name: str
    trainer_name_kana: str | None = None
    affiliation: str | None = None  # 美浦/栗東
    stable_location: str | None = None
    license_year: int | None = None
    career_wins: int | None = None
    career_starts: int | None = None


@dataclass(frozen=True)
class TrainerStatsDetailData:
    """厩舎（調教師）成績統計データ."""

    trainer_id: str
    trainer_name: str
    total_starts: int
    wins: int
    second_places: int
    third_places: int
    win_rate: float
    place_rate: float
    prize_money: int | None = None
    period: str = "all"  # recent/all/year
    year: int | None = None


@dataclass(frozen=True)
class TrainerTrackStatsData:
    """厩舎コース別成績."""

    track_type: str  # 芝/ダート/障害
    starts: int
    wins: int
    win_rate: float


@dataclass(frozen=True)
class TrainerClassStatsData:
    """厩舎クラス別成績."""

    grade_class: str  # G1/G2/G3/OP/1勝/2勝/3勝/未勝利/新馬
    starts: int
    wins: int
    win_rate: float


@dataclass(frozen=True)
class StallionOffspringStatsData:
    """種牡馬産駒成績統計データ."""

    stallion_id: str
    stallion_name: str
    total_offspring: int
    total_starts: int
    wins: int
    win_rate: float
    place_rate: float
    g1_wins: int
    earnings: int | None = None


@dataclass(frozen=True)
class StallionTrackStatsData:
    """種牡馬トラック別成績."""

    track_type: str  # 芝/ダート/障害
    starts: int
    wins: int
    win_rate: float
    avg_distance: int | None = None


@dataclass(frozen=True)
class StallionDistanceStatsData:
    """種牡馬距離別成績."""

    distance_range: str  # 例: "1600-2000m"
    starts: int
    wins: int
    win_rate: float


@dataclass(frozen=True)
class StallionConditionStatsData:
    """種牡馬馬場状態別成績."""

    condition: str  # 良/稍/重/不
    starts: int
    wins: int
    win_rate: float


@dataclass(frozen=True)
class TopOffspringData:
    """トップ産駒データ."""

    horse_name: str
    wins: int
    g1_wins: int


@dataclass(frozen=True)
class AllOddsData:
    """全券種オッズデータ."""

    race_id: str
    win: dict[str, float]
    place: dict[str, dict[str, float]]
    quinella: dict[str, float]
    quinella_place: dict[str, float]
    exacta: dict[str, float]
    trio: dict[str, float]
    trifecta: dict[str, float]


class RaceDataProvider(ABC):
    """レースデータ取得インターフェース（外部システム）."""

    @abstractmethod
    def get_race(self, race_id: RaceId) -> RaceData | None:
        """レース情報を取得する."""
        pass

    @abstractmethod
    def get_races_by_date(
        self, target_date: date, venue: str | None = None
    ) -> list[RaceData]:
        """日付でレース一覧を取得する.

        Args:
            target_date: 対象日付
            venue: 開催場（指定しない場合は全開催場）

        Returns:
            レース一覧（開催場、レース番号順）
        """
        pass

    @abstractmethod
    def get_runners(self, race_id: RaceId) -> list[RunnerData]:
        """出走馬情報を取得する."""
        pass

    @abstractmethod
    def get_past_performance(self, horse_id: str) -> list[PerformanceData]:
        """馬の過去成績を取得する."""
        pass

    @abstractmethod
    def get_jockey_stats(self, jockey_id: str, course: str) -> JockeyStatsData | None:
        """騎手のコース成績を取得する."""
        pass

    @abstractmethod
    def get_pedigree(self, horse_id: str) -> PedigreeData | None:
        """馬の血統情報を取得する."""
        pass

    @abstractmethod
    def get_weight_history(self, horse_id: str, limit: int = 5) -> list[WeightData]:
        """馬の体重履歴を取得する."""
        pass

    @abstractmethod
    def get_race_weights(self, race_id: RaceId) -> dict[int, WeightData]:
        """レースの馬体重情報を取得する.

        Returns:
            馬番をキーとした馬体重データの辞書
        """
        pass

    @abstractmethod
    def get_jra_checksum(
        self,
        venue_code: str,
        kaisai_kai: str,
        kaisai_nichime: int,
        race_number: int,
    ) -> int | None:
        """JRA出馬表URLのチェックサムを取得する.

        Args:
            venue_code: 競馬場コード（01-10）
            kaisai_kai: 回次（01-05）
            kaisai_nichime: 日目（1-12）
            race_number: レース番号（1-12）

        Returns:
            チェックサム値（0-255）、データがない場合はNone
        """
        pass

    @abstractmethod
    def get_race_dates(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[date]:
        """開催日一覧を取得する.

        Args:
            from_date: 開始日（省略時は制限なし）
            to_date: 終了日（省略時は制限なし）

        Returns:
            開催日のリスト（降順）
        """
        pass

    @abstractmethod
    def get_past_race_stats(
        self,
        track_type: str,
        distance: int,
        grade_class: str | None = None,
        limit: int = 100
    ) -> PastRaceStats | None:
        """過去の同条件レース統計を取得する.

        Args:
            track_type: トラック種別（芝、ダート、障害）
            distance: 距離（メートル）
            grade_class: グレードクラス（省略可）
            limit: 集計対象レース数

        Returns:
            過去レース統計、データがない場合はNone
        """
        pass

    @abstractmethod
    def get_jockey_info(self, jockey_id: str) -> JockeyInfoData | None:
        """騎手基本情報を取得する.

        Args:
            jockey_id: 騎手コード

        Returns:
            騎手基本情報、見つからない場合はNone
        """
        pass

    @abstractmethod
    def get_jockey_stats_detail(
        self,
        jockey_id: str,
        year: int | None = None,
        period: str = "recent",
    ) -> JockeyStatsDetailData | None:
        """騎手の成績統計を取得する.

        Args:
            jockey_id: 騎手コード
            year: 年（指定時はその年の成績）
            period: 期間（recent=直近1年, ytd=今年初から, all=通算）

        Returns:
            騎手成績統計、見つからない場合はNone
        """
        pass

    @abstractmethod
    def get_horse_performances(
        self,
        horse_id: str,
        limit: int = 5,
        track_type: str | None = None,
    ) -> list[HorsePerformanceData]:
        """馬の過去成績を詳細に取得する.

        Args:
            horse_id: 馬コード
            limit: 取得件数（デフォルト5、最大20）
            track_type: 芝/ダート/障害 でフィルタ

        Returns:
            過去成績データのリスト（新しい順）
        """
        pass

    @abstractmethod
    def get_horse_training(
        self,
        horse_id: str,
        limit: int = 5,
        days: int = 30,
    ) -> tuple[list[TrainingRecordData], TrainingSummaryData | None]:
        """馬の調教データを取得する.

        Args:
            horse_id: 馬コード
            limit: 取得件数（デフォルト5、最大10）
            days: 直近N日分（デフォルト30）

        Returns:
            調教データのリストとサマリーのタプル
        """
        pass

    @abstractmethod
    def get_extended_pedigree(self, horse_id: str) -> ExtendedPedigreeData | None:
        """馬の拡張血統情報（3代血統）を取得する.

        Args:
            horse_id: 馬コード

        Returns:
            拡張血統情報、見つからない場合はNone
        """
        pass

    @abstractmethod
    def get_odds_history(self, race_id: RaceId) -> OddsHistoryData | None:
        """レースのオッズ履歴を取得する.

        Args:
            race_id: レースID

        Returns:
            オッズ履歴データ、見つからない場合はNone
        """
        pass

    @abstractmethod
    def get_running_styles(self, race_id: RaceId) -> list[RunningStyleData]:
        """レースの出走馬の脚質データを取得する.

        Args:
            race_id: レースID

        Returns:
            脚質データのリスト
        """
        pass

    @abstractmethod
    def get_course_aptitude(self, horse_id: str) -> CourseAptitudeData | None:
        """馬のコース適性を取得する.

        Args:
            horse_id: 馬コード

        Returns:
            コース適性データ、見つからない場合はNone
        """
        pass

    @abstractmethod
    def get_trainer_info(self, trainer_id: str) -> TrainerInfoData | None:
        """厩舎（調教師）基本情報を取得する.

        Args:
            trainer_id: 調教師コード

        Returns:
            厩舎基本情報、見つからない場合はNone
        """
        pass

    @abstractmethod
    def get_trainer_stats_detail(
        self,
        trainer_id: str,
        year: int | None = None,
        period: str = "all",
    ) -> tuple[TrainerStatsDetailData | None, list[TrainerTrackStatsData], list[TrainerClassStatsData]]:
        """厩舎（調教師）の成績統計を取得する.

        Args:
            trainer_id: 調教師コード
            year: 年（指定時はその年の成績）
            period: 期間（recent=直近1年, all=通算）

        Returns:
            成績統計、コース別成績リスト、クラス別成績リストのタプル
        """
        pass

    @abstractmethod
    def get_stallion_offspring_stats(
        self,
        stallion_id: str,
        year: int | None = None,
        track_type: str | None = None,
    ) -> tuple[
        StallionOffspringStatsData | None,
        list[StallionTrackStatsData],
        list[StallionDistanceStatsData],
        list[StallionConditionStatsData],
        list[TopOffspringData],
    ]:
        """種牡馬の産駒成績統計を取得する.

        Args:
            stallion_id: 種牡馬コード（馬ID）
            year: 集計年度（省略時は通算）
            track_type: 芝/ダート/障害 でフィルタ

        Returns:
            (産駒成績統計, トラック別成績, 距離別成績, 馬場状態別成績, トップ産駒)
            見つからない場合は(None, [], [], [], [])
        """
        pass

    @abstractmethod
    def get_gate_position_stats(
        self,
        venue: str,
        track_type: str | None = None,
        distance: int | None = None,
        track_condition: str | None = None,
        limit: int = 100,
    ) -> "GatePositionStatsData | None":
        """枠順別成績統計を取得する.

        Args:
            venue: 競馬場（必須）
            track_type: 芝/ダート/障害
            distance: 距離（メートル）
            track_condition: 馬場状態（良/稍/重/不）
            limit: 集計対象レース数

        Returns:
            枠順別成績統計、データがない場合はNone
        """
        pass

    @abstractmethod
    def get_race_results(self, race_id: RaceId) -> "RaceResultsData | None":
        """レース結果・払戻金を取得する.

        Args:
            race_id: レースID

        Returns:
            レース結果データ、見つからない場合はNone
        """
        pass

    @abstractmethod
    def get_owner_info(self, owner_id: str) -> "OwnerInfoData | None":
        """馬主基本情報を取得する.

        Args:
            owner_id: 馬主コード

        Returns:
            馬主基本情報、見つからない場合はNone
        """
        pass

    @abstractmethod
    def get_owner_stats(
        self,
        owner_id: str,
        year: int | None = None,
        period: str = "all",
    ) -> "OwnerStatsData | None":
        """馬主成績統計を取得する.

        Args:
            owner_id: 馬主コード
            year: 年（指定時はその年の成績）
            period: 期間（recent=直近1年, all=通算）

        Returns:
            馬主成績統計、見つからない場合はNone
        """
        pass

    @abstractmethod
    def get_breeder_info(self, breeder_id: str) -> "BreederInfoData | None":
        """生産者基本情報を取得する.

        Args:
            breeder_id: 生産者コード

        Returns:
            生産者基本情報、見つからない場合はNone
        """
        pass

    @abstractmethod
    def get_breeder_stats(
        self,
        breeder_id: str,
        year: int | None = None,
        period: str = "all",
    ) -> "BreederStatsData | None":
        """生産者成績統計を取得する.

        Args:
            breeder_id: 生産者コード
            year: 年（指定時はその年の成績）
            period: 期間（recent=直近1年, all=通算）

        Returns:
            生産者成績統計、見つからない場合はNone
        """
        pass

    @abstractmethod
    def get_all_odds(self, race_id: RaceId) -> AllOddsData | None:
        """全券種のオッズを一括取得する.

        Args:
            race_id: レースID

        Returns:
            全券種オッズデータ、見つからない場合はNone
        """
        pass


@dataclass(frozen=True)
class GateStatsData:
    """枠番別成績データ."""

    gate: int  # 枠番（1-8）
    gate_range: str  # 例: "1-2枠"
    starts: int
    wins: int
    places: int
    win_rate: float
    place_rate: float
    avg_finish: float


@dataclass(frozen=True)
class HorseNumberStatsData:
    """馬番別成績データ."""

    horse_number: int
    starts: int
    wins: int
    win_rate: float


@dataclass(frozen=True)
class GateAnalysisData:
    """枠順分析データ."""

    favorable_gates: list[int]  # 有利な枠
    unfavorable_gates: list[int]  # 不利な枠
    comment: str


@dataclass(frozen=True)
class GatePositionConditionsData:
    """枠順統計の検索条件."""

    venue: str
    track_type: str | None
    distance: int | None
    track_condition: str | None


@dataclass(frozen=True)
class GatePositionStatsData:
    """枠順別成績統計データ."""

    conditions: GatePositionConditionsData
    total_races: int
    by_gate: list[GateStatsData]
    by_horse_number: list[HorseNumberStatsData]
    analysis: GateAnalysisData


@dataclass(frozen=True)
class RaceResultData:
    """レース結果データ（着順）."""

    horse_number: int
    horse_name: str
    finish_position: int
    time: str | None  # 例: "1:33.5"
    margin: str | None  # 例: "クビ"
    last_3f: str | None  # 上がり3ハロン
    popularity: int | None
    odds: float | None
    jockey_name: str | None


@dataclass(frozen=True)
class PayoutData:
    """払戻金データ."""

    bet_type: str  # 単勝/複勝/枠連/馬連/ワイド/馬単/三連複/三連単
    combination: str  # 例: "3", "3-5", "3-5-7"
    payout: int  # 払戻金（円）
    popularity: int | None  # 人気順


@dataclass(frozen=True)
class RaceResultsData:
    """レース結果総合データ."""

    race_id: str
    race_name: str
    race_date: str
    venue: str
    results: list[RaceResultData]
    payouts: list[PayoutData]
    is_finalized: bool  # 確定済みかどうか


@dataclass(frozen=True)
class OwnerInfoData:
    """馬主基本情報."""

    owner_id: str
    owner_name: str
    representative_name: str | None = None
    registered_year: int | None = None


@dataclass(frozen=True)
class OwnerStatsData:
    """馬主成績統計."""

    owner_id: str
    owner_name: str
    total_horses: int
    total_starts: int
    wins: int
    second_places: int
    third_places: int
    win_rate: float
    place_rate: float
    total_prize: int | None = None
    g1_wins: int = 0
    period: str = "all"
    year: int | None = None


@dataclass(frozen=True)
class BreederInfoData:
    """生産者基本情報."""

    breeder_id: str
    breeder_name: str
    location: str | None = None
    registered_year: int | None = None


@dataclass(frozen=True)
class BreederStatsData:
    """生産者成績統計."""

    breeder_id: str
    breeder_name: str
    total_horses: int
    total_starts: int
    wins: int
    second_places: int
    third_places: int
    win_rate: float
    place_rate: float
    total_prize: int | None = None
    g1_wins: int = 0
    period: str = "all"
    year: int | None = None