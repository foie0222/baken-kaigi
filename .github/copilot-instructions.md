# GitHub Copilot カスタムインストラクション

## プロジェクト概要

競馬予想アプリ「馬券会議」- JRA-VAN データと AI を活用した競馬予想支援アプリケーション。
ユーザーがレース情報を閲覧し、AI アドバイザーと相談しながら馬券を選択できる。

## テックスタック

### Frontend
- React 18 + TypeScript
- Vite（ビルドツール）
- Zustand（状態管理）
- Vitest + Testing Library（テスト）

### Backend
- Python 3.12
- AWS Lambda（サーバーレス）
- DynamoDB（データストア）
- Amazon Bedrock AgentCore（AI 機能）

### Infrastructure
- AWS CDK（TypeScript）
- API Gateway
- AWS Amplify（フロントエンドホスティング）

### データ連携
- JRA-VAN JV-Link（競馬データ）
- EC2 Windows Server（JV-Link 連携用）
- SQLite（ローカルデータキャッシュ）

## コーディングガイドライン

### 言語設定
- コメントは日本語で記述すること
- 変数名・関数名は英語（キャメルケース/スネークケース）
- コミットメッセージは日本語可（プレフィックスは英語: feat, fix, docs 等）

### TypeScript（Frontend）
- `strict: true` を遵守
- 型推論に頼らず、明示的な型注釈を優先
- `any` 型の使用禁止（`unknown` を使用）
- インターフェースは `I` プレフィックスなし（例: `User` not `IUser`）
- コンポーネントは関数コンポーネント + hooks を使用

### Python（Backend）
- 型ヒントを必ず付与
- docstring は Google スタイル
- f-string を優先（`%` や `.format()` より）
- 例外は具体的な型でキャッチ（`except Exception` を避ける）

### 共通ルール
- マジックナンバー禁止（定数として定義）
- 早期リターンでネストを浅く保つ
- 1 関数 1 責務（単一責任の原則）
- DRY 原則に従う（重複コードは共通化）

## アーキテクチャ

### ドメイン駆動設計（DDD）
このプロジェクトは DDD に基づいて設計されています。

```
backend/src/
├── domain/           # ドメイン層（ビジネスロジック）
│   ├── entities/     # エンティティ
│   ├── value_objects/# 値オブジェクト
│   └── ports/        # ポート（インターフェース）
├── application/      # アプリケーション層
│   └── use_cases/    # ユースケース
├── infrastructure/   # インフラ層
│   ├── repositories/ # リポジトリ実装
│   └── providers/    # 外部サービス連携
└── api/              # プレゼンテーション層
    └── handlers/     # Lambda ハンドラー
```

### 依存性の方向
- 外側の層は内側の層に依存する
- ドメイン層は他の層に依存しない
- インターフェースは `ports/` に定義し、実装は `infrastructure/` に配置

## テスト

### TDD（テスト駆動開発）
1. Red - 失敗するテストを書く
2. Green - テストが通る最小限のコードを書く
3. Refactor - コードをリファクタリングする

### テストファイル配置
- Frontend: `src/__tests__/` または `*.test.ts(x)`
- Backend: `tests/` ディレクトリ

### テスト命名規則
```python
# Python
def test_add_to_cart_should_return_success_when_valid_input():
    ...
```

```typescript
// TypeScript
describe('CartStore', () => {
  it('should add item to cart when valid', () => {
    ...
  });
});
```

## 技術的負債を避けるためのルール

### 禁止事項
- `// TODO` コメントを残さない（Issue を作成する）
- `console.log` をコミットしない（デバッグ用は削除）
- 未使用のインポート・変数を残さない
- `@ts-ignore` / `# type: ignore` を使わない
- テストなしで機能を追加しない

### 必須事項
- 新機能にはユニットテストを追加
- 型定義は厳密に（`any` 禁止）
- エラーハンドリングを適切に実装
- 関数・クラスには JSDoc/docstring を付与

### コードレビュー観点
- セキュリティ（入力検証、認証、認可）
- パフォーマンス（N+1、不要な再レンダリング）
- 可読性（命名、コメント、構造）
- テスタビリティ（依存性注入、モック可能性）

## プロジェクト構造

```
baken-kaigi/
├── frontend/           # React アプリケーション
│   ├── src/
│   │   ├── api/        # API クライアント
│   │   ├── components/ # UI コンポーネント
│   │   ├── hooks/      # カスタムフック
│   │   ├── pages/      # ページコンポーネント
│   │   ├── stores/     # Zustand ストア
│   │   ├── styles/     # CSS
│   │   └── types/      # 型定義
│   └── __tests__/      # テスト
├── backend/            # Python Lambda
│   ├── src/            # ソースコード（DDD 構造）
│   └── tests/          # テストコード
├── cdk/                # AWS CDK インフラ定義
│   └── stacks/         # CDK スタック
└── jravan-api/         # JRA-VAN 連携（EC2 用）
```

## 開発コマンド

### Frontend
```bash
cd frontend
npm run dev          # 開発サーバー起動
npm run lint         # ESLint 実行
npm run typecheck    # 型チェック
npm run test:run     # テスト実行
npm run build        # ビルド
```

### Backend
```bash
cd backend
pytest               # テスト実行
pytest --cov=src     # カバレッジ付きテスト
```

### CDK
```bash
cd cdk
npx cdk synth        # CloudFormation 生成
npx cdk deploy --all --context jravan=true  # デプロイ
```

## セキュリティガイドライン

- 環境変数で機密情報を管理（ハードコード禁止）
- IAM は最小権限の原則に従う
- 入力値は必ずバリデーション
- SQL インジェクション・XSS 対策を実施
- CORS は本番環境では制限する
