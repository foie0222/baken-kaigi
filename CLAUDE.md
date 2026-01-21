# CLAUDE.md

## 概要

開発を進めるうえで遵守すべき標準ルールを定義します。

## プロジェクト構造

```
baken-kaigi/
├── frontend/           # React + TypeScript + Vite（フロントエンド）
├── backend/            # Python バックエンド
│   ├── src/            # ソースコード
│   ├── tests/          # テストコード
│   └── agentcore/      # AgentCore 関連
├── cdk/                # AWS CDK インフラ定義
│   ├── stacks/         # CDK スタック
│   └── lambda_layer/   # Lambda レイヤー
├── jravan-api/         # JRA-VAN API 関連（EC2デプロイ用）
└── aidlc-docs/         # AIDLC ドキュメント
    ├── inception/      # インセプションフェーズ
    └── construction/   # コンストラクションフェーズ
```

## 開発プロセス

### ドメイン駆動設計（DDD）

AI-DLC（AI-Driven Life Cycle）に基づき、ドメイン駆動設計で開発を進めます。
ドメインモデルのドキュメントは `aidlc-docs/` 内で管理しています。

- **ユビキタス言語** - `ubiquitous_language.md` を参照
- **エンティティ** - `entities.md` を参照
- **値オブジェクト** - `value_objects.md` を参照
- **集約** - `aggregates.md` を参照
- **ドメインサービス** - `domain_services.md` を参照

### テスト駆動開発（TDD）

コーディングを行う際はテスト駆動で開発すること。

1. **Red** - 失敗するテストを書く
2. **Green** - テストが通る最小限のコードを書く
3. **Refactor** - コードをリファクタリングする

### コミット前の確認事項

- `npm run lint` でリントエラーがないこと
- `npm run typecheck` で型エラーがないこと
- `npm test` でテストが通ること
- `npm run build` でビルドが成功すること

## AWS 操作

### 認証

AWS の認証情報が必要な場合は `aws login` コマンドで要求すること。

```bash
aws login
```

### EC2 サーバー操作

バックエンドの EC2 サーバーは AWS SSM 経由で操作します。

```bash
# インスタンスID確認
aws ec2 describe-instances --filters "Name=tag:Name,Values=*jravan*" --query 'Reservations[].Instances[].InstanceId' --output text

# SSM経由でコマンド実行
aws ssm send-command \
  --instance-ids "<instance-id>" \
  --document-name "AWS-RunPowerShellScript" \
  --parameters 'commands=["cd C:\\jravan-api; python script.py"]'
```

### API エンドポイント確認

```bash
# API Gateway エンドポイント確認
aws apigateway get-rest-apis --query 'items[?name==`baken-kaigi`].id' --output text
```

## Git 管理

### コミットメッセージ

プレフィックスを付けて、変更内容を明確に記載する。

| プレフィックス | 用途 |
|--------------|------|
| `feat` | 新機能追加 |
| `fix` | バグ修正 |
| `docs` | ドキュメント修正 |
| `style` | コードスタイル修正（フォーマット等） |
| `refactor` | リファクタリング |
| `test` | テスト追加・修正 |
| `chore` | ビルド・設定等の雑務 |

```
# 例
feat: レース名表示を改善 - 特別レース名を優先表示
fix: 日付選択時のエラーを修正
docs: CLAUDE.md を追加
refactor: API クライアントの共通処理を抽出
test: レース取得APIのテストを追加
```

## 動作確認

修正後は AWS クラウド上の環境をブラウザで開き、実際に意図した修正がなされたか動作確認すること。

## 注意事項

- セキュリティを最優先にしたコーディング（IAM最小権限原則、シークレット管理など）
