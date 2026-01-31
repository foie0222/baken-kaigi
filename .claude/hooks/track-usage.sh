#!/bin/bash
# Claude Code スキル・エージェント使用追跡フック
# PreToolUseで呼び出され、SkillとTaskツールの使用をログに記録する

# エラーが発生してもツール実行はブロックしない
set +e

# jqコマンドの存在確認（未インストールでもツール実行はブロックしない）
if ! command -v jq >/dev/null 2>&1; then
    exit 0
fi

# 相対パスを使用（フックはプロジェクトルートから実行される）
LOG_DIR=".claude/logs"
LOG_FILE="${LOG_DIR}/usage-log.jsonl"

# ログディレクトリが存在しない場合は作成し、パーミッションを制限
mkdir -p "${LOG_DIR}" 2>/dev/null
chmod 700 "${LOG_DIR}" 2>/dev/null

# stdinからツール入力を読み取る
INPUT=$(cat)

# ツール名を取得
TOOL_NAME=$(echo "${INPUT}" | jq -r '.tool_name // empty' 2>/dev/null || echo "")

# ツール名が取得できない場合は終了
if [[ -z "${TOOL_NAME}" ]]; then
    exit 0
fi

# タイムスタンプを生成（ISO 8601形式、タイムゾーン付き）
TIMESTAMP=$(date '+%Y-%m-%dT%H:%M:%S%:z')

# ログ書き込み関数（flockでファイルロック）
write_log() {
    local log_entry="$1"
    (
        flock -x 200
        echo "${log_entry}" >> "${LOG_FILE}"
    ) 200>"${LOG_FILE}.lock" 2>/dev/null
}

# Skillツールの場合
if [[ "${TOOL_NAME}" == "Skill" ]]; then
    SKILL_NAME=$(echo "${INPUT}" | jq -r '.tool_input.skill // empty' 2>/dev/null || echo "")
    SKILL_ARGS=$(echo "${INPUT}" | jq -r '.tool_input.args // empty' 2>/dev/null || echo "")

    if [[ -n "${SKILL_NAME}" ]]; then
        LOG_ENTRY=$(jq -n -c \
            --arg ts "${TIMESTAMP}" \
            --arg type "skill" \
            --arg name "${SKILL_NAME}" \
            --arg args "${SKILL_ARGS}" \
            '{timestamp: $ts, type: $type, name: $name, args: $args}' 2>/dev/null)
        write_log "${LOG_ENTRY}"
    fi
fi

# Taskツールの場合
if [[ "${TOOL_NAME}" == "Task" ]]; then
    AGENT_TYPE=$(echo "${INPUT}" | jq -r '.tool_input.subagent_type // empty' 2>/dev/null || echo "")
    DESCRIPTION=$(echo "${INPUT}" | jq -r '.tool_input.description // empty' 2>/dev/null || echo "")

    if [[ -n "${AGENT_TYPE}" ]]; then
        LOG_ENTRY=$(jq -n -c \
            --arg ts "${TIMESTAMP}" \
            --arg type "agent" \
            --arg name "${AGENT_TYPE}" \
            --arg desc "${DESCRIPTION}" \
            '{timestamp: $ts, type: $type, name: $name, description: $desc}' 2>/dev/null)
        write_log "${LOG_ENTRY}"
    fi
fi

# フックは常に成功を返す（ツール実行をブロックしない）
exit 0
