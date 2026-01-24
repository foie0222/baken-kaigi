#!/bin/bash
# PreToolUse hook: 危険なGitHub操作をブロック
#
# stdin から JSON を受け取り、以下の操作をブロック:
# - gh pr merge / gh pr close
# - gh api でのPRコメントresolve (resolveReviewThread)

set -e

# stdin から JSON を読み取り
INPUT=$(cat)

# ツール名を取得（jq -r は存在しないキーで "null" を返すため // "" でデフォルト空文字に）
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null || echo "")

# Bash ツール以外は許可
[ "$TOOL_NAME" != "Bash" ] && exit 0

# コマンドを取得
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || echo "")

# gh pr merge または gh pr close をブロック
# - 絶対パス (/usr/bin/gh) にも対応
# - echo "gh pr merge" のような安全なコマンドは除外（先頭コマンドのみマッチ）
if echo "$COMMAND" | grep -qE '^[[:space:]]*([[:alnum:]/._-]+/)?gh[[:space:]]+pr[[:space:]]+(merge|close)\b'; then
  echo "BLOCK: PRのマージ/クローズは手動で行ってください。Claudeからの実行は禁止されています。" >&2
  exit 2
fi

# gh api での resolveReviewThread をブロック（PRコメントのresolve）
if echo "$COMMAND" | grep -qE '^[[:space:]]*([[:alnum:]/._-]+/)?gh[[:space:]]+api([[:space:]]|$)' && echo "$COMMAND" | grep -qE 'resolveReviewThread'; then
  echo "BLOCK: PRコメントのresolveは手動で行ってください。Claudeからの実行は禁止されています。" >&2
  exit 2
fi

exit 0
