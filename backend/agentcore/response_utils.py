"""レスポンス処理のユーティリティ関数.

bedrock_agentcore / strands に依存しないピュア関数を配置し、
テストから直接インポート可能にする。
"""

import json

BET_PROPOSALS_SEPARATOR = "---BET_PROPOSALS_JSON---"


def inject_bet_proposal_separator(
    message_text: str, cached_result: dict | None
) -> str:
    """キャッシュされたツール結果からセパレータ付きJSONを付与する.

    Args:
        message_text: LLMの応答テキスト
        cached_result: generate_bet_proposal のキャッシュ結果（Noneの場合は何もしない）

    Returns:
        セパレータ付きの応答テキスト。キャッシュがない/エラーの場合はそのまま返す。
    """
    if cached_result is None or "error" in cached_result:
        return message_text

    return (
        message_text
        + "\n"
        + BET_PROPOSALS_SEPARATOR
        + "\n"
        + json.dumps(cached_result, ensure_ascii=False)
    )
