"""モックレースデータプロバイダー."""
import hashlib
from datetime import date, datetime, timedelta

from src.domain.identifiers import RaceId
from src.domain.ports import (
    AncestorData,
    ExtendedPedigreeData,
    HorsePerformanceData,
    InbreedingData,
    JockeyInfoData,
    JockeyStatsData,
    JockeyStatsDetailData,
    PastRaceStats,
    PedigreeData,
    PerformanceData,
    PopularityStats,
    RaceData,
    RaceDataProvider,
    RunnerData,
    TrainerClassStatsData,
    TrainerInfoData,
    TrainerStatsDetailData,
    TrainerTrackStatsData,
    TrainingRecordData,
    TrainingSummaryData,
    WeightData,
)


def _stable_hash(s: str) -> int:
    """文字列から安定したハッシュ値を返す.

    Python の組み込み hash() はセッション間でランダム化されるため、
    hashlib を使用して再現可能なハッシュ値を得る。
    """
    return int(hashlib.md5(s.encode()).hexdigest(), 16)


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

    # サンプルの調教師名
    TRAINER_NAMES = [
        "矢作芳人",
        "国枝栄",
        "堀宣行",
        "藤沢和雄",
        "友道康夫",
        "池江泰寿",
        "中内田充正",
        "手塚貴久",
        "須貝尚介",
        "角居勝彦",
        "音無秀孝",
        "藤原英昭",
        "松永幹夫",
        "池添学",
        "木村哲也",
        "西村真幸",
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

    # サンプルの種牡馬名
    SIRE_NAMES = [
        "ディープインパクト",
        "キングカメハメハ",
        "ハーツクライ",
        "ロードカナロア",
        "エピファネイア",
        "キズナ",
        "ドゥラメンテ",
        "モーリス",
        "サトノダイヤモンド",
        "コントレイル",
    ]

    # サンプルの繁殖牝馬名
    DAM_NAMES = [
        "ウインドインハーヘア",
        "シーザリオ",
        "アパパネ",
        "ブエナビスタ",
        "ジェンティルドンナ",
        "リスグラシュー",
        "アーモンドアイ",
        "グランアレグリア",
        "デアリングタクト",
        "ソダシ",
    ]

    # サンプルの母父馬名
    BROODMARE_SIRE_NAMES = [
        "サンデーサイレンス",
        "スペシャルウィーク",
        "ダンスインザダーク",
        "クロフネ",
        "マンハッタンカフェ",
        "ネオユニヴァース",
        "ゼンノロブロイ",
        "シンボリクリスエス",
        "タニノギムレット",
        "アグネスタキオン",
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

        random.seed(_stable_hash(race_id_str) % (2**32))
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
                horse_id=f"horse_{_stable_hash(horse_name) % 10000:04d}",
                jockey_name=jockey_name,
                jockey_id=f"jockey_{_stable_hash(jockey_name) % 1000:03d}",
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

        random.seed(_stable_hash(horse_id) % (2**32))

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

        random.seed(_stable_hash(f"{jockey_id}_{course}") % (2**32))

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

    def get_pedigree(self, horse_id: str) -> PedigreeData | None:
        """馬の血統情報を取得する."""
        import random

        random.seed(_stable_hash(horse_id) % (2**32))

        # 馬名を生成（horse_idから推定）
        horse_index = int(horse_id.split("_")[1]) % len(self.HORSE_NAMES)
        horse_name = self.HORSE_NAMES[horse_index]

        sire_name = random.choice(self.SIRE_NAMES)
        dam_name = random.choice(self.DAM_NAMES)
        broodmare_sire = random.choice(self.BROODMARE_SIRE_NAMES)

        return PedigreeData(
            horse_id=horse_id,
            horse_name=horse_name,
            sire_name=sire_name,
            dam_name=dam_name,
            broodmare_sire=broodmare_sire,
        )

    def get_weight_history(self, horse_id: str, limit: int = 5) -> list[WeightData]:
        """馬の体重履歴を取得する."""
        import random

        random.seed(_stable_hash(horse_id) % (2**32))

        weights = []
        base_weight = random.randint(440, 520)

        for i in range(limit):
            # 前走との差を生成
            weight_diff = random.randint(-10, 10)
            weight = base_weight + weight_diff * (limit - i - 1)

            weights.append(WeightData(
                weight=weight,
                weight_diff=weight_diff if i > 0 else 0,
            ))

        return weights

    def get_race_weights(self, race_id: RaceId) -> dict[int, WeightData]:
        """レースの馬体重情報を取得する."""
        import random

        race_id_str = str(race_id)
        random.seed(_stable_hash(race_id_str) % (2**32))

        # 出走馬リストを取得
        runners = self.get_runners(race_id)
        weights: dict[int, WeightData] = {}

        for runner in runners:
            base_weight = random.randint(440, 520)
            weight_diff = random.randint(-10, 10)

            weights[runner.horse_number] = WeightData(
                weight=base_weight,
                weight_diff=weight_diff,
            )

        return weights

    def get_jra_checksum(
        self,
        venue_code: str,
        kaisai_kai: str,
        kaisai_nichime: int,
        race_number: int,
    ) -> int | None:
        """JRA出馬表URLのチェックサムを取得する（モック実装）."""
        # モックでは常にNoneを返す（JRA URLは生成されない）
        return None

    def get_race_dates(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[date]:
        """開催日一覧を取得する（モック実装）.

        モックでは前週と次週の土日（最大4日）を返す。
        """
        today = date.today()
        # 直近の土曜日を計算
        days_since_saturday = (today.weekday() + 2) % 7
        last_saturday = today - timedelta(days=days_since_saturday)
        last_sunday = last_saturday + timedelta(days=1)

        # 次の土曜日
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7
        next_saturday = today + timedelta(days=days_until_saturday)
        next_sunday = next_saturday + timedelta(days=1)

        dates = [next_sunday, next_saturday, last_sunday, last_saturday]

        # フィルタリング
        if from_date:
            dates = [d for d in dates if d >= from_date]
        if to_date:
            dates = [d for d in dates if d <= to_date]

        return sorted(dates, reverse=True)

    def get_past_race_stats(
        self,
        track_type: str,
        distance: int,
        grade_class: str | None = None,
        limit: int = 100
    ) -> PastRaceStats | None:
        """過去の同条件レース統計を取得する（モック実装）."""
        import random

        random.seed(_stable_hash(f"{track_type}_{distance}_{grade_class}") % (2**32))

        # モックデータを生成
        popularity_stats = []
        for pop in range(1, 19):
            total_runs = random.randint(50, 100)
            wins = int(total_runs * (0.35 - pop * 0.02) if pop <= 5 else total_runs * 0.02)
            places = int(total_runs * (0.60 - pop * 0.03) if pop <= 10 else total_runs * 0.10)

            popularity_stats.append(PopularityStats(
                popularity=pop,
                total_runs=total_runs,
                wins=max(wins, 0),
                places=max(places, 0),
                win_rate=round(max(wins, 0) / total_runs * 100, 1) if total_runs > 0 else 0,
                place_rate=round(max(places, 0) / total_runs * 100, 1) if total_runs > 0 else 0,
            ))

        return PastRaceStats(
            total_races=limit,
            popularity_stats=popularity_stats,
            avg_win_payout=random.uniform(300, 500),
            avg_place_payout=random.uniform(150, 250),
            track_type=track_type,
            distance=distance,
            grade_class=grade_class,
        )

    def get_jockey_info(self, jockey_id: str) -> JockeyInfoData | None:
        """騎手基本情報を取得する（モック実装）."""
        import random

        random.seed(_stable_hash(jockey_id) % (2**32))

        # 騎手名を特定
        try:
            jockey_index = int(jockey_id.split("_")[1]) % len(self.JOCKEY_NAMES)
        except (IndexError, ValueError):
            jockey_index = _stable_hash(jockey_id) % len(self.JOCKEY_NAMES)
        jockey_name = self.JOCKEY_NAMES[jockey_index]

        # モックデータを生成
        birth_year = random.randint(1970, 2000)
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)
        birth_date = f"{birth_year:04d}-{birth_month:02d}-{birth_day:02d}"

        affiliation = random.choice(["美浦", "栗東"])
        license_year = random.randint(1988, 2020)

        return JockeyInfoData(
            jockey_id=jockey_id,
            jockey_name=jockey_name,
            jockey_name_kana=None,  # モックではカナは省略
            birth_date=birth_date,
            affiliation=affiliation,
            license_year=license_year,
        )

    def get_jockey_stats_detail(
        self,
        jockey_id: str,
        year: int | None = None,
        period: str = "recent",
    ) -> JockeyStatsDetailData | None:
        """騎手の成績統計を取得する（モック実装）."""
        import random

        random.seed(_stable_hash(f"{jockey_id}_{year}_{period}") % (2**32))

        # 騎手名を特定
        try:
            jockey_index = int(jockey_id.split("_")[1]) % len(self.JOCKEY_NAMES)
        except (IndexError, ValueError):
            jockey_index = _stable_hash(jockey_id) % len(self.JOCKEY_NAMES)
        jockey_name = self.JOCKEY_NAMES[jockey_index]

        total_rides = random.randint(200, 800)
        win_rate = random.uniform(0.08, 0.20)
        wins = int(total_rides * win_rate)
        second_places = int(total_rides * random.uniform(0.08, 0.15))
        third_places = int(total_rides * random.uniform(0.08, 0.15))
        places = wins + second_places + third_places
        place_rate = round(places / total_rides * 100, 1) if total_rides > 0 else 0.0

        return JockeyStatsDetailData(
            jockey_id=jockey_id,
            jockey_name=jockey_name,
            total_rides=total_rides,
            wins=wins,
            second_places=second_places,
            third_places=third_places,
            win_rate=round(win_rate * 100, 1),
            place_rate=place_rate,
            period=period if not year else "year",
            year=year,
        )

    def get_horse_performances(
        self,
        horse_id: str,
        limit: int = 5,
        track_type: str | None = None,
    ) -> list[HorsePerformanceData]:
        """馬の過去成績を詳細に取得する（モック実装）."""
        import random

        random.seed(_stable_hash(horse_id) % (2**32))

        performances = []
        base_date = datetime.now()
        track_types = ["芝", "ダート", "障害"]
        track_conditions = ["良", "稍", "重", "不"]
        margins = ["クビ", "ハナ", "1/2", "3/4", "1", "1 1/2", "2", "3", "大差"]
        paces = ["S", "M", "H"]
        styles = ["逃げ", "先行", "差し", "追込"]

        # 馬名を特定
        try:
            horse_index = int(horse_id.split("_")[1]) % len(self.HORSE_NAMES)
        except (IndexError, ValueError):
            horse_index = _stable_hash(horse_id) % len(self.HORSE_NAMES)
        horse_name = self.HORSE_NAMES[horse_index]

        # フィルタを考慮して多めにループ
        for i in range(min(limit * 2, 40)):
            if len(performances) >= limit:
                break
            race_date = base_date - timedelta(days=30 * (i + 1))
            tt = random.choice(track_types)

            # track_typeでフィルタ
            if track_type and tt != track_type:
                continue

            venue = random.choice(self.VENUES)
            distance = random.choice([1200, 1400, 1600, 1800, 2000, 2200, 2400])
            finish = random.choices(
                range(1, 19),
                weights=[10, 8, 7, 6, 5, 4, 3, 3, 3, 2, 2, 2, 2, 2, 1, 1, 1, 1],
            )[0]
            total_runners = random.randint(max(finish, 8), 18)

            minutes = distance // 1000
            seconds = (distance % 1000) / 100 * 6 + random.uniform(0, 5)
            time_str = f"{minutes}:{seconds:04.1f}"

            track_condition = random.choices(
                track_conditions, weights=[6, 2, 1, 1]
            )[0]

            jockey = random.choice(self.JOCKEY_NAMES)
            odds_val = random.uniform(1.5, 50.0)
            pop = random.randint(1, total_runners)

            perf = HorsePerformanceData(
                race_id=f"{race_date.strftime('%Y%m%d')}_{venue.lower()}_{random.randint(1,12):02d}",
                race_date=race_date.strftime("%Y%m%d"),
                race_name=f"{venue}{distance}m {random.choice(self.RACE_NAMES)}",
                venue=venue,
                distance=distance,
                track_type=tt,
                track_condition=track_condition,
                finish_position=finish,
                total_runners=total_runners,
                time=time_str,
                horse_name=horse_name,
                time_diff=f"+{random.uniform(0, 2.0):.1f}" if finish > 1 else None,
                last_3f=f"{random.uniform(33.0, 37.0):.1f}",
                weight_carried=random.choice([54.0, 55.0, 56.0, 57.0, 58.0]),
                jockey_name=jockey,
                odds=round(odds_val, 1),
                popularity=pop,
                margin=random.choice(margins) if finish > 1 else None,
                race_pace=random.choice(paces),
                running_style=random.choice(styles),
            )
            performances.append(perf)

        return performances[:limit]

    def get_horse_training(
        self,
        horse_id: str,
        limit: int = 5,
        days: int = 30,
    ) -> tuple[list[TrainingRecordData], TrainingSummaryData | None]:
        """馬の調教データを取得する（モック実装）."""
        import random

        random.seed(_stable_hash(horse_id) % (2**32))

        training_courses = [
            "栗東CW", "栗東坂路", "栗東P", "栗東芝",
            "美浦南W", "美浦坂路", "美浦北C", "美浦南P"
        ]
        course_conditions = ["良", "稍", "重", "不"]
        training_types = ["馬なり", "一杯", "強め", "仕掛け", "叩き一杯"]
        evaluations = ["A", "B", "C", "D"]

        records = []
        base_date = datetime.now()
        times = []

        for i in range(limit):
            # days以内のランダムな日付
            training_date = base_date - timedelta(days=random.randint(1, days))
            course = random.choice(training_courses)

            # 距離によってタイムを変える
            distance = random.choice([800, 1000, 1200])
            base_time = 51.0 + (distance - 800) / 200 * 5
            time_val = base_time + random.uniform(-2, 3)
            time_str = f"{time_val:.1f}"
            times.append(time_val)

            last_3f = f"{random.uniform(11.5, 13.5):.1f}"
            last_1f = f"{random.uniform(11.5, 13.0):.1f}"

            # 併せ馬（50%の確率）
            partner = random.choice(self.HORSE_NAMES) if random.random() > 0.5 else None

            record = TrainingRecordData(
                date=training_date.strftime("%Y%m%d"),
                course=course,
                course_condition=random.choices(course_conditions, weights=[6, 2, 1, 1])[0],
                distance=distance,
                time=time_str,
                last_3f=last_3f,
                last_1f=last_1f,
                training_type=random.choice(training_types),
                partner_horse=partner,
                evaluation=random.choices(evaluations, weights=[2, 4, 3, 1])[0],
                comment=None,
            )
            records.append(record)

        # サマリーを生成
        if times:
            avg_time = sum(times) / len(times)
            best_time = min(times)
            # 最近のトレンドを判定（最新3件の平均と残りの平均を比較）
            if len(times) >= 3:
                recent_avg = sum(times[:3]) / 3
                older_avg = sum(times[3:]) / max(len(times) - 3, 1) if len(times) > 3 else recent_avg
                if recent_avg < older_avg - 0.3:
                    trend = "上昇"
                elif recent_avg > older_avg + 0.3:
                    trend = "下降"
                else:
                    trend = "平行"
            else:
                trend = "平行"

            summary = TrainingSummaryData(
                recent_trend=trend,
                average_time=f"{avg_time:.1f}",
                best_time=f"{best_time:.1f}",
            )
        else:
            summary = None

        return records, summary

    def get_extended_pedigree(self, horse_id: str) -> ExtendedPedigreeData | None:
        """馬の拡張血統情報（3代血統）を取得する（モック実装）."""
        import random

        # nonexistent で始まるIDの場合はNoneを返す
        if horse_id.startswith("nonexistent"):
            return None

        random.seed(_stable_hash(horse_id) % (2**32))

        # 馬名を特定
        try:
            horse_index = int(horse_id.split("_")[1]) % len(self.HORSE_NAMES)
        except (IndexError, ValueError):
            horse_index = _stable_hash(horse_id) % len(self.HORSE_NAMES)
        horse_name = self.HORSE_NAMES[horse_index]

        # 父の情報
        sire_name = random.choice(self.SIRE_NAMES)
        sire_sire = random.choice(self.SIRE_NAMES)
        sire_dam = random.choice(self.DAM_NAMES)
        sire_broodmare_sire = random.choice(self.BROODMARE_SIRE_NAMES)
        sire = AncestorData(
            name=sire_name,
            sire=sire_sire,
            dam=sire_dam,
            broodmare_sire=sire_broodmare_sire,
        )

        # 母の情報
        dam_name = random.choice(self.DAM_NAMES)
        dam_sire = random.choice(self.BROODMARE_SIRE_NAMES)  # 母父
        dam_dam = random.choice(self.DAM_NAMES)
        dam_broodmare_sire = random.choice(self.BROODMARE_SIRE_NAMES)
        dam = AncestorData(
            name=dam_name,
            sire=dam_sire,
            dam=dam_dam,
            broodmare_sire=dam_broodmare_sire,
        )

        # インブリード情報を生成（50%の確率で存在）
        inbreeding = []
        if random.random() < 0.5:
            common_ancestor = random.choice(self.SIRE_NAMES + self.BROODMARE_SIRE_NAMES)
            patterns = ["3x3", "3x4", "4x4", "3x5", "4x5", "5x5"]
            percentages = {"3x3": 12.5, "3x4": 9.375, "4x4": 6.25, "3x5": 6.25, "4x5": 4.6875, "5x5": 3.125}
            pattern = random.choice(patterns)
            inbreeding.append(InbreedingData(
                ancestor=common_ancestor,
                pattern=pattern,
                percentage=percentages[pattern],
            ))
            # 2つ目のインブリード（20%の確率）
            if random.random() < 0.2:
                common_ancestor2 = random.choice(self.SIRE_NAMES + self.BROODMARE_SIRE_NAMES)
                pattern2 = random.choice(patterns)
                inbreeding.append(InbreedingData(
                    ancestor=common_ancestor2,
                    pattern=pattern2,
                    percentage=percentages[pattern2],
                ))

        # 系統タイプを決定（父の父で判定）
        lineage_types = {
            "ディープインパクト": "サンデーサイレンス系",
            "キングカメハメハ": "キングマンボ系",
            "ハーツクライ": "サンデーサイレンス系",
            "ロードカナロア": "キングマンボ系",
            "エピファネイア": "シンボリクリスエス系",
            "キズナ": "サンデーサイレンス系",
            "ドゥラメンテ": "キングマンボ系",
            "モーリス": "ロベルト系",
            "サトノダイヤモンド": "サンデーサイレンス系",
            "コントレイル": "サンデーサイレンス系",
        }
        lineage_type = lineage_types.get(sire_sire, "その他")

        return ExtendedPedigreeData(
            horse_id=horse_id,
            horse_name=horse_name,
            sire=sire,
            dam=dam,
            inbreeding=inbreeding,
            lineage_type=lineage_type,
        )

    def _generate_race_data(
        self, race_id: str, target_date: date, venue: str, race_number: int
    ) -> RaceData:
        """レースデータを生成する."""
        import random

        random.seed(_stable_hash(race_id) % (2**32))

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

    def get_trainer_info(self, trainer_id: str) -> TrainerInfoData | None:
        """厩舎（調教師）基本情報を取得する（モック実装）."""
        import random

        # nonexistent で始まるIDの場合はNoneを返す
        if trainer_id.startswith("nonexistent"):
            return None

        random.seed(_stable_hash(trainer_id) % (2**32))

        # 調教師名を特定
        try:
            trainer_index = int(trainer_id.split("_")[1]) % len(self.TRAINER_NAMES)
        except (IndexError, ValueError):
            trainer_index = _stable_hash(trainer_id) % len(self.TRAINER_NAMES)
        trainer_name = self.TRAINER_NAMES[trainer_index]

        affiliation = random.choice(["美浦", "栗東"])
        license_year = random.randint(1985, 2020)
        career_wins = random.randint(100, 1500)
        career_starts = random.randint(career_wins * 3, career_wins * 12)

        return TrainerInfoData(
            trainer_id=trainer_id,
            trainer_name=trainer_name,
            trainer_name_kana=None,  # モックではカナは省略
            affiliation=affiliation,
            stable_location=f"{affiliation}トレセン",
            license_year=license_year,
            career_wins=career_wins,
            career_starts=career_starts,
        )

    def get_trainer_stats_detail(
        self,
        trainer_id: str,
        year: int | None = None,
        period: str = "all",
    ) -> tuple[TrainerStatsDetailData | None, list[TrainerTrackStatsData], list[TrainerClassStatsData]]:
        """厩舎（調教師）の成績統計を取得する（モック実装）."""
        import random

        # nonexistent で始まるIDの場合はNoneを返す
        if trainer_id.startswith("nonexistent"):
            return None, [], []

        random.seed(_stable_hash(trainer_id + str(year) + period) % (2**32))

        # 調教師名を特定
        try:
            trainer_index = int(trainer_id.split("_")[1]) % len(self.TRAINER_NAMES)
        except (IndexError, ValueError):
            trainer_index = _stable_hash(trainer_id) % len(self.TRAINER_NAMES)
        trainer_name = self.TRAINER_NAMES[trainer_index]

        total_starts = random.randint(200, 1000)
        win_rate = random.uniform(0.08, 0.18)
        wins = int(total_starts * win_rate)
        second_places = int(total_starts * random.uniform(0.08, 0.12))
        third_places = int(total_starts * random.uniform(0.08, 0.12))
        places = wins + second_places + third_places
        place_rate = round(places / total_starts * 100, 1) if total_starts > 0 else 0.0
        prize_money = random.randint(100000000, 2000000000)

        stats = TrainerStatsDetailData(
            trainer_id=trainer_id,
            trainer_name=trainer_name,
            total_starts=total_starts,
            wins=wins,
            second_places=second_places,
            third_places=third_places,
            win_rate=round(win_rate * 100, 1),
            place_rate=place_rate,
            prize_money=prize_money,
            period=period if not year else "year",
            year=year,
        )

        # コース別成績
        track_stats = []
        for track_type in ["芝", "ダート", "障害"]:
            track_starts = random.randint(50, 400)
            track_win_rate = random.uniform(0.08, 0.20)
            track_wins = int(track_starts * track_win_rate)
            track_stats.append(TrainerTrackStatsData(
                track_type=track_type,
                starts=track_starts,
                wins=track_wins,
                win_rate=round(track_win_rate * 100, 1),
            ))

        # クラス別成績
        class_stats = []
        classes = ["G1", "G2", "G3", "OP", "3勝", "2勝", "1勝", "未勝利", "新馬"]
        for grade_class in classes:
            class_starts = random.randint(10, 200)
            class_win_rate = random.uniform(0.05, 0.25)
            class_wins = int(class_starts * class_win_rate)
            class_stats.append(TrainerClassStatsData(
                grade_class=grade_class,
                starts=class_starts,
                wins=class_wins,
                win_rate=round(class_win_rate * 100, 1),
            ))

        return stats, track_stats, class_stats
