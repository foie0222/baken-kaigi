#!/bin/bash
# PostToolUse hook: ファイル編集後の自動lint/構文チェック
set -e

# jq でファイルパスを抽出
FILE_PATH=$(jq -r '.tool_input.file_path' 2>/dev/null || echo "")
[ -z "$FILE_PATH" ] && exit 0
[ ! -f "$FILE_PATH" ] && exit 0

# フロントエンド TypeScript/TSX: eslint --fix
if echo "$FILE_PATH" | grep -qE "frontend/.*\\.tsx?$"; then
  cd "$(dirname "$FILE_PATH")/../.." 2>/dev/null || exit 0
  npx eslint --fix "$FILE_PATH" 2>/dev/null || true
fi

# バックエンド Python: 構文チェック
if echo "$FILE_PATH" | grep -qE "backend/.*\\.py$"; then
  python3 -m py_compile "$FILE_PATH" 2>&1 || true
fi

exit 0
