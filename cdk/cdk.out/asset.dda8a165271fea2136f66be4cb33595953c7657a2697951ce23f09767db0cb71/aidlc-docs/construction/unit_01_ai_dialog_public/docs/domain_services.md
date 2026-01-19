# ドメインサービス定義

## 概要

ドメインサービスは、特定のエンティティに自然に属さないドメインロジックを担当します。
複数の集約をまたがる操作や、外部システムとの連携が必要な操作を実装します。

---

## ドメインサービス一覧

| サービス名 | 責務 | 依存 |
|-----------|------|------|
| ConsultationService | 相談セッションの開始と管理 | Cart, ConsultationSession, FeedbackGenerator |
| FeedbackGenerator | AIを使用したフィードバック生成 | AIClient（インフラ）, RaceDataProvider（外部） |
| BetSelectionValidator | 買い目の検証 | - |
| DeadlineChecker | 投票締め切りのチェック | RaceDataProvider（外部） |

---

## ConsultationService（相談サービス）

### 責務

カートの買い目に対するAI相談セッションを開始し、フィードバックを取得する。

### 依存関係

```
ConsultationService
  ├── Cart
  ├── ConsultationSession
  ├── FeedbackGenerator
  └── DeadlineChecker
```

### 操作

#### startConsultation

```
startConsultation(cart: Cart, remainingLossLimit: Money?): ConsultationSession

入力:
  - cart: 相談対象のカート
  - remainingLossLimit: 残り許容負け額（ログイン時のみ、オプショナル）

処理:
  1. カートが空でないことを確認
  2. 各買い目の締め切りをチェック
  3. ConsultationSessionを作成し開始
  4. FeedbackGeneratorでフィードバックを生成
  5. セッションにフィードバックを設定

出力:
  - フィードバック設定済みのConsultationSession

例外:
  - CartEmptyException: カートが空の場合
  - DeadlinePassedException: 締め切り切れの買い目がある場合
```

#### continueConversation

```
continueConversation(session: ConsultationSession, userMessage: String): ConsultationSession

入力:
  - session: 現在のセッション
  - userMessage: ユーザーからの追加質問

処理:
  1. セッションがIN_PROGRESS状態であることを確認
  2. ユーザーメッセージを追加
  3. AIに送信してレスポンスを取得
  4. AIメッセージを追加

出力:
  - 更新されたConsultationSession

例外:
  - SessionNotInProgressException: セッションが進行中でない場合
```

#### endConsultation

```
endConsultation(session: ConsultationSession): ConsultationSession

入力:
  - session: 終了するセッション

処理:
  1. セッションを終了状態に遷移

出力:
  - 終了したConsultationSession
```

---

## FeedbackGenerator（フィードバック生成サービス）

### 責務

AIを使用して、買い目に対するデータフィードバックと掛け金フィードバックを生成する。

### 依存関係

```
FeedbackGenerator
  ├── AIClient（インフラ）
  └── RaceDataProvider（外部）
```

### 操作

#### generateDataFeedbacks

```
generateDataFeedbacks(cartItems: List<CartItem>): List<DataFeedback>

入力:
  - cartItems: フィードバック対象の買い目リスト

処理:
  1. 各買い目のレースIDから外部レースデータを取得
  2. 馬の過去成績、騎手成績、馬場適性を取得
  3. AIにデータを渡してフィードバック文を生成
  4. DataFeedbackオブジェクトを構築

出力:
  - 各買い目に対するDataFeedbackのリスト
```

#### generateAmountFeedback

```
generateAmountFeedback(
  totalAmount: Money,
  remainingLossLimit: Money?,
  averageAmount: Money?
): AmountFeedback

入力:
  - totalAmount: 合計掛け金
  - remainingLossLimit: 残り許容負け額（オプショナル）
  - averageAmount: 過去の平均掛け金（オプショナル）

処理:
  1. 限度額超過をチェック
  2. 警告レベルを判定（NONE/CAUTION/WARNING）
  3. AIにコンテキストを渡してフィードバック文を生成
  4. AmountFeedbackオブジェクトを構築

出力:
  - AmountFeedback

警告レベル判定:
  - NONE: 限度額の80%未満
  - CAUTION: 限度額の80%以上100%未満
  - WARNING: 限度額超過
```

---

## BetSelectionValidator（買い目検証サービス）

### 責務

買い目が有効かどうかを検証する。

### 操作

#### validate

```
validate(betSelection: BetSelection): ValidationResult

入力:
  - betSelection: 検証対象の買い目

処理:
  1. 券種が有効か確認
  2. 選択馬番の数が券種の要件を満たすか確認
  3. 各馬番が有効範囲（1-18）内か確認
  4. 金額が有効（100円以上、100円単位）か確認

出力:
  - ValidationResult（valid: Boolean, errors: List<String>）
```

#### validateForRace

```
validateForRace(betSelection: BetSelection, raceRef: RaceReference): ValidationResult

入力:
  - betSelection: 検証対象の買い目
  - raceRef: 対象レースの参照

処理:
  1. 基本検証を実行
  2. 選択馬番がレースの出走馬に含まれるか確認
  3. レースの締め切り前か確認

出力:
  - ValidationResult
```

---

## DeadlineChecker（締め切りチェックサービス）

### 責務

レースの投票締め切りをチェックする。

### 依存関係

```
DeadlineChecker
  └── RaceDataProvider（外部）
```

### 操作

#### isBeforeDeadline

```
isBeforeDeadline(raceId: RaceId): Boolean

入力:
  - raceId: チェック対象のレースID

処理:
  1. レースの締め切り時刻を取得
  2. 現在時刻と比較

出力:
  - 締め切り前ならtrue
```

#### getRemainingTime

```
getRemainingTime(raceId: RaceId): Duration?

入力:
  - raceId: チェック対象のレースID

処理:
  1. レースの締め切り時刻を取得
  2. 現在時刻との差分を計算

出力:
  - 残り時間（締め切り後はnull）
```

#### checkCartDeadlines

```
checkCartDeadlines(cart: Cart): DeadlineCheckResult

入力:
  - cart: チェック対象のカート

処理:
  1. カート内の全アイテムの締め切りをチェック
  2. 締め切り切れのアイテムを特定

出力:
  - DeadlineCheckResult
    - allValid: Boolean（全て締め切り前か）
    - expiredItems: List<ItemId>（締め切り切れアイテム）
    - nearestDeadline: DateTime?（最も近い締め切り）
```

---

## 外部インターフェース（ポート）

### AIClient（インフラ層で実装）

```
interface AIClient {
  // 買い目データに基づくフィードバック文を生成
  generateBetFeedback(context: BetFeedbackContext): String

  // 掛け金に関するフィードバック文を生成
  generateAmountFeedback(context: AmountFeedbackContext): String

  // 自由会話の応答を生成
  generateConversationResponse(
    messages: List<Message>,
    context: ConsultationContext
  ): String
}
```

### RaceDataProvider（外部システム）

```
interface RaceDataProvider {
  // レース情報を取得
  getRace(raceId: RaceId): RaceData?

  // 出走馬情報を取得
  getRunners(raceId: RaceId): List<RunnerData>

  // 馬の過去成績を取得
  getPastPerformance(horseId: HorseId): List<PerformanceData>

  // 騎手のコース成績を取得
  getJockeyStats(jockeyId: JockeyId, course: String): JockeyStatsData
}
```

---

## サービス間の協調

### 相談開始フロー

```
ConsultationService.startConsultation(cart, remainingLimit)
    │
    ├── DeadlineChecker.checkCartDeadlines(cart)
    │       └── RaceDataProvider.getRace(raceId) [各アイテム]
    │
    ├── ConsultationSession.create() & start()
    │
    ├── FeedbackGenerator.generateDataFeedbacks(cartItems)
    │       ├── RaceDataProvider.getRunners(raceId)
    │       ├── RaceDataProvider.getPastPerformance(horseId)
    │       └── AIClient.generateBetFeedback(context)
    │
    └── FeedbackGenerator.generateAmountFeedback(total, limit, avg)
            └── AIClient.generateAmountFeedback(context)
```
