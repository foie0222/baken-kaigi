#!/bin/bash
# PreToolUse hook: PRマージを条件付きで許可
#
# stdin から JSON を受け取り、以下の制御を行う:
# - gh pr merge: Copilotレビュー + 全コメント解決済みの場合のみ許可
# - gh pr close: 許可
# - resolveReviewThread: 許可

set -e

# stdin から JSON を読み取り
INPUT=$(cat)

# ツール名を取得
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null || echo "")

# Bash ツール以外は許可
[ "$TOOL_NAME" != "Bash" ] && exit 0

# コマンドを取得
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || echo "")

# gh pr merge を条件付きで許可
if echo "$COMMAND" | grep -qE '^[[:space:]]*([[:alnum:]/._-]+/)?gh[[:space:]]+pr[[:space:]]+merge\b'; then
  # --help フラグは許可
  if echo "$COMMAND" | grep -qE '\-\-help|\-h'; then
    exit 0
  fi

  # PR番号を抽出
  # パターン1: gh pr merge 123
  PR_NUMBER=$(echo "$COMMAND" | grep -oP 'merge\s+\K\d+' || true)

  # パターン2: gh pr merge https://github.com/.../pull/123
  if [ -z "$PR_NUMBER" ]; then
    PR_NUMBER=$(echo "$COMMAND" | grep -oP 'pull/\K\d+' || true)
  fi

  # パターン3: 引数なし（現在のブランチから取得）
  if [ -z "$PR_NUMBER" ]; then
    PR_NUMBER=$(gh pr view --json number -q '.number' 2>/dev/null || true)
  fi

  if [ -z "$PR_NUMBER" ]; then
    echo "BLOCK: PR番号を特定できませんでした。PR番号を明示的に指定してください。" >&2
    exit 2
  fi

  # Copilotレビューの確認
  HAS_COPILOT=$(gh pr view "$PR_NUMBER" --json reviews \
    --jq '[.reviews[] | select(.author.login == "copilot-pull-request-reviewer")] | length > 0' 2>/dev/null || echo "false")

  if [ "$HAS_COPILOT" != "true" ]; then
    echo "BLOCK: Copilotのレビューがありません。Copilotレビューを受けてからマージしてください。" >&2
    exit 2
  fi

  # 未解決コメントの確認
  REPO_INFO=$(gh repo view --json owner,name -q '"\(.owner.login)/\(.name)"' 2>/dev/null || echo "")
  OWNER=$(echo "$REPO_INFO" | cut -d'/' -f1)
  REPO=$(echo "$REPO_INFO" | cut -d'/' -f2)

  if [ -z "$OWNER" ] || [ -z "$REPO" ]; then
    echo "BLOCK: リポジトリ情報を取得できませんでした。" >&2
    exit 2
  fi

  UNRESOLVED_COUNT=$(gh api graphql -f query="
    query {
      repository(owner: \"$OWNER\", name: \"$REPO\") {
        pullRequest(number: $PR_NUMBER) {
          reviewThreads(first: 100) {
            nodes {
              isResolved
            }
          }
        }
      }
    }" --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length' 2>/dev/null || echo "-1")

  if [ "$UNRESOLVED_COUNT" = "-1" ]; then
    echo "BLOCK: PRの状態を確認できませんでした。" >&2
    exit 2
  fi

  if [ "$UNRESOLVED_COUNT" -gt 0 ]; then
    echo "BLOCK: 未解決のコメントが${UNRESOLVED_COUNT}件あります。全てのコメントを解決してからマージしてください。" >&2
    exit 2
  fi

  # 両方の条件を満たした場合は許可
  exit 0
fi

# gh pr close は許可
# resolveReviewThread は許可

exit 0
