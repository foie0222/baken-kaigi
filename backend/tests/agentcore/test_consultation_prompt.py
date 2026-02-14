"""agentcore/prompts/consultation.py および bet_proposal.py のプロンプト内容テスト."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentcore.prompts.bet_proposal import BET_PROPOSAL_SYSTEM_PROMPT
from agentcore.prompts.consultation import SYSTEM_PROMPT


class TestSystemPromptの基本構造:
    """SYSTEM_PROMPTの基本的な構造を検証する."""

    def test_SYSTEM_PROMPT変数が文字列(self):
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 0

    def test_重要なルール8項目が存在(self):
        assert "## 重要なルール" in SYSTEM_PROMPT
        assert "**推奨禁止**" in SYSTEM_PROMPT
        assert "**促進禁止**" in SYSTEM_PROMPT
        assert "**判断委任**" in SYSTEM_PROMPT
        assert "**データ駆動**" in SYSTEM_PROMPT
        assert "**弱点指摘**" in SYSTEM_PROMPT
        assert "**冷静促進**" in SYSTEM_PROMPT
        assert "**AI指数は期待値ではない**" in SYSTEM_PROMPT
        assert "**日本語で回答**" in SYSTEM_PROMPT

    def test_6ツール必須呼び出しフローが存在(self):
        assert "絶対に全6ツールを呼び出すこと（省略厳禁）" in SYSTEM_PROMPT
        assert "Step 0" in SYSTEM_PROMPT
        assert "Step 1" in SYSTEM_PROMPT
        assert "Step 2" in SYSTEM_PROMPT
        assert "Step 3" in SYSTEM_PROMPT
        assert "Step 4" in SYSTEM_PROMPT
        assert "Step 5" in SYSTEM_PROMPT

    def test_禁止表現が維持されている(self):
        assert "「この馬がおすすめです」" in SYSTEM_PROMPT
        assert "「勝てそうですね」" in SYSTEM_PROMPT
        assert "「買いましょう」" in SYSTEM_PROMPT
        assert "「狙うべきです」" in SYSTEM_PROMPT


class TestバリューファーストSセクション:
    """分析の優先順位（バリュー・ファースト）セクションの検証."""

    def test_セクションヘッダが存在(self):
        assert "## 分析の優先順位（バリュー・ファースト）" in SYSTEM_PROMPT

    def test_第1優先_期待値判定(self):
        assert "### 第1優先: 期待値判定" in SYSTEM_PROMPT
        assert "analyze_bet_selectionのexpected_returnが全分析の基盤" in SYSTEM_PROMPT
        assert "JRA控除率を考慮すると長期的にマイナス" in SYSTEM_PROMPT

    def test_第2優先_AI合議(self):
        assert "### 第2優先: AI合議による信頼度判定" in SYSTEM_PROMPT
        assert "2ソース以上が合意" in SYSTEM_PROMPT

    def test_第3優先_展開リスク(self):
        assert "### 第3優先: 展開・リスクとの整合性" in SYSTEM_PROMPT

    def test_第4優先_市場の歪み(self):
        assert "### 第4優先: 市場の歪み検出" in SYSTEM_PROMPT
        assert "市場の見落とし候補" in SYSTEM_PROMPT


class TestマルチソースAI分析手順セクション:
    """マルチソースAI指数の分析手順セクションの検証."""

    def test_セクションヘッダが存在(self):
        assert "## マルチソースAI指数の分析手順" in SYSTEM_PROMPT

    def test_合議分析の手順(self):
        assert "### 合議分析（2ソース以上ある場合）" in SYSTEM_PROMPT
        assert "まず合意度を確認" in SYSTEM_PROMPT
        assert "完全合意の場合" in SYSTEM_PROMPT

    def test_4象限マトリクス(self):
        assert "### AI指数×オッズの4象限マトリクス" in SYSTEM_PROMPT
        assert "AI合意上位" in SYSTEM_PROMPT
        assert "AI評価割れ" in SYSTEM_PROMPT
        assert "最重要: 妙味あり" in SYSTEM_PROMPT


class Testレースタイプ別セクション:
    """レースタイプ別の分析アプローチセクションの検証."""

    def test_セクションヘッダが存在(self):
        assert "## レースタイプ別の分析アプローチ" in SYSTEM_PROMPT

    def test_G1G2セクション(self):
        assert "### G1・G2（重賞）" in SYSTEM_PROMPT
        assert "補正1.05" in SYSTEM_PROMPT

    def test_ハンデ戦セクション(self):
        assert "### ハンデ戦" in SYSTEM_PROMPT
        assert "補正0.85" in SYSTEM_PROMPT

    def test_新馬戦セクション(self):
        assert "### 新馬戦" in SYSTEM_PROMPT
        assert "補正0.88" in SYSTEM_PROMPT

    def test_障害戦セクション(self):
        assert "### 障害戦" in SYSTEM_PROMPT
        assert "補正0.80" in SYSTEM_PROMPT


class Testツール矛盾判断基準セクション:
    """ツール結果が矛盾する場合の判断基準セクションの検証."""

    def test_セクションヘッダが存在(self):
        assert "## ツール結果が矛盾する場合の判断基準" in SYSTEM_PROMPT

    def test_AI上位vs展開不利(self):
        assert "### AI上位 vs 展開不利" in SYSTEM_PROMPT

    def test_期待値プラスvs高リスク(self):
        assert "### 期待値プラス vs 高リスクシナリオ" in SYSTEM_PROMPT

    def test_AI乖離vsオッズ安定(self):
        assert "### AI乖離 vs オッズ安定" in SYSTEM_PROMPT

    def test_全シグナル一致(self):
        assert "### 全シグナル一致（好材料揃い）" in SYSTEM_PROMPT


class Test弱点改善アクションセクション:
    """弱点指摘→改善アクションの提示セクションの検証."""

    def test_セクションヘッダが存在(self):
        assert "## 弱点指摘 → 改善アクションの提示（セット厳守）" in SYSTEM_PROMPT

    def test_トリガミ検知時(self):
        assert "### トリガミ検知時" in SYSTEM_PROMPT
        assert "買い目を3→2点に絞る" in SYSTEM_PROMPT

    def test_人気馬偏重検知時(self):
        assert "### 人気馬偏重検知時" in SYSTEM_PROMPT

    def test_見送り推奨時(self):
        assert "### 見送り推奨時" in SYSTEM_PROMPT
        assert "見送りは\"負けない\"という最強の戦略" in SYSTEM_PROMPT

    def test_期待値マイナス時(self):
        assert "### 期待値マイナス時" in SYSTEM_PROMPT


class Test応答の構成更新:
    """応答の構成が「結論→根拠」順に更新されていることの検証."""

    def test_結論先行フォーマット(self):
        assert "各項目は冒頭に1行結論を置き、その後に根拠データを記載する" in SYSTEM_PROMPT

    def test_AI指数期待値の結論フォーマット(self):
        assert "期待値○.○○ → {妙味あり/割高}" in SYSTEM_PROMPT

    def test_オッズ変動の結論フォーマット(self):
        assert "市場評価は{安定/変動あり}" in SYSTEM_PROMPT

    def test_展開予想の結論フォーマット(self):
        assert "{ペース}予想 → 選択馬に{有利/不利/中立}" in SYSTEM_PROMPT

    def test_リスク分析の結論フォーマット(self):
        assert "見送りスコアX/10 → {見送り推奨/慎重検討/問題なし}" in SYSTEM_PROMPT

    def test_総合判断材料にエッジとリスクを含む(self):
        assert "この買い目のエッジは○○。リスクは○○。最終判断はご自身で" in SYSTEM_PROMPT

    def test_AI合議レベルが記載項目に含まれる(self):
        assert "AI合議レベル" in SYSTEM_PROMPT

    def test_4象限分析が記載項目に含まれる(self):
        assert "AI×オッズ4象限分析" in SYSTEM_PROMPT


class Testツール説明の更新:
    """get_ai_predictionのツール説明が更新されていることの検証."""

    def test_旧説明が削除されている(self):
        assert "ai-shisu.com" not in SYSTEM_PROMPT

    def test_新説明が含まれている(self):
        assert "複数ソースがある場合はコンセンサス分析も返す" in SYSTEM_PROMPT

    def test_sourceパラメータが追加されている(self):
        assert "Noneで全ソース取得" in SYSTEM_PROMPT

    def test_sources戻り値が追加されている(self):
        assert "`sources`: ソース別の予想リスト" in SYSTEM_PROMPT

    def test_consensus戻り値が追加されている(self):
        assert "`consensus`: コンセンサス分析（2ソース以上の場合）" in SYSTEM_PROMPT
        assert "`agreed_top3`: 合意上位3頭" in SYSTEM_PROMPT
        assert "`consensus_level`: 合議レベル（完全合意/概ね合意/部分合意/大きな乖離）" in SYSTEM_PROMPT
        assert "`divergence_horses`: 評価が割れている馬リスト" in SYSTEM_PROMPT


class Test推奨表現の追加:
    """新しい推奨表現が追加されていることの検証."""

    def test_AI合意表現(self):
        assert "AI2社が一致して8番を最上位評価。独立したモデルの合意は信頼に値する" in SYSTEM_PROMPT

    def test_AI乖離表現(self):
        assert "3番はAI-A 2位だがAI-B 7位。評価が大きく割れており不確実性が高い" in SYSTEM_PROMPT

    def test_見送り戦略表現(self):
        assert "見送りは\"負けない\"最強の戦略。資金を温存して次のレースに備える手もある" in SYSTEM_PROMPT

    def test_市場見落とし表現(self):
        assert "AI合意上位かつオッズ高い5番は市場の見落とし候補。期待値1.2で統計的に妙味あり" in SYSTEM_PROMPT


class TestBetProposalSystemPromptの基本構造:
    """BET_PROPOSAL_SYSTEM_PROMPTの基本的な構造を検証する."""

    def test_変数が文字列(self):
        assert isinstance(BET_PROPOSAL_SYSTEM_PROMPT, str)
        assert len(BET_PROPOSAL_SYSTEM_PROMPT) > 0

    def test_EVベースのツール名が記載されている(self):
        assert "analyze_race_for_betting" in BET_PROPOSAL_SYSTEM_PROMPT
        assert "propose_bets" in BET_PROPOSAL_SYSTEM_PROMPT

    def test_ツール呼び出し必須指示が含まれる(self):
        assert "必ず" in BET_PROPOSAL_SYSTEM_PROMPT
        assert "analyze_race_for_betting" in BET_PROPOSAL_SYSTEM_PROMPT

    def test_フォールバック分析禁止指示が含まれる(self):
        assert "テキストで代替分析を行ってはならない" in BET_PROPOSAL_SYSTEM_PROMPT

    def test_他ツール呼び出し禁止指示が含まれる(self):
        assert "以外のツールを呼び出してはならない" in BET_PROPOSAL_SYSTEM_PROMPT

    def test_セパレータ出力指示が含まれる(self):
        assert "---BET_PROPOSALS_JSON---" in BET_PROPOSAL_SYSTEM_PROMPT

    def test_相談用プロンプトとは異なる内容(self):
        assert BET_PROPOSAL_SYSTEM_PROMPT != SYSTEM_PROMPT

    def test_相談用プロンプトの6ツールフローを含まない(self):
        assert "絶対に全6ツールを呼び出すこと" not in BET_PROPOSAL_SYSTEM_PROMPT
