"""血統分析ツール.

馬の血統から距離適性・馬場適性・成長曲線などを分析するツール。
"""

import logging

import requests
from strands import tool

from .jravan_client import cached_get, get_api_url

logger = logging.getLogger(__name__)

# 定数定義
API_TIMEOUT_SECONDS = 30

# 系統別の特徴データベース
SIRE_LINE_CHARACTERISTICS = {
    "サンデーサイレンス系": {
        "distance": "中〜長距離",
        "turf": "A",
        "dirt": "C",
        "growth_peak": "3〜4歳",
        "speed_type": "瞬発力型",
    },
    "ディープインパクト": {
        "distance": "中〜長距離",
        "distance_range": (1600, 2400),
        "turf": "A",
        "dirt": "C",
        "growth_peak": "3〜4歳",
        "speed_type": "瞬発力型",
    },
    "キングカメハメハ系": {
        "distance": "マイル〜中距離",
        "turf": "A",
        "dirt": "A",
        "growth_peak": "3歳",
        "speed_type": "パワー型",
    },
    "ロードカナロア": {
        "distance": "短〜マイル",
        "distance_range": (1000, 1600),
        "turf": "A",
        "dirt": "B",
        "growth_peak": "3歳",
        "speed_type": "スピード型",
    },
    "ハーツクライ系": {
        "distance": "中〜長距離",
        "turf": "A",
        "dirt": "C",
        "growth_peak": "4〜5歳",
        "speed_type": "晩成型",
    },
    "ノーザンダンサー系": {
        "distance": "万能",
        "turf": "A",
        "dirt": "B",
        "growth_peak": "3歳",
        "speed_type": "バランス型",
    },
    "ミスタープロスペクター系": {
        "distance": "短〜マイル",
        "turf": "B",
        "dirt": "A",
        "growth_peak": "3歳",
        "speed_type": "スピード型",
    },
}

# インブリード効果データベース
INBREEDING_EFFECTS = {
    "サンデーサイレンス": "瞬発力・切れ味強化",
    "ノーザンダンサー": "スタミナ・パワー強化",
    "ミスタープロスペクター": "スピード強化",
    "Halo": "瞬発力強化",
    "ニジンスキー": "スタミナ強化",
    "ナスルーラ": "スピード・闘争心強化",
}


@tool
def analyze_pedigree_aptitude(
    horse_id: str,
    horse_name: str,
    race_distance: int = 0,
    track_type: str = "",
    track_condition: str = "",
) -> dict:
    """馬の血統から適性を分析する。

    父系・母系の特徴、距離適性、馬場適性、
    インブリードの影響などを総合的に分析します。

    Args:
        horse_id: 馬コード
        horse_name: 馬名（表示用）
        race_distance: レース距離（省略時は一般的な適性を分析）
        track_type: コース種別（芝/ダート）
        track_condition: 馬場状態（良/稍重/重/不良）

    Returns:
        分析結果（血統サマリー、距離適性、馬場適性、インブリード影響など）
    """
    try:
        # 血統情報を取得
        pedigree_response = cached_get(
            f"{get_api_url()}/horses/{horse_id}/pedigree/extended",
            timeout=API_TIMEOUT_SECONDS,
        )

        if pedigree_response.status_code == 404:
            return {
                "warning": "血統データが見つかりませんでした",
                "horse_name": horse_name,
            }

        pedigree_response.raise_for_status()
        pedigree_data = pedigree_response.json()

        # 種牡馬の産駒成績を取得（父のID）
        sire_stats = None
        sire_name = pedigree_data.get("sire", {}).get("name", "")
        if sire_name:
            try:
                # 種牡馬IDは馬IDと同じ想定
                stallion_response = cached_get(
                    f"{get_api_url()}/stallions/{horse_id[:8]}00/offspring-stats",
                    timeout=API_TIMEOUT_SECONDS,
                )
                if stallion_response.status_code == 200:
                    sire_stats = stallion_response.json()
            except requests.RequestException:
                pass  # 産駒成績が取得できなくても続行

        # 血統サマリー生成
        pedigree_summary = _create_pedigree_summary(pedigree_data)

        # 距離適性分析
        distance_aptitude = _analyze_distance_aptitude(
            pedigree_data, sire_stats, race_distance
        )

        # 馬場適性分析
        track_aptitude = _analyze_track_aptitude(
            pedigree_data, sire_stats, track_type
        )

        # 馬場状態適性分析
        condition_aptitude = _analyze_condition_aptitude(
            pedigree_data, sire_stats, track_condition
        )

        # インブリード分析
        inbreeding_analysis = _analyze_inbreeding(pedigree_data)

        # 成長曲線分析
        growth_stage = _analyze_growth_stage(pedigree_data)

        # 総合コメント生成
        overall_comment = _generate_pedigree_comment(
            horse_name,
            pedigree_summary,
            distance_aptitude,
            track_aptitude,
            race_distance,
            track_type,
        )

        return {
            "horse_name": horse_name,
            "pedigree_summary": pedigree_summary,
            "distance_aptitude": distance_aptitude,
            "track_aptitude": track_aptitude,
            "condition_aptitude": condition_aptitude,
            "inbreeding": inbreeding_analysis,
            "growth_stage": growth_stage,
            "overall_comment": overall_comment,
        }
    except requests.RequestException as e:
        logger.error(f"Failed to analyze pedigree aptitude: {e}")
        return {"error": f"API呼び出しに失敗しました: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to analyze pedigree aptitude: {e}")
        return {"error": str(e)}


def _create_pedigree_summary(pedigree_data: dict) -> dict[str, str | list[str]]:
    """血統サマリーを生成する.

    Args:
        pedigree_data: 血統データ

    Returns:
        血統サマリー（父系、父、母父、重要先祖）
    """
    sire = pedigree_data.get("sire", {})
    dam = pedigree_data.get("dam", {})

    sire_name = sire.get("name", "不明")
    broodmare_sire = dam.get("sire", "不明")

    # 父系の系統を推定
    sire_line = _estimate_sire_line(sire_name)

    # キー先祖を特定
    key_ancestors = _identify_key_ancestors(pedigree_data)

    return {
        "sire_line": sire_line,
        "sire": sire_name,
        "broodmare_sire": broodmare_sire,
        "key_ancestors": key_ancestors,
    }


def _estimate_sire_line(sire_name: str) -> str:
    """父名から系統を推定する.

    Args:
        sire_name: 父馬名

    Returns:
        系統名
    """
    # 直接マッチ
    if sire_name in SIRE_LINE_CHARACTERISTICS:
        return sire_name

    # 有名種牡馬のマッピング
    deep_impact_sons = [
        "コントレイル", "キズナ", "シャフリヤール", "サトノダイヤモンド",
        "アルアイン", "フィエールマン", "グローリーヴェイズ",
    ]
    if sire_name in deep_impact_sons or "ディープ" in sire_name:
        return "ディープインパクト"

    king_kamehameha_sons = [
        "ドゥラメンテ", "ルーラーシップ", "レイデオロ", "ロードカナロア",
    ]
    if sire_name in king_kamehameha_sons:
        return "キングカメハメハ系"

    if "ロードカナロア" in sire_name:
        return "ロードカナロア"

    if "ハーツクライ" in sire_name or sire_name in ["リスグラシュー", "ジャスタウェイ"]:
        return "ハーツクライ系"

    # デフォルト
    return "サンデーサイレンス系"


def _identify_key_ancestors(pedigree_data: dict) -> list[str]:
    """重要な先祖を特定する.

    Args:
        pedigree_data: 血統データ

    Returns:
        重要先祖のリスト（最大4つ）
    """
    key_ancestors: list[str] = []

    # インブリードから取得
    inbreeding = pedigree_data.get("inbreeding", [])
    for ib in inbreeding:
        ancestor = ib.get("ancestor", "")
        if ancestor and ancestor not in key_ancestors:
            key_ancestors.append(ancestor)

    # 父・母父も追加
    sire = pedigree_data.get("sire", {}).get("name", "")
    broodmare_sire = pedigree_data.get("dam", {}).get("sire", "")

    if sire and sire not in key_ancestors:
        key_ancestors.insert(0, sire)
    if broodmare_sire and broodmare_sire not in key_ancestors:
        key_ancestors.append(broodmare_sire)

    return key_ancestors[:4]  # 最大4つ


def _analyze_distance_aptitude(
    pedigree_data: dict, sire_stats: dict | None, race_distance: int
) -> dict[str, str]:
    """距離適性を分析する.

    Args:
        pedigree_data: 血統データ
        sire_stats: 種牡馬産駒成績
        race_distance: レース距離

    Returns:
        距離適性分析結果
    """
    sire_name = pedigree_data.get("sire", {}).get("name", "")
    sire_line = _estimate_sire_line(sire_name)
    characteristics = SIRE_LINE_CHARACTERISTICS.get(
        sire_line, SIRE_LINE_CHARACTERISTICS.get("サンデーサイレンス系", {})
    )

    # 産駒成績から適性距離を算出
    if sire_stats:
        by_distance = sire_stats.get("by_distance", [])
        best_dist_range = _find_best_distance_range(by_distance)
    else:
        best_dist_range = characteristics.get("distance_range", (1600, 2400))

    suitable_range = f"{best_dist_range[0]}-{best_dist_range[1]}m"

    # レース距離との適合度判定
    if race_distance > 0:
        if best_dist_range[0] <= race_distance <= best_dist_range[1]:
            rating = "A"
            fit = "最適距離内"
        elif (
            abs(race_distance - best_dist_range[0]) <= 200
            or abs(race_distance - best_dist_range[1]) <= 200
        ):
            rating = "B"
            fit = "適性距離近辺"
        else:
            rating = "C"
            fit = "適性外"
    else:
        rating = "B"
        fit = "判定対象なし"

    comment = f"父{sire_name}は{characteristics.get('distance', '中距離')}で産駒活躍"

    return {
        "rating": rating,
        "suitable_range": suitable_range,
        "race_distance_fit": fit,
        "comment": comment,
    }


def _find_best_distance_range(by_distance: list[dict]) -> tuple[int, int]:
    """産駒成績から最適距離帯を算出する.

    Args:
        by_distance: 距離別成績データ

    Returns:
        最適距離帯（min, max）
    """
    if not by_distance:
        return (1600, 2400)

    # 勝率が高い距離帯を特定
    best_range = None
    best_win_rate = 0.0

    for d in by_distance:
        win_rate = d.get("win_rate", 0.0)
        if win_rate > best_win_rate:
            best_win_rate = win_rate
            best_range = d.get("distance_range", "1600-2000m")

    if best_range:
        # "1600-2000m" → (1600, 2000)
        parts = best_range.replace("m", "").split("-")
        if len(parts) == 2:
            try:
                return (int(parts[0]), int(parts[1]))
            except ValueError:
                pass

    return (1600, 2400)


def _analyze_track_aptitude(
    pedigree_data: dict, sire_stats: dict | None, track_type: str
) -> dict[str, str]:
    """馬場適性を分析する.

    Args:
        pedigree_data: 血統データ
        sire_stats: 種牡馬産駒成績
        track_type: コース種別

    Returns:
        馬場適性分析結果
    """
    sire_name = pedigree_data.get("sire", {}).get("name", "")
    sire_line = _estimate_sire_line(sire_name)
    characteristics = SIRE_LINE_CHARACTERISTICS.get(
        sire_line, SIRE_LINE_CHARACTERISTICS.get("サンデーサイレンス系", {})
    )

    turf_rating = characteristics.get("turf", "B")
    dirt_rating = characteristics.get("dirt", "B")

    # 産駒成績から上書き
    if sire_stats:
        by_track = sire_stats.get("by_track_type", [])
        for t in by_track:
            if t.get("track_type") == "芝":
                turf_rating = _win_rate_to_rating(t.get("win_rate", 0))
            elif t.get("track_type") == "ダート":
                dirt_rating = _win_rate_to_rating(t.get("win_rate", 0))

    # コメント生成
    if turf_rating in ("A", "B") and dirt_rating in ("C", "D"):
        comment = "芝血統。ダートは苦戦傾向"
    elif dirt_rating in ("A", "B") and turf_rating in ("C", "D"):
        comment = "ダート血統。芝は苦戦傾向"
    elif turf_rating in ("A", "B") and dirt_rating in ("A", "B"):
        comment = "芝ダート兼用の万能血統"
    else:
        comment = "特筆なし"

    return {
        "turf_rating": turf_rating,
        "dirt_rating": dirt_rating,
        "comment": comment,
    }


def _win_rate_to_rating(win_rate: float) -> str:
    """勝率から評価を算出.

    Args:
        win_rate: 勝率（0-1の小数）

    Returns:
        評価（A/B/C/D）
    """
    if win_rate >= 0.12:
        return "A"
    elif win_rate >= 0.08:
        return "B"
    elif win_rate >= 0.05:
        return "C"
    else:
        return "D"


def _analyze_condition_aptitude(
    pedigree_data: dict, sire_stats: dict | None, track_condition: str
) -> dict[str, str]:
    """馬場状態適性を分析する.

    Args:
        pedigree_data: 血統データ
        sire_stats: 種牡馬産駒成績
        track_condition: 馬場状態

    Returns:
        馬場状態適性分析結果
    """
    good_rating = "A"
    heavy_rating = "B"

    # 産駒成績から算出
    if sire_stats:
        by_condition = sire_stats.get("by_track_condition", [])
        for c in by_condition:
            condition = c.get("condition", "")
            if condition == "良":
                good_rating = _win_rate_to_rating(c.get("win_rate", 0))
            elif condition in ("重", "不良"):
                heavy_rating = _win_rate_to_rating(c.get("win_rate", 0))

    # コメント生成
    if good_rating == "A" and heavy_rating in ("C", "D"):
        comment = "良馬場巧者。重馬場は苦手"
    elif heavy_rating in ("A", "B") and good_rating in ("A", "B"):
        comment = "道悪もこなすが良馬場がベスト"
    elif heavy_rating == "A":
        comment = "重馬場得意"
    else:
        comment = "馬場状態は問わない"

    return {
        "good_rating": good_rating,
        "heavy_rating": heavy_rating,
        "comment": comment,
    }


def _analyze_inbreeding(pedigree_data: dict) -> dict[str, bool | list[str] | str]:
    """インブリードを分析する.

    Args:
        pedigree_data: 血統データ

    Returns:
        インブリード分析結果
    """
    inbreeding = pedigree_data.get("inbreeding", [])

    if not inbreeding:
        return {
            "detected": False,
            "patterns": [],
            "effect": "クロスなし（アウトブリード）",
        }

    patterns = []
    effects = []

    for ib in inbreeding:
        ancestor = ib.get("ancestor", "")
        pattern = ib.get("pattern", "")
        if ancestor and pattern:
            patterns.append(f"{ancestor} {pattern}")

            # 効果を取得
            effect = INBREEDING_EFFECTS.get(ancestor)
            if effect and effect not in effects:
                effects.append(effect)

    return {
        "detected": True,
        "patterns": patterns,
        "effect": "、".join(effects) if effects else "特筆なし",
    }


def _analyze_growth_stage(pedigree_data: dict) -> dict[str, str]:
    """成長曲線を分析する.

    Args:
        pedigree_data: 血統データ

    Returns:
        成長曲線分析結果
    """
    sire_name = pedigree_data.get("sire", {}).get("name", "")
    sire_line = _estimate_sire_line(sire_name)
    characteristics = SIRE_LINE_CHARACTERISTICS.get(
        sire_line, SIRE_LINE_CHARACTERISTICS.get("サンデーサイレンス系", {})
    )

    typical_peak = characteristics.get("growth_peak", "3〜4歳")
    speed_type = characteristics.get("speed_type", "バランス型")

    # 晩成型かどうか
    if "晩成" in speed_type or "5歳" in typical_peak:
        current_status = "晩成型・成長余地あり"
    elif "早熟" in speed_type or typical_peak == "2歳":
        current_status = "早熟型・完成度高い"
    else:
        current_status = "標準型"

    return {
        "typical_peak": typical_peak,
        "current_status": current_status,
        "speed_type": speed_type,
    }


def _generate_pedigree_comment(
    horse_name: str,
    pedigree_summary: dict,
    distance_aptitude: dict,
    track_aptitude: dict,
    race_distance: int,
    track_type: str,
) -> str:
    """総合コメントを生成する.

    Args:
        horse_name: 馬名
        pedigree_summary: 血統サマリー
        distance_aptitude: 距離適性
        track_aptitude: 馬場適性
        race_distance: レース距離
        track_type: コース種別

    Returns:
        総合コメント
    """
    parts: list[str] = []

    # 血統的な条件適合度
    sire = pedigree_summary.get("sire", "")
    if sire:
        parts.append(f"血統的には{sire}産駒")

    # 距離適性
    dist_rating = distance_aptitude.get("rating", "")
    if dist_rating == "A" and race_distance > 0:
        parts.append(f"{race_distance}mは最適距離")
    elif dist_rating == "B" and race_distance > 0:
        parts.append(f"{race_distance}mはこなせる範囲")
    elif dist_rating == "C" and race_distance > 0:
        parts.append(f"{race_distance}mは血統的に不安")

    # 馬場適性
    if track_type == "芝":
        turf_rating = track_aptitude.get("turf_rating", "")
        if turf_rating == "A":
            parts.append("芝適性◎")
    elif track_type == "ダート":
        dirt_rating = track_aptitude.get("dirt_rating", "")
        if dirt_rating == "A":
            parts.append("ダート適性◎")
        elif dirt_rating in ("C", "D"):
            parts.append("ダートは血統的に疑問")

    if not parts:
        return f"{horse_name}の血統は今回の条件に大きな問題なし。"

    return "。".join(parts) + "。"
