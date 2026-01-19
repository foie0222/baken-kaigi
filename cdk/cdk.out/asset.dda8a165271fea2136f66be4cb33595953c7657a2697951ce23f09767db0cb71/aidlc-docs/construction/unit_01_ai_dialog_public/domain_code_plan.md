# ドメインモデル実装計画

## 前提条件の質問

### [Question] 1. 実装言語
ドメインモデルを実装する言語を教えてください（例：TypeScript, Python, Java, Kotlin, C# など）。

[Answer] Python


### [Question] 2. 出力ディレクトリ
生成したコードを配置するディレクトリのパスを教えてください。

[Answer] ソースコードはsrc以下 テストコードは tests 以下 でどうかな？あとcdkでデプロイしてほしいんだけど、それはどこに配置すべき？


### [Question] 3. 日付・時間ライブラリ
DateTime や Duration の表現に使用するライブラリはありますか？（例：TypeScript の場合 Date / dayjs / date-fns、Python の場合 datetime / pendulum など）

[Answer] 指定なし → Python 標準の datetime モジュールを使用


### [Question] 4. CDK の配置とスコープ
CDK は一般的に以下のいずれかに配置します：
- `cdk/` ディレクトリ（推奨）
- `infra/` ディレクトリ

また、CDK でデプロイする対象について確認させてください。今回のドメインモデルは純粋な Python コードです。

a) Lambda + API Gateway でサーバーレス API として公開する
b) ECS/Fargate でコンテナとしてデプロイする
c) CDK の構成だけ先に作成しておき、後でアプリケーション層を追加する
d) その他

[Answer] a


---

## 実装ステップ

### フェーズ 1: 基盤（識別子型・列挙型）

- [x] **Step 1.1**: CartId - カート識別子の値オブジェクト
- [x] **Step 1.2**: ItemId - カートアイテム識別子の値オブジェクト
- [x] **Step 1.3**: SessionId - セッション識別子の値オブジェクト
- [x] **Step 1.4**: MessageId - メッセージ識別子の値オブジェクト
- [x] **Step 1.5**: RaceId - レース識別子の値オブジェクト（外部参照用）
- [x] **Step 1.6**: UserId - ユーザー識別子の値オブジェクト（外部参照用）
- [x] **Step 1.7**: BetType - 券種の列挙型（WIN, PLACE, QUINELLA, QUINELLA_PLACE, EXACTA, TRIO, TRIFECTA）
- [x] **Step 1.8**: MessageType - メッセージ種別の列挙型（USER, AI, SYSTEM）
- [x] **Step 1.9**: SessionStatus - セッション状態の列挙型（NOT_STARTED, IN_PROGRESS, COMPLETED）
- [x] **Step 1.10**: WarningLevel - 警告レベルの列挙型（NONE, CAUTION, WARNING）

### フェーズ 2: コアビジネス値オブジェクト

- [x] **Step 2.1**: Money - 金額を表現する値オブジェクト（加算、減算、比較、フォーマット機能）
- [x] **Step 2.2**: HorseNumbers - 選択馬番のコレクション（バリデーション付き）
- [x] **Step 2.3**: BetSelection - 買い目を表現する値オブジェクト（券種、馬番、金額）
- [x] **Step 2.4**: RaceReference - レースへの参照情報（ID、名称、開催場、発走時刻、締め切り）

### フェーズ 3: フィードバック値オブジェクト

- [x] **Step 3.1**: HorseDataSummary - 馬のデータ要約
- [x] **Step 3.2**: DataFeedback - データに基づくフィードバック
- [x] **Step 3.3**: AmountFeedback - 掛け金フィードバック

### フェーズ 4: エンティティ

- [x] **Step 4.1**: CartItem - カート内アイテムエンティティ
- [x] **Step 4.2**: Message - メッセージエンティティ
- [x] **Step 4.3**: Cart - カート集約ルート（addItem, removeItem, clear, getTotalAmount など）
- [x] **Step 4.4**: ConsultationSession - 相談セッション集約ルート（start, addMessage, setFeedbacks, end など）

### フェーズ 5: ポート（インターフェース）

- [ ] **Step 5.1**: AIClient - AI呼び出しインターフェース
- [ ] **Step 5.2**: RaceDataProvider - レースデータ取得インターフェース

### フェーズ 6: リポジトリ

- [ ] **Step 6.1**: CartRepository - カートリポジトリインターフェース
- [ ] **Step 6.2**: InMemoryCartRepository - インメモリ実装
- [ ] **Step 6.3**: ConsultationSessionRepository - セッションリポジトリインターフェース
- [ ] **Step 6.4**: InMemoryConsultationSessionRepository - インメモリ実装

### フェーズ 7: ドメインサービス

- [ ] **Step 7.1**: BetSelectionValidator - 買い目検証サービス
- [ ] **Step 7.2**: DeadlineChecker - 締め切りチェックサービス
- [ ] **Step 7.3**: FeedbackGenerator - フィードバック生成サービス
- [ ] **Step 7.4**: ConsultationService - 相談サービス

### フェーズ 8: プロジェクト設定

- [ ] **Step 8.1**: pyproject.toml - プロジェクト設定ファイル
- [ ] **Step 8.2**: src/__init__.py - パッケージ初期化
- [ ] **Step 8.3**: tests/__init__.py - テストパッケージ初期化

---

## 実装ファイル一覧（予定）

フラットな構造で、各クラスを個別ファイルに配置：

```
aidlc-docs/construction/unit_01_ai_dialog_public/
├── src/
│   ├── __init__.py
│   ├── cart_id.py
│   ├── item_id.py
│   ├── session_id.py
│   ├── message_id.py
│   ├── race_id.py
│   ├── user_id.py
│   ├── bet_type.py
│   ├── message_type.py
│   ├── session_status.py
│   ├── warning_level.py
│   ├── money.py
│   ├── horse_numbers.py
│   ├── bet_selection.py
│   ├── race_reference.py
│   ├── horse_data_summary.py
│   ├── data_feedback.py
│   ├── amount_feedback.py
│   ├── cart_item.py
│   ├── message.py
│   ├── cart.py
│   ├── consultation_session.py
│   ├── ai_client.py
│   ├── race_data_provider.py
│   ├── cart_repository.py
│   ├── in_memory_cart_repository.py
│   ├── consultation_session_repository.py
│   ├── in_memory_consultation_session_repository.py
│   ├── bet_selection_validator.py
│   ├── deadline_checker.py
│   ├── feedback_generator.py
│   └── consultation_service.py
├── tests/
│   └── __init__.py
└── pyproject.toml
```

---

## 決定事項まとめ

| 項目 | 決定内容 |
|------|----------|
| 実装言語 | Python |
| ソースコード | src/ |
| テストコード | tests/ |
| 日付・時間 | Python 標準 datetime |

---

## 後続タスク（今回のスコープ外）

- アプリケーション層（ユースケース）
- API エンドポイント（Lambda ハンドラー）
- CDK（Lambda + API Gateway）
- フロントエンド

---

## 備考

- 各クラスは不変性の原則に従う（値オブジェクト）→ Python では `@dataclass(frozen=True)` を使用
- ログには Python 標準の `logging` モジュールを使用
- リポジトリはインメモリ実装として `dict` を使用
- 外部参照（Race, User など）は ID のみで参照し、詳細は RaceDataProvider 経由で取得
- ファイル名は Python の命名規則に従い snake_case を使用
