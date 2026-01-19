# エンティティ定義

## 概要

エンティティは、ライフサイクルを持ち、識別子（ID）によって一意に識別されるドメインオブジェクトです。

---

## エンティティ一覧

| エンティティ | 説明 | 集約ルート |
|-------------|------|-----------|
| Cart | 買い目を一時保持するカート | ○ |
| CartItem | カート内の個々のアイテム | - |
| ConsultationSession | AIとの相談セッション | ○ |
| Message | 相談セッション内のメッセージ | - |

---

## Cart（カート）

### 説明
ユーザーが購入を検討する複数の買い目を一時的に保持するコンテナ。

### 識別子
- `cartId: CartId` - カートの一意識別子（セッションベースまたはユーザー紐付け）

### 属性

| 属性名 | 型 | 説明 |
|-------|-----|------|
| cartId | CartId | カートの一意識別子 |
| userId | UserId? | 紐付けられたユーザーID（オプショナル、ログイン時） |
| items | List&lt;CartItem&gt; | カート内のアイテムリスト |
| createdAt | DateTime | カート作成日時 |
| updatedAt | DateTime | 最終更新日時 |

### 振る舞い

| メソッド | 説明 | 事前条件 | 事後条件 |
|---------|------|---------|---------|
| addItem(betSelection) | 買い目をカートに追加 | betSelectionが有効 | itemsに追加、updatedAt更新 |
| removeItem(itemId) | 指定アイテムを削除 | itemIdが存在 | itemsから削除、updatedAt更新 |
| clear() | 全アイテムを削除 | - | itemsが空、updatedAt更新 |
| getTotalAmount() | 合計金額を計算 | - | 全アイテムの金額合計を返す |
| getItemCount() | アイテム数を取得 | - | items.sizeを返す |
| isEmpty() | カートが空か判定 | - | items.isEmpty()を返す |
| associateUser(userId) | ユーザーを紐付け | userIdがnull | userIdが設定される |

### ビジネスルール

1. **同一買い目の重複**: 同じレース・券種・馬番の組み合わせは追加可能（金額が異なる場合がある）
2. **カートの有効期限**: セッション終了またはブラウザクローズで破棄（認証不要のため）
3. **最大アイテム数**: 制限なし（UIで推奨上限を表示する可能性あり）

---

## CartItem（カートアイテム）

### 説明
カートに追加された個々の買い目。Cart集約内でのみ意味を持つ。

### 識別子
- `itemId: ItemId` - カート内でのローカル識別子

### 属性

| 属性名 | 型 | 説明 |
|-------|-----|------|
| itemId | ItemId | アイテムのローカル識別子 |
| raceId | RaceId | 対象レースのID（外部参照） |
| raceName | String | レース名（表示用キャッシュ） |
| betSelection | BetSelection | 買い目の詳細（値オブジェクト） |
| addedAt | DateTime | カートへの追加日時 |

### 振る舞い

| メソッド | 説明 |
|---------|------|
| getAmount() | 買い目の金額を取得 |
| getBetType() | 券種を取得 |
| getSelectedNumbers() | 選択馬番を取得 |

### ビジネスルール

1. **不変性**: 追加後は編集不可（編集したい場合は削除→再追加）
2. **レース情報のキャッシュ**: raceNameは表示用にキャッシュし、詳細はraceIdで外部参照

---

## ConsultationSession（相談セッション）

### 説明
ユーザーがAIに買い目について相談する一連のやり取りをカプセル化したセッション。

### 識別子
- `sessionId: SessionId` - セッションの一意識別子

### 属性

| 属性名 | 型 | 説明 |
|-------|-----|------|
| sessionId | SessionId | セッションの一意識別子 |
| userId | UserId? | 紐付けられたユーザーID（オプショナル） |
| cartSnapshot | List&lt;CartItem&gt; | 相談開始時のカートのスナップショット |
| messages | List&lt;Message&gt; | 会話メッセージのリスト |
| dataFeedbacks | List&lt;DataFeedback&gt; | 各買い目へのデータフィードバック |
| amountFeedback | AmountFeedback? | 掛け金フィードバック |
| status | SessionStatus | セッションの状態 |
| startedAt | DateTime | セッション開始日時 |
| endedAt | DateTime? | セッション終了日時 |

### 振る舞い

| メソッド | 説明 | 事前条件 | 事後条件 |
|---------|------|---------|---------|
| start(cartItems) | セッションを開始 | statusがNOT_STARTED | cartSnapshotが設定、statusがIN_PROGRESS |
| addMessage(message) | メッセージを追加 | statusがIN_PROGRESS | messagesに追加 |
| setDataFeedbacks(feedbacks) | データフィードバックを設定 | statusがIN_PROGRESS | dataFeedbacksが設定 |
| setAmountFeedback(feedback) | 掛け金フィードバックを設定 | statusがIN_PROGRESS | amountFeedbackが設定 |
| end() | セッションを終了 | statusがIN_PROGRESS | statusがCOMPLETED、endedAt設定 |
| getTotalAmount() | 合計掛け金を取得 | - | cartSnapshotの合計金額 |
| isLimitExceeded(remainingLimit) | 限度額超過判定 | - | 合計金額 > remainingLimit |

### ビジネスルール

1. **スナップショット**: 相談開始時のカート状態を保存（相談中のカート変更は反映しない）
2. **セッション状態遷移**: NOT_STARTED → IN_PROGRESS → COMPLETED
3. **Unit 1での永続化**: 認証不要のため、セッションは永続化しない（Unit 2で履歴保存）

---

## Message（メッセージ）

### 説明
相談セッション内の個々の発言。ConsultationSession集約内でのみ意味を持つ。

### 識別子
- `messageId: MessageId` - セッション内でのローカル識別子

### 属性

| 属性名 | 型 | 説明 |
|-------|-----|------|
| messageId | MessageId | メッセージのローカル識別子 |
| type | MessageType | メッセージ種別（USER/AI/SYSTEM） |
| content | String | メッセージ内容 |
| timestamp | DateTime | 送信日時 |

### 振る舞い

| メソッド | 説明 |
|---------|------|
| isFromUser() | ユーザーからのメッセージか判定 |
| isFromAI() | AIからのメッセージか判定 |
| isSystem() | システムメッセージか判定 |

### ビジネスルール

1. **不変性**: 一度作成されたメッセージは変更不可
2. **順序性**: timestampによって時系列順に管理

---

## セッション状態（SessionStatus）

| 状態 | 説明 |
|------|------|
| NOT_STARTED | 未開始 |
| IN_PROGRESS | 相談中 |
| COMPLETED | 完了 |

---

## 状態遷移図

### Cart

```
Empty ---[addItem()]--> HasItems
HasItems ---[addItem()]--> HasItems
HasItems ---[removeItem()]--> HasItems or Empty
HasItems ---[clear()]--> Empty
```

### ConsultationSession

```
NOT_STARTED ---[start()]--> IN_PROGRESS
IN_PROGRESS ---[addMessage()]--> IN_PROGRESS
IN_PROGRESS ---[setDataFeedbacks()]--> IN_PROGRESS
IN_PROGRESS ---[setAmountFeedback()]--> IN_PROGRESS
IN_PROGRESS ---[end()]--> COMPLETED
```
