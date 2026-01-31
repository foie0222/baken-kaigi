#!/bin/bash
# PreToolUse hook: mainワークツリーでの編集操作をブロック
#
# mainワークツリー内のファイルに対してEdit/Writeツールが呼ばれた場合にエラーを返す
# 注意: git rev-parse ではなくファイルパスで判定する（worktree対応）

set -e

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null || echo "")

# Edit/Write以外は許可
[ "$TOOL_NAME" != "Edit" ] && [ "$TOOL_NAME" != "Write" ] && exit 0

# 編集対象のファイルパスを取得
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null || echo "")

# ファイルパスが空の場合は許可
[ -z "$FILE_PATH" ] && exit 0

# mainワークツリー内のファイル編集をブロック
# パターン: /baken-kaigi/main/ を含むパス
if echo "$FILE_PATH" | grep -q "/baken-kaigi/main/"; then
  echo "BLOCK: mainワークツリー内のファイル編集は禁止されています。" >&2
  echo "featureブランチのworktreeで作業してください: git worktree add <name> -b feature/<name>" >&2
  exit 2
fi

exit 0
