#!/bin/bash
# PostToolUse hook: ファイル編集後の自動lint/構文チェック
#
# このスクリプトは Claude Code の PostToolUse フックとして実行される。
# Claude Code はツール実行後に、本スクリプトを起動し、ツール実行結果を表す JSON を
# stdin に書き込む。JSON の想定フォーマット:
#
# {
#   "tool_name": "Edit",
#   "tool_input": {
#     "file_path": "/absolute/path/to/file.tsx"
#   },
#   "tool_response": { ... }
# }
#
# - .tool_input.file_path には編集されたファイルの絶対パスが入る
# - file_path が存在しない/空の場合は何もせず終了する
set -e

# jq でファイルパスを抽出
FILE_PATH=$(jq -r '.tool_input.file_path' 2>/dev/null || echo "")
[ -z "$FILE_PATH" ] && exit 0
[ ! -f "$FILE_PATH" ] && exit 0

# フロントエンド TypeScript/TSX: eslint --fix
if echo "$FILE_PATH" | grep -qE "frontend/.*\\.tsx?$"; then
  # frontend/ 配下の相対パスに変換してから、frontend ディレクトリで eslint を実行する
  REL_PATH="${FILE_PATH#*frontend/}"
  (cd frontend && npx eslint --fix "$REL_PATH") || true
fi

# バックエンド Python: 構文チェック
if echo "$FILE_PATH" | grep -qE "backend/.*\\.py$"; then
  python3 -m py_compile "$FILE_PATH" || true
fi

exit 0
