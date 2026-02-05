"""展開分析・レース特性分析ツール.

レースの展開を予想し、脚質と展開の相性を分析する。
レース難易度判定、枠順の有利不利、展開サマリーも生成する。
"""

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers


# ペース予想結果と有利脚質のマッピング
PACE_FAVORABLE_STYLES = {
    "ハイ": ["差し", "追込"],
    "ミドル": ["先行", "差し"],
    "スロー": ["逃げ", "先行"],
}

# 競馬場別の荒れやすさ補正値（JRA 2019-2024年 1番人気勝率の偏差に基づく）
# 福島・中京・小倉: 1番人気勝率が全国平均より低い（荒れやすい）
# 京都・阪神: 1番人気勝率が全国平均より高い（堅い傾向）
VENUE_UPSET_FACTOR = {
    "札幌": 0,
    "函館": 0,
    "福島": 1,
    "新潟": 0,
    "東京": 0,
    "中山": 0,
    "中京": 1,
    "京都": -1,
    "阪神": -1,
    "小倉": 1,
}

# レース条件別の荒れ度補正値（JRA統計: 条件別1番人気勝率の偏差に基づく）
# handicap/hurdle: 1番人気勝率が大幅に低い（荒れやすい）
# g1/g2: 実力馬が集まり1番人気勝率が高い（堅い傾向）
RACE_CONDITION_UPSET = {
    "handicap": 2,
    "maiden_new": 1,
    "maiden": 0,
    "hurdle": 2,
    "g1": -1,
    "g2": -1,
    "g3": 0,
    "fillies_mares": 0,
}

# 枠順分析の区分数（内枠/中枠/外枠の3分割）
POST_POSITION_GROUPS = 3

# オッズ断層分析の閾値
# 3-4番人気間のオッズ比がこの値以上 → 堅いレースの予兆
ODDS_GAP_THRESHOLD = 2.0
# 1-2番人気間のオッズ比がこの値以下 → 上位が団子状態（荒れやすい）
ODDS_DANGO_THRESHOLD = 1.3


def _get_running_styles(race_id: str) -> list[dict]:
    """APIから脚質データを取得する."""
    try:
        response = requests.get(
            f"{get_api_url()}/races/{race_id}/running-styles",
            headers=get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []


def _predict_pace(front_runners: int, total_runners: int) -> str:
    """逃げ・先行馬の頭数からペースを予想.

    Args:
        front_runners: 逃げ馬の頭数
        total_runners: 出走馬総数

    Returns:
        予想ペース（"ハイ", "ミドル", "スロー"）
    """
    if total_runners == 0:
        return "不明"

    # 逃げ馬が3頭以上 → ハイペース傾向
    # 逃げ馬が1頭 or 0頭 → スローペース傾向（0頭は先行馬が押し出されて逃げ）
    # 逃げ馬が2頭 → ミドルペース
    if front_runners >= 3:
        return "ハイ"
    elif front_runners <= 1:
        return "スロー"
    else:
        return "ミドル"


def _generate_pace_analysis(
    predicted_pace: str,
    front_runner_count: int,
    runners_by_style: dict[str, list[dict]],
) -> str:
    """ペース予想に基づく分析コメントを生成する.

    Args:
        predicted_pace: 予想ペース（"ハイ", "ミドル", "スロー", "不明"）
        front_runner_count: 逃げ馬の頭数
        runners_by_style: 脚質別の出走馬辞書

    Returns:
        分析コメント文字列
    """
    escaper_names = [r["horse_name"] for r in runners_by_style.get("逃げ", [])]

    if predicted_pace == "ハイ":
        comment = (
            f"逃げ馬が{front_runner_count}頭いるため、ハイペースが予想されます。"
            "前が潰れやすく、差し・追込馬に展開利がある可能性が高いです。"
        )
    elif predicted_pace == "スロー":
        if escaper_names:
            comment = (
                f"逃げ馬は{escaper_names[0]}のみでスローペースが予想されます。"
                "前残りしやすい展開で、逃げ・先行馬が有利な可能性があります。"
            )
        else:
            comment = (
                "明確な逃げ馬が不在で、スローペースが予想されます。"
                "前残りしやすい展開で、先行馬が有利な可能性があります。"
            )
    else:
        comment = (
            f"逃げ馬が{front_runner_count}頭でミドルペースが予想されます。"
            "どの脚質にも展開利があり、各馬の能力が問われる展開です。"
        )

    return comment


def _analyze_race_development_impl(
    race_id: str,
    running_styles_data: list[dict],
) -> dict:
    """レースの展開を予想する（実装）.

    Args:
        race_id: レースID
        running_styles_data: 出走馬の脚質データリスト

    Returns:
        展開予想結果の辞書（脚質別馬リスト、予想ペース、有利脚質、分析コメント）
    """
    if not running_styles_data:
        return {
            "error": "脚質データが取得できませんでした",
            "race_id": race_id,
        }

    # 脚質別に馬を分類
    runners_by_style: dict[str, list[dict]] = {
        "逃げ": [],
        "先行": [],
        "差し": [],
        "追込": [],
        "自在": [],
        "不明": [],
    }

    for runner in running_styles_data:
        style = runner.get("running_style", "不明")
        if style in runners_by_style:
            runners_by_style[style].append({
                "horse_number": runner.get("horse_number"),
                "horse_name": runner.get("horse_name"),
            })
        else:
            runners_by_style["不明"].append({
                "horse_number": runner.get("horse_number"),
                "horse_name": runner.get("horse_name"),
            })

    # 逃げ馬の頭数
    front_runner_count = len(runners_by_style["逃げ"])
    total_runners = len(running_styles_data)

    # ペース予想
    predicted_pace = _predict_pace(front_runner_count, total_runners)

    # 有利な脚質
    favorable_styles = PACE_FAVORABLE_STYLES.get(predicted_pace, [])

    # 分析コメント
    analysis = _generate_pace_analysis(
        predicted_pace, front_runner_count, runners_by_style
    )

    return {
        "race_id": race_id,
        "runners_by_style": runners_by_style,
        "front_runner_count": front_runner_count,
        "total_runners": total_runners,
        "predicted_pace": predicted_pace,
        "favorable_styles": favorable_styles,
        "analysis": analysis,
    }


@tool
def analyze_race_development(race_id: str) -> dict:
    """レースの展開を予想する.

    逃げ馬の頭数からペースを判定し、有利な脚質を分析する。

    Args:
        race_id: レースID (例: "20260125_05_11")

    Returns:
        展開予想結果（脚質別の馬リスト、予想ペース、有利脚質、分析コメント）
    """
    running_styles = _get_running_styles(race_id)
    return _analyze_race_development_impl(race_id, running_styles)


def _analyze_running_style_match_impl(
    race_id: str,
    horse_numbers: list[int],
    running_styles_data: list[dict],
    predicted_pace: str,
) -> dict:
    """選択馬の脚質と展開の相性を分析する（実装）.

    Args:
        race_id: レースID
        horse_numbers: 分析対象の馬番リスト
        running_styles_data: 出走馬の脚質データリスト
        predicted_pace: 予想ペース

    Returns:
        脚質相性分析結果の辞書（予想ペース、各馬の相性評価とコメント）
    """
    if not running_styles_data:
        return {
            "error": "脚質データが取得できませんでした",
            "race_id": race_id,
        }

    favorable_styles = PACE_FAVORABLE_STYLES.get(predicted_pace, [])

    horses_analysis = []
    for runner in running_styles_data:
        horse_number = runner.get("horse_number")
        if horse_number not in horse_numbers:
            continue

        running_style = runner.get("running_style", "不明")

        # 相性判定
        if predicted_pace == "不明":
            # ペース予想が不明な場合は有利不利を判定しない
            pace_compatibility = "不明"
            comment = "ペース予想が困難なため、脚質の有利不利は判断できません"
        elif running_style in favorable_styles:
            pace_compatibility = "有利"
            comment = f"{predicted_pace}ペース予想で{running_style}脚質は好展開"
        elif running_style == "自在":
            pace_compatibility = "中立"
            comment = "自在脚質のためどの展開にも対応可能"
        elif running_style == "不明":
            pace_compatibility = "不明"
            comment = "脚質データなし"
        else:
            pace_compatibility = "不利"
            if predicted_pace == "ハイ":
                comment = f"ハイペース予想で{running_style}馬は厳しい展開"
            elif predicted_pace == "スロー":
                comment = f"スローペース予想で{running_style}馬は脚を余す可能性あり"
            else:
                comment = f"ミドルペースで{running_style}馬はやや不利"

        horses_analysis.append({
            "horse_number": horse_number,
            "horse_name": runner.get("horse_name"),
            "running_style": running_style,
            "pace_compatibility": pace_compatibility,
            "comment": comment,
        })

    return {
        "race_id": race_id,
        "predicted_pace": predicted_pace,
        "favorable_styles": favorable_styles,
        "horses": horses_analysis,
    }


@tool
def analyze_running_style_match(
    race_id: str,
    horse_numbers: list[int],
) -> dict:
    """選択馬の脚質と展開の相性を分析する.

    レースの展開予想を行い、選択された馬の脚質との相性を判定する。

    Args:
        race_id: レースID (例: "20260125_05_11")
        horse_numbers: 分析対象の馬番リスト

    Returns:
        脚質相性分析結果（予想ペース、各馬の相性評価とコメント）
    """
    running_styles = _get_running_styles(race_id)

    # まず展開予想を実行
    development = _analyze_race_development_impl(race_id, running_styles)

    if "error" in development:
        return development

    predicted_pace = development.get("predicted_pace", "不明")

    return _analyze_running_style_match_impl(
        race_id, horse_numbers, running_styles, predicted_pace
    )


def _assess_race_difficulty(
    total_runners: int,
    race_conditions: list[str] | None = None,
    venue: str = "",
    runners_data: list[dict] | None = None,
) -> dict:
    """レースの荒れ度を★1〜★5で判定する.

    Args:
        total_runners: 出走頭数
        race_conditions: レース条件リスト（"handicap", "maiden_new"等）
        venue: 競馬場名
        runners_data: 出走馬データ（オッズ情報を含む）

    Returns:
        難易度判定結果（difficulty_stars, upset_score, factors）
    """
    race_conditions = race_conditions or []
    runners_data = runners_data or []

    upset_score = 0
    factors = []

    # 1. 頭数による補正
    if total_runners >= 16:
        upset_score += 2
        factors.append(f"{total_runners}頭立ての多頭数レース（荒れやすい）")
    elif total_runners >= 13:
        upset_score += 1
        factors.append(f"{total_runners}頭立て（やや荒れやすい）")
    elif total_runners <= 8:
        upset_score -= 1
        factors.append(f"{total_runners}頭立ての少頭数（堅い傾向）")

    # 2. レース条件による補正
    for condition in race_conditions:
        adjustment = RACE_CONDITION_UPSET.get(condition, 0)
        if adjustment != 0:
            upset_score += adjustment
            condition_names = {
                "handicap": "ハンデ戦",
                "maiden_new": "新馬戦",
                "maiden": "未勝利戦",
                "hurdle": "障害戦",
                "g1": "G1",
                "g2": "G2",
                "g3": "G3",
                "fillies_mares": "牝馬限定",
            }
            name = condition_names.get(condition, condition)
            if adjustment > 0:
                factors.append(f"{name}（荒れやすい）")
            else:
                factors.append(f"{name}（堅い傾向）")

    # 3. 競馬場による補正
    venue_adjustment = VENUE_UPSET_FACTOR.get(venue, 0)
    if venue_adjustment != 0:
        upset_score += venue_adjustment
        if venue_adjustment > 0:
            factors.append(f"{venue}開催（荒れやすい）")
        else:
            factors.append(f"{venue}開催（堅い傾向）")

    # 4. オッズ断層分析
    if runners_data:
        odds_gap = _analyze_odds_gap(runners_data)
        if odds_gap:
            upset_score += odds_gap["adjustment"]
            factors.append(odds_gap["comment"])

    # スコアを★1〜★5に変換（-3以下=★1、4以上=★5）
    difficulty_stars = max(1, min(5, upset_score + 3))

    star_labels = {
        1: "堅いレース",
        2: "やや堅い",
        3: "標準",
        4: "荒れ模様",
        5: "大荒れ注意",
    }

    return {
        "difficulty_stars": difficulty_stars,
        "difficulty_label": star_labels[difficulty_stars],
        "upset_score": upset_score,
        "factors": factors,
    }


def _analyze_odds_gap(runners_data: list[dict]) -> dict | None:
    """オッズ断層を分析する.

    3-4番人気間に大きな断層がある → 堅いレースの予兆
    上位が団子状態 → 荒れやすい

    Args:
        runners_data: 出走馬データ（oddsを含む）

    Returns:
        断層分析結果 or None
    """
    # オッズ順にソート
    sorted_runners = sorted(
        [r for r in runners_data if r.get("odds") and r.get("odds") > 0],
        key=lambda x: x["odds"],
    )

    if len(sorted_runners) < 4:
        return None

    # 上位4頭のオッズを取得
    top4_odds = [r["odds"] for r in sorted_runners[:4]]

    # ゼロ除算防御（オッズが0以下のデータは上でフィルタ済みだが念のため）
    if top4_odds[0] <= 0 or top4_odds[2] <= 0:
        return None

    # 3番人気と4番人気の断層（3-4番人気間のオッズ比）
    gap_ratio = top4_odds[3] / top4_odds[2]

    # 1-2番人気間のオッズ比（団子状態チェック）
    top2_ratio = top4_odds[1] / top4_odds[0]

    if gap_ratio >= ODDS_GAP_THRESHOLD:
        return {
            "adjustment": -1,
            "comment": f"3-4番人気間にオッズ断層（{top4_odds[2]:.1f}→{top4_odds[3]:.1f}倍）。堅い予兆",
        }
    elif top2_ratio <= ODDS_DANGO_THRESHOLD and top4_odds[2] / top4_odds[0] <= ODDS_GAP_THRESHOLD:
        return {
            "adjustment": 1,
            "comment": f"上位3頭が{top4_odds[0]:.1f}〜{top4_odds[2]:.1f}倍の団子状態。荒れる可能性",
        }

    return None


def _analyze_post_position(
    horse_number: int,
    total_runners: int,
    surface: str,
) -> dict:
    """枠順の有利不利を分析する.

    Args:
        horse_number: 馬番
        total_runners: 出走頭数
        surface: 馬場（"芝" or "ダート"）

    Returns:
        枠順分析結果（position_group, advantage, comment）
    """
    if total_runners == 0:
        return {
            "position_group": "不明",
            "advantage": "中立",
            "comment": "出走頭数が不明",
        }

    # 内枠・中枠・外枠の判定（全体をPOST_POSITION_GROUPS等分）
    group_size = max(1, total_runners / POST_POSITION_GROUPS)
    if horse_number <= group_size:
        position_group = "内枠"
    elif horse_number <= group_size * 2:
        position_group = "中枠"
    else:
        position_group = "外枠"

    # 芝: 内枠有利（距離ロスが少ない）
    # ダート: 外枠有利（砂を被らない）
    if surface == "芝":
        if position_group == "内枠":
            advantage = "有利"
            comment = "芝コースの内枠。距離ロスが少なく有利"
        elif position_group == "外枠":
            advantage = "不利"
            comment = "芝コースの外枠。距離ロスが発生しやすい"
        else:
            advantage = "中立"
            comment = "芝コースの中枠。枠による影響は少ない"
    elif surface == "ダート":
        if position_group == "外枠":
            advantage = "有利"
            comment = "ダートの外枠。砂を被りにくく有利"
        elif position_group == "内枠":
            advantage = "不利"
            comment = "ダートの内枠。砂を被りやすい"
        else:
            advantage = "中立"
            comment = "ダートの中枠。枠による影響は少ない"
    else:
        advantage = "中立"
        comment = f"{position_group}。馬場情報なし"

    return {
        "position_group": position_group,
        "advantage": advantage,
        "comment": comment,
    }


def _generate_development_summary(
    predicted_pace: str,
    runners_by_style: dict[str, list[dict]],
    difficulty: dict,
    surface: str,
    total_runners: int,
) -> str:
    """展開予想の自然言語サマリーを生成する.

    Args:
        predicted_pace: 予想ペース
        runners_by_style: 脚質別馬リスト
        difficulty: 難易度判定結果
        surface: 馬場（"芝" or "ダート"）
        total_runners: 出走頭数

    Returns:
        展開サマリー文字列
    """
    escaper_names = [r["horse_name"] for r in runners_by_style.get("逃げ", [])]
    leader_names = [r["horse_name"] for r in runners_by_style.get("先行", [])]

    parts = []

    # ペースの描写
    if predicted_pace == "ハイ":
        if len(escaper_names) >= 3:
            names = "・".join(escaper_names[:3])
            parts.append(f"{names}ら{len(escaper_names)}頭が逃げを主張し、ハイペースが濃厚")
        else:
            parts.append("逃げ馬が複数おり、ハイペースが予想される")
        parts.append("前が潰れる展開で差し・追込馬に展開利")
    elif predicted_pace == "スロー":
        if escaper_names:
            parts.append(f"{escaper_names[0]}がハナを主張し、スローペースが予想される")
            parts.append("前残りしやすい展開で逃げ・先行馬が有利")
        else:
            parts.append("明確な逃げ馬不在でスローペースが予想される")
            if leader_names:
                parts.append(f"{leader_names[0]}あたりが押し出されてハナに立つ可能性")
            parts.append("先行馬が有利な展開")
    else:
        parts.append("逃げ馬が2頭でミドルペース想定")
        parts.append("能力がストレートに問われる展開")

    # 枠順の傾向
    if surface == "芝":
        parts.append("芝コースのため内枠が有利")
    elif surface == "ダート":
        parts.append("ダートのため外枠が砂を被りにくく有利")

    # 荒れ度
    stars = "★" * difficulty["difficulty_stars"] + "☆" * (5 - difficulty["difficulty_stars"])
    parts.append(f"レース難易度: {stars}（{difficulty['difficulty_label']}）")

    return "。".join(parts)


def _analyze_race_characteristics_impl(
    race_id: str,
    running_styles_data: list[dict],
    runners_data: list[dict] | None = None,
    race_conditions: list[str] | None = None,
    venue: str = "",
    surface: str = "",
    horse_numbers: list[int] | None = None,
) -> dict:
    """レース特性を総合的に分析する（実装）.

    展開予想、脚質分析、レース難易度、枠順、展開サマリーを統合する。

    Args:
        race_id: レースID
        running_styles_data: 出走馬の脚質データ
        runners_data: 出走馬データ（オッズ情報を含む）
        race_conditions: レース条件リスト
        venue: 競馬場名
        surface: 馬場（"芝" or "ダート"）
        horse_numbers: 分析対象の馬番リスト（省略時は全馬）

    Returns:
        総合分析結果
    """
    # 1. 展開予想
    development = _analyze_race_development_impl(race_id, running_styles_data)
    if "error" in development:
        return development

    total_runners = development["total_runners"]
    predicted_pace = development["predicted_pace"]
    runners_by_style = development["runners_by_style"]

    # 2. レース難易度判定
    difficulty = _assess_race_difficulty(
        total_runners, race_conditions, venue, runners_data
    )

    # 3. 枠順分析（選択馬）
    target_numbers = horse_numbers or [
        r.get("horse_number") for r in running_styles_data
    ]
    target_numbers_set = set(target_numbers)
    post_position_analysis = []
    for runner in running_styles_data:
        hn = runner.get("horse_number")
        if hn not in target_numbers_set:
            continue
        post = _analyze_post_position(hn, total_runners, surface)
        post_position_analysis.append({
            "horse_number": hn,
            "horse_name": runner.get("horse_name"),
            **post,
        })

    # 4. 脚質相性分析（選択馬）
    style_match = _analyze_running_style_match_impl(
        race_id, target_numbers, running_styles_data, predicted_pace
    )

    # 5. 展開サマリー生成
    summary = _generate_development_summary(
        predicted_pace, runners_by_style, difficulty, surface, total_runners
    )

    return {
        "race_id": race_id,
        "development": {
            "predicted_pace": predicted_pace,
            "favorable_styles": development["favorable_styles"],
            "runners_by_style": runners_by_style,
            "front_runner_count": development["front_runner_count"],
            "total_runners": total_runners,
            "analysis": development["analysis"],
        },
        "difficulty": difficulty,
        "post_position": post_position_analysis,
        "style_match": style_match.get("horses", []),
        "summary": summary,
    }


@tool
def analyze_race_characteristics(
    race_id: str,
    horse_numbers: list[int] | None = None,
    race_conditions: list[str] | None = None,
    venue: str = "",
    surface: str = "",
    runners_data: list[dict] | None = None,
) -> dict:
    """レースの展開予想・特性分析を総合的に行う.

    脚質データからペース予想、枠順の有利不利、レース難易度（★1〜★5）、
    展開から見た各馬の有利不利を分析し、自然言語サマリーを生成する。

    Args:
        race_id: レースID (例: "20260201_05_11")
        horse_numbers: 分析対象の馬番リスト（省略時は全馬）
        race_conditions: レース条件リスト（"handicap", "maiden_new", "maiden",
            "hurdle", "g1", "g2", "g3", "fillies_mares"）
        venue: 競馬場名（"東京", "中山", "阪神", "京都", "中京", "小倉", "福島",
            "新潟", "札幌", "函館"）
        surface: 馬場（"芝" or "ダート"）
        runners_data: 出走馬データ（オッズ情報を含む。オッズ断層分析に使用）

    Returns:
        総合分析結果（展開予想、難易度、枠順、脚質相性、サマリー）
    """
    running_styles = _get_running_styles(race_id)
    return _analyze_race_characteristics_impl(
        race_id,
        running_styles,
        runners_data=runners_data,
        race_conditions=race_conditions,
        venue=venue,
        surface=surface,
        horse_numbers=horse_numbers,
    )
