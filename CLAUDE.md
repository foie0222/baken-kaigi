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

## スキル

- `/copilot-review` - GitHub Copilot PRレビュー対応
- `/verification` - 本番環境（bakenkaigi.com）動作確認

## 作業方針

- 実装タスクには専門家チームを編成し、役割分担と並列作業で対応する

## 注意事項

- セキュリティ最優先（IAM最小権限、シークレット管理）
- CDKは必ず `--context jravan=true` を付ける
