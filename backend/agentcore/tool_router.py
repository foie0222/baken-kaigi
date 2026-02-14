"""ツールルーター - 質問カテゴリに応じたツール選択."""

from typing import Any, Callable, Literal

# ツールカテゴリ定義
TOOL_CATEGORIES = {
    "full_analysis": {
        "description": "初回の包括的分析（カート分析、フル分析依頼）",
        "keywords": ["分析", "診断", "チェック", "どう思", "大丈夫", "カート"],
    },
    "horse_focused": {
        "description": "特定の馬・騎手・調教師に関する質問",
        "keywords": ["馬", "騎手", "ジョッキー", "調教", "血統", "厩舎", "体重", "斤量"],
    },
    "bet_focused": {
        "description": "買い目・賭け方に関する質問",
        "keywords": ["買い目", "馬券", "オッズ", "配当", "期待値", "トリガミ", "金額", "券種"],
    },
    "race_focused": {
        "description": "レース展開・コース特性に関する質問",
        "keywords": ["展開", "ペース", "コース", "馬場", "距離", "枠順", "逃げ", "差し", "先行"],
    },
    "risk_focused": {
        "description": "リスク・注意点に関する質問",
        "keywords": ["リスク", "危険", "注意", "罠", "見送", "やめ", "不安"],
    },
    "followup": {
        "description": "既に分析済みの追加質問（データ取得不要）",
        "keywords": [],
    },
}


def classify_question(user_message: str, has_cart: bool = False, has_runners: bool = False) -> str:
    """ユーザーの質問をカテゴリに分類する.

    Args:
        user_message: ユーザーのメッセージ
        has_cart: カートにアイテムがあるか
        has_runners: 出走馬データがあるか

    Returns:
        カテゴリ名
    """
    msg = user_message

    # 全カテゴリのキーワードマッチ（followup除く）
    scores: dict[str, int] = {}
    for category, config in TOOL_CATEGORIES.items():
        if category == "followup":
            continue
        keywords = config["keywords"]
        score = sum(1 for kw in keywords if kw in msg)
        if score > 0:
            scores[category] = score

    if scores:
        max_score = max(scores.values())
        top_categories = [k for k, v in scores.items() if v == max_score]

        if len(top_categories) == 1:
            return top_categories[0]

        # 同点の場合:
        # - データコンテキスト（カートまたは出走馬）がある → full_analysis優先
        # - データコンテキストなし → 具体的カテゴリ優先
        if "full_analysis" in top_categories:
            if has_cart or has_runners:
                return "full_analysis"
            specific = [k for k in top_categories if k != "full_analysis"]
            if specific:
                return specific[0]

        return top_categories[0]

    # キーワードに一致しない場合はfollowup
    return "followup"


CategoryType = Literal[
    "full_analysis", "horse_focused", "bet_focused",
    "race_focused", "risk_focused", "followup",
]


def get_tools_for_category(category: CategoryType) -> list[Callable[..., Any]]:
    """カテゴリに応じたツールリストを返す.

    Args:
        category: 質問カテゴリ

    Returns:
        ツール関数のリスト
    """
    from tools.ai_prediction import get_ai_prediction
    from tools.bet_analysis import analyze_bet_selection
    from tools.bet_proposal import generate_bet_proposal
    from tools.ev_proposer import propose_bets
    from tools.odds_analysis import analyze_odds_movement
    from tools.pace_analysis import analyze_race_characteristics
    from tools.past_performance import get_past_performance
    from tools.race_analyzer import analyze_race_for_betting
    from tools.race_data import get_race_runners
    from tools.risk_analysis import analyze_risk_factors
    from tools.speed_index import get_speed_index, list_speed_indices_for_date

    all_tools = [
        get_ai_prediction,
        get_speed_index,
        list_speed_indices_for_date,
        get_past_performance,
        get_race_runners,
        analyze_bet_selection,
        analyze_odds_movement,
        analyze_race_characteristics,
        analyze_risk_factors,
        generate_bet_proposal,
        analyze_race_for_betting,
        propose_bets,
    ]

    # EVベース買い目提案専用ツールセット
    ev_proposal_tools = [analyze_race_for_betting, propose_bets]

    tool_sets = {
        "full_analysis": all_tools,
        "horse_focused": [
            get_race_runners,
            get_ai_prediction,
            get_past_performance,
            get_speed_index,
            analyze_race_characteristics,
        ],
        "bet_focused": [
            analyze_bet_selection,
            analyze_odds_movement,
            generate_bet_proposal,
            analyze_risk_factors,
            get_ai_prediction,
            analyze_race_for_betting,
            propose_bets,
        ],
        "race_focused": [
            get_race_runners,
            analyze_race_characteristics,
            get_ai_prediction,
            get_speed_index,
            list_speed_indices_for_date,
        ],
        "risk_focused": [
            analyze_risk_factors,
            analyze_bet_selection,
            analyze_odds_movement,
            get_ai_prediction,
        ],
        "followup": [],
        "ev_proposal": ev_proposal_tools,
    }

    return tool_sets.get(category, all_tools)


# カテゴリ別のプロンプト補助指示
CATEGORY_INSTRUCTIONS = {
    "horse_focused": (
        "【分析フォーカス: 馬・騎手・調教】"
        "この質問は特定の馬や騎手に関するものです。"
        "get_race_runners, get_ai_prediction, get_past_performance を中心に回答してください。"
    ),
    "bet_focused": (
        "【分析フォーカス: 買い目・期待値】"
        "この質問は買い目に関するものです。"
        "analyze_bet_selection, analyze_odds_movement を中心に回答してください。"
    ),
    "race_focused": (
        "【分析フォーカス: レース展開・コース】"
        "この質問はレース展開に関するものです。"
        "analyze_race_characteristics を中心に回答してください。"
    ),
    "risk_focused": (
        "【分析フォーカス: リスク管理】"
        "この質問はリスクに関するものです。"
        "analyze_risk_factors, analyze_bet_selection を中心に回答してください。"
    ),
    "followup": (
        "【フォローアップ質問】"
        "この質問は既に分析済みの追加質問です。"
        "新しいツール呼び出しは不要です。既存の分析結果と知識をもとに簡潔に回答してください。"
    ),
}
