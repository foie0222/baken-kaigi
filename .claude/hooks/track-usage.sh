#!/bin/bash
# Claude Code スキル・エージェント使用追跡フック
# PreToolUseで呼び出され、SkillとTaskツールの使用をログに記録する

set -euo pipefail

LOG_DIR="${HOME}/dev/baken-kaigi/.claude/logs"
LOG_FILE="${LOG_DIR}/usage-log.jsonl"

# ログディレクトリが存在しない場合は作成
mkdir -p "${LOG_DIR}"

# stdinからツール入力を読み取る
INPUT=$(cat)

# ツール名を取得
TOOL_NAME=$(echo "${INPUT}" | jq -r '.tool_name // empty')

# タイムスタンプを生成（ISO 8601形式、タイムゾーン付き）
TIMESTAMP=$(date '+%Y-%m-%dT%H:%M:%S%:z')

# Skillツールの場合
if [[ "${TOOL_NAME}" == "Skill" ]]; then
    SKILL_NAME=$(echo "${INPUT}" | jq -r '.tool_input.skill // empty')
    SKILL_ARGS=$(echo "${INPUT}" | jq -r '.tool_input.args // empty')

    if [[ -n "${SKILL_NAME}" ]]; then
        jq -n -c \
            --arg ts "${TIMESTAMP}" \
            --arg type "skill" \
            --arg name "${SKILL_NAME}" \
            --arg args "${SKILL_ARGS}" \
            '{timestamp: $ts, type: $type, name: $name, args: $args}' >> "${LOG_FILE}"
    fi
fi

# Taskツールの場合
if [[ "${TOOL_NAME}" == "Task" ]]; then
    AGENT_TYPE=$(echo "${INPUT}" | jq -r '.tool_input.subagent_type // empty')
    DESCRIPTION=$(echo "${INPUT}" | jq -r '.tool_input.description // empty')

    if [[ -n "${AGENT_TYPE}" ]]; then
        jq -n -c \
            --arg ts "${TIMESTAMP}" \
            --arg type "agent" \
            --arg name "${AGENT_TYPE}" \
            --arg desc "${DESCRIPTION}" \
            '{timestamp: $ts, type: $type, name: $name, description: $desc}' >> "${LOG_FILE}"
    fi
fi

# フックは常に成功を返す（ツール実行をブロックしない）
exit 0
