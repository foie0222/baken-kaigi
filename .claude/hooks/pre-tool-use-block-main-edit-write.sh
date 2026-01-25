#!/bin/bash
# PreToolUse hook: mainブランチでの編集操作をブロック
#
# mainブランチでEdit/Writeツールが呼ばれた場合にエラーを返す

set -e

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null || echo "")

# Edit/Write以外は許可
[ "$TOOL_NAME" != "Edit" ] && [ "$TOOL_NAME" != "Write" ] && exit 0

# 現在のブランチを取得
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

# mainブランチの場合はブロック
if [ "$CURRENT_BRANCH" = "main" ]; then
  echo "BLOCK: mainブランチでのファイル編集は禁止されています。" >&2
  echo "worktreeで作業してください: git worktree add <name> -b feature/<name>" >&2
  exit 2
fi

exit 0
