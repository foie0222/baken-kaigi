#!/bin/bash
# Claude Code スキル・エージェント使用集計レポート
# 使用例:
#   .claude/scripts/usage-report.sh           # 全期間
#   .claude/scripts/usage-report.sh --today   # 今日のみ
#   .claude/scripts/usage-report.sh --week    # 過去7日間

set -euo pipefail

LOG_FILE="${HOME}/dev/baken-kaigi/.claude/logs/usage-log.jsonl"

# ログファイルが存在しない場合
if [[ ! -f "${LOG_FILE}" ]]; then
    echo "ログファイルが見つかりません: ${LOG_FILE}"
    echo "スキルやエージェントを使用するとログが記録されます。"
    exit 0
fi

# 期間フィルタの設定
FILTER_DATE=""
PERIOD_LABEL="全期間"

case "${1:-}" in
    --today)
        FILTER_DATE=$(date '+%Y-%m-%d')
        PERIOD_LABEL="今日 (${FILTER_DATE})"
        ;;
    --week)
        if [[ "$(uname)" == "Darwin" ]]; then
            FILTER_DATE=$(date -v-7d '+%Y-%m-%d')
        else
            FILTER_DATE=$(date -d '7 days ago' '+%Y-%m-%d')
        fi
        PERIOD_LABEL="過去7日間 (${FILTER_DATE} 以降)"
        ;;
    --help|-h)
        echo "使用方法: $0 [オプション]"
        echo ""
        echo "オプション:"
        echo "  (なし)     全期間のレポート"
        echo "  --today    今日のレポート"
        echo "  --week     過去7日間のレポート"
        echo "  --help     このヘルプを表示"
        exit 0
        ;;
    "")
        # 全期間
        ;;
    *)
        echo "不明なオプション: $1"
        echo "使用方法: $0 [--today|--week|--help]"
        exit 1
        ;;
esac

# フィルタリングされたログを取得
if [[ -n "${FILTER_DATE}" ]]; then
    FILTERED_LOG=$(jq -c "select(.timestamp >= \"${FILTER_DATE}\")" "${LOG_FILE}" 2>/dev/null || true)
else
    FILTERED_LOG=$(cat "${LOG_FILE}")
fi

# ログが空の場合
if [[ -z "${FILTERED_LOG}" ]]; then
    echo "=== Claude Code 使用レポート (${PERIOD_LABEL}) ==="
    echo ""
    echo "該当期間のログがありません。"
    exit 0
fi

echo "=== Claude Code 使用レポート (${PERIOD_LABEL}) ==="
echo ""

# 総使用回数
TOTAL_COUNT=$(echo "${FILTERED_LOG}" | wc -l | tr -d ' ')
SKILL_COUNT=$(echo "${FILTERED_LOG}" | jq -r 'select(.type == "skill")' | grep -c '"type"' || echo "0")
AGENT_COUNT=$(echo "${FILTERED_LOG}" | jq -r 'select(.type == "agent")' | grep -c '"type"' || echo "0")

echo "📊 総使用回数: ${TOTAL_COUNT}"
echo "   - スキル: ${SKILL_COUNT}"
echo "   - エージェント: ${AGENT_COUNT}"
echo ""

# スキル使用回数ランキング
echo "🎯 スキル使用回数ランキング:"
SKILL_RANKING=$(echo "${FILTERED_LOG}" | jq -r 'select(.type == "skill") | .name' 2>/dev/null | sort | uniq -c | sort -rn || true)
if [[ -n "${SKILL_RANKING}" ]]; then
    echo "${SKILL_RANKING}" | while read -r count name; do
        printf "   %3d回  %s\n" "${count}" "${name}"
    done
else
    echo "   (なし)"
fi
echo ""

# エージェント使用回数ランキング
echo "🤖 エージェント使用回数ランキング:"
AGENT_RANKING=$(echo "${FILTERED_LOG}" | jq -r 'select(.type == "agent") | .name' 2>/dev/null | sort | uniq -c | sort -rn || true)
if [[ -n "${AGENT_RANKING}" ]]; then
    echo "${AGENT_RANKING}" | while read -r count name; do
        printf "   %3d回  %s\n" "${count}" "${name}"
    done
else
    echo "   (なし)"
fi
echo ""

# 日別使用回数
echo "📅 日別使用回数:"
DAILY_USAGE=$(echo "${FILTERED_LOG}" | jq -r '.timestamp[:10]' 2>/dev/null | sort | uniq -c | sort -k2 || true)
if [[ -n "${DAILY_USAGE}" ]]; then
    echo "${DAILY_USAGE}" | while read -r count date; do
        printf "   %s: %3d回\n" "${date}" "${count}"
    done
else
    echo "   (なし)"
fi
