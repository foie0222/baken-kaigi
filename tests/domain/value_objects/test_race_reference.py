"""RaceReferenceのテスト."""
from datetime import datetime, timedelta

import pytest

from src.domain.identifiers import RaceId
from src.domain.value_objects import RaceReference


class TestRaceReference:
    """RaceReferenceの単体テスト."""

    def test_有効なレース参照を生成できる(self) -> None:
        """有効なレース参照情報を生成できることを確認."""
        deadline = datetime(2024, 1, 1, 15, 30)
        start_time = datetime(2024, 1, 1, 15, 40)
        ref = RaceReference(
            race_id=RaceId("2024010101"),
            race_name="日本ダービー",
            race_number=11,
            venue="東京",
            start_time=start_time,
            betting_deadline=deadline,
        )
        assert ref.race_name == "日本ダービー"
        assert ref.race_number == 11
        assert ref.venue == "東京"

    def test_空のレース名でエラー(self) -> None:
        """空のレース名を指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="Race name cannot be empty"):
            RaceReference(
                race_id=RaceId("2024010101"),
                race_name="",
                race_number=1,
                venue="東京",
                start_time=datetime(2024, 1, 1, 15, 40),
                betting_deadline=datetime(2024, 1, 1, 15, 30),
            )

    def test_レース番号が0でエラー(self) -> None:
        """レース番号が0だとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="between 1 and 12"):
            RaceReference(
                race_id=RaceId("2024010101"),
                race_name="テスト",
                race_number=0,
                venue="東京",
                start_time=datetime(2024, 1, 1, 15, 40),
                betting_deadline=datetime(2024, 1, 1, 15, 30),
            )

    def test_レース番号が13でエラー(self) -> None:
        """レース番号が13だとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="between 1 and 12"):
            RaceReference(
                race_id=RaceId("2024010101"),
                race_name="テスト",
                race_number=13,
                venue="東京",
                start_time=datetime(2024, 1, 1, 15, 40),
                betting_deadline=datetime(2024, 1, 1, 15, 30),
            )

    def test_空の開催場でエラー(self) -> None:
        """空の開催場を指定するとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="Venue cannot be empty"):
            RaceReference(
                race_id=RaceId("2024010101"),
                race_name="テスト",
                race_number=1,
                venue="",
                start_time=datetime(2024, 1, 1, 15, 40),
                betting_deadline=datetime(2024, 1, 1, 15, 30),
            )

    def test_締め切りが発走後でエラー(self) -> None:
        """締め切りが発走時刻より後だとValueErrorが発生することを確認."""
        with pytest.raises(ValueError, match="before start time"):
            RaceReference(
                race_id=RaceId("2024010101"),
                race_name="テスト",
                race_number=1,
                venue="東京",
                start_time=datetime(2024, 1, 1, 15, 30),
                betting_deadline=datetime(2024, 1, 1, 15, 40),  # 発走後
            )

    def test_is_before_deadlineで締め切り前はTrue(self) -> None:
        """is_before_deadlineで締め切り前の場合Trueが返ることを確認."""
        deadline = datetime(2024, 1, 1, 15, 30)
        ref = RaceReference(
            race_id=RaceId("2024010101"),
            race_name="テスト",
            race_number=1,
            venue="東京",
            start_time=datetime(2024, 1, 1, 15, 40),
            betting_deadline=deadline,
        )
        now = datetime(2024, 1, 1, 15, 0)  # 締め切り30分前
        assert ref.is_before_deadline(now) is True

    def test_is_before_deadlineで締め切り後はFalse(self) -> None:
        """is_before_deadlineで締め切り後の場合Falseが返ることを確認."""
        deadline = datetime(2024, 1, 1, 15, 30)
        ref = RaceReference(
            race_id=RaceId("2024010101"),
            race_name="テスト",
            race_number=1,
            venue="東京",
            start_time=datetime(2024, 1, 1, 15, 40),
            betting_deadline=deadline,
        )
        now = datetime(2024, 1, 1, 16, 0)  # 締め切り後
        assert ref.is_before_deadline(now) is False

    def test_get_remaining_timeで残り時間を取得(self) -> None:
        """get_remaining_timeで締め切りまでの残り時間を取得できることを確認."""
        deadline = datetime(2024, 1, 1, 15, 30)
        ref = RaceReference(
            race_id=RaceId("2024010101"),
            race_name="テスト",
            race_number=1,
            venue="東京",
            start_time=datetime(2024, 1, 1, 15, 40),
            betting_deadline=deadline,
        )
        now = datetime(2024, 1, 1, 15, 0)
        remaining = ref.get_remaining_time(now)
        assert remaining == timedelta(minutes=30)

    def test_get_remaining_timeで締め切り後はNone(self) -> None:
        """get_remaining_timeで締め切り後の場合Noneが返ることを確認."""
        deadline = datetime(2024, 1, 1, 15, 30)
        ref = RaceReference(
            race_id=RaceId("2024010101"),
            race_name="テスト",
            race_number=1,
            venue="東京",
            start_time=datetime(2024, 1, 1, 15, 40),
            betting_deadline=deadline,
        )
        now = datetime(2024, 1, 1, 16, 0)
        assert ref.get_remaining_time(now) is None

    def test_to_display_stringで表示用文字列(self) -> None:
        """to_display_stringで表示用文字列を取得できることを確認."""
        ref = RaceReference(
            race_id=RaceId("2024010101"),
            race_name="日本ダービー",
            race_number=11,
            venue="東京",
            start_time=datetime(2024, 1, 1, 15, 40),
            betting_deadline=datetime(2024, 1, 1, 15, 30),
        )
        assert ref.to_display_string() == "東京11R 日本ダービー"

    def test_不変オブジェクトである(self) -> None:
        """RaceReferenceは不変（frozen）であることを確認."""
        ref = RaceReference(
            race_id=RaceId("2024010101"),
            race_name="テスト",
            race_number=1,
            venue="東京",
            start_time=datetime(2024, 1, 1, 15, 40),
            betting_deadline=datetime(2024, 1, 1, 15, 30),
        )
        with pytest.raises(AttributeError):
            ref.race_name = "変更"  # type: ignore
