# CLAUDE.md

## プロジェクト構造

```
baken-kaigi/
├── frontend/     # React + TypeScript + Vite
├── backend/      # Python Lambda
├── cdk/          # AWS CDK インフラ
├── jravan-api/   # JRA-VAN API（EC2用）
└── aidlc-docs/   # DDD設計ドキュメント
```

## 開発プロセス

### DDD（ドメイン駆動設計）

設計ドキュメント: `aidlc-docs/construction/unit_01_ai_dialog_public/docs/`
- `ubiquitous_language.md` - ユビキタス言語
- `entities.md` - エンティティ
- `value_objects.md` - 値オブジェクト
- `aggregates.md` - 集約
- `domain_services.md` - ドメインサービス

### TDD（テスト駆動開発）

1. **Red** - 失敗するテストを書く
2. **Green** - テストが通る最小限のコードを書く
3. **Refactor** - リファクタリング

## 重要コマンド

```bash
# デプロイ前チェック（必須）
./scripts/pre-deploy-check.sh

# CDKデプロイ（必ず --context jravan=true を付ける）
cd cdk && npx cdk deploy --all --context jravan=true --require-approval never

# フロントエンド開発
cd frontend && npm run dev

# バックエンドテスト
cd backend && pytest
```

## コミットメッセージ

`feat|fix|docs|style|refactor|test|chore: 説明`

## Git運用

- `main` への直接 push 禁止
- feature ブランチ → PR → レビュー対応 → マージ
- `git worktree` で作業ディレクトリを分離して並行作業
- 詳細: `.claude/docs/git-workflow.md`

## 動作確認

修正後は必ず本番環境で動作確認すること。

## 詳細ドキュメント

- AWS操作: `.claude/docs/aws-operations.md`
- Git運用: `.claude/docs/git-workflow.md`

## タスク別ワークフロー

### 新機能実装時
`tdd-generator` エージェントを使用してTDD駆動で実装する。
- Red → Green → Refactor サイクルを自動実行

### API拡張時
1. `/ddd-check` でドメイン設計との整合性を検証
2. `/api-extend` で6段階ワークフロー実行（ports → provider → handler → Mock → テスト → フロント型 → UI）
3. `frontend-mapper` エージェントでTypeScript型を自動生成

### UI実装時
- `/ui-component` でReact + Tailwind CSSパターンを適用
- コンポーネント設計のベストプラクティスに従う

### PR対応時
- `/copilot-review` でGitHub Copilotレビューコメントを取得→修正→返信→解決

### デプロイ前（必須）
- `/deploy-prep` でチェックスクリプト実行（テスト、リント、CDK Synth検証）

### Issue対応時
- `/issue-to-task` でGitHub Issueからタスク分解・チェックリスト生成

### EC2操作時
- `/ec2-sync` でSSMコマンドを簡素化
- `/jravan-ec2` でJRA-VAN APIへのファイル送信

### コードベース調査時
`Explore` エージェントを使用して効率的に調査する。

## 注意事項

- セキュリティ最優先（IAM最小権限、シークレット管理）
- CDKは必ず `--context jravan=true` を付ける
