"""レース詳細取得ユースケース."""
from dataclasses import dataclass

from src.domain.identifiers import RaceId
from src.domain.ports import RaceData, RaceDataProvider, RunnerData


@dataclass(frozen=True)
class RaceDetailResult:
    """レース詳細取得結果."""

    race: RaceData
    runners: list[RunnerData]


class GetRaceDetailUseCase:
    """レース詳細取得ユースケース."""

    def __init__(self, race_data_provider: RaceDataProvider) -> None:
        """初期化.

        Args:
            race_data_provider: レースデータプロバイダー
        """
        self._race_data_provider = race_data_provider

    def execute(self, race_id: RaceId) -> RaceDetailResult | None:
        """レース詳細を取得する.

        Args:
            race_id: レースID

        Returns:
            レース詳細取得結果（存在しない場合はNone）
        """
        race = self._race_data_provider.get_race(race_id)
        if race is None:
            return None

        runners = self._race_data_provider.get_runners(race_id)

        return RaceDetailResult(
            race=race,
            runners=runners,
        )
