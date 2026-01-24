# Git運用ガイド

## ブランチ運用ルール

**重要**: `main` ブランチへの直接 push は禁止

```
feature ブランチ作成 → 開発 → PR作成 → CI成功 → レビュー対応 → マージ
```

## Git Worktree

このリポジトリは `git worktree` で並行作業可能。

```bash
# worktree一覧
git worktree list

# 新しいブランチで作業開始
git worktree add feature-xxx -b feature/xxx

# 作業後の削除
git worktree remove feature-xxx
git branch -d feature/xxx
```

### ディレクトリ構成

```
baken-kaigi/
├── .bare/              # bare リポジトリ（実体）
├── main/               # main ブランチ
└── feature-xxx/        # feature ブランチ
```

## コミットメッセージ

```
feat: 新機能追加
fix: バグ修正
docs: ドキュメント修正
style: コードスタイル修正
refactor: リファクタリング
test: テスト追加・修正
chore: ビルド・設定等
```

例:
```
feat: レース名表示を改善 - 特別レース名を優先表示
fix: 日付選択時のエラーを修正
```

## PRレビュー対応

GitHub Copilot によるレビューコメントへの対応:

```bash
/copilot-review <PR番号>
```

詳細は `/copilot-review` スキルを参照。

### 手動対応する場合

```bash
# コメント確認
gh api repos/foie0222/baken-kaigi/pulls/<PR番号>/comments --jq '.[] | {id, path, body}'

# 修正後、返信
gh api repos/foie0222/baken-kaigi/pulls/<PR番号>/comments/<コメントID>/replies \
  -X POST -f body='修正しました。'
```

**重要**: 全てのコメントを解決しないとマージできない（ブランチ保護ルール）。
