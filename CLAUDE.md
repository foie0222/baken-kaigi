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

### デプロイ前チェック

**重要**: デプロイ前には必ずチェックスクリプトを実行すること。

```bash
# デプロイ前チェック（テスト・リント・CDK Synth）
./scripts/pre-deploy-check.sh
```

このスクリプトは以下を自動実行します:
1. バックエンドテスト (`pytest`)
2. フロントエンドリント (`npm run lint`)
3. フロントエンドテスト (`npm run test:run`)
4. CDK Synth 確認

### CDK デプロイ

**重要**: CDKデプロイは必ず `--context jravan=true` を付けて実行すること。
このフラグがないとLambda関数がVPCなしのモックモードになってしまう。

```bash
# バックエンドのデプロイ（必須オプション付き）
cd cdk
npx cdk deploy --all --context jravan=true --require-approval never
```

### EC2 コード更新

JRA-VAN API のコードを EC2 に反映する手順:

**注意**: EC2 には Git がインストールされていないため、SSM 経由で直接ファイルを送信する。

```bash
# 1. インスタンスID確認
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=*jravan*" \
  --query 'Reservations[].Instances[].InstanceId' --output text)

# 2. ファイルをBase64エンコードしてSSM経由で送信
FILE_B64=$(base64 jravan-api/sync_jvlink.py | tr -d '\n')
aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunPowerShellScript" \
  --parameters "commands=[\"[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('$FILE_B64')) | Out-File -FilePath C:\\jravan-api\\sync_jvlink.py -Encoding UTF8 -Force\"]"

# 3. データ再同期（差分）
aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunPowerShellScript" \
  --parameters 'commands=["cd C:\\jravan-api; python sync_jvlink.py"]'

# 4. データ再同期（指定日から）
aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunPowerShellScript" \
  --parameters 'commands=["cd C:\\jravan-api; python sync_jvlink.py --from 20260101"]'
```

### デプロイ後の確認

1. **ブラウザでの動作確認** - 必ず本番環境で意図した修正が反映されていることを確認
2. **レース情報の確認** - レース名・距離・コース情報が正しく表示されること
3. **エラーログの確認** - CloudWatch Logs でエラーが発生していないこと

### API エンドポイント確認

```bash
# API Gateway エンドポイント確認
aws apigateway get-rest-apis --query 'items[?name==`baken-kaigi`].id' --output text
```

## CI/CD

### GitHub Actions

プッシュ・PR 時に自動でテストが実行されます:

- **frontend-test**: リント、型チェック、テスト
- **backend-test**: pytest によるテスト
- **cdk-synth**: CDK 構文チェック

### Amplify

フロントエンドは Amplify でホスティングされています。
`main` ブランチへのプッシュで自動デプロイが実行されます。

デプロイ前に以下が自動実行されます:
- `npm run lint`
- `npm run test:run`

## Git 管理

### ブランチ運用ルール

**重要**: `main` ブランチへの直接 push は禁止（運用ルール）

```
feature ブランチ作成
    ↓
開発・コミット
    ↓
PR 作成
    ↓
CI 成功確認（Frontend Tests / Backend Tests / CDK Synth Check）
    ↓
Copilot レビューコメント対応
    ↓
マージ → 自動デプロイ
```

### PR レビューコメント対応

PR には GitHub Copilot による自動レビューが入ります。コメントが付いた場合は以下の手順で対応すること。

#### 1. コメント確認

```bash
# レビューコメントを確認
gh api repos/foie0222/baken-kaigi/pulls/<PR番号>/comments --jq '.[] | {id, path, body}'
```

#### 2. 修正が必要か判断

- 指摘内容が妥当であれば修正を実施
- 対応不要と判断した場合は理由を返信

#### 3. 修正をコミット・プッシュ

```bash
git add <修正ファイル>
git commit -m "fix: Copilotレビュー指摘対応"
git push
```

#### 4. コメントに返信

```bash
gh api repos/foie0222/baken-kaigi/pulls/<PR番号>/comments/<コメントID>/replies \
  -X POST \
  -f body='修正しました。〜〜'
```

#### 5. スレッドを解決

```bash
# スレッドIDを取得
gh api graphql -f query='
query {
  repository(owner: "foie0222", name: "baken-kaigi") {
    pullRequest(number: <PR番号>) {
      reviewThreads(first: 10) {
        nodes {
          id
          isResolved
        }
      }
    }
  }
}'

# スレッドを解決
gh api graphql -f query='
mutation {
  resolveReviewThread(input: {threadId: "<スレッドID>"}) {
    thread {
      isResolved
    }
  }
}'
```

**重要**: ブランチ保護ルールにより、全てのコメントを解決しないとマージできません。

### Git Worktree によるブランチ管理

このリポジトリでは `git worktree` を使用して、ブランチごとに別フォルダで並行作業ができます。

#### ディレクトリ構成

```
baken-kaigi/
├── .bare/              # bare リポジトリ（実体）
├── .git                # bare リポジトリへの参照ファイル
├── main/               # main ブランチの worktree
├── feature-xxx/        # feature ブランチの worktree
└── docs-xxx/           # docs ブランチの worktree
```

#### 基本操作

```bash
# 現在の worktree 一覧を確認
git worktree list

# 新しいブランチで worktree を作成
git worktree add <フォルダ名> -b <ブランチ名>

# 例: feature/add-new-api ブランチで作業開始
git worktree add feature-add-new-api -b feature/add-new-api

# 既存のリモートブランチから worktree を作成
git worktree add <フォルダ名> <ブランチ名>

# worktree の削除（ブランチは残る）
git worktree remove <フォルダ名>

# worktree とブランチ両方を削除
git worktree remove <フォルダ名>
git branch -d <ブランチ名>
```

#### 開発フロー

```bash
# 1. 新機能開発用の worktree を作成
git worktree add feature-add-new-feature -b feature/add-new-feature

# 2. そのフォルダに移動して開発
cd feature-add-new-feature
# ... 開発作業 ...

# 3. コミット・プッシュ
git add .
git commit -m "feat: 新機能追加"
git push -u origin feature/add-new-feature

# 4. PR 作成
gh pr create --title "feat: 新機能追加" --body "説明"

# 5. マージ後、worktree を削除
cd ..
git worktree remove feature-add-new-feature
git branch -d feature/add-new-feature
```

#### メリット

- **並行作業**: 複数のブランチで同時に作業可能（ブランチ切り替え不要）
- **コンテキスト保持**: 各ブランチの作業状態がそのまま保存される
- **IDE 対応**: 各 worktree を別ウィンドウで開ける

#### 注意事項

- worktree フォルダは `.gitignore` で除外済み
- `main/` フォルダは常に最新の main ブランチを反映
- PR マージ後は不要な worktree を削除してクリーンに保つ

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
