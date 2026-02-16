"""展開分析・レース特性分析ツール.

脚質構成を集計し、レース難易度判定、枠順の有利不利、展開サマリーを生成する。
"""

import logging

import requests
from strands import tool

from .jravan_client import get_api_url, get_headers

logger = logging.getLogger(__name__)


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
    url = f"{get_api_url()}/races/{race_id}/running-styles"
    try:
        response = requests.get(
            url,
            headers=get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(
            "Failed to get running styles: url=%s, error=%s", url, e
        )
        return []


def _analyze_race_development_impl(
    race_id: str,
    running_styles_data: list[dict],
) -> dict:
    """レースの展開を分析する（実装）.

    Args:
        race_id: レースID
        running_styles_data: 出走馬の脚質データリスト

    Returns:
        展開分析結果の辞書（脚質別馬リスト、逃げ馬頭数、脚質構成サマリー）
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

    front_runner_count = len(runners_by_style["逃げ"])
    total_runners = len(running_styles_data)

    # 脚質構成サマリー（各脚質の頭数）
    running_style_summary = {
        style: len(horses)
        for style, horses in runners_by_style.items()
        if len(horses) > 0
    }

    return {
        "race_id": race_id,
        "runners_by_style": runners_by_style,
        "front_runner_count": front_runner_count,
        "total_runners": total_runners,
        "running_style_summary": running_style_summary,
    }


def _assess_race_difficulty(
    total_runners: int,
    race_conditions: list[str] | None = None,
    venue: str = "",
    runners_data: list[dict] | None = None,
) -> dict:
    """レースの荒れ度を★1〜★5で判定する.

    ベースラインの難易度を算出する。頭数・レース条件・会場から機械的に判定し、
    AI予想の分散・ペース・馬場状態などの総合判断はエージェント（LLM）に委ねる。

    Args:
        total_runners: 出走頭数
        race_conditions: レース条件リスト（"handicap", "maiden_new"等）
        venue: 競馬場名
        runners_data: 出走馬データ（互換性のため受け取るが難易度判定には使用しない）

    Returns:
        難易度判定結果（difficulty_stars, upset_score, factors）
    """
    race_conditions = race_conditions or []

    upset_score = 0
    factors = []

    # 1. 頭数による補正
    if total_runners >= 16:
        upset_score += 1
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

    # スコアを★1〜★5に変換（-2以下=★1、3以上=★5）
    difficulty_stars = max(1, min(5, upset_score + 2))

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
    runners_by_style: dict[str, list[dict]],
    difficulty: dict,
    surface: str,
    total_runners: int,
) -> str:
    """展開予想の自然言語サマリーを生成する.

    Args:
        runners_by_style: 脚質別馬リスト
        difficulty: 難易度判定結果
        surface: 馬場（"芝" or "ダート"）
        total_runners: 出走頭数

    Returns:
        展開サマリー文字列
    """
    escaper_names = [r["horse_name"] for r in runners_by_style.get("逃げ", [])]
    leader_names = [r["horse_name"] for r in runners_by_style.get("先行", [])]
    escaper_count = len(escaper_names)

    parts = []

    # 脚質構成ベースの描写
    if escaper_count >= 3:
        names = "・".join(escaper_names[:3])
        parts.append(f"逃げ馬が{escaper_count}頭（{names}）と多い構成")
    elif escaper_count == 2:
        names = "・".join(escaper_names)
        parts.append(f"逃げ馬が2頭（{names}）の構成")
    elif escaper_count == 1:
        parts.append(f"逃げ馬は{escaper_names[0]}の1頭のみ")
    else:
        parts.append("明確な逃げ馬が不在")
        if leader_names:
            parts.append(f"{leader_names[0]}あたりが押し出されてハナに立つ可能性")

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
    # 1. 展開分析
    development = _analyze_race_development_impl(race_id, running_styles_data)
    if "error" in development:
        return development

    total_runners = development["total_runners"]
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

    # 4. 展開サマリー生成
    summary = _generate_development_summary(
        runners_by_style, difficulty, surface, total_runners
    )

    return {
        "race_id": race_id,
        "development": {
            "running_style_summary": development["running_style_summary"],
            "runners_by_style": runners_by_style,
            "front_runner_count": development["front_runner_count"],
            "total_runners": total_runners,
        },
        "difficulty": difficulty,
        "post_position": post_position_analysis,
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
        race_id: レースID (例: "202602010511")
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
