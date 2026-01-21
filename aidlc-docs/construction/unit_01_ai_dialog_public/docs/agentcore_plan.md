# AgentCore 実装計画

## 概要

馬券会議 AI エージェントを Amazon Bedrock AgentCore にデプロイするための実装計画。

## 技術選定

| 項目 | 選択 | 理由 |
|------|------|------|
| フレームワーク | Strands Agents | AWS 公式、BedrockAgentCoreApp との親和性が高い |
| デプロイ方式 | Direct Code Deploy | Docker 不要、高速デプロイ（約10秒） |
| AI モデル | Claude Sonnet (Bedrock) | コスト効率と品質のバランス |
| ランタイム | Python 3.12 | 最新の安定版 |

## ディレクトリ構成

```
backend/
├── agentcore/                    # AgentCore エージェント
│   ├── agent.py                  # メインエージェント
│   ├── tools/                    # カスタムツール
│   │   ├── __init__.py
│   │   ├── race_data.py          # レースデータ取得ツール
│   │   └── bet_analysis.py       # 買い目分析ツール
│   ├── prompts/                  # システムプロンプト
│   │   └── consultation.py
│   ├── requirements.txt          # 依存関係
│   └── .bedrock_agentcore.yaml   # AgentCore 設定（自動生成）
└── src/                          # 既存の DDD バックエンド（参考用）
```

## 実装ステップ

### Step 1: プロジェクト初期化

```bash
# ディレクトリ作成
mkdir -p backend/agentcore/tools backend/agentcore/prompts

# CLI インストール
pip install bedrock-agentcore-starter-toolkit
```

### Step 2: カスタムツールの実装

#### tools/race_data.py

JRA-VAN API を呼び出してレース・馬・騎手データを取得するツール。

```python
from strands import tool
import requests
import os

JRAVAN_API_URL = os.environ.get("JRAVAN_API_URL", "https://ryzl2uhi94.execute-api.ap-northeast-1.amazonaws.com/prod")

@tool
def get_race_runners(race_id: str) -> dict:
    """指定されたレースの出走馬一覧を取得する。

    Args:
        race_id: レースID (例: "202506050811")

    Returns:
        出走馬情報のリスト（馬番、馬名、騎手、オッズ、人気）
    """
    response = requests.get(f"{JRAVAN_API_URL}/races/{race_id}/runners")
    response.raise_for_status()
    return response.json()

@tool
def get_race_info(race_id: str) -> dict:
    """指定されたレースの詳細情報を取得する。

    Args:
        race_id: レースID

    Returns:
        レース情報（レース名、開催場、距離、馬場状態など）
    """
    response = requests.get(f"{JRAVAN_API_URL}/races/{race_id}")
    response.raise_for_status()
    return response.json()
```

#### tools/bet_analysis.py

買い目の分析を行うツール。

```python
from strands import tool

@tool
def analyze_bet_selection(
    race_id: str,
    bet_type: str,
    horse_numbers: list[int],
    amount: int,
    runners_data: list[dict]
) -> dict:
    """買い目を分析し、データに基づくフィードバックを生成する。

    Args:
        race_id: レースID
        bet_type: 券種 (win, place, quinella, quinella_place, exacta, trio, trifecta)
        horse_numbers: 選択した馬番のリスト
        amount: 掛け金
        runners_data: 出走馬データ

    Returns:
        分析結果（選択馬のオッズ、人気、期待値など）
    """
    selected_horses = [
        r for r in runners_data
        if r["horse_number"] in horse_numbers
    ]

    total_odds = sum(h.get("odds", 0) or 0 for h in selected_horses)
    avg_popularity = sum(h.get("popularity", 0) or 0 for h in selected_horses) / len(selected_horses) if selected_horses else 0

    return {
        "selected_horses": selected_horses,
        "total_odds": total_odds,
        "average_popularity": avg_popularity,
        "amount": amount,
        "bet_type": bet_type,
    }
```

### Step 3: システムプロンプトの定義

#### prompts/consultation.py

```python
SYSTEM_PROMPT = """あなたは競馬の買い目について相談に乗るAIアシスタント「馬券会議AI」です。

## 重要なルール

1. **推奨禁止**: 「この馬を買うべき」「おすすめ」といった助言をしてはいけません
2. **促進禁止**: ギャンブルを促進する表現は避けてください
3. **判断委任**: 「最終判断はご自身で行ってください」という姿勢を保ってください
4. **客観性**: データに基づく客観的な情報提供のみを行ってください
5. **冷静促進**: ユーザーが熱くなりすぎている場合は、冷静になるよう促してください

## あなたができること

- レースデータの取得と説明
- 選択された馬のオッズ・人気の提示
- 過去成績や騎手データの客観的な提示（将来実装）
- 掛け金に関する責任あるギャンブルの観点からのフィードバック

## 応答スタイル

- 簡潔に（150文字以内を目安）
- データを根拠として提示
- 「〜かもしれません」「〜という見方もあります」など断定を避ける表現
"""
```

### Step 4: メインエージェントの実装

#### agent.py

```python
import os
os.environ["BYPASS_TOOL_CONSENT"] = "true"

from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from tools.race_data import get_race_runners, get_race_info
from tools.bet_analysis import analyze_bet_selection
from prompts.consultation import SYSTEM_PROMPT

# エージェント初期化
agent = Agent(
    system_prompt=SYSTEM_PROMPT,
    tools=[get_race_runners, get_race_info, analyze_bet_selection],
)

# AgentCore アプリ初期化
app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload: dict, context: dict) -> dict:
    """エージェント呼び出しハンドラー。

    payload 形式:
    {
        "prompt": "ユーザーメッセージ",
        "cart_items": [...],  # オプション: カート内容
        "session_id": "..."   # オプション: セッションID
    }
    """
    user_message = payload.get("prompt", "こんにちは")
    cart_items = payload.get("cart_items", [])

    # カート情報をコンテキストとして追加
    if cart_items:
        cart_summary = format_cart_summary(cart_items)
        user_message = f"【現在のカート】\n{cart_summary}\n\n【質問】\n{user_message}"

    # エージェント実行
    result = agent(user_message)

    return {
        "message": result.message,
        "session_id": context.get("session_id"),
    }

def format_cart_summary(cart_items: list) -> str:
    """カート内容をフォーマットする。"""
    lines = []
    for item in cart_items:
        line = f"- {item.get('raceName', '')} {item.get('betType', '')} {item.get('horseNumbers', [])} ¥{item.get('amount', 0):,}"
        lines.append(line)
    return "\n".join(lines)

if __name__ == "__main__":
    app.run()
```

### Step 5: 依存関係の定義

#### requirements.txt

```
bedrock-agentcore
strands-agents>=0.1.0
requests>=2.31.0
```

### Step 6: ローカルテスト

```bash
cd backend/agentcore

# ローカルサーバー起動
agentcore dev

# 別ターミナルでテスト
agentcore invoke --local '{
  "prompt": "東京5Rの出走馬を教えて",
  "cart_items": []
}'
```

### Step 7: AWS へデプロイ

```bash
# 設定（初回のみ）
agentcore configure \
  --entrypoint agent.py \
  --name baken-kaigi-ai \
  --runtime PYTHON_3_12 \
  --region ap-northeast-1 \
  --non-interactive

# デプロイ
agentcore launch \
  --env JRAVAN_API_URL=https://ryzl2uhi94.execute-api.ap-northeast-1.amazonaws.com/prod

# 動作確認
agentcore invoke '{"prompt": "こんにちは"}'

# ステータス確認
agentcore status
```

## フロントエンド連携

### API クライアント更新

```typescript
// frontend/src/api/client.ts に追加

interface ConsultationRequest {
  prompt: string;
  cart_items: CartItem[];
  session_id?: string;
}

interface ConsultationResponse {
  message: string;
  session_id: string;
}

async startConsultation(request: ConsultationRequest): Promise<ApiResponse<ConsultationResponse>> {
  return this.request<ConsultationResponse>('/consultation', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}
```

### ConsultationPage 更新

```typescript
// handleQuickReply の修正
const handleQuickReply = async (reply: string) => {
  setMessages(prev => [...prev, { type: 'user', text: reply }]);
  setIsLoading(true);

  try {
    const response = await apiClient.startConsultation({
      prompt: reply,
      cart_items: items,
      session_id: sessionId,
    });

    if (response.success && response.data) {
      setMessages(prev => [...prev, { type: 'ai', text: response.data.message }]);
      setSessionId(response.data.session_id);
    }
  } catch (error) {
    setMessages(prev => [...prev, { type: 'ai', text: 'エラーが発生しました。' }]);
  } finally {
    setIsLoading(false);
  }
};
```

## 環境変数

| 変数名 | 値 | 説明 |
|--------|-----|------|
| JRAVAN_API_URL | https://ryzl2uhi94... | JRA-VAN API エンドポイント |
| AWS_REGION | ap-northeast-1 | AWS リージョン |

## テスト計画

### 単体テスト

```python
# tests/test_tools.py
def test_get_race_runners():
    result = get_race_runners("202506050811")
    assert "horse_number" in result[0]
    assert "horse_name" in result[0]

def test_analyze_bet_selection():
    runners = [{"horse_number": 1, "odds": 3.5, "popularity": 2}]
    result = analyze_bet_selection("race1", "win", [1], 100, runners)
    assert result["amount"] == 100
```

### E2E テスト

1. **相談開始**: カート内容を送信して初期分析を受け取る
2. **質問応答**: クイックリプライで追加質問
3. **データ取得**: ツール呼び出しでレースデータ取得

## 制約事項

- AgentCore は現在 **us-west-2** がデフォルト。ap-northeast-1 を明示的に指定。
- Direct Code Deploy は Python 3.10〜3.13 対応
- セッションタイムアウト: デフォルト 900 秒（15分）

## タイムライン

| フェーズ | 作業内容 | 見積もり |
|----------|----------|----------|
| Phase 1 | ツール実装 + agent.py | 2時間 |
| Phase 2 | ローカルテスト | 1時間 |
| Phase 3 | AWS デプロイ | 30分 |
| Phase 4 | フロントエンド連携 | 2時間 |
| Phase 5 | E2E テスト | 1時間 |

## 次のアクション

1. `backend/agentcore/` ディレクトリ作成
2. `tools/race_data.py` 実装
3. `tools/bet_analysis.py` 実装
4. `prompts/consultation.py` 実装
5. `agent.py` 実装
6. `requirements.txt` 作成
7. ローカルテスト
8. AWS デプロイ
