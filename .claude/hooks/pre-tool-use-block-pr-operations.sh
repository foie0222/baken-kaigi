#!/bin/bash
# PreToolUse hook: PRマージを条件付きで許可
#
# stdin から JSON を受け取り、以下の制御を行う:
# - gh pr merge: Copilotレビューコメント投稿済み + 全コメント解決済みの場合のみ許可
# - GitHub API 直接呼び出し: ブロック（hookバイパス防止）
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

# GitHub REST API での PR 直接操作をブロック（hookバイパス防止）
# curl, wget, gh api などツールに依存せず、GitHub の PR エンドポイント自体へのアクセスを検出
if echo "$COMMAND" | grep -qiE 'api\.github\.com.*/pulls/[0-9]+/(merge|update)'; then
  echo "BLOCK: GitHub REST APIでのPR直接操作は禁止されています。" >&2
  echo "gh CLIを使用してください: gh pr merge <PR番号>" >&2
  exit 2
fi

# GitHub GraphQL API での mergePullRequest mutation をブロック
if echo "$COMMAND" | grep -qiE 'api\.github\.com/graphql' && echo "$COMMAND" | grep -qiE 'mergePullRequest'; then
  echo "BLOCK: GitHub GraphQL APIでのPR直接操作は禁止されています。" >&2
  echo "gh CLIを使用してください: gh pr merge <PR番号>" >&2
  exit 2
fi

# gh api での PR 直接操作をブロック
if echo "$COMMAND" | grep -qE 'gh[[:space:]]+api.*pulls/[0-9]+/(merge|update)'; then
  echo "BLOCK: gh apiでのPR直接操作は禁止されています。" >&2
  echo "gh pr merge を使用してください" >&2
  exit 2
fi

# gh pr merge を条件付きで許可
if echo "$COMMAND" | grep -qE '^[[:space:]]*([[:alnum:]/._~-]+/)?gh[[:space:]]+pr[[:space:]]+merge\b'; then
  # --help フラグは許可
  if echo "$COMMAND" | grep -qE '\-\-help|\-h'; then
    exit 0
  fi

  # PR番号を抽出（POSIX準拠：sedを使用）
  # パターン1: gh pr merge 123
  PR_NUMBER=$(echo "$COMMAND" | sed -n 's/.*merge[[:space:]][[:space:]]*\([0-9][0-9]*\).*/\1/p' | head -n 1)

  # パターン2: gh pr merge https://github.com/.../pull/123
  if [ -z "$PR_NUMBER" ]; then
    PR_NUMBER=$(echo "$COMMAND" | sed -n 's#.*/pull/\([0-9][0-9]*\).*#\1#p' | head -n 1)
  fi

  # パターン3: 引数なし（現在のブランチから取得）
  if [ -z "$PR_NUMBER" ]; then
    PR_NUMBER=$(gh pr view --json number -q '.number' 2>/dev/null || true)
  fi

  if [ -z "$PR_NUMBER" ]; then
    echo "BLOCK: PR番号を特定できませんでした。PR番号を明示的に指定してください。" >&2
    exit 2
  fi

  # PR番号が純粋な整数であることを確認
  if ! echo "$PR_NUMBER" | grep -qE '^[0-9]+$'; then
    echo "BLOCK: 無効なPR番号です: $PR_NUMBER" >&2
    exit 2
  fi

  # リポジトリ情報を取得してバリデーション（Copilotコメント確認に必要）
  REPO_INFO=$(gh repo view --json owner,name -q '"\(.owner.login)/\(.name)"' 2>/dev/null || echo "")
  OWNER=$(echo "$REPO_INFO" | cut -d'/' -f1)
  REPO=$(echo "$REPO_INFO" | cut -d'/' -f2)

  if [ -z "$OWNER" ] || [ -z "$REPO" ]; then
    echo "BLOCK: リポジトリ情報を取得できませんでした。" >&2
    exit 2
  fi

  # OWNER/REPOが英数字、ハイフン、アンダースコアのみであることを確認
  if ! echo "$OWNER" | grep -qE '^[a-zA-Z0-9_-]+$'; then
    echo "BLOCK: 無効なリポジトリオーナー名です。" >&2
    exit 2
  fi
  if ! echo "$REPO" | grep -qE '^[a-zA-Z0-9_.-]+$'; then
    echo "BLOCK: 無効なリポジトリ名です。" >&2
    exit 2
  fi

  # Copilotレビューコメントと未解決コメントの確認（1回のクエリで取得）
  # ※レビューが「存在する」だけでなく「コメントが投稿済み」であることを確認
  # ※各スレッドで最大10件のコメントを取得し、Copilotの返信コメントも検知
  COPILOT_QUERY=$(cat <<EOF
query {
  repository(owner: "$OWNER", name: "$REPO") {
    pullRequest(number: $PR_NUMBER) {
      reviewThreads(first: 100) {
        totalCount
        nodes {
          isResolved
          comments(first: 10) {
            nodes {
              author { login }
            }
          }
        }
      }
    }
  }
}
EOF
  )

  QUERY_RESULT=$(gh api graphql -f query="$COPILOT_QUERY" 2>/dev/null || echo "")
  if [ -z "$QUERY_RESULT" ]; then
    echo "BLOCK: PRの状態を確認できませんでした（APIリクエスト失敗）。" >&2
    exit 2
  fi

  # GraphQLエラーの確認（.errors が存在する場合はエラー）
  HAS_ERRORS=$(echo "$QUERY_RESULT" | jq 'has("errors")' 2>/dev/null || echo "true")
  if [ "$HAS_ERRORS" = "true" ]; then
    ERROR_MSG=$(echo "$QUERY_RESULT" | jq -r '.errors[0].message // "不明なエラー"' 2>/dev/null || echo "不明なエラー")
    echo "BLOCK: PRの状態を確認できませんでした（GraphQLエラー: ${ERROR_MSG}）。" >&2
    exit 2
  fi

  # .data.repository.pullRequest が null でないことを確認
  PR_DATA=$(echo "$QUERY_RESULT" | jq '.data.repository.pullRequest' 2>/dev/null || echo "null")
  if [ "$PR_DATA" = "null" ]; then
    echo "BLOCK: PRの情報を取得できませんでした（PR番号が無効か、アクセス権限がありません）。" >&2
    exit 2
  fi

  # Copilotのコメント数を確認（コメントが1件以上投稿されているか）
  # jq失敗時は-1を返して後続のエラーチェックで検出
  COPILOT_COMMENT_COUNT=$(echo "$QUERY_RESULT" | jq '[.data.repository.pullRequest.reviewThreads.nodes[].comments.nodes[] | select(.author.login == "copilot-pull-request-reviewer")] | length' 2>/dev/null)
  if [ -z "$COPILOT_COMMENT_COUNT" ] || ! echo "$COPILOT_COMMENT_COUNT" | grep -qE '^[0-9]+$'; then
    echo "BLOCK: Copilotコメント数の取得に失敗しました（レスポンス解析エラー）。" >&2
    exit 2
  fi

  if [ "$COPILOT_COMMENT_COUNT" -eq 0 ]; then
    echo "BLOCK: Copilotのレビューコメントがありません。Copilotレビューが完了してからマージしてください。" >&2
    exit 2
  fi

  # 総コメント数を確認（100件を超える場合は警告）
  TOTAL_COUNT=$(echo "$QUERY_RESULT" | jq '.data.repository.pullRequest.reviewThreads.totalCount // -1' 2>/dev/null || echo "-1")
  if [ "$TOTAL_COUNT" -gt 100 ]; then
    echo "BLOCK: レビューコメントが100件を超えています（${TOTAL_COUNT}件）。全てのコメントを確認できないため、手動でマージしてください。" >&2
    exit 2
  fi

  # 未解決コメントの確認
  UNRESOLVED_COUNT=$(echo "$QUERY_RESULT" | jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length' 2>/dev/null || echo "-1")

  if [ "$UNRESOLVED_COUNT" = "-1" ]; then
    echo "BLOCK: PRの状態を確認できませんでした。" >&2
    exit 2
  fi

  if [ "$UNRESOLVED_COUNT" -gt 0 ]; then
    echo "BLOCK: 未解決のコメントが${UNRESOLVED_COUNT:-0}件あります。全てのコメントを解決してからマージしてください。" >&2
    exit 2
  fi

  # 全ての条件を満たした場合は許可
  exit 0
fi

# gh pr close は許可
# resolveReviewThread は許可

exit 0
