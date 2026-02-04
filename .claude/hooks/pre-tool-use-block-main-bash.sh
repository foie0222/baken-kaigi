#!/bin/bash
# PreToolUse hook: mainワークツリーでのBash破壊的操作をブロック
#
# mainワークツリー内のファイルに対して破壊的なBashコマンドが呼ばれた場合にエラーを返す
# 注意: 環境に依存しないパターンマッチング（/baken-kaigi/main/）を使用

set -e

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null || echo "")

# Bash以外は許可
[ "$TOOL_NAME" != "Bash" ] && exit 0

# コマンドを取得
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || echo "")

# コマンドが空の場合は許可
[ -z "$COMMAND" ] && exit 0

# mainワークツリーのパスパターン（環境に依存しない）
MAIN_PATH_PATTERN='/baken-kaigi/main/'

# 現在のワーキングディレクトリがmainワークツリー内かチェック（パターンマッチング）
case "$PWD" in
  */baken-kaigi/main | */baken-kaigi/main/*)
    IN_MAIN_DIR=true
    ;;
  *)
    IN_MAIN_DIR=false
    ;;
esac

# 破壊的コマンドのパターン
# rm, mv, truncate, shred
DESTRUCTIVE_PATTERN='(^|[;&|])[[:space:]]*(rm|mv|truncate|shred)[[:space:]]'
# git reset --hard, git checkout .(./path含む), git restore .(./path含む), git clean -fd
GIT_DESTRUCTIVE_PATTERN='git[[:space:]]+(reset[[:space:]]+--hard|checkout[[:space:]]+\.(/[^[:space:];|&]+)?|restore[[:space:]]+\.(/[^[:space:];|&]+)?|clean[[:space:]]+-[fd]+)'

# コマンドにmainワークツリーのパスが含まれる場合
if echo "$COMMAND" | grep -q "$MAIN_PATH_PATTERN"; then
  if echo "$COMMAND" | grep -qE "$DESTRUCTIVE_PATTERN"; then
    echo "BLOCK: mainワークツリー内のファイルに対する破壊的操作は禁止されています。" >&2
    echo "featureブランチのworktreeで作業してください。" >&2
    exit 2
  fi
  if echo "$COMMAND" | grep -qE "$GIT_DESTRUCTIVE_PATTERN"; then
    echo "BLOCK: mainワークツリー内のファイルに対する破壊的操作は禁止されています。" >&2
    echo "featureブランチのworktreeで作業してください。" >&2
    exit 2
  fi
fi

# 現在のディレクトリがmainワークツリー内で、破壊的コマンドを実行しようとしている場合
if [ "$IN_MAIN_DIR" = true ]; then
  if echo "$COMMAND" | grep -qE "$DESTRUCTIVE_PATTERN"; then
    # 絶対パスを抽出して確認（/で始まり、mainパスを含まない場合は許可）
    # クォート付き/無しの絶対パスを抽出
    TARGET_PATHS=$(echo "$COMMAND" | grep -oE '"(/[^"]+)"|'\''(/[^'\'']+)'\''|(/[^[:space:];|&"'\'']+)' | sed 's/^["'\'']//' | sed 's/["'\'']$//' | grep '^/' || true)
    ALL_OUTSIDE_MAIN=true
    HAS_PATH=false

    # while read で安全に反復処理
    if [ -n "$TARGET_PATHS" ]; then
      echo "$TARGET_PATHS" | while read -r path; do
        if [ -n "$path" ]; then
          if echo "$path" | grep -q "$MAIN_PATH_PATTERN"; then
            # main内のパスが見つかった場合、フラグファイルを作成
            echo "found" > /tmp/main_path_found_$$
          fi
        fi
      done
      HAS_PATH=true
    fi

    # main内のパスが見つかったかチェック
    if [ -f /tmp/main_path_found_$$ ]; then
      rm -f /tmp/main_path_found_$$
      ALL_OUTSIDE_MAIN=false
    fi

    # 絶対パスがあり、すべてmain外なら許可
    if [ "$HAS_PATH" = true ] && [ "$ALL_OUTSIDE_MAIN" = true ]; then
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
