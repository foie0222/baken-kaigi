"""agentcore/agent.py のユーティリティ関数のテスト."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class TestBetProposalPrompt:
    """BET_PROPOSAL_SYSTEM_PROMPT の基本検証."""

    def test_買い目提案用プロンプトにEVベースツール必須指示が含まれる(self):
        from agentcore.prompts.bet_proposal import BET_PROPOSAL_SYSTEM_PROMPT

        assert "analyze_race_for_betting" in BET_PROPOSAL_SYSTEM_PROMPT
        assert "propose_bets" in BET_PROPOSAL_SYSTEM_PROMPT
        assert "必ず" in BET_PROPOSAL_SYSTEM_PROMPT

    def test_買い目提案用プロンプトにフォールバック禁止が含まれる(self):
        from agentcore.prompts.bet_proposal import BET_PROPOSAL_SYSTEM_PROMPT

        assert "テキストで代替分析を行ってはならない" in BET_PROPOSAL_SYSTEM_PROMPT

    def test_買い目提案用プロンプトにセパレータ指示が含まれる(self):
        from agentcore.prompts.bet_proposal import BET_PROPOSAL_SYSTEM_PROMPT

        assert "---BET_PROPOSALS_JSON---" in BET_PROPOSAL_SYSTEM_PROMPT

    def test_プロンプトモジュールからエクスポートされている(self):
        from agentcore.prompts import BET_PROPOSAL_SYSTEM_PROMPT

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
    import re

    # 正規表現でセパレーターのバリエーションを検出（行全体がセパレーターである場合のみ）
    pattern = r"^\s*\*{0,2}-{0,3}\s*SUGGESTED_QUESTIONS\s*-{0,3}\*{0,2}\s*$"
    match = re.search(pattern, text, flags=re.MULTILINE)

    if not match:
        return text.strip(), []

    main_text = text[: match.start()].strip()
    questions_text = text[match.end() :].strip()

    if not questions_text:
        return main_text, []

    # すべての行を取得し、空行を除外
    raw_questions = [q.strip() for q in questions_text.split("\n") if q.strip()]

    # 1行に複数の質問が「？」区切りで並んでいる場合を展開
    expanded: list[str] = []
    for line in raw_questions:
        # 「？ 」で区切られた複数質問を分割（末尾の？は保持）
        parts = re.split(r"？\s+", line)
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            # 最後のパート以外は「？」を付け直す
            if i < len(parts) - 1:
                part += "？"
            expanded.append(part)

    # 先頭の「-」「- 」を除去（箇条書き形式の場合）
    questions = [q.lstrip("-").strip() for q in expanded]

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

    def test_マークダウン太字セパレーターを処理できる(self):
        """AIがマークダウン太字でセパレーターを出力した場合も処理できる."""
        text = """分析結果です。

**SUGGESTED_QUESTIONS---**
穴馬を探して
展開予想は？"""

        main_text, questions = _extract_suggested_questions(text)

        assert main_text == "分析結果です。"
        assert len(questions) == 2
        assert questions[0] == "穴馬を探して"
        assert questions[1] == "展開予想は？"

    def test_マークダウン太字セパレーター_質問が同一行(self):
        """太字セパレーターの後に質問が改行なしで続く場合も処理できる."""
        text = "分析結果。\n\n**SUGGESTED_QUESTIONS---**\n2番が外れた場合の保険は？ 4-6追加すべき？ AI指数の差は？"

        main_text, questions = _extract_suggested_questions(text)

        assert main_text == "分析結果。"
        assert len(questions) >= 2

    def test_ダッシュなし太字セパレーター(self):
        """**SUGGESTED_QUESTIONS** のみの場合も処理できる."""
        text = """分析結果。

**SUGGESTED_QUESTIONS**
穴馬を探して
展開予想は？"""

        main_text, questions = _extract_suggested_questions(text)

        assert main_text == "分析結果。"
        assert len(questions) == 2


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


# =============================================================================
# _format_cart_summary のテスト
# =============================================================================

# agent.py は strands/bedrock_agentcore に依存しているため直接インポートできない。
# ロジックを再定義してテストする。

_BET_TYPE_NAMES = {
    "win": "単勝",
    "place": "複勝",
    "quinella": "馬連",
    "quinella_place": "ワイド",
    "exacta": "馬単",
    "trio": "三連複",
    "trifecta": "三連単",
}


def _format_cart_summary(cart_items: list) -> str:
    """カート内容をフォーマットする（agent.py からロジックを再定義）."""
    if not cart_items:
        return "カートは空です"

    lines = []
    horse_count: dict[int, int] = {}
    race_ids: dict[str, str] = {}
    total_amount = 0

    for i, item in enumerate(cart_items, 1):
        race_id = item.get("raceId", "")
        bet_type = item.get("betType", "")
        bet_type_display = _BET_TYPE_NAMES.get(bet_type, bet_type)
        horse_numbers = item.get("horseNumbers", [])
        amount = item.get("amount", 0)
        race_name = item.get("raceName", "")

        if race_id:
            race_ids[race_id] = race_name

        display = "-".join(str(n) for n in horse_numbers)
        line = f"{i}. {race_name} {bet_type_display} {display} ¥{amount:,}"
        lines.append(line)
        total_amount += amount

        for hn in horse_numbers:
            horse_count[hn] = horse_count.get(hn, 0) + 1

    total_bets = len(cart_items)
    header = f"買い目一覧（全{total_bets}点、合計¥{total_amount:,}）"

    race_id_lines = []
    for rid, rname in race_ids.items():
        race_id_lines.append(f"  {rname}: race_id={rid}")

    freq_lines = []
    for hn in sorted(horse_count.keys()):
        count = horse_count[hn]
        freq_lines.append(f"  {hn}番: {total_bets}点中{count}点に出現")

    parts = [header]
    if race_id_lines:
        parts.append("")
        parts.append("対象レース:")
        parts.extend(race_id_lines)
    parts.append("")
    parts.extend(lines)
    if freq_lines:
        parts.append("")
        parts.append("馬番の出現頻度:")
        parts.extend(freq_lines)

    return "\n".join(parts)


class TestFormatCartSummary:
    """_format_cart_summary 関数のテスト."""

    def test_空カートの場合(self):
        """カートが空の場合は固定メッセージを返す."""
        assert _format_cart_summary([]) == "カートは空です"

    def test_レースIDが出力に含まれる(self):
        """race_id がフォーマットされた出力に含まれ、ツール呼び出しに使える."""
        items = [
            {
                "raceId": "202505020811",
                "raceName": "きさらぎ賞",
                "betType": "quinella",
                "horseNumbers": [2, 6],
                "amount": 300,
            },
        ]
        result = _format_cart_summary(items)

        assert "対象レース:" in result
        assert "race_id=202505020811" in result
        assert "きさらぎ賞: race_id=202505020811" in result

    def test_複数レースのIDが全て含まれる(self):
        """複数レースがある場合、全てのrace_idが含まれる."""
        items = [
            {
                "raceId": "202505020811",
                "raceName": "きさらぎ賞",
                "betType": "win",
                "horseNumbers": [2],
                "amount": 300,
            },
            {
                "raceId": "202505020812",
                "raceName": "東京新聞杯",
                "betType": "win",
                "horseNumbers": [5],
                "amount": 300,
            },
        ]
        result = _format_cart_summary(items)

        assert "race_id=202505020811" in result
        assert "race_id=202505020812" in result
        assert "きさらぎ賞" in result
        assert "東京新聞杯" in result

    def test_馬番出現頻度が計算される(self):
        """馬番の出現頻度が正しく計算される."""
        items = [
            {
                "raceId": "R1",
                "raceName": "R1",
                "betType": "quinella",
                "horseNumbers": [2, 6],
                "amount": 300,
            },
            {
                "raceId": "R1",
                "raceName": "R1",
                "betType": "quinella",
                "horseNumbers": [2, 8],
                "amount": 300,
            },
        ]
        result = _format_cart_summary(items)

        assert "2番: 2点中2点に出現" in result
        assert "6番: 2点中1点に出現" in result
        assert "8番: 2点中1点に出現" in result

    def test_合計金額と点数がヘッダーに含まれる(self):
        """ヘッダーに合計金額と買い目数が含まれる."""
        items = [
            {
                "raceId": "R1",
                "raceName": "R1",
                "betType": "win",
                "horseNumbers": [1],
                "amount": 500,
            },
            {
                "raceId": "R1",
                "raceName": "R1",
                "betType": "place",
                "horseNumbers": [3],
                "amount": 300,
            },
        ]
        result = _format_cart_summary(items)

        assert "全2点" in result
        assert "¥800" in result

    def test_券種名が日本語に変換される(self):
        """betType が日本語名に変換される."""
        items = [
            {
                "raceId": "R1",
                "raceName": "テスト",
                "betType": "trifecta",
                "horseNumbers": [1, 2, 3],
                "amount": 100,
            },
        ]
        result = _format_cart_summary(items)

        assert "三連単" in result
        assert "1-2-3" in result


# =============================================================================
# _extract_bet_actions のテスト
# =============================================================================

from response_utils import BET_ACTIONS_SEPARATOR


def _extract_bet_actions(text: str) -> tuple[str, list[dict]]:
    """応答テキストから買い目アクション情報を抽出する（agent.py からロジックを再定義）."""
    idx = text.find(BET_ACTIONS_SEPARATOR)
    if idx == -1:
        return text, []

    main_text = text[:idx].strip()
    json_text = text[idx + len(BET_ACTIONS_SEPARATOR) :].strip()

    if not json_text:
        return main_text, []

    try:
        actions = json.loads(json_text)
        if isinstance(actions, list):
            return main_text, actions[:5]
    except json.JSONDecodeError:
        # JSONパースに失敗した場合はアクションなしとして扱う
        pass

    return main_text, []


class TestExtractBetActions:
    """_extract_bet_actions 関数のテスト."""

    def test_アクションリストを抽出できる(self):
        """セパレーターの後のアクションJSONを抽出できる."""
        actions_json = json.dumps([
            {"type": "remove_horse", "label": "3番を外す", "params": {"horse_number": 3}},
            {"type": "change_amount", "label": "金額を500円に", "params": {"amount": 500}},
        ], ensure_ascii=False)
        text = f"分析結果です。\n\n{BET_ACTIONS_SEPARATOR}\n{actions_json}"

        main_text, actions = _extract_bet_actions(text)

        assert main_text == "分析結果です。"
        assert len(actions) == 2
        assert actions[0]["type"] == "remove_horse"
        assert actions[0]["params"]["horse_number"] == 3
        assert actions[1]["type"] == "change_amount"
        assert actions[1]["params"]["amount"] == 500

    def test_セパレーターがない場合は空リストを返す(self):
        """セパレーターがない場合は本文のみを返す."""
        text = "分析結果のみ。アクションなし。"

        main_text, actions = _extract_bet_actions(text)

        assert main_text == text
        assert actions == []

    def test_不正JSONの場合は空リストを返す(self):
        """JSONパースに失敗した場合は空リストを返す."""
        text = f"分析結果。\n\n{BET_ACTIONS_SEPARATOR}\n{{invalid json}}"

        main_text, actions = _extract_bet_actions(text)

        assert main_text == "分析結果。"
        assert actions == []

    def test_5つまでに制限される(self):
        """アクションは5つまでに制限される."""
        many_actions = [{"type": "remove_horse", "label": f"{i}番を外す", "params": {"horse_number": i}} for i in range(1, 8)]
        text = f"分析です。\n\n{BET_ACTIONS_SEPARATOR}\n{json.dumps(many_actions, ensure_ascii=False)}"

        main_text, actions = _extract_bet_actions(text)

        assert len(actions) == 5

    def test_空のJSON配列の場合は空リストを返す(self):
        """空のJSON配列の場合."""
        text = f"分析結果。\n\n{BET_ACTIONS_SEPARATOR}\n[]"

        main_text, actions = _extract_bet_actions(text)

        assert main_text == "分析結果。"
        assert actions == []

    def test_セパレーター後にテキストがない場合(self):
        """セパレーター後に何もない場合は空リストを返す."""
        text = f"分析結果。\n\n{BET_ACTIONS_SEPARATOR}\n"

        main_text, actions = _extract_bet_actions(text)

        assert main_text == "分析結果。"
        assert actions == []

    def test_JSONがオブジェクトの場合は空リストを返す(self):
        """JSONが配列でなくオブジェクトの場合は空リストを返す."""
        text = f"分析結果。\n\n{BET_ACTIONS_SEPARATOR}\n{{\"type\": \"remove_horse\"}}"

        main_text, actions = _extract_bet_actions(text)

        assert main_text == "分析結果。"
        assert actions == []

    def test_SUGGESTED_QUESTIONSとBET_ACTIONSの両方がある場合(self):
        """SUGGESTED_QUESTIONSとBET_ACTIONSが両方ある場合、両方抽出できる."""
        actions_json = json.dumps([
            {"type": "remove_horse", "label": "3番を外す", "params": {"horse_number": 3}},
        ], ensure_ascii=False)
        text = (
            "分析結果です。\n\n"
            "---SUGGESTED_QUESTIONS---\n"
            "穴馬を探して\n"
            "展開予想は？\n\n"
            f"{BET_ACTIONS_SEPARATOR}\n"
            f"{actions_json}"
        )

        # agent.py と同じ順序: 先に bet_actions、次に suggested_questions
        main_text_ba, actions = _extract_bet_actions(text)
        main_text_sq, questions = _extract_suggested_questions(main_text_ba)

        assert len(actions) == 1
        assert actions[0]["type"] == "remove_horse"
        assert len(questions) == 2
        assert questions[0] == "穴馬を探して"
        assert questions[1] == "展開予想は？"


# =============================================================================
# _format_betting_context のテスト
# =============================================================================


def _format_betting_context(summary: dict) -> str:
    """ユーザーの成績サマリーをフォーマットする（agent.py からロジックを再定義）."""
    parts = []
    if summary.get("record_count", 0) > 0:
        parts.append(f"通算成績: {summary['record_count']}件")
        if summary.get("win_rate") is not None:
            parts.append(f"的中率: {summary['win_rate']:.1f}%")
        if summary.get("roi") is not None:
            parts.append(f"回収率: {summary['roi']:.1f}%")
        if summary.get("net_profit") is not None:
            parts.append(f"収支: {summary['net_profit']:+,}円")
    return " / ".join(parts) if parts else "成績データなし"


class TestFormatBettingContext:
    """_format_betting_context 関数のテスト."""

    def test_全項目が揃っている場合(self):
        """全項目が揃っている場合にフォーマットされる."""
        summary = {
            "record_count": 50,
            "win_rate": 25.0,
            "roi": 85.5,
            "net_profit": -7250,
        }
        result = _format_betting_context(summary)

        assert "通算成績: 50件" in result
        assert "的中率: 25.0%" in result
        assert "回収率: 85.5%" in result
        assert "収支: -7,250円" in result
        assert " / " in result

    def test_成績データがない場合(self):
        """record_countが0の場合は成績データなしを返す."""
        summary = {"record_count": 0}
        result = _format_betting_context(summary)

        assert result == "成績データなし"

    def test_空辞書の場合(self):
        """空辞書の場合は成績データなしを返す."""
        result = _format_betting_context({})

        assert result == "成績データなし"

    def test_プラス収支の場合(self):
        """プラス収支はプラス記号付きで表示される."""
        summary = {
            "record_count": 10,
            "win_rate": 40.0,
            "roi": 120.0,
            "net_profit": 5000,
        }
        result = _format_betting_context(summary)

        assert "収支: +5,000円" in result

    def test_roi_win_rateがNoneの場合(self):
        """roiやwin_rateがNoneの場合はスキップされる."""
        summary = {
            "record_count": 5,
            "win_rate": None,
            "roi": None,
            "net_profit": -1000,
        }
        result = _format_betting_context(summary)

        assert "通算成績: 5件" in result
        assert "的中率" not in result
        assert "回収率" not in result
        assert "収支: -1,000円" in result

    def test_Decimal型の値を処理できる(self):
        """DynamoDB由来のDecimal型もfloatフォーマットで処理できる."""
        from decimal import Decimal

        summary = {
            "record_count": 20,
            "win_rate": Decimal("30.0"),
            "roi": Decimal("92.5"),
            "net_profit": Decimal("-1500"),
        }
        result = _format_betting_context(summary)

        assert "的中率: 30.0%" in result
        assert "回収率: 92.5%" in result
        assert "収支: -1,500円" in result
