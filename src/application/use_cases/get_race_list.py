"""レース一覧取得ユースケース."""
from dataclasses import dataclass
from datetime import date

from src.domain.ports import RaceData, RaceDataProvider


@dataclass(frozen=True)
class RaceListResult:
    """レース一覧取得結果."""

    races: list[RaceData]
    venues: list[str]
    target_date: date


class GetRaceListUseCase:
    """レース一覧取得ユースケース."""

    def __init__(self, race_data_provider: RaceDataProvider) -> None:
        """初期化.

        Args:
            race_data_provider: レースデータプロバイダー
        """
        self._race_data_provider = race_data_provider

    def execute(self, target_date: date, venue: str | None = None) -> RaceListResult:
        """レース一覧を取得する.

        Args:
            target_date: 対象日付
            venue: 開催場（指定しない場合は全開催場）

        Returns:
            レース一覧取得結果
        """
        races = self._race_data_provider.get_races_by_date(target_date, venue)
        venues = sorted(set(r.venue for r in races))

        return RaceListResult(
            races=races,
            venues=venues,
            target_date=target_date,
        )
