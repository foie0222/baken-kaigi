"""レスポンス処理のユーティリティ関数.

bedrock_agentcore / strands に依存しないピュア関数を配置し、
テストから直接インポート可能にする。
"""

import json

BET_PROPOSALS_SEPARATOR = "---BET_PROPOSALS_JSON---"
BET_ACTIONS_SEPARATOR = "---BET_ACTIONS_JSON---"


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


def replace_or_inject_bet_proposal_json(
    message_text: str, cached_result: dict | None
) -> str:
    """キャッシュされたツール結果で買い目JSONを常に置換する.

    LLMがセパレータ付きで切り詰められた（truncated）JSONを出力するケースに対応。
    キャッシュがある場合はLLMのJSON部分を捨ててキャッシュで置換する。

    Args:
        message_text: LLMの応答テキスト（セパレータ付きの場合あり）
        cached_result: ツールの実行結果キャッシュ

    Returns:
        セパレータ付きの応答テキスト。
    """
    has_valid_cache = cached_result is not None and "error" not in cached_result

    if has_valid_cache:
        # キャッシュがある場合: LLMのJSON部分を捨ててキャッシュで置換
        if BET_PROPOSALS_SEPARATOR in message_text:
            main_text = message_text.split(BET_PROPOSALS_SEPARATOR, 1)[0].strip()
        else:
            main_text = message_text
        return inject_bet_proposal_separator(main_text, cached_result)

    # キャッシュがない場合: LLMの出力をそのまま返す
    return message_text
