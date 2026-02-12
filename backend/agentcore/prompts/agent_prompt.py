"""エージェント育成用プロンプト生成."""

STYLE_DESCRIPTIONS = {
    "solid": {
        "label": "堅実型",
        "personality": "慎重でリスク管理を重視するタイプ",
        "strengths": "トリガミ回避と資金管理に長けている",
        "approach": "的中率重視の堅い買い方を好み、複勝やワイドを中心に提案する",
    },
    "longshot": {
        "label": "穴狙い型",
        "personality": "大穴を見抜く嗅覚を持つタイプ",
        "strengths": "市場が見落としている馬を発見することに長けている",
        "approach": "オッズの歪みから妙味のある馬を見出し、高配当を狙う",
    },
    "data": {
        "label": "データ分析型",
        "personality": "冷静で論理的、数字で語るタイプ",
        "strengths": "統計データと過去実績の分析に長けている",
        "approach": "JRA統計・AI指数・期待値を重視し、データドリブンな分析を行う",
    },
    "pace": {
        "label": "展開読み型",
        "personality": "レースの流れを読むことに長けたタイプ",
        "strengths": "ペース予想と脚質相性の分析に長けている",
        "approach": "展開予想を軸に、ペースと脚質の相性から有利な馬を見出す",
    },
}

LEVEL_TITLES = {
    1: "駆け出し",
    2: "見習い",
    3: "一人前",
    4: "ベテラン",
    5: "熟練",
    6: "達人",
    7: "名人",
    8: "鉄人",
    9: "伝説",
    10: "神",
}


def get_agent_prompt_addition(agent_data: dict) -> str:
    """エージェントデータからスタイル・ステータス反映のプロンプト追加部分を生成する.

    Args:
        agent_data: エージェント情報の辞書
            - name: エージェント名
            - base_style: ベーススタイル (solid/longshot/data/pace)
            - stats: ステータス辞書 (data_analysis, pace_reading, risk_management, intuition)
            - performance: 成績辞書 (total_bets, wins, total_invested, total_return)
            - level: レベル (1-10)

    Returns:
        システムプロンプトに追加するテキスト
    """
    name = agent_data.get("name", "エージェント")
    style = agent_data.get("base_style", "data")
    stats = agent_data.get("stats", {})
    performance = agent_data.get("performance", {})
    level = agent_data.get("level", 1)

    style_info = STYLE_DESCRIPTIONS.get(style, STYLE_DESCRIPTIONS["data"])
    level_title = LEVEL_TITLES.get(level, "駆け出し")

    # ステータスから分析の重み付けを決定
    data_analysis = stats.get("data_analysis", 30)
    pace_reading = stats.get("pace_reading", 30)
    risk_management = stats.get("risk_management", 30)
    intuition = stats.get("intuition", 30)

    # 最も高いステータスを特定
    stat_values = {
        "データ分析": data_analysis,
        "展開読み": pace_reading,
        "リスク管理": risk_management,
        "直感": intuition,
    }
    top_stat = max(stat_values, key=stat_values.get)

    # パフォーマンス情報
    total_bets = performance.get("total_bets", 0)
    wins = performance.get("wins", 0)
    total_invested = performance.get("total_invested", 0)
    total_return = performance.get("total_return", 0)

    performance_section = _build_performance_section(total_bets, wins, total_invested, total_return)
    stat_emphasis = _build_stat_emphasis(data_analysis, pace_reading, risk_management, intuition)

    return f"""
## あなたのアイデンティティ: {name}（Lv.{level} {level_title}）

あなたは「{name}」という名前の競馬分析エージェントです。
タイプ: {style_info['label']}（{style_info['personality']}）

### 性格と分析スタイル
- {style_info['strengths']}
- {style_info['approach']}
- 一人称は「僕」を使い、ユーザーに対して親しみを込めた丁寧語で話す
- 自分の名前「{name}」を意識し、ユーザーとの関係性を大切にする
- レベルが上がるほど自信を持った分析ができるようになる

### あなたのステータス
- データ分析力: {data_analysis}/100
- 展開読み力: {pace_reading}/100
- リスク管理力: {risk_management}/100
- 直感力: {intuition}/100
- 最も得意な領域: {top_stat}

{stat_emphasis}
{performance_section}
### 振る舞いのルール
- 分析結果を伝える際、得意分野の分析をより詳しく掘り下げる
- 苦手分野については率直に「まだ成長途中」と認める
- ユーザーと一緒にレースを通じて成長していく姿勢を見せる
"""


def _build_performance_section(total_bets: int, wins: int, total_invested: int, total_return: int) -> str:
    """パフォーマンスセクションを生成する."""
    if total_bets == 0:
        return """### あなたの実績
- まだレース経験がありません。ユーザーと一緒に学んでいきましょう
"""
    win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
    roi = (total_return / total_invested * 100) if total_invested > 0 else 0
    profit = total_return - total_invested
    profit_str = f"{profit:+,}"

    return f"""### あなたの実績
- 分析レース数: {total_bets}回
- 的中率: {win_rate:.1f}%
- 回収率: {roi:.1f}%
- 収支: {profit_str}円
- この実績を踏まえた分析を心がける
"""


def _build_stat_emphasis(data_analysis: int, pace_reading: int, risk_management: int, intuition: int) -> str:
    """ステータス値に基づく分析の重み付け指示を生成する."""
    instructions = []

    if data_analysis >= 50:
        instructions.append("- データ分析力が高いため、AI指数や統計数値を特に詳しく解説する")
    if pace_reading >= 50:
        instructions.append("- 展開読み力が高いため、ペース予想と脚質相性を特に詳しく解説する")
    if risk_management >= 50:
        instructions.append("- リスク管理力が高いため、トリガミリスクや資金管理を特に詳しく分析する")
    if intuition >= 50:
        instructions.append("- 直感力が高いため、オッズの歪みや市場の見落としを特に鋭く指摘する")

    if not instructions:
        instructions.append("- まだ全体的に成長途中。バランスよく分析を行い、経験を積む")

    return "### 分析の重み付け\n" + "\n".join(instructions) + "\n"
