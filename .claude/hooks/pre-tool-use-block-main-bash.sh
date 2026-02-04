#!/bin/bash
# PreToolUse hook: mainワークツリーでのBash破壊的操作をブロック
#
# mainワークツリー内のファイルに対して破壊的なBashコマンドが呼ばれた場合にエラーを返す

set -e

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null || echo "")

# Bash以外は許可
[ "$TOOL_NAME" != "Bash" ] && exit 0

# コマンドを取得
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || echo "")

# コマンドが空の場合は許可
[ -z "$COMMAND" ] && exit 0

# 現在のワーキングディレクトリがmainワークツリー内かチェック
MAIN_WORKTREE="/home/inoue-d/dev/baken-kaigi/main"
if [ "$PWD" = "$MAIN_WORKTREE" ] || [[ "$PWD" == "$MAIN_WORKTREE/"* ]]; then
  IN_MAIN_DIR=true
else
  IN_MAIN_DIR=false
fi

# 破壊的コマンドのパターン
# rm, mv, git reset --hard, git checkout ., git restore ., truncate, shred
DESTRUCTIVE_PATTERN='(^|[;&|])[[:space:]]*(rm|mv|truncate|shred)[[:space:]]'
GIT_DESTRUCTIVE_PATTERN='git[[:space:]]+(reset[[:space:]]+--hard|checkout[[:space:]]+\.|restore[[:space:]]+\.)'

# mainワークツリーのパスを含むかチェック
MAIN_PATH_PATTERN='/baken-kaigi/main/'

# コマンドにmainワークツリーのパスが含まれる場合
if echo "$COMMAND" | grep -q "$MAIN_PATH_PATTERN"; then
  if echo "$COMMAND" | grep -qE "$DESTRUCTIVE_PATTERN"; then
    echo "BLOCK: mainワークツリー内のファイルに対する破壊的操作は禁止されています。" >&2
    echo "featureブランチのworktreeで作業してください。" >&2
    exit 2
  fi
fi

# 現在のディレクトリがmainワークツリー内で、破壊的コマンドを実行しようとしている場合
if [ "$IN_MAIN_DIR" = true ]; then
  # 絶対パスがmain外を指している場合は許可
  # 絶対パスで始まり、かつ main ワークツリーのパスを含まない場合はスキップ
  if echo "$COMMAND" | grep -qE "$DESTRUCTIVE_PATTERN"; then
    # 絶対パスを抽出して確認（/で始まり、mainパスを含まない場合は許可）
    TARGET_PATHS=$(echo "$COMMAND" | grep -oE '/[^[:space:];|&]+' || true)
    ALL_OUTSIDE_MAIN=true
    for path in $TARGET_PATHS; do
      if echo "$path" | grep -q "$MAIN_PATH_PATTERN"; then
        ALL_OUTSIDE_MAIN=false
        break
      fi
    done
    # 絶対パスがあり、すべてmain外なら許可
    if [ -n "$TARGET_PATHS" ] && [ "$ALL_OUTSIDE_MAIN" = true ]; then
      exit 0
    fi
    # 相対パスまたはmain内の絶対パスがある場合はブロック
    echo "BLOCK: mainワークツリー内での破壊的コマンド (rm, mv等) は禁止されています。" >&2
    echo "featureブランチのworktreeで作業してください。" >&2
    exit 2
  fi
  if echo "$COMMAND" | grep -qE "$GIT_DESTRUCTIVE_PATTERN"; then
    echo "BLOCK: mainワークツリー内での破壊的Gitコマンドは禁止されています。" >&2
    echo "featureブランチのworktreeで作業してください。" >&2
    exit 2
  fi
fi

exit 0
