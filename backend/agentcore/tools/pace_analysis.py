"""展開分析ツール.

レースの展開を予想し、脚質と展開の相性を分析する。
"""

import os

import boto3
import requests
from strands import tool

JRAVAN_API_URL = os.environ.get(
    "JRAVAN_API_URL",
    "https://ryzl2uhi94.execute-api.ap-northeast-1.amazonaws.com/prod",
)
JRAVAN_API_KEY = os.environ.get("JRAVAN_API_KEY", "")
JRAVAN_API_KEY_ID = os.environ.get("JRAVAN_API_KEY_ID", "zeq5hh8qp6")

_cached_api_key: str | None = None


def _get_api_key() -> str:
    """APIキーを取得（キャッシュあり）."""
    global _cached_api_key
    if _cached_api_key is not None:
        return _cached_api_key

    # 環境変数から取得
    if JRAVAN_API_KEY:
        _cached_api_key = JRAVAN_API_KEY
        return _cached_api_key

    # boto3でAPI Gatewayから取得
    try:
        client = boto3.client("apigateway", region_name="ap-northeast-1")
        response = client.get_api_key(apiKey=JRAVAN_API_KEY_ID, includeValue=True)
        _cached_api_key = response.get("value", "")
        return _cached_api_key
    except Exception:
        _cached_api_key = ""
        return _cached_api_key


def _get_headers() -> dict:
    """APIリクエスト用ヘッダーを取得."""
    headers = {}
    api_key = _get_api_key()
    if api_key:
        headers["x-api-key"] = api_key
    return headers


# ペース予想結果と有利脚質のマッピング
PACE_FAVORABLE_STYLES = {
    "ハイ": ["差し", "追込"],
    "ミドル": ["先行", "差し"],
    "スロー": ["逃げ", "先行"],
}


def _get_running_styles(race_id: str) -> list[dict]:
    """APIから脚質データを取得する."""
    try:
        response = requests.get(
            f"{JRAVAN_API_URL}/races/{race_id}/running-styles",
            headers=_get_headers(),
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
    # 逃げ馬が1頭のみ → スローペース傾向
    if front_runners >= 3:
        return "ハイ"
    elif front_runners == 1:
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
