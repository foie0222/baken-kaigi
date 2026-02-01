#!/bin/bash
# AgentCore Runtime用の依存関係をバンドルするスクリプト
# AgentCore RuntimeはARM64アーキテクチャで動作するため、ARM64用の依存関係が必要

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENTCORE_DIR="$PROJECT_ROOT/backend/agentcore"

echo "=== AgentCore バンドルスクリプト ==="
echo "プロジェクトルート: $PROJECT_ROOT"
echo "AgentCoreディレクトリ: $AGENTCORE_DIR"

# 既存の依存関係をクリーンアップ（*.dist-info と主要パッケージディレクトリ）
echo ""
echo "既存の依存関係をクリーンアップ中..."
cd "$AGENTCORE_DIR"

# dist-info ディレクトリを削除
find . -maxdepth 1 -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true

# 主要なパッケージディレクトリを削除（agent.py, prompts, tools, requirements.txt は保持）
for item in */; do
    case "$item" in
        prompts/|tools/|__pycache__/|.bedrock_agentcore/)
            # これらは保持
            ;;
        *)
            rm -rf "$item"
            ;;
    esac
done

# .so ファイルを削除
find . -maxdepth 1 -name "*.so" -delete 2>/dev/null || true

# ARM64用の依存関係をインストール
echo ""
echo "ARM64用の依存関係をインストール中..."
uv run --with pip pip install \
    --platform manylinux2014_aarch64 \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    -r requirements.txt \
    -t .

echo ""
echo "=== バンドル完了 ==="
echo "AgentCoreディレクトリの内容:"
ls -la | head -20
echo "..."
echo ""
echo "次のステップ: cd cdk && npx cdk deploy --all --context jravan=true"
