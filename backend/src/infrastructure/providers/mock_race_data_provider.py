"""モックレースデータプロバイダー."""
from datetime import date, datetime, timedelta

from src.domain.identifiers import RaceId
from src.domain.ports import (
    JockeyStatsData,
    PerformanceData,
    RaceData,
    RaceDataProvider,
    RunnerData,
)


class MockRaceDataProvider(RaceDataProvider):
    """モックレースデータプロバイダー（開発・デモ用）."""

    # サンプルの開催場
    VENUES = ["東京", "中山", "阪神", "京都", "中京", "小倉", "新潟", "札幌"]

    # サンプルの馬名
    HORSE_NAMES = [
        "サイレンススズカ",
        "ディープインパクト",
        "オルフェーヴル",
        "キタサンブラック",
        "アーモンドアイ",
        "イクイノックス",
        "ドウデュース",
        "リバティアイランド",
        "ソールオリエンス",
        "タスティエーラ",
        "スターズオンアース",
        "ジャックドール",
        "シャフリヤール",
        "エフフォーリア",
        "コントレイル",
        "デアリングタクト",
        "クロノジェネシス",
        "グランアレグリア",
    ]

    # サンプルの騎手名
    JOCKEY_NAMES = [
        "川田将雅",
        "ルメール",
        "モレイラ",
        "横山武史",
        "松山弘平",
        "戸崎圭太",
        "福永祐一",
        "武豊",
        "横山典弘",
        "岩田望来",
        "田辺裕信",
        "三浦皇成",
        "丸山元気",
        "池添謙一",
        "藤岡佑介",
        "坂井瑠星",
        "吉田隼人",
        "浜中俊",
    ]

    # サンプルのレース名
    RACE_NAMES = [
        "メイクデビュー",
        "未勝利",
        "1勝クラス",
        "2勝クラス",
        "3勝クラス",
        "オープン",
        "リステッド",
        "G3",
        "G2",
        "G1",
    ]

    def __init__(self) -> None:
        """初期化."""
        self._races: dict[str, RaceData] = {}
        self._runners: dict[str, list[RunnerData]] = {}

    def get_race(self, race_id: RaceId) -> RaceData | None:
        """レース情報を取得する."""
        race_id_str = str(race_id)

        # キャッシュにあればそれを返す
        if race_id_str in self._races:
            return self._races[race_id_str]

        # レースIDをパースして情報を生成
        # フォーマット: YYYYMMDD_VENUE_RACE_NUMBER (例: 20240120_tokyo_01)
        parts = race_id_str.split("_")
        if len(parts) < 3:
            return None

        try:
            date_str = parts[0]
            venue = parts[1]
            race_num = int(parts[2])
            target_date = datetime.strptime(date_str, "%Y%m%d")
        except (ValueError, IndexError):
            return None

        # レースデータを生成
        race = self._generate_race_data(
            race_id_str, target_date.date(), venue, race_num
        )
        self._races[race_id_str] = race
        return race

    def get_races_by_date(
        self, target_date: date, venue: str | None = None
    ) -> list[RaceData]:
        """日付でレース一覧を取得する."""
        races = []
        date_str = target_date.strftime("%Y%m%d")

        # 指定会場または複数会場のレースを生成
        venues_to_use = [venue] if venue else self.VENUES[:3]  # デフォルトは3会場

        for v in venues_to_use:
            venue_lower = v.lower()
            for race_num in range(1, 13):  # 1R〜12R
                race_id = f"{date_str}_{venue_lower}_{race_num:02d}"
                race = self._generate_race_data(race_id, target_date, v, race_num)
                races.append(race)
                self._races[race_id] = race

        # 開催場、レース番号順でソート
        races.sort(key=lambda r: (r.venue, r.race_number))
        return races

    def get_runners(self, race_id: RaceId) -> list[RunnerData]:
        """出走馬情報を取得する."""
        race_id_str = str(race_id)

        # キャッシュにあればそれを返す
        if race_id_str in self._runners:
            return self._runners[race_id_str]

        # 出走馬を生成（8〜18頭）
        import random

        random.seed(hash(race_id_str) % (2**32))
        num_runners = random.randint(8, 18)

        # 枠番を計算（JRA方式）
        waku_assignments = self._calculate_waku_assignments(num_runners)

        runners = []
        used_names = set()

        for i in range(1, num_runners + 1):
            # ユニークな馬名を選択
            available_names = [n for n in self.HORSE_NAMES if n not in used_names]
            if not available_names:
                available_names = self.HORSE_NAMES
            horse_name = random.choice(available_names)
            used_names.add(horse_name)

            jockey_name = random.choice(self.JOCKEY_NAMES)

            # オッズを生成（人気順に基づく）
            base_odds = 1.5 + (i - 1) * random.uniform(0.5, 3.0)
            odds_str = f"{base_odds:.1f}"

            runner = RunnerData(
                horse_number=i,
                horse_name=horse_name,
                horse_id=f"horse_{hash(horse_name) % 10000:04d}",
                jockey_name=jockey_name,
                jockey_id=f"jockey_{hash(jockey_name) % 1000:03d}",
                odds=odds_str,
                popularity=i,
                waku_ban=waku_assignments[i - 1],
            )
            runners.append(runner)

        # オッズで並び替えて人気を再設定
        runners.sort(key=lambda r: float(r.odds))
        runners = [
            RunnerData(
                horse_number=r.horse_number,
                horse_name=r.horse_name,
                horse_id=r.horse_id,
                jockey_name=r.jockey_name,
                jockey_id=r.jockey_id,
                odds=r.odds,
                popularity=idx + 1,
                waku_ban=r.waku_ban,
            )
            for idx, r in enumerate(runners)
        ]

        # 馬番順に戻す
        runners.sort(key=lambda r: r.horse_number)

        self._runners[race_id_str] = runners
        return runners

    def _calculate_waku_assignments(self, num_runners: int) -> list[int]:
        """馬番に対する枠番を計算する（JRA方式）.

        JRAの枠番割り当てルール:
        - 8頭以下: 馬番=枠番
        - 9頭以上: 8枠に均等に割り当て、後ろの枠から複数頭になる
        """
        if num_runners <= 8:
            return list(range(1, num_runners + 1))

        # 9頭以上の場合
        waku_assignments = []
        extra_horses = num_runners - 8  # 8枠を超える馬の数

        for horse_num in range(1, num_runners + 1):
            if num_runners <= 16:
                # 9-16頭: 後ろの枠から2頭ずつ
                if horse_num <= (8 - extra_horses):
                    waku = horse_num
                else:
                    waku = 8 - ((num_runners - horse_num) // 2)
            else:
                # 17-18頭: より複雑な割り当て
                if horse_num == 1:
                    waku = 1
                elif horse_num == 2:
                    waku = 2
                elif horse_num <= 4:
                    waku = 3
                elif horse_num <= 6:
                    waku = 4
                elif horse_num <= 8:
                    waku = 5
                elif horse_num <= 11:
                    waku = 6
                elif horse_num <= 14:
                    waku = 7
                else:
                    waku = 8

            waku_assignments.append(waku)

        return waku_assignments

    def get_past_performance(self, horse_id: str) -> list[PerformanceData]:
        """馬の過去成績を取得する."""
        import random

        random.seed(hash(horse_id) % (2**32))

        performances = []
        base_date = datetime.now()

        # 過去5走を生成
        for i in range(5):
            race_date = base_date - timedelta(days=30 * (i + 1))
            venue = random.choice(self.VENUES)
            distance = random.choice([1200, 1400, 1600, 1800, 2000, 2200, 2400])
            finish = random.choices(
                range(1, 19),
                weights=[10, 8, 7, 6, 5, 4, 3, 3, 3, 2, 2, 2, 2, 2, 1, 1, 1, 1],
            )[0]

            minutes = distance // 1000
            seconds = (distance % 1000) / 100 * 6 + random.uniform(0, 5)
            time_str = f"{minutes}:{seconds:04.1f}"

            track_conditions = ["良", "稍重", "重", "不良"]
            track_condition = random.choices(
                track_conditions, weights=[6, 2, 1, 1]
            )[0]

            perf = PerformanceData(
                race_date=race_date,
                race_name=f"{venue}{distance}m {random.choice(self.RACE_NAMES)}",
                venue=venue,
                finish_position=finish,
                distance=distance,
                track_condition=track_condition,
                time=time_str,
            )
            performances.append(perf)

        return performances

    def get_jockey_stats(self, jockey_id: str, course: str) -> JockeyStatsData | None:
        """騎手のコース成績を取得する."""
        import random

        random.seed(hash(f"{jockey_id}_{course}") % (2**32))

        # 騎手名を特定
        jockey_index = int(jockey_id.split("_")[1]) % len(self.JOCKEY_NAMES)
        jockey_name = self.JOCKEY_NAMES[jockey_index]

        total_races = random.randint(50, 500)
        win_rate = random.uniform(0.05, 0.25)
        wins = int(total_races * win_rate)
        place_rate = random.uniform(win_rate, min(win_rate * 3, 0.6))

        return JockeyStatsData(
            jockey_id=jockey_id,
            jockey_name=jockey_name,
            course=course,
            total_races=total_races,
            wins=wins,
            win_rate=win_rate,
            place_rate=place_rate,
        )

    def _generate_race_data(
        self, race_id: str, target_date: date, venue: str, race_number: int
    ) -> RaceData:
        """レースデータを生成する."""
        import random

        random.seed(hash(race_id) % (2**32))

        # レース名を決定
        if race_number <= 4:
            race_name = random.choice(["メイクデビュー", "未勝利", "1勝クラス"])
        elif race_number <= 8:
            race_name = random.choice(["1勝クラス", "2勝クラス", "3勝クラス"])
        elif race_number <= 10:
            race_name = random.choice(["3勝クラス", "オープン", "リステッド"])
        else:
            race_name = random.choice(["オープン", "リステッド", "G3", "G2", "G1"])

        # 開始時刻（10:00〜16:30）
        hour = 10 + (race_number - 1) // 2
        minute = 30 if race_number % 2 == 0 else 0
        start_time = datetime.combine(
            target_date, datetime.min.time()
        ).replace(hour=hour, minute=minute)

        # 締切は発走の2分前
        betting_deadline = start_time - timedelta(minutes=2)

        # 馬場状態
        track_conditions = ["良", "稍重", "重", "不良"]
        track_condition = random.choices(
            track_conditions, weights=[7, 2, 0.5, 0.5]
        )[0]

        return RaceData(
            race_id=race_id,
            race_name=f"{venue}{race_number}R {race_name}",
            race_number=race_number,
            venue=venue,
            start_time=start_time,
            betting_deadline=betting_deadline,
            track_condition=track_condition,
        )
