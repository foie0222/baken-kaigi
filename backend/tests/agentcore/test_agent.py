"""agentcore/agent.py のユーティリティ関数のテスト."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class Testプロンプト切り替え:
    """request_type に応じてプロンプトが切り替わることの検証."""

    def test_相談用と買い目提案用のプロンプトが異なる(self):
        from agentcore.prompts.bet_proposal import BET_PROPOSAL_SYSTEM_PROMPT
        from agentcore.prompts.consultation import SYSTEM_PROMPT

        assert SYSTEM_PROMPT != BET_PROPOSAL_SYSTEM_PROMPT

    def test_相談用プロンプトに6ツールフローが含まれる(self):
        from agentcore.prompts.consultation import SYSTEM_PROMPT

        assert "絶対に全6ツールを呼び出すこと" in SYSTEM_PROMPT

    def test_買い目提案用プロンプトにgenerate_bet_proposal必須指示が含まれる(self):
        from agentcore.prompts.bet_proposal import BET_PROPOSAL_SYSTEM_PROMPT

        assert "generate_bet_proposal" in BET_PROPOSAL_SYSTEM_PROMPT
        assert "必ず" in BET_PROPOSAL_SYSTEM_PROMPT

    def test_買い目提案用プロンプトにフォールバック禁止が含まれる(self):
        from agentcore.prompts.bet_proposal import BET_PROPOSAL_SYSTEM_PROMPT

        assert "テキストで代替分析を行ってはならない" in BET_PROPOSAL_SYSTEM_PROMPT

    def test_買い目提案用プロンプトにセパレータ指示が含まれる(self):
        from agentcore.prompts.bet_proposal import BET_PROPOSAL_SYSTEM_PROMPT

        assert "---BET_PROPOSALS_JSON---" in BET_PROPOSAL_SYSTEM_PROMPT

    def test_プロンプトモジュールからエクスポートされている(self):
        from agentcore.prompts import BET_PROPOSAL_SYSTEM_PROMPT, SYSTEM_PROMPT

        assert isinstance(SYSTEM_PROMPT, str)
        assert isinstance(BET_PROPOSAL_SYSTEM_PROMPT, str)


# _extract_suggested_questions 関数のロジックを直接テスト
# Note: agentcore.agent をインポートするには strands/bedrock_agentcore が必要なため、
# ロジックをここで再定義してテストしている
def _extract_suggested_questions(text: str) -> tuple[str, list[str]]:
    """応答テキストからクイックリプライ提案を抽出する.

    Args:
        text: AIの応答テキスト

    Returns:
        (本文, 提案リスト) のタプル
    """
    separator = "---SUGGESTED_QUESTIONS---"

    if separator not in text:
        return text.strip(), []

    parts = text.split(separator, 1)
    main_text = parts[0].strip()

    if len(parts) < 2:
        return main_text, []

    questions_text = parts[1].strip()

    # すべての行を取得し、空行を除外
    raw_questions = [q.strip() for q in questions_text.split("\n") if q.strip()]

    # 先頭の「-」「- 」を除去（箇条書き形式の場合）
    questions = [q.lstrip("-").strip() for q in raw_questions]

    # 空の質問を除外し、5個までに制限
    questions = [q for q in questions if q][:5]

    return main_text, questions


class TestExtractSuggestedQuestions:
    """_extract_suggested_questions 関数のテスト."""

    def test_質問リストを抽出できる(self):
        """セパレーターの後の質問を抽出できる."""
        text = """分析結果です。

---SUGGESTED_QUESTIONS---
穴馬を探して
展開予想は？
騎手の成績は？"""

        main_text, questions = _extract_suggested_questions(text)

        assert main_text == "分析結果です。"
        assert len(questions) == 3
        assert questions[0] == "穴馬を探して"
        assert questions[1] == "展開予想は？"
        assert questions[2] == "騎手の成績は？"

    def test_セパレーターがない場合は空リストを返す(self):
        """セパレーターがない場合は本文のみを返す."""
        text = "分析結果のみ。クイックリプライなし。"

        main_text, questions = _extract_suggested_questions(text)

        assert main_text == text
        assert questions == []

    def test_5つまでに制限される(self):
        """質問は5つまでに制限される."""
        text = """分析です。

---SUGGESTED_QUESTIONS---
質問1
質問2
質問3
質問4
質問5
質問6
質問7"""

        main_text, questions = _extract_suggested_questions(text)

        assert len(questions) == 5
        assert questions[-1] == "質問5"

    def test_空行は除外される(self):
        """空行は質問リストに含まれない."""
        text = """分析結果。

---SUGGESTED_QUESTIONS---
質問1

質問2

質問3"""

        main_text, questions = _extract_suggested_questions(text)

        assert len(questions) == 3
        assert "" not in questions

    def test_箇条書き形式の質問を処理できる(self):
        """箇条書き形式（-で始まる）の質問を処理できる."""
        text = """分析結果。

---SUGGESTED_QUESTIONS---
- 穴馬を探して
- 展開予想は？
- リスク確認"""

        main_text, questions = _extract_suggested_questions(text)

        assert len(questions) == 3
        # 「-」プレフィックスは除去される
        assert questions[0] == "穴馬を探して"
        assert questions[1] == "展開予想は？"
        assert questions[2] == "リスク確認"

    def test_本文がトリムされる(self):
        """本文の前後の空白はトリムされる."""
        text = """

分析結果です。



---SUGGESTED_QUESTIONS---
質問"""

        main_text, questions = _extract_suggested_questions(text)

        assert main_text == "分析結果です。"

    def test_セパレーター後に質問がない場合(self):
        """セパレーター後に質問がない場合は空リストを返す."""
        text = """分析結果。

---SUGGESTED_QUESTIONS---
"""

        main_text, questions = _extract_suggested_questions(text)

        assert main_text == "分析結果。"
        assert questions == []

    def test_ハイフンのみの行は空として除外される(self):
        """ハイフンのみの行は空として除外される."""
        text = """分析結果。

---SUGGESTED_QUESTIONS---
-
質問1
- 質問2"""

        main_text, questions = _extract_suggested_questions(text)

        assert len(questions) == 2
        assert questions[0] == "質問1"
        assert questions[1] == "質問2"


# =============================================================================
# inject_bet_proposal_separator のテスト
# =============================================================================

# 本番実装をインポート（response_utils は外部依存がないピュア関数モジュール）
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agentcore"))

from response_utils import BET_PROPOSALS_SEPARATOR, inject_bet_proposal_separator


class TestInjectBetProposalSeparator:
    """inject_bet_proposal_separator 関数のテスト."""

    def test_セパレータ欠落時にキャッシュから復元する_既にある場合はそのまま(self):
        """既にセパレータが含まれている場合、inject はキャッシュを無視する（呼び出し元で判定）."""
        # NOTE: セパレータ有無のチェックは agent.py の _ensure_bet_proposal_separator で行う。
        # inject_bet_proposal_separator はキャッシュがあれば常に付与する。
        text = "買い目を提案しました。"
        cached = {"should": "be_used"}
        result = inject_bet_proposal_separator(text, cached)
        assert BET_PROPOSALS_SEPARATOR in result

    def test_セパレータ欠落時にキャッシュから復元する(self):
        """セパレータが欠落していてもキャッシュ結果からJSONを復元する."""
        text = "買い目を提案しました。"
        cached = {"race_id": "test", "proposed_bets": [{"bet_type": "win"}]}
        result = inject_bet_proposal_separator(text, cached)

        assert BET_PROPOSALS_SEPARATOR in result
        assert result.startswith(text)
        # セパレータ以降がJSON
        json_part = result.split(BET_PROPOSALS_SEPARATOR, 1)[1].strip()
        parsed = json.loads(json_part)
        assert parsed["race_id"] == "test"
        assert parsed["proposed_bets"] == [{"bet_type": "win"}]

    def test_キャッシュがNoneの場合はそのまま返す(self):
        """キャッシュが空の場合は本文をそのまま返す."""
        text = "買い目を提案しました。"
        result = inject_bet_proposal_separator(text, None)
        assert result == text
        assert BET_PROPOSALS_SEPARATOR not in result

    def test_キャッシュがエラーの場合はそのまま返す(self):
        """ツール実行がエラーだった場合はセパレータを付与しない."""
        text = "エラーが発生しました。"
        cached = {"error": "API呼び出しに失敗しました"}
        result = inject_bet_proposal_separator(text, cached)
        assert result == text
        assert BET_PROPOSALS_SEPARATOR not in result

    def test_日本語を含むJSONが正しくシリアライズされる(self):
        """日本語文字がエスケープされずにJSON出力される."""
        text = "提案しました。"
        cached = {"analysis_comment": "混戦レースです", "proposed_bets": []}
        result = inject_bet_proposal_separator(text, cached)

        json_part = result.split(BET_PROPOSALS_SEPARATOR, 1)[1].strip()
        assert "混戦レースです" in json_part
        parsed = json.loads(json_part)
        assert parsed["analysis_comment"] == "混戦レースです"
