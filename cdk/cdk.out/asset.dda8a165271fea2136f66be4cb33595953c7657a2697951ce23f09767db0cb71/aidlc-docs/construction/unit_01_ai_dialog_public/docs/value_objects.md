# 値オブジェクト定義

## 概要

値オブジェクトは、不変（Immutable）であり、識別子を持たず、属性の値によって等価性が判断されるドメインオブジェクトです。

---

## 値オブジェクト一覧

| カテゴリ | 値オブジェクト | 説明 |
|---------|--------------|------|
| 識別子 | CartId, ItemId, SessionId, MessageId | エンティティの識別子 |
| 識別子 | RaceId, UserId | 外部参照用識別子 |
| コア | BetSelection | 買い目の詳細 |
| コア | Money | 金額 |
| コア | HorseNumbers | 選択馬番のコレクション |
| 列挙 | BetType | 券種 |
| 列挙 | MessageType | メッセージ種別 |
| 列挙 | SessionStatus | セッション状態 |
| フィードバック | DataFeedback | データに基づくフィードバック |
| フィードバック | AmountFeedback | 掛け金フィードバック |
| フィードバック | HorseDataSummary | 馬のデータ要約 |
| 参照 | RaceReference | レースへの参照情報 |

---

## 識別子型

### CartId

```
CartId {
    value: String  // UUID形式
}
```

### ItemId

```
ItemId {
    value: String  // カート内ローカルID
}
```

### SessionId

```
SessionId {
    value: String  // UUID形式
}
```

### MessageId

```
MessageId {
    value: String  // セッション内ローカルID
}
```

### RaceId

```
RaceId {
    value: String  // 外部システムのレースID
}
```

### UserId

```
UserId {
    value: String  // ユーザーシステムのID
}
```

---

## コアビジネス値オブジェクト

### BetSelection（買い目）

ユーザーが入力した馬券の買い目を表現する。

#### 属性

| 属性名 | 型 | 説明 | 制約 |
|-------|-----|------|------|
| betType | BetType | 券種 | 必須 |
| horseNumbers | HorseNumbers | 選択した馬番 | 券種に応じた頭数 |
| amount | Money | 掛け金額 | 100円以上 |

#### 振る舞い

| メソッド | 説明 |
|---------|------|
| isValid() | 買い目が有効か検証（券種に対して正しい頭数が選択されているか） |
| getRequiredCount() | 券種に必要な選択頭数を取得 |
| equals(other) | 値による等価性判定 |

#### ファクトリメソッド

| メソッド | 説明 |
|---------|------|
| create(betType, horseNumbers, amount) | バリデーション付きで生成 |

#### バリデーションルール

1. betTypeが有効な券種であること
2. horseNumbersの数が券種の要件を満たすこと
3. amountが100円以上であること
4. amountが100円単位であること

---

### Money（金額）

金額を表現する。

#### 属性

| 属性名 | 型 | 説明 | 制約 |
|-------|-----|------|------|
| value | Integer | 金額（円） | 0以上 |

#### 振る舞い

| メソッド | 説明 |
|---------|------|
| add(other) | 金額を加算して新しいMoneyを返す |
| subtract(other) | 金額を減算して新しいMoneyを返す |
| multiply(factor) | 金額を乗算して新しいMoneyを返す |
| isGreaterThan(other) | 比較 |
| isLessThanOrEqual(other) | 比較 |
| format() | 表示用フォーマット（例: "¥1,000"） |

#### ファクトリメソッド

| メソッド | 説明 |
|---------|------|
| of(value) | 指定金額で生成 |
| zero() | ゼロ円を生成 |
| fromPreset(preset) | プリセット値から生成（100, 500, 1000, 5000） |

---

### HorseNumbers（馬番コレクション）

選択された馬番のコレクションを表現する。

#### 属性

| 属性名 | 型 | 説明 | 制約 |
|-------|-----|------|------|
| numbers | List&lt;Integer&gt; | 馬番リスト | 1〜18、重複なし |

#### 振る舞い

| メソッド | 説明 |
|---------|------|
| count() | 選択された馬番の数 |
| contains(number) | 指定馬番が含まれるか |
| toList() | リストとして取得 |
| toDisplayString() | 表示用文字列（例: "3-5-8"） |

#### ファクトリメソッド

| メソッド | 説明 |
|---------|------|
| of(numbers...) | 可変長引数で生成 |
| fromList(list) | リストから生成 |

#### バリデーションルール

1. 各馬番が1〜18の範囲内
2. 重複する馬番がないこと

---

## 列挙型

### BetType（券種）

| 値 | 表示名 | 必要頭数 | 説明 |
|----|--------|---------|------|
| WIN | 単勝 | 1 | 1着を当てる |
| PLACE | 複勝 | 1 | 3着以内を当てる |
| QUINELLA | 馬連 | 2 | 1-2着を当てる（順不同） |
| QUINELLA_PLACE | ワイド | 2 | 3着以内の2頭を当てる（順不同） |
| EXACTA | 馬単 | 2 | 1-2着を当てる（順序あり） |
| TRIO | 三連複 | 3 | 1-3着を当てる（順不同） |
| TRIFECTA | 三連単 | 3 | 1-3着を当てる（順序あり） |

#### 振る舞い

| メソッド | 説明 |
|---------|------|
| getRequiredCount() | 必要な選択頭数を返す |
| getDisplayName() | 日本語表示名を返す |
| isOrderRequired() | 順序が必要か（馬単、三連単） |

---

### MessageType（メッセージ種別）

| 値 | 説明 |
|----|------|
| USER | ユーザーからの入力 |
| AI | AIからの応答 |
| SYSTEM | システムからの通知 |

---

### SessionStatus（セッション状態）

| 値 | 説明 |
|----|------|
| NOT_STARTED | 未開始 |
| IN_PROGRESS | 進行中 |
| COMPLETED | 完了 |

---

## フィードバック値オブジェクト

### DataFeedback（データフィードバック）

選択した馬に関するデータに基づくフィードバック。

#### 属性

| 属性名 | 型 | 説明 |
|-------|-----|------|
| cartItemId | ItemId | 対象カートアイテムのID |
| horseSummaries | List&lt;HorseDataSummary&gt; | 各馬のデータ要約 |
| overallComment | String | 全体的なコメント |
| generatedAt | DateTime | 生成日時 |

---

### HorseDataSummary（馬のデータ要約）

個々の馬に関するデータ要約。

#### 属性

| 属性名 | 型 | 説明 |
|-------|-----|------|
| horseNumber | Integer | 馬番 |
| horseName | String | 馬名 |
| recentResults | String | 過去5走の成績要約 |
| jockeyStats | String | 騎手の当該コース成績 |
| trackSuitability | String | 馬場適性コメント |
| currentOdds | String | 現在のオッズ |
| popularity | Integer | 人気順 |

---

### AmountFeedback（掛け金フィードバック）

掛け金額に対するフィードバック。

#### 属性

| 属性名 | 型 | 説明 |
|-------|-----|------|
| totalAmount | Money | 合計掛け金 |
| remainingLossLimit | Money? | 残り許容負け額（ログイン時のみ） |
| averageAmount | Money? | 過去の平均掛け金（ログイン時のみ） |
| isLimitExceeded | Boolean | 限度額超過フラグ |
| warningLevel | WarningLevel | 警告レベル |
| comment | String | フィードバックコメント |
| generatedAt | DateTime | 生成日時 |

#### WarningLevel（警告レベル）

| 値 | 説明 |
|----|------|
| NONE | 警告なし |
| CAUTION | 注意（80%接近） |
| WARNING | 警告（超過） |

---

## 参照値オブジェクト

### RaceReference（レース参照）

外部のレース情報への参照。表示用の基本情報をキャッシュとして保持。

#### 属性

| 属性名 | 型 | 説明 |
|-------|-----|------|
| raceId | RaceId | レースID |
| raceName | String | レース名 |
| raceNumber | Integer | レース番号 |
| venue | String | 開催場 |
| startTime | DateTime | 発走時刻 |
| bettingDeadline | DateTime | 投票締め切り |

#### 振る舞い

| メソッド | 説明 |
|---------|------|
| isBeforeDeadline(now) | 締め切り前かどうか |
| getRemainingTime(now) | 締め切りまでの残り時間 |
| toDisplayString() | 表示用文字列（例: "東京11R 日本ダービー"） |

---

## 不変性の保証

全ての値オブジェクトは以下の原則に従う：

1. **コンストラクタでの完全な初期化**: 全属性をコンストラクタで設定
2. **セッターなし**: 属性変更用のメソッドを持たない
3. **変更は新インスタンス生成**: 変更が必要な場合は新しいインスタンスを返す
4. **深い不変性**: コレクション属性も不変コレクションとして保持
