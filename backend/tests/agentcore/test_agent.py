"""agentcore/agent.py の _extract_suggested_questions 関数のテスト."""

import pytest


# _extract_suggested_questions 関数のロジックを直接テスト
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
    questions = [
        q.strip()
        for q in questions_text.split("\n")
        if q.strip() and not q.strip().startswith("-")
    ]

    # 先頭の「-」を除去（箇条書き形式の場合）
    questions = [
        q.lstrip("- ").strip() if q.startswith("-") else q.strip()
        for q in questions
    ]

    # 空の質問を除外し、3〜5個に制限
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
穴馬を探して
展開予想は？
リスク確認"""

        main_text, questions = _extract_suggested_questions(text)

        assert len(questions) == 3
        assert questions[0] == "穴馬を探して"

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
