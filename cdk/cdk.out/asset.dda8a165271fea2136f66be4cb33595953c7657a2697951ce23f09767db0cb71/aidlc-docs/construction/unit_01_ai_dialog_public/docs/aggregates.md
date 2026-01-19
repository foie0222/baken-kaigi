# 集約定義

## 概要

集約は、トランザクション境界を定義し、データの一貫性を保証する単位です。集約ルートを通じてのみ集約内のオブジェクトにアクセスできます。

---

## 集約一覧

| 集約名 | 集約ルート | 内部エンティティ | 主要値オブジェクト |
|-------|-----------|----------------|------------------|
| Cart | Cart | CartItem | BetSelection, Money, RaceReference |
| ConsultationSession | ConsultationSession | Message | DataFeedback, AmountFeedback |

---

## Cart集約

### 概要

ユーザーが購入を検討する買い目を管理するカート。

```
Cart集約
├── Cart（集約ルート）
│   └── CartItem（0..*）
│       ├── BetSelection（値オブジェクト）
│       │   ├── BetType
│       │   ├── HorseNumbers
│       │   └── Money
│       └── RaceReference（値オブジェクト）
```

### 集約ルート: Cart

#### 不変条件（Invariants）

1. **CartItemの一意性**: 同じitemIdを持つCartItemは存在しない
2. **合計金額の整合性**: getTotalAmount()は全CartItemの金額合計と一致
3. **アイテム数の整合性**: getItemCount()はitemsのサイズと一致

#### 外部への公開

| 公開メソッド | 戻り値 | 説明 |
|------------|--------|------|
| getCartId() | CartId | カートIDを取得 |
| getUserId() | UserId? | 紐付けユーザーIDを取得 |
| getItems() | List&lt;CartItemSnapshot&gt; | アイテムのスナップショットを取得（防御的コピー） |
| getTotalAmount() | Money | 合計金額を取得 |
| getItemCount() | Integer | アイテム数を取得 |
| isEmpty() | Boolean | カートが空か判定 |

#### 操作（Commands）

| 操作 | 引数 | 説明 | 発行イベント |
|-----|------|------|-------------|
| addItem | raceRef, betSelection | 買い目を追加 | CartItemAdded |
| removeItem | itemId | アイテムを削除 | CartItemRemoved |
| clear | - | 全アイテムを削除 | CartCleared |
| associateUser | userId | ユーザーを紐付け | UserAssociated |

### 集約内エンティティ: CartItem

CartItemはCart集約内でのみ意味を持つエンティティです。

#### アクセス制御

- **作成**: Cartのadditem()経由でのみ作成
- **削除**: CartのremoveItem()経由でのみ削除
- **参照**: CartのgetItems()で読み取り専用スナップショットとして公開

---

## ConsultationSession集約

### 概要

AIとの相談セッションと会話履歴を管理する。

```
ConsultationSession集約
├── ConsultationSession（集約ルート）
│   ├── Message（0..*）
│   ├── CartItemSnapshot（1..*）
│   ├── DataFeedback（0..*、値オブジェクト）
│   └── AmountFeedback（0..1、値オブジェクト）
```

### 集約ルート: ConsultationSession

#### 不変条件（Invariants）

1. **状態遷移の整合性**: NOT_STARTED → IN_PROGRESS → COMPLETED の順序でのみ遷移
2. **メッセージの時系列**: messagesはtimestamp順に並ぶ
3. **フィードバックの対応**: dataFeedbacksの各要素はcartSnapshotのアイテムに対応
4. **操作の状態依存**: IN_PROGRESS状態でのみメッセージ追加・フィードバック設定が可能

#### 外部への公開

| 公開メソッド | 戻り値 | 説明 |
|------------|--------|------|
| getSessionId() | SessionId | セッションIDを取得 |
| getStatus() | SessionStatus | 現在の状態を取得 |
| getCartSnapshot() | List&lt;CartItemSnapshot&gt; | 相談対象の買い目を取得 |
| getMessages() | List&lt;MessageSnapshot&gt; | 会話履歴を取得 |
| getDataFeedbacks() | List&lt;DataFeedback&gt; | データフィードバックを取得 |
| getAmountFeedback() | AmountFeedback? | 掛け金フィードバックを取得 |
| getTotalAmount() | Money | 合計掛け金を取得 |
| isLimitExceeded(limit) | Boolean | 限度額超過判定 |

#### 操作（Commands）

| 操作 | 引数 | 説明 | 発行イベント |
|-----|------|------|-------------|
| start | cartItems | セッションを開始 | SessionStarted |
| addUserMessage | content | ユーザーメッセージを追加 | UserMessageAdded |
| addAIMessage | content | AIメッセージを追加 | AIMessageAdded |
| addSystemMessage | content | システムメッセージを追加 | SystemMessageAdded |
| setDataFeedbacks | feedbacks | データフィードバックを設定 | DataFeedbacksSet |
| setAmountFeedback | feedback | 掛け金フィードバックを設定 | AmountFeedbackSet |
| end | - | セッションを終了 | SessionEnded |

### 集約内エンティティ: Message

MessageはConsultationSession集約内でのみ意味を持つエンティティです。

#### アクセス制御

- **作成**: ConsultationSessionのaddXxxMessage()経由でのみ作成
- **参照**: getMessages()で読み取り専用スナップショットとして公開

---

## 集約間の関係

```
Cart ---[スナップショットコピー]--> ConsultationSession

Cart ---[RaceId参照]--> 外部リードモデル（Race, Runner, etc.）
ConsultationSession ---[RaceId参照]--> 外部リードモデル
```

### 関係の説明

1. **CartからConsultationSessionへのコピー**
   - 相談開始時に、CartのアイテムをConsultationSessionにスナップショットとしてコピー
   - コピー後はConsultationSession内のデータとして独立
   - 相談中にCartが変更されても、ConsultationSessionには影響しない

2. **外部リードモデルへの参照**
   - RaceIdを通じて外部のレース情報を参照
   - 表示用の基本情報（レース名など）はRaceReferenceとしてキャッシュ

---

## トランザクション境界

### Cart集約のトランザクション

| 操作 | トランザクション範囲 | 備考 |
|-----|-------------------|------|
| addItem | Cart集約のみ | 他の集約に影響しない |
| removeItem | Cart集約のみ | 他の集約に影響しない |
| clear | Cart集約のみ | 他の集約に影響しない |

### ConsultationSession集約のトランザクション

| 操作 | トランザクション範囲 | 備考 |
|-----|-------------------|------|
| start | ConsultationSession集約のみ | CartからのコピーはCartを変更しない |
| addMessage | ConsultationSession集約のみ | |
| setFeedbacks | ConsultationSession集約のみ | |
| end | ConsultationSession集約のみ | |

---

## 整合性の保証

### 即時整合性（Strong Consistency）

集約内の整合性は即時に保証される：
- Cart内のitems変更とtotalAmountの計算
- ConsultationSession内のmessages追加とstatus管理

### 結果整合性（Eventual Consistency）

集約間の整合性は結果整合性で対応：
- CartからConsultationSessionへのスナップショットコピー後、Cartが変更されてもConsultationSessionは影響を受けない（設計意図）
